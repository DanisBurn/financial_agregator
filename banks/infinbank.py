import re

from BaseBank import BaseBankScraper


class InfinBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "InfinBank"
        self.main_url = "https://www.infinbank.com/ru/private/exchange-rates/"
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

    def _strip_tags(self, value):
        return re.sub(r"<[^>]+>", "", value).replace("&nbsp;", " ").strip()

    def _extract_table(self, html):
        match = re.search(
            r'<div class="rates-table">\s*<table>(.*?)</table>\s*</div>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return match.group(1) if match else None

    def _extract_currency_codes(self, table_html):
        header_match = re.search(
            r"<thead>(.*?)</thead>",
            table_html,
            re.IGNORECASE | re.DOTALL,
        )
        if not header_match:
            return []

        return [
            code.upper()
            for code in re.findall(
                r'<span class="text">\s*([A-Z]{3})\s*</span>',
                header_match.group(1),
                re.IGNORECASE,
            )
        ]

    def _extract_exchange_rows(self, table_html):
        match = re.search(
            r'<tr[^>]*>\s*<td[^>]*class="rates-subtitle"[^>]*rowspan="2"[^>]*>\s*Обменный пункт\s*</td>(.*?)</tr>\s*'
            r'<tr[^>]*>(.*?)</tr>',
            table_html,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None, None
        return match.group(1), match.group(2)

    def _extract_row_values(self, row_html):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.IGNORECASE | re.DOTALL)
        return [self._strip_tags(cell) for cell in cells]

    def parse(self, html):
        if not html:
            return None

        table_html = self._extract_table(html)
        if not table_html:
            return None

        currency_codes = self._extract_currency_codes(table_html)
        if not currency_codes:
            return None

        buy_row_html, sell_row_html = self._extract_exchange_rows(table_html)
        if not buy_row_html or not sell_row_html:
            return None

        buy_cells = self._extract_row_values(buy_row_html)
        sell_cells = self._extract_row_values(sell_row_html)
        if len(buy_cells) < len(currency_codes) + 1 or len(sell_cells) < len(currency_codes) + 1:
            return None

        buy_values = buy_cells[1:1 + len(currency_codes)]
        sell_values = sell_cells[1:1 + len(currency_codes)]

        results = {}
        for code in ("USD", "EUR", "RUB"):
            if code not in currency_codes:
                continue

            idx = currency_codes.index(code)
            try:
                results[code] = {
                    "buy": self._to_float(buy_values[idx]),
                    "sell": self._to_float(sell_values[idx]),
                }
            except ValueError:
                continue

        return results or None


if __name__ == "__main__":
    bank = InfinBank()
    data = bank.parse(bank.fetch_data())
    print(data)
