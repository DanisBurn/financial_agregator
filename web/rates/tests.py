from django.test import SimpleTestCase

from .services import home_page


class HomePageServiceTests(SimpleTestCase):
    def test_build_bank_cards_skips_cbu_for_best_buy_and_renames_xb(self):
        raw = [
            {"bank_name": "CBU", "currency": "USD", "buy": 13000, "sell": 13000, "timestamp": "2026-04-10T10:00:00"},
            {"bank_name": "XB", "currency": "USD", "buy": 12150, "sell": 12200, "timestamp": "2026-04-10T10:00:00"},
            {"bank_name": "Bank B", "currency": "USD", "buy": 12120, "sell": 12190, "timestamp": "2026-04-10T10:00:00"},
        ]
        previous_raw = [
            {"bank_name": "CBU", "currency": "USD", "buy": 12900, "sell": 12900, "timestamp": "2026-04-09T10:00:00"},
            {"bank_name": "XB", "currency": "USD", "buy": 12000, "sell": 12100, "timestamp": "2026-04-09T10:00:00"},
            {"bank_name": "Bank B", "currency": "USD", "buy": 12080, "sell": 12170, "timestamp": "2026-04-09T10:00:00"},
        ]

        cards = home_page.build_bank_cards("USD", raw, previous_raw)

        self.assertEqual([card.name for card in cards], ["Bank B", "CBU", "XalqBank"])
        best_buy_cards = [card for card in cards if card.is_best_buy]
        self.assertEqual(len(best_buy_cards), 1)
        self.assertEqual(best_buy_cards[0].name, "XalqBank")
        self.assertFalse(next(card for card in cards if card.name == "CBU").is_best_buy)

    def test_build_gold_creates_selectable_weights_with_derived_one_gram(self):
        gold = home_page.build_gold(
            gold_docs=[
                {"weight": "5 g", "sell": 3600000},
                {"weight": "10 g", "sell": 7000000},
            ],
            previous_gold_docs=[
                {"weight": "5 g", "sell": 3500000},
            ],
        )

        self.assertEqual(gold["selected_weight"], "1 g")
        self.assertEqual(gold["price_display"], "720 000")
        self.assertEqual([option["weight"] for option in gold["options"]], ["1 g", "5 g", "10 g"])
        self.assertGreater(gold["change_pct"], 0)

    def test_build_history_and_forecast_chart_shapes(self):
        history_chart = home_page.build_history_chart(
            {
                "USD": [
                    {"date_only": "2026-04-08", "buy": 12100},
                    {"date_only": "2026-04-09", "buy": 12200},
                ],
                "EUR": [
                    {"date_only": "2026-04-08", "buy": 14100},
                    {"date_only": "2026-04-09", "buy": 14200},
                ],
                "RUB": [
                    {"date_only": "2026-04-08", "buy": 150},
                    {"date_only": "2026-04-09", "buy": 151},
                ],
            }
        )
        forecast_chart = home_page.build_forecast_chart(
            raw=[
                {"bank_name": "CBU", "currency": "USD", "buy": 12228.58},
                {"bank_name": "CBU", "currency": "EUR", "buy": 14282.98},
                {"bank_name": "CBU", "currency": "RUB", "buy": 155.96},
            ],
            prediction_docs=[
                {"currency": "USD", "predicted_for_date": "2026-04-10", "predicted_rate": 12233.0283},
                {"currency": "EUR", "predicted_for_date": "2026-04-10", "predicted_rate": 14283.0286},
            ],
        )

        self.assertEqual(history_chart["labels"], ["08.04.2026", "09.04.2026"])
        self.assertEqual([series["key"] for series in history_chart["series"]], ["USD", "EUR", "RUB"])
        self.assertEqual(forecast_chart["labels"], ["USD", "EUR"])
        self.assertEqual([series["key"] for series in forecast_chart["series"]], ["current", "forecast"])
        self.assertEqual(forecast_chart["forecast_date"], "10.04.2026")
