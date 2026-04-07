import json
from datetime import datetime
from TengeBank import TengeBank
from KapitalBank import KapitalBank


def main():
    banks = [TengeBank(), KapitalBank()]

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