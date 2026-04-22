from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.models import (
    SocialPlatformStatus,
    SocialPlatformSyncResult,
    SocialPlatformsStatusResponse,
    SocialPlatformsSyncResponse,
)
from app.services.google_website import get_sheet_values, load_service_account_credentials, merge_sheet_rows
from app.services.oauth_connections import (
    ensure_provider_access_token,
    get_connected_asset_ids,
    get_connection,
    get_facebook_page_tokens,
)
from app.services.website_reporting import latest_snapshot, parse_sheet_records

SOCIAL_SHEET_HEADER = [
    "sync_date",
    "platform",
    "account_id",
    "account_name",
    "content_id",
    "content_type",
    "title",
    "description",
    "published_at",
    "permalink",
    "views",
    "likes",
    "comments",
    "shares",
    "impressions",
    "engagements",
    "followers",
    "subscribers",
]


@dataclass
class PlatformConfig:
    name: str
    worksheet: str
    configured_assets: int
    has_credentials: bool
    ready: bool
    warnings: list[str]


def as_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def truncate_text(value: str, limit: int = 120) -> str:
    cleaned = " ".join((value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}..."


def get_facebook_page_ids(settings: Settings) -> list[str]:
    page_ids = settings.get_facebook_page_ids()
    if page_ids:
        return page_ids
    return get_connected_asset_ids(settings, "facebook")


def get_youtube_channel_ids(settings: Settings) -> list[str]:
    channel_ids = settings.get_youtube_channel_ids()
    if channel_ids:
        return channel_ids
    return get_connected_asset_ids(settings, "google-youtube")


def has_youtube_credentials(settings: Settings) -> bool:
    return bool((settings.youtube_api_key and settings.youtube_api_key.strip()) or get_connection(settings, "google-youtube"))


def has_facebook_credentials(settings: Settings) -> bool:
    return bool(
        (settings.facebook_access_token and settings.facebook_access_token.strip())
        or get_connection(settings, "facebook")
    )


def has_linkedin_credentials(settings: Settings) -> bool:
    return bool(
        (settings.linkedin_access_token and settings.linkedin_access_token.strip())
        or get_connection(settings, "linkedin")
    )


def has_tiktok_credentials(settings: Settings) -> bool:
    return bool(
        (settings.tiktok_access_token and settings.tiktok_access_token.strip())
        or get_connection(settings, "tiktok")
    )


def build_social_platform_configs(settings: Settings) -> list[PlatformConfig]:
    facebook_page_ids = get_facebook_page_ids(settings)
    linkedin_org_ids = settings.get_linkedin_organization_ids()
    youtube_channel_ids = get_youtube_channel_ids(settings)
    tiktok_assets = get_connected_asset_ids(settings, "tiktok")

    return [
        PlatformConfig(
            name="Facebook",
            worksheet=settings.facebook_worksheet,
            configured_assets=len(facebook_page_ids),
            has_credentials=has_facebook_credentials(settings),
            ready=bool(facebook_page_ids and has_facebook_credentials(settings)),
            warnings=(
                ([] if facebook_page_ids else ["Thiếu page ID Facebook. Hãy kết nối OAuth hoặc điền FACEBOOK_PAGE_IDS_JSON."])
                + ([] if has_facebook_credentials(settings) else ["Thiếu quyền truy cập Facebook."])
            ),
        ),
        PlatformConfig(
            name="LinkedIn",
            worksheet=settings.linkedin_worksheet,
            configured_assets=len(linkedin_org_ids),
            has_credentials=has_linkedin_credentials(settings),
            ready=bool(linkedin_org_ids and has_linkedin_credentials(settings)),
            warnings=(
                ([] if linkedin_org_ids else ["Thiếu LINKEDIN_ORGANIZATION_ID hoặc LINKEDIN_ORGANIZATION_IDS_JSON."])
                + ([] if has_linkedin_credentials(settings) else ["Thiếu quyền truy cập LinkedIn."])
            ),
        ),
        PlatformConfig(
            name="YouTube",
            worksheet=settings.youtube_worksheet,
            configured_assets=len(youtube_channel_ids),
            has_credentials=has_youtube_credentials(settings),
            ready=bool(youtube_channel_ids and has_youtube_credentials(settings)),
            warnings=(
                ([] if youtube_channel_ids else ["Thiếu channel ID YouTube. Hãy kết nối OAuth hoặc điền YOUTUBE_CHANNEL_IDS_JSON."])
                + ([] if has_youtube_credentials(settings) else ["Thiếu API key hoặc kết nối OAuth Google/YouTube."])
            ),
        ),
        PlatformConfig(
            name="TikTok",
            worksheet=settings.tiktok_worksheet,
            configured_assets=len(tiktok_assets),
            has_credentials=has_tiktok_credentials(settings),
            ready=has_tiktok_credentials(settings),
            warnings=[] if has_tiktok_credentials(settings) else ["Thiếu quyền truy cập TikTok."],
        ),
    ]


def get_social_platforms_status(settings: Settings) -> SocialPlatformsStatusResponse:
    statuses = [
        SocialPlatformStatus(
            name=config.name,
            worksheet=config.worksheet,
            ready=config.ready,
            configuredAssets=config.configured_assets,
            hasCredentials=config.has_credentials,
            message=(
                f"Sẵn sàng đồng bộ về sheet {config.worksheet}."
                if config.ready
                else f"Chưa đủ cấu hình để đồng bộ về sheet {config.worksheet}."
            ),
            warnings=config.warnings,
        )
        for config in build_social_platform_configs(settings)
    ]
    return SocialPlatformsStatusResponse(spreadsheetId=settings.google_sheet_id, statuses=statuses)


def write_social_platform_sheet(settings: Settings, worksheet: str, rows: list[list[str]]) -> str:
    credentials = load_service_account_credentials(settings)
    existing_rows = get_sheet_values(settings, credentials, worksheet)
    merged_rows = merge_sheet_rows(
        existing_rows,
        rows,
        key_columns=["sync_date", "platform", "account_id", "content_id"],
    )

    from googleapiclient.discovery import build

    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
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


async def fetch_facebook_rows(settings: Settings, snapshot_date: str) -> list[list[str]]:
    page_ids = get_facebook_page_ids(settings)
    user_access_token = settings.facebook_access_token or await ensure_provider_access_token("facebook", settings)
    if not page_ids or not user_access_token:
        raise ValueError("Thiếu cấu hình Facebook.")

    page_tokens = get_facebook_page_tokens(settings)
    rows: list[list[str]] = [SOCIAL_SHEET_HEADER]
    async with httpx.AsyncClient(timeout=45.0) as client:
        for page_id in page_ids:
            access_token = page_tokens.get(page_id) or user_access_token
            page_response = await client.get(
                f"https://graph.facebook.com/v24.0/{page_id}",
                params={
                    "fields": "id,name,followers_count,fan_count,link",
                    "access_token": access_token,
                },
            )
            page_response.raise_for_status()
            page_data = page_response.json()
            page_name = str(page_data.get("name", page_id))
            followers = as_int(page_data.get("followers_count") or page_data.get("fan_count"))

            rows.append(
                [
                    snapshot_date,
                    "facebook",
                    page_id,
                    page_name,
                    page_id,
                    "page_profile",
                    page_name,
                    "",
                    "",
                    str(page_data.get("link", f"https://facebook.com/{page_id}")),
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    str(followers),
                    "0",
                ]
            )

            posts_response = await client.get(
                f"https://graph.facebook.com/v24.0/{page_id}/posts",
                params={
                    "fields": "id,message,created_time,permalink_url,shares,reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)",
                    "limit": 25,
                    "access_token": access_token,
                },
            )
            posts_response.raise_for_status()
            for post in posts_response.json().get("data", []):
                likes = as_int(post.get("reactions", {}).get("summary", {}).get("total_count"))
                comments = as_int(post.get("comments", {}).get("summary", {}).get("total_count"))
                shares = as_int(post.get("shares", {}).get("count"))
                message = str(post.get("message") or "Bài đăng Facebook")
                rows.append(
                    [
                        snapshot_date,
                        "facebook",
                        page_id,
                        page_name,
                        str(post.get("id", "")),
                        "post",
                        truncate_text(message),
                        message,
                        str(post.get("created_time", "")),
                        str(post.get("permalink_url", "")),
                        "0",
                        str(likes),
                        str(comments),
                        str(shares),
                        "0",
                        str(likes + comments + shares),
                        str(followers),
                        "0",
                    ]
                )
    return rows


def parse_linkedin_post_text(post: dict[str, Any]) -> str:
    commentary = post.get("commentary")
    if isinstance(commentary, str):
        return commentary
    if isinstance(commentary, dict) and isinstance(commentary.get("text"), str):
        return str(commentary.get("text"))
    return ""


async def fetch_linkedin_rows(settings: Settings, snapshot_date: str) -> list[list[str]]:
    organization_ids = settings.get_linkedin_organization_ids()
    access_token = settings.linkedin_access_token or await ensure_provider_access_token("linkedin", settings)
    if not organization_ids or not access_token:
        raise ValueError("Thiếu cấu hình LinkedIn.")

    rows: list[list[str]] = [SOCIAL_SHEET_HEADER]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": settings.linkedin_api_version,
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        for organization_id in organization_ids:
            author_urn = f"urn:li:organization:{organization_id}"
            encoded_author = quote(author_urn, safe="")
            posts_response = await client.get(
                f"https://api.linkedin.com/rest/posts?q=author&author={encoded_author}&count=25&sortBy=LAST_MODIFIED",
                headers=headers,
            )
            posts_response.raise_for_status()

            rows.append(
                [
                    snapshot_date,
                    "linkedin",
                    organization_id,
                    author_urn,
                    organization_id,
                    "organization_profile",
                    author_urn,
                    "",
                    "",
                    "",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                ]
            )

            for post in posts_response.json().get("elements", []):
                post_urn = str(post.get("id") or post.get("urn") or post.get("entity") or "")
                comments = 0
                likes = 0
                if post_urn:
                    metadata_response = await client.get(
                        f"https://api.linkedin.com/rest/socialMetadata/{quote(post_urn, safe='')}",
                        headers=headers,
                    )
                    if metadata_response.status_code < 400:
                        metadata = metadata_response.json()
                        comments = as_int(metadata.get("commentSummary", {}).get("count"))
                        likes = sum(
                            as_int(item.get("count"))
                            for item in metadata.get("reactionSummaries", {}).values()
                            if isinstance(item, dict)
                        )

                text = parse_linkedin_post_text(post)
                rows.append(
                    [
                        snapshot_date,
                        "linkedin",
                        organization_id,
                        author_urn,
                        post_urn or str(post.get("createdAt", "")),
                        "post",
                        truncate_text(text or "Bài đăng LinkedIn"),
                        text,
                        str(post.get("publishedAt") or post.get("createdAt") or ""),
                        "",
                        "0",
                        str(likes),
                        str(comments),
                        "0",
                        "0",
                        str(likes + comments),
                        "0",
                        "0",
                    ]
                )
    return rows


async def fetch_youtube_rows(settings: Settings, snapshot_date: str) -> list[list[str]]:
    channel_ids = get_youtube_channel_ids(settings)
    oauth_token = await ensure_provider_access_token("google-youtube", settings)
    api_key = settings.youtube_api_key
    if not channel_ids or not (api_key or oauth_token):
        raise ValueError("Thiếu cấu hình YouTube.")

    rows: list[list[str]] = [SOCIAL_SHEET_HEADER]
    async with httpx.AsyncClient(timeout=45.0) as client:
        request_headers: dict[str, str] = {}
        channels_params = {"part": "snippet,statistics,contentDetails"}
        if oauth_token:
            request_headers["Authorization"] = f"Bearer {oauth_token}"
            channels_params["id"] = ",".join(channel_ids)
        else:
            channels_params["id"] = ",".join(channel_ids)
            channels_params["key"] = api_key or ""

        channels_response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers=request_headers,
            params=channels_params,
        )
        channels_response.raise_for_status()

        for channel in channels_response.json().get("items", []):
            channel_id = str(channel.get("id", ""))
            channel_name = str(channel.get("snippet", {}).get("title", channel_id))
            channel_stats = channel.get("statistics", {})
            subscribers = as_int(channel_stats.get("subscriberCount"))
            channel_views = as_int(channel_stats.get("viewCount"))
            uploads_playlist_id = str(channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""))

            rows.append(
                [
                    snapshot_date,
                    "youtube",
                    channel_id,
                    channel_name,
                    channel_id,
                    "channel_profile",
                    channel_name,
                    str(channel.get("snippet", {}).get("description", "")),
                    "",
                    f"https://www.youtube.com/channel/{channel_id}",
                    str(channel_views),
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    str(subscribers),
                ]
            )

            if not uploads_playlist_id:
                continue

            playlist_params = {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": 25,
            }
            if oauth_token:
                playlist_headers = {"Authorization": f"Bearer {oauth_token}"}
            else:
                playlist_headers = {}
                playlist_params["key"] = api_key or ""

            playlist_response = await client.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                headers=playlist_headers,
                params=playlist_params,
            )
            playlist_response.raise_for_status()
            video_ids = [
                str(item.get("contentDetails", {}).get("videoId", ""))
                for item in playlist_response.json().get("items", [])
                if item.get("contentDetails", {}).get("videoId")
            ]
            if not video_ids:
                continue

            videos_params = {
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
            }
            if oauth_token:
                videos_headers = {"Authorization": f"Bearer {oauth_token}"}
            else:
                videos_headers = {}
                videos_params["key"] = api_key or ""

            videos_response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                headers=videos_headers,
                params=videos_params,
            )
            videos_response.raise_for_status()
            for video in videos_response.json().get("items", []):
                video_id = str(video.get("id", ""))
                video_stats = video.get("statistics", {})
                likes = as_int(video_stats.get("likeCount"))
                comments = as_int(video_stats.get("commentCount"))
                views = as_int(video_stats.get("viewCount"))
                rows.append(
                    [
                        snapshot_date,
                        "youtube",
                        channel_id,
                        channel_name,
                        video_id,
                        "video",
                        str(video.get("snippet", {}).get("title", "Video YouTube")),
                        str(video.get("snippet", {}).get("description", "")),
                        str(video.get("snippet", {}).get("publishedAt", "")),
                        f"https://www.youtube.com/watch?v={video_id}",
                        str(views),
                        str(likes),
                        str(comments),
                        "0",
                        "0",
                        str(views + likes + comments),
                        "0",
                        str(subscribers),
                    ]
                )
    return rows


async def fetch_tiktok_rows(settings: Settings, snapshot_date: str) -> list[list[str]]:
    access_token = settings.tiktok_access_token or await ensure_provider_access_token("tiktok", settings)
    if not access_token:
        raise ValueError("Thiếu cấu hình TikTok.")

    rows: list[list[str]] = [SOCIAL_SHEET_HEADER]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        user_response = await client.get(
            "https://open.tiktokapis.com/v2/user/info/",
            params={"fields": "open_id,display_name,profile_deep_link,bio_description"},
            headers=headers,
        )
        user_response.raise_for_status()
        user_data = user_response.json().get("data", {}).get("user", {})
        open_id = str(user_data.get("open_id") or settings.tiktok_open_id or "tiktok_user")
        display_name = str(user_data.get("display_name") or "TikTok")

        rows.append(
            [
                snapshot_date,
                "tiktok",
                open_id,
                display_name,
                open_id,
                "profile",
                display_name,
                str(user_data.get("bio_description", "")),
                "",
                str(user_data.get("profile_deep_link", "")),
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
            ]
        )

        list_response = await client.post(
            "https://open.tiktokapis.com/v2/video/list/",
            params={"fields": "id,title,video_description,duration,share_url,embed_link"},
            headers=headers,
            json={"max_count": 20},
        )
        list_response.raise_for_status()
        video_ids = [
            str(video.get("id", ""))
            for video in list_response.json().get("data", {}).get("videos", [])
            if video.get("id")
        ]
        if not video_ids:
            return rows

        query_response = await client.post(
            "https://open.tiktokapis.com/v2/video/query/",
            params={
                "fields": "id,title,video_description,duration,create_time,share_url,embed_link,like_count,comment_count,share_count,view_count"
            },
            headers=headers,
            json={"filters": {"video_ids": video_ids}},
        )
        query_response.raise_for_status()
        for video in query_response.json().get("data", {}).get("videos", []):
            likes = as_int(video.get("like_count"))
            comments = as_int(video.get("comment_count"))
            shares = as_int(video.get("share_count"))
            views = as_int(video.get("view_count"))
            rows.append(
                [
                    snapshot_date,
                    "tiktok",
                    open_id,
                    display_name,
                    str(video.get("id", "")),
                    "video",
                    str(video.get("title") or "Video TikTok"),
                    str(video.get("video_description", "")),
                    str(video.get("create_time", "")),
                    str(video.get("share_url") or video.get("embed_link") or ""),
                    str(views),
                    str(likes),
                    str(comments),
                    str(shares),
                    "0",
                    str(views + likes + comments + shares),
                    "0",
                    "0",
                ]
            )
    return rows


def load_social_sheet_data(settings: Settings) -> dict[str, list[dict[str, str]]]:
    credentials = load_service_account_credentials(settings)
    sheets = {
        "Facebook": settings.facebook_worksheet,
        "LinkedIn": settings.linkedin_worksheet,
        "YouTube": settings.youtube_worksheet,
        "TikTok": settings.tiktok_worksheet,
    }
    datasets: dict[str, list[dict[str, str]]] = {}
    for platform_name, worksheet in sheets.items():
        rows = get_sheet_values(settings, credentials, worksheet)
        datasets[platform_name] = parse_sheet_records(rows)
    return datasets


def latest_social_channel_rows(settings: Settings) -> dict[str, list[dict[str, str]]]:
    datasets = load_social_sheet_data(settings)
    snapshots: dict[str, list[dict[str, str]]] = {}
    for platform_name, records in datasets.items():
        _, rows = latest_snapshot(records)
        snapshots[platform_name] = rows
    return snapshots


async def sync_social_platforms(settings: Settings) -> SocialPlatformsSyncResponse:
    if not settings.google_sheet_id:
        raise ValueError("Thiếu GOOGLE_SHEET_ID để ghi dữ liệu social vào Google Sheets.")
    if not (
        (settings.google_service_account_json and settings.google_service_account_json.strip())
        or (settings.google_service_account_file and settings.google_service_account_file.strip())
    ):
        raise ValueError("Thiếu GOOGLE_SERVICE_ACCOUNT_JSON hoặc GOOGLE_SERVICE_ACCOUNT_FILE.")

    configs = build_social_platform_configs(settings)
    if not any(config.ready for config in configs):
        raise ValueError("Chưa có nền tảng social nào đủ cấu hình để đồng bộ.")

    snapshot_date = date.today().isoformat()
    results: list[SocialPlatformSyncResult] = []
    warnings: list[str] = []
    fetchers = {
        "Facebook": fetch_facebook_rows,
        "LinkedIn": fetch_linkedin_rows,
        "YouTube": fetch_youtube_rows,
        "TikTok": fetch_tiktok_rows,
    }

    for config in configs:
        if not config.ready:
            results.append(
                SocialPlatformSyncResult(
                    platform=config.name,
                    worksheet=config.worksheet,
                    rows=0,
                    updatedRange="",
                    status="skipped",
                    detail="Chưa đủ cấu hình để đồng bộ.",
                )
            )
            warnings.extend(f"{config.name}: {warning}" for warning in config.warnings)
            continue

        try:
            rows = await fetchers[config.name](settings, snapshot_date)
            updated_range = write_social_platform_sheet(settings, config.worksheet, rows)
            results.append(
                SocialPlatformSyncResult(
                    platform=config.name,
                    worksheet=config.worksheet,
                    rows=max(len(rows) - 1, 0),
                    updatedRange=updated_range,
                    status="success",
                    detail=f"Đã đồng bộ {max(len(rows) - 1, 0)} dòng về sheet {config.worksheet}.",
                )
            )
        except Exception as exc:
            warnings.append(f"{config.name}: {exc}")
            results.append(
                SocialPlatformSyncResult(
                    platform=config.name,
                    worksheet=config.worksheet,
                    rows=0,
                    updatedRange="",
                    status="warning",
                    detail=f"Đồng bộ thất bại: {exc}",
                )
            )

    success_count = len([result for result in results if result.status == "success"])
    return SocialPlatformsSyncResponse(
        status="partial_success" if warnings else "success",
        message=(
            f"Đã đồng bộ {success_count} nền tảng social vào Google Sheets."
            if success_count
            else "Chưa đồng bộ được nền tảng social nào."
        ),
        spreadsheetId=settings.google_sheet_id,
        results=results,
        warnings=warnings,
    )
