from __future__ import annotations

import httpx

from app.core.config import Settings
from app.models import ContentGenerateResponse, MarketingPromptRequest


async def get_available_ollama_models(settings: Settings) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [str(model.get("name", "")).strip() for model in data.get("models", []) if model.get("name")]
    except (httpx.HTTPError, ValueError):
        return []


def build_model_candidates(settings: Settings, available_models: list[str]) -> list[str]:
    preferred_candidates = [
        settings.ollama_model,
        "qwen2.5:3b",
        "qwen2.5:1.5b-instruct",
        "qwen2.5:1.5b",
        "qwen:7b",
        "qwen:4b",
        "qwen2:0.5b-instruct",
    ]
    candidates: list[str] = []

    for model_name in preferred_candidates:
        if model_name and model_name in available_models and model_name not in candidates:
            candidates.append(model_name)

    for model_name in available_models:
        if model_name.startswith("qwen") and model_name not in candidates:
            candidates.append(model_name)

    return candidates


async def generate_text_with_ollama(prompt: str, settings: Settings) -> tuple[str, str, str]:
    available_models = await get_available_ollama_models(settings)
    model_candidates = build_model_candidates(settings, available_models)

    async with httpx.AsyncClient(timeout=120.0) as client:
        for model_name in model_candidates:
            try:
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                }
                response = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                content = str(data.get("response", "")).strip()
                if content:
                    return content, "ollama", model_name
            except (httpx.HTTPError, ValueError):
                continue

    return "", "fallback", settings.ollama_model


def build_prompt(request: MarketingPromptRequest) -> str:
    return " ".join(
        [
            "Ban la chuyen gia marketing performance.",
            f"Nen tang uu tien: {request.platform}.",
            f"Muc tieu: {request.goal}.",
            f"Giong van: {request.tone}.",
            f"Tom tat brief: {request.brief}.",
            "Hay tao 1 bai viet marketing ngan, 3 hook, 3 CTA va 3 goi y hinh anh.",
        ]
    )


def build_fallback_response(request: MarketingPromptRequest, model: str) -> ContentGenerateResponse:
    content = "\n".join(
        [
            f"Tieu de de xuat cho {request.platform}: {request.goal}.",
            "",
            f"Mo bai: {request.brief}",
            "",
            "Hook 1: Mo ra bang mot pain point ro rang va con so cu the.",
            "Hook 2: Neu loi ich nhanh, de do va gan voi KPI.",
            "Hook 3: Chen bang chung social proof tu campaign truoc.",
            "",
            f"CTA 1: Dang ky ngay de tang {request.goal.lower()}.",
            f"CTA 2: Inbox de nhan ke hoach {request.platform.lower()} ca nhan hoa.",
            "CTA 3: Tai checklist de trien khai trong 7 ngay.",
            "",
            "Visual: Hero graphic, mini dashboard KPI, testimonial card.",
        ]
    )
    return ContentGenerateResponse(response=content, model=model, source="fallback")


async def generate_marketing_copy(request: MarketingPromptRequest, settings: Settings) -> ContentGenerateResponse:
    content, source, used_model = await generate_text_with_ollama(build_prompt(request), settings)
    if content and source == "ollama":
        return ContentGenerateResponse(response=content, model=used_model, source="ollama")

    return build_fallback_response(request, settings.ollama_model)
