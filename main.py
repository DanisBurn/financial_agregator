import json
import os
import sys
from datetime import datetime

import urllib3


root_dir = os.path.dirname(os.path.abspath(__file__))

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


def build_banks():
    return [
       Agrobank(), AloqaBank(), AnorBank(), ApexBank(), AsakaBank(),
       AsiaAllianceBank(), BRB(), CBU(), DavrBank(), GarantBank(), 
       HamkorBank(), HayotBank(), InfinBank(), IpakYuliBank(), 
       IpotekaBank(), KapitalBank(), MikroKreditBank(), NBU(),
       OctoBank(), OrientFinansBank(), PoytaxtBank(), SQB(),
       TBCBank(), TengeBank(), TrustBank(), TuronBank(),
       UniversalBank(), XalqBank(),
    ]


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


def save_report(report):
    file_path = build_report_path()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    return file_path


def refresh_report(include_gold=True, verbose=True):
    banks = build_banks()
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "banks": {},
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

    save_report(final_report)
    return final_report


def main():
    report = refresh_report(include_gold=True, verbose=True)
    file_path = build_report_path()
    print(f"\n[+] Готово! Банки обработаны: {len(report['banks'])}.")
    if report.get("gold"):
        print(f"[+] Данные по золоту сохранены: {len(report['gold'])} весов.")
    print(f"Результат здесь: {file_path}")


if __name__ == "__main__":
    main()
