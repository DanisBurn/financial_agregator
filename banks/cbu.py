from BaseBank import BaseBankScraper

class CBU(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "CBU"
        self.main_url = "https://cbu.uz/ru/"
        self.api_url = "https://cbu.uz/ru/arkhiv-kursov-valyut/json/"
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

    def _normalize_rate(self, item):
        rate = self._to_float(item.get("Rate", 0))
        nominal = self._to_float(item.get("Nominal", 1))
        if nominal <= 0:
            raise ValueError("Некорректный nominal")
        return rate / nominal

    def parse(self, data):
        if not data:
            return None

        results = {}
        target_codes = {"USD", "EUR", "RUB"}

        for item in data:
            code = str(item.get("Ccy", "")).upper()
            if code not in target_codes or code in results:
                continue

            try:
                rate = self._normalize_rate(item)
            except (TypeError, ValueError):
                continue

            results[code] = {
                "buy": rate,
                "sell": rate,
            }

        return results or None


if __name__ == "__main__":
    bank = CBU()
    data = bank.parse(bank.fetch_data())
    print(data)
