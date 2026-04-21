from __future__ import annotations

import base64
from html import unescape
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import WordPressSiteConfig


def build_wordpress_headers(site: WordPressSiteConfig) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if site.username and site.application_password:
        credentials = f"{site.username}:{site.application_password}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        headers["Authorization"] = f"Basic {encoded}"
    return headers


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    return f"{scheme}://{netloc}{path}"


def extract_path_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.split("?", 1)[0].rstrip("/")
    return path or "/"


async def fetch_wordpress_posts_for_site(site: WordPressSiteConfig, per_page: int = 20) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    page = 1
    headers = build_wordpress_headers(site)
    base_url = site.base_url.rstrip("/")
    endpoints = [
        f"{base_url}/wp-json/wp/v2/posts",
        f"{base_url}/?rest_route=/wp/v2/posts",
    ]

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        while True:
            payload: list[dict[str, Any]] | None = None
            total_pages = 1
            last_error: Exception | None = None

            for endpoint in endpoints:
                try:
                    response = await client.get(
                        endpoint,
                        params={
                            "page": page,
                            "per_page": per_page,
                            "_fields": "id,date,slug,link,status,title.rendered",
                        },
                        headers=headers,
                    )
                    response.raise_for_status()
                    candidate = response.json()
                    if not isinstance(candidate, list):
                        raise ValueError(f"Unexpected WordPress response shape from {endpoint}.")
                    payload = candidate
                    total_pages = int(response.headers.get("X-WP-TotalPages", "1"))
                    break
                except Exception as exc:
                    last_error = exc

            if payload is None:
                raise ValueError(f"Unable to fetch WordPress posts for {site.name}: {last_error}")

            if not payload:
                break

            for item in payload:
                link = str(item.get("link", "")).strip()
                posts.append(
                    {
                        "site_name": site.name,
                        "id": item.get("id"),
                        "date": item.get("date", ""),
                        "slug": item.get("slug", ""),
                        "link": normalize_url(link) if link else "",
                        "status": item.get("status", ""),
                        "title": unescape(str(item.get("title", {}).get("rendered", "")).strip()),
                    }
                )

            if page >= total_pages:
                break
            page += 1

    return posts
