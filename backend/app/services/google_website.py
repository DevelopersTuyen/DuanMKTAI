from __future__ import annotations

import json
from datetime import date, timedelta
from urllib.parse import urlparse

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings
from app.models import GoogleWebsiteStatusResponse, GoogleWebsiteSyncResponse
from app.services.wordpress_connector import extract_path_from_url, fetch_wordpress_posts_for_site, normalize_url

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def get_google_website_status(settings: Settings) -> GoogleWebsiteStatusResponse:
    warnings: list[str] = []
    wordpress_sites = settings.get_wordpress_sites()
    has_service_account_key = bool(
        (settings.google_service_account_json and settings.google_service_account_json.strip())
        or (settings.google_service_account_file and settings.google_service_account_file.strip())
    )
    has_api_key = bool(settings.google_api_key and settings.google_api_key.strip())

    if not settings.google_sheet_id:
        warnings.append("Missing GOOGLE_SHEET_ID.")
    if not settings.google_sheet_worksheet:
        warnings.append("Missing GOOGLE_SHEET_WORKSHEET.")
    if not settings.google_analytics_property_id:
        warnings.append("Missing GOOGLE_ANALYTICS_PROPERTY_ID.")
    if not settings.google_search_console_site_url:
        warnings.append("Missing GOOGLE_SEARCH_CONSOLE_SITE_URL.")
    if not has_service_account_key:
        warnings.append("Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE.")
    if not has_api_key:
        warnings.append("Missing GOOGLE_API_KEY.")
    if not wordpress_sites:
        warnings.append("No WordPress sites configured in WORDPRESS_SITES_JSON.")

    ready = (
        bool(settings.google_sheet_id)
        and bool(settings.google_sheet_worksheet)
        and bool(settings.google_analytics_property_id)
        and bool(settings.google_search_console_site_url)
        and has_service_account_key
    )

    message = (
        "Ready to fetch Google Analytics + Search Console and write into Google Sheets."
        if ready
        else "Google website sync is not ready. Complete the missing credentials/config first."
    )

    return GoogleWebsiteStatusResponse(
        ready=ready,
        hasApiKey=has_api_key,
        hasServiceAccountKey=has_service_account_key,
        wordpressSitesCount=len(wordpress_sites),
        spreadsheetId=settings.google_sheet_id,
        worksheet=settings.google_sheet_worksheet,
        analyticsPropertyId=settings.google_analytics_property_id,
        searchConsoleSiteUrl=settings.google_search_console_site_url,
        message=message,
        warnings=warnings,
    )


def load_service_account_credentials(settings: Settings) -> Credentials:
    if settings.google_service_account_json and settings.google_service_account_json.strip():
        credentials_info = json.loads(settings.google_service_account_json)
        return Credentials.from_service_account_info(credentials_info, scopes=GOOGLE_SCOPES)

    if settings.google_service_account_file and settings.google_service_account_file.strip():
        return Credentials.from_service_account_file(settings.google_service_account_file, scopes=GOOGLE_SCOPES)

    raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE.")


def fetch_google_analytics_rows(settings: Settings, credentials: Credentials) -> list[list[str]]:
    if not settings.google_analytics_property_id:
        raise ValueError("Missing GOOGLE_ANALYTICS_PROPERTY_ID.")

    client = BetaAnalyticsDataClient(credentials=credentials)
    request = RunReportRequest(
        property=f"properties/{settings.google_analytics_property_id}",
        dimensions=[Dimension(name="date"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
            Metric(name="engagedSessions"),
        ],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        limit=100,
    )
    response = client.run_report(request)

    rows: list[list[str]] = [["date", "channel_group", "sessions", "active_users", "page_views", "engaged_sessions"]]
    for row in response.rows:
        rows.append(
            [
                row.dimension_values[0].value,
                row.dimension_values[1].value,
                row.metric_values[0].value,
                row.metric_values[1].value,
                row.metric_values[2].value,
                row.metric_values[3].value,
            ]
        )
    return rows


def fetch_google_analytics_page_rows(settings: Settings, credentials: Credentials) -> list[list[str]]:
    if not settings.google_analytics_property_id:
        raise ValueError("Missing GOOGLE_ANALYTICS_PROPERTY_ID.")

    client = BetaAnalyticsDataClient(credentials=credentials)
    request = RunReportRequest(
        property=f"properties/{settings.google_analytics_property_id}",
        dimensions=[Dimension(name="hostName"), Dimension(name="pagePathPlusQueryString")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="sessions"),
            Metric(name="activeUsers"),
        ],
        date_ranges=[DateRange(start_date="28daysAgo", end_date="today")],
        limit=500,
    )
    response = client.run_report(request)

    rows: list[list[str]] = [["hostname", "page_path", "page_views", "sessions", "active_users"]]
    for row in response.rows:
        rows.append(
            [
                row.dimension_values[0].value,
                row.dimension_values[1].value,
                row.metric_values[0].value,
                row.metric_values[1].value,
                row.metric_values[2].value,
            ]
        )
    return rows


def fetch_search_console_rows(settings: Settings, credentials: Credentials) -> list[list[str]]:
    if not settings.google_search_console_site_url:
        raise ValueError("Missing GOOGLE_SEARCH_CONSOLE_SITE_URL.")

    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    response = (
        service.searchanalytics()
        .query(
            siteUrl=settings.google_search_console_site_url,
            body={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["page", "query"],
                "rowLimit": 100,
            },
        )
        .execute()
    )

    rows: list[list[str]] = [["page", "query", "clicks", "impressions", "ctr", "position"]]
    for row in response.get("rows", []):
        keys = row.get("keys", ["", ""])
        rows.append(
            [
                str(keys[0] if len(keys) > 0 else ""),
                str(keys[1] if len(keys) > 1 else ""),
                str(row.get("clicks", 0)),
                str(row.get("impressions", 0)),
                str(row.get("ctr", 0)),
                str(row.get("position", 0)),
            ]
        )
    return rows


def fetch_search_console_page_rows(settings: Settings, credentials: Credentials) -> list[list[str]]:
    if not settings.google_search_console_site_url:
        raise ValueError("Missing GOOGLE_SEARCH_CONSOLE_SITE_URL.")

    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    end_date = date.today()
    start_date = end_date - timedelta(days=28)

    response = (
        service.searchanalytics()
        .query(
            siteUrl=settings.google_search_console_site_url,
            body={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["page"],
                "rowLimit": 250,
            },
        )
        .execute()
    )

    rows: list[list[str]] = [["page", "clicks", "impressions", "ctr", "position"]]
    for row in response.get("rows", []):
        keys = row.get("keys", [""])
        rows.append(
            [
                str(keys[0] if keys else ""),
                str(row.get("clicks", 0)),
                str(row.get("impressions", 0)),
                str(row.get("ctr", 0)),
                str(row.get("position", 0)),
            ]
        )
    return rows


def build_analytics_page_lookup(page_rows: list[list[str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in page_rows[1:]:
        host, path, page_views, sessions, active_users = row
        normalized_path = path.split("?", 1)[0].rstrip("/") or "/"
        hostname = host.lower()
        key = f"{hostname}{normalized_path}"
        lookup[key] = {
            "page_views": page_views,
            "sessions": sessions,
            "active_users": active_users,
        }
    return lookup


def build_search_console_page_lookup(page_rows: list[list[str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in page_rows[1:]:
        page, clicks, impressions, ctr, position = row
        normalized = normalize_url(page)
        lookup[normalized] = {
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "position": position,
        }
    return lookup


async def fetch_wordpress_post_rows(
    settings: Settings,
    analytics_page_rows: list[list[str]],
    search_console_page_rows: list[list[str]],
) -> tuple[list[list[str]], list[str]]:
    rows: list[list[str]] = [[
        "site",
        "post_id",
        "title",
        "status",
        "published_at",
        "url",
        "slug",
        "ga_page_views_28d",
        "ga_sessions_28d",
        "ga_active_users_28d",
        "gsc_clicks_28d",
        "gsc_impressions_28d",
        "gsc_ctr_28d",
        "gsc_position_28d",
    ]]
    warnings: list[str] = []

    analytics_lookup = build_analytics_page_lookup(analytics_page_rows)
    search_console_lookup = build_search_console_page_lookup(search_console_page_rows)

    for site in settings.get_wordpress_sites():
        try:
            site_posts = await fetch_wordpress_posts_for_site(site)
        except Exception as exc:
            warnings.append(f"WordPress fetch failed for {site.name}: {exc}")
            continue

        for post in site_posts:
            normalized_link = str(post.get("link", ""))
            parsed = urlparse(normalized_link)
            analytics_key = f"{parsed.netloc.lower()}{extract_path_from_url(normalized_link)}"
            ga_metrics = analytics_lookup.get(
                analytics_key,
                {"page_views": "0", "sessions": "0", "active_users": "0"},
            )
            gsc_metrics = search_console_lookup.get(
                normalized_link,
                {"clicks": "0", "impressions": "0", "ctr": "0", "position": "0"},
            )
            rows.append(
                [
                    str(post.get("site_name", "")),
                    str(post.get("id", "")),
                    str(post.get("title", "")),
                    str(post.get("status", "")),
                    str(post.get("date", "")),
                    normalized_link,
                    str(post.get("slug", "")),
                    ga_metrics["page_views"],
                    ga_metrics["sessions"],
                    ga_metrics["active_users"],
                    gsc_metrics["clicks"],
                    gsc_metrics["impressions"],
                    gsc_metrics["ctr"],
                    gsc_metrics["position"],
                ]
            )

    return rows, warnings


def ensure_sheet_exists(settings: Settings, credentials: Credentials) -> None:
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    spreadsheet = (
        service.spreadsheets()
        .get(spreadsheetId=settings.google_sheet_id, fields="sheets.properties.title")
        .execute()
    )
    titles = [sheet["properties"]["title"] for sheet in spreadsheet.get("sheets", [])]
    if settings.google_sheet_worksheet not in titles:
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=settings.google_sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": settings.google_sheet_worksheet}}}]},
            )
            .execute()
        )


def write_website_sheet(
    settings: Settings,
    credentials: Credentials,
    analytics_rows: list[list[str]],
    search_console_rows: list[list[str]],
    wordpress_rows: list[list[str]],
) -> list[str]:
    ensure_sheet_exists(settings, credentials)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    worksheet = settings.google_sheet_worksheet
    analytics_start_row = 7
    search_console_start_row = analytics_start_row + len(analytics_rows) + 3
    wordpress_start_row = search_console_start_row + len(search_console_rows) + 3

    metadata_values = [
        ["source", "value"],
        ["generated_by", "Marketing AI Hub Backend"],
        ["worksheet", worksheet],
        ["analytics_property_id", settings.google_analytics_property_id or ""],
        ["search_console_site_url", settings.google_search_console_site_url or ""],
        ["generated_range", "last_7_days"],
    ]

    (
        service.spreadsheets()
        .values()
        .clear(spreadsheetId=settings.google_sheet_id, range=f"{worksheet}!A:Z", body={})
        .execute()
    )

    body = {
        "valueInputOption": "RAW",
        "data": [
            {"range": f"{worksheet}!A1:B6", "values": metadata_values},
            {"range": f"{worksheet}!A{analytics_start_row}", "values": [["Google Analytics 4"]] + analytics_rows},
            {"range": f"{worksheet}!A{search_console_start_row}", "values": [["Google Search Console"]] + search_console_rows},
            {"range": f"{worksheet}!A{wordpress_start_row}", "values": [["WordPress Posts + SEO Mapping"]] + wordpress_rows},
        ],
    }

    response = (
        service.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=settings.google_sheet_id, body=body)
        .execute()
    )

    return [item.get("updatedRange", "") for item in response.get("responses", [])]


async def sync_google_website_data(settings: Settings) -> GoogleWebsiteSyncResponse:
    status = get_google_website_status(settings)
    if not status.ready:
        raise ValueError("; ".join(status.warnings))

    credentials = load_service_account_credentials(settings)
    warnings = list(status.warnings)
    analytics_rows: list[list[str]] = [["date", "channel_group", "sessions", "active_users", "page_views", "engaged_sessions"]]
    search_console_rows: list[list[str]] = [["page", "query", "clicks", "impressions", "ctr", "position"]]
    analytics_page_rows: list[list[str]] = [["hostname", "page_path", "page_views", "sessions", "active_users"]]
    search_console_page_rows: list[list[str]] = [["page", "clicks", "impressions", "ctr", "position"]]
    wordpress_rows: list[list[str]] = [[
        "site",
        "post_id",
        "title",
        "status",
        "published_at",
        "url",
        "slug",
        "ga_page_views_28d",
        "ga_sessions_28d",
        "ga_active_users_28d",
        "gsc_clicks_28d",
        "gsc_impressions_28d",
        "gsc_ctr_28d",
        "gsc_position_28d",
    ]]

    try:
        analytics_rows = fetch_google_analytics_rows(settings, credentials)
    except Exception as exc:
        warnings.append(f"GA4 fetch failed: {exc}")

    try:
        analytics_page_rows = fetch_google_analytics_page_rows(settings, credentials)
    except Exception as exc:
        warnings.append(f"GA4 page mapping failed: {exc}")

    try:
        search_console_rows = fetch_search_console_rows(settings, credentials)
    except Exception as exc:
        warnings.append(f"GSC fetch failed: {exc}")

    try:
        search_console_page_rows = fetch_search_console_page_rows(settings, credentials)
    except Exception as exc:
        warnings.append(f"GSC page mapping failed: {exc}")

    wordpress_rows, wordpress_warnings = await fetch_wordpress_post_rows(
        settings,
        analytics_page_rows,
        search_console_page_rows,
    )
    warnings.extend(wordpress_warnings)

    if len(analytics_rows) <= 1 and len(search_console_rows) <= 1 and len(wordpress_rows) <= 1:
        raise ValueError("No Google data could be fetched. " + "; ".join(warnings))

    updated_ranges = write_website_sheet(settings, credentials, analytics_rows, search_console_rows, wordpress_rows)
    is_partial = bool(warnings)

    return GoogleWebsiteSyncResponse(
        status="partial_success" if is_partial else "success",
        message=(
            "Fetched available Google website data and wrote them into Google Sheets with some warnings."
            if is_partial
            else "Fetched Google Analytics + Search Console data and wrote them into Google Sheets."
        ),
        spreadsheetId=settings.google_sheet_id,
        worksheet=settings.google_sheet_worksheet,
        wordpressPosts=max(len(wordpress_rows) - 1, 0),
        analyticsRows=max(len(analytics_rows) - 1, 0),
        searchConsoleRows=max(len(search_console_rows) - 1, 0),
        updatedRanges=updated_ranges,
        warnings=warnings,
    )
