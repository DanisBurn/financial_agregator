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
        pattern = re.compile(
            r"(\d+)\s*грамм\s*"
            r"([\d\s]+)\s*сум\s*"
            r"([\d\s]+)\s*сум\s*"
            r"([\d\s]+)\s*сум",
            re.IGNORECASE,
        )

        prices_by_weight = {}
        for weight, sell, buy_good, buy_damaged in pattern.findall(text):
            weight_key = f"{int(weight)} g"
            prices_by_weight[weight_key] = {
                "sell": self.clean_price(sell),
                "buy": self.clean_price(buy_good),
                "buy_damaged": self.clean_price(buy_damaged),
            }

        return prices_by_weight or None

if __name__ == "__main__":
    bank = CbuGold()
    c = bank.fetch_data()
    data = bank.parse(c)
    print(data)
