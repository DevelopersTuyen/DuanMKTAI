from __future__ import annotations

import json
import re
from copy import deepcopy
from collections import defaultdict
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings
from app.models import (
    DailyReportDeleteResponse,
    DailyReportHistoryItem,
    DailyReportHistoryResponse,
    DailyReportLatestResponse,
    DailyReportSyncResponse,
)
from app.services.google_website import (
    get_sheet_values,
    load_service_account_credentials,
    merge_sheet_rows,
)
from app.services.ollama_client import generate_text_with_ollama
from app.services.website_reporting import latest_snapshot, load_website_dataset, to_float

DAILY_REPORT_CACHE_TTL_SECONDS = 45
_DAILY_REPORT_CACHE: dict[str, tuple[datetime, dict[str, str]]] = {}
DAILY_REPORT_HEADER = [
    "ngay",
    "tong_quat",
    "chi_tiet_tung_nen_tang",
    "van_de_gap_phai",
    "de_xuat",
    "model_ai",
    "nguon_ai",
    "generated_at",
]


def build_daily_report_cache_key(settings: Settings) -> str:
    return f"{settings.google_sheet_id}:{settings.daily_report_worksheet}"


def invalidate_daily_report_cache(settings: Settings | None = None) -> None:
    if settings is None:
        _DAILY_REPORT_CACHE.clear()
        return
    _DAILY_REPORT_CACHE.pop(build_daily_report_cache_key(settings), None)


def format_compact_number(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def normalize_multiline(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return "\n".join(
            f"{str(key).strip()}: {str(item).strip()}"
            for key, item in value.items()
            if str(item).strip()
        )
    return str(value).strip()


def extract_json_payload(raw_text: str) -> dict[str, str]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start_index = cleaned.find("{")
    end_index = cleaned.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return {}

    try:
        parsed = json.loads(cleaned[start_index : end_index + 1])
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return {
        "tong_quat": normalize_multiline(parsed.get("tong_quat", "")),
        "chi_tiet_tung_nen_tang": normalize_multiline(parsed.get("chi_tiet_tung_nen_tang", "")),
        "van_de_gap_phai": normalize_multiline(parsed.get("van_de_gap_phai", "")),
        "de_xuat": normalize_multiline(parsed.get("de_xuat", "")),
    }


def collect_daily_report_context(
    settings: Settings,
) -> dict[str, object]:
    website_records, post_records = load_website_dataset(settings)
    ga_records = [record for record in website_records if record.get("source") == "google_analytics"]
    gsc_records = [record for record in website_records if record.get("source") == "google_search_console"]

    latest_ga_date, latest_ga_rows = latest_snapshot(ga_records)
    latest_gsc_date, latest_gsc_rows = latest_snapshot(gsc_records)
    latest_post_date, latest_post_rows = latest_snapshot(post_records)

    total_sessions = sum(to_float(row.get("sessions_28d")) for row in latest_ga_rows)
    total_page_views = sum(to_float(row.get("page_views_28d")) for row in latest_ga_rows)
    total_active_users = sum(to_float(row.get("active_users_28d")) for row in latest_ga_rows)

    host_metrics: dict[str, dict[str, float]] = defaultdict(lambda: {"page_views": 0.0, "sessions": 0.0})
    for row in latest_ga_rows:
        hostname = (row.get("hostname") or "khong-xac-dinh").lower()
        host_metrics[hostname]["page_views"] += to_float(row.get("page_views_28d"))
        host_metrics[hostname]["sessions"] += to_float(row.get("sessions_28d"))

    post_hosts = {
        urlparse(str(row.get("url") or "")).netloc.lower()
        for row in latest_post_rows
        if row.get("url")
    }

    configured_wordpress_hosts = {
        urlparse(site.base_url).netloc.lower()
        for site in settings.get_wordpress_sites()
        if site.base_url
    }
    missing_wordpress_hosts = sorted(host for host in configured_wordpress_hosts if host and host not in post_hosts)

    top_pages = sorted(
        latest_ga_rows,
        key=lambda item: to_float(item.get("page_views_28d")),
        reverse=True,
    )[:5]
    top_posts = sorted(
        latest_post_rows,
        key=lambda item: (
            to_float(item.get("ga_page_views_28d")),
            to_float(item.get("gsc_clicks_28d")),
        ),
        reverse=True,
    )[:5]

    platform_details: list[str] = []
    if latest_ga_rows:
        host_lines = [
            f"- {host}: {format_compact_number(values['page_views'])} lượt xem trang, {format_compact_number(values['sessions'])} phiên"
            for host, values in sorted(host_metrics.items(), key=lambda item: item[1]["page_views"], reverse=True)[:5]
        ]
        top_page_lines = [
            f"- {row.get('hostname') or 'website'} {row.get('page_path') or '/'}: {format_compact_number(to_float(row.get('page_views_28d')))} lượt xem"
            for row in top_pages
        ]
        platform_details.append(
            "\n".join(
                [
                    "Website:",
                    f"- Snapshot GA4: {latest_ga_date or 'chưa có dữ liệu'}",
                    f"- Tổng lượt xem trang 28 ngày: {format_compact_number(total_page_views)}",
                    f"- Tổng phiên 28 ngày: {format_compact_number(total_sessions)}",
                    f"- Tổng người dùng hoạt động 28 ngày: {format_compact_number(total_active_users)}",
                    f"- Số bài WordPress đang theo dõi: {len(latest_post_rows)}",
                    f"- Số dòng Search Console hiện có: {len(latest_gsc_rows)}",
                    "- Domain nổi bật:",
                    *host_lines,
                    "- Trang nổi bật:",
                    *(top_page_lines or ["- Chưa có trang nổi bật"]),
                ]
            )
        )
    else:
        platform_details.append("Website:\n- Chưa có dữ liệu thật trong sheet website.")

    if latest_post_rows:
        top_post_lines = [
            f"- {row.get('site') or 'WordPress'} | {row.get('title') or row.get('slug') or row.get('url')}: {format_compact_number(to_float(row.get('ga_page_views_28d')))} lượt xem"
            for row in top_posts
        ]
        platform_details.append(
            "\n".join(
                [
                    "WordPress:",
                    f"- Snapshot bài viết: {latest_post_date or 'chưa có dữ liệu'}",
                    f"- Website có bài viết đồng bộ: {len(post_hosts)} / {len(configured_wordpress_hosts) or len(post_hosts)}",
                    "- Bài viết nổi bật:",
                    *(top_post_lines or ["- Chưa có bài viết nổi bật"]),
                ]
            )
        )
    else:
        platform_details.append("WordPress:\n- Chưa có bài viết thật trong sheet Post_web.")

    for channel_name in ["Facebook", "TikTok", "LinkedIn", "YouTube"]:
        platform_details.append(f"{channel_name}:\n- Chưa kết nối dữ liệu thật nên chưa có số liệu để phân tích.")

    issues: list[str] = []
    if not latest_ga_rows:
        issues.append("- Sheet website chưa có dữ liệu GA4 thật cho ngày hiện tại.")
    if not latest_gsc_rows:
        issues.append("- Google Search Console chưa có dữ liệu thật hoặc service account chưa đủ quyền truy cập.")
    if missing_wordpress_hosts:
        issues.append(f"- Chưa lấy được bài viết từ các website WordPress: {', '.join(missing_wordpress_hosts)}.")
    issues.extend(
        [
            "- Facebook chưa có sheet dữ liệu thật để đưa vào báo cáo ngày.",
            "- TikTok chưa có sheet dữ liệu thật để đưa vào báo cáo ngày.",
            "- LinkedIn chưa có sheet dữ liệu thật để đưa vào báo cáo ngày.",
            "- YouTube chưa có sheet dữ liệu thật để đưa vào báo cáo ngày.",
        ]
    )

    recommendations: list[str] = []
    if top_pages:
        lead_page = top_pages[0]
        recommendations.append(
            f"- Ưu tiên tối ưu CTA và điều hướng nội bộ cho trang {lead_page.get('page_path') or '/'} trên {lead_page.get('hostname') or 'website chính'}."
        )
    if top_posts:
        lead_post = top_posts[0]
        recommendations.append(
            f"- Làm mới bài viết '{lead_post.get('title') or lead_post.get('slug') or lead_post.get('url')}' để giữ đà truy cập và tăng chuyển đổi."
        )
    if not latest_gsc_rows:
        recommendations.append("- Cấp quyền Search Console cho service account để bổ sung dữ liệu SEO thật theo từng trang.")
    if missing_wordpress_hosts:
        recommendations.append(f"- Rà soát REST API hoặc lớp bảo mật của các site WordPress lỗi: {', '.join(missing_wordpress_hosts)}.")
    recommendations.append("- Kết nối các sheet Facebook, TikTok, LinkedIn và YouTube trước khi dùng AI để kết luận đa nền tảng.")

    overview = (
        f"Ngày {date.today().isoformat()}, hệ thống đang có dữ liệu thật chủ yếu từ website với "
        f"{format_compact_number(total_page_views)} lượt xem trang, {format_compact_number(total_sessions)} phiên "
        f"và {len(latest_post_rows)} bài WordPress trong snapshot mới nhất."
    )
    if latest_gsc_rows:
        overview += f" Dữ liệu SEO hiện có {len(latest_gsc_rows)} dòng Search Console để đối chiếu theo từng trang."
    else:
        overview += " Dữ liệu Search Console vẫn chưa sẵn sàng nên phần SEO mới dừng ở mức cảnh báo."

    return {
        "report_date": date.today().isoformat(),
        "snapshot_date": latest_ga_date or latest_post_date or latest_gsc_date or "",
        "overview": overview,
        "platform_details": "\n\n".join(platform_details),
        "issues": "\n".join(issues),
        "recommendations": "\n".join(recommendations),
        "latest_ga_rows": latest_ga_rows,
        "latest_gsc_rows": latest_gsc_rows,
        "latest_post_rows": latest_post_rows,
        "missing_wordpress_hosts": missing_wordpress_hosts,
        "host_metrics": host_metrics,
        "top_pages": top_pages,
        "top_posts": top_posts,
    }


def build_daily_report_prompt(context: dict[str, object]) -> str:
    latest_ga_rows = context["latest_ga_rows"]
    latest_gsc_rows = context["latest_gsc_rows"]
    latest_post_rows = context["latest_post_rows"]
    top_pages = context["top_pages"]
    top_posts = context["top_posts"]
    host_metrics = context["host_metrics"]
    missing_wordpress_hosts = context["missing_wordpress_hosts"]

    host_lines = "\n".join(
        [
            f"- {host}: {format_compact_number(values['page_views'])} lượt xem, {format_compact_number(values['sessions'])} phiên"
            for host, values in sorted(host_metrics.items(), key=lambda item: item[1]["page_views"], reverse=True)[:5]
        ]
    ) or "- Chưa có domain nào"

    top_page_lines = "\n".join(
        [
            f"- {row.get('hostname')} {row.get('page_path')}: {row.get('page_views_28d')} lượt xem, {row.get('sessions_28d')} phiên"
            for row in top_pages
        ]
    ) or "- Chưa có trang nổi bật"

    top_post_lines = "\n".join(
        [
            f"- {row.get('site')} | {row.get('title')}: {row.get('ga_page_views_28d')} lượt xem, CTR GSC {row.get('gsc_ctr_28d')}"
            for row in top_posts
        ]
    ) or "- Chưa có bài viết nổi bật"

    missing_sites_text = ", ".join(missing_wordpress_hosts) if missing_wordpress_hosts else "Không có"

    return "\n".join(
        [
            "Bạn là chuyên gia lập báo cáo marketing hàng ngày.",
            "Hãy tạo nội dung báo cáo để ghi vào Google Sheet.",
            "Chỉ dùng dữ liệu được cung cấp. Không bịa thêm số liệu cho các kênh chưa kết nối.",
            "Bắt buộc trả về JSON hợp lệ, không markdown, theo đúng schema:",
            '{"tong_quat":"...","chi_tiet_tung_nen_tang":"...","van_de_gap_phai":"...","de_xuat":"..."}',
            "Yêu cầu:",
            "- Viết tiếng Việt có dấu.",
            "- `tong_quat` gồm 2-3 câu ngắn, mang tính điều hành.",
            "- `chi_tiet_tung_nen_tang` trình bày theo từng nền tảng, ngăn cách bằng dòng mới.",
            "- `van_de_gap_phai` là danh sách nhiều dòng, mỗi dòng bắt đầu bằng '- '.",
            "- `de_xuat` là danh sách nhiều dòng, mỗi dòng bắt đầu bằng '- '.",
            "",
            f"Ngày báo cáo: {context['report_date']}",
            f"Ngày snapshot dữ liệu gần nhất: {context['snapshot_date'] or 'chưa có dữ liệu'}",
            f"Số dòng GA4 theo trang: {len(latest_ga_rows)}",
            f"Số dòng Search Console: {len(latest_gsc_rows)}",
            f"Số bài WordPress: {len(latest_post_rows)}",
            f"Website WordPress chưa lấy được dữ liệu: {missing_sites_text}",
            "",
            "Tổng quan website:",
            str(context["overview"]),
            "",
            "Domain nổi bật:",
            host_lines,
            "",
            "Trang nổi bật:",
            top_page_lines,
            "",
            "Bài viết nổi bật:",
            top_post_lines,
            "",
            "Các kênh chưa có dữ liệu thật: Facebook, TikTok, LinkedIn, YouTube.",
        ]
    )


def build_fallback_sections(context: dict[str, object]) -> dict[str, str]:
    return {
        "tong_quat": str(context["overview"]),
        "chi_tiet_tung_nen_tang": str(context["platform_details"]),
        "van_de_gap_phai": str(context["issues"]),
        "de_xuat": str(context["recommendations"]),
    }


async def generate_daily_report_sections(settings: Settings) -> tuple[dict[str, str], str, str]:
    context = collect_daily_report_context(settings)
    prompt = build_daily_report_prompt(context)
    fallback_sections = build_fallback_sections(context)

    for _ in range(3):
        generated_text, source, used_model = await generate_text_with_ollama(
            prompt,
            settings,
            job_name="Tạo báo cáo ngày",
        )
        parsed_sections = extract_json_payload(generated_text)

        if parsed_sections:
            for key, fallback_value in fallback_sections.items():
                if not parsed_sections.get(key):
                    parsed_sections[key] = fallback_value
            return parsed_sections, source, used_model

    return fallback_sections, "fallback", settings.ollama_model


def write_daily_report_sheet(
    settings: Settings,
    credentials: Credentials,
    row_values: list[str],
) -> str:
    worksheet = settings.daily_report_worksheet
    new_rows = [DAILY_REPORT_HEADER, row_values]
    existing_rows = get_sheet_values(settings, credentials, worksheet)
    merged_rows = merge_sheet_rows(existing_rows, new_rows, key_columns=["ngay"])
    return overwrite_daily_report_rows(settings, credentials, merged_rows)


def overwrite_daily_report_rows(
    settings: Settings,
    credentials: Credentials,
    rows: list[list[str]],
) -> str:
    worksheet = settings.daily_report_worksheet
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    (
        service.spreadsheets()
        .values()
        .clear(
            spreadsheetId=settings.google_sheet_id,
            range=worksheet,
            body={},
        )
        .execute()
    )
    response = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=settings.google_sheet_id,
            range=f"{worksheet}!A1",
            valueInputOption="RAW",
            body={"values": rows},
        )
        .execute()
    )
    invalidate_daily_report_cache(settings)
    return response.get("updatedRange", "")


async def sync_daily_report(settings: Settings) -> DailyReportSyncResponse:
    credentials = load_service_account_credentials(settings)
    sections, source, used_model = await generate_daily_report_sections(settings)
    report_date = date.today().isoformat()
    generated_at = datetime.now().isoformat(timespec="seconds")
    updated_range = write_daily_report_sheet(
        settings,
        credentials,
        [
            report_date,
            sections["tong_quat"],
            sections["chi_tiet_tung_nen_tang"],
            sections["van_de_gap_phai"],
            sections["de_xuat"],
            used_model,
            source,
            generated_at,
        ],
    )

    return DailyReportSyncResponse(
        status="success",
        message="Đã tạo báo cáo ngày và ghi vào worksheet reportday.",
        worksheet=settings.daily_report_worksheet,
        reportDate=report_date,
        updatedRange=updated_range,
        model=used_model,
        source=source,
        generatedAt=generated_at,
    )


def get_latest_daily_report(settings: Settings) -> DailyReportLatestResponse:
    cache_key = build_daily_report_cache_key(settings)
    cached = _DAILY_REPORT_CACHE.get(cache_key)
    if cached and (datetime.now(UTC) - cached[0]).total_seconds() < DAILY_REPORT_CACHE_TTL_SECONDS:
        latest_record = deepcopy(cached[1])
        return DailyReportLatestResponse(
            reportDate=latest_record.get("ngay", ""),
            tongQuat=latest_record.get("tong_quat", ""),
            chiTietTungNenTang=latest_record.get("chi_tiet_tung_nen_tang", ""),
            vanDeGapPhai=latest_record.get("van_de_gap_phai", ""),
            deXuat=latest_record.get("de_xuat", ""),
            model=latest_record.get("model_ai", ""),
            source=latest_record.get("nguon_ai", ""),
            generatedAt=latest_record.get("generated_at", ""),
            worksheet=settings.daily_report_worksheet,
        )

    credentials = load_service_account_credentials(settings)
    rows = get_sheet_values(settings, credentials, settings.daily_report_worksheet)
    if not rows or len(rows) <= 1:
        raise ValueError("Chưa có báo cáo ngày nào trong sheet reportday.")

    header = rows[0]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        record = {
            column: row[index] if index < len(row) else ""
            for index, column in enumerate(header)
        }
        if any(value for value in record.values()):
            records.append(record)

    if not records:
        raise ValueError("Chưa có báo cáo ngày nào trong sheet reportday.")

    latest_record = max(
        records,
        key=lambda item: (
            item.get("ngay", ""),
            item.get("generated_at", ""),
        ),
    )
    _DAILY_REPORT_CACHE[cache_key] = (datetime.now(UTC), deepcopy(latest_record))

    return DailyReportLatestResponse(
        reportDate=latest_record.get("ngay", ""),
        tongQuat=latest_record.get("tong_quat", ""),
        chiTietTungNenTang=latest_record.get("chi_tiet_tung_nen_tang", ""),
        vanDeGapPhai=latest_record.get("van_de_gap_phai", ""),
        deXuat=latest_record.get("de_xuat", ""),
        model=latest_record.get("model_ai", ""),
        source=latest_record.get("nguon_ai", ""),
        generatedAt=latest_record.get("generated_at", ""),
        worksheet=settings.daily_report_worksheet,
    )


def list_daily_reports(settings: Settings, limit: int = 30) -> DailyReportHistoryResponse:
    credentials = load_service_account_credentials(settings)
    rows = get_sheet_values(settings, credentials, settings.daily_report_worksheet)
    if not rows or len(rows) <= 1:
        return DailyReportHistoryResponse(worksheet=settings.daily_report_worksheet, reports=[])

    header = rows[0]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        record = {
            column: row[index] if index < len(row) else ""
            for index, column in enumerate(header)
        }
        if any(value for value in record.values()):
            records.append(record)

    ordered = sorted(
        records,
        key=lambda item: (item.get("ngay", ""), item.get("generated_at", "")),
        reverse=True,
    )[:limit]

    return DailyReportHistoryResponse(
        worksheet=settings.daily_report_worksheet,
        reports=[
            DailyReportHistoryItem(
                reportDate=record.get("ngay", ""),
                tongQuat=record.get("tong_quat", ""),
                model=record.get("model_ai", ""),
                source=record.get("nguon_ai", ""),
                generatedAt=record.get("generated_at", ""),
            )
            for record in ordered
        ],
    )


def delete_daily_report(settings: Settings, report_date: str) -> DailyReportDeleteResponse:
    credentials = load_service_account_credentials(settings)
    rows = get_sheet_values(settings, credentials, settings.daily_report_worksheet)
    if not rows:
        raise ValueError("Chưa có báo cáo ngày nào trong sheet reportday.")

    header = rows[0]
    date_index = header.index("ngay") if "ngay" in header else 0
    filtered_rows = [header]
    found = False

    for row in rows[1:]:
        row_date = row[date_index] if date_index < len(row) else ""
        if row_date == report_date:
            found = True
            continue
        if any(cell for cell in row):
            filtered_rows.append(row)

    if not found:
        raise ValueError("Không tìm thấy báo cáo ngày để xóa.")

    overwrite_daily_report_rows(settings, credentials, filtered_rows)
    return DailyReportDeleteResponse(
        status="success",
        message="Đã xóa báo cáo ngày khỏi worksheet reportday.",
        reportDate=report_date,
        worksheet=settings.daily_report_worksheet,
    )
