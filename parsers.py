import requests
import json
from abc import ABC, abstractmethod
from datetime import datetime
from bs4 import BeautifulSoup

class BaseBankScraper(ABC):
    def __init__(self):
        self.bank_name = "BaseBank"
        self.main_url = ""
        self.api_url = ""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        })

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=10)
            
            response = self.session.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    @abstractmethod
    def parse(self, data):
        pass

class TengeBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Tenge Bank"
        self.main_url = 'https://www.tengebank.uz/ru/exchange-rates'
        self.api_url = 'https://www.tengebank.uz/api/exchangerates/tables'
        
        self.session.headers.update({
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': self.main_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })

    def parse(self, data):
        if not data or 'personal' not in data:
            return None

        try:
            latest_entry = data['personal'][0]
            all_currencies = latest_entry.get('currency', {})
            
            target_codes = ['USD', 'EUR', 'RUB']
            results = {}

            for code in target_codes:
                if code in all_currencies:
                    results[code] = {
                        "buy": all_currencies[code].get('buy'),
                        "sell": all_currencies[code].get('sell')
                    }
            
            return results if results else None
            
        except (IndexError, KeyError) as e:
            print(f"[-] Ошибка структуры JSON: {e}")
            return None
        

class KapitalBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Kapital Bank"
        self.main_url = 'https://www.kapitalbank.uz/ru/services/exchange-rates/'
        self.api_url = self.main_url

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=10)
            
            response = self.session.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.text 
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def parse(self, html):
        if not html: return None
        
        soup = BeautifulSoup(html, 'html.parser')
        results = {}
        target_codes = ['USD', 'EUR', 'RUB']
        target_branch = "Ташкентский городской филиал АКБ Капиталбанк"

        rows = soup.find_all('tr', attrs={'data-id': '1'})
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4: continue
            
            branch_name = cells[1].get_text(strip=True)
            if target_branch not in branch_name:
                continue
                
            currency_code = cells[0].get_text(strip=True)
            
            if currency_code in target_codes:
                try:
                    buy = cells[2].get_text(strip=True)
                    sell = cells[3].get_text(strip=True)
                    
                    results[currency_code] = {
                        "buy": float(buy),
                        "sell": float(sell)
                    }
                except ValueError:
                    continue
                    
        return results if results else None

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
