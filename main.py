import json
from datetime import datetime
from tengebank import TengeBank
from kapitalbank import KapitalBank
from orientfinansbank import OrientFinansBank
from cbu import Cbu
from hayotbank import HayotBank
from apexbank import ApexBank
from octobank import Octobank
from davrbank import DavrBank
from anorbank import Anorbank
from poytaxtbank import PoytaxtBank
from tbcbank import TBCBank


def main():
    banks = [TengeBank(), KapitalBank(), OrientFinansBank(), HayotBank(), ApexBank(), Octobank(), DavrBank(), Anorbank(), PoytaxtBank(), TBCBank()]

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
