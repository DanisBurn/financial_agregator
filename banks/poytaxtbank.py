import re
from bs4 import BeautifulSoup
from BaseBank import BaseBankScraper
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PoytaxtBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Poytaxt Bank"
        self.main_url = 'https://poytaxtbank.uz/ru/services/exchange-rates/'
        self.api_url = self.main_url

    def fetch_data(self):
        try:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
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
        rows = soup.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                currency_text = cells[0].get_text(separator=' ', strip=True).upper()
                
                for code in target_codes:
                    if code in currency_text and code not in results:
                        
                        buy_text = cells[1].get_text(separator=' ', strip=True)
                        sell_text = cells[2].get_text(separator=' ', strip=True)
                        
                        try:
                            buy_clean = re.sub(r'[^\d,.]', '', buy_text).replace(',', '.')
                            sell_clean = re.sub(r'[^\d,.]', '', sell_text).replace(',', '.')
                            buy_val = float(buy_clean) if buy_clean else None
                            sell_val = float(sell_clean) if sell_clean else None
                            
                            if buy_val is not None or sell_val is not None:
                                results[code] = {
                                    "buy": buy_val,
                                    "sell": sell_val
                                }
                        except ValueError:
                            continue
                            
        return results if results else None