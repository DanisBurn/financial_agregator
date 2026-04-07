import requests
from abc import ABC, abstractmethod


class BaseBankScraper(ABC):
    def __init__(self):
        self.bank_name = "BaseBank"
        self.main_url = ""
        self.api_url = ""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        })

    def fetch_data(self):
        try:
            self.session.get(self.main_url, timeout=10)
            response = self.session.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[-] Ошибка в {self.bank_name}: {e}")
            return None

    @abstractmethod
    def parse(self, data):
        pass
