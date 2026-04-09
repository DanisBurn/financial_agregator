import re

from BaseBank import BaseBankScraper


class MikroKreditBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "MKBank"
        self.main_url = "https://mkbank.uz/ru/services/exchange-rates/"
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
        if not cleaned:
            return 0.0
        return float(cleaned)

    def _extract_office_table(self, html):
        match = re.search(
            r'<div(?=[^>]*class="[^"]*\bexchange__group\b[^"]*")(?=[^>]*data-tabs-target="tab1")[^>]*>'
            r"\s*<table[^>]*class=\"exchange__table\"[^>]*>(.*?)</table>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return match.group(1) if match else None

    def parse(self, html):
        if not html:
            return None

        table_html = self._extract_office_table(html)
        if not table_html:
            return None

        row_pattern = re.compile(
            r"<tr>\s*"
            r"<td>\s*(?P<code>[A-Z]{3})\s*</td>\s*"
            r"<td>\s*(?P<buy>[^<]*)\s*</td>\s*"
            r"<td>\s*(?P<sell>[^<]*)\s*</td>",
            re.IGNORECASE | re.DOTALL,
        )

        rates_by_code = {}
        target_codes = ("USD", "EUR", "RUB")

        for match in row_pattern.finditer(table_html):
            code = match.group("code").upper()
            if code not in target_codes or code in rates_by_code:
                continue

            buy_raw = match.group("buy").strip()
            sell_raw = match.group("sell").strip()
            if not buy_raw and not sell_raw:
                continue

            try:
                rates_by_code[code] = {
                    "buy": self._to_float(buy_raw),
                    "sell": self._to_float(sell_raw),
                }
            except ValueError:
                continue

        results = {}
        for code in target_codes:
            if code in rates_by_code:
                results[code] = rates_by_code[code]

        return results or None


if __name__ == "__main__":
    bank = MikroKreditBank()
    data = bank.parse(bank.fetch_data())
    print(data)
