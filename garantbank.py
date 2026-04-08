import re
from BaseBank import BaseBankScraper


class GarantBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Garant Bank"
        self.main_url = "https://garantbank.uz/ru/exchange-rates"
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
        cleaned = str(value).replace("\xa0", " ").replace(" ", "").replace(",", ".").strip()
        return float(cleaned)

    def _extract_row(self, html, code):
        pattern = re.compile(
            rf'<tr>\s*<td><span class="exchange-currency">\s*{re.escape(code)}\s*</span></td>(.*?)</tr>',
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(html)
        if not match:
            return None
        return match.group(1)

    def _extract_cash_values(self, row_html):
        values = re.findall(
            r'<div class="exchange-row">\s*'
            r'<span class="exchange-purchase">\s*([^<]*)\s*</span>\s*'
            r'<span class="exchange-sale">\s*([^<]*)\s*</span>\s*'
            r'</div>',
            row_html,
            re.IGNORECASE | re.DOTALL,
        )
        if not values:
            return None
        return values[0]

    def parse(self, html):
        if not html:
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")

        for code in target_codes:
            row_html = self._extract_row(html, code)
            if not row_html:
                continue

            cash_values = self._extract_cash_values(row_html)
            if not cash_values:
                continue

            buy_raw, sell_raw = cash_values
            if not buy_raw.strip() or not sell_raw.strip():
                continue

            try:
                results[code] = {
                    "buy": self._to_float(buy_raw),
                    "sell": self._to_float(sell_raw),
                }
            except ValueError:
                continue

        return results or None


if __name__ == "__main__":
    bank = GarantBank()
    data = bank.parse(bank.fetch_data())
    print(data)
