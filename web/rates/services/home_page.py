"""
Replace stubs with your parsers, DB queries, and ML calls.

These functions exist so a single view can stay readable: compose many steps,
then return one HttpResponse at the end.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def load_raw_bank_payloads() -> list[dict[str, Any]]:
    """TODO: fetch or read JSON from banks; return list of decoded dicts."""
    return []


def aggregate_best_rates(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """TODO: compute best buy/sell per currency and gold from `raw`."""
    return {
        'currencies': [],
        'gold': [],
        'as_of': None,
    }


def build_chart_series(aggregated: dict[str, Any]) -> dict[str, Any]:
    """TODO: shape data for Chart.js / ECharts / front-end charts."""
    return {
        'labels': [],
        'buy': [],
        'sell': [],
    }


def forecast_stub(aggregated: dict[str, Any]) -> dict[str, Any] | None:
    """TODO: call your model; return predicted next values or None."""
    return None


# ---- Structures expected by the new template ----

@dataclass(frozen=True)
class BankCard:
    id: str
    name: str
    type: str
    abbr: str
    color: str
    bg: str
    buy: float
    sell: float
    change_pct: float
    is_best_buy: bool

    @property
    def buy_display(self) -> str:
        return format_intlike(self.buy)

    @property
    def sell_display(self) -> str:
        return format_intlike(self.sell)

    @property
    def spread_display(self) -> str:
        return format_intlike(self.sell - self.buy)


def format_intlike(value: float | int) -> str:
    """Formats numeric values like `12 930` for UZ rates UI."""
    n = int(round(float(value)))
    # use thin spaces similar to ru-RU grouping
    return f"{n:,}".replace(",", " ")


def get_supported_currencies() -> list[str]:
    return ['USD', 'EUR', 'RUB', 'CNY', 'GBP', 'JPY', 'KZT', 'TRY', 'AED', 'KRW']


def pick_currency(request_get: dict[str, Any]) -> str:
    cur = (request_get.get('c') or '').upper().strip()
    return cur if cur in set(get_supported_currencies()) else 'USD'


def build_demo_banks(current_currency: str) -> list[BankCard]:
    """
    Temporary demo data so UI looks like your HTML sample.
    Replace this with your real parsed/aggregated bank dataset.
    """
    banks_meta = [
        dict(id='nbu', name='Central Bank', type='State bank', abbr='CB', color='#00e5a0', bg='rgba(0,229,160,0.13)'),
        dict(id='xalq', name='Xalq Bank', type='State bank', abbr='XB', color='#4a9eff', bg='rgba(74,158,255,0.13)'),
        dict(id='asaka', name='Asaka Bank', type='State bank', abbr='AB', color='#9b59b6', bg='rgba(155,89,182,0.13)'),
        dict(id='ipak', name="Ipak Yuli Bank", type='Private bank', abbr='IY', color='#f39c12', bg='rgba(243,156,18,0.13)'),
        dict(id='orient', name="Orient Finans", type='Private bank', abbr='OF', color='#e74c3c', bg='rgba(231,76,60,0.13)'),
        dict(id='hamkor', name="Hamkorbank", type='Private bank', abbr='HB', color='#1abc9c', bg='rgba(26,188,156,0.13)'),
    ]
    base = {
        'USD': (12860, 12940, 0.30),
        'EUR': (14020, 14140, -0.20),
        'RUB': (142, 148, 0.10),
        'CNY': (1760, 1790, 0.40),
        'GBP': (16340, 16500, -0.10),
        'JPY': (85, 88, 0.20),
        'KZT': (26, 28, 0.00),
        'TRY': (380, 395, -0.50),
        'AED': (3490, 3540, 0.10),
        'KRW': (9.1, 9.5, 0.00),
    }
    buy0, sell0, ch0 = base.get(current_currency, base['USD'])

    cards: list[BankCard] = []
    for idx, meta in enumerate(banks_meta):
        # deterministic small variations
        sp = ((idx * 7) + ord(current_currency[0])) % 80 - 30
        buy = buy0 + sp * 0.7
        sell = sell0 + sp * 0.5
        change = round(ch0 + ((idx % 3) - 1) * 0.15, 2)
        cards.append(
            BankCard(
                id=meta['id'],
                name=meta['name'],
                type=meta['type'],
                abbr=meta['abbr'],
                color=meta['color'],
                bg=meta['bg'],
                buy=float(buy),
                sell=float(sell),
                change_pct=float(change),
                is_best_buy=False,
            )
        )

    if cards:
        best_buy = max(c.buy for c in cards)
        cards = [
            BankCard(**{**c.__dict__, 'is_best_buy': (c.buy == best_buy)})
            for c in cards
        ]

    return cards


def build_compare_rows(banks: list[BankCard]) -> list[dict[str, Any]]:
    # keep template simple: dictionaries
    return [
        dict(
            name=b.name,
            type=b.type,
            abbr=b.abbr,
            color=b.color,
            bg=b.bg,
            buy_display=b.buy_display,
            sell_display=b.sell_display,
            spread_display=b.spread_display,
        )
        for b in sorted(banks, key=lambda x: x.buy, reverse=True)
    ]


def build_stats(banks: list[BankCard]) -> dict[str, Any]:
    if not banks:
        return dict(bank_count=0)
    top_buy = max(banks, key=lambda b: b.buy)
    low_sell = min(banks, key=lambda b: b.sell)
    return {
        'bank_count': len(banks),
        'top_buy_rate': top_buy.buy_display,
        'top_buy_bank': top_buy.name,
        'low_sell_rate': low_sell.sell_display,
        'low_sell_bank': low_sell.name,
    }


def build_gold() -> dict[str, Any]:
    # TODO: replace with CBU gold/XAU rate from your feed
    price = 681420
    return {
        'price_display': format_intlike(price),
        'change_pct': 1.2,
    }


def build_ticker_items() -> list[dict[str, Any]]:
    # TODO: replace with real “latest rates” snapshot
    return [
        {'flag': '🇺🇸', 'code': 'USD', 'value': '12 875', 'dir': 'up'},
        {'flag': '🇪🇺', 'code': 'EUR', 'value': '14 080', 'dir': 'down'},
        {'flag': '🇷🇺', 'code': 'RUB', 'value': '144', 'dir': 'up'},
        {'flag': '🇨🇳', 'code': 'CNY', 'value': '1 770', 'dir': 'up'},
        {'flag': '🇬🇧', 'code': 'GBP', 'value': '16 420', 'dir': 'down'},
        {'flag': '🇯🇵', 'code': 'JPY', 'value': '86', 'dir': 'up'},
        {'flag': '🥇', 'code': 'XAU', 'value': '681 420/gr', 'dir': 'up'},
    ]


def now_as_of() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M')
