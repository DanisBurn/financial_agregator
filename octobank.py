import json
from bs4 import BeautifulSoup
import urllib3
from BaseBank import BaseBankScraper

class Octobank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Octobank"
        self.main_url = 'https://octobank.uz/en/interactive-services/kurs-valyut'
        self.api_url = self.main_url

    def fetch_data(self):
        try:
            response = self.session.get(self.api_url, timeout=10, verify=False)
            response.raise_for_status()
            return response.text 
        except Exception as e:
            print(f"[-] Ошибка загрузки {self.bank_name}: {e}")
            return None

    def parse(self, html):
        if not html: return None
        
        soup = BeautifulSoup(html, 'html.parser')
        results = {}
        target_codes = ['USD', 'EUR', 'RUB']
        rates_div = soup.find('div', id='currency-rates')
        if not rates_div or not rates_div.has_attr('data-rates'):
            print("[-] Octobank: Блок data-rates не найден на странице")
            return None

        try:
            raw_json_string = rates_div['data-rates']
            rates_data = json.loads(raw_json_string)
            
            for code in target_codes:
                if code in rates_data:
                    buy = rates_data[code].get('buy')
                    sell = rates_data[code].get('sell')
                    
                    if buy and sell:
                        results[code] = {
                            "buy": float(buy),
                            "sell": float(sell)
                        }
                        
        except json.JSONDecodeError as e:
            print(f"[-] Octobank: Банк сломал структуру JSON внутри атрибута: {e}")
        except (ValueError, TypeError) as e:
            print(f"[-] Octobank: Ошибка конвертации чисел: {e}")
            
        return results if results else None