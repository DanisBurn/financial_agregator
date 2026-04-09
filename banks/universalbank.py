from BaseBank import BaseBankScraper


class UniversalBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "UniversalBank"
        self.main_url = "https://universalbank.uz/ru/currency"
        self.api_url = "https://universalbank.uz/api/currencies/daily"
        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            response = self.session.get(self.api_url, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def _to_float(self, value):
        return float(str(value).replace(",", "."))

    def parse(self, data):
        if not data or not isinstance(data, dict):
            return None

        items = data.get("items")
        if not isinstance(items, list):
            return None

        code_map = {
            "840": "USD",
            "978": "EUR",
            "643": "RUB",
        }

        results = {}
        for numeric_code, code in code_map.items():
            item = next(
                (entry for entry in items if str(entry.get("code", "")) == numeric_code),
                None,
            )
            if not item:
                continue

            try:
                results[code] = {
                    "buy": self._to_float(item.get("buyingRate", 0)),
                    "sell": self._to_float(item.get("sellingRate", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = UniversalBank()
    data = bank.parse(bank.fetch_data())
    print(data)
