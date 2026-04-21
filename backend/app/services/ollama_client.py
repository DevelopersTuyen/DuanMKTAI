from __future__ import annotations

import httpx

from app.core.config import Settings
from app.models import ContentGenerateResponse, MarketingPromptRequest


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
    payload = {
        "model": settings.ollama_model,
        "prompt": build_prompt(request),
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            content = str(data.get("response", "")).strip()
            if content:
                return ContentGenerateResponse(response=content, model=settings.ollama_model, source="ollama")
    except (httpx.HTTPError, ValueError):
        pass

    return build_fallback_response(request, settings.ollama_model)
