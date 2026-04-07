import re

from bs4 import BeautifulSoup

try:
    from .base_bank_scraper import BaseBankScraper
except ImportError:
    from base_bank_scraper import BaseBankScraper


class Cbu(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "CBU"
        self.main_url = "https://cbu.uz/ru/"
        self.api_url = self.main_url
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.main_url,
        })

    def fetch_data(self):
        try:
            response = self.session.get(self.api_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def parse(self, html):
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)
        date_match = re.search(r"с\s\b(\d{2}\.\d{2}\.\d{4})\b", text)
        pattern = re.compile(
            r"(USD|EUR|RUB|GBP|JPY)\s*\n\s*=\s*(\d+\.\d+)",
            re.IGNORECASE,
        )

        items = {}
        for currency, value in pattern.findall(text):
            items[currency.upper()] = float(value)

        if not date_match and not items:
            return None

        return {
            "date": date_match.group(1) if date_match else None,
            "url": self.api_url,
            "items": items,
        }


if __name__ == "__main__":
    scraper = Cbu()
    raw_data = scraper.fetch_data()
    print(scraper.parse(raw_data))
