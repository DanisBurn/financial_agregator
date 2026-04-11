from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl

from django.conf import settings


SUPPORTED_LANGUAGES = {code for code, _label in settings.LANGUAGES}


@dataclass(frozen=True)
class TelegramMiniAppAuth:
    user: dict[str, Any]
    auth_date: datetime
    query_id: str | None
    raw: dict[str, Any]


def get_bot_token() -> str:
    return (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("BOT_TOKEN")
        or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        or ""
    ).strip()


def get_bot_username() -> str:
    return (
        os.getenv("TELEGRAM_BOT_USERNAME")
        or getattr(settings, "TELEGRAM_BOT_USERNAME", "")
        or ""
    ).strip()


def get_miniapp_url() -> str:
    configured = (
        os.getenv("MINIAPP_URL")
        or getattr(settings, "MINIAPP_URL", "")
        or ""
    ).strip()
    return configured


def _parse_json_field(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError):
        return raw_value


def parse_init_data(init_data: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, value in parse_qsl(init_data, keep_blank_values=True):
        if key in {"user", "receiver", "chat"}:
            parsed[key] = _parse_json_field(value)
        else:
            parsed[key] = value
    return parsed


def _build_data_check_string(parsed: dict[str, Any]) -> str:
    rows = []
    for key in sorted(key for key in parsed if key != "hash"):
        value = parsed[key]
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            serialized = str(value)
        rows.append(f"{key}={serialized}")
    return "\n".join(rows)


def _build_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()


def validate_init_data(init_data: str, max_age_seconds: int | None = None) -> TelegramMiniAppAuth:
    if not init_data:
        raise ValueError("Telegram init data is empty")

    bot_token = get_bot_token()
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    parsed = parse_init_data(init_data)
    provided_hash = str(parsed.get("hash") or "").strip()
    if not provided_hash:
        raise ValueError("Telegram init data hash is missing")

    data_check_string = _build_data_check_string(parsed)
    secret = _build_secret_key(bot_token)
    expected_hash = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, provided_hash):
        raise ValueError("Telegram init data signature is invalid")

    auth_date_raw = parsed.get("auth_date")
    try:
        auth_timestamp = int(str(auth_date_raw))
    except (TypeError, ValueError):
        raise ValueError("Telegram auth_date is invalid") from None

    auth_date = datetime.fromtimestamp(auth_timestamp, tz=timezone.utc)
    if max_age_seconds:
        age = time.time() - auth_timestamp
        if age > max_age_seconds:
            raise ValueError("Telegram init data has expired")

    user = parsed.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        raise ValueError("Telegram user payload is missing")

    return TelegramMiniAppAuth(
        user=user,
        auth_date=auth_date,
        query_id=str(parsed.get("query_id") or "").strip() or None,
        raw=parsed,
    )


def normalize_telegram_user(user: dict[str, Any]) -> dict[str, Any]:
    first_name = str(user.get("first_name") or "").strip()
    last_name = str(user.get("last_name") or "").strip()
    username = str(user.get("username") or "").strip()
    language_code = str(user.get("language_code") or "").strip().lower()
    display_name = " ".join(part for part in [first_name, last_name] if part).strip() or username or "Telegram user"
    initials_source = display_name.split()
    initials = "".join(part[:1] for part in initials_source[:2]).upper() or "TG"

    return {
        "telegram_id": int(user["id"]),
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "display_name": display_name,
        "language_code": language_code if language_code in SUPPORTED_LANGUAGES else "",
        "is_premium": bool(user.get("is_premium")),
        "allows_write_to_pm": bool(user.get("allows_write_to_pm")),
        "photo_url": str(user.get("photo_url") or "").strip(),
        "initials": initials,
    }
