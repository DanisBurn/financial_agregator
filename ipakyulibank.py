import re
from BaseBank import BaseBankScraper


class IpakYuliBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "IpakYuliBank"
        self.main_url = "https://ru.ipakyulibank.uz/physical/obmen-valyut"
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
        return float(value) / 100

    def parse(self, html):
        if not html:
            return None

        pattern = re.compile(
            r'\{"id":\d+,"name":\d+,"code":\d+,"code_name":\d+,"symbol":\d+,"rate":\d+\},'
            r'\d+,"[^"]+","\d+","(?P<code>USD|EUR|RUB)","[^"]*",'
            r'\{"buy":\d+,"sell":\d+,"cb":\d+\},'
            r'(?P<buy>\d+),(?P<sell>\d+),(?P<cb>\d+)',
            re.IGNORECASE,
        )

        results = {}
        for match in pattern.finditer(html):
            code = match.group("code").upper()
            if code in results:
                continue

            try:
                results[code] = {
                    "buy": self._to_float(match.group("buy")),
                    "sell": self._to_float(match.group("sell")),
                }
            except (TypeError, ValueError):
                continue

        ordered_results = {}
        for code in ("USD", "EUR", "RUB"):
            if code in results:
                ordered_results[code] = results[code]

        return ordered_results or None


if __name__ == "__main__":
    bank = IpakYuliBank()
    data = bank.parse(bank.fetch_data())
    print(data)
