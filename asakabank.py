from BaseBank import BaseBankScraper
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AsakaBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "AsakaBank"
        self.main_url = "https://asakabank.uz/ru/physical-persons/home"
        self.api_url = "https://back.asakabank.uz/core/v1/currency-list/"
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
            "Origin": "https://asakabank.uz",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=20, verify=False)
            response = self.session.get(
                self.api_url,
                params={"page_size": 100},
                timeout=20,
                verify=False
            )
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

        items = data.get("results")
        if not isinstance(items, list):
            return None

        target_codes = ("USD", "EUR", "RUB")
        results = {}

        for code in target_codes:
            item = next(
                (
                    entry for entry in items
                    if str(entry.get("short_name", "")).upper() == code
                    and entry.get("currency_type") == 1
                ),
                None,
            )
            if not item:
                continue

            try:
                results[code] = {
                    "buy": self._to_float(item.get("purchase", 0)),
                    "sell": self._to_float(item.get("sale", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = AsakaBank()
    data = bank.parse(bank.fetch_data())
    print(data)
