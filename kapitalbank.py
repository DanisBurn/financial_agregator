import re

from BaseBank import BaseBankScraper
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

class KapitalBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Kapital Bank"
        self.main_url = 'https://www.kapitalbank.uz/ru/services/exchange-rates/'
        self.api_url = self.main_url

    def fetch_data(self):
        try:
            session = curl_requests.Session(impersonate="chrome136")
            session.headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": self.main_url,
            })

            response = session.get(
                self.api_url,
                timeout=30,
                allow_redirects=True,
            )
            response.raise_for_status()

            if "Just a moment..." in response.text or "cf-challenge" in response.text:
                raise RuntimeError(
                    "Cloudflare challenge was returned instead of exchange rates page"
                )

            return response.text
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    def _to_float(self, value):
        cleaned = value.replace("\xa0", " ").replace(" ", "").replace(",", ".")
        cleaned = re.sub(r"[^0-9.]", "", cleaned)
        return float(cleaned)

    def parse(self, html):
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        results = {}
        target_codes = {'USD', 'EUR', 'RUB'}
        target_branch = "Ташкентский городской филиал АКБ Капиталбанк"

        rows = soup.find_all('tr', attrs={'data-id': '1'})

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4:
                continue

            branch_name = cells[1].get_text(strip=True)
            if target_branch not in branch_name:
                continue

            currency_code = cells[0].get_text(strip=True).upper()
            if currency_code not in target_codes or currency_code in results:
                continue

            try:
                buy = self._to_float(cells[2].get_text(strip=True))
                sell = self._to_float(cells[3].get_text(strip=True))
                results[currency_code] = {
                    "buy": buy,
                    "sell": sell
                }
            except ValueError:
                continue

        return results if results else None

if __name__ == "__main__":
    bank = KapitalBank()
    data = bank.parse(bank.fetch_data())
    print(data)
