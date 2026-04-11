from __future__ import annotations

import json
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import TelegramMiniAppUser
from .services import home_page as home_services
from .services import telegram_miniapp as telegram_services


SUPPORTED_LANGUAGES = {code for code, _label in settings.LANGUAGES}


def _serialize_bank_card(card) -> dict[str, Any]:
    return {
        "id": card.id,
        "name": card.name,
        "type": card.type,
        "abbr": card.abbr,
        "color": card.color,
        "bg": card.bg,
        "buy": card.buy,
        "sell": card.sell,
        "buy_display": card.buy_display,
        "sell_display": card.sell_display,
        "spread_display": card.spread_display,
        "change_pct": card.change_pct,
        "is_best_buy": card.is_best_buy,
        "is_best_sell": card.is_best_sell,
        "is_reference": card.is_reference,
    }


def _serialize_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "aggregated": context["aggregated"],
        "raw_count": context["raw_count"],
        "current_currency": context["current_currency"],
        "currencies": context["currencies"],
        "banks": [_serialize_bank_card(bank) for bank in context["banks"]],
        "compare_rows": context["compare_rows"],
        "stats": context["stats"],
        "gold": context["gold"],
        "history_chart": context["history_chart"],
        "forecast_chart": context["forecast_chart"],
        "cbu_reference": context["cbu_reference"],
        "ticker_items": context["ticker_items"],
        "miniapp_mode": context["miniapp_mode"],
        "miniapp_config": context["miniapp_config"],
        "telegram_user": context["telegram_user"],
    }


def _get_session_telegram_user(request: HttpRequest) -> dict[str, Any] | None:
    session_user = request.session.get("telegram_user")
    return session_user if isinstance(session_user, dict) else None


def _build_miniapp_config(request: HttpRequest, miniapp_mode: bool, telegram_user: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "mode": miniapp_mode,
        "authUrl": reverse("rates:miniapp_auth"),
        "statusUrl": reverse("rates:miniapp_status"),
        "dashboardUrl": reverse("rates:dashboard_api"),
        "entryUrl": reverse("miniapp_entry"),
        "botUsername": telegram_services.get_bot_username(),
        "miniappUrl": telegram_services.get_miniapp_url(),
        "currentLanguage": translation.get_language() or settings.LANGUAGE_CODE,
        "telegramUser": telegram_user,
    }


def build_home_context(request: HttpRequest) -> dict[str, Any]:
    snapshot = home_services.load_dashboard_snapshot()
    raw = home_services.load_raw_bank_payloads(snapshot)
    currencies = home_services.get_supported_currencies(raw)
    current_currency = home_services.pick_currency(request.GET, currencies)
    aggregated = home_services.aggregate_best_rates(raw)
    banks = home_services.build_bank_cards(
        current_currency=current_currency,
        raw=raw,
        previous_raw=snapshot.previous_currency_docs,
    )
    gold = home_services.build_gold(
        gold_docs=snapshot.current_gold_docs,
        previous_gold_docs=snapshot.previous_gold_docs,
    )
    history_chart = home_services.build_history_chart(snapshot.cbu_history)
    forecast_chart = home_services.build_forecast_chart(
        raw=snapshot.current_currency_docs,
        cbu_history=snapshot.cbu_history,
        prediction_docs=snapshot.prediction_docs,
    )
    cbu_reference = home_services.build_cbu_reference_block(
        raw=snapshot.current_currency_docs,
        current_currency=current_currency,
        previous_raw=snapshot.previous_currency_docs,
    )
    miniapp_mode = request.GET.get("miniapp") == "1"
    telegram_user = _get_session_telegram_user(request)

    context = {
        "aggregated": {**aggregated, "as_of": aggregated.get("as_of") or home_services.now_as_of()},
        "raw_count": len(raw),
        "current_currency": current_currency,
        "currencies": currencies,
        "banks": banks,
        "compare_rows": home_services.build_compare_rows(banks),
        "stats": home_services.build_stats(banks),
        "gold": gold,
        "history_chart": history_chart,
        "forecast_chart": forecast_chart,
        "cbu_reference": cbu_reference,
        "ticker_items": home_services.build_ticker_items(
            raw=raw,
            previous_raw=snapshot.previous_currency_docs,
            gold_docs=snapshot.current_gold_docs,
            previous_gold_docs=snapshot.previous_gold_docs,
        ),
        "miniapp_mode": miniapp_mode,
        "telegram_user": telegram_user,
    }
    context["miniapp_config"] = _build_miniapp_config(request, miniapp_mode, telegram_user)
    return context


@ensure_csrf_cookie
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "rates/home.html", build_home_context(request))


@require_GET
def miniapp_entry(request: HttpRequest) -> HttpResponse:
    language_code = str(
        request.GET.get("lang")
        or request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        or "ru"
    ).strip().lower()
    if language_code not in SUPPORTED_LANGUAGES:
        language_code = "ru"

    query = request.GET.copy()
    query.pop("lang", None)
    query["miniapp"] = "1"
    if not query.get("c"):
        query["c"] = "USD"

    with translation.override(language_code):
        target_url = reverse("rates:home")

    query_string = query.urlencode()
    if query_string:
        target_url = f"{target_url}?{query_string}"

    return redirect(target_url)


@require_GET
def dashboard_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True, "data": _serialize_context(build_home_context(request))})


@require_GET
def miniapp_status(request: HttpRequest) -> JsonResponse:
    miniapp_mode = request.GET.get("miniapp") == "1"
    telegram_user = _get_session_telegram_user(request)
    return JsonResponse(
        {
            "ok": True,
            "data": {
                "authenticated": bool(telegram_user),
                "telegram_user": telegram_user,
                "miniapp_config": _build_miniapp_config(request, miniapp_mode, telegram_user),
            },
        }
    )


@require_POST
def miniapp_auth(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid JSON body"}, status=400)

    init_data = str(payload.get("init_data") or "").strip()
    if not init_data:
        return JsonResponse({"ok": False, "error": "init_data is required"}, status=400)

    try:
        auth = telegram_services.validate_init_data(
            init_data,
            max_age_seconds=settings.TELEGRAM_AUTH_MAX_AGE,
        )
    except RuntimeError as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=503)
    except ValueError as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=403)

    user_payload = telegram_services.normalize_telegram_user(auth.user)
    profile, _created = TelegramMiniAppUser.objects.update_or_create(
        telegram_id=user_payload["telegram_id"],
        defaults={
            "username": user_payload["username"],
            "first_name": user_payload["first_name"],
            "last_name": user_payload["last_name"],
            "language_code": user_payload["language_code"],
            "photo_url": user_payload["photo_url"],
            "is_premium": user_payload["is_premium"],
            "allows_write_to_pm": user_payload["allows_write_to_pm"],
            "last_auth_at": auth.auth_date,
        },
    )

    session_user = {
        **user_payload,
        "profile_id": profile.pk,
        "last_auth_at": auth.auth_date.isoformat(),
        "query_id": auth.query_id,
    }
    request.session["telegram_user"] = session_user
    request.session["telegram_profile_id"] = profile.pk
    request.session["telegram_authenticated"] = True
    request.session["telegram_auth_at"] = auth.auth_date.isoformat()

    return JsonResponse({"ok": True, "user": session_user})
