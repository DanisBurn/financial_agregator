from dataclasses import dataclass
from datetime import datetime, timedelta
from html import escape
import os
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import telebot
from telebot.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

try:
    from telebot.types import MenuButtonWebApp
except ImportError:  # pragma: no cover - depends on telebot version
    MenuButtonWebApp = None

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(root_dir, "web")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(os.path.join(root_dir, ".env"))

from web.rates.services.home_page import (
    DISPLAY_BANK_NAMES,
    FLAG_BY_CURRENCY,
    GOLD_WEIGHT_ORDER,
    REFERENCE_BANKS,
    format_rate,
    get_supported_currencies,
    load_dashboard_snapshot,
)


TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
MINIAPP_URL = (os.getenv("MINIAPP_URL") or "").strip()
DEFAULT_MINIAPP_LANGUAGE = (os.getenv("MINIAPP_DEFAULT_LANGUAGE") or "ru").strip().lower()

if not TOKEN:
    raise RuntimeError("Укажите TELEGRAM_BOT_TOKEN или BOT_TOKEN в переменных окружения")

bot = telebot.TeleBot(TOKEN)

CURRENCIES = ("USD", "EUR", "RUB")
SUPPORTED_LANGUAGES = {"ru", "uz", "en"}
SORT_LABELS = {
    "alpha": "по алфавиту",
    "buy_desc": "лучший курс покупки банком",
    "sell_asc": "лучший курс продажи банком",
}
CACHE_TTL = timedelta(minutes=2)

BUTTON_OPEN_MINIAPP = "📱 Открыть Mini App"
BUTTON_RATES = "💱 Курсы валют"
BUTTON_GOLD = "🥇 Золото"
BUTTON_REFRESH = "🔄 Обновить из базы"
BUTTON_MAIN_MENU = "🏠 Главное меню"
BUTTON_SORT_ALPHA = "🔤 A-Z"
BUTTON_SORT_BUY = "📈 Лучший buy"
BUTTON_SORT_SELL = "📉 Лучший sell"

CURRENCY_BUTTONS = {
    "🇺🇸 USD": "USD",
    "🇪🇺 EUR": "EUR",
    "🇷🇺 RUB": "RUB",
}
SORT_BY_BUTTON = {
    BUTTON_SORT_ALPHA: "alpha",
    BUTTON_SORT_BUY: "buy_desc",
    BUTTON_SORT_SELL: "sell_asc",
}

_cached_snapshot = None
_cached_snapshot_loaded_at = None
_chat_state = {}


@dataclass
class CurrencyRow:
    bank: str
    buy: float | None
    sell: float | None
    previous_buy: float | None
    previous_sell: float | None
    is_best_buy: bool = False
    is_best_sell: bool = False


@dataclass
class GoldRow:
    weight: str
    grams: int
    sell: float | None
    buy: float | None
    buy_damaged: float | None
    previous_sell: float | None
    previous_buy: float | None
    previous_buy_damaged: float | None
    is_derived: bool = False


def get_chat_state(chat_id):
    return _chat_state.setdefault(
        chat_id,
        {
            "view": "main",
            "currency": "USD",
            "sort": "sell_asc",
        },
    )


def normalize_language_code(raw_language: str | None) -> str:
    language = str(raw_language or DEFAULT_MINIAPP_LANGUAGE or "ru").split("-")[0].lower()
    return language if language in SUPPORTED_LANGUAGES else "ru"


def build_miniapp_launch_url(language_code: str | None = None) -> str:
    if not MINIAPP_URL:
        return ""

    parts = urlsplit(MINIAPP_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("lang", normalize_language_code(language_code))
    query.setdefault("source", "telegram-bot")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def build_miniapp_keyboard(language_code: str | None = None):
    launch_url = build_miniapp_launch_url(language_code)
    if not launch_url:
        return None

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text=BUTTON_OPEN_MINIAPP,
            web_app=WebAppInfo(url=launch_url),
        )
    )
    return keyboard


def _to_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _snapshot_has_data(snapshot) -> bool:
    return bool(
        snapshot.current_currency_docs
        or snapshot.current_gold_docs
        or snapshot.prediction_docs
    )


def _snapshot_updated_at(snapshot) -> datetime | None:
    timestamps = []
    for doc in (
        list(snapshot.current_currency_docs)
        + list(snapshot.current_gold_docs)
        + list(snapshot.prediction_docs)
    ):
        parsed = _parse_datetime(str(doc.get("timestamp") or ""))
        if parsed:
            timestamps.append(parsed)

    if timestamps:
        return max(timestamps)

    if snapshot.current_date:
        return _parse_datetime(f"{snapshot.current_date}T00:00:00")

    return None


def _format_snapshot_timestamp(snapshot) -> str:
    updated_at = _snapshot_updated_at(snapshot)
    if updated_at is None:
        return "неизвестно"
    return updated_at.strftime("%d.%m.%Y %H:%M")


def get_snapshot(force_refresh=False):
    global _cached_snapshot, _cached_snapshot_loaded_at

    now = datetime.now()
    if (
        not force_refresh
        and _cached_snapshot is not None
        and _cached_snapshot_loaded_at is not None
        and now - _cached_snapshot_loaded_at <= CACHE_TTL
    ):
        return _cached_snapshot

    snapshot = load_dashboard_snapshot()
    if _snapshot_has_data(snapshot):
        _cached_snapshot = snapshot
        _cached_snapshot_loaded_at = now
        return snapshot

    if _cached_snapshot is not None:
        return _cached_snapshot

    raise RuntimeError(
        "В MongoDB пока нет актуальных данных. Проверьте, что kursuz-updater с main_server.py запущен."
    )


def _display_bank_name(bank_name: str) -> str:
    return DISPLAY_BANK_NAMES.get(bank_name, bank_name)


def _extract_doc_rate(doc) -> float | None:
    return _to_float(doc.get("buy")) or _to_float(doc.get("sell")) or _to_float(doc.get("rate"))


def _currency_indexes(snapshot):
    current_index = {}
    previous_index = {}

    for doc in snapshot.current_currency_docs:
        bank = str(doc.get("bank_name") or "").strip()
        currency = str(doc.get("currency") or "").upper().strip()
        if bank and currency:
            current_index[(bank, currency)] = doc

    for doc in snapshot.previous_currency_docs:
        bank = str(doc.get("bank_name") or "").strip()
        currency = str(doc.get("currency") or "").upper().strip()
        if bank and currency:
            previous_index[(bank, currency)] = doc

    return current_index, previous_index


def _gold_indexes(snapshot):
    current_index = {}
    previous_index = {}

    for doc in snapshot.current_gold_docs:
        weight = str(doc.get("weight") or "").strip()
        if weight:
            current_index[weight] = doc

    for doc in snapshot.previous_gold_docs:
        weight = str(doc.get("weight") or "").strip()
        if weight:
            previous_index[weight] = doc

    return current_index, previous_index


def _parse_weight_grams(weight: str) -> int | None:
    digits = "".join(ch for ch in weight if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _build_currency_rows(snapshot, currency_code: str) -> list[CurrencyRow]:
    _, previous_index = _currency_indexes(snapshot)
    rows = []

    for doc in snapshot.current_currency_docs:
        currency = str(doc.get("currency") or "").upper().strip()
        raw_bank_name = str(doc.get("bank_name") or "").strip()
        if currency != currency_code or not raw_bank_name or raw_bank_name in REFERENCE_BANKS:
            continue

        buy = _to_float(doc.get("buy"))
        sell = _to_float(doc.get("sell"))
        if buy is None and sell is None:
            continue

        previous_doc = previous_index.get((raw_bank_name, currency_code))
        rows.append(
            CurrencyRow(
                bank=_display_bank_name(raw_bank_name),
                buy=buy,
                sell=sell,
                previous_buy=_to_float(previous_doc.get("buy")) if previous_doc else None,
                previous_sell=_to_float(previous_doc.get("sell")) if previous_doc else None,
            )
        )

    best_buy = max((row.buy for row in rows if row.buy is not None), default=None)
    best_sell = min((row.sell for row in rows if row.sell is not None), default=None)
    for row in rows:
        row.is_best_buy = best_buy is not None and row.buy == best_buy
        row.is_best_sell = best_sell is not None and row.sell == best_sell

    return rows


def _sort_currency_rows(rows: list[CurrencyRow], sort_mode: str) -> list[CurrencyRow]:
    if sort_mode == "alpha":
        return sorted(rows, key=lambda row: row.bank.lower())
    if sort_mode == "buy_desc":
        return sorted(
            rows,
            key=lambda row: (
                row.buy is None,
                -(row.buy or 0),
                row.bank.lower(),
            ),
        )
    return sorted(
        rows,
        key=lambda row: (
            row.sell is None,
            row.sell or float("inf"),
            row.bank.lower(),
        ),
    )


def _find_cbu_doc(snapshot, currency_code: str):
    current_index, previous_index = _currency_indexes(snapshot)
    current_doc = current_index.get(("CBU", currency_code))
    previous_doc = previous_index.get(("CBU", currency_code))
    return current_doc, previous_doc


def _format_signed_delta(delta: float) -> str:
    sign = "+" if delta > 0 else "-"
    return f"{sign}{format_rate(abs(delta))}"


def _trend_text(current: float | None, previous: float | None) -> str:
    if current is None:
        return ""
    if previous is None:
        return "🆕"

    delta = current - previous
    if abs(delta) < 0.005:
        return "➖ 0"
    if delta > 0:
        return f"📈 {_format_signed_delta(delta)}"
    return f"📉 {_format_signed_delta(delta)}"


def _format_metric(label: str, current: float | None, previous: float | None) -> str:
    suffix = _trend_text(current, previous)
    if suffix:
        return f"{label} <b>{format_rate(current)}</b> {suffix}"
    return f"{label} <b>{format_rate(current)}</b>"


def _currency_highlights(snapshot, currency_code: str) -> tuple[CurrencyRow | None, CurrencyRow | None]:
    rows = _build_currency_rows(snapshot, currency_code)
    best_buy = max((row for row in rows if row.buy is not None), key=lambda row: row.buy or 0, default=None)
    best_sell = min(
        (row for row in rows if row.sell is not None),
        key=lambda row: row.sell or float("inf"),
        default=None,
    )
    return best_buy, best_sell


def _build_gold_rows(snapshot) -> list[GoldRow]:
    current_index, previous_index = _gold_indexes(snapshot)
    actual_rows = {}

    for weight, doc in current_index.items():
        grams = _parse_weight_grams(weight)
        if not grams:
            continue

        previous_doc = previous_index.get(weight)
        actual_rows[weight] = GoldRow(
            weight=weight,
            grams=grams,
            sell=_to_float(doc.get("sell")),
            buy=_to_float(doc.get("buy")),
            buy_damaged=_to_float(doc.get("buy_damaged")),
            previous_sell=_to_float(previous_doc.get("sell")) if previous_doc else None,
            previous_buy=_to_float(previous_doc.get("buy")) if previous_doc else None,
            previous_buy_damaged=_to_float(previous_doc.get("buy_damaged")) if previous_doc else None,
            is_derived=False,
        )

    if not actual_rows:
        return []

    rows = []
    smallest = min(actual_rows.values(), key=lambda row: row.grams)
    rows.append(
        GoldRow(
            weight="1 g",
            grams=1,
            sell=(smallest.sell / smallest.grams) if smallest.sell is not None else None,
            buy=(smallest.buy / smallest.grams) if smallest.buy is not None else None,
            buy_damaged=(smallest.buy_damaged / smallest.grams) if smallest.buy_damaged is not None else None,
            previous_sell=(smallest.previous_sell / smallest.grams) if smallest.previous_sell is not None else None,
            previous_buy=(smallest.previous_buy / smallest.grams) if smallest.previous_buy is not None else None,
            previous_buy_damaged=(
                smallest.previous_buy_damaged / smallest.grams
                if smallest.previous_buy_damaged is not None
                else None
            ),
            is_derived=True,
        )
    )

    for weight in GOLD_WEIGHT_ORDER:
        if weight == "1 g":
            continue
        row = actual_rows.get(weight)
        if row is not None:
            rows.append(row)

    extra_rows = sorted(
        (
            row
            for weight, row in actual_rows.items()
            if weight not in set(GOLD_WEIGHT_ORDER)
        ),
        key=lambda row: row.grams,
    )
    rows.extend(extra_rows)
    return rows


def _build_highlight_lines(snapshot) -> list[str]:
    lines = []
    supported = [code for code in CURRENCIES if code in set(get_supported_currencies(snapshot.current_currency_docs))]
    for currency_code in supported:
        best_buy, best_sell = _currency_highlights(snapshot, currency_code)
        if not best_buy and not best_sell:
            continue

        parts = [f"{FLAG_BY_CURRENCY.get(currency_code, '💱')} <b>{currency_code}</b>"]
        if best_sell:
            parts.append(f"sell: <b>{escape(best_sell.bank)}</b> {format_rate(best_sell.sell)}")
        if best_buy:
            parts.append(f"buy: <b>{escape(best_buy.bank)}</b> {format_rate(best_buy.buy)}")
        lines.append(" | ".join(parts))
    return lines


def build_keyboard(rows):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in rows:
        keyboard.row(*row)
    return keyboard


def build_main_keyboard(language_code: str | None = None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    launch_url = build_miniapp_launch_url(language_code)
    if launch_url:
        keyboard.row(KeyboardButton(text=BUTTON_OPEN_MINIAPP, web_app=WebAppInfo(url=launch_url)))
    keyboard.row(KeyboardButton(BUTTON_RATES), KeyboardButton(BUTTON_GOLD))
    keyboard.row(KeyboardButton(BUTTON_REFRESH))
    return keyboard


def build_rates_keyboard(language_code: str | None = None):
    keyboard = build_main_keyboard(language_code)
    keyboard.row(*(KeyboardButton(text) for text in CURRENCY_BUTTONS))
    keyboard.row(
        KeyboardButton(BUTTON_SORT_ALPHA),
        KeyboardButton(BUTTON_SORT_BUY),
        KeyboardButton(BUTTON_SORT_SELL),
    )
    keyboard.row(KeyboardButton(BUTTON_MAIN_MENU))
    return keyboard


def build_gold_keyboard(language_code: str | None = None):
    keyboard = build_main_keyboard(language_code)
    keyboard.row(KeyboardButton(BUTTON_MAIN_MENU))
    return keyboard


def format_main_text(snapshot=None):
    lines = [
        "<b>KursUZ Bot</b>",
        "📡 Источник данных: MongoDB",
        "🔄 Сервер обновляет данные через <code>main_server.py</code> раз в час.",
    ]

    if snapshot is not None:
        lines.append(f"⏱ Обновлено в базе: {_format_snapshot_timestamp(snapshot)}")
        lines.append(f"🏦 Банков в базе: {len(_build_currency_rows(snapshot, 'USD'))}")
        gold_rows = _build_gold_rows(snapshot)
        if gold_rows:
            lines.append(f"🥇 Весов золота: {len(gold_rows)}")
        highlight_lines = _build_highlight_lines(snapshot)
        if highlight_lines:
            lines.append("")
            lines.append("<b>Лучшие курсы сейчас</b>")
            lines.extend(highlight_lines)

    return "\n".join(lines)


def format_currency_menu_text(chat_id, snapshot):
    state = get_chat_state(chat_id)
    return (
        "<b>💱 Курсы валют банков</b>\n"
        f"⏱ Обновлено: {_format_snapshot_timestamp(snapshot)}\n"
        f"💵 Текущая валюта: {state['currency']}\n"
        f"↕️ Сортировка: {SORT_LABELS[state['sort']]}\n"
        "🏛 Курс CBU показывается отдельно и не участвует в выборе лучших коммерческих курсов."
    )


def format_currency_text(snapshot, currency_code, sort_mode):
    rows = _sort_currency_rows(_build_currency_rows(snapshot, currency_code), sort_mode)
    current_cbu_doc, previous_cbu_doc = _find_cbu_doc(snapshot, currency_code)
    current_cbu_rate = _extract_doc_rate(current_cbu_doc) if current_cbu_doc else None
    previous_cbu_rate = _extract_doc_rate(previous_cbu_doc) if previous_cbu_doc else None

    if not rows and current_cbu_rate is None:
        return f"<b>{currency_code}</b>\nДанные по выбранной валюте пока недоступны."

    best_buy, best_sell = _currency_highlights(snapshot, currency_code)
    lines = [
        f"<b>{FLAG_BY_CURRENCY.get(currency_code, '💱')} {currency_code}: курсы банков</b>",
        f"⏱ Обновлено: {_format_snapshot_timestamp(snapshot)}",
        f"↕️ Сортировка: {SORT_LABELS[sort_mode]}",
        "",
    ]

    if current_cbu_rate is not None:
        lines.append(
            "🏛 CBU: "
            f"<b>{format_rate(current_cbu_rate)}</b> {_trend_text(current_cbu_rate, previous_cbu_rate)}"
        )

    if best_sell is not None:
        lines.append(
            "🟢 Лучший курс продажи банком: "
            f"<b>{escape(best_sell.bank)}</b> {format_rate(best_sell.sell)}"
        )

    if best_buy is not None:
        lines.append(
            "🟢 Лучший курс покупки банком: "
            f"<b>{escape(best_buy.bank)}</b> {format_rate(best_buy.buy)}"
        )

    if rows:
        lines.append("")

    for index, row in enumerate(rows, start=1):
        badges = []
        if row.is_best_buy:
            badges.append("🏆 buy")
        if row.is_best_sell:
            badges.append("🏆 sell")
        badge_suffix = f" {' '.join(badges)}" if badges else ""
        lines.append(
            f"{index}. <b>{escape(row.bank)}</b>{badge_suffix} | "
            f"{_format_metric('Покупка', row.buy, row.previous_buy)} | "
            f"{_format_metric('Продажа', row.sell, row.previous_sell)}"
        )

    return "\n".join(lines)


def format_gold_text(snapshot):
    rows = _build_gold_rows(snapshot)
    if not rows:
        return "<b>🥇 Курс золота</b>\nДанные по золоту сейчас недоступны."

    lines = [
        "<b>🥇 Золотые слитки ЦБ Узбекистана</b>",
        f"⏱ Обновлено: {_format_snapshot_timestamp(snapshot)}",
        "📈 и 📉 показывают изменение к предыдущему дню.",
        "",
    ]

    for row in rows:
        label = f"{row.weight}{' (расчётно)' if row.is_derived else ''}"
        lines.append(
            f"{label} | "
            f"{_format_metric('Продажа', row.sell, row.previous_sell)} | "
            f"{_format_metric('Выкуп', row.buy, row.previous_buy)} | "
            f"{_format_metric('Поврежд.', row.buy_damaged, row.previous_buy_damaged)}"
        )

    return "\n".join(lines)


def send_message(chat_id, text, reply_markup, inline_markup=None):
    bot.send_message(chat_id, text, parse_mode="html", reply_markup=reply_markup)
    if inline_markup is not None:
        bot.send_message(chat_id, "📱 Открыть приложение:", reply_markup=inline_markup)


def send_error_message(chat_id, error, language_code: str | None = None):
    send_message(
        chat_id,
        f"⚠️ Ошибка при получении данных:\n<code>{escape(str(error))}</code>",
        build_main_keyboard(language_code),
    )


def show_main_menu(chat_id, language_code: str | None = None, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "main"

    snapshot = None
    try:
        snapshot = get_snapshot(force_refresh=force_refresh)
    except RuntimeError:
        pass

    send_message(
        chat_id,
        format_main_text(snapshot),
        build_main_keyboard(language_code),
        inline_markup=build_miniapp_keyboard(language_code),
    )


def show_currency_menu(chat_id, language_code: str | None = None, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "rates"

    snapshot = get_snapshot(force_refresh=force_refresh)
    send_message(chat_id, format_currency_menu_text(chat_id, snapshot), build_rates_keyboard(language_code))


def show_currency_rates(chat_id, language_code: str | None = None, currency_code=None, sort_mode=None, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "rates"

    if currency_code:
        currency_code = currency_code.upper()
        if currency_code not in CURRENCIES:
            raise RuntimeError("Неизвестная валюта")
        state["currency"] = currency_code

    if sort_mode in SORT_LABELS:
        state["sort"] = sort_mode

    snapshot = get_snapshot(force_refresh=force_refresh)
    send_message(
        chat_id,
        format_currency_text(snapshot, state["currency"], state["sort"]),
        build_rates_keyboard(language_code),
    )


def show_gold_rates(chat_id, language_code: str | None = None, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "gold"

    snapshot = get_snapshot(force_refresh=force_refresh)
    send_message(chat_id, format_gold_text(snapshot), build_gold_keyboard(language_code))


def refresh_current_view(chat_id, language_code: str | None = None):
    state = get_chat_state(chat_id)

    if state["view"] == "rates":
        show_currency_rates(chat_id, language_code=language_code, force_refresh=True)
        return

    if state["view"] == "gold":
        show_gold_rates(chat_id, language_code=language_code, force_refresh=True)
        return

    show_main_menu(chat_id, language_code=language_code, force_refresh=True)


def configure_bot_ui():
    try:
        bot.set_my_commands(
            [
                BotCommand("start", "Открыть главное меню"),
                BotCommand("app", "Открыть Mini App"),
                BotCommand("rates", "Показать курсы валют из базы"),
                BotCommand("gold", "Показать золото из базы"),
                BotCommand("refresh", "Перечитать данные из MongoDB"),
            ]
        )
    except Exception:
        pass

    if MINIAPP_URL and MenuButtonWebApp is not None:
        try:
            bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Mini App",
                    web_app=WebAppInfo(url=build_miniapp_launch_url(DEFAULT_MINIAPP_LANGUAGE)),
                )
            )
        except Exception:
            pass


@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    language_code = normalize_language_code(getattr(message.from_user, "language_code", None))
    try:
        show_main_menu(message.chat.id, language_code=language_code)
    except Exception as error:
        send_error_message(message.chat.id, error, language_code=language_code)


@bot.message_handler(commands=["app"])
def handle_app(message):
    language_code = normalize_language_code(getattr(message.from_user, "language_code", None))
    keyboard = build_miniapp_keyboard(language_code)
    if keyboard is None:
        send_message(
            message.chat.id,
            "Mini App URL не настроен. Укажите MINIAPP_URL в переменных окружения.",
            build_main_keyboard(language_code),
        )
        return

    bot.send_message(
        message.chat.id,
        "Нажмите кнопку ниже, чтобы открыть Mini App.",
        reply_markup=keyboard,
    )


@bot.message_handler(commands=["rates"])
def handle_rates(message):
    language_code = normalize_language_code(getattr(message.from_user, "language_code", None))
    try:
        show_currency_menu(message.chat.id, language_code=language_code)
    except Exception as error:
        send_error_message(message.chat.id, error, language_code=language_code)


@bot.message_handler(commands=["gold"])
def handle_gold(message):
    language_code = normalize_language_code(getattr(message.from_user, "language_code", None))
    try:
        show_gold_rates(message.chat.id, language_code=language_code)
    except Exception as error:
        send_error_message(message.chat.id, error, language_code=language_code)


@bot.message_handler(commands=["refresh"])
def handle_refresh(message):
    language_code = normalize_language_code(getattr(message.from_user, "language_code", None))
    try:
        refresh_current_view(message.chat.id, language_code=language_code)
    except Exception as error:
        send_error_message(message.chat.id, error, language_code=language_code)


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = (message.text or "").strip()
    language_code = normalize_language_code(getattr(message.from_user, "language_code", None))

    try:
        if text == BUTTON_MAIN_MENU:
            show_main_menu(chat_id, language_code=language_code)
            return

        if text == BUTTON_RATES:
            show_currency_menu(chat_id, language_code=language_code)
            return

        if text == BUTTON_GOLD:
            show_gold_rates(chat_id, language_code=language_code)
            return

        if text == BUTTON_REFRESH:
            refresh_current_view(chat_id, language_code=language_code)
            return

        if text == BUTTON_OPEN_MINIAPP:
            handle_app(message)
            return

        if text in CURRENCY_BUTTONS:
            show_currency_rates(chat_id, language_code=language_code, currency_code=CURRENCY_BUTTONS[text])
            return

        if text in CURRENCIES:
            show_currency_rates(chat_id, language_code=language_code, currency_code=text)
            return

        if text in SORT_BY_BUTTON:
            show_currency_rates(chat_id, language_code=language_code, sort_mode=SORT_BY_BUTTON[text])
            return

        show_main_menu(chat_id, language_code=language_code)
    except Exception as error:
        send_error_message(chat_id, error, language_code=language_code)


def main():
    configure_bot_ui()
    print("Бот запущен")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
