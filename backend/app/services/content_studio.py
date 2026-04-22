from __future__ import annotations

import json
import re
import unicodedata
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
    GeneratedImageAsset,
    MarketingPromptRequest,
    PublishTargetResult,
)
from app.services.google_website import get_sheet_values, load_service_account_credentials, merge_sheet_rows
from app.services.local_image_generation import generate_images_for_slots
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
TOPIC_STOPWORDS = {
    "va",
    "voi",
    "cho",
    "mot",
    "nhung",
    "cac",
    "bai",
    "viet",
    "gioi",
    "thieu",
    "co",
    "kem",
    "hinh",
    "anh",
    "hay",
    "the",
    "nao",
    "theo",
    "yeu",
    "cau",
    "noi",
    "dung",
    "chuan",
    "seo",
    "tren",
    "duoi",
    "dang",
    "viet",
    "bai",
    "chu",
    "de",
    "kem",
    "hinh",
    "anh",
    "gioi",
    "thieu",
    "chuan",
    "seo",
}
TOPIC_LEADING_FILLERS = {
    "hay",
    "vui",
    "long",
    "giup",
    "toi",
    "cho",
    "minh",
    "viet",
    "tao",
    "lam",
    "mot",
    "1",
    "bai",
    "gioi",
    "thieu",
    "ve",
    "noi",
}
TOPIC_TRAILING_BREAKERS = {
    "co",
    "kem",
    "chuan",
    "theo",
    "de",
    "muc",
    "giong",
    "tone",
    "platform",
    "nen",
    "tang",
    "dang",
}
TOPIC_INSTRUCTION_VERBS = {
    "tao",
    "lam",
    "them",
    "chen",
    "dua",
    "giup",
}
OUTLINE_ARTIFACT_MARKERS = [
    "điểm cần lưu ý",
    "diem can luu y",
    "vị trí chèn",
    "vi tri chen",
    "mô tả ảnh",
    "mo ta anh",
    "caption:",
    "alt text:",
    "gợi ý",
    "goi y",
]
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
    "generated_images_json",
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


def serialize_generated_images(images: list[GeneratedImageAsset]) -> str:
    return json.dumps([image.model_dump() for image in images], ensure_ascii=False)


def deserialize_generated_images(raw_value: str) -> list[GeneratedImageAsset]:
    if not raw_value.strip():
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    results: list[GeneratedImageAsset] = []
    for item in parsed:
        if isinstance(item, dict):
            try:
                results.append(GeneratedImageAsset.model_validate(item))
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


def normalize_text_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    stripped = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", stripped)


def clean_topic_phrase(value: str) -> str:
    cleaned = " ".join(value.replace('"', " ").replace("'", " ").split()).strip(" .,-")
    if not cleaned:
        return ""
    original_tokens = re.findall(r"[0-9A-Za-zÀ-ỹ]+", cleaned, flags=re.UNICODE)
    if not original_tokens:
        return cleaned

    normalized_tokens = [normalize_text_for_match(token).strip() for token in original_tokens]
    collected: list[str] = []

    for index, token in enumerate(original_tokens):
        normalized = normalized_tokens[index]
        next_token = normalized_tokens[index + 1] if index + 1 < len(normalized_tokens) else ""

        if not normalized:
            continue
        if not collected and normalized in TOPIC_LEADING_FILLERS:
            continue
        if collected and normalized in TOPIC_TRAILING_BREAKERS:
            break
        if collected and normalized in TOPIC_INSTRUCTION_VERBS:
            break
        if collected and normalized == "va" and next_token in TOPIC_INSTRUCTION_VERBS.union(TOPIC_TRAILING_BREAKERS):
            break
        collected.append(token)

    while collected and normalize_text_for_match(collected[-1]).strip() in TOPIC_LEADING_FILLERS:
        collected.pop()

    topic = " ".join(collected).strip(" .,-")
    return topic or cleaned


def resolve_primary_topic(payload: MarketingPromptRequest) -> str:
    brief = " ".join(payload.brief.split()).strip()
    if brief:
        return clean_topic_phrase(brief).rstrip(".") or brief.rstrip(".")
    goal = " ".join(payload.goal.split()).strip()
    return clean_topic_phrase(goal) or goal or "chủ đề theo yêu cầu"


def extract_focus_terms(payload: MarketingPromptRequest) -> list[str]:
    normalized = normalize_text_for_match(resolve_primary_topic(payload))
    tokens = [token for token in normalized.split() if len(token) >= 3 and token not in TOPIC_STOPWORDS]
    unique_tokens: list[str] = []
    for token in tokens:
        if token not in unique_tokens:
            unique_tokens.append(token)
    return unique_tokens[:6]


def is_topic_aligned(content: str, payload: MarketingPromptRequest) -> bool:
    focus_terms = extract_focus_terms(payload)
    if not focus_terms:
        return True
    normalized_content = normalize_text_for_match(content)
    matches = sum(1 for term in focus_terms if term in normalized_content)
    return matches >= min(2, len(focus_terms))


def has_outline_artifacts(content: str) -> bool:
    normalized = normalize_text_for_match(content)
    return any(marker in normalized for marker in OUTLINE_ARTIFACT_MARKERS)


def build_outline_prompt(payload: MarketingPromptRequest) -> str:
    primary_topic = resolve_primary_topic(payload)
    return "\n".join(
        [
            "Ban la SEO assistant.",
            "Hay tao dan bai bai viet bang Markdown, viet bang tieng Viet co dau, ro rang va co tinh tong quat.",
            "Brief la nguon su that chinh ve chu de. Phai bam sat chu de trong brief, khong duoc tu y chuyen sang chu de khac.",
            "Neu brief noi ve gom su Bat Trang thi toan bo dan bai va vi tri anh chi duoc xoay quanh gom su Bat Trang.",
            "Tuyet doi khong dua noi dung ve Facebook, LinkedIn, lead, dashboard marketing neu brief khong nhac den.",
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
            f"Chu de chinh: {primary_topic}",
            f"Nen tang dich: {payload.platform}",
            f"Muc tieu: {payload.goal}",
            f"Giong van: {payload.tone}",
            f"Brief: {payload.brief}",
            "Hay tao dan bai co 5-7 phan chinh va it nhat 2 IMAGE_SLOT.",
        ]
    )


def fallback_outline(payload: MarketingPromptRequest) -> str:
    primary_topic = resolve_primary_topic(payload)
    return "\n".join(
        [
            "# Dan bai bai viet",
            "## Mo dau",
            f"- Gioi thieu tong quan ve {primary_topic.lower()}.",
            "- Neu gia tri van hoa, cong dung hoac diem dac sac cua chu de.",
            "",
            "## Nguon goc va dac trung",
            f"- Tom tat lich su, xuat xu va net rieng cua {primary_topic.lower()}.",
            "",
            "<!-- IMAGE_SLOT: image-1 -->",
            "- Vi tri chen: Sau phan gioi thieu nguon goc va dac trung.",
            f"- Mo ta anh: Anh canh nghe nhan hoac san pham tieu bieu lien quan den {primary_topic.lower()}.",
            "",
            "## Gia tri va suc hut",
            "- Trinh bay nhung diem noi bat, chat lieu, hoa tiet hoac trai nghiem gan voi chu de.",
            "",
            "## Cach lua chon hoac trai nghiem",
            "- Dua ra goi y thuc te cho nguoi doc quan tam den chu de nay.",
            "",
            "<!-- IMAGE_SLOT: image-2 -->",
            "- Vi tri chen: Truoc phan ket luan.",
            f"- Mo ta anh: Anh bo tri khong gian, san pham hoan chinh hoac hinh anh trai nghiem thuc te ve {primary_topic.lower()}.",
            "",
            "## Ket luan",
            "- Tong ket gia tri chinh cua chu de.",
            "- Chen CTA phu hop voi muc dich bai viet.",
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


def inject_image_metadata(
    markdown_text: str,
    metadata: list[dict[str, str]],
    generated_images: list[GeneratedImageAsset] | None = None,
) -> str:
    updated = markdown_text
    image_map = {item.slotId: item for item in generated_images or []}
    for item in metadata:
        generated_asset = image_map.get(item["slotId"])
        extra_lines: list[str] = []
        if generated_asset and generated_asset.imageUrl:
            extra_lines.append(f"- Image URL: {generated_asset.imageUrl}")
        if generated_asset and generated_asset.error:
            extra_lines.append(f"- Image status: {generated_asset.status} - {generated_asset.error}")
        replacement = "\n".join(
            [
                f"<!-- IMAGE_SLOT: {item['slotId']} -->",
                f"- Vi tri chen: {_find_slot_value(markdown_text, item['slotId'], 'placement')}",
                f"- Mo ta anh: {_find_slot_value(markdown_text, item['slotId'], 'description')}",
                f"- Caption: {item['caption']}",
                f"- Alt text: {item['altText']}",
                *extra_lines,
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
    primary_topic = resolve_primary_topic(payload)
    return "\n".join(
        [
            "Ban la SEO assistant chuyen viet bai chuan SEO bang tieng Viet co dau.",
            "Hay dung file Markdown duoi day de viet mot bai hoan chinh.",
            "Chu de phai bam sat brief. Khong duoc doi chu de, khong duoc chen noi dung marketing khong lien quan.",
            f"Chu de chinh bat buoc: {primary_topic}",
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
            "- Tu khoa, meta title va than bai phai phan anh dung chu de trong brief.",
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


def filter_instruction_bullets(bullets: list[str]) -> list[str]:
    ignored_prefixes = (
        "vi tri chen:",
        "mo ta anh:",
        "caption:",
        "alt text:",
    )
    filtered = [bullet for bullet in bullets if not bullet.lower().startswith(ignored_prefixes)]
    return filtered


def expand_bullet_to_paragraph(topic: str, heading: str, bullet: str) -> str:
    cleaned_bullet = bullet.rstrip(".")
    return (
        f"Trong phần {heading.lower()}, {cleaned_bullet.lower()}. "
        f"Khi triển khai thành bài viết hoàn chỉnh về {topic.lower()}, nội dung cần đi từ quan sát thực tế, "
        "chi tiết cụ thể đến giá trị mà người đọc có thể cảm nhận hoặc áp dụng ngay, thay vì chỉ dừng ở mức gợi ý."
    )


def build_direct_topic_article(payload: MarketingPromptRequest) -> str:
    topic = resolve_primary_topic(payload)
    topic_display = topic[:1].upper() + topic[1:] if topic else "Chủ đề này"
    return "\n\n".join(
        [
            "## Mở đầu",
            (
                f"{topic_display} là chủ đề rất phù hợp để phát triển thành một bài viết chuẩn SEO vì vừa có chiều sâu thông tin, "
                "vừa có nhiều chất liệu để minh họa bằng hình ảnh và trải nghiệm thực tế. "
                "Khi được triển khai đúng hướng, bài viết không chỉ giúp người đọc hiểu rõ bản chất của chủ đề mà còn tăng thời gian ở lại trang và khả năng tiếp cận từ công cụ tìm kiếm."
            ),
            (
                f"Thay vì chỉ dừng ở mức giới thiệu ngắn, nội dung về {topic} cần đi xa hơn: làm rõ bối cảnh, chỉ ra điểm nổi bật, "
                "giải thích giá trị thực tế và gợi mở lý do vì sao người đọc nên quan tâm. "
                "Đó là nền tảng để bài viết trở thành một nội dung có thể xuất bản ngay, thay vì chỉ là dàn ý hay các gợi ý rời rạc."
            ),
            "## Bối cảnh và điểm nổi bật",
            (
                f"Khi nhìn vào bối cảnh hình thành và quá trình phát triển của {topic}, người đọc sẽ thấy sức hút của chủ đề này không đến từ một chi tiết đơn lẻ, "
                "mà đến từ tổng hòa giữa lịch sử, bề dày trải nghiệm, đặc điểm nhận diện và những giá trị được duy trì theo thời gian. "
                "Một bài viết tốt cần làm rõ các lớp nghĩa này để người đọc hiểu vì sao chủ đề có chỗ đứng riêng và vì sao nó vẫn giữ được sự quan tâm đến hiện tại."
            ),
            (
                f"Ngoài yếu tố thông tin, {topic} còn hấp dẫn ở khả năng kể chuyện. "
                "Nếu biết cách triển khai bằng các đoạn văn rõ ý, có dẫn dắt và có ví dụ cụ thể, nội dung sẽ trở nên giàu hình dung hơn rất nhiều. "
                "Đây cũng là điểm giúp bài viết khác biệt so với các bản nháp chỉ lặp lại từ khóa hoặc mô tả quá chung chung."
            ),
            "## Giá trị thực tế và chiều sâu nội dung",
            (
                f"Giá trị của {topic} không chỉ nằm ở việc được biết đến rộng rãi, mà còn ở khả năng liên hệ trực tiếp với nhu cầu, cảm xúc hoặc mối quan tâm thực tế của người đọc. "
                "Bài viết cần chỉ ra rõ chủ đề này có ý nghĩa gì trong đời sống, có thể đem lại trải nghiệm gì và vì sao nó đáng để tìm hiểu sâu hơn."
            ),
            (
                "Khi nội dung chuyển từ mô tả chung sang phân tích cụ thể, bài viết sẽ dễ tạo niềm tin hơn. "
                "Người đọc thường ở lại lâu hơn với những đoạn văn có thông tin thật, có hình dung rõ và có khả năng trả lời những câu hỏi thực tế của họ. "
                "Đó cũng là cách giúp một bài SEO giữ được giá trị lâu dài thay vì chỉ tối ưu cho từ khóa."
            ),
            "## Hình ảnh minh họa và trải nghiệm đọc",
            (
                f"Với những chủ đề như {topic}, hình ảnh minh họa đóng vai trò rất quan trọng trong việc tăng sức thuyết phục. "
                "Ảnh nên được chèn ở đúng nhịp bài, làm rõ chi tiết chính hoặc bổ sung thêm một lớp cảm nhận mà chữ viết khó truyền tải hết. "
                "Khi caption và alt-text được viết chuẩn, hình ảnh không chỉ hỗ trợ trải nghiệm đọc mà còn giúp bài viết thân thiện hơn với SEO."
            ),
            (
                "Một bài viết có hình ảnh đặt đúng chỗ sẽ bớt khô hơn, giữ nhịp đọc tự nhiên hơn và giúp người đọc dễ ghi nhớ nội dung hơn. "
                "Đó là lý do bài viết hoàn chỉnh cần xem hình ảnh như một phần của câu chuyện, chứ không phải phần trang trí thêm vào ở cuối."
            ),
            "## Kết luận",
            (
                f"Tóm lại, để viết tốt về {topic}, nội dung cần hội đủ ba yếu tố: thông tin rõ ràng, cấu trúc mạch lạc và hình ảnh đúng ngữ cảnh. "
                "Khi ba phần này đi cùng nhau, bài viết sẽ có đủ chiều sâu để thuyết phục người đọc và đủ độ hoàn chỉnh để đưa vào xuất bản ngay."
            ),
            (
                f"Nếu muốn nâng chất lượng nội dung về {topic}, hãy ưu tiên các đoạn văn hoàn chỉnh, ví dụ cụ thể, cách diễn đạt tự nhiên và CTA rõ ràng ở cuối bài. "
                "Đó là cách giúp nội dung sinh ra thực sự trở thành một bài viết thành phẩm, vừa tốt cho SEO vừa đủ sức tạo ấn tượng với người đọc."
            ),
        ]
    )


def build_article_body_from_markdown(payload: MarketingPromptRequest, markdown_text: str) -> str:
    primary_topic = resolve_primary_topic(payload)
    sections = extract_section_bullets(markdown_text)
    paragraphs: list[str] = [
        "## Mở đầu",
        (
            f"{primary_topic.capitalize()} là chủ đề có sức hút riêng vì hội tụ cả giá trị văn hóa, tính thẩm mỹ và chiều sâu trải nghiệm. "
            "Chỉ cần tiếp cận đúng cách, người viết đã có thể mở ra một câu chuyện giàu hình ảnh, dễ đọc và đủ sức giữ chân người đọc lâu hơn trên trang."
        ),
        (
            f"Bài viết này được triển khai theo giọng điệu {payload.tone.lower()}, bám sát chủ đề để giúp người đọc hiểu rõ nguồn gốc, đặc trưng, giá trị sử dụng "
            f"và nét hấp dẫn riêng của {primary_topic.lower()} trong đời sống hiện đại."
        ),
    ]

    for heading, bullets in sections:
        if heading.lower().startswith("dan bai"):
            continue
        content_bullets = filter_instruction_bullets(bullets)
        paragraphs.append(f"## {heading}")
        if content_bullets:
            intro = " ".join(content_bullets[:2])
            paragraphs.append(
                f"{heading} là lớp nội dung giúp người đọc tiếp cận {primary_topic.lower()} một cách mạch lạc hơn. "
                f"Thay vì chỉ đưa ra nhận xét ngắn, phần này cần mở rộng thành thông tin có chiều sâu, gắn với bối cảnh thực tế và cảm nhận cụ thể. {intro}"
            )
            for bullet in content_bullets[:3]:
                paragraphs.append(expand_bullet_to_paragraph(primary_topic, heading, bullet))
        else:
            paragraphs.append(
                f"{heading} cần được triển khai thành đoạn văn hoàn chỉnh, bám sát chủ đề {primary_topic.lower()} và ưu tiên mô tả cụ thể thay vì ghi chú dạng gợi ý."
            )

    paragraphs.extend(
        [
            "## Kết luận",
            (
                f"Một bài viết chuẩn SEO về {primary_topic.lower()} không chỉ cần đúng từ khóa mà còn phải có cấu trúc rõ ràng, hình ảnh đúng ngữ cảnh và thông tin đủ thuyết phục để giữ chân người đọc."
            ),
            (
                f"Nếu muốn xây dựng nội dung chất lượng về {primary_topic.lower()}, người viết nên ưu tiên sự cụ thể, tính kể chuyện và chiều sâu thông tin. "
                "Khi nội dung vừa giàu hình ảnh vừa có cấu trúc tốt, bài viết sẽ dễ đạt hiệu quả SEO hơn mà vẫn giữ được cảm xúc tự nhiên cho người đọc."
            ),
        ]
    )

    return "\n\n".join(paragraphs)


def fallback_seo_article(payload: MarketingPromptRequest, markdown_text: str) -> str:
    article_body = build_article_body_from_markdown(payload, markdown_text)
    if has_outline_artifacts(article_body) or len(article_body.split()) < 220 or not is_topic_aligned(article_body, payload):
        article_body = build_direct_topic_article(payload)
    primary_topic = resolve_primary_topic(payload)
    keywords = [primary_topic, payload.platform, "bài viết chuẩn SEO", "hình ảnh minh họa", "nội dung chuyên đề"]
    return "\n".join(
        [
            "# Meta title",
            f"{primary_topic} | Bài viết chuẩn SEO",
            "",
            "# Meta description",
            (
                f"Khám phá {primary_topic.lower()} qua bài viết chuẩn SEO có hình ảnh minh họa, nội dung mạch lạc và thông tin dễ tiếp cận cho người đọc."
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
    return has_sections and has_subheadings and body_length >= 250 and not has_outline_artifacts(content)


def normalize_seo_article(content: str, payload: MarketingPromptRequest, markdown_text: str) -> str:
    if is_complete_seo_article(content):
        return content.strip()

    fallback = fallback_seo_article(payload, markdown_text)
    primary_topic = resolve_primary_topic(payload)

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
            meta_title or f"{primary_topic} | Bài viết chuẩn SEO",
            "",
            "# Meta description",
            meta_description
            or (
                f"Khám phá {primary_topic.lower()} qua bài viết chuẩn SEO có hình ảnh minh họa, nội dung mạch lạc và thông tin dễ tiếp cận cho người đọc."
            ),
            "",
            "# Keywords",
            keywords or f"{primary_topic}, {payload.platform}, bài viết chuẩn SEO",
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
    primary_topic = resolve_primary_topic(payload)
    meta_title = strip_markdown_syntax(extract_seo_section(seo_markdown, "Meta title")) or (
        f"{primary_topic.capitalize()} | Bài viết chuẩn SEO"
    )
    meta_description = strip_markdown_syntax(extract_seo_section(seo_markdown, "Meta description")) or (
        f"Khám phá {primary_topic.lower()} qua bài viết chuẩn SEO có hình ảnh minh họa, nội dung mạch lạc và thông tin dễ tiếp cận cho người đọc."
    )
    keywords = normalize_keywords_text(strip_markdown_syntax(extract_seo_section(seo_markdown, "Keywords"))) or (
        f"{primary_topic}, {payload.platform}, bài viết chuẩn SEO"
    )
    article_body = strip_markdown_syntax(extract_seo_section(seo_markdown, "Noi dung bai viet")) or strip_markdown_syntax(
        seo_markdown
    )
    if has_outline_artifacts(article_body) or len(article_body.split()) < 220 or not is_topic_aligned(article_body, payload):
        article_body = build_direct_topic_article(payload)
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
    draft_id: str,
    payload: MarketingPromptRequest,
    settings: Settings,
) -> tuple[str, str, str, str, str, list[GeneratedImageAsset]]:
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
    slot_payload = [
        {
            "slotId": slot["slotId"],
            "placement": slot["placement"],
            "description": slot["description"],
            "caption": next((item["caption"] for item in metadata if item["slotId"] == slot["slotId"]), ""),
            "altText": next((item["altText"] for item in metadata if item["slotId"] == slot["slotId"]), ""),
        }
        for slot in slots
    ]
    generated_images = await generate_images_for_slots(draft_id, payload, slot_payload, settings)
    enriched_markdown = inject_image_metadata(outline_markdown, metadata, generated_images)

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
        if not is_topic_aligned(seo_markdown, payload):
            seo_markdown = fallback_seo_article(payload, enriched_markdown)
            source = "fallback"
            seo_used_model = SEO_MODEL

    return (
        outline_markdown,
        enriched_markdown,
        seo_markdown,
        source,
        "|".join([outline_used_model or OUTLINE_MODEL, image_used_model or IMAGE_MODEL, seo_used_model or SEO_MODEL]),
        generated_images,
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
        generatedImages=deserialize_generated_images(record.get("generated_images_json", "")),
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
    draft_id = uuid.uuid4().hex
    timestamp = now_iso()
    outline_markdown, enriched_markdown, seo_markdown, source, model_trace, generated_images = await run_markdown_pipeline(
        draft_id,
        payload,
        settings,
    )
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
        generatedImages=generated_images,
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
                serialize_generated_images(draft.generatedImages),
            ],
        ],
    )

    return ContentDraftGenerateResponse(
        message=(
            f"Đã chạy pipeline {OUTLINE_MODEL} -> {IMAGE_MODEL} -> {SEO_MODEL}. "
            f"Sheet {get_content_sheet_name(settings)} chỉ lưu bài viết hoàn chỉnh; "
            f"đã xử lý {len([item for item in generated_images if item.status == 'ready'])}/{len(generated_images)} ảnh local; "
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
        generatedImages=deserialize_generated_images(record.get("generated_images_json", "")),
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
                serialize_generated_images(draft.generatedImages),
            ],
        ],
    )

    return ContentDraftConfirmResponse(
        message="Đã xác nhận nội dung và chuyển sang bước đẩy nền tảng theo cấu hình hiện có.",
        draft=draft,
    )
