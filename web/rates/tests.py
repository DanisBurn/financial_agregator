from django.test import SimpleTestCase, override_settings

from .services import home_page


class HomePageServiceTests(SimpleTestCase):
    def test_build_bank_cards_excludes_cbu_and_renames_xb(self):
        raw = [
            {"bank_name": "CBU", "currency": "USD", "buy": 13000, "sell": 13000, "timestamp": "2026-04-10T10:00:00"},
            {"bank_name": "XB", "currency": "USD", "buy": 12150, "sell": 12200, "timestamp": "2026-04-10T10:00:00"},
            {"bank_name": "Bank B", "currency": "USD", "buy": 12120, "sell": 12170, "timestamp": "2026-04-10T10:00:00"},
        ]
        previous_raw = [
            {"bank_name": "CBU", "currency": "USD", "buy": 12900, "sell": 12900, "timestamp": "2026-04-09T10:00:00"},
            {"bank_name": "XB", "currency": "USD", "buy": 12000, "sell": 12100, "timestamp": "2026-04-09T10:00:00"},
            {"bank_name": "Bank B", "currency": "USD", "buy": 12080, "sell": 12170, "timestamp": "2026-04-09T10:00:00"},
        ]

        cards = home_page.build_bank_cards("USD", raw, previous_raw)

        self.assertEqual([card.name for card in cards], ["Bank B", "XalqBank"])
        best_buy_cards = [card for card in cards if card.is_best_buy]
        best_sell_cards = [card for card in cards if card.is_best_sell]
        self.assertEqual(len(best_buy_cards), 1)
        self.assertEqual(len(best_sell_cards), 1)
        self.assertEqual(best_buy_cards[0].name, "XalqBank")
        self.assertEqual(best_sell_cards[0].name, "Bank B")
        self.assertTrue(all(not card.is_reference for card in cards))

    def test_build_cbu_reference_block_keeps_cbu_separate_from_bank_cards(self):
        raw = [
            {"bank_name": "CBU", "currency": "USD", "buy": 12228.58, "sell": 12228.58, "timestamp": "2026-04-10T10:00:00"},
            {"bank_name": "CBU", "currency": "EUR", "buy": 14282.98, "sell": 14282.98, "timestamp": "2026-04-10T10:00:00"},
            {"bank_name": "CBU", "currency": "RUB", "buy": 155.96, "sell": 155.96, "timestamp": "2026-04-10T10:00:00"},
        ]
        previous_raw = [
            {"bank_name": "CBU", "currency": "USD", "buy": 12200.00, "sell": 12200.00, "timestamp": "2026-04-09T10:00:00"},
            {"bank_name": "CBU", "currency": "EUR", "buy": 14300.00, "sell": 14300.00, "timestamp": "2026-04-09T10:00:00"},
            {"bank_name": "CBU", "currency": "RUB", "buy": 155.10, "sell": 155.10, "timestamp": "2026-04-09T10:00:00"},
        ]

        cbu_reference = home_page.build_cbu_reference_block(raw, "USD", previous_raw)

        self.assertEqual([item["code"] for item in cbu_reference["rates"]], ["USD", "EUR", "RUB"])
        self.assertTrue(cbu_reference["rates"][0]["is_active"])
        self.assertEqual(cbu_reference["rates"][0]["rate_display"], "12 229")

    def test_supported_currencies_ignore_reference_only_rows(self):
        currencies = home_page.get_supported_currencies(
            [
                {"bank_name": "CBU", "currency": "GBP", "buy": 16000},
                {"bank_name": "Bank A", "currency": "USD", "buy": 12000},
            ]
        )

        self.assertEqual(currencies, ["USD"])

    def test_build_gold_creates_selectable_weights_with_derived_one_gram(self):
        gold = home_page.build_gold(
            gold_docs=[
                {"weight": "5 g", "sell": 3600000, "buy": 3400000, "buy_damaged": 3300000},
                {"weight": "10 g", "sell": 7000000, "buy": 6800000, "buy_damaged": 6600000},
            ],
            previous_gold_docs=[
                {"weight": "5 g", "sell": 3500000, "buy": 3300000, "buy_damaged": 3200000},
            ],
        )

        self.assertEqual(gold["selected_weight"], "1 g")
        self.assertEqual(gold["price_display"], "720 000")
        self.assertEqual(gold["buy_display"], "680 000")
        self.assertEqual(gold["buy_damaged_display"], "660 000")
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
                {"bank_name": "CBU", "currency": "USD", "buy": 12228.58, "date_only": "2026-04-10"},
                {"bank_name": "CBU", "currency": "EUR", "buy": 14282.98, "date_only": "2026-04-10"},
                {"bank_name": "CBU", "currency": "RUB", "buy": 155.96},
            ],
            cbu_history={
                "USD": [
                    {"date_only": "2026-04-08", "buy": 12100},
                    {"date_only": "2026-04-09", "buy": 12200},
                    {"date_only": "2026-04-10", "buy": 12228.58},
                ],
                "EUR": [
                    {"date_only": "2026-04-08", "buy": 14100},
                    {"date_only": "2026-04-09", "buy": 14200},
                    {"date_only": "2026-04-10", "buy": 14282.98},
                ],
            },
            prediction_docs=[
                {"currency": "USD", "date_only": "2026-04-10", "predicted_for_date": "2026-04-11", "predicted_rate": 12233.0283},
                {"currency": "EUR", "date_only": "2026-04-10", "predicted_for_date": "2026-04-11", "predicted_rate": 14283.0286},
            ],
        )

        self.assertEqual([tab["key"] for tab in history_chart["tabs"]], ["USD", "EUR", "RUB"])
        self.assertEqual(history_chart["datasets"]["USD"]["labels"], ["08.04", "09.04"])
        self.assertEqual(history_chart["selected_key"], "USD")
        self.assertEqual([tab["key"] for tab in forecast_chart["tabs"]], ["USD", "EUR"])
        self.assertEqual(
            [series["key"] for series in forecast_chart["datasets"]["USD"]["series"]],
            ["current", "forecast"],
        )
        self.assertEqual(
            forecast_chart["datasets"]["USD"]["labels"],
            ["08.04", "09.04", "10.04", "11.04"],
        )
        self.assertEqual(
            forecast_chart["datasets"]["USD"]["series"][0]["values"],
            [12100, 12200, 12228.58, None],
        )
        self.assertEqual(
            forecast_chart["datasets"]["USD"]["series"][1]["values"],
            [12100, 12200, 12228.58, 12233.0283],
        )
        self.assertEqual(forecast_chart["forecast_date"], "08.04.2026 - 11.04.2026")

    @override_settings(ALLOWED_HOSTS=["localhost", "testserver"])
    def test_set_language_redirects_to_translated_url(self):
        response = self.client.post(
            "/i18n/setlang/",
            {"language": "ru", "next": "/en/?c=USD"},
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ru/?c=USD")

    @override_settings(ALLOWED_HOSTS=["localhost", "testserver"])
    def test_home_page_contains_language_links(self):
        response = self.client.get("/en/?c=USD", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn('href="/ru/?c=USD"', content)
        self.assertIn('href="/uz/?c=USD"', content)
