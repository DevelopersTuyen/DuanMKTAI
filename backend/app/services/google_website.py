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
    analytics_property_ids = settings.get_google_analytics_property_ids()
    has_service_account_key = bool(
        (settings.google_service_account_json and settings.google_service_account_json.strip())
        or (settings.google_service_account_file and settings.google_service_account_file.strip())
    )
    has_api_key = bool(settings.google_api_key and settings.google_api_key.strip())

    if not settings.google_sheet_id:
        warnings.append("Thiếu GOOGLE_SHEET_ID.")
    if not settings.google_sheet_worksheet:
        warnings.append("Thiếu GOOGLE_SHEET_WORKSHEET.")
    if not analytics_property_ids:
        warnings.append("Thiếu GOOGLE_ANALYTICS_PROPERTY_ID hoặc GOOGLE_ANALYTICS_PROPERTY_IDS_JSON.")
    if not settings.google_search_console_site_url:
        warnings.append("Thiếu GOOGLE_SEARCH_CONSOLE_SITE_URL.")
    if not has_service_account_key:
        warnings.append("Thiếu GOOGLE_SERVICE_ACCOUNT_JSON hoặc GOOGLE_SERVICE_ACCOUNT_FILE.")
    if not has_api_key:
        warnings.append("Thiếu GOOGLE_API_KEY.")
    if not wordpress_sites:
        warnings.append("Chưa có website WordPress nào được cấu hình trong WORDPRESS_SITES_JSON.")

    ready = (
        bool(settings.google_sheet_id)
        and bool(settings.google_sheet_worksheet)
        and bool(analytics_property_ids)
        and bool(settings.google_search_console_site_url)
        and has_service_account_key
    )

    message = (
        "Sẵn sàng lấy Google Analytics và Search Console vào website, đồng thời ghi bài viết WordPress vào Post_web."
        if ready
        else "Đồng bộ website Google chưa sẵn sàng. Hãy hoàn tất phần cấu hình hoặc khóa còn thiếu trước."
    )

    return GoogleWebsiteStatusResponse(
        ready=ready,
        hasApiKey=has_api_key,
        hasServiceAccountKey=has_service_account_key,
        wordpressSitesCount=len(wordpress_sites),
        spreadsheetId=settings.google_sheet_id,
        worksheet=settings.google_sheet_worksheet,
        wordpressWorksheet=settings.wordpress_posts_worksheet,
        analyticsPropertyId=", ".join(analytics_property_ids),
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

    raise ValueError("Thiếu GOOGLE_SERVICE_ACCOUNT_JSON hoặc GOOGLE_SERVICE_ACCOUNT_FILE.")


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
    property_ids = settings.get_google_analytics_property_ids()
    if not property_ids:
        raise ValueError("Thiếu GOOGLE_ANALYTICS_PROPERTY_ID hoặc GOOGLE_ANALYTICS_PROPERTY_IDS_JSON.")

    client = BetaAnalyticsDataClient(credentials=credentials)
    rows: list[list[str]] = [["property_id", "hostname", "page_path", "page_views", "sessions", "active_users"]]

    for property_id in property_ids:
        request = RunReportRequest(
            property=f"properties/{property_id}",
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

        for row in response.rows:
            rows.append(
                [
                    property_id,
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
        raise ValueError("Thiếu GOOGLE_SEARCH_CONSOLE_SITE_URL.")

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
        raise ValueError("Thiếu GOOGLE_SEARCH_CONSOLE_SITE_URL.")

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


def build_google_sheet_rows(
    analytics_page_rows: list[list[str]],
    search_console_page_rows: list[list[str]],
    snapshot_date: str,
) -> list[list[str]]:
    rows: list[list[str]] = [[
        "sync_date",
        "source",
        "property_id",
        "page",
        "hostname",
        "page_path",
        "query",
        "page_views_28d",
        "sessions_28d",
        "active_users_28d",
        "clicks_28d",
        "impressions_28d",
        "ctr_28d",
        "position_28d",
    ]]

    for row in analytics_page_rows[1:]:
        property_id, hostname, page_path, page_views, sessions, active_users = row
        hostname = hostname.lower()
        normalized_page = f"https://{hostname}{page_path}" if hostname else page_path
        rows.append(
            [
                snapshot_date,
                "google_analytics",
                property_id,
                normalized_page,
                hostname,
                page_path,
                "",
                page_views,
                sessions,
                active_users,
                "0",
                "0",
                "0",
                "0",
            ]
        )

    for row in search_console_page_rows[1:]:
        page, clicks, impressions, ctr, position = row
        normalized_page = normalize_url(page)
        parsed = urlparse(normalized_page)
        rows.append(
            [
                snapshot_date,
                "google_search_console",
                "",
                normalized_page,
                parsed.netloc.lower(),
                extract_path_from_url(normalized_page),
                "",
                "0",
                "0",
                "0",
                clicks,
                impressions,
                ctr,
                position,
            ]
        )

    return rows


def build_analytics_page_lookup(page_rows: list[list[str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in page_rows[1:]:
        property_id, host, path, page_views, sessions, active_users = row
        normalized_path = path.split("?", 1)[0].rstrip("/") or "/"
        hostname = host.lower()
        key = f"{hostname}{normalized_path}"
        lookup[key] = {
            "property_id": property_id,
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
    snapshot_date: str,
) -> tuple[list[list[str]], list[str]]:
    rows: list[list[str]] = [[
        "sync_date",
        "site",
        "post_id",
        "title",
        "status",
        "published_at",
        "url",
        "slug",
        "ga_property_id",
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
            warnings.append(f"Lấy dữ liệu WordPress thất bại cho {site.name}: {exc}")
            continue

        for post in site_posts:
            normalized_link = str(post.get("link", ""))
            parsed = urlparse(normalized_link)
            analytics_key = f"{parsed.netloc.lower()}{extract_path_from_url(normalized_link)}"
            ga_metrics = analytics_lookup.get(
                analytics_key,
                {"property_id": "", "page_views": "0", "sessions": "0", "active_users": "0"},
            )
            gsc_metrics = search_console_lookup.get(
                normalized_link,
                {"clicks": "0", "impressions": "0", "ctr": "0", "position": "0"},
            )
            rows.append(
                [
                    snapshot_date,
                    str(post.get("site_name", "")),
                    str(post.get("id", "")),
                    str(post.get("title", "")),
                    str(post.get("status", "")),
                    str(post.get("date", "")),
                    normalized_link,
                    str(post.get("slug", "")),
                    ga_metrics["property_id"],
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


def ensure_sheet_exists(settings: Settings, credentials: Credentials, worksheet: str) -> None:
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    spreadsheet = (
        service.spreadsheets()
        .get(spreadsheetId=settings.google_sheet_id, fields="sheets.properties.title")
        .execute()
    )
    titles = [sheet["properties"]["title"] for sheet in spreadsheet.get("sheets", [])]
    if worksheet not in titles:
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=settings.google_sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": worksheet}}}]},
            )
            .execute()
        )


def get_sheet_values(settings: Settings, credentials: Credentials, worksheet: str) -> list[list[str]]:
    ensure_sheet_exists(settings, credentials, worksheet)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.google_sheet_id, range=f"{worksheet}!A:Z")
        .execute()
    )
    return response.get("values", [])


def normalize_rows_to_header(rows: list[list[str]], target_header: list[str]) -> list[list[str]]:
    if not rows:
        return [target_header]

    source_header = rows[0]
    source_index = {column: index for index, column in enumerate(source_header)}
    normalized_rows: list[list[str]] = [target_header]

    for row in rows[1:]:
        normalized_rows.append(
            [
                row[source_index[column]] if column in source_index and source_index[column] < len(row) else ""
                for column in target_header
            ]
        )

    return normalized_rows


def build_row_key(header: list[str], row: list[str], key_columns: list[str]) -> tuple[str, ...]:
    index_map = {column: index for index, column in enumerate(header)}
    return tuple(row[index_map[column]] if index_map[column] < len(row) else "" for column in key_columns)


def merge_sheet_rows(
    existing_rows: list[list[str]],
    new_rows: list[list[str]],
    key_columns: list[str],
) -> list[list[str]]:
    target_header = new_rows[0]
    merged_rows = normalize_rows_to_header(existing_rows, target_header)
    existing_index_by_key: dict[tuple[str, ...], int] = {}

    for index, row in enumerate(merged_rows[1:], start=1):
        existing_index_by_key[build_row_key(target_header, row, key_columns)] = index

    for row in new_rows[1:]:
        row_key = build_row_key(target_header, row, key_columns)
        existing_index = existing_index_by_key.get(row_key)

        if existing_index is not None:
            merged_rows[existing_index] = row
            continue

        existing_index_by_key[row_key] = len(merged_rows)
        merged_rows.append(row)

    return merged_rows


def write_google_metrics_sheet(
    settings: Settings,
    credentials: Credentials,
    website_rows: list[list[str]],
) -> str:
    worksheet = settings.google_sheet_worksheet
    existing_rows = get_sheet_values(settings, credentials, worksheet)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    merged_rows = merge_sheet_rows(
        existing_rows,
        website_rows,
        key_columns=["sync_date", "source", "property_id", "page", "query"],
    )

    body = {
        "valueInputOption": "RAW",
        "data": [
            {"range": f"{worksheet}!A1", "values": merged_rows},
        ],
    }

    response = (
        service.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=settings.google_sheet_id, body=body)
        .execute()
    )

    return response.get("responses", [{}])[-1].get("updatedRange", "")


def write_wordpress_posts_sheet(
    settings: Settings,
    credentials: Credentials,
    wordpress_rows: list[list[str]],
) -> str:
    worksheet = settings.wordpress_posts_worksheet
    existing_rows = get_sheet_values(settings, credentials, worksheet)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    merged_rows = merge_sheet_rows(
        existing_rows,
        wordpress_rows,
        key_columns=["sync_date", "site", "post_id", "url"],
    )

    response = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=settings.google_sheet_id,
            range=f"{worksheet}!A1",
            valueInputOption="RAW",
            body={"values": merged_rows},
        )
        .execute()
    )

    return response.get("updatedRange", "")


async def sync_google_website_data(settings: Settings) -> GoogleWebsiteSyncResponse:
    status = get_google_website_status(settings)
    if not status.ready:
        raise ValueError("; ".join(status.warnings))

    credentials = load_service_account_credentials(settings)
    snapshot_date = date.today().isoformat()
    warnings = list(status.warnings)
    analytics_page_rows: list[list[str]] = [["property_id", "hostname", "page_path", "page_views", "sessions", "active_users"]]
    search_console_page_rows: list[list[str]] = [["page", "clicks", "impressions", "ctr", "position"]]
    wordpress_rows: list[list[str]] = [[
        "sync_date",
        "site",
        "post_id",
        "title",
        "status",
        "published_at",
        "url",
        "slug",
        "ga_property_id",
        "ga_page_views_28d",
        "ga_sessions_28d",
        "ga_active_users_28d",
        "gsc_clicks_28d",
        "gsc_impressions_28d",
        "gsc_ctr_28d",
        "gsc_position_28d",
    ]]

    try:
        analytics_page_rows = fetch_google_analytics_page_rows(settings, credentials)
    except Exception as exc:
        warnings.append(f"Lấy dữ liệu GA4 thất bại: {exc}")

    try:
        search_console_page_rows = fetch_search_console_page_rows(settings, credentials)
    except Exception as exc:
        warnings.append(f"Lấy dữ liệu GSC thất bại: {exc}")

    wordpress_rows, wordpress_warnings = await fetch_wordpress_post_rows(
        settings,
        analytics_page_rows,
        search_console_page_rows,
        snapshot_date,
    )
    warnings.extend(wordpress_warnings)

    if len(analytics_page_rows) <= 1 and len(search_console_page_rows) <= 1 and len(wordpress_rows) <= 1:
        raise ValueError("Không lấy được dữ liệu Google nào. " + "; ".join(warnings))

    website_rows = build_google_sheet_rows(analytics_page_rows, search_console_page_rows, snapshot_date)
    updated_ranges = [
        write_google_metrics_sheet(settings, credentials, website_rows),
        write_wordpress_posts_sheet(settings, credentials, wordpress_rows),
    ]
    from app.services.website_reporting import invalidate_website_dataset_cache

    invalidate_website_dataset_cache(settings)
    is_partial = bool(warnings)

    return GoogleWebsiteSyncResponse(
        status="partial_success" if is_partial else "success",
        message=(
            "Đã lấy dữ liệu Google khả dụng vào website và bài viết WordPress vào Post_web, kèm một số cảnh báo."
            if is_partial
            else "Đã lấy Google Analytics và Search Console vào website, đồng thời ghi bài viết WordPress vào Post_web."
        ),
        spreadsheetId=settings.google_sheet_id,
        worksheet=settings.google_sheet_worksheet,
        wordpressWorksheet=settings.wordpress_posts_worksheet,
        wordpressPosts=max(len(wordpress_rows) - 1, 0),
        analyticsRows=max(len(analytics_page_rows) - 1, 0),
        searchConsoleRows=max(len(search_console_page_rows) - 1, 0),
        updatedRanges=updated_ranges,
        warnings=warnings,
    )
