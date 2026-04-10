from __future__ import annotations

from django.shortcuts import render

from .services import home_page as home_services


def home(request):
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

    context = {
        'aggregated': {**aggregated, 'as_of': aggregated.get('as_of') or home_services.now_as_of()},
        'raw_count': len(raw),
        'current_currency': current_currency,
        'currencies': currencies,
        'banks': banks,
        'compare_rows': home_services.build_compare_rows(banks),
        'stats': home_services.build_stats(banks),
        'gold': gold,
        'history_chart': history_chart,
        'forecast_chart': forecast_chart,
        'cbu_reference': cbu_reference,
        'ticker_items': home_services.build_ticker_items(
            raw=raw,
            previous_raw=snapshot.previous_currency_docs,
            gold_docs=snapshot.current_gold_docs,
            previous_gold_docs=snapshot.previous_gold_docs,
        ),
    }
    return render(request, 'rates/home.html', context)
