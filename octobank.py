import re
from bs4 import BeautifulSoup
import urllib3
from BaseBank import BaseBankScraper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OctoBank(BaseBankScraper):
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
            return None

        raw_string = rates_div['data-rates']
        
        for code in target_codes:
            match = re.search(fr'["\']?{code}["\']?\s*:\s*\{{\s*["\']?buy["\']?\s*:\s*([\d.]+)\s*,\s*["\']?sell["\']?\s*:\s*([\d.]+)', raw_string)
            
            if match:
                try:
                    results[code] = {
                        "buy": float(match.group(1)),
                        "sell": float(match.group(2))
                    }
                except ValueError:
                    continue
                    
        return results if results else None