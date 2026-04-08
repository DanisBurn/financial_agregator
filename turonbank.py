import re
from BaseBank import BaseBankScraper


class TuronBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "TuronBank"
        self.main_url = "https://turonbank.uz/ru/services/exchange-rates/"
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

    def _extract_exchange_point_block(self, html):
        match = re.search(
            r'<div class="exchange__group active" data-tabs-target="tab1">(.*?)</table>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None
        return match.group(1)

    def _extract_row(self, block_html, code):
        match = re.search(
            rf'<tr>\s*<td>\s*<div class="currency-name">\s*'
            rf'<div class="currency-name__code">\s*{re.escape(code)}\s*</div>'
            rf'.*?</tr>',
            block_html,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None
        return match.group(0)

    def _extract_values(self, row_html):
        values = re.findall(
            r'<td>\s*<div class="exchange-value">\s*(?:<span>\s*([^<]*)\s*</span>)?',
            row_html,
            re.IGNORECASE | re.DOTALL,
        )
        if len(values) < 3:
            return None
        return values[0], values[1]

    def parse(self, html):
        if not html:
            return None

        block_html = self._extract_exchange_point_block(html)
        if not block_html:
            return None

        results = {}
        target_codes = ("USD", "EUR", "RUB")

        for code in target_codes:
            row_html = self._extract_row(block_html, code)
            if not row_html:
                continue

            values = self._extract_values(row_html)
            if not values:
                continue

            buy_raw, sell_raw = values
            if not str(buy_raw).strip() or not str(sell_raw).strip():
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
    bank = TuronBank()
    data = bank.parse(bank.fetch_data())
    print(data)
