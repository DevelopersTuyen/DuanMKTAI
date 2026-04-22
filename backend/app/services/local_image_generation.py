from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.models import GeneratedImageAsset, MarketingPromptRequest

BASE_DIR = Path(__file__).resolve().parents[2]
GENERATED_IMAGES_DIR = BASE_DIR / "storage" / "generated_images"
logger = logging.getLogger(__name__)

def resolve_image_topic(payload: MarketingPromptRequest) -> str:
    brief = " ".join(payload.brief.split()).strip()
    if not brief:
        return payload.goal.strip() or "chủ đề theo yêu cầu"

    lowered = brief.lower()
    markers = [" có kèm", " kèm ", " chuẩn seo", " và tạo ", " cùng hình ảnh", " với hình ảnh"]
    cut_index = len(brief)
    for marker in markers:
        current_index = lowered.find(marker)
        if current_index != -1:
            cut_index = min(cut_index, current_index)
    topic = brief[:cut_index].strip(" .,-")
    prefixes = ["hãy viết 1 bài viết về ", "hãy viết bài về ", "viết 1 bài viết về ", "viết bài về ", "giới thiệu về "]
    lowered_topic = topic.lower()
    for prefix in prefixes:
        if lowered_topic.startswith(prefix):
            topic = topic[len(prefix) :].strip(" .,-")
            break
    return topic or brief


def ensure_generated_images_dir(draft_id: str) -> Path:
    target = GENERATED_IMAGES_DIR / draft_id
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_image_prompt(
    payload: MarketingPromptRequest,
    slot: dict[str, str],
    caption: str,
    alt_text: str,
) -> str:
    topic = resolve_image_topic(payload)
    return (
        f"Ảnh minh họa chất lượng cao cho bài viết về {topic}. "
        f"Vị trí chèn: {slot.get('placement', '')}. "
        f"Mô tả chính: {slot.get('description', '')}. "
        f"Caption tham chiếu: {caption}. "
        f"Alt text tham chiếu: {alt_text}. "
        "Bố cục rõ ràng, đúng chủ đề, ánh sáng tự nhiên, chi tiết tốt, không chèn chữ, không watermark."
    ).strip()


def build_public_image_url(settings: Settings, draft_id: str, filename: str) -> str:
    base_url = settings.public_backend_url.rstrip("/")
    query = urlencode({"path": f"{draft_id}/{filename}"})
    return f"{base_url}/api/content/generated-image?{query}"


def _normalize_base64_image(value: str) -> bytes:
    payload = value.split(",", 1)[-1]
    return base64.b64decode(payload)


async def _generate_with_automatic1111(prompt: str, settings: Settings) -> bytes:
    endpoint = f"{settings.automatic1111_base_url.rstrip('/')}/sdapi/v1/txt2img"
    payload = {
        "prompt": prompt,
        "negative_prompt": settings.local_image_negative_prompt,
        "steps": settings.local_image_steps,
        "cfg_scale": settings.local_image_cfg_scale,
        "width": settings.local_image_width,
        "height": settings.local_image_height,
        "sampler_name": settings.local_image_sampler,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

    images = data.get("images") or []
    if not images:
        raise ValueError("AUTOMATIC1111 không trả về ảnh nào.")
    return _normalize_base64_image(str(images[0]))


def _replace_workflow_placeholders(value: Any, mapping: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_workflow_placeholders(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_workflow_placeholders(item, mapping) for item in value]
    if isinstance(value, str):
        if value in mapping:
            return mapping[value]
        result = value
        for placeholder, replacement in mapping.items():
            if isinstance(replacement, str):
                result = result.replace(placeholder, replacement)
        return result
    return value


async def _generate_with_comfyui(prompt: str, settings: Settings) -> bytes:
    if not settings.comfyui_workflow_file:
        raise ValueError("COMFYUI_WORKFLOW_FILE chưa được cấu hình.")

    workflow_path = Path(settings.comfyui_workflow_file)
    if not workflow_path.exists():
        raise ValueError(f"Không tìm thấy workflow ComfyUI: {workflow_path}")

    workflow_template = json.loads(workflow_path.read_text(encoding="utf-8"))
    mapping: dict[str, Any] = {
        "{{prompt}}": prompt,
        "{{negative_prompt}}": settings.local_image_negative_prompt,
        "{{width}}": settings.local_image_width,
        "{{height}}": settings.local_image_height,
        "{{steps}}": settings.local_image_steps,
        "{{cfg_scale}}": settings.local_image_cfg_scale,
        "{{sampler_name}}": settings.local_image_sampler,
        "{{seed}}": 0,
    }
    workflow_payload = _replace_workflow_placeholders(workflow_template, mapping)
    client_id = uuid.uuid4().hex

    async with httpx.AsyncClient(timeout=180) as client:
        prompt_response = await client.post(
            f"{settings.comfyui_base_url.rstrip('/')}/prompt",
            json={"prompt": workflow_payload, "client_id": client_id},
        )
        prompt_response.raise_for_status()
        prompt_data = prompt_response.json()
        prompt_id = str(prompt_data.get("prompt_id") or "").strip()
        if not prompt_id:
            raise ValueError("ComfyUI không trả về prompt_id.")

        history_payload: dict[str, Any] | None = None
        for _ in range(180):
            history_response = await client.get(f"{settings.comfyui_base_url.rstrip('/')}/history/{prompt_id}")
            history_response.raise_for_status()
            history_payload = history_response.json()
            if history_payload:
                break
            await asyncio.sleep(1)

        if not history_payload:
            raise ValueError("ComfyUI không trả về lịch sử sinh ảnh trong thời gian chờ.")

        history_entry = history_payload.get(prompt_id) if isinstance(history_payload, dict) else None
        outputs = history_entry.get("outputs", {}) if isinstance(history_entry, dict) else {}
        image_record: dict[str, Any] | None = None
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            images = node_output.get("images") or []
            if images:
                first_image = images[0]
                if isinstance(first_image, dict):
                    image_record = first_image
                    break

        if not image_record:
            raise ValueError("ComfyUI không trả về metadata ảnh đầu ra.")

        query = urlencode(
            {
                "filename": str(image_record.get("filename", "")),
                "subfolder": str(image_record.get("subfolder", "")),
                "type": str(image_record.get("type", "output")),
            }
        )
        image_response = await client.get(f"{settings.comfyui_base_url.rstrip('/')}/view?{query}")
        image_response.raise_for_status()
        return image_response.content


async def probe_local_image_provider(settings: Settings) -> tuple[bool, str]:
    provider = settings.local_image_provider.strip().lower()
    if provider in {"", "disabled", "none"}:
        return False, "Local image provider đang tắt."

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if provider == "automatic1111":
                response = await client.get(f"{settings.automatic1111_base_url.rstrip('/')}/sdapi/v1/sd-models")
                response.raise_for_status()
                models = response.json()
                model_count = len(models) if isinstance(models, list) else 0
                return True, f"AUTOMATIC1111 online tại {settings.automatic1111_base_url} ({model_count} model)."

            if provider == "comfyui":
                workflow_path = Path(settings.comfyui_workflow_file or "")
                if not settings.comfyui_workflow_file or not workflow_path.exists():
                    return False, f"ComfyUI workflow không hợp lệ: {settings.comfyui_workflow_file or 'chưa cấu hình'}"
                response = await client.get(f"{settings.comfyui_base_url.rstrip('/')}/system_stats")
                response.raise_for_status()
                return True, f"ComfyUI online tại {settings.comfyui_base_url} với workflow {workflow_path.name}."

            return False, f"Provider '{provider}' chưa được hỗ trợ."
    except Exception as exc:
        return False, f"Không kết nối được provider '{provider}': {exc}"


async def generate_images_for_slots(
    draft_id: str,
    payload: MarketingPromptRequest,
    slot_metadata: list[dict[str, str]],
    settings: Settings,
) -> list[GeneratedImageAsset]:
    provider = settings.local_image_provider.strip().lower()
    generated_assets: list[GeneratedImageAsset] = []
    target_dir = ensure_generated_images_dir(draft_id)
    logger.info(
        "Local image generation started: draft_id=%s provider=%s slots=%s",
        draft_id,
        provider or "disabled",
        len(slot_metadata),
    )

    for index, slot in enumerate(slot_metadata, start=1):
        placement = slot.get("placement", "")
        caption = slot.get("caption", "")
        alt_text = slot.get("altText", "")
        prompt = build_image_prompt(payload, slot, caption, alt_text)
        asset = GeneratedImageAsset(
            slotId=slot.get("slotId", f"image-{index}"),
            placement=placement,
            prompt=prompt,
            caption=caption,
            altText=alt_text,
            provider=provider or "disabled",
            status="pending",
        )

        if provider in {"", "disabled", "none"}:
            asset.status = "skipped"
            asset.error = "Chưa cấu hình local image provider."
            logger.warning(
                "Local image generation skipped: draft_id=%s slot=%s reason=%s",
                draft_id,
                asset.slotId,
                asset.error,
            )
            generated_assets.append(asset)
            continue

        try:
            if provider == "automatic1111":
                image_bytes = await _generate_with_automatic1111(prompt, settings)
            elif provider == "comfyui":
                image_bytes = await _generate_with_comfyui(prompt, settings)
            else:
                raise ValueError(f"Provider '{provider}' chưa được hỗ trợ.")

            filename = f"{asset.slotId}-{index}.png"
            local_path = target_dir / filename
            local_path.write_bytes(image_bytes)
            asset.status = "ready"
            asset.localPath = str(local_path)
            asset.imageUrl = build_public_image_url(settings, draft_id, filename)
            logger.info(
                "Local image generation ready: draft_id=%s slot=%s provider=%s file=%s",
                draft_id,
                asset.slotId,
                asset.provider,
                local_path.name,
            )
        except Exception as exc:
            asset.status = "error"
            asset.error = str(exc)
            logger.exception(
                "Local image generation error: draft_id=%s slot=%s provider=%s",
                draft_id,
                asset.slotId,
                asset.provider,
            )

        generated_assets.append(asset)

    ready_count = len([item for item in generated_assets if item.status == "ready"])
    logger.info(
        "Local image generation finished: draft_id=%s ready=%s total=%s",
        draft_id,
        ready_count,
        len(generated_assets),
    )
    return generated_assets
