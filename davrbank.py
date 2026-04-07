from bs4 import BeautifulSoup
import re
from BaseBank import BaseBankScraper

class DavrBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Davr Bank"
        self.main_url = 'https://davrbank.uz/ru/exchange-rate'
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
        currency_map = {
            'ДОЛЛАР': 'USD',
            'ЕВРО': 'EUR',
            'РУБЛ': 'RUB'
        }

        table = soup.find('table')
        if not table:
            print("[-] Davr Bank: Таблица не найдена в HTML")
            return None

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) < 4:
                continue
                
            currency_text = cells[0].get_text(separator=' ', strip=True).upper()
            
            for ru_name, code in currency_map.items():
                if ru_name in currency_text:
                    try:
                        sell_text = cells[2].get_text(strip=True)
                        buy_text = cells[3].get_text(strip=True)
                        
                        buy = re.sub(r'[^\d,.]', '', buy_text).replace(',', '.')
                        sell = re.sub(r'[^\d,.]', '', sell_text).replace(',', '.')
                        
                        results[code] = {
                            "buy": float(buy),
                            "sell": float(sell)
                        }
                    except (ValueError, IndexError):
                        continue
                        
        return results if results else None