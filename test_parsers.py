import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
banks_dir = os.path.join(current_dir, "banks")
if banks_dir not in sys.path:
    sys.path.insert(0, banks_dir)


from banks.tbcbank import TBCBank
from banks.agrobank import Agrobank


def test_tbcbank_parser_success():
    """
    Проверяем, как парсер TBC справляется со сложной структурой JS-массива.
    """
    bank = TBCBank()
    
    fake_html = """
    <html>
        <body>
            <script>
                var state = [
                    "USD", 12150.00, 35, 12250.00,
                    "EUR", "UZS", 13800.00, 100, 14700.00
                ];
            </script>
        </body>
    </html>
    """
    
    result = bank.parse(fake_html)
    
    assert result is not None, "Парсер вернул None, хотя данные в HTML есть"
    
    assert "USD" in result
    assert result["USD"]["buy"] == 12150.0, "Неверный курс покупки USD"
    assert result["USD"]["sell"] == 12250.0, "Неверный курс продажи USD"
    
    assert "EUR" in result
    assert result["EUR"]["buy"] == 13800.0, "Неверный курс покупки EUR"
    assert result["EUR"]["sell"] == 14700.0, "Неверный курс продажи EUR"


def test_tbcbank_parser_empty_html():
    """Проверяем, что парсер не падает при пустой странице"""
    bank = TBCBank()
    result = bank.parse("<html><body><h1>Сайт на реконструкции</h1></body></html>")
    
    assert result is None, "Если валют нет, парсер должен тихо вернуть None"


def test_classic_table_parser_template():
    """Шаблон для банков с таблицами"""
    bank = Agrobank() 
    
    fake_html = """
    <table>
        <tr>
            <td>Покупка</td>
            <td>Продажа</td>
        </tr>
        <tr>
            <td>USD</td>
            <td>12100.50</td>
            <td>12230</td>
        </tr>
        <tr>
            <td>EUR</td>
            <td>13500</td>
            <td>14600</td>
        </tr>
    </table>
    """
    
    result = bank.parse(fake_html)