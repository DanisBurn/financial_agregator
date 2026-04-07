from BaseBank import BaseBankScraper

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