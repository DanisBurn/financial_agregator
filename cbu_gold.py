import re
import requests
from bs4 import BeautifulSoup

URL = "https://cbu.uz/ru/banknotes-coins/gold-bars/prices/"

def clean_price(price_str: str) -> int:
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits)

def parse_gold_prices(url: str = URL) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)

    if date_match:
        page_date = date_match.group(1)
    else:
        page_date = None

    print(date_match)

    pattern = re.compile(
        r"(\d+)\s*грамм\s*"
        r"([\d\s]+)\s*сум\s*"
        r"([\d\s]+)\s*сум\s*"
        r"([\d\s]+)\s*сум",
        re.IGNORECASE
    )

    items = []
    for weight, sell, buy_good, buy_damaged in pattern.findall(text):
        items.append({
            "weight_gram": int(weight),
            "sell_price_uzs": clean_price(sell),
            "buyback_undamaged_uzs": clean_price(buy_good),
            "buyback_damaged_uzs": clean_price(buy_damaged),
        })

    return {
        "date": page_date,
        "url": url,
        "items": items,
    }

if __name__ == "__main__":
    data = parse_gold_prices()
    print(data)
