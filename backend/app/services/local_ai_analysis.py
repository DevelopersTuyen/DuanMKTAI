from __future__ import annotations

from datetime import datetime

from app.core.config import Settings
from app.models import LocalAiAnalysisResponse, LocalAiChannelStatus
from app.services.ollama_client import generate_text_with_ollama
from app.services.website_reporting import latest_snapshot, load_website_dataset, to_float


def format_number(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def build_channel_statuses(
    latest_website_rows: list[dict[str, str]],
    latest_post_rows: list[dict[str, str]],
    latest_gsc_rows: list[dict[str, str]],
) -> list[LocalAiChannelStatus]:
    return [
        LocalAiChannelStatus(
            name="Website",
            status="Đã kết nối",
            detail=(
                f"Có {len(latest_website_rows)} dòng GA4 theo trang, "
                f"{len(latest_post_rows)} bài WordPress và {len(latest_gsc_rows)} dòng GSC khả dụng."
            ),
            rows=len(latest_website_rows) + len(latest_post_rows) + len(latest_gsc_rows),
        ),
        LocalAiChannelStatus(
            name="Facebook",
            status="Chưa kết nối",
            detail="Chưa có sheet dữ liệu thật để AI phân tích.",
            rows=0,
        ),
        LocalAiChannelStatus(
            name="TikTok",
            status="Chưa kết nối",
            detail="Chưa có sheet dữ liệu thật để AI phân tích.",
            rows=0,
        ),
        LocalAiChannelStatus(
            name="LinkedIn",
            status="Chưa kết nối",
            detail="Chưa có sheet dữ liệu thật để AI phân tích.",
            rows=0,
        ),
        LocalAiChannelStatus(
            name="YouTube",
            status="Chưa kết nối",
            detail="Chưa có sheet dữ liệu thật để AI phân tích.",
            rows=0,
        ),
    ]


def build_analysis_prompt(
    latest_date: str,
    latest_website_rows: list[dict[str, str]],
    latest_post_rows: list[dict[str, str]],
    latest_gsc_rows: list[dict[str, str]],
    channels: list[LocalAiChannelStatus],
) -> str:
    total_sessions = sum(to_float(row.get("sessions_28d")) for row in latest_website_rows)
    total_pageviews = sum(to_float(row.get("page_views_28d")) for row in latest_website_rows)
    total_active_users = sum(to_float(row.get("active_users_28d")) for row in latest_website_rows)

    top_pages = sorted(
        latest_website_rows,
        key=lambda item: to_float(item.get("page_views_28d")),
        reverse=True,
    )[:5]
    top_posts = sorted(
        latest_post_rows,
        key=lambda item: (to_float(item.get("ga_page_views_28d")), to_float(item.get("gsc_clicks_28d"))),
        reverse=True,
    )[:5]

    top_page_lines = "\n".join(
        [
            f"- {row.get('hostname')} {row.get('page_path')}: {row.get('page_views_28d')} views, {row.get('sessions_28d')} sessions"
            for row in top_pages
        ]
    ) or "- Chưa có trang nổi bật"

    top_post_lines = "\n".join(
        [
            f"- {row.get('site')} | {row.get('title')}: {row.get('ga_page_views_28d')} views, CTR GSC {row.get('gsc_ctr_28d')}"
            for row in top_posts
        ]
    ) or "- Chưa có bài viết nổi bật"

    channel_lines = "\n".join(
        [
            f"- {channel.name}: {channel.status}. {channel.detail}"
            for channel in channels
        ]
    )

    return "\n".join(
        [
            "Bạn là chuyên gia phân tích marketing đa kênh, đang chạy trên mô hình AI cục bộ.",
            "Hãy phân tích dữ liệu thật hiện có, không bịa thêm dữ liệu cho các kênh chưa kết nối.",
            "Chỉ trả lời bằng tiếng Việt có dấu.",
            "Bố cục bắt buộc:",
            "1. Tóm tắt điều hành trong 2-3 câu.",
            "2. 3 phát hiện quan trọng nhất.",
            "3. 3 hành động ưu tiên trong 7 ngày tới.",
            "4. Ghi rõ kênh nào chưa có dữ liệu nên chưa thể kết luận.",
            "",
            f"Ngày snapshot: {latest_date or 'chưa có dữ liệu'}",
            f"Tổng sessions website: {format_number(total_sessions)}",
            f"Tổng pageviews website: {format_number(total_pageviews)}",
            f"Tổng active users website: {format_number(total_active_users)}",
            f"Số dòng GSC hiện có: {len(latest_gsc_rows)}",
            f"Số bài WordPress hiện có: {len(latest_post_rows)}",
            "",
            "Top trang website:",
            top_page_lines,
            "",
            "Top bài WordPress:",
            top_post_lines,
            "",
            "Trạng thái nguồn dữ liệu:",
            channel_lines,
        ]
    )


def build_fallback_analysis(
    latest_website_rows: list[dict[str, str]],
    latest_post_rows: list[dict[str, str]],
    latest_gsc_rows: list[dict[str, str]],
    channels: list[LocalAiChannelStatus],
) -> str:
    total_sessions = sum(to_float(row.get("sessions_28d")) for row in latest_website_rows)
    total_pageviews = sum(to_float(row.get("page_views_28d")) for row in latest_website_rows)
    top_page = max(
        latest_website_rows,
        key=lambda item: to_float(item.get("page_views_28d")),
        default={},
    )
    top_post = max(
        latest_post_rows,
        key=lambda item: to_float(item.get("ga_page_views_28d")),
        default={},
    )
    unavailable_channels = ", ".join([channel.name for channel in channels if channel.rows == 0])

    return "\n".join(
        [
            "1. Tóm tắt điều hành",
            (
                f"Website hiện là nguồn dữ liệu thật duy nhất để phân tích. "
                f"Tổng pageviews đang ở mức {format_number(total_pageviews)} và tổng sessions ở mức {format_number(total_sessions)}."
            ),
            "",
            "2. Phát hiện quan trọng",
            f"- Trang nổi bật nhất hiện tại là {top_page.get('page_path') or '/'} trên {top_page.get('hostname') or 'website chính'}.",
            f"- Hệ thống đang có {len(latest_post_rows)} bài WordPress trong sheet Post_web để theo dõi nội dung thật.",
            f"- Dữ liệu Search Console hiện có {len(latest_gsc_rows)} dòng, nên các kết luận SEO còn hạn chế nếu chưa cấp quyền GSC.",
            "",
            "3. Hành động ưu tiên 7 ngày",
            "- Tối ưu lại các trang có pageviews cao để kéo thêm chuyển đổi.",
            f"- Rà soát bài viết WordPress như '{top_post.get('title') or 'bài đang dẫn đầu'}' để bổ sung CTA và liên kết nội bộ.",
            "- Cấp quyền Search Console cho service account để AI có thể phân tích SEO thật.",
            "",
            "4. Kênh chưa có dữ liệu",
            f"- Chưa có dữ liệu thật cho các kênh: {unavailable_channels}.",
        ]
    )


async def get_local_ai_analysis(settings: Settings) -> LocalAiAnalysisResponse:
    website_records, post_records = load_website_dataset(settings)
    website_ga_rows = [record for record in website_records if record.get("source") == "google_analytics"]
    website_gsc_rows = [record for record in website_records if record.get("source") == "google_search_console"]

    latest_date, latest_website_rows = latest_snapshot(website_ga_rows)
    _, latest_gsc_rows = latest_snapshot(website_gsc_rows)
    _, latest_post_rows = latest_snapshot(post_records)

    channels = build_channel_statuses(latest_website_rows, latest_post_rows, latest_gsc_rows)
    prompt = build_analysis_prompt(latest_date, latest_website_rows, latest_post_rows, latest_gsc_rows, channels)
    generated_text, source, used_model = await generate_text_with_ollama(prompt, settings)

    if not generated_text:
        generated_text = build_fallback_analysis(latest_website_rows, latest_post_rows, latest_gsc_rows, channels)
        source = "fallback"
        used_model = settings.ollama_model

    if latest_website_rows:
        summary = (
            f"AI đang phân tích dữ liệu thật của website tại snapshot {latest_date}, "
            f"với {len(latest_website_rows)} dòng GA4 và {len(latest_post_rows)} bài WordPress."
        )
    else:
        summary = "AI cục bộ chưa có dữ liệu website thật để phân tích."

    return LocalAiAnalysisResponse(
        summary=summary,
        analysis=generated_text,
        model=used_model,
        source=source,  # type: ignore[arg-type]
        generatedAt=datetime.now().isoformat(timespec="seconds"),
        channels=channels,
    )
