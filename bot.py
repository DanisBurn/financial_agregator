from datetime import datetime, timedelta
from html import escape

import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

from main import load_report, refresh_report


TOKEN = "8765369215:AAEIMdNKNK-21dhzqOAziks_hnXrRH-RQu0"
if not TOKEN:
    raise RuntimeError("Укажите токен бота в переменной TOKEN в файле bot.py")

bot = telebot.TeleBot(TOKEN)

CURRENCIES = ("USD", "EUR", "RUB")
SORT_LABELS = {
    "alpha": "A-Z",
    "asc": "Продажа: по возрастанию",
    "desc": "Продажа: по убыванию",
}
CACHE_TTL = timedelta(minutes=15)

BUTTON_RATES = "Курсы валют банков"
BUTTON_GOLD = "Курс золота"
BUTTON_REFRESH = "Обновить данные"
BUTTON_MAIN_MENU = "Главное меню"
BUTTON_SORT_ALPHA = "A-Z"
BUTTON_SORT_ASC = "По возр."
BUTTON_SORT_DESC = "По убыв."

SORT_BY_BUTTON = {
    BUTTON_SORT_ALPHA: "alpha",
    BUTTON_SORT_ASC: "asc",
    BUTTON_SORT_DESC: "desc",
}

_cached_report = None
_chat_state = {}


def get_chat_state(chat_id):
    return _chat_state.setdefault(
        chat_id,
        {
            "view": "main",
            "currency": "USD",
            "sort": "asc",
        },
    )


def parse_report_timestamp(report):
    timestamp = report.get("timestamp")
    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def report_is_fresh(report):
    timestamp = parse_report_timestamp(report)
    if not timestamp:
        return False

    return datetime.now() - timestamp <= CACHE_TTL


def get_report(force_refresh=False):
    global _cached_report

    saved_report = load_report()

    if not force_refresh and _cached_report and report_is_fresh(_cached_report):
        return _cached_report

    if not force_refresh and saved_report and report_is_fresh(saved_report):
        _cached_report = saved_report
        return _cached_report

    try:
        _cached_report = refresh_report(include_gold=True, verbose=False)
        return _cached_report
    except Exception:
        if _cached_report:
            return _cached_report
        if saved_report:
            _cached_report = saved_report
            return _cached_report
        raise RuntimeError("Не удалось получить данные из парсеров и нет сохранённого отчёта")


def format_number(value, decimals=2):
    if value is None:
        return "нет данных"

    pattern = f"{{:,.{decimals}f}}"
    return pattern.format(value).replace(",", " ")


def normalize_rate(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return number


def get_currency_rows(report, currency_code):
    rows = []

    for bank_name, rates in report.get("banks", {}).items():
        currency_data = rates.get(currency_code)
        if not currency_data:
            continue

        buy = normalize_rate(currency_data.get("buy"))
        sell = normalize_rate(currency_data.get("sell"))
        if buy is None and sell is None:
            continue

        rows.append({
            "bank": bank_name,
            "buy": buy,
            "sell": sell,
        })

    return rows


def sort_currency_rows(rows, sort_mode):
    if sort_mode == "alpha":
        return sorted(rows, key=lambda row: row["bank"].lower())

    if sort_mode == "desc":
        return sorted(
            rows,
            key=lambda row: row["sell"] if row["sell"] is not None else float("-inf"),
            reverse=True,
        )

    return sorted(
        rows,
        key=lambda row: row["sell"] if row["sell"] is not None else float("inf"),
    )


def find_best_rate(rows, field, reverse):
    candidates = [row for row in rows if row[field] is not None]
    if not candidates:
        return None

    selector = max if reverse else min
    return selector(candidates, key=lambda row: row[field])


def format_timestamp(report):
    timestamp = parse_report_timestamp(report)
    if not timestamp:
        return "неизвестно"

    return timestamp.strftime("%d.%m.%Y %H:%M")


def build_keyboard(rows):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in rows:
        keyboard.row(*[KeyboardButton(text) for text in row])
    return keyboard


def build_main_keyboard():
    return build_keyboard([
        [BUTTON_RATES],
        [BUTTON_GOLD],
        [BUTTON_REFRESH],
    ])


def build_rates_keyboard():
    return build_keyboard([
        list(CURRENCIES),
        [BUTTON_SORT_ALPHA, BUTTON_SORT_ASC, BUTTON_SORT_DESC],
        [BUTTON_GOLD, BUTTON_REFRESH],
        [BUTTON_MAIN_MENU],
    ])


def build_gold_keyboard():
    return build_keyboard([
        [BUTTON_RATES, BUTTON_REFRESH],
        [BUTTON_MAIN_MENU],
    ])


def format_main_text(report=None):
    lines = [
        "<b>Финансовый агрегатор</b>",
        "Выберите раздел ниже.",
    ]

    if report:
        lines.append(f"Последнее обновление: {format_timestamp(report)}")
        lines.append(f"Банков в отчёте: {len(report.get('banks', {}))}")

    return "\n".join(lines)


def format_currency_menu_text(chat_id, report):
    state = get_chat_state(chat_id)
    return (
        "<b>Курсы валют банков</b>\n"
        f"Обновлено: {format_timestamp(report)}\n"
        f"Текущая валюта: {state['currency']}\n"
        f"Текущая сортировка: {SORT_LABELS[state['sort']]}\n"
        "Выберите валюту или сортировку с клавиатуры."
    )


def format_currency_text(report, currency_code, sort_mode):
    rows = sort_currency_rows(get_currency_rows(report, currency_code), sort_mode)
    if not rows:
        return f"<b>{currency_code}</b>\nНет данных по выбранной валюте."

    best_sell = find_best_rate(rows, "sell", reverse=False)
    best_buy = find_best_rate(rows, "buy", reverse=True)

    lines = [
        f"<b>{currency_code}: курсы банков</b>",
        f"Обновлено: {format_timestamp(report)}",
        f"Сортировка: {SORT_LABELS[sort_mode]}",
        "",
    ]

    if best_sell:
        lines.append(
            "Самый выгодный для покупки валюты: "
            f"<b>{escape(best_sell['bank'])}</b> "
            f"({format_number(best_sell['sell'])})"
        )

    if best_buy:
        lines.append(
            "Лучший курс покупки банком: "
            f"<b>{escape(best_buy['bank'])}</b> "
            f"({format_number(best_buy['buy'])})"
        )

    lines.append("")

    for index, row in enumerate(rows, start=1):
        lines.append(
            f"{index}. <b>{escape(row['bank'])}</b> | "
            f"Покупка {format_number(row['buy'])} | "
            f"Продажа {format_number(row['sell'])}"
        )

    return "\n".join(lines)


def format_gold_text(report):
    gold = report.get("gold")
    if not gold or not gold.get("items"):
        return "<b>Курс золота</b>\nДанные по золоту сейчас недоступны."

    items = sorted(gold["items"], key=lambda item: item["weight_gram"])
    lines = [
        "<b>Стоимость золотых слитков ЦБ Узбекистана</b>",
        f"Обновлено: {format_timestamp(report)}",
    ]

    if gold.get("date"):
        lines.append(f"Дата ЦБ: {gold['date']}")

    lines.append("")

    for item in items:
        lines.append(
            f"{item['weight_gram']} г | "
            f"Продажа {format_number(item['sell_price_uzs'], 0)} | "
            f"Выкуп {format_number(item['buyback_undamaged_uzs'], 0)} | "
            f"Повреждённый {format_number(item['buyback_damaged_uzs'], 0)}"
        )

    return "\n".join(lines)


def send_message(chat_id, text, reply_markup):
    bot.send_message(chat_id, text, parse_mode="html", reply_markup=reply_markup)


def send_error_message(chat_id, error):
    send_message(
        chat_id,
        f"Ошибка при получении данных:\n<code>{escape(str(error))}</code>",
        build_main_keyboard(),
    )


def show_main_menu(chat_id, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "main"

    report = None
    try:
        report = get_report(force_refresh=force_refresh)
    except RuntimeError:
        pass

    send_message(chat_id, format_main_text(report), build_main_keyboard())


def show_currency_menu(chat_id, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "rates"

    report = get_report(force_refresh=force_refresh)
    send_message(chat_id, format_currency_menu_text(chat_id, report), build_rates_keyboard())


def show_currency_rates(chat_id, currency_code=None, sort_mode=None, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "rates"

    if currency_code:
        currency_code = currency_code.upper()
        if currency_code not in CURRENCIES:
            raise RuntimeError("Неизвестная валюта")
        state["currency"] = currency_code

    if sort_mode in SORT_LABELS:
        state["sort"] = sort_mode

    report = get_report(force_refresh=force_refresh)
    send_message(
        chat_id,
        format_currency_text(report, state["currency"], state["sort"]),
        build_rates_keyboard(),
    )


def show_gold_rates(chat_id, force_refresh=False):
    state = get_chat_state(chat_id)
    state["view"] = "gold"

    report = get_report(force_refresh=force_refresh)
    send_message(chat_id, format_gold_text(report), build_gold_keyboard())


def refresh_current_view(chat_id):
    state = get_chat_state(chat_id)

    if state["view"] == "rates":
        show_currency_rates(chat_id, force_refresh=True)
        return

    if state["view"] == "gold":
        show_gold_rates(chat_id, force_refresh=True)
        return

    show_main_menu(chat_id, force_refresh=True)


@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    try:
        show_main_menu(message.chat.id)
    except Exception as error:
        send_error_message(message.chat.id, error)


@bot.message_handler(commands=["rates"])
def handle_rates(message):
    try:
        show_currency_menu(message.chat.id)
    except Exception as error:
        send_error_message(message.chat.id, error)


@bot.message_handler(commands=["gold"])
def handle_gold(message):
    try:
        show_gold_rates(message.chat.id)
    except Exception as error:
        send_error_message(message.chat.id, error)


@bot.message_handler(commands=["refresh"])
def handle_refresh(message):
    try:
        refresh_current_view(message.chat.id)
    except Exception as error:
        send_error_message(message.chat.id, error)


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = (message.text or "").strip()

    try:
        if text == BUTTON_MAIN_MENU:
            show_main_menu(chat_id)
            return

        if text == BUTTON_RATES:
            show_currency_menu(chat_id)
            return

        if text == BUTTON_GOLD:
            show_gold_rates(chat_id)
            return

        if text == BUTTON_REFRESH:
            refresh_current_view(chat_id)
            return

        if text in CURRENCIES:
            show_currency_rates(chat_id, currency_code=text)
            return

        if text in SORT_BY_BUTTON:
            show_currency_rates(chat_id, sort_mode=SORT_BY_BUTTON[text])
            return

        show_main_menu(chat_id)
    except Exception as error:
        send_error_message(chat_id, error)


def main():
    print("Бот запущен")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
