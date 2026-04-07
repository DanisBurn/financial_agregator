import re
import requests
import telebot
from bs4 import BeautifulSoup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8765369215:AAEIMdNKNK-21dhzqOAziks_hnXrRH-RQu0"
bot = telebot.TeleBot(TOKEN)

CBU_URL = "https://cbu.uz/ru/"

CURRENCY_FLAGS = {
    "USD": "🇺🇸 USD",
    "EUR": "🇪🇺 EUR",
    "RUB": "🇷🇺 RUB",
    "GBP": "🇬🇧 GBP",
    "JPY": "🇯🇵 JPY",
}

# ─── Парсер курсов валют ────────────────────────────────────────────────────

def parse_currency_rates() -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(CBU_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    date_match = re.search(r"с\s\b(\d{2}\.\d{2}.\d{4})\b", text)
    page_date = date_match.group(1) if date_match else "—"

    pattern = re.compile(
        r"(USD|EUR|RUB|GBP|JPY)\s*\n\s*=\s*(\d+\.\d+)",
        re.IGNORECASE
    )

    items = {}
    for currency, value in pattern.findall(text):
        items[currency.upper()] = float(value)

    return {"date": page_date, "items": items}


def format_rates(data: dict) -> str:
    lines = [f"💱 <b>Курс валют ЦБ Узбекистана</b>", f"📅 {data['date']}\n"]
    for code, label in CURRENCY_FLAGS.items():
        rate = data["items"].get(code)
        if rate:
            lines.append(f"{label}  →  <b>{rate:,.2f}</b> сум")
    return "\n".join(lines)


# ─── Клавиатуры ─────────────────────────────────────────────────────────────

def main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💱 Все курсы", callback_data="all"),
        InlineKeyboardButton("🔄 Обновить", callback_data="all"),
    )
    kb.add(
        InlineKeyboardButton("🇺🇸 USD", callback_data="USD"),
        InlineKeyboardButton("🇪🇺 EUR", callback_data="EUR"),
        InlineKeyboardButton("🇷🇺 RUB", callback_data="RUB"),
        InlineKeyboardButton("🇬🇧 GBP", callback_data="GBP"),
    )
    kb.add(
        InlineKeyboardButton("🌐 cbu.uz", url="https://cbu.uz/ru/")
    )
    return kb


# ─── Хэндлеры ───────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "hello"])
def cmd_start(message):
    name = message.from_user.first_name or ""
    bot.send_message(
        message.chat.id,
        f"👋 Привет, <b>{name}</b>!\n\nЯ показываю актуальный курс валют по данным ЦБ Узбекистана.",
        parse_mode="html",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["rates", "курс"])
def cmd_rates(message):
    msg = bot.send_message(message.chat.id, "⏳ Загружаю курсы...", reply_markup=main_keyboard())
    try:
        data = parse_currency_rates()
        bot.edit_message_text(
            format_rates(data),
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode="html",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", chat_id=message.chat.id, message_id=msg.message_id)


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "<b>Доступные команды:</b>\n"
        "/start — начать\n"
        "/rates — курс всех валют\n"
        "/help — помощь",
        parse_mode="html",
        reply_markup=main_keyboard(),
    )


@bot.message_handler()
def cmd_text(message):
    text = message.text.lower()
    if text in ("привет", "hello", "hi"):
        bot.send_message(
            message.chat.id,
            f"👋 Привет, <b>{message.from_user.first_name}</b>!",
            parse_mode="html",
            reply_markup=main_keyboard(),
        )
    elif text == "id":
        bot.reply_to(message, f"🆔 {message.from_user.id}")
    else:
        bot.send_message(
            message.chat.id,
            "Нажми кнопку ниже, чтобы узнать курс валют 👇",
            reply_markup=main_keyboard(),
        )


# ─── Callback-и кнопок ──────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    bot.answer_callback_query(call.id, "⏳ Загружаю...")
    try:
        data = parse_currency_rates()

        if call.data == "all":
            text = format_rates(data)

        else:
            code = call.data
            rate = data["items"].get(code)
            label = CURRENCY_FLAGS.get(code, code)
            if rate:
                text = (
                    f"{label}\n"
                    f"📅 {data['date']}\n\n"
                    f"1 {code} = <b>{rate:,.2f}</b> сум"
                )
            else:
                text = f"❌ Курс {code} не найден"

        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="html",
            reply_markup=main_keyboard(),
        )

    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка при получении данных:\n{e}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=main_keyboard(),
        )


# ─── Запуск ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)