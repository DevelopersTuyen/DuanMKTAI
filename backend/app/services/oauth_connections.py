from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.models import OAuthActionResponse, OAuthProviderStatus, OAuthProvidersResponse, OAuthStartResponse
from app.services.google_website import ensure_sheet_exists, get_sheet_values, load_service_account_credentials

BASE_DIR = Path(__file__).resolve().parents[2]
OAUTH_SHEET_HEADER = ["record_type", "record_key", "provider", "payload_json", "updated_at"]
STORE_CACHE_TTL_SECONDS = 5
_STORE_CACHE: dict[str, tuple[datetime, dict[str, Any]]] = {}


@dataclass(frozen=True)
class ProviderDefinition:
    slug: str
    label: str
    worksheet: str
    auth_type: str
    auth_note: str
    supports_refresh: bool
    supports_auto_refresh: bool
    authorization_url: str
    token_url: str
    scopes: list[str]
    client_id: str | None
    client_secret: str | None


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat()


def as_iso_expiry(expires_in: int | str | None) -> str | None:
    try:
        seconds = int(expires_in or 0)
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return (utc_now() + timedelta(seconds=seconds)).isoformat()


def parse_scopes(value: str | list[str] | None) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    normalized = value.replace(",", " ")
    return [item.strip() for item in normalized.split() if item.strip()]


def storage_path(settings: Settings) -> Path:
    configured = Path(settings.oauth_storage_file)
    if configured.is_absolute():
        path = configured
    else:
        path = BASE_DIR / configured
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def can_use_google_sheet_store(settings: Settings) -> bool:
    return bool(
        settings.google_sheet_id
        and settings.oauth_keys_worksheet
        and (
            (settings.google_service_account_json and settings.google_service_account_json.strip())
            or (settings.google_service_account_file and settings.google_service_account_file.strip())
        )
    )


def cache_key(settings: Settings) -> str:
    return f"{settings.google_sheet_id}:{settings.oauth_keys_worksheet}"


def normalize_sheet_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    normalized = payload or {}
    normalized.setdefault("connections", {})
    normalized.setdefault("states", {})
    return normalized


def read_sheet_store(settings: Settings) -> dict[str, Any]:
    credentials = load_service_account_credentials(settings)
    worksheet = settings.oauth_keys_worksheet
    ensure_sheet_exists(settings, credentials, worksheet)
    rows = get_sheet_values(settings, credentials, worksheet)
    if not rows:
        return {"connections": {}, "states": {}}

    header = rows[0]
    index = {column: position for position, column in enumerate(header)}
    payload: dict[str, Any] = {"connections": {}, "states": {}}

    for row in rows[1:]:
        record_type = row[index["record_type"]] if index.get("record_type") is not None and index["record_type"] < len(row) else ""
        record_key = row[index["record_key"]] if index.get("record_key") is not None and index["record_key"] < len(row) else ""
        raw_json = row[index["payload_json"]] if index.get("payload_json") is not None and index["payload_json"] < len(row) else "{}"
        if not record_type or not record_key:
            continue
        try:
            record_payload = json.loads(raw_json or "{}")
        except json.JSONDecodeError:
            continue
        if record_type == "connection":
            payload["connections"][record_key] = record_payload
        elif record_type == "state":
            payload["states"][record_key] = record_payload

    return payload


def write_sheet_store(settings: Settings, payload: dict[str, Any]) -> None:
    credentials = load_service_account_credentials(settings)
    worksheet = settings.oauth_keys_worksheet
    ensure_sheet_exists(settings, credentials, worksheet)

    rows: list[list[str]] = [OAUTH_SHEET_HEADER]
    for provider, connection in sorted(payload.get("connections", {}).items()):
        rows.append(
            [
                "connection",
                provider,
                provider,
                json.dumps(connection, ensure_ascii=False),
                iso_now(),
            ]
        )

    for state, state_payload in sorted(payload.get("states", {}).items()):
        rows.append(
            [
                "state",
                state,
                str(state_payload.get("provider", "")),
                json.dumps(state_payload, ensure_ascii=False),
                iso_now(),
            ]
        )

    from googleapiclient.discovery import build

    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    service.spreadsheets().values().clear(
        spreadsheetId=settings.google_sheet_id,
        range=f"{worksheet}!A:Z",
        body={},
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=settings.google_sheet_id,
        range=f"{worksheet}!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()


def read_file_store(settings: Settings) -> dict[str, Any]:
    path = storage_path(settings)
    if not path.exists():
        return {"connections": {}, "states": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"connections": {}, "states": {}}
    return normalize_sheet_payload(payload)


def write_file_store(settings: Settings, payload: dict[str, Any]) -> None:
    path = storage_path(settings)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_store(settings: Settings) -> dict[str, Any]:
    if can_use_google_sheet_store(settings):
        key = cache_key(settings)
        cached = _STORE_CACHE.get(key)
        if cached and (utc_now() - cached[0]).total_seconds() < STORE_CACHE_TTL_SECONDS:
            return normalize_sheet_payload(json.loads(json.dumps(cached[1])))
        payload = normalize_sheet_payload(read_sheet_store(settings))
        _STORE_CACHE[key] = (utc_now(), json.loads(json.dumps(payload)))
        return payload
    return read_file_store(settings)


def write_store(settings: Settings, payload: dict[str, Any]) -> None:
    normalized = normalize_sheet_payload(payload)
    if can_use_google_sheet_store(settings):
        write_sheet_store(settings, normalized)
        _STORE_CACHE[cache_key(settings)] = (utc_now(), json.loads(json.dumps(normalized)))
        return
    write_file_store(settings, normalized)


def get_provider_definitions(settings: Settings) -> dict[str, ProviderDefinition]:
    return {
        "google-youtube": ProviderDefinition(
            slug="google-youtube",
            label="Google / YouTube",
            worksheet=settings.youtube_worksheet,
            auth_type="OAuth 2.0 + refresh token",
            auth_note="Dùng để kết nối kênh YouTube bằng tài khoản Google, lấy refresh token để backend tự làm mới access token.",
            supports_refresh=True,
            supports_auto_refresh=True,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/youtube.readonly"],
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
        ),
        "tiktok": ProviderDefinition(
            slug="tiktok",
            label="TikTok",
            worksheet=settings.tiktok_worksheet,
            auth_type="OAuth v2 + refresh token",
            auth_note="TikTok cấp access token và refresh token. Backend sẽ lưu và tự làm mới token khi gần hết hạn.",
            supports_refresh=True,
            supports_auto_refresh=True,
            authorization_url="https://www.tiktok.com/v2/auth/authorize/",
            token_url="https://open.tiktokapis.com/v2/oauth/token/",
            scopes=["user.info.basic", "video.list"],
            client_id=settings.tiktok_client_key,
            client_secret=settings.tiktok_client_secret,
        ),
        "facebook": ProviderDefinition(
            slug="facebook",
            label="Facebook",
            worksheet=settings.facebook_worksheet,
            auth_type="OAuth 2.0 + long-lived page token",
            auth_note="Facebook không dùng refresh token chuẩn như Google. Backend sẽ đổi sang long-lived user token rồi lấy page token để đồng bộ.",
            supports_refresh=False,
            supports_auto_refresh=False,
            authorization_url="https://www.facebook.com/v24.0/dialog/oauth",
            token_url="https://graph.facebook.com/v24.0/oauth/access_token",
            scopes=["pages_show_list", "pages_read_engagement"],
            client_id=settings.facebook_app_id,
            client_secret=settings.facebook_app_secret,
        ),
        "linkedin": ProviderDefinition(
            slug="linkedin",
            label="LinkedIn",
            worksheet=settings.linkedin_worksheet,
            auth_type="3-legged OAuth",
            auth_note="LinkedIn dùng 3-legged OAuth. Một số app có refresh token, một số app chỉ làm mới bằng cách cấp quyền lại.",
            supports_refresh=True,
            supports_auto_refresh=True,
            authorization_url="https://www.linkedin.com/oauth/v2/authorization",
            token_url="https://www.linkedin.com/oauth/v2/accessToken",
            scopes=["r_organization_social", "rw_organization_admin"],
            client_id=settings.linkedin_client_id,
            client_secret=settings.linkedin_client_secret,
        ),
    }


def get_provider_definition(provider: str, settings: Settings) -> ProviderDefinition:
    definitions = get_provider_definitions(settings)
    if provider not in definitions:
        raise ValueError(f"Nhà cung cấp OAuth không hợp lệ: {provider}")
    return definitions[provider]


def get_connection(settings: Settings, provider: str) -> dict[str, Any] | None:
    return read_store(settings).get("connections", {}).get(provider)


def save_connection(settings: Settings, provider: str, connection: dict[str, Any]) -> None:
    store = read_store(settings)
    store["connections"][provider] = connection
    write_store(settings, store)


def remove_connection(settings: Settings, provider: str) -> None:
    store = read_store(settings)
    store.get("connections", {}).pop(provider, None)
    write_store(settings, store)


def create_state(settings: Settings, provider: str, return_url: str) -> str:
    store = read_store(settings)
    state = secrets.token_urlsafe(24)
    store["states"][state] = {
        "provider": provider,
        "createdAt": iso_now(),
        "returnUrl": return_url,
    }
    write_store(settings, store)
    return state


def consume_state(settings: Settings, provider: str, state: str) -> dict[str, Any]:
    store = read_store(settings)
    payload = store.get("states", {}).pop(state, None)
    write_store(settings, store)
    if not payload or payload.get("provider") != provider:
        raise ValueError("State OAuth không hợp lệ hoặc đã hết hạn.")
    return payload


def get_callback_url(settings: Settings, provider: str) -> str:
    return f"{settings.public_backend_url.rstrip('/')}{settings.api_prefix}/oauth/{provider}/callback"


def get_default_return_url(settings: Settings) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/integrations"


def build_frontend_redirect_url(base_url: str, provider: str, status: str, message: str) -> str:
    separator = "&" if "?" in base_url else "?"
    query = urlencode(
        {
            "oauth_provider": provider,
            "oauth_status": status,
            "oauth_message": message,
        }
    )
    return f"{base_url}{separator}{query}"


def is_connection_expired(connection: dict[str, Any] | None) -> bool:
    if not connection:
        return False
    expires_at = connection.get("expiresAt")
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    return expiry <= utc_now() + timedelta(minutes=2)


async def get_google_youtube_profile(access_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        userinfo_response = await client.get("https://openidconnect.googleapis.com/v1/userinfo", headers=headers)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

        channels_response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers=headers,
            params={"part": "snippet,statistics,contentDetails", "mine": "true"},
        )
        channels_response.raise_for_status()
        channels = channels_response.json().get("items", [])

    return {
        "accountLabel": userinfo.get("email") or userinfo.get("name") or "Google account",
        "accountId": userinfo.get("sub"),
        "metadata": {
            "email": userinfo.get("email"),
            "name": userinfo.get("name"),
            "channelIds": [str(item.get("id")) for item in channels if item.get("id")],
            "channels": [
                {
                    "id": str(item.get("id", "")),
                    "title": str(item.get("snippet", {}).get("title", "")),
                }
                for item in channels
            ],
        },
    }


async def get_tiktok_profile(access_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://open.tiktokapis.com/v2/user/info/",
            params={"fields": "open_id,display_name,profile_deep_link,avatar_url,bio_description"},
            headers=headers,
        )
        response.raise_for_status()
    user = response.json().get("data", {}).get("user", {})
    return {
        "accountLabel": user.get("display_name") or "Tài khoản TikTok",
        "accountId": user.get("open_id"),
        "metadata": {
            "openId": user.get("open_id"),
            "profileDeepLink": user.get("profile_deep_link"),
            "displayName": user.get("display_name"),
        },
    }


async def get_facebook_profile(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        me_response = await client.get(
            "https://graph.facebook.com/v24.0/me",
            params={"fields": "id,name", "access_token": access_token},
        )
        me_response.raise_for_status()
        me = me_response.json()

        pages_response = await client.get(
            "https://graph.facebook.com/v24.0/me/accounts",
            params={"fields": "id,name,access_token", "access_token": access_token},
        )
        pages_response.raise_for_status()
        pages = pages_response.json().get("data", [])

    return {
        "accountLabel": me.get("name") or "Tài khoản Facebook",
        "accountId": me.get("id"),
        "metadata": {
            "pageIds": [str(page.get("id")) for page in pages if page.get("id")],
            "pages": [
                {
                    "id": str(page.get("id", "")),
                    "name": str(page.get("name", "")),
                    "accessToken": str(page.get("access_token", "")),
                }
                for page in pages
            ],
        },
    }


async def get_linkedin_profile(access_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    profile: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("https://api.linkedin.com/v2/me", headers=headers)
        if response.status_code < 400:
            profile = response.json()

    localized_name = " ".join(
        part
        for part in [
            str(profile.get("localizedFirstName", "")).strip(),
            str(profile.get("localizedLastName", "")).strip(),
        ]
        if part
    ).strip()

    return {
        "accountLabel": localized_name or "Tài khoản LinkedIn",
        "accountId": profile.get("id"),
        "metadata": {},
    }


async def exchange_google_youtube_code(settings: Settings, code: str, redirect_uri: str) -> dict[str, Any]:
    definition = get_provider_definition("google-youtube", settings)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            definition.token_url,
            data={
                "code": code,
                "client_id": definition.client_id or "",
                "client_secret": definition.client_secret or "",
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
    payload = response.json()
    profile = await get_google_youtube_profile(payload["access_token"])
    return {
        "accessToken": payload.get("access_token"),
        "refreshToken": payload.get("refresh_token"),
        "tokenType": payload.get("token_type"),
        "scopes": parse_scopes(payload.get("scope")),
        "expiresAt": as_iso_expiry(payload.get("expires_in")),
        **profile,
    }


async def exchange_tiktok_code(settings: Settings, code: str, redirect_uri: str) -> dict[str, Any]:
    definition = get_provider_definition("tiktok", settings)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            definition.token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": definition.client_id or "",
                "client_secret": definition.client_secret or "",
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        response.raise_for_status()
    data = response.json().get("data", response.json())
    profile = await get_tiktok_profile(data["access_token"])
    return {
        "accessToken": data.get("access_token"),
        "refreshToken": data.get("refresh_token"),
        "tokenType": "Bearer",
        "scopes": parse_scopes(data.get("scope")),
        "expiresAt": as_iso_expiry(data.get("expires_in")),
        "refreshExpiresAt": as_iso_expiry(data.get("refresh_expires_in")),
        **profile,
    }


async def exchange_facebook_code(settings: Settings, code: str, redirect_uri: str) -> dict[str, Any]:
    definition = get_provider_definition("facebook", settings)
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_response = await client.get(
            definition.token_url,
            params={
                "client_id": definition.client_id or "",
                "client_secret": definition.client_secret or "",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        token_response.raise_for_status()
        short_payload = token_response.json()
        user_access_token = short_payload.get("access_token")

        long_response = await client.get(
            definition.token_url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": definition.client_id or "",
                "client_secret": definition.client_secret or "",
                "fb_exchange_token": user_access_token,
            },
        )
        long_response.raise_for_status()
        long_payload = long_response.json()

    access_token = long_payload.get("access_token") or user_access_token
    profile = await get_facebook_profile(access_token)
    return {
        "accessToken": access_token,
        "tokenType": "Bearer",
        "scopes": definition.scopes,
        "expiresAt": as_iso_expiry(long_payload.get("expires_in") or short_payload.get("expires_in")),
        **profile,
    }


async def exchange_linkedin_code(settings: Settings, code: str, redirect_uri: str) -> dict[str, Any]:
    definition = get_provider_definition("linkedin", settings)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            definition.token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": definition.client_id or "",
                "client_secret": definition.client_secret or "",
            },
        )
        response.raise_for_status()
    payload = response.json()
    profile = await get_linkedin_profile(payload["access_token"])
    return {
        "accessToken": payload.get("access_token"),
        "refreshToken": payload.get("refresh_token"),
        "tokenType": "Bearer",
        "scopes": parse_scopes(payload.get("scope")),
        "expiresAt": as_iso_expiry(payload.get("expires_in")),
        "refreshExpiresAt": as_iso_expiry(payload.get("refresh_token_expires_in")),
        **profile,
    }


async def exchange_code_for_tokens(provider: str, settings: Settings, code: str, redirect_uri: str) -> dict[str, Any]:
    if provider == "google-youtube":
        return await exchange_google_youtube_code(settings, code, redirect_uri)
    if provider == "tiktok":
        return await exchange_tiktok_code(settings, code, redirect_uri)
    if provider == "facebook":
        return await exchange_facebook_code(settings, code, redirect_uri)
    if provider == "linkedin":
        return await exchange_linkedin_code(settings, code, redirect_uri)
    raise ValueError(f"Nhà cung cấp OAuth không hợp lệ: {provider}")


async def refresh_connection(provider: str, settings: Settings) -> dict[str, Any]:
    definition = get_provider_definition(provider, settings)
    connection = get_connection(settings, provider)
    if not connection:
        raise ValueError(f"{definition.label} chưa được kết nối.")
    refresh_token = connection.get("refreshToken")

    if provider == "facebook":
        raise ValueError("Facebook không hỗ trợ refresh token chuẩn. Hãy kết nối lại nếu token hết hạn.")

    if not refresh_token:
        raise ValueError(f"{definition.label} chưa có refresh token để làm mới.")

    if provider == "google-youtube":
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                definition.token_url,
                data={
                    "client_id": definition.client_id or "",
                    "client_secret": definition.client_secret or "",
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
        payload = response.json()
        connection["accessToken"] = payload.get("access_token")
        connection["expiresAt"] = as_iso_expiry(payload.get("expires_in"))
        connection["updatedAt"] = iso_now()
        connection.setdefault("scopes", parse_scopes(payload.get("scope")) or connection.get("scopes", []))
        save_connection(settings, provider, connection)
        return connection

    if provider == "tiktok":
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                definition.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": definition.client_id or "",
                    "client_secret": definition.client_secret or "",
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
        payload = response.json().get("data", response.json())
        connection["accessToken"] = payload.get("access_token")
        connection["refreshToken"] = payload.get("refresh_token") or refresh_token
        connection["expiresAt"] = as_iso_expiry(payload.get("expires_in"))
        connection["refreshExpiresAt"] = as_iso_expiry(payload.get("refresh_expires_in"))
        connection["updatedAt"] = iso_now()
        save_connection(settings, provider, connection)
        return connection

    if provider == "linkedin":
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                definition.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": definition.client_id or "",
                    "client_secret": definition.client_secret or "",
                },
            )
            response.raise_for_status()
        payload = response.json()
        connection["accessToken"] = payload.get("access_token")
        connection["refreshToken"] = payload.get("refresh_token") or refresh_token
        connection["expiresAt"] = as_iso_expiry(payload.get("expires_in"))
        connection["refreshExpiresAt"] = as_iso_expiry(payload.get("refresh_token_expires_in"))
        connection["updatedAt"] = iso_now()
        save_connection(settings, provider, connection)
        return connection

    raise ValueError(f"Chưa hỗ trợ làm mới token cho {definition.label}.")


async def ensure_provider_access_token(provider: str, settings: Settings) -> str | None:
    connection = get_connection(settings, provider)
    if not connection:
        return None
    if not is_connection_expired(connection):
        return connection.get("accessToken")
    definition = get_provider_definition(provider, settings)
    if definition.supports_auto_refresh and connection.get("refreshToken"):
        refreshed = await refresh_connection(provider, settings)
        return refreshed.get("accessToken")
    return None


def get_provider_metadata(settings: Settings, provider: str) -> dict[str, Any]:
    return (get_connection(settings, provider) or {}).get("metadata", {})


def get_connected_asset_ids(settings: Settings, provider: str) -> list[str]:
    metadata = get_provider_metadata(settings, provider)
    if provider == "google-youtube":
        return [str(item) for item in metadata.get("channelIds", []) if str(item).strip()]
    if provider == "facebook":
        return [str(item) for item in metadata.get("pageIds", []) if str(item).strip()]
    if provider == "tiktok":
        return [str(metadata.get("openId", "")).strip()] if str(metadata.get("openId", "")).strip() else []
    return []


def get_facebook_page_tokens(settings: Settings) -> dict[str, str]:
    metadata = get_provider_metadata(settings, "facebook")
    page_tokens: dict[str, str] = {}
    for page in metadata.get("pages", []):
        page_id = str(page.get("id", "")).strip()
        access_token = str(page.get("accessToken", "")).strip()
        if page_id and access_token:
            page_tokens[page_id] = access_token
    return page_tokens


def get_oauth_provider_statuses(settings: Settings) -> OAuthProvidersResponse:
    definitions = get_provider_definitions(settings)
    statuses: list[OAuthProviderStatus] = []

    for slug, definition in definitions.items():
        connection = get_connection(settings, slug)
        connected = bool(connection)
        connectable = bool(definition.client_id and definition.client_secret)
        expired = is_connection_expired(connection)

        if slug == "google-youtube":
            configured_assets = len(get_connected_asset_ids(settings, slug) or settings.get_youtube_channel_ids())
            asset_summary = f"{configured_assets} kênh YouTube"
        elif slug == "facebook":
            configured_assets = len(get_connected_asset_ids(settings, slug) or settings.get_facebook_page_ids())
            asset_summary = f"{configured_assets} trang Facebook"
        elif slug == "linkedin":
            configured_assets = len(settings.get_linkedin_organization_ids())
            asset_summary = f"{configured_assets} trang doanh nghiệp"
        else:
            configured_assets = len(get_connected_asset_ids(settings, slug))
            asset_summary = "1 hồ sơ TikTok" if configured_assets else "Chưa có hồ sơ TikTok"

        warnings: list[str] = []
        if not connectable:
            warnings.append("Thiếu client ID hoặc client secret.")
        if connected and expired and not definition.supports_auto_refresh:
            warnings.append("Token hiện tại có thể đã hết hạn, cần kết nối lại.")
        if slug == "linkedin" and connected and configured_assets == 0:
            warnings.append("Đã có token LinkedIn nhưng chưa khai báo organization ID để đồng bộ bài đăng.")
        if slug == "facebook" and connected and configured_assets == 0:
            warnings.append("Đã cấp quyền Facebook nhưng chưa lấy được page ID từ tài khoản này.")

        if connected and not expired:
            status = "Đã kết nối"
            status_class = "status-live"
        elif connected and expired:
            status = "Cần làm mới"
            status_class = "status-warning"
        elif connectable:
            status = "Sẵn sàng kết nối"
            status_class = "status-draft"
        else:
            status = "Thiếu cấu hình"
            status_class = "status-warning"

        ready = connected and (configured_assets > 0 or slug == "tiktok") and (not expired or definition.supports_auto_refresh)
        statuses.append(
            OAuthProviderStatus(
                provider=slug,
                label=definition.label,
                worksheet=definition.worksheet,
                connected=connected,
                ready=ready,
                connectable=connectable,
                supportsRefresh=definition.supports_refresh and bool(connection and connection.get("refreshToken")),
                supportsAutoRefresh=definition.supports_auto_refresh,
                status=status,
                statusClass=status_class,
                authType=definition.auth_type,
                accountLabel=connection.get("accountLabel") if connection else None,
                accountId=connection.get("accountId") if connection else None,
                configuredAssets=configured_assets,
                assetSummary=asset_summary,
                connectedAt=connection.get("connectedAt") if connection else None,
                expiresAt=connection.get("expiresAt") if connection else None,
                authNote=definition.auth_note,
                warnings=warnings,
            )
        )

    return OAuthProvidersResponse(
        frontendBaseUrl=settings.frontend_base_url,
        backendBaseUrl=settings.public_backend_url,
        providers=statuses,
    )


def build_authorization_url(provider: str, settings: Settings, return_url: str | None = None) -> OAuthStartResponse:
    definition = get_provider_definition(provider, settings)
    if not definition.client_id or not definition.client_secret:
        raise ValueError(f"{definition.label} chưa có client ID hoặc client secret.")

    callback_url = get_callback_url(settings, provider)
    target_return_url = return_url or get_default_return_url(settings)
    state = create_state(settings, provider, target_return_url)

    if provider == "google-youtube":
        params = {
            "client_id": definition.client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "scope": " ".join(definition.scopes),
            "state": state,
        }
    elif provider == "tiktok":
        params = {
            "client_key": definition.client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": ",".join(definition.scopes),
            "state": state,
        }
    elif provider == "facebook":
        params = {
            "client_id": definition.client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": ",".join(definition.scopes),
            "state": state,
        }
    else:
        params = {
            "response_type": "code",
            "client_id": definition.client_id,
            "redirect_uri": callback_url,
            "scope": " ".join(definition.scopes),
            "state": state,
        }

    return OAuthStartResponse(
        provider=provider,
        authorizationUrl=f"{definition.authorization_url}?{urlencode(params)}",
    )


async def handle_oauth_callback(
    provider: str,
    settings: Settings,
    state: str,
    code: str | None,
    error: str | None,
    error_description: str | None,
) -> str:
    state_payload = consume_state(settings, provider, state)
    return_url = state_payload.get("returnUrl") or get_default_return_url(settings)

    if error:
        message = error_description or error
        return build_frontend_redirect_url(return_url, provider, "error", f"Cấp quyền thất bại: {message}")

    if not code:
        return build_frontend_redirect_url(return_url, provider, "error", "Không nhận được mã xác thực từ nền tảng.")

    callback_url = get_callback_url(settings, provider)
    try:
        token_payload = await exchange_code_for_tokens(provider, settings, code, callback_url)
    except Exception as exc:
        return build_frontend_redirect_url(return_url, provider, "error", f"Đổi mã xác thực thất bại: {exc}")

    connection = {
        "provider": provider,
        "accessToken": token_payload.get("accessToken"),
        "refreshToken": token_payload.get("refreshToken"),
        "tokenType": token_payload.get("tokenType"),
        "scopes": token_payload.get("scopes", []),
        "expiresAt": token_payload.get("expiresAt"),
        "refreshExpiresAt": token_payload.get("refreshExpiresAt"),
        "connectedAt": iso_now(),
        "updatedAt": iso_now(),
        "accountLabel": token_payload.get("accountLabel"),
        "accountId": token_payload.get("accountId"),
        "metadata": token_payload.get("metadata", {}),
    }
    save_connection(settings, provider, connection)
    return build_frontend_redirect_url(return_url, provider, "success", f"Kết nối {get_provider_definition(provider, settings).label} thành công.")


async def refresh_provider_connection(provider: str, settings: Settings) -> OAuthActionResponse:
    connection = await refresh_connection(provider, settings)
    definition = get_provider_definition(provider, settings)
    return OAuthActionResponse(
        provider=provider,
        status="success",
        message=f"Đã làm mới token {definition.label}.",
        connected=True,
        accountLabel=connection.get("accountLabel"),
        expiresAt=connection.get("expiresAt"),
    )


def disconnect_provider_connection(provider: str, settings: Settings) -> OAuthActionResponse:
    definition = get_provider_definition(provider, settings)
    remove_connection(settings, provider)
    return OAuthActionResponse(
        provider=provider,
        status="success",
        message=f"Đã gỡ kết nối {definition.label}.",
        connected=False,
        accountLabel=None,
        expiresAt=None,
    )
