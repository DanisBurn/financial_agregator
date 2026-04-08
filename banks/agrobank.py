from BaseBank import BaseBankScraper


class Agrobank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Agrobank"
        self.main_url = "https://agrobank.uz/ru/person/exchange_rates"
        self.api_url = "https://agrobank.uz/api/v1/?action=pages&code=ru/person/exchange_rates"
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

    def _extract_office_items(self, data):
        sections = data.get("data", {}).get("sections", [])

        for section in sections:
            blocks = section.get("blocks", [])
            if not isinstance(blocks, list):
                continue

            current_tab_code = None

            for block in blocks:
                block_type = block.get("type")
                content = block.get("content", {})

                if block_type == "tab":
                    current_tab_code = content.get("code")
                    continue

                if block_type == "currency-rates" and current_tab_code == "office":
                    items = content.get("items", [])
                    if isinstance(items, list):
                        return items

        return []

    def parse(self, data):
        if not data or not isinstance(data, dict):
            return None

        items = self._extract_office_items(data)
        if not items:
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")
        items_by_code = {}

        for item in items:
            code = str(item.get("alpha3", "")).upper()
            if code in target_codes:
                items_by_code[code] = item

        for code in target_codes:
            item = items_by_code.get(code)
            if not item:
                continue

            try:
                results[code] = {
                    "buy": float(item.get("buy", 0)),
                    "sell": float(item.get("sale", 0)),
                }
            except (TypeError, ValueError):
                continue

        return results or None


if __name__ == "__main__":
    bank = Agrobank()
    data = bank.parse(bank.fetch_data())
    print(data)
