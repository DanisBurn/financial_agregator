import re

from BaseBank import BaseBankScraper


class IpotekaBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "IpotekaBank"
        self.main_url = "https://www.ipotekabank.uz/ru/private/services/currency/"
        self.api_url = self.main_url
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            response = self.session.get(self.api_url, timeout=20)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def _to_float(self, value):
        cleaned = value.replace("\xa0", " ").replace(" ", "").replace(",", ".")
        cleaned = re.sub(r"[^0-9.]", "", cleaned)
        return float(cleaned)

    def _extract_office_block(self, html):
        match = re.search(
            r'<div[^>]+id="curr"[^>]*>(.*?)</div>\s*</div>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return match.group(1) if match else None

    def parse(self, html):
        if not html:
            return None

        office_block = self._extract_office_block(html)
        if not office_block:
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")

        for code in target_codes:
            match = re.search(
                rf'<div[^>]+id="{code}"[^>]+data-buy="([^"]+)"[^>]+data-sell="([^"]+)"',
                office_block,
                re.IGNORECASE,
            )
            if not match:
                continue

            try:
                results[code] = {
                    "buy": self._to_float(match.group(1)),
                    "sell": self._to_float(match.group(2)),
                }
            except ValueError:
                continue

        return results or None


if __name__ == "__main__":
    bank = IpotekaBank()
    data = bank.parse(bank.fetch_data())
    print(data)
