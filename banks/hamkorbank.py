from BaseBank import BaseBankScraper


class HamkorBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "HamkorBank"
        self.main_url = "https://hamkorbank.uz/exchange-rate/"
        self.api_url = "https://api-dbo.hamkorbank.uz/webflow/v1/exchanges"
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
            code = str(item.get("currency_char", "")).upper()
            destination_code = str(item.get("destination_code", ""))
            begin_sum_i = item.get("begin_sum_i", 0)

            if destination_code != "2" or code not in target_codes:
                continue

            current_item = items_by_code.get(code)
            if current_item is None or begin_sum_i < current_item.get("begin_sum_i", 0):
                items_by_code[code] = item

        for code in target_codes:
            item = items_by_code.get(code)
            if not item:
                continue

            try:
                results[code] = {
                    "buy": self._normalize_rate(item.get("buying_rate", 0)),
                    "sell": self._normalize_rate(item.get("selling_rate", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = HamkorBank()
    data = bank.parse(bank.fetch_data())
    print(data)
