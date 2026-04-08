from BaseBank import BaseBankScraper


class XB(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "XB"
        self.main_url = "https://xb.uz/page/valyuta-ayirboshlash"
        self.api_url = "https://xb.uz/api/v1/external/client/default"
        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=20)

            response = self.session.get(
                self.api_url,
                params={
                    "destination": 2,
                    "_f": "json",
                    "_l": "uz",
                },
                timeout=20,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def _to_float(self, value):
        return float(str(value).replace(" ", "").replace(",", ".").strip())

    def parse(self, data):
        if not data or not isinstance(data, list):
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")
        items_by_code = {}

        for item in data:
            code = str(item.get("title", "")).upper()
            if code in target_codes:
                items_by_code[code] = item

        for code in target_codes:
            item = items_by_code.get(code)
            if not item:
                continue

            try:
                results[code] = {
                    "buy": self._to_float(item.get("BUYING_RATE", 0)),
                    "sell": self._to_float(item.get("SELLING_RATE", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = XB()
    data = bank.parse(bank.fetch_data())
    print(data)
