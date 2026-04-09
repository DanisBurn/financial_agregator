import re

from BaseBank import BaseBankScraper


class TrustBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "TrustBank"
        self.main_url = "https://trustbank.uz/ru/services/exchange-rates/"
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
        cleaned = str(value).replace("\xa0", " ").replace(" ", "").replace(",", ".")
        cleaned = re.sub(r"[^0-9.]", "", cleaned)
        return float(cleaned)

    def _extract_rate_block(self, html, block_name):
        match = re.search(
            rf'"{block_name}"\s*:\s*\{{(?P<block>.*?)\}}',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return match.group("block") if match else None

    def _extract_rate(self, block, code):
        if not block:
            return None

        match = re.search(
            rf'"{code}"\s*:\s*("?[^",}}]+"?|\d+(?:\.\d+)?)',
            block,
            re.IGNORECASE,
        )
        return match.group(1).strip('"') if match else None

    def parse(self, html):
        if not html:
            return None

        buy_block = self._extract_rate_block(html, "BUY")
        sell_block = self._extract_rate_block(html, "SALE")
        if not buy_block or not sell_block:
            return None

        results = {}
        for code in ("USD", "EUR", "RUB"):
            buy_raw = self._extract_rate(buy_block, code)
            sell_raw = self._extract_rate(sell_block, code)
            if buy_raw is None or sell_raw is None:
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
    bank = TrustBank()
    data = bank.parse(bank.fetch_data())
    print(data)
