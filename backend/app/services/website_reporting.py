from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime

from app.core.config import Settings
from app.models import (
    AnalyticsResponse,
    ChannelShare,
    ContentPerformance,
    DashboardKpi,
    DashboardResponse,
    KeywordInsight,
    PlatformPerformance,
    Recommendation,
    SeoInsightsResponse,
    TrendPoint,
)
from app.services.google_website import get_sheet_values, load_service_account_credentials
from app.services.mock_data import get_data_sync_data

WEBSITE_DATASET_CACHE_TTL_SECONDS = 45
_WEBSITE_DATASET_CACHE: dict[str, tuple[datetime, tuple[list[dict[str, str]], list[dict[str, str]]]]] = {}


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_dataset_cache_key(settings: Settings) -> str:
    return ":".join(
        [
            settings.google_sheet_id,
            settings.google_sheet_worksheet,
            settings.wordpress_posts_worksheet,
        ]
    )


def invalidate_website_dataset_cache(settings: Settings | None = None) -> None:
    if settings is None:
        _WEBSITE_DATASET_CACHE.clear()
        return
    _WEBSITE_DATASET_CACHE.pop(build_dataset_cache_key(settings), None)


def to_float(value: str | None) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def format_compact_number(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def to_percent(value: float) -> float:
    if value <= 1:
        return round(value * 100, 2)
    return round(value, 2)


def compute_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def parse_sheet_records(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []

    header = rows[0]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        record = {
            column: row[index] if index < len(row) else ""
            for index, column in enumerate(header)
        }
        if any(value for value in record.values()):
            records.append(record)
    return records


def sort_dates(dates: set[str]) -> list[str]:
    return sorted(
        [value for value in dates if value],
        key=lambda item: datetime.strptime(item, "%Y-%m-%d"),
    )


def latest_snapshot(records: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    available_dates = sort_dates({record.get("sync_date", "") for record in records})
    if not available_dates:
        return "", []

    latest_date = available_dates[-1]
    return latest_date, [record for record in records if record.get("sync_date") == latest_date]


def compute_trend(current_value: float, previous_value: float) -> tuple[str, str]:
    if previous_value <= 0 and current_value > 0:
        return "Mới", "trend-up"
    if previous_value <= 0:
        return "0%", "trend-flat"

    delta = ((current_value - previous_value) / previous_value) * 100
    if delta > 1:
        return f"+{delta:.1f}%", "trend-up"
    if delta < -1:
        return f"{delta:.1f}%", "trend-alert"
    return f"{delta:.1f}%", "trend-flat"


def build_recommendations(
    latest_ga_rows: list[dict[str, str]],
    latest_gsc_rows: list[dict[str, str]],
    latest_post_rows: list[dict[str, str]],
) -> list[Recommendation]:
    recommendations: list[Recommendation] = []

    if latest_ga_rows:
        top_page = max(latest_ga_rows, key=lambda item: to_float(item.get("page_views_28d")))
        recommendations.append(
            Recommendation(
                title=f"Đẩy thêm nội dung cho trang {top_page.get('page_path') or '/'}",
                detail=(
                    f"Trang này đang dẫn đầu với {format_compact_number(to_float(top_page.get('page_views_28d')))} lượt xem "
                    f"trên {top_page.get('hostname') or 'không xác định'}."
                ),
                priority="High",
            )
        )

    if latest_post_rows:
        weakest_post = min(latest_post_rows, key=lambda item: to_float(item.get("gsc_ctr_28d")))
        recommendations.append(
            Recommendation(
                title=f"Làm mới bài viết {weakest_post.get('title') or weakest_post.get('slug')}",
                detail=(
                    f"Bài viết này đang có CTR {to_percent(to_float(weakest_post.get('gsc_ctr_28d'))):.2f}% "
                    "và nên tối ưu lại tiêu đề, liên kết nội bộ, CTA."
                ),
                priority="High",
            )
        )

    if not latest_gsc_rows:
        recommendations.append(
            Recommendation(
                title="Cấp quyền Search Console cho service account",
                detail="Hiện chưa có dữ liệu GSC thật trên giao diện website vì thuộc tính Search Console đang bị 403.",
                priority="High",
            )
        )

    if not recommendations:
        recommendations.append(
            Recommendation(
                title="Chưa có dữ liệu website để phân tích",
                detail="Cần đồng bộ GA4, GSC và WordPress trước khi bảng điều khiển website có dữ liệu thật.",
                priority="Medium",
            )
        )

    return recommendations[:3]


def load_website_dataset(settings: Settings) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    cache_key = build_dataset_cache_key(settings)
    cached = _WEBSITE_DATASET_CACHE.get(cache_key)
    if cached and (utc_now() - cached[0]).total_seconds() < WEBSITE_DATASET_CACHE_TTL_SECONDS:
        website_records, post_records = cached[1]
        return deepcopy(website_records), deepcopy(post_records)

    credentials = load_service_account_credentials(settings)
    website_rows = get_sheet_values(settings, credentials, settings.google_sheet_worksheet)
    post_rows = get_sheet_values(settings, credentials, settings.wordpress_posts_worksheet)
    parsed_dataset = (parse_sheet_records(website_rows), parse_sheet_records(post_rows))
    _WEBSITE_DATASET_CACHE[cache_key] = (utc_now(), deepcopy(parsed_dataset))
    return deepcopy(parsed_dataset[0]), deepcopy(parsed_dataset[1])


def get_website_dashboard_data(settings: Settings) -> DashboardResponse:
    website_records, post_records = load_website_dataset(settings)
    ga_records = [record for record in website_records if record.get("source") == "google_analytics"]
    gsc_records = [record for record in website_records if record.get("source") == "google_search_console"]

    latest_date, latest_ga_rows = latest_snapshot(ga_records)
    _, latest_gsc_rows = latest_snapshot(gsc_records)
    _, latest_post_rows = latest_snapshot(post_records)

    ga_dates = sort_dates({record.get("sync_date", "") for record in ga_records})
    trend_source_dates = ga_dates[-7:]
    trend_points: list[TrendPoint] = []

    for sync_date in trend_source_dates:
        total_sessions = sum(
            to_float(record.get("sessions_28d"))
            for record in ga_records
            if record.get("sync_date") == sync_date
        )
        trend_points.append(
            TrendPoint(label=datetime.strptime(sync_date, "%Y-%m-%d").strftime("%d/%m"), value=round(total_sessions))
        )

    host_views: dict[str, float] = defaultdict(float)
    for row in latest_ga_rows:
        host_views[row.get("hostname", "unknown")] += to_float(row.get("page_views_28d"))

    total_host_views = sum(host_views.values())
    channel_breakdown = [
        ChannelShare(
            name=hostname,
            value=round((views / total_host_views) * 100) if total_host_views > 0 else 0,
        )
        for hostname, views in sorted(host_views.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    current_sessions = sum(to_float(record.get("sessions_28d")) for record in latest_ga_rows)
    previous_sessions = 0.0
    if len(trend_source_dates) > 1:
        previous_date = trend_source_dates[-2]
        previous_sessions = sum(
            to_float(record.get("sessions_28d"))
            for record in ga_records
            if record.get("sync_date") == previous_date
        )

    sessions_trend, sessions_tone = compute_trend(current_sessions, previous_sessions)
    total_page_views = sum(to_float(record.get("page_views_28d")) for record in latest_ga_rows)
    indexed_pages = len(latest_gsc_rows)
    total_posts = len(latest_post_rows)

    kpis = [
        DashboardKpi(
            label="Phiên website 28 ngày",
            value=format_compact_number(current_sessions),
            note=f"Ảnh chụp ngày {latest_date or 'chưa có dữ liệu'} từ {len(settings.get_google_analytics_property_ids())} thuộc tính GA4.",
            trend=sessions_trend,
            trendTone=sessions_tone,
        ),
        DashboardKpi(
            label="Lượt xem trang 28 ngày",
            value=format_compact_number(total_page_views),
            note=f"Theo dõi trên {len(host_views)} domain website đang đồng bộ thật.",
            trend=f"{len(latest_ga_rows)} trang",
            trendTone="trend-flat",
        ),
        DashboardKpi(
            label="Bài viết WordPress đã đồng bộ",
            value=str(total_posts),
            note="Số bài viết thật đang có trong trang tính Post_web của lần đồng bộ mới nhất.",
            trend="Đang chạy",
            trendTone="trend-up",
        ),
        DashboardKpi(
            label="Trang SEO đang theo dõi",
            value=str(indexed_pages),
            note=(
                "Dữ liệu Search Console thật theo từng trang."
                if indexed_pages > 0
                else "Đang thiếu quyền Search Console nên chưa kéo được dữ liệu SEO thật."
            ),
            trend="Cần quyền" if indexed_pages == 0 else "Sẵn sàng",
            trendTone="trend-alert" if indexed_pages == 0 else "trend-up",
        ),
    ]

    sync_channels = get_data_sync_data(
        wordpress_sites_count=len(settings.get_wordpress_sites()) or 3,
        analytics_property_count=len(settings.get_google_analytics_property_ids()) or 1,
    ).syncChannels

    return DashboardResponse(
        kpis=kpis,
        performanceTrend=trend_points or [TrendPoint(label="Không có dữ liệu", value=0)],
        channelBreakdown=channel_breakdown or [ChannelShare(name="Chưa có dữ liệu", value=100)],
        syncChannels=sync_channels,
        recommendations=build_recommendations(latest_ga_rows, latest_gsc_rows, latest_post_rows),
    )


def get_website_analytics_data(settings: Settings) -> AnalyticsResponse:
    website_records, post_records = load_website_dataset(settings)
    ga_records = [record for record in website_records if record.get("source") == "google_analytics"]
    gsc_records = [record for record in website_records if record.get("source") == "google_search_console"]

    _, latest_ga_rows = latest_snapshot(ga_records)
    _, latest_gsc_rows = latest_snapshot(gsc_records)
    _, latest_post_rows = latest_snapshot(post_records)

    gsc_by_host: dict[str, dict[str, float]] = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0})
    for row in latest_gsc_rows:
        host = row.get("hostname", "unknown")
        gsc_by_host[host]["clicks"] += to_float(row.get("clicks_28d"))
        gsc_by_host[host]["impressions"] += to_float(row.get("impressions_28d"))

    host_metrics: dict[str, dict[str, float]] = defaultdict(
        lambda: {"page_views": 0.0, "sessions": 0.0, "active_users": 0.0}
    )
    for row in latest_ga_rows:
        host = row.get("hostname", "unknown")
        host_metrics[host]["page_views"] += to_float(row.get("page_views_28d"))
        host_metrics[host]["sessions"] += to_float(row.get("sessions_28d"))
        host_metrics[host]["active_users"] += to_float(row.get("active_users_28d"))

    platforms = [
        PlatformPerformance(
            platform=host,
            reach=format_compact_number(values["page_views"]),
            engagementRate=compute_rate(values["active_users"], values["sessions"]),
            ctr=compute_rate(gsc_by_host[host]["clicks"], gsc_by_host[host]["impressions"]),
            conversionRate=compute_rate(values["active_users"], values["page_views"]),
        )
        for host, values in sorted(host_metrics.items(), key=lambda item: item[1]["page_views"], reverse=True)[:4]
    ]

    top_contents = [
        ContentPerformance(
            title=record.get("title") or record.get("slug") or record.get("url") or "Bài viết chưa có tiêu đề",
            platform=record.get("site") or "WordPress",
            format="Bài viết",
            views=format_compact_number(to_float(record.get("ga_page_views_28d"))),
            ctr=to_percent(to_float(record.get("gsc_ctr_28d"))),
            engagementRate=compute_rate(
                to_float(record.get("ga_active_users_28d")),
                to_float(record.get("ga_sessions_28d")),
            ),
            statusClass=(
                "status-live"
                if to_float(record.get("ga_page_views_28d")) >= 500
                else "status-draft"
            ),
            statusLabel=(
                "Hiệu quả"
                if to_float(record.get("ga_page_views_28d")) >= 500
                else "Theo dõi"
            ),
        )
        for record in sorted(
            latest_post_rows,
            key=lambda item: (
                to_float(item.get("ga_page_views_28d")),
                to_float(item.get("gsc_clicks_28d")),
            ),
            reverse=True,
        )[:8]
    ]

    return AnalyticsResponse(
        platforms=platforms,
        topContents=top_contents,
        recommendations=build_recommendations(latest_ga_rows, latest_gsc_rows, latest_post_rows),
    )


def get_website_seo_data(settings: Settings) -> SeoInsightsResponse:
    website_records, post_records = load_website_dataset(settings)
    gsc_records = [record for record in website_records if record.get("source") == "google_search_console"]
    ga_records = [record for record in website_records if record.get("source") == "google_analytics"]

    _, latest_gsc_rows = latest_snapshot(gsc_records)
    _, latest_ga_rows = latest_snapshot(ga_records)
    _, latest_post_rows = latest_snapshot(post_records)

    keywords = [
        KeywordInsight(
            keyword=record.get("page_path") or record.get("page") or "/",
            clicks=round(to_float(record.get("clicks_28d"))),
            impressions=round(to_float(record.get("impressions_28d"))),
            ctr=to_percent(to_float(record.get("ctr_28d"))),
            position=round(to_float(record.get("position_28d")), 2),
            action=(
                "Làm mới tiêu đề và thêm liên kết nội bộ"
                if to_float(record.get("position_28d")) >= 5 and to_float(record.get("position_28d")) <= 12
                else "Giữ ổn định và tiếp tục theo dõi"
            ),
        )
        for record in sorted(
            latest_gsc_rows,
            key=lambda item: (to_float(item.get("impressions_28d")), to_float(item.get("clicks_28d"))),
            reverse=True,
        )[:10]
    ]

    recommendations = build_recommendations(latest_ga_rows, latest_gsc_rows, latest_post_rows)
    if not keywords:
        recommendations = [
            Recommendation(
                title="Không có dữ liệu Search Console thật",
                detail="Giao diện SEO đang đọc dữ liệu thật từ sheet website, nhưng hiện thuộc tính Search Console vẫn chưa cấp quyền cho service account.",
                priority="High",
            ),
            *recommendations[:2],
        ]

    return SeoInsightsResponse(
        keywords=keywords,
        recommendations=recommendations[:3],
    )
