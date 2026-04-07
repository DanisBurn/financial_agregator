import re
import requests
import datetime
from bs4 import BeautifulSoup

URL = "https://nbu.uz/ru/fizicheskim-litsam-kursy-valyut"

def clean_price(price_str: str) -> float:
   digits = re.sub(r"[^\d]", "", price_str) 
   return float(digits)
   
def parse_gold_prices(url: str = URL) -> dict:
   headers = {
      "User-Agent": "Mozilla/5.0"
   }
   response = requests.get(url, headers=headers, timeout=30)
   response.raise_for_status()

   soup = BeautifulSoup(response.text, "html.parser")
   text = soup.get_text("\n", strip=True)
   date_match = re.search(r"Курс\sвалют\s\b(\d{2}\.\d{2}.\d{4})\b", text)

   if date_match:
        page_date = date_match.group(1)
   else:
        page_date = None

   print(date_match)

   print(text)

   pattern = re.compile(
      r"(USD|EUR|RUB|GBP|JPY)\s*\n\s*=\s*(\d+\.\d+)",
      re.IGNORECASE
   )

   items = {}
   for currency, value in pattern.findall(text):
      items[currency] = float(value)

   return {
      "date": page_date,
      "url": url,
      "items" : items,
   }


if __name__ == "__main__":
   data = parse_gold_prices()
   print(data)

