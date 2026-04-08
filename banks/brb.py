from BaseBank import BaseBankScraper


class BRB(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "BRB"
        self.main_url = "https://brb.uz/ru/valyutalar-kursi"
        self.api_url = "https://brb.uz/api/currency/compare"
        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=20)

            response = self.session.get(
                self.api_url,
                params={"type": "jismoniy"},
                timeout=20,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def _normalize_rate(self, value):
        return float(value) / 100

    def parse(self, data):
        if not data or not isinstance(data, dict):
            return None

        items = data.get("data")
        if not isinstance(items, list):
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")
        items_by_code = {}

        for item in items:
            code = str(item.get("code", "")).upper()
            if code in target_codes:
                items_by_code[code] = item

        for code in target_codes:
            item = items_by_code.get(code)
            if not item:
                continue

            try:
                results[code] = {
                    "buy": self._normalize_rate(item.get("buy", 0)),
                    "sell": self._normalize_rate(item.get("sell", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = BRB()
    data = bank.parse(bank.fetch_data())
    print(data)
