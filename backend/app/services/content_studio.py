from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.models import (
    ContentDraft,
    ContentDraftConfirmResponse,
    ContentDraftGenerateResponse,
    ContentDraftListResponse,
    MarketingPromptRequest,
    PublishTargetResult,
)
from app.services.google_website import get_sheet_values, load_service_account_credentials, merge_sheet_rows
from app.services.ollama_client import generate_text_with_model
from app.services.social_platforms import get_social_platforms_status
from app.services.website_reporting import parse_sheet_records

BASE_DIR = Path(__file__).resolve().parents[2]
CONTENT_MD_DIR = BASE_DIR / "storage" / "content_markdown"
OUTLINE_MODEL = "llama3.2:3b"
IMAGE_MODEL = "llava"
SEO_MODEL = "qwen2.5:3b"
CONTENT_RECORDS_CACHE_TTL_SECONDS = 45
_CONTENT_RECORDS_CACHE: dict[str, tuple[datetime, list[dict[str, str]]]] = {}
IMAGE_SLOT_PATTERN = re.compile(
    r"<!--\s*IMAGE_SLOT:\s*(?P<slot_id>[a-zA-Z0-9_-]+)\s*-->\s*"
    r"-\s*Vi tri chen:\s*(?P<placement>.+?)\s*"
    r"-\s*Mo ta anh:\s*(?P<description>.+?)(?=\n(?:<!--\s*IMAGE_SLOT:|\Z))",
    re.DOTALL,
)

CONTENT_DRAFT_HEADER = [
    "draft_id",
    "created_at",
    "updated_at",
    "status",
    "requested_platforms",
    "goal",
    "tone",
    "brief",
    "generated_content",
    "meta_title",
    "meta_description",
    "keywords",
    "article_body",
    "outline_model",
    "image_model",
    "seo_model",
    "model_ai",
    "nguon_ai",
    "confirmed_at",
    "published_at",
    "dispatch_status",
    "dispatch_results_json",
]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_content_sheet_name(settings: Settings) -> str:
    return settings.ai_content_posts_worksheet


def build_content_cache_key(settings: Settings) -> str:
    return f"{settings.google_sheet_id}:{get_content_sheet_name(settings)}"


def invalidate_content_records_cache(settings: Settings | None = None) -> None:
    if settings is None:
        _CONTENT_RECORDS_CACHE.clear()
        return
    _CONTENT_RECORDS_CACHE.pop(build_content_cache_key(settings), None)


def ensure_markdown_dir() -> Path:
    CONTENT_MD_DIR.mkdir(parents=True, exist_ok=True)
    return CONTENT_MD_DIR


def build_markdown_path(draft_id: str) -> str:
    return str(ensure_markdown_dir() / f"{draft_id}.md")


def read_markdown_file(markdown_path: str | None) -> str:
    if not markdown_path:
        return ""
    path = Path(markdown_path)
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def write_markdown_file(draft_id: str, content: str) -> str:
    path = Path(build_markdown_path(draft_id))
    path.write_text(content, encoding="utf-8")
    return str(path)


def split_platforms(raw_value: str) -> list[str]:
    normalized = raw_value.replace("+", ",").replace("/", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def serialize_dispatch_results(results: list[PublishTargetResult]) -> str:
    return json.dumps([result.model_dump() for result in results], ensure_ascii=False)


def deserialize_dispatch_results(raw_value: str) -> list[PublishTargetResult]:
    if not raw_value.strip():
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    results: list[PublishTargetResult] = []
    for item in parsed:
        if isinstance(item, dict):
            try:
                results.append(PublishTargetResult.model_validate(item))
            except Exception:
                continue
    return results


def write_content_rows(settings: Settings, rows: list[list[str]]) -> str:
    credentials = load_service_account_credentials(settings)
    worksheet = get_content_sheet_name(settings)
    existing_rows = get_sheet_values(settings, credentials, worksheet)
    merged_rows = merge_sheet_rows(existing_rows, rows, key_columns=["draft_id"])

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
    invalidate_content_records_cache(settings)
    return str(response.get("updatedRange", ""))


def load_content_records(settings: Settings) -> list[dict[str, str]]:
    cache_key = build_content_cache_key(settings)
    cached = _CONTENT_RECORDS_CACHE.get(cache_key)
    if cached and (datetime.now(UTC) - cached[0]).total_seconds() < CONTENT_RECORDS_CACHE_TTL_SECONDS:
        return deepcopy(cached[1])

    credentials = load_service_account_credentials(settings)
    rows = get_sheet_values(settings, credentials, get_content_sheet_name(settings))
    records = parse_sheet_records(rows)
    _CONTENT_RECORDS_CACHE[cache_key] = (datetime.now(UTC), deepcopy(records))
    return deepcopy(records)


def build_outline_prompt(payload: MarketingPromptRequest) -> str:
    return "\n".join(
        [
            "Ban la SEO assistant.",
            "Hay tao dan bai bai viet bang Markdown, viet bang tieng Viet co dau, ro rang va co tinh tong quat.",
            "Bat buoc tra ve DUY NHAT Markdown, khong giai thich ngoai le.",
            "Format bat buoc:",
            "# Dan bai bai viet",
            "## Muc lon",
            "- Y chinh ...",
            "",
            "Mỗi vị trí chèn ảnh phải dùng đúng mẫu sau:",
            "<!-- IMAGE_SLOT: image-1 -->",
            "- Vi tri chen: ...",
            "- Mo ta anh: ...",
            "",
            f"Nen tang dich: {payload.platform}",
            f"Muc tieu: {payload.goal}",
            f"Giong van: {payload.tone}",
            f"Brief: {payload.brief}",
            "Hay tao dan bai co 5-7 phan chinh va it nhat 2 IMAGE_SLOT.",
        ]
    )


def fallback_outline(payload: MarketingPromptRequest) -> str:
    return "\n".join(
        [
            "# Dan bai bai viet",
            "## Mo dau",
            f"- Neu van de chinh lien quan den {payload.goal.lower()}.",
            f"- Dat boi canh cho {payload.platform}.",
            "",
            "## Thach thuc hien tai",
            "- Liet ke cac diem dau trong van hanh marketing va SEO.",
            "",
            "<!-- IMAGE_SLOT: image-1 -->",
            "- Vi tri chen: Sau phan thach thuc hien tai.",
            f"- Mo ta anh: Anh dashboard tong hop the hien KPI va muc tieu {payload.goal.lower()}.",
            "",
            "## Giai phap de xuat",
            "- Trinh bay quy trinh, cong cu va cach do luong.",
            "",
            "## Cach trien khai",
            "- Chia nho cac buoc hanh dong va KPI can theo doi.",
            "",
            "<!-- IMAGE_SLOT: image-2 -->",
            "- Vi tri chen: Truoc phan ket luan.",
            "- Mo ta anh: Anh doi ngu dang xem quy trinh lam viec va lich dang bai tren man hinh.",
            "",
            "## Ket luan",
            "- Tong ket loi ich chinh.",
            "- Chen CTA ro rang.",
        ]
    )


def extract_image_slots(markdown_text: str) -> list[dict[str, str]]:
    slots: list[dict[str, str]] = []
    for match in IMAGE_SLOT_PATTERN.finditer(markdown_text):
        slots.append(
            {
                "slotId": match.group("slot_id").strip(),
                "placement": " ".join(match.group("placement").split()),
                "description": " ".join(match.group("description").split()),
            }
        )
    return slots


def fallback_image_metadata(slots: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "slotId": slot["slotId"],
            "caption": f"Hinh minh hoa cho {slot['placement'].lower()}.",
            "altText": slot["description"],
        }
        for slot in slots
    ]


def build_image_prompt(markdown_text: str, slots: list[dict[str, str]]) -> str:
    slot_lines = "\n".join(
        [
            f"- {slot['slotId']}: vi tri {slot['placement']}; mo ta {slot['description']}"
            for slot in slots
        ]
    )
    return "\n".join(
        [
            "Ban dang dung model llava o che do van ban de tao metadata cho anh duoc tham chieu trong markdown.",
            "Hay dua tren mo ta anh co san de tao JSON hop le.",
            "Schema bat buoc:",
            '[{"slotId":"image-1","caption":"...","altText":"..."}]',
            "Khong them text ngoai JSON.",
            "",
            "Markdown dau vao:",
            markdown_text,
            "",
            "Danh sach anh can xu ly:",
            slot_lines,
        ]
    )


def parse_image_metadata(raw_text: str, slots: list[dict[str, str]]) -> list[dict[str, str]]:
    cleaned = raw_text.strip()
    start_index = cleaned.find("[")
    end_index = cleaned.rfind("]")
    if start_index == -1 or end_index == -1:
        return fallback_image_metadata(slots)

    try:
        parsed = json.loads(cleaned[start_index : end_index + 1])
    except json.JSONDecodeError:
        return fallback_image_metadata(slots)

    if not isinstance(parsed, list):
        return fallback_image_metadata(slots)

    metadata_by_slot: dict[str, dict[str, str]] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        slot_id = str(item.get("slotId", "")).strip()
        if not slot_id:
            continue
        metadata_by_slot[slot_id] = {
            "slotId": slot_id,
            "caption": str(item.get("caption", "")).strip(),
            "altText": str(item.get("altText", "")).strip(),
        }

    fallback = fallback_image_metadata(slots)
    final_metadata: list[dict[str, str]] = []
    for item in fallback:
        current = metadata_by_slot.get(item["slotId"], {})
        final_metadata.append(
            {
                "slotId": item["slotId"],
                "caption": current.get("caption") or item["caption"],
                "altText": current.get("altText") or item["altText"],
            }
        )
    return final_metadata


def inject_image_metadata(markdown_text: str, metadata: list[dict[str, str]]) -> str:
    updated = markdown_text
    for item in metadata:
        replacement = "\n".join(
            [
                f"<!-- IMAGE_SLOT: {item['slotId']} -->",
                f"- Vi tri chen: {_find_slot_value(markdown_text, item['slotId'], 'placement')}",
                f"- Mo ta anh: {_find_slot_value(markdown_text, item['slotId'], 'description')}",
                f"- Caption: {item['caption']}",
                f"- Alt text: {item['altText']}",
            ]
        )
        pattern = re.compile(
            rf"<!--\s*IMAGE_SLOT:\s*{re.escape(item['slotId'])}\s*-->\s*"
            r"-\s*Vi tri chen:\s*.+?\s*"
            r"-\s*Mo ta anh:\s*.+?(?=\n(?:<!--\s*IMAGE_SLOT:|\Z))",
            re.DOTALL,
        )
        updated = pattern.sub(replacement, updated)
    return updated


def _find_slot_value(markdown_text: str, slot_id: str, field: str) -> str:
    for slot in extract_image_slots(markdown_text):
        if slot["slotId"] == slot_id:
            return slot["placement"] if field == "placement" else slot["description"]
    return ""


def build_seo_prompt(markdown_text: str, payload: MarketingPromptRequest) -> str:
    return "\n".join(
        [
            "Ban la SEO assistant chuyen viet bai chuan SEO bang tieng Viet co dau.",
            "Hay dung file Markdown duoi day de viet mot bai hoan chinh.",
            "Bat buoc tra ve Markdown voi cac muc sau va dung dung ten heading:",
            "# Meta title",
            "# Meta description",
            "# Keywords",
            "# Noi dung bai viet",
            "Noi dung bai viet phai co cau truc H2/H3, mach lac, co yeu to SEO, va tan dung thong tin anh da duoc bo sung.",
            "Yeu cau chat luong:",
            "- Meta title toi da 60 ky tu.",
            "- Meta description 140-160 ky tu.",
            "- Keywords viet tren 1 dong, cach nhau boi dau phay.",
            "- Phan '# Noi dung bai viet' phai la mot bai hoan chinh co mo dau, than bai, ket luan va CTA.",
            "- Khong duoc tra ve dan bai. Phai la bai viet day du.",
            f"Nen tang dich: {payload.platform}",
            f"Muc tieu: {payload.goal}",
            f"Giong van: {payload.tone}",
            "",
            "Markdown dau vao:",
            markdown_text,
        ]
    )


def extract_section_bullets(markdown_text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_bullets: list[str] = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if current_heading:
                sections.append((current_heading, current_bullets))
            current_heading = line[3:].strip()
            current_bullets = []
            continue
        if line.startswith("- "):
            current_bullets.append(line[2:].strip())

    if current_heading:
        sections.append((current_heading, current_bullets))
    return sections


def build_article_body_from_markdown(payload: MarketingPromptRequest, markdown_text: str) -> str:
    sections = extract_section_bullets(markdown_text)
    paragraphs: list[str] = [
        "## Mở đầu",
        (
            f"{payload.goal} đang là mục tiêu trọng tâm của nhiều đội ngũ marketing, nhưng để đạt hiệu quả bền vững "
            f"thì cần kết hợp nội dung, SEO và quy trình triển khai rõ ràng cho {payload.platform.lower()}."
        ),
        (
            f"Bài viết này tổng hợp một lộ trình thực tế theo giọng điệu {payload.tone.lower()}, giúp doanh nghiệp "
            "xây dựng nội dung vừa tối ưu tìm kiếm vừa có khả năng hỗ trợ chuyển đổi."
        ),
    ]

    for heading, bullets in sections:
        if heading.lower().startswith("dan bai"):
            continue
        paragraphs.append(f"## {heading}")
        if bullets:
            intro = " ".join(bullets[:2])
            paragraphs.append(
                f"{heading} là phần quan trọng trong chiến lược SEO vì nó tác động trực tiếp đến khả năng tiếp cận, mức độ tin cậy và hành vi người đọc. {intro}"
            )
            for bullet in bullets:
                paragraphs.append(f"### Điểm cần lưu ý\n{bullet}. Đây là ý cần được triển khai thành nội dung cụ thể, có số liệu hoặc ví dụ minh họa để tăng độ thuyết phục.")
        else:
            paragraphs.append(
                f"{heading} cần được triển khai bằng nội dung có chiều sâu, kết nối với mục tiêu {payload.goal.lower()} và nhu cầu thực tế của người đọc."
            )

    paragraphs.extend(
        [
            "## Kết luận",
            (
                f"Một bài viết chuẩn SEO không chỉ dừng ở việc có từ khóa, mà còn phải tổ chức nội dung mạch lạc, có hình ảnh đúng ngữ cảnh "
                f"và dẫn dắt người đọc tới hành động phù hợp với mục tiêu {payload.goal.lower()}."
            ),
            (
                f"Nếu bạn đang cần đẩy mạnh hiệu quả cho {payload.platform.lower()}, hãy dùng cấu trúc trên như một khung chuẩn để xuất bản nội dung đều đặn, "
                "dễ đo lường và dễ tối ưu ở các vòng tiếp theo."
            ),
        ]
    )

    return "\n\n".join(paragraphs)


def fallback_seo_article(payload: MarketingPromptRequest, markdown_text: str) -> str:
    article_body = build_article_body_from_markdown(payload, markdown_text)
    keywords = [payload.goal, payload.platform, "SEO assistant", "nội dung AI", "bài viết chuẩn SEO"]
    return "\n".join(
        [
            "# Meta title",
            f"{payload.goal} cho {payload.platform} | Bài viết chuẩn SEO",
            "",
            "# Meta description",
            (
                f"Bài viết hướng dẫn cách triển khai {payload.goal.lower()} cho {payload.platform.lower()} "
                "bằng quy trình nội dung AI, hình ảnh và tối ưu SEO bài bản."
            ),
            "",
            "# Keywords",
            ", ".join(keywords),
            "",
            "# Noi dung bai viet",
            article_body,
        ]
    )


def is_complete_seo_article(content: str) -> bool:
    normalized = content.lower()
    has_sections = (
        "# meta title" in normalized
        and "# meta description" in normalized
        and "# keywords" in normalized
        and "# noi dung bai viet" in normalized
    )
    has_subheadings = "## " in content
    body_length = len(content.split())
    return has_sections and has_subheadings and body_length >= 250


def normalize_seo_article(content: str, payload: MarketingPromptRequest, markdown_text: str) -> str:
    if is_complete_seo_article(content):
        return content.strip()

    fallback = fallback_seo_article(payload, markdown_text)

    extracted_meta_title = re.search(r"#\s*Meta title\s*(.+?)(?=\n#|\Z)", content, re.DOTALL | re.IGNORECASE)
    extracted_meta_description = re.search(r"#\s*Meta description\s*(.+?)(?=\n#|\Z)", content, re.DOTALL | re.IGNORECASE)
    extracted_keywords = re.search(r"#\s*Keywords\s*(.+?)(?=\n#|\Z)", content, re.DOTALL | re.IGNORECASE)
    extracted_body = re.search(r"#\s*(?:Noi dung bai viet|Nội dung bài viết)\s*(.+?)(?=\Z)", content, re.DOTALL | re.IGNORECASE)

    meta_title = extracted_meta_title.group(1).strip() if extracted_meta_title else None
    meta_description = extracted_meta_description.group(1).strip() if extracted_meta_description else None
    keywords = extracted_keywords.group(1).strip() if extracted_keywords else None
    body = extracted_body.group(1).strip() if extracted_body else None

    return "\n".join(
        [
            "# Meta title",
            meta_title or f"{payload.goal} cho {payload.platform} | Bài viết chuẩn SEO",
            "",
            "# Meta description",
            meta_description
            or (
                f"Bài viết hướng dẫn cách triển khai {payload.goal.lower()} cho {payload.platform.lower()} "
                "bằng quy trình nội dung AI, hình ảnh và tối ưu SEO bài bản."
            ),
            "",
            "# Keywords",
            keywords or f"{payload.goal}, {payload.platform}, SEO assistant, bài viết chuẩn SEO",
            "",
            "# Noi dung bai viet",
            body or fallback.split("# Noi dung bai viet", 1)[1].strip(),
        ]
    )


def build_pipeline_markdown(outline_markdown: str, enriched_markdown: str, seo_markdown: str) -> str:
    return "\n\n".join(
        [
            "# Buoc 1 - Dan bai Markdown",
            outline_markdown.strip(),
            "# Buoc 2 - Dan bai da bo sung caption va alt-text",
            enriched_markdown.strip(),
            "# Buoc 3 - Bai viet SEO hoan chinh",
            seo_markdown.strip(),
        ]
    )


def extract_seo_section(content: str, heading: str) -> str:
    pattern = re.compile(
        rf"#\s*{re.escape(heading)}\s*(.+?)(?=\n#\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def normalize_keywords_text(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.replace("\n", " ").replace("\r", " ")).strip(" ,")
    return cleaned


def strip_markdown_syntax(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^>\s*", "", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"\*(.*?)\*", r"\1", line)
        line = re.sub(r"`(.*?)`", r"\1", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def build_sheet_ready_article(seo_markdown: str, payload: MarketingPromptRequest) -> tuple[str, str, str, str, str]:
    meta_title = strip_markdown_syntax(extract_seo_section(seo_markdown, "Meta title")) or (
        f"{payload.goal} cho {payload.platform}"
    )
    meta_description = strip_markdown_syntax(extract_seo_section(seo_markdown, "Meta description")) or (
        f"Bài viết chuẩn SEO về {payload.goal.lower()} cho {payload.platform.lower()}."
    )
    keywords = normalize_keywords_text(strip_markdown_syntax(extract_seo_section(seo_markdown, "Keywords"))) or (
        f"{payload.goal}, {payload.platform}, bài viết chuẩn SEO"
    )
    article_body = strip_markdown_syntax(extract_seo_section(seo_markdown, "Noi dung bai viet")) or strip_markdown_syntax(
        seo_markdown
    )
    final_article = "\n\n".join(
        [
            f"Meta title: {meta_title}",
            f"Meta description: {meta_description}",
            f"Keywords: {keywords}",
            "Nội dung bài viết:",
            article_body,
        ]
    )
    return final_article, meta_title, meta_description, keywords, article_body


async def run_markdown_pipeline(
    payload: MarketingPromptRequest,
    settings: Settings,
) -> tuple[str, str, str, str, str]:
    outline_markdown, _, outline_used_model = await generate_text_with_model(
        build_outline_prompt(payload),
        settings,
        requested_model=OUTLINE_MODEL,
        job_name="Tao dan bai Markdown",
    )
    if not outline_markdown:
        outline_markdown = fallback_outline(payload)
        outline_used_model = OUTLINE_MODEL

    slots = extract_image_slots(outline_markdown)
    if not slots:
        outline_markdown = fallback_outline(payload)
        slots = extract_image_slots(outline_markdown)

    image_raw_text, _, image_used_model = await generate_text_with_model(
        build_image_prompt(outline_markdown, slots),
        settings,
        requested_model=IMAGE_MODEL,
        job_name="Bo sung caption va alt-text",
    )
    metadata = parse_image_metadata(image_raw_text, slots)
    enriched_markdown = inject_image_metadata(outline_markdown, metadata)

    seo_markdown, source, seo_used_model = await generate_text_with_model(
        build_seo_prompt(enriched_markdown, payload),
        settings,
        requested_model=SEO_MODEL,
        job_name="Viet bai SEO hoan chinh",
    )
    if not seo_markdown:
        seo_markdown = fallback_seo_article(payload, enriched_markdown)
        source = "fallback"
        seo_used_model = SEO_MODEL
    else:
        seo_markdown = normalize_seo_article(seo_markdown, payload, enriched_markdown)

    return outline_markdown, enriched_markdown, seo_markdown, source, "|".join(
        [outline_used_model or OUTLINE_MODEL, image_used_model or IMAGE_MODEL, seo_used_model or SEO_MODEL]
    )


def record_to_draft(record: dict[str, str], settings: Settings) -> ContentDraft:
    draft_id = record.get("draft_id", "")
    markdown_path = build_markdown_path(draft_id) if draft_id else ""
    resolved_markdown_path = markdown_path if markdown_path and Path(markdown_path).exists() else None
    return ContentDraft(
        draftId=draft_id,
        createdAt=record.get("created_at", ""),
        updatedAt=record.get("updated_at", ""),
        status=record.get("status", "draft"),
        requestedPlatforms=record.get("requested_platforms", ""),
        goal=record.get("goal", ""),
        tone=record.get("tone", ""),
        brief=record.get("brief", ""),
        generatedContent=record.get("generated_content", ""),
        markdownPath=resolved_markdown_path,
        markdownContent=read_markdown_file(resolved_markdown_path),
        model=record.get("model_ai", ""),
        outlineModel=record.get("outline_model") or None,
        imageModel=record.get("image_model") or None,
        seoModel=record.get("seo_model") or None,
        source=record.get("nguon_ai", "fallback"),  # type: ignore[arg-type]
        worksheet=get_content_sheet_name(settings),
        confirmedAt=record.get("confirmed_at") or None,
        publishedAt=record.get("published_at") or None,
        dispatchStatus=record.get("dispatch_status", "draft"),
        dispatchResults=deserialize_dispatch_results(record.get("dispatch_results_json", "")),
    )


def list_content_drafts(settings: Settings, limit: int = 12) -> ContentDraftListResponse:
    records = load_content_records(settings)
    drafts = [
        record_to_draft(record, settings)
        for record in sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]
    ]
    return ContentDraftListResponse(worksheet=get_content_sheet_name(settings), drafts=drafts)


def find_draft_record(settings: Settings, draft_id: str) -> dict[str, str]:
    records = load_content_records(settings)
    for record in records:
        if record.get("draft_id") == draft_id:
            return record
    raise ValueError("Không tìm thấy bản nháp nội dung.")


def build_dispatch_results(settings: Settings, requested_platforms: str) -> tuple[str, list[PublishTargetResult]]:
    statuses = {item.name.lower(): item for item in get_social_platforms_status(settings).statuses}
    results: list[PublishTargetResult] = []

    for platform in split_platforms(requested_platforms):
        status = statuses.get(platform.lower())
        if status and status.ready:
            results.append(
                PublishTargetResult(
                    platform=platform,
                    status="queued",
                    detail=f"Đã xác nhận và chuyển sang hàng đợi xuất bản cho {platform}.",
                )
            )
            continue
        if status:
            warning_text = status.warnings[0] if status.warnings else f"{platform} chưa đủ cấu hình xuất bản."
            results.append(
                PublishTargetResult(
                    platform=platform,
                    status="pending_config",
                    detail=warning_text,
                )
            )
            continue
        results.append(
            PublishTargetResult(
                platform=platform,
                status="manual_review",
                detail=f"Chưa có adapter xuất bản tự động cho {platform}.",
            )
        )

    overall_status = "queued" if any(item.status == "queued" for item in results) else "manual_review"
    return overall_status, results


async def generate_content_draft(
    payload: MarketingPromptRequest,
    settings: Settings,
) -> ContentDraftGenerateResponse:
    outline_markdown, enriched_markdown, seo_markdown, source, model_trace = await run_markdown_pipeline(payload, settings)
    draft_id = uuid.uuid4().hex
    timestamp = now_iso()
    markdown_content = build_pipeline_markdown(outline_markdown, enriched_markdown, seo_markdown)
    markdown_path = write_markdown_file(draft_id, markdown_content)
    final_article, meta_title, meta_description, keywords, article_body = build_sheet_ready_article(
        seo_markdown,
        payload,
    )

    models = model_trace.split("|")
    outline_model = models[0] if len(models) > 0 else OUTLINE_MODEL
    image_model = models[1] if len(models) > 1 else IMAGE_MODEL
    seo_model = models[2] if len(models) > 2 else SEO_MODEL

    draft = ContentDraft(
        draftId=draft_id,
        createdAt=timestamp,
        updatedAt=timestamp,
        status="draft",
        requestedPlatforms=payload.platform,
        goal=payload.goal,
        tone=payload.tone,
        brief=payload.brief,
        generatedContent=final_article,
        markdownPath=markdown_path,
        markdownContent=markdown_content,
        model=seo_model,
        outlineModel=outline_model,
        imageModel=image_model,
        seoModel=seo_model,
        source=source,  # type: ignore[arg-type]
        worksheet=get_content_sheet_name(settings),
        confirmedAt=None,
        publishedAt=None,
        dispatchStatus="draft",
        dispatchResults=[],
    )

    write_content_rows(
        settings,
        [
            CONTENT_DRAFT_HEADER,
            [
                draft.draftId,
                draft.createdAt,
                draft.updatedAt,
                draft.status,
                draft.requestedPlatforms,
                draft.goal,
                draft.tone,
                draft.brief,
                draft.generatedContent,
                meta_title,
                meta_description,
                keywords,
                article_body,
                draft.outlineModel or "",
                draft.imageModel or "",
                draft.seoModel or "",
                draft.model,
                draft.source,
                "",
                "",
                draft.dispatchStatus,
                "[]",
            ],
        ],
    )

    return ContentDraftGenerateResponse(
        message=(
            f"Đã chạy pipeline {OUTLINE_MODEL} -> {IMAGE_MODEL} -> {SEO_MODEL}. "
            f"Sheet {get_content_sheet_name(settings)} chỉ lưu bài viết hoàn chỉnh; "
            "Markdown pipeline được giữ nội bộ trên backend."
        ),
        draft=draft,
    )


def confirm_content_draft(settings: Settings, draft_id: str) -> ContentDraftConfirmResponse:
    record = find_draft_record(settings, draft_id)
    confirmed_at = now_iso()
    dispatch_status, dispatch_results = build_dispatch_results(settings, record.get("requested_platforms", ""))
    record_draft_id = record.get("draft_id", "")
    markdown_path = build_markdown_path(record_draft_id) if record_draft_id else None
    if markdown_path and not Path(markdown_path).exists():
        markdown_path = None

    draft = ContentDraft(
        draftId=record_draft_id,
        createdAt=record.get("created_at", ""),
        updatedAt=confirmed_at,
        status="confirmed",
        requestedPlatforms=record.get("requested_platforms", ""),
        goal=record.get("goal", ""),
        tone=record.get("tone", ""),
        brief=record.get("brief", ""),
        generatedContent=record.get("generated_content", ""),
        markdownPath=markdown_path,
        markdownContent=read_markdown_file(markdown_path),
        model=record.get("model_ai", ""),
        outlineModel=record.get("outline_model") or None,
        imageModel=record.get("image_model") or None,
        seoModel=record.get("seo_model") or None,
        source=record.get("nguon_ai", "fallback"),  # type: ignore[arg-type]
        worksheet=get_content_sheet_name(settings),
        confirmedAt=confirmed_at,
        publishedAt=None,
        dispatchStatus=dispatch_status,
        dispatchResults=dispatch_results,
    )

    write_content_rows(
        settings,
        [
            CONTENT_DRAFT_HEADER,
            [
                draft.draftId,
                draft.createdAt,
                draft.updatedAt,
                draft.status,
                draft.requestedPlatforms,
                draft.goal,
                draft.tone,
                draft.brief,
                draft.generatedContent,
                record.get("meta_title", ""),
                record.get("meta_description", ""),
                record.get("keywords", ""),
                record.get("article_body", ""),
                draft.outlineModel or "",
                draft.imageModel or "",
                draft.seoModel or "",
                draft.model,
                draft.source,
                draft.confirmedAt or "",
                draft.publishedAt or "",
                draft.dispatchStatus,
                serialize_dispatch_results(draft.dispatchResults),
            ],
        ],
    )

    return ContentDraftConfirmResponse(
        message="Đã xác nhận nội dung và chuyển sang bước đẩy nền tảng theo cấu hình hiện có.",
        draft=draft,
    )
