import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse

from .models import TelegramMiniAppUser


pytestmark = pytest.mark.django_db


def build_telegram_init_data(user_payload, bot_token, auth_timestamp=None):
    auth_timestamp = auth_timestamp or int(time.time())
    params = {
        "auth_date": str(auth_timestamp),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user_payload, separators=(",", ":"), ensure_ascii=False),
    }
    data_check_string = "\n".join(f"{key}={params[key]}" for key in sorted(params))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(params)


@patch("rates.views.home_services")
def test_home_page_view_loads_successfully(mock_services, client):
    mock_services.load_dashboard_snapshot.return_value = type(
        "Snapshot",
        (),
        {
            "previous_currency_docs": [],
            "current_gold_docs": [],
            "previous_gold_docs": [],
            "current_currency_docs": [],
            "prediction_docs": [],
            "cbu_history": {},
        },
    )()
    mock_services.load_raw_bank_payloads.return_value = []
    mock_services.get_supported_currencies.return_value = ["USD", "EUR", "RUB"]
    mock_services.pick_currency.return_value = "USD"
    mock_services.aggregate_best_rates.return_value = {"as_of": "2026-04-10T10:00:00"}
    mock_services.build_bank_cards.return_value = []
    mock_services.build_compare_rows.return_value = []
    mock_services.build_ticker_items.return_value = []
    mock_services.build_gold.return_value = None
    mock_services.build_history_chart.return_value = None
    mock_services.build_forecast_chart.return_value = None
    mock_services.build_cbu_reference_block.return_value = None
    mock_services.build_stats.return_value = {}
    mock_services.now_as_of.return_value = "2026-04-10T10:00:00"

    url = reverse("rates:home")
    response = client.get(url)

    assert response.status_code == 200
    assert "rates/home.html" in [template.name for template in response.templates]
    assert mock_services.load_dashboard_snapshot.called


def test_miniapp_entry_redirects_to_localized_home(client):
    response = client.get(reverse("miniapp_entry"), {"lang": "ru", "c": "EUR"})

    assert response.status_code == 302
    assert response["Location"] == "/ru/?c=EUR&miniapp=1"


@override_settings(TELEGRAM_AUTH_MAX_AGE=3600)
def test_miniapp_auth_creates_telegram_user_and_session(client):
    bot_token = "test-bot-token"
    user_payload = {
        "id": 777000,
        "first_name": "Mini",
        "last_name": "App",
        "username": "mini_app_user",
        "language_code": "ru",
        "is_premium": True,
    }
    init_data = build_telegram_init_data(user_payload, bot_token)

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": bot_token}, clear=False):
        response = client.post(
            reverse("rates:miniapp_auth"),
            data=json.dumps({"init_data": init_data}),
            content_type="application/json",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["user"]["telegram_id"] == 777000
    assert payload["user"]["display_name"] == "Mini App"

    profile = TelegramMiniAppUser.objects.get(telegram_id=777000)
    assert profile.username == "mini_app_user"
    assert client.session["telegram_user"]["telegram_id"] == 777000
