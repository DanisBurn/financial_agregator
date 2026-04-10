import pytest
from unittest.mock import patch

from banks.BaseBank import BaseBankScraper

# --- ВСПОМОГАТЕЛЬНЫЙ КЛАСС ---
class MinimalBank(BaseBankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "Minimal Test Bank"
        self.api_url = "http://test.com"

    def parse(self, html):
        return {"USD": {"buy": 12000, "sell": 12100}}

# --- ТЕСТЫ ДЛЯ BASEBANK ---

def test_base_bank_initialization():
    """Проверяем, что базовый класс корректно создает настройки и сессию."""
    bank = MinimalBank()
    
    assert hasattr(bank, 'session'), "У базового класса должна быть session"
    assert hasattr(bank, 'bank_name'), "Должен быть атрибут bank_name"
    assert hasattr(bank, 'main_url'), "Должен быть атрибут main_url"

@patch('banks.BaseBank.requests.Session.get')
def test_base_bank_fetch_data_network_error(mock_get):
    """Проверяем, как ядро реагирует на таймауты и недоступность сайтов банков."""
    mock_get.side_effect = Exception("Connection Timeout")
    
    bank = MinimalBank()
    result = bank.fetch_data()
    
    assert result is None, "При ошибке сети fetch_data должен безопасно возвращать None"