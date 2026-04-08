import re
from bs4 import BeautifulSoup
from BaseBank import BaseBankScraper

class ApexBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Apex Bank"
        self.main_url = 'https://www.apexbank.uz/en/about/exchange-rates/'
        self.api_url = self.main_url
        if 'X-Requested-With' in self.session.headers:
            del self.session.headers['X-Requested-With']

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

        for code in target_codes:
            tables = soup.find_all('table')
            
            for table in tables:
                container = table.find_parent('section') or table.find_parent('div', class_='col-12') or table.parent.parent
                if container and code in container.get_text(separator=' ').upper():
                    
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        rates = []
                        
                        for cell in cells:
                            span = cell.find('span')
                            raw_text = span.get_text(strip=True) if span else cell.get_text(strip=True)
                            
                            clean_text = re.sub(r'[^\d,.]', '', raw_text).replace(',', '.')
                            
                            if clean_text and any(c.isdigit() for c in clean_text):
                                try:
                                    rates.append(float(clean_text))
                                except ValueError:
                                    continue
                                    
                        if len(rates) >= 2:
                            results[code] = {
                                "buy": rates[0],
                                "sell": rates[1]
                            }
                            break
                            
                    if code in results:
                        break
                        
        return results if results else None