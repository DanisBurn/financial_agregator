import re
from BaseBank import BaseBankScraper
from bs4 import BeautifulSoup

class CbuGold(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "CBU Gold"
        self.main_url = "https://cbu.uz/ru/banknotes-coins/gold-bars/prices/"
        self.api_url = self.main_url
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.main_url,
        })

    @staticmethod
    def clean_price(price_str: str) -> int:
        digits = re.sub(r"[^\d]", "", price_str)
        return int(digits)

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
        date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        pattern = re.compile(
            r"(\d+)\s*грамм\s*"
            r"([\d\s]+)\s*сум\s*"
            r"([\d\s]+)\s*сум\s*"
            r"([\d\s]+)\s*сум",
            re.IGNORECASE,
        )

        items = []
        for weight, sell, buy_good, buy_damaged in pattern.findall(text):
            items.append({
                "weight_gram": int(weight),
                "sell_price_uzs": self.clean_price(sell),
                "buyback_undamaged_uzs": self.clean_price(buy_good),
                "buyback_damaged_uzs": self.clean_price(buy_damaged),
            })

        if not date_match and not items:
            return None

        return {
            "date": date_match.group(1) if date_match else None,
            "url": self.api_url,
            "items": items,
        }
