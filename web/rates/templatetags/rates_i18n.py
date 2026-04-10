from __future__ import annotations

from django import template
from django.urls import translate_url


register = template.Library()


@register.simple_tag(takes_context=True)
def switch_language_url(context, language_code: str) -> str:
    request = context.get("request")
    current_url = request.get_full_path() if request else "/"
    return translate_url(current_url, language_code)
