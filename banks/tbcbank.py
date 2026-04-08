import re
from bs4 import BeautifulSoup
import urllib3
from BaseBank import BaseBankScraper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TBCBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "TBC Bank"
        self.main_url = 'https://tbcbank.uz/ru/currencies/'
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
        
        results = {}
        target_codes = ['USD', 'EUR']
        for code in target_codes:
            match = re.search(fr'"{code}"\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)', html)
            if match:
                results[code] = {
                    "buy": float(match.group(1)),
                    "sell": float(match.group(2))
                }
        if len(results) == len(target_codes):
            return results
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 5:
                text = row.get_text(separator=' ', strip=True).upper()
                
                for code in target_codes:
                    if code in text and code not in results:
                        sell_text = cells[3].get_text(strip=True)
                        buy_text = cells[4].get_text(strip=True)
                        
                        try:
                            buy_clean = re.sub(r'[^\d,.]', '', buy_text).replace(',', '.')
                            sell_clean = re.sub(r'[^\d,.]', '', sell_text).replace(',', '.')
                            
                            results[code] = {
                                "buy": float(buy_clean),
                                "sell": float(sell_clean)
                            }
                        except ValueError:
                            pass
                            
        return results if results else None