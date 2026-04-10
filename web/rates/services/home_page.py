from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils.translation import gettext as _

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None


MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://dubrovskayaamaliya_db_user:3Sbu5zoJLEb7gDoI@zoloto.wkualrv.mongodb.net/?appName=Zoloto",
)
MONGO_DB_NAME = "banks_data"
MONGO_COLLECTION_NAME = "currency_rates"
MONGO_GOLD_COLLECTION_NAME = "gold_rates"
MONGO_PREDICTIONS_COLLECTION_NAME = "predictions"

DEFAULT_CURRENCIES = ["USD", "EUR", "RUB"]
PREFERRED_CURRENCY_ORDER = ["USD", "EUR", "RUB", "CNY", "GBP", "JPY", "KZT", "TRY", "AED", "KRW"]
HISTORY_CURRENCIES = ["USD", "EUR", "RUB"]
FORECAST_CURRENCIES = ["USD", "EUR"]
REFERENCE_BANKS = {"CBU"}
DISPLAY_BANK_NAMES = {"XB": "XalqBank"}
GOLD_WEIGHT_ORDER = ["1 g", "5 g", "10 g", "20 g", "50 g", "100 g"]
FLAG_BY_CURRENCY = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
    "CNY": "🇨🇳",
    "GBP": "🇬🇧",
    "JPY": "🇯🇵",
    "KZT": "🇰🇿",
    "TRY": "🇹🇷",
    "AED": "🇦🇪",
    "KRW": "🇰🇷",
    "XAU": "🥇",
}
CURRENCY_COLORS = {
    "USD": "#00e5a0",
    "EUR": "#f59e0b",
    "RUB": "#4a9eff",
}
BANK_META_OVERRIDES = {
    "CBU": {"abbr": "CB", "color": "#00e5a0", "bg": "rgba(0,229,160,0.13)"},
    "XalqBank": {"abbr": "XB", "color": "#0ea5e9", "bg": "rgba(14,165,233,0.13)"},
    "AsakaBank": {"abbr": "AB", "color": "#f97316", "bg": "rgba(249,115,22,0.13)"},
    "IpakYuliBank": {"abbr": "IY", "color": "#f59e0b", "bg": "rgba(245,158,11,0.13)"},
    "HamkorBank": {"abbr": "HB", "color": "#14b8a6", "bg": "rgba(20,184,166,0.13)"},
    "Orient Finans Bank": {"abbr": "OF", "color": "#ef4444", "bg": "rgba(239,68,68,0.13)"},
}
BANK_COLOR_PALETTE = [
    ("#4a9eff", "rgba(74,158,255,0.13)"),
    ("#f97316", "rgba(249,115,22,0.13)"),
    ("#14b8a6", "rgba(20,184,166,0.13)"),
    ("#ef4444", "rgba(239,68,68,0.13)"),
    ("#8b5cf6", "rgba(139,92,246,0.13)"),
    ("#eab308", "rgba(234,179,8,0.13)"),
]


@dataclass(frozen=True)
class DashboardSnapshot:
    current_date: str | None
    previous_date: str | None
    current_currency_docs: list[dict[str, Any]]
    previous_currency_docs: list[dict[str, Any]]
    current_gold_docs: list[dict[str, Any]]
    previous_gold_docs: list[dict[str, Any]]
    prediction_docs: list[dict[str, Any]]
    cbu_history: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class BankCard:
    id: str
    name: str
    type: str
    abbr: str
    color: str
    bg: str
    buy: float | None
    sell: float | None
    change_pct: float
    is_best_buy: bool
    is_reference: bool

    @property
    def buy_display(self) -> str:
        return format_rate(self.buy)

    @property
    def sell_display(self) -> str:
        return format_rate(self.sell)

    @property
    def spread_display(self) -> str:
        if self.buy is None or self.sell is None:
            return "—"
        return format_rate(self.sell - self.buy)


def _empty_snapshot() -> DashboardSnapshot:
    return DashboardSnapshot(
        current_date=None,
        previous_date=None,
        current_currency_docs=[],
        previous_currency_docs=[],
        current_gold_docs=[],
        previous_gold_docs=[],
        prediction_docs=[],
        cbu_history={},
    )


def _create_client():
    if MongoClient is None:
        return None

    try:
        return MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
    except Exception:
        return None


def _find_latest_date(collection) -> str | None:
    doc = collection.find_one(sort=[("date_only", -1), ("timestamp", -1)])
    return doc.get("date_only") if doc else None


def _find_previous_date(collection, current_date: str | None) -> str | None:
    if not current_date:
        return None

    doc = collection.find_one(
        {"date_only": {"$lt": current_date}},
        sort=[("date_only", -1), ("timestamp", -1)],
    )
    return doc.get("date_only") if doc else None


def _load_cbu_history(collection) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = {}
    for currency in HISTORY_CURRENCIES:
        docs = list(
            collection.find(
                {"bank_name": "CBU", "currency": currency},
                {"_id": 0},
            )
            .sort([("date_only", -1), ("timestamp", -1)])
            .limit(14)
        )
        history[currency] = list(reversed(docs))
    return history


def load_dashboard_snapshot() -> DashboardSnapshot:
    client = _create_client()
    if client is None:
        return _empty_snapshot()

    try:
        db = client[MONGO_DB_NAME]
        currency_collection = db[MONGO_COLLECTION_NAME]
        current_date = _find_latest_date(currency_collection)
        if not current_date:
            return _empty_snapshot()

        previous_date = _find_previous_date(currency_collection, current_date)

        current_currency_docs = list(
            currency_collection.find({"date_only": current_date}, {"_id": 0}).sort(
                [("currency", 1), ("bank_name", 1)]
            )
        )
        previous_currency_docs: list[dict[str, Any]] = []
        if previous_date:
            previous_currency_docs = list(
                currency_collection.find({"date_only": previous_date}, {"_id": 0}).sort(
                    [("currency", 1), ("bank_name", 1)]
                )
            )

        gold_collection = db[MONGO_GOLD_COLLECTION_NAME]
        current_gold_docs = list(
            gold_collection.find({"date_only": current_date}, {"_id": 0}).sort([("weight", 1)])
        )
        previous_gold_docs: list[dict[str, Any]] = []
        if previous_date:
            previous_gold_docs = list(
                gold_collection.find({"date_only": previous_date}, {"_id": 0}).sort([("weight", 1)])
            )

        prediction_docs = list(
            db[MONGO_PREDICTIONS_COLLECTION_NAME]
            .find({"date_only": current_date}, {"_id": 0})
            .sort([("bank_name", 1), ("currency", 1)])
        )

        return DashboardSnapshot(
            current_date=current_date,
            previous_date=previous_date,
            current_currency_docs=current_currency_docs,
            previous_currency_docs=previous_currency_docs,
            current_gold_docs=current_gold_docs,
            previous_gold_docs=previous_gold_docs,
            prediction_docs=prediction_docs,
            cbu_history=_load_cbu_history(currency_collection),
        )
    except Exception:
        return _empty_snapshot()
    finally:
        client.close()


def _to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return number


def _mean_rate(buy: float | None, sell: float | None) -> float | None:
    candidates = [value for value in (buy, sell) if value is not None]
    if not candidates:
        return None
    return sum(candidates) / len(candidates)


def _format_timestamp(timestamp: str | None) -> str | None:
    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return timestamp


def _format_date(value: str | None) -> str | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def _doc_timestamp(doc: dict[str, Any]) -> str:
    return str(doc.get("timestamp") or "")


def _sorted_currencies(codes: set[str]) -> list[str]:
    ordered = [code for code in PREFERRED_CURRENCY_ORDER if code in codes]
    extras = sorted(code for code in codes if code not in set(PREFERRED_CURRENCY_ORDER))
    return ordered + extras


def _slugify_bank(bank_name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in bank_name).strip("-")


def _is_reference_bank(bank_name: str) -> bool:
    return bank_name in REFERENCE_BANKS


def _display_bank_name(bank_name: str) -> str:
    return DISPLAY_BANK_NAMES.get(bank_name, bank_name)


def _bank_abbr(bank_name: str) -> str:
    parts = [part for part in bank_name.replace("-", " ").split() if part]
    if not parts:
        return "BK"

    if len(parts) == 1:
        letters = "".join(ch for ch in parts[0] if ch.isalpha())
        return (letters[:2] or parts[0][:2]).upper()

    return "".join(part[0] for part in parts[:2]).upper()


def _bank_visual(bank_name: str) -> dict[str, str]:
    override = BANK_META_OVERRIDES.get(bank_name)
    if override:
        return override

    idx = sum(ord(ch) for ch in bank_name) % len(BANK_COLOR_PALETTE)
    color, bg = BANK_COLOR_PALETTE[idx]
    return {
        "abbr": _bank_abbr(bank_name),
        "color": color,
        "bg": bg,
    }


def _index_currency_docs(raw: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for doc in raw:
        bank_name = str(doc.get("bank_name") or "")
        currency = str(doc.get("currency") or "").upper()
        if bank_name and currency:
            indexed[(bank_name, currency)] = doc
    return indexed


def _group_currency_docs(raw: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for doc in raw:
        currency = str(doc.get("currency") or "").upper()
        if currency:
            grouped.setdefault(currency, []).append(doc)
    return grouped


def _index_gold_docs(raw: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for doc in raw:
        weight = str(doc.get("weight") or "")
        if weight:
            indexed[weight] = doc
    return indexed


def _parse_weight_grams(weight: str) -> int | None:
    digits = "".join(ch for ch in weight if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _extract_doc_rate(doc: dict[str, Any]) -> float | None:
    return _to_float(doc.get("buy")) or _to_float(doc.get("sell")) or _to_float(doc.get("rate"))


def _find_best_doc(
    docs: list[dict[str, Any]],
    field: str,
    reverse: bool,
) -> tuple[dict[str, Any] | None, float | None]:
    candidates = []
    for doc in docs:
        value = _to_float(doc.get(field))
        if value is not None:
            candidates.append((doc, value))

    if not candidates:
        return None, None

    selector = max if reverse else min
    return selector(candidates, key=lambda item: item[1])


def format_rate(value: float | int | None) -> str:
    if value is None:
        return "—"

    return f"{int(round(float(value))):,}".replace(",", " ")


def load_raw_bank_payloads(snapshot: DashboardSnapshot | None = None) -> list[dict[str, Any]]:
    snapshot = snapshot or load_dashboard_snapshot()
    return snapshot.current_currency_docs


def aggregate_best_rates(raw: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = _group_currency_docs(raw)
    as_of_candidates = []
    currencies = []

    for code in _sorted_currencies(set(grouped)):
        docs = [doc for doc in grouped.get(code, []) if not _is_reference_bank(str(doc.get("bank_name") or ""))]
        as_of_candidates.extend(_doc_timestamp(doc) for doc in docs)

        best_buy_doc, best_buy = _find_best_doc(docs, "buy", reverse=True)
        best_sell_doc, best_sell = _find_best_doc(docs, "sell", reverse=False)

        currencies.append(
            {
                "code": code,
                "best_buy": best_buy,
                "best_buy_bank": _display_bank_name(str(best_buy_doc.get("bank_name") or "")) if best_buy_doc else None,
                "best_sell": best_sell,
                "best_sell_bank": _display_bank_name(str(best_sell_doc.get("bank_name") or "")) if best_sell_doc else None,
            }
        )

    as_of = _format_timestamp(max((value for value in as_of_candidates if value), default=None))
    return {"currencies": currencies, "as_of": as_of}


def get_supported_currencies(raw: list[dict[str, Any]] | None = None) -> list[str]:
    raw = raw or []
    codes = {str(doc.get("currency") or "").upper() for doc in raw if doc.get("currency")}
    sorted_codes = _sorted_currencies(codes)
    return sorted_codes or DEFAULT_CURRENCIES


def pick_currency(request_get: dict[str, Any], supported_currencies: list[str] | None = None) -> str:
    supported_currencies = supported_currencies or DEFAULT_CURRENCIES
    cur = (request_get.get("c") or "").upper().strip()
    return cur if cur in set(supported_currencies) else supported_currencies[0]


def build_bank_cards(
    current_currency: str,
    raw: list[dict[str, Any]],
    previous_raw: list[dict[str, Any]] | None = None,
) -> list[BankCard]:
    previous_index = _index_currency_docs(previous_raw or [])
    cards: list[BankCard] = []

    for doc in raw:
        if str(doc.get("currency") or "").upper() != current_currency:
            continue

        raw_bank_name = str(doc.get("bank_name") or "").strip()
        if not raw_bank_name:
            continue

        display_name = _display_bank_name(raw_bank_name)
        buy = _to_float(doc.get("buy"))
        sell = _to_float(doc.get("sell"))
        if buy is None and sell is None:
            continue

        previous_doc = previous_index.get((raw_bank_name, current_currency))
        previous_buy = _to_float(previous_doc.get("buy")) if previous_doc else None
        previous_sell = _to_float(previous_doc.get("sell")) if previous_doc else None

        current_mid = _mean_rate(buy, sell)
        previous_mid = _mean_rate(previous_buy, previous_sell)
        change_pct = 0.0
        if current_mid is not None and previous_mid:
            change_pct = round(((current_mid - previous_mid) / previous_mid) * 100, 2)

        meta = _bank_visual(display_name)
        cards.append(
            BankCard(
                id=_slugify_bank(display_name),
                name=display_name,
                type=_("Central bank") if _is_reference_bank(raw_bank_name) else _("Commercial bank"),
                abbr=meta["abbr"],
                color=meta["color"],
                bg=meta["bg"],
                buy=buy,
                sell=sell,
                change_pct=change_pct,
                is_best_buy=False,
                is_reference=_is_reference_bank(raw_bank_name),
            )
        )

    best_buy = max(
        (card.buy for card in cards if card.buy is not None and not card.is_reference),
        default=None,
    )

    return [
        BankCard(
            **{
                **card.__dict__,
                "is_best_buy": bool(best_buy is not None and not card.is_reference and card.buy == best_buy),
            }
        )
        for card in sorted(cards, key=lambda card: card.name.lower())
    ]


def build_compare_rows(banks: list[BankCard]) -> list[dict[str, Any]]:
    return [
        {
            "name": bank.name,
            "type": bank.type,
            "abbr": bank.abbr,
            "color": bank.color,
            "bg": bank.bg,
            "buy_display": bank.buy_display,
            "sell_display": bank.sell_display,
            "spread_display": bank.spread_display,
            "is_reference": bank.is_reference,
        }
        for bank in sorted(
            banks,
            key=lambda card: (card.is_reference, card.buy is None, -(card.buy or 0), card.name.lower()),
        )
    ]


def build_stats(banks: list[BankCard]) -> dict[str, Any]:
    commercial_banks = [bank for bank in banks if not bank.is_reference]
    buy_candidates = [bank for bank in commercial_banks if bank.buy is not None]
    sell_candidates = [bank for bank in commercial_banks if bank.sell is not None]

    if not buy_candidates and not sell_candidates:
        return {"bank_count": len(commercial_banks)}

    top_buy = max(buy_candidates, key=lambda bank: bank.buy or 0) if buy_candidates else None
    low_sell = min(sell_candidates, key=lambda bank: bank.sell or float("inf")) if sell_candidates else None

    return {
        "bank_count": len(commercial_banks),
        "top_buy_rate": top_buy.buy_display if top_buy else "—",
        "top_buy_bank": top_buy.name if top_buy else "—",
        "low_sell_rate": low_sell.sell_display if low_sell else "—",
        "low_sell_bank": low_sell.name if low_sell else "—",
    }


def build_gold_options(
    gold_docs: list[dict[str, Any]] | None = None,
    previous_gold_docs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    current_index = _index_gold_docs(gold_docs or [])
    previous_index = _index_gold_docs(previous_gold_docs or [])
    actual_options: dict[str, dict[str, Any]] = {}

    for weight, doc in current_index.items():
        grams = _parse_weight_grams(weight)
        current_price = _to_float(doc.get("sell")) or _to_float(doc.get("buy"))
        if not grams or current_price is None:
            continue

        previous_doc = previous_index.get(weight)
        previous_price = None
        if previous_doc:
            previous_price = _to_float(previous_doc.get("sell")) or _to_float(previous_doc.get("buy"))

        change_pct = None
        if previous_price:
            change_pct = round(((current_price - previous_price) / previous_price) * 100, 2)

        actual_options[weight] = {
            "weight": weight,
            "grams": grams,
            "price": current_price,
            "price_display": format_rate(current_price),
            "previous_price": previous_price,
            "per_gram": current_price / grams,
            "per_gram_display": format_rate(current_price / grams),
            "change_pct": change_pct,
            "is_derived": False,
        }

    options: list[dict[str, Any]] = []
    if actual_options:
        smallest = min(actual_options.values(), key=lambda item: item["grams"])
        previous_per_gram = None
        if smallest.get("previous_price"):
            previous_per_gram = smallest["previous_price"] / smallest["grams"]

        change_pct = None
        if previous_per_gram:
            change_pct = round(((smallest["per_gram"] - previous_per_gram) / previous_per_gram) * 100, 2)

        options.append(
            {
                "weight": "1 g",
                "grams": 1,
                "price": smallest["per_gram"],
                "price_display": format_rate(smallest["per_gram"]),
                "previous_price": previous_per_gram,
                "per_gram": smallest["per_gram"],
                "per_gram_display": format_rate(smallest["per_gram"]),
                "change_pct": change_pct,
                "is_derived": True,
            }
        )

    for weight in GOLD_WEIGHT_ORDER:
        if weight == "1 g":
            continue
        if weight in actual_options:
            options.append(actual_options[weight])

    extra_weights = sorted(
        (
            weight
            for weight in actual_options
            if weight not in set(GOLD_WEIGHT_ORDER)
        ),
        key=lambda item: _parse_weight_grams(item) or 10**9,
    )
    for weight in extra_weights:
        options.append(actual_options[weight])

    return options


def build_gold(
    gold_docs: list[dict[str, Any]] | None = None,
    previous_gold_docs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    options = build_gold_options(gold_docs, previous_gold_docs)
    if not options:
        return {
            "price_display": "—",
            "change_pct": None,
            "selected_weight": None,
            "per_gram_display": "—",
            "options": [],
            "selected_price": None,
        }

    selected = options[0]
    return {
        "price_display": selected["price_display"],
        "change_pct": selected["change_pct"],
        "selected_weight": selected["weight"],
        "per_gram_display": selected["per_gram_display"],
        "options": options,
        "selected_price": selected["price"],
    }


def _ticker_direction(current_value: float | None, previous_value: float | None) -> str:
    if current_value is None or previous_value is None:
        return "flat"
    if current_value > previous_value:
        return "up"
    if current_value < previous_value:
        return "down"
    return "flat"


def build_ticker_items(
    raw: list[dict[str, Any]],
    previous_raw: list[dict[str, Any]] | None = None,
    gold_docs: list[dict[str, Any]] | None = None,
    previous_gold_docs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    previous_index = _index_currency_docs(previous_raw or [])
    grouped = _group_currency_docs(raw)
    previous_grouped = _group_currency_docs(previous_raw or [])
    items = []

    for code in get_supported_currencies(raw):
        docs = grouped.get(code, [])
        if not docs:
            continue

        cbu_doc = next((doc for doc in docs if str(doc.get("bank_name") or "") == "CBU"), None)
        if cbu_doc:
            current_rate = _extract_doc_rate(cbu_doc)
            previous_doc = previous_index.get(("CBU", code))
            previous_rate = _extract_doc_rate(previous_doc) if previous_doc else None
            items.append(
                {
                    "kind": "cbu",
                    "flag": FLAG_BY_CURRENCY.get(code, "💱"),
                    "code": code,
                    "bank": "CBU",
                    "value": format_rate(current_rate),
                    "dir": _ticker_direction(current_rate, previous_rate),
                }
            )

        commercial_docs = [doc for doc in docs if not _is_reference_bank(str(doc.get("bank_name") or ""))]
        previous_commercial_docs = [
            doc
            for doc in previous_grouped.get(code, [])
            if not _is_reference_bank(str(doc.get("bank_name") or ""))
        ]

        best_buy_doc, best_buy = _find_best_doc(commercial_docs, "buy", reverse=True)
        _, previous_best_buy = _find_best_doc(previous_commercial_docs, "buy", reverse=True)
        if best_buy_doc and best_buy is not None:
            items.append(
                {
                    "kind": "best-buy",
                    "flag": FLAG_BY_CURRENCY.get(code, "💱"),
                    "code": code,
                    "bank": _display_bank_name(str(best_buy_doc.get("bank_name") or "")),
                    "value": format_rate(best_buy),
                    "dir": _ticker_direction(best_buy, previous_best_buy),
                }
            )

        best_sell_doc, best_sell = _find_best_doc(commercial_docs, "sell", reverse=False)
        _, previous_best_sell = _find_best_doc(previous_commercial_docs, "sell", reverse=False)
        if best_sell_doc and best_sell is not None:
            items.append(
                {
                    "kind": "best-sell",
                    "flag": FLAG_BY_CURRENCY.get(code, "💱"),
                    "code": code,
                    "bank": _display_bank_name(str(best_sell_doc.get("bank_name") or "")),
                    "value": format_rate(best_sell),
                    "dir": _ticker_direction(best_sell, previous_best_sell),
                }
            )

    for option in build_gold_options(gold_docs, previous_gold_docs):
        items.append(
            {
                "kind": "gold",
                "flag": FLAG_BY_CURRENCY["XAU"],
                "code": option["weight"],
                "bank": "XAU",
                "value": option["price_display"],
                "dir": _ticker_direction(option["price"], option.get("previous_price")),
            }
        )

    return items


def build_history_chart(cbu_history: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any] | None:
    cbu_history = cbu_history or {}
    labels_raw = sorted(
        {
            str(doc.get("date_only") or "")
            for docs in cbu_history.values()
            for doc in docs
            if doc.get("date_only")
        }
    )
    if not labels_raw:
        return None

    series = []
    for currency in HISTORY_CURRENCIES:
        docs = cbu_history.get(currency) or []
        values_by_date = {
            str(doc.get("date_only") or ""): _extract_doc_rate(doc)
            for doc in docs
            if doc.get("date_only")
        }
        series_values = [values_by_date.get(label) for label in labels_raw]
        if not any(value is not None for value in series_values):
            continue

        series.append(
            {
                "key": currency,
                "label": currency,
                "color": CURRENCY_COLORS.get(currency, "#00e5a0"),
                "values": series_values,
            }
        )

    if not series:
        return None

    return {
        "labels": [_format_date(label) or label for label in labels_raw],
        "series": series,
    }


def build_forecast_chart(
    raw: list[dict[str, Any]],
    prediction_docs: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    prediction_docs = prediction_docs or []
    current_cbu_rates = {
        str(doc.get("currency") or "").upper(): _extract_doc_rate(doc)
        for doc in raw
        if str(doc.get("bank_name") or "") == "CBU"
    }

    ordered_predictions = sorted(
        (
            doc
            for doc in prediction_docs
            if str(doc.get("currency") or "").upper() in FORECAST_CURRENCIES
        ),
        key=lambda doc: FORECAST_CURRENCIES.index(str(doc.get("currency") or "").upper()),
    )

    labels = []
    current_values = []
    predicted_values = []
    forecast_date = None

    for doc in ordered_predictions:
        currency = str(doc.get("currency") or "").upper()
        current_rate = current_cbu_rates.get(currency)
        predicted_rate = _to_float(doc.get("predicted_rate"))
        if current_rate is None or predicted_rate is None:
            continue

        labels.append(currency)
        current_values.append(current_rate)
        predicted_values.append(predicted_rate)
        forecast_date = forecast_date or _format_date(str(doc.get("predicted_for_date") or ""))

    if not labels:
        return None

    return {
        "labels": labels,
        "series": [
            {
                "key": "current",
                "label": _("Current CBU rate"),
                "color": "#00e5a0",
                "values": current_values,
            },
            {
                "key": "forecast",
                "label": _("Model forecast"),
                "color": "#f59e0b",
                "values": predicted_values,
            },
        ],
        "forecast_date": forecast_date,
    }


def now_as_of() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")
