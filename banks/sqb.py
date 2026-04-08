from BaseBank import BaseBankScraper

class SQB(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "SQB"
        self.main_url = "https://sqb.uz/individuals/exchange-money/"
        self.api_url = "https://sqb.uz/api/site-kurs-api/"
        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=20)

            response = self.session.get(self.api_url, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def _to_float(self, value):
        return float(str(value).replace(",", ".").strip())

    def _normalize_price(self, value):
        amount = self._to_float(value)
        return amount / 100

    def parse(self, data):
        if not data or not isinstance(data, dict):
            return None

        payload = data.get("data")
        if not isinstance(payload, dict):
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")
        items = payload.get("offline", [])
        if not isinstance(items, list):
            return None

        items_by_code = {}
        for item in items:
            code = str(item.get("code", "")).upper()
            if code not in target_codes:
                continue

            items_by_code[code] = item

        for code in target_codes:
            item = items_by_code.get(code)
            if not item:
                continue

            try:
                results[code] = {
                    "buy": self._normalize_price(item.get("buy", 0)),
                    "sell": self._normalize_price(item.get("sell", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = SQB()
    data = bank.parse(bank.fetch_data())
    print(data)
