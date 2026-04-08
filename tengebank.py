from BaseBank import BaseBankScraper

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