import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

root_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(root_dir)


def add_local_venv_site_packages():
    venv_lib_dir = os.path.join(project_root, ".venv", "lib")
    if not os.path.isdir(venv_lib_dir):
        return

    for entry in os.listdir(venv_lib_dir):
        site_packages_dir = os.path.join(venv_lib_dir, entry, "site-packages")
        if os.path.isdir(site_packages_dir) and site_packages_dir not in sys.path:
            sys.path.insert(0, site_packages_dir)


add_local_venv_site_packages()

import urllib3

try:
    import joblib
except ImportError:
    joblib = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from pymongo import MongoClient, UpdateOne
except ImportError:
    MongoClient = None
    UpdateOne = None

banks_dir = os.path.join(root_dir, "banks")
if banks_dir not in sys.path:
    sys.path.insert(0, banks_dir)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from banks.agrobank import Agrobank
from banks.aloqabank import AloqaBank
from banks.anorbank import AnorBank
from banks.apexbank import ApexBank
from banks.asakabank import AsakaBank
from banks.asiaalliancebank import AsiaAllianceBank
from banks.brb import BRB
from banks.cbu import CBU
from banks.cbu_gold import CbuGold
from banks.davrbank import DavrBank
from banks.garantbank import GarantBank
from banks.hamkorbank import HamkorBank
from banks.hayotbank import HayotBank
from banks.infinbank import InfinBank
from banks.ipakyulibank import IpakYuliBank
from banks.ipotekabank import IpotekaBank
from banks.kapitalbank import KapitalBank
from banks.mikrokreditbank import MikroKreditBank
from banks.nbu import NBU
from banks.octobank import OctoBank
from banks.orientfinansbank import OrientFinansBank
from banks.poytaxtbank import PoytaxtBank
from banks.sqb import SQB
from banks.tbcbank import TBCBank
from banks.tengebank import TengeBank
from banks.trustbank import TrustBank
from banks.turonbank import TuronBank
from banks.universalbank import UniversalBank
from banks.xalqbank import XalqBank


MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://dubrovskayaamaliya_db_user:3Sbu5zoJLEb7gDoI@zoloto.wkualrv.mongodb.net/?appName=Zoloto",
)
MONGO_DB_NAME = "banks_data"
MONGO_COLLECTION_NAME = "currency_rates"
MONGO_GOLD_COLLECTION_NAME = "gold_rates"
MONGO_PREDICTIONS_COLLECTION_NAME = "predictions"
PREDICTION_DIRECTORIES = [
    os.path.join(root_dir, "predict"),
    os.path.join(root_dir, "prediction"),
]
PREDICTION_MODEL_CANDIDATES = {
    "USD": [
        "usd_model.pkl",
        "usd_mode.pkl",
        "linear_regression_usd_with_features.pkl",
    ],
    "EUR": [
        "eur_model.pkl",
        "best_eur_model_with_features.pkl",
    ],
}
DEFAULT_MODEL_FEATURES = ["lag1", "lag2", "day_of_week", "month", "day_of_month"]
MODEL_BANK_NAME = "CBU"


def build_banks():
    return [
        Agrobank(),
        AloqaBank(),
        AnorBank(),
        ApexBank(),
        AsakaBank(),
        AsiaAllianceBank(),
        BRB(),
        CBU(),
        DavrBank(),
        GarantBank(),
        HamkorBank(),
        HayotBank(),
        InfinBank(),
        IpakYuliBank(),
        IpotekaBank(),
        KapitalBank(),
        MikroKreditBank(),
        NBU(),
        OctoBank(),
        OrientFinansBank(),
        PoytaxtBank(),
        SQB(),
        TBCBank(),
        TengeBank(),
        TrustBank(),
        TuronBank(),
        UniversalBank(),
        XalqBank(),
    ]


def build_report_path():
    return os.path.join(root_dir, "currency_rates.json")


def load_report(file_path=None):
    file_path = file_path or build_report_path()
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_report(report):
    file_path = build_report_path()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    return file_path


def extract_numeric_rate(rate_info):
    if not isinstance(rate_info, dict):
        raise ValueError("Данные по курсу должны быть словарем")

    for field_name in ("rate", "buy", "sell"):
        value = rate_info.get(field_name)
        if isinstance(value, (int, float)):
            return float(value)

    raise ValueError("Не найдено числовое значение курса")


def extract_report_rate(report, bank_name, currency_code):
    banks_data = report.get("banks") or {}
    bank_data = banks_data.get(bank_name) or {}
    currency_data = bank_data.get(currency_code)

    if not currency_data:
        raise ValueError(f"В final_report нет данных {bank_name}/{currency_code}")

    return extract_numeric_rate(currency_data)


def find_prediction_model_path(currency_code):
    for directory in PREDICTION_DIRECTORIES:
        for file_name in PREDICTION_MODEL_CANDIDATES.get(currency_code, []):
            candidate_path = os.path.join(directory, file_name)
            if os.path.exists(candidate_path):
                return candidate_path

    raise FileNotFoundError(
        f"Файл модели для {currency_code} не найден. Проверены пути: "
        + ", ".join(
            os.path.join(directory, file_name)
            for directory in PREDICTION_DIRECTORIES
            for file_name in PREDICTION_MODEL_CANDIDATES.get(currency_code, [])
        )
    )


def load_prediction_model(model_path):
    if joblib is None:
        raise ImportError("Не установлен joblib")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Файл модели не найден: {model_path}")

    saved_obj = joblib.load(model_path)

    if hasattr(saved_obj, "predict"):
        feature_names = list(getattr(saved_obj, "feature_names_in_", [])) or DEFAULT_MODEL_FEATURES
        return saved_obj, feature_names, type(saved_obj).__name__

    if isinstance(saved_obj, dict) and "model" in saved_obj:
        model = saved_obj["model"]
        feature_names = list(
            saved_obj.get("features")
            or getattr(model, "feature_names_in_", [])
            or DEFAULT_MODEL_FEATURES
        )
        model_name = saved_obj.get("model_name") or type(model).__name__
        return model, feature_names, model_name

    raise ValueError("Не удалось извлечь модель из pkl-файла")


def build_date_only(timestamp):
    try:
        return datetime.fromisoformat(timestamp).date().isoformat()
    except (TypeError, ValueError):
        return datetime.now().date().isoformat()


def build_prediction_feature_values(current_rate, previous_rate, predicted_dt):
    ratio = current_rate / previous_rate if previous_rate else 1.0

    return {
        "lag1": current_rate,
        "lag2": previous_rate,
        "diff_lag1_lag2": current_rate - previous_rate,
        "ratio_lag1_lag2": ratio,
        "mean_lag1_lag2": (current_rate + previous_rate) / 2,
        "day_of_week": predicted_dt.weekday(),
        "month": predicted_dt.month,
        "day_of_month": predicted_dt.day,
        "dow_sin": math.sin(2 * math.pi * predicted_dt.weekday() / 7),
        "dow_cos": math.cos(2 * math.pi * predicted_dt.weekday() / 7),
        "month_sin": math.sin(2 * math.pi * predicted_dt.month / 12),
        "month_cos": math.cos(2 * math.pi * predicted_dt.month / 12),
    }


def build_prediction_payload(final_report, bank_name, currency_code, previous_report=None):
    current_rate = extract_report_rate(final_report, bank_name, currency_code)

    previous_rate = current_rate
    if previous_report:
        try:
            previous_rate = extract_report_rate(previous_report, bank_name, currency_code)
        except ValueError:
            previous_rate = current_rate

    base_timestamp = final_report.get("timestamp") or datetime.now().isoformat()
    base_dt = datetime.fromisoformat(base_timestamp)
    predicted_dt = base_dt + timedelta(days=1)
    feature_values = build_prediction_feature_values(current_rate, previous_rate, predicted_dt)
    return predicted_dt, feature_values


def build_model_input(feature_names, feature_values):
    ordered_features = {
        feature_name: feature_values[feature_name]
        for feature_name in feature_names
    }

    if pd is not None:
        return pd.DataFrame([ordered_features], columns=feature_names)

    return [[ordered_features[feature_name] for feature_name in feature_names]]


def add_prediction_for_currency(report, bank_name, currency_code, previous_report=None, verbose=True):
    try:
        model_path = find_prediction_model_path(currency_code)
        model, feature_names, model_name = load_prediction_model(model_path)
        predicted_dt, feature_values = build_prediction_payload(
            final_report=report,
            bank_name=bank_name,
            currency_code=currency_code,
            previous_report=previous_report,
        )

        missing_features = [
            feature_name
            for feature_name in feature_names
            if feature_name not in feature_values
        ]
        if missing_features:
            raise ValueError(
                "В модели есть неподдерживаемые признаки: "
                + ", ".join(missing_features)
            )

        model_input = build_model_input(feature_names, feature_values)
        predicted_rate = float(model.predict(model_input)[0])

        report.setdefault("predictions", {})
        report["predictions"].setdefault(bank_name, {})
        report["predictions"][bank_name][currency_code] = {
            "predicted_for_date": predicted_dt.date().isoformat(),
            "predicted_rate": round(predicted_rate, 4),
            "model": model_name,
            "model_path": model_path,
            "features_used": {
                feature_name: feature_values[feature_name]
                for feature_name in feature_names
            },
        }

        if verbose:
            print(f"[+] Прогноз для {bank_name}/{currency_code} успешно добавлен в final_report")
    except Exception as e:
        if verbose:
            print(f"[-] Не удалось добавить прогноз для {bank_name}/{currency_code}: {e}")

    return report


def add_predictions_to_report(report, previous_report=None, verbose=True):
    for currency_code in sorted(PREDICTION_MODEL_CANDIDATES):
        report = add_prediction_for_currency(
            report,
            bank_name=MODEL_BANK_NAME,
            currency_code=currency_code,
            previous_report=previous_report,
            verbose=verbose,
        )

    return report


def add_predictions_to_saved_report(file_path, previous_report=None, verbose=True):
    report = load_report(file_path)
    if report is None:
        raise ValueError(f"Не удалось загрузить JSON-отчет: {file_path}")

    updated_report = add_predictions_to_report(
        report,
        previous_report=previous_report,
        verbose=verbose,
    )
    save_report(updated_report)
    return updated_report


def send_to_mongo(report, verbose=True):
    if MongoClient is None or UpdateOne is None:
        if verbose:
            print("[-] Отправка в MongoDB пропущена: не установлен pymongo")
        return {
            "banks": {"status": "skipped", "reason": "pymongo_missing"},
            "gold": {"status": "skipped", "reason": "pymongo_missing"},
            "predictions": {"status": "skipped", "reason": "pymongo_missing"},
        }

    timestamp = report.get("currency_updated_at") or report.get("timestamp") or datetime.now().isoformat()
    date_only = build_date_only(timestamp)
    client = None

    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        summary = {
            "banks": {"status": "skipped", "reason": "no_data"},
            "gold": {"status": "skipped", "reason": "no_data"},
            "predictions": {"status": "skipped", "reason": "no_data"},
        }

        bank_operations = []
        for bank_name, currencies in (report.get("banks") or {}).items():
            for currency, rates in currencies.items():
                buy = rates.get("buy") if isinstance(rates, dict) else None
                sell = rates.get("sell") if isinstance(rates, dict) else None
                spread = (
                    sell - buy
                    if isinstance(buy, (int, float)) and isinstance(sell, (int, float))
                    else None
                )

                doc = {
                    "timestamp": timestamp,
                    "date_only": date_only,
                    "bank_name": bank_name,
                    "currency": currency,
                    "buy": buy,
                    "sell": sell,
                    "spread": spread,
                    "loaded_at": datetime.now(timezone.utc),
                }

                if isinstance(rates, dict):
                    for key, value in rates.items():
                        if key not in {"buy", "sell"}:
                            doc[key] = value

                bank_operations.append(
                    UpdateOne(
                        {
                            "date_only": date_only,
                            "bank_name": bank_name,
                            "currency": currency,
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                )

        if bank_operations:
            result = db[MONGO_COLLECTION_NAME].bulk_write(bank_operations, ordered=False)
            summary["banks"] = {
                "status": "success",
                "inserted": result.upserted_count,
                "updated": result.modified_count,
            }
        elif verbose:
            print("[-] MongoDB banks: отправка пропущена, нет данных по валютам")

        gold_operations = []
        for weight, gold_rates in (report.get("gold") or {}).items():
            doc = {
                "timestamp": timestamp,
                "date_only": date_only,
                "weight": weight,
                "loaded_at": datetime.now(timezone.utc),
            }

            if isinstance(gold_rates, dict):
                doc.update(gold_rates)

            gold_operations.append(
                UpdateOne(
                    {
                        "date_only": date_only,
                        "weight": weight,
                    },
                    {"$set": doc},
                    upsert=True,
                )
            )

        if gold_operations:
            result = db[MONGO_GOLD_COLLECTION_NAME].bulk_write(gold_operations, ordered=False)
            summary["gold"] = {
                "status": "success",
                "inserted": result.upserted_count,
                "updated": result.modified_count,
            }
        elif verbose:
            print("[-] MongoDB gold: отправка пропущена, нет данных по золоту")

        prediction_operations = []
        for bank_name, currencies in (report.get("predictions") or {}).items():
            for currency, prediction in currencies.items():
                doc = {
                    "timestamp": timestamp,
                    "date_only": date_only,
                    "bank_name": bank_name,
                    "currency": currency,
                    "loaded_at": datetime.now(timezone.utc),
                }

                if isinstance(prediction, dict):
                    doc.update(prediction)

                prediction_operations.append(
                    UpdateOne(
                        {
                            "date_only": date_only,
                            "bank_name": bank_name,
                            "currency": currency,
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                )

        if prediction_operations:
            result = db[MONGO_PREDICTIONS_COLLECTION_NAME].bulk_write(
                prediction_operations,
                ordered=False,
            )
            summary["predictions"] = {
                "status": "success",
                "inserted": result.upserted_count,
                "updated": result.modified_count,
            }
        elif verbose:
            print("[-] MongoDB predictions: отправка пропущена, нет данных по предикту")

        if verbose:
            for section_name, section_summary in summary.items():
                if section_summary["status"] == "success":
                    print(
                        f"[MongoDB][{section_name}] inserted: {section_summary['inserted']}, "
                        f"updated: {section_summary['updated']}"
                    )

        return summary
    except Exception as e:
        if verbose:
            print(f"[-] Ошибка при отправке в MongoDB: {e}")
        return {
            "banks": {"status": "error", "reason": str(e)},
            "gold": {"status": "error", "reason": str(e)},
            "predictions": {"status": "error", "reason": str(e)},
        }
    finally:
        if client is not None:
            client.close()


def refresh_report(include_gold=True, verbose=True):
    previous_report = load_report()
    banks = build_banks()
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "banks": {},
        "gold": {},
        "predictions": {},
    }

    for bank in banks:
        if verbose:
            print(f"Получаю данные из {bank.bank_name}...")

        try:
            raw_data = bank.fetch_data()
            parsed_rates = bank.parse(raw_data)

            if parsed_rates:
                final_report["banks"][bank.bank_name] = parsed_rates
                if verbose:
                    print(f"Успешно: {parsed_rates}")
            elif verbose:
                print(f"Не удалось обработать данные для {bank.bank_name}")
        except Exception as e:
            if verbose:
                print(f"[-] Ошибка в {bank.bank_name}: {e}")

    if final_report["banks"]:
        final_report["currency_updated_at"] = final_report["timestamp"]

    if include_gold:
        gold = CbuGold()
        if verbose:
            print(f"Получаю данные из {gold.bank_name}...")

        try:
            raw_gold_data = gold.fetch_data()
            parsed_gold = gold.parse(raw_gold_data)
            if parsed_gold:
                final_report["gold"] = parsed_gold
                if verbose:
                    print(f"Успешно: {parsed_gold}")
            elif verbose:
                print(f"Не удалось обработать данные для {gold.bank_name}")
        except Exception as e:
            if verbose:
                print(f"[-] Ошибка в {gold.bank_name}: {e}")

        if final_report["gold"]:
            final_report["gold_updated_at"] = final_report["timestamp"]

    file_path = save_report(final_report)
    return add_predictions_to_saved_report(
        file_path,
        previous_report=previous_report,
        verbose=verbose,
    )


def main():
    report = refresh_report(include_gold=True, verbose=True)
    file_path = build_report_path()

    print(f"\n[+] Готово! Банки обработаны: {len(report['banks'])}.")
    if report.get("gold"):
        print(f"[+] Данные по золоту сохранены: {len(report['gold'])} весов.")
    print(f"Результат здесь: {file_path}")

    print("\nОтправляю данные в MongoDB...")
    mongo_summary = send_to_mongo(report, verbose=True)

    successful_sections = [
        section_name
        for section_name, section_summary in mongo_summary.items()
        if section_summary.get("status") == "success"
    ]
    failed_sections = [
        section_name
        for section_name, section_summary in mongo_summary.items()
        if section_summary.get("status") == "error"
    ]

    if failed_sections:
        print(f"[-] Ошибка отправки в MongoDB для: {', '.join(failed_sections)}")
    elif successful_sections:
        print(f"Готово: в MongoDB отправлены разделы: {', '.join(successful_sections)}")
    else:
        print("[-] Данные не были отправлены в MongoDB")


if __name__ == "__main__":
    main()
