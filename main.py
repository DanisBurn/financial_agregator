import json
from datetime import datetime
from cbu import CBU
from nbu import NBU
from sqb import SQB
from agrobank import Agrobank
from xb import XB
from garantbank import GarantBank
from brb import BRB
from turonbank import TuronBank
from hamkorbank import HamkorBank
from asakabank import AsakaBank
from ipakyulibank import IpakYuliBank
from KapitalBank import KapitalBank
from orientfinansbank import OrientFinansBank
from TengeBank import TengeBank
from hayotbank import HayotBank
from apexbank import ApexBank
from octobank import OctoBank
from davrbank import DavrBank
from anorbank import AnorBank
from poytaxtbank import PoytaxtBank
from tbcbank import TBCBank

def main():
    banks = [
        CBU(),
        NBU(), 
        SQB(), 
        Agrobank(), 
        XB(), 
        GarantBank(), 
        BRB(), 
        TuronBank(), 
        HamkorBank(), 
        AsakaBank(), 
        IpakYuliBank(), 
        KapitalBank(),
        OrientFinansBank(), 
        TengeBank(),
        HayotBank(),
        ApexBank(),
        OctoBank(),
        DavrBank(),
        AnorBank(),
        PoytaxtBank(),
        TBCBank(),
        ]

    final_report = {
        "timestamp": datetime.now().isoformat(),
        "banks": {}
    }

    for bank in banks:
        print(f"Получаю данные из {bank.bank_name}...")
        raw_data = bank.fetch_data()
        parsed_rates = bank.parse(raw_data)
        
        if parsed_rates:
            final_report["banks"][bank.bank_name] = parsed_rates
            print(f"Успешно: {parsed_rates}")
        else:
            print(f"Не удалось обработать данные для {bank.bank_name}")

    file_name = "currency_rates.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=4)
    
    print(f"\nДанные сохранены в файл: {file_name}")

if __name__ == "__main__":
    main()
