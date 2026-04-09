from __future__ import annotations

from django.shortcuts import render

from .services import home_page as home_services


def home(request):
    """
    One HTTP request → one response. You may call many helper functions inside
    this view to build context; only the final `render(...)` sends HTML.
    """
    current_currency = home_services.pick_currency(request.GET)

    raw = home_services.load_raw_bank_payloads()
    aggregated = home_services.aggregate_best_rates(raw)

    # Demo dataset to make the UI look like the provided HTML.
    # Replace `build_demo_banks` with your real aggregation output.
    banks = home_services.build_demo_banks(current_currency)

    forecast = home_services.forecast_stub(aggregated)

    context = {
        'aggregated': {**aggregated, 'as_of': aggregated.get('as_of') or home_services.now_as_of()},
        'forecast': forecast,
        'raw_count': len(raw),
        'current_currency': current_currency,
        'currencies': home_services.get_supported_currencies(),
        'banks': banks,
        'compare_rows': home_services.build_compare_rows(banks),
        'stats': home_services.build_stats(banks),
        'gold': home_services.build_gold(),
        'ticker_items': home_services.build_ticker_items(),
    }
    return render(request, 'rates/home.html', context)
