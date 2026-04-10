import importlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

from main import add_predictions_to_saved_report, send_to_mongo

root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

banks_dir = os.path.join(root_dir, "banks")
if banks_dir not in sys.path:
    sys.path.insert(0, banks_dir)

BANK_SPECS = [
    ("agrobank", "Agrobank"),
    ("aloqabank", "AloqaBank"),
    ("anorbank", "AnorBank"),
    ("apexbank", "ApexBank"),
    ("asakabank", "AsakaBank"),
    ("asiaalliancebank", "AsiaAllianceBank"),
    ("brb", "BRB"),
    ("cbu", "CBU"),
    ("davrbank", "DavrBank"),
    ("garantbank", "GarantBank"),
    ("hamkorbank", "HamkorBank"),
    ("hayotbank", "HayotBank"),
    ("infinbank", "InfinBank"),
    ("ipakyulibank", "IpakYuliBank"),
    ("ipotekabank", "IpotekaBank"),
    ("kapitalbank", "KapitalBank"),
    ("mikrokreditbank", "MikroKreditBank"),
    ("nbu", "NBU"),
    ("octobank", "OctoBank"),
    ("orientfinansbank", "OrientFinansBank"),
    ("poytaxtbank", "PoytaxtBank"),
    ("sqb", "SQB"),
    ("tbcbank", "TBCBank"),
    ("tengebank", "TengeBank"),
    ("trustbank", "TrustBank"),
    ("turonbank", "TuronBank"),
    ("universalbank", "UniversalBank"),
    ("xalqbank", "XalqBank"),
]

GOLD_BANK_SPEC = ("cbu_gold", "CbuGold")


def build_report_path():
    return os.path.join(root_dir, "currency_rates.json")


def load_report():
    file_path = build_report_path()
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _load_bank_class(module_name, class_name):
    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except Exception as e:
        print(f"[-] Пропускаю {class_name}: не удалось импортировать модуль {module_name} ({e})")
        return None


def build_banks():
    banks = []

    for module_name, class_name in BANK_SPECS:
        bank_class = _load_bank_class(module_name, class_name)
        if not bank_class:
            continue

        try:
            banks.append(bank_class())
        except Exception as e:
            print(f"[-] Пропускаю {class_name}: не удалось создать экземпляр ({e})")

    return banks


def build_gold_bank():
    module_name, class_name = GOLD_BANK_SPEC
    gold_class = _load_bank_class(module_name, class_name)
    if not gold_class:
        return None

    try:
        return gold_class()
    except Exception as e:
        print(f"[-] Пропускаю {class_name}: не удалось создать экземпляр ({e})")
        return None


def save_report_atomic(report):
    file_path = build_report_path()
    directory = os.path.dirname(file_path)

    fd, temp_path = tempfile.mkstemp(
        prefix="currency_rates_",
        suffix=".json",
        dir=directory,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=4)
        os.replace(temp_path, file_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return file_path


def build_server_report():
    report = load_report() or {}
    fallback_timestamp = report.get("timestamp")

    return {
        "timestamp": fallback_timestamp,
        "currency_updated_at": report.get("currency_updated_at") or (
            fallback_timestamp if report.get("banks") else None
        ),
        "gold_updated_at": report.get("gold_updated_at") or (
            fallback_timestamp if report.get("gold") else None
        ),
        "banks": report.get("banks", {}),
        "gold": report.get("gold", {}),
    }


def refresh_currency_rates(report, verbose=True):
    banks = build_banks()
    updated_banks = {}

    for bank in banks:
        if verbose:
            print(f"Получаю данные из {bank.bank_name}...")

        try:
            raw_data = bank.fetch_data()
            parsed_rates = bank.parse(raw_data)

            if parsed_rates:
                updated_banks[bank.bank_name] = parsed_rates
                if verbose:
                    print(f"Успешно: {parsed_rates}")
            elif verbose:
                print(f"Не удалось обработать данные для {bank.bank_name}")
        except Exception as e:
            if verbose:
                print(f"[-] Ошибка в {bank.bank_name}: {e}")

    if updated_banks:
        report["banks"] = updated_banks
        report["currency_updated_at"] = datetime.now().isoformat()

    return bool(updated_banks)


def refresh_gold_rates(report, verbose=True):
    gold = build_gold_bank()
    if not gold:
        return False

    if verbose:
        print(f"Получаю данные из {gold.bank_name}...")

    try:
        raw_gold_data = gold.fetch_data()
        parsed_gold = gold.parse(raw_gold_data)

        if parsed_gold:
            report["gold"] = parsed_gold
            report["gold_updated_at"] = datetime.now().isoformat()
            if verbose:
                print(f"Успешно: {parsed_gold}")
            return True

        if verbose:
            print(f"Не удалось обработать данные для {gold.bank_name}")
    except Exception as e:
        if verbose:
            print(f"[-] Ошибка в {gold.bank_name}: {e}")

    return False


def refresh_report_server(verbose=True):
    previous_report = load_report()
    report = build_server_report()

    currency_updated = refresh_currency_rates(report, verbose=verbose)
    gold_updated = refresh_gold_rates(report, verbose=verbose)

    report["timestamp"] = datetime.now().isoformat()
    file_path = save_report_atomic(report)
    mongo_report = {
        "timestamp": report["timestamp"],
        "banks": {},
        "gold": {},
        "predictions": {},
    }

    if currency_updated:
        report = add_predictions_to_saved_report(
            file_path,
            previous_report=previous_report,
            verbose=verbose,
        )
        mongo_report["banks"] = report.get("banks", {})
        mongo_report["predictions"] = report.get("predictions", {})
        mongo_report["currency_updated_at"] = report.get("currency_updated_at")

    if gold_updated:
        mongo_report["gold"] = report.get("gold", {})
        mongo_report["gold_updated_at"] = report.get("gold_updated_at")

    mongo_summary = send_to_mongo(mongo_report, verbose=verbose)

    if verbose:
        print()
        print(f"[+] JSON сохранен: {file_path}")
        print(f"[+] Валюты обновлены: {'да' if currency_updated else 'нет'}")
        print(f"[+] Золото обновлено: {'да' if gold_updated else 'нет'}")
        print(f"[+] Время обновления валют: {report.get('currency_updated_at')}")
        print(f"[+] Время обновления золота: {report.get('gold_updated_at')}")
        print(
            "[+] MongoDB: "
            + ", ".join(
                section_name
                for section_name, section_summary in mongo_summary.items()
                if section_summary.get("status") == "success"
            )
        )

    return report


def seconds_until_next_hour():
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return max(int((next_hour - now).total_seconds()), 1)


def main_server():
    print("[*] Запускаю серверное обновление курсов.")
    refresh_report_server(verbose=True)

    while True:
        sleep_seconds = seconds_until_next_hour()
        next_run = datetime.now() + timedelta(seconds=sleep_seconds)
        print(f"[*] Следующее обновление: {next_run.isoformat()}")
        time.sleep(sleep_seconds)
        refresh_report_server(verbose=True)


if __name__ == "__main__":
    try:
        main_server()
    except KeyboardInterrupt:
        print("\n[!] Остановка серверного обновления.")
