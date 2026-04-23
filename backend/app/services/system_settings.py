from __future__ import annotations

import json

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.models import SettingsResponse, SettingsSaveResponse, SettingsUpdateRequest
from app.services.oauth_connections import read_store, write_store


def get_default_api_base_url(settings: Settings) -> str:
    return f"{settings.public_backend_url.rstrip('/')}{settings.api_prefix}"


def _as_string(value: object, fallback: str) -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _as_int(value: object, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _as_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return fallback


def _as_choice(value: object, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback


def _as_time_string(value: object, fallback: str) -> str:
    normalized = str(value or "").strip()
    if len(normalized) != 5 or normalized[2] != ":":
        return fallback
    hour, minute = normalized.split(":", maxsplit=1)
    if not (hour.isdigit() and minute.isdigit()):
        return fallback
    if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
        return fallback
    return f"{int(hour):02d}:{int(minute):02d}"


def _as_days_of_week(value: object, fallback: list[int]) -> list[int]:
    if not isinstance(value, list):
        return fallback

    normalized_days = sorted(
        {
            int(item)
            for item in value
            if isinstance(item, int) and 0 <= item <= 6
        }
    )
    return normalized_days or fallback


def load_system_settings_payload(base_settings: Settings) -> dict[str, object]:
    raw_payload = read_store(base_settings).get("systemSettings", {})

    return {
        "apiBaseUrl": _as_string(raw_payload.get("apiBaseUrl"), get_default_api_base_url(base_settings)),
        "ollamaBaseUrl": _as_string(raw_payload.get("ollamaBaseUrl"), base_settings.ollama_base_url),
        "ollamaModel": _as_string(raw_payload.get("ollamaModel"), base_settings.ollama_model),
        "spreadsheetId": _as_string(raw_payload.get("spreadsheetId"), base_settings.google_sheet_id),
        "worksheet": _as_string(raw_payload.get("worksheet"), base_settings.google_sheet_worksheet),
        "syncMode": _as_choice(raw_payload.get("syncMode"), {"interval", "scheduled"}, base_settings.sync_mode),
        "syncStartTime": _as_time_string(raw_payload.get("syncStartTime"), base_settings.sync_start_time),
        "syncIntervalMinutes": _as_int(raw_payload.get("syncIntervalMinutes"), base_settings.sync_interval_minutes),
        "syncDaysOfWeek": _as_days_of_week(raw_payload.get("syncDaysOfWeek"), base_settings.get_sync_days_of_week()),
        "syncLoopEnabled": _as_bool(raw_payload.get("syncLoopEnabled"), base_settings.sync_loop_enabled),
        "syncWebsiteEnabled": _as_bool(raw_payload.get("syncWebsiteEnabled"), base_settings.sync_website_enabled),
        "syncSocialEnabled": _as_bool(raw_payload.get("syncSocialEnabled"), base_settings.sync_social_enabled),
        "autoSync": _as_bool(raw_payload.get("autoSync"), base_settings.auto_sync),
        "autoRecommend": _as_bool(raw_payload.get("autoRecommend"), base_settings.auto_recommend),
        "autoSchedule": _as_bool(raw_payload.get("autoSchedule"), base_settings.auto_schedule),
    }


def build_settings_response(base_settings: Settings) -> SettingsResponse:
    payload = load_system_settings_payload(base_settings)
    return SettingsResponse(**payload)


def apply_runtime_settings(base_settings: Settings) -> Settings:
    payload = load_system_settings_payload(base_settings)
    return base_settings.model_copy(
        update={
            "ollama_base_url": payload["ollamaBaseUrl"],
            "ollama_model": payload["ollamaModel"],
            "google_sheet_id": payload["spreadsheetId"],
            "google_sheet_worksheet": payload["worksheet"],
            "sync_mode": payload["syncMode"],
            "sync_start_time": payload["syncStartTime"],
            "sync_interval_minutes": payload["syncIntervalMinutes"],
            "sync_days_of_week_json": json.dumps(payload["syncDaysOfWeek"]),
            "sync_loop_enabled": payload["syncLoopEnabled"],
            "sync_website_enabled": payload["syncWebsiteEnabled"],
            "sync_social_enabled": payload["syncSocialEnabled"],
            "auto_sync": payload["autoSync"],
            "auto_recommend": payload["autoRecommend"],
            "auto_schedule": payload["autoSchedule"],
        }
    )


def get_runtime_settings(base_settings: Settings = Depends(get_settings)) -> Settings:
    return apply_runtime_settings(base_settings)


def save_system_settings(base_settings: Settings, payload: SettingsUpdateRequest) -> SettingsSaveResponse:
    normalized_days_of_week = sorted({day for day in payload.syncDaysOfWeek if 0 <= day <= 6}) or [0, 1, 2, 3, 4, 5, 6]
    normalized_payload = {
        "apiBaseUrl": payload.apiBaseUrl.strip().rstrip("/"),
        "ollamaBaseUrl": payload.ollamaBaseUrl.strip().rstrip("/"),
        "ollamaModel": payload.ollamaModel.strip(),
        "spreadsheetId": payload.spreadsheetId.strip(),
        "worksheet": payload.worksheet.strip(),
        "syncMode": payload.syncMode,
        "syncStartTime": payload.syncStartTime,
        "syncIntervalMinutes": payload.syncIntervalMinutes,
        "syncDaysOfWeek": normalized_days_of_week,
        "syncLoopEnabled": payload.syncLoopEnabled,
        "syncWebsiteEnabled": payload.syncWebsiteEnabled,
        "syncSocialEnabled": payload.syncSocialEnabled,
        "autoSync": payload.autoSync,
        "autoRecommend": payload.autoRecommend,
        "autoSchedule": payload.autoSchedule,
    }

    store = read_store(base_settings)
    store["systemSettings"] = normalized_payload
    write_store(base_settings, store)

    return SettingsSaveResponse(
        status="success",
        message="Đã lưu cài đặt hệ thống.",
        settings=SettingsResponse(**normalized_payload),
    )
