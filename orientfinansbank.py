from BaseBank import BaseBankScraper
from bs4 import BeautifulSoup
import re

class OrientFinansBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Orient Finans Bank"
        self.main_url = 'https://ofb.uz/ru/kursy-valyut'
        self.api_url = self.main_url

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=10)
            response = self.session.get(self.api_url, timeout=10)
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

        table = soup.find('table')
        if not table:
            print("[-] Таблица не найдена в HTML коде OFB")
            return None

        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
                
            currency_text = cells[0].get_text(strip=True).upper()
            
            for code in target_codes:
                if code in currency_text:
                    raw_buy = cells[1].get_text(strip=True)
                    raw_sell = cells[2].get_text(strip=True)
                    
                    try:
                        clean_buy = raw_buy.replace(',', '.')
                        clean_sell = raw_sell.replace(',', '.')
                        
                        buy = re.sub(r'[^\d.]', '', clean_buy)
                        sell = re.sub(r'[^\d.]', '', clean_sell)
                        
                        results[code] = {
                            "buy": float(buy),
                            "sell": float(sell)
                        }
                    except ValueError:
                        print(f"[-] OFB: Ошибка числа для {code} (покупка: '{raw_buy}', продажа: '{raw_sell}')")
                        continue
                        
        return results if results else None