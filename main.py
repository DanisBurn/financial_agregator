import sys
import os
import json
import urllib3
from datetime import datetime

# 1. Настройка путей
# Получаем путь к папке financial_agregator (где лежит этот main.py)
root_dir = os.path.dirname(os.path.abspath(__file__))

# Добавляем папку 'banks' в пути поиска Python. 
# Это НУЖНО, чтобы cbu.py и другие могли написать "from BaseBank import..."
banks_dir = os.path.join(root_dir, "banks")
if banks_dir not in sys.path:
    sys.path.insert(0, banks_dir)

# 2. Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 3. Импортируем банки
# Теперь мы пишем "from banks.имя_файла", так как папка banks — это пакет
try:
    from banks.cbu import CBU
    from banks.nbu import NBU
    from banks.sqb import SQB
    from banks.agrobank import Agrobank
    from banks.xb import XB
    from banks.garantbank import GarantBank
    from banks.brb import BRB
    from banks.turonbank import TuronBank
    from banks.hamkorbank import HamkorBank
    from banks.asakabank import AsakaBank
    from banks.ipakyulibank import IpakYuliBank
    from banks.kapitalbank import KapitalBank
    from banks.orientfinansbank import OrientFinansBank
    from banks.tengebank import TengeBank
    from banks.hayotbank import HayotBank
    from banks.apexbank import ApexBank
    from banks.octobank import OctoBank
    from banks.davrbank import DavrBank
    from banks.anorbank import AnorBank
    from banks.poytaxtbank import PoytaxtBank
    from banks.tbcbank import TBCBank
except ImportError as e:
    print(f"\n[!] Ошибка импорта: {e}")
    sys.exit(1)

def main():
    banks = [
        CBU(), NBU(), SQB(), Agrobank(), XB(), GarantBank(), 
        BRB(), TuronBank(), HamkorBank(), AsakaBank(), 
        IpakYuliBank(), KapitalBank(), OrientFinansBank(), 
        TengeBank(), HayotBank(), ApexBank(), OctoBank(), 
        DavrBank(), AnorBank(), PoytaxtBank(), TBCBank()
    ]

    final_report = {
        "timestamp": datetime.now().isoformat(),
        "banks": {}
    }

    for bank in banks:
        print(f"Получаю данные из {bank.bank_name}...")
        try:
            raw_data = bank.fetch_data()
            parsed_rates = bank.parse(raw_data)
            
            if parsed_rates:
                final_report["banks"][bank.bank_name] = parsed_rates
                print(f"Успешно: {parsed_rates}")
            else:
                print(f"Не удалось обработать данные для {bank.bank_name}")
        except Exception as e:
            print(f"[-] Ошибка в {bank.bank_name}: {e}")

    # Сохраняем файл в корень (рядом с main.py)
    file_path = os.path.join(root_dir, "currency_rates.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=4)
    
    print(f"\n[+] Готово! Все 21 банк обработаны.")
    print(f"Результат здесь: {file_path}")

if __name__ == "__main__":
    main()