import re
from bs4 import BeautifulSoup
from BaseBank import BaseBankScraper

class Anorbank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Anorbank"
        self.main_url = 'https://anorbank.uz/about/exchange-rates/'
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
        
        blocks = soup.find_all('div', class_='block-container')
        for block in blocks:
            name_div = block.find('div', class_=re.compile(r'block-0'))
            if name_div:
                name_text = name_div.get_text(strip=True).upper()
                if 'USD' in name_text and 'USD' not in results:
                    buy_div = block.find('div', class_=re.compile(r'block-1'))
                    sell_div = block.find('div', class_=re.compile(r'block-2'))
                    
                    if buy_div and sell_div:
                        try:
                            buy = re.sub(r'[^\d,.]', '', buy_div.get_text()).replace(',', '.')
                            sell = re.sub(r'[^\d,.]', '', sell_div.get_text()).replace(',', '.')
                            results['USD'] = {"buy": float(buy), "sell": float(sell)}
                        except ValueError:
                            pass

        table = soup.find('table', id='desktop_currencies_table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    name_text = cells[0].get_text(strip=True).upper()
                    
                    for code in ['EUR', 'RUB']:
                        if code in name_text and code not in results:
                            buy_text = cells[1].get_text(strip=True)
                            sell_text = cells[2].get_text(strip=True)
                            
                            try:
                                buy = re.sub(r'[^\d,.]', '', buy_text).replace(',', '.')
                                sell = re.sub(r'[^\d,.]', '', sell_text).replace(',', '.')
                                results[code] = {"buy": float(buy), "sell": float(sell)}
                            except ValueError:
                                pass
                                
        return results if results else None