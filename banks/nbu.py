import re
from BaseBank import BaseBankScraper


class NBU(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "NBU"
        self.main_url = "https://nbu.uz/ru/fizicheskim-litsam-kursy-valyut"
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

    def _extract_cards(self, html):
        card_pattern = re.compile(
            r'<a[^>]+class="(?=[^"]*\bswiper-slide\b)(?=[^"]*\bis-navbar-22\b)(?=[^"]*\bw-inline-block\b)[^"]*"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        return card_pattern.findall(html)

    def parse(self, html):
        if not html:
            return None

        results = {}
        target_codes = {"USD", "EUR", "RUB"}

        for card in self._extract_cards(html):
            heading_match = re.search(
                r'navbar_22_top-currency-heading">\s*([A-Z]{3})\s*</div>',
                card,
                re.IGNORECASE,
            )
            if not heading_match:
                continue

            code = heading_match.group(1).upper()
            if code not in target_codes or code in results:
                continue

            values = re.findall(
                r'navbar_22_top-currency-text">\s*([^<]+?)\s*</div>',
                card,
                re.IGNORECASE,
            )
            if len(values) < 2:
                continue

            try:
                results[code] = {
                    "buy": self._to_float(values[0]),
                    "sell": self._to_float(values[1]),
                }
            except ValueError:
                continue

        return results or None
