import pytest
from django.urls import reverse
from unittest.mock import patch

pytestmark = pytest.mark.django_db

@patch('rates.views.home_services') 
def test_home_page_view_loads_successfully(mock_services, client):
    """
    Проверяем, что главная страница отдает 200 OK и рендерит HTML.
    Мы мокаем сервисный слой, чтобы изолировать тест от MongoDB.
    """
    
    mock_services.load_raw_bank_payloads.return_value = [] 
    mock_services.get_supported_currencies.return_value = ["USD", "EUR", "RUB"]
    mock_services.pick_currency.return_value = "USD"
    mock_services.aggregate_best_rates.return_value = {"as_of": "2026-04-10T10:00:00"}
    mock_services.build_bank_cards.return_value = []
    mock_services.build_compare_rows.return_value = []
    mock_services.build_ticker_items.return_value = []
    
    # --- ИСПРАВЛЕНИЕ ---
    # Указываем обычные типы данных (None или {}), чтобы фильтр |json_script 
    # в твоих HTML-шаблонах не сломался при попытке конвертации
    mock_services.build_gold.return_value = None
    mock_services.build_history_chart.return_value = None
    mock_services.build_forecast_chart.return_value = None
    mock_services.build_cbu_reference_block.return_value = None
    mock_services.build_stats.return_value = {}
    mock_services.now_as_of.return_value = "2026-04-10T10:00:00"

    # 2. Делаем виртуальный GET-запрос к сайту
    url = reverse('rates:home') 
    response = client.get(url)
    
    # 3. Проверки
    assert response.status_code == 200, "Страница должна возвращать статус 200 OK"
    assert 'rates/home.html' in [t.name for t in response.templates], "Должен использоваться правильный шаблон (rates/home.html)"
    assert mock_services.load_dashboard_snapshot.called, "View должен был загрузить данные из сервиса"