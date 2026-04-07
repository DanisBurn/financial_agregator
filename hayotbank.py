from BaseBank import BaseBankScraper

class HayotBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Hayot Bank"
        self.main_url = 'https://hayotbank.uz/main/exchange-rate'
        self.api_url = 'https://api.hayotbank.uz/api/curr-exchange-rate/get-all?size=2000&search=currExchangeRate.active=true'

    def parse(self, data):
        if not data or 'data' not in data:
            return None

        results = {}
        target_codes = ['USD', 'EUR', 'RUB']

        for item in data['data']:
            try:
                title_ru = item.get('currency', {}).get('title', {}).get('ru', '').upper()
                for code in target_codes:
                    if code in title_ru:
                        results[code] = {
                            "buy": float(item.get('buy', 0)),
                            "sell": float(item.get('sell', 0))
                        }
            except (ValueError, AttributeError, TypeError):
                continue
                
        return results if results else None