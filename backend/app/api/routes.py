from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import Settings, get_settings
from app.models import (
    AiQueueStatusResponse,
    AnalyticsResponse,
    AutomationStatusResponse,
    CampaignsResponse,
    ContentDraftConfirmResponse,
    ContentDraftGenerateResponse,
    ContentDraftListResponse,
    ContentGenerateResponse,
    ContentResponse,
    DashboardResponse,
    DataSyncResponse,
    DailyReportLatestResponse,
    DailyReportSyncResponse,
    GoogleWebsiteStatusResponse,
    GoogleWebsiteSyncResponse,
    ImageProviderStatusResponse,
    IntegrationsResponse,
    LocalAiAnalysisResponse,
    MarketingPromptRequest,
    OAuthActionResponse,
    OAuthProvidersResponse,
    OAuthStartResponse,
    ReportsResponse,
    SchedulerResponse,
    SeoInsightsResponse,
    SettingsSaveResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    SocialPlatformsStatusResponse,
    SocialPlatformsSyncResponse,
)
from app.services.automation import automation_manager
from app.services.content_studio import confirm_content_draft, generate_content_draft, list_content_drafts
from app.services.daily_report import get_latest_daily_report, sync_daily_report
from app.services.google_website import get_google_website_status, sync_google_website_data
from app.services.local_image_generation import probe_local_image_provider
from app.services.local_ai_analysis import get_local_ai_analysis
from app.services.mock_data import (
    get_campaigns_data,
    get_content_data,
    get_data_sync_data,
    get_integrations_data,
    get_reports_data,
    get_scheduler_data,
)
from app.services.oauth_connections import (
    build_authorization_url,
    disconnect_provider_connection,
    get_oauth_provider_statuses,
    handle_oauth_callback,
    refresh_provider_connection,
)
from app.services.ollama_client import generate_marketing_copy, get_ollama_queue_status
from app.services.social_platforms import get_social_platforms_status, sync_social_platforms
from app.services.system_settings import build_settings_response, get_runtime_settings, save_system_settings
from app.services.website_reporting import (
    get_website_analytics_data,
    get_website_dashboard_data,
    get_website_seo_data,
)

router = APIRouter()
GENERATED_IMAGES_DIR = Path(__file__).resolve().parents[2] / "storage" / "generated_images"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(settings: Settings = Depends(get_runtime_settings)) -> DashboardResponse:
    return get_website_dashboard_data(settings)


@router.get("/ai/local-analysis", response_model=LocalAiAnalysisResponse)
async def ai_local_analysis(settings: Settings = Depends(get_runtime_settings)) -> LocalAiAnalysisResponse:
    return await get_local_ai_analysis(settings)


@router.get("/ai/queue-status", response_model=AiQueueStatusResponse)
async def ai_queue_status() -> AiQueueStatusResponse:
    return get_ollama_queue_status()


@router.get("/image-provider/status", response_model=ImageProviderStatusResponse)
async def image_provider_status(settings: Settings = Depends(get_runtime_settings)) -> ImageProviderStatusResponse:
    ready, message = await probe_local_image_provider(settings)
    provider = settings.local_image_provider.strip().lower() or "disabled"
    endpoint = None
    workflow_file = None
    if provider == "automatic1111":
        endpoint = settings.automatic1111_base_url
    elif provider == "comfyui":
        endpoint = settings.comfyui_base_url
        workflow_file = settings.comfyui_workflow_file

    return ImageProviderStatusResponse(
        provider=provider,
        ready=ready,
        message=message,
        endpoint=endpoint,
        workflowFile=workflow_file,
    )


@router.get("/data-sync", response_model=DataSyncResponse)
async def data_sync(settings: Settings = Depends(get_runtime_settings)) -> DataSyncResponse:
    wordpress_sites_count = len(settings.get_wordpress_sites()) or 3
    analytics_property_count = len(settings.get_google_analytics_property_ids()) or 1
    return get_data_sync_data(wordpress_sites_count, analytics_property_count)


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(settings: Settings = Depends(get_runtime_settings)) -> AnalyticsResponse:
    return get_website_analytics_data(settings)


@router.get("/content", response_model=ContentResponse)
async def content() -> ContentResponse:
    return get_content_data()


@router.post("/content/generate", response_model=ContentGenerateResponse)
async def content_generate(
    payload: MarketingPromptRequest,
    settings: Settings = Depends(get_runtime_settings),
) -> ContentGenerateResponse:
    return await generate_marketing_copy(payload, settings)


@router.get("/content/drafts", response_model=ContentDraftListResponse)
async def content_drafts(settings: Settings = Depends(get_runtime_settings)) -> ContentDraftListResponse:
    return list_content_drafts(settings)


@router.post("/content/drafts/generate", response_model=ContentDraftGenerateResponse)
async def content_drafts_generate(
    payload: MarketingPromptRequest,
    settings: Settings = Depends(get_runtime_settings),
) -> ContentDraftGenerateResponse:
    return await generate_content_draft(payload, settings)


@router.post("/content/drafts/{draft_id}/confirm", response_model=ContentDraftConfirmResponse)
async def content_drafts_confirm(
    draft_id: str,
    settings: Settings = Depends(get_runtime_settings),
) -> ContentDraftConfirmResponse:
    try:
        return confirm_content_draft(settings, draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/content/generated-image")
async def content_generated_image(path: str = Query(..., min_length=1)) -> FileResponse:
    target = (GENERATED_IMAGES_DIR / path).resolve()
    base = GENERATED_IMAGES_DIR.resolve()
    if base not in target.parents and target != base:
        raise HTTPException(status_code=400, detail="Đường dẫn ảnh không hợp lệ.")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh đã sinh.")
    return FileResponse(target)


@router.get("/scheduler", response_model=SchedulerResponse)
async def scheduler() -> SchedulerResponse:
    return get_scheduler_data()


@router.get("/campaigns", response_model=CampaignsResponse)
async def campaigns() -> CampaignsResponse:
    return get_campaigns_data()


@router.get("/seo-insights", response_model=SeoInsightsResponse)
async def seo_insights(settings: Settings = Depends(get_runtime_settings)) -> SeoInsightsResponse:
    return get_website_seo_data(settings)


@router.get("/integrations", response_model=IntegrationsResponse)
async def integrations() -> IntegrationsResponse:
    return get_integrations_data()


@router.get("/oauth/providers", response_model=OAuthProvidersResponse)
async def oauth_providers(settings: Settings = Depends(get_settings)) -> OAuthProvidersResponse:
    return get_oauth_provider_statuses(settings)


@router.get("/oauth/{provider}/start", response_model=OAuthStartResponse)
async def oauth_start(
    provider: str,
    return_url: str | None = Query(default=None, alias="returnUrl"),
    settings: Settings = Depends(get_settings),
) -> OAuthStartResponse:
    try:
        return build_authorization_url(provider, settings, return_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    state: str,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = Query(default=None, alias="error_description"),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    try:
        redirect_url = await handle_oauth_callback(
            provider=provider,
            settings=settings,
            state=state,
            code=code,
            error=error,
            error_description=error_description,
        )
    except Exception as exc:
        redirect_url = (
            f"{settings.frontend_base_url.rstrip('/')}/integrations?"
            f"{urlencode({'oauth_provider': provider, 'oauth_status': 'error', 'oauth_message': str(exc)})}"
        )
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/oauth/{provider}/refresh", response_model=OAuthActionResponse)
async def oauth_refresh(provider: str, settings: Settings = Depends(get_settings)) -> OAuthActionResponse:
    try:
        return await refresh_provider_connection(provider, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Làm mới token thất bại: {exc}") from exc


@router.delete("/oauth/{provider}", response_model=OAuthActionResponse)
async def oauth_disconnect(provider: str, settings: Settings = Depends(get_settings)) -> OAuthActionResponse:
    try:
        return disconnect_provider_connection(provider, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reports", response_model=ReportsResponse)
async def reports() -> ReportsResponse:
    return get_reports_data()


@router.post("/reports/daily/sync", response_model=DailyReportSyncResponse)
async def reports_daily_sync(settings: Settings = Depends(get_runtime_settings)) -> DailyReportSyncResponse:
    try:
        return await sync_daily_report(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Tạo báo cáo ngày thất bại: {exc}") from exc


@router.get("/reports/daily/latest", response_model=DailyReportLatestResponse)
async def reports_daily_latest(settings: Settings = Depends(get_runtime_settings)) -> DailyReportLatestResponse:
    try:
        return get_latest_daily_report(settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Không thể đọc báo cáo ngày: {exc}") from exc


@router.get("/settings/defaults", response_model=SettingsResponse)
async def settings_defaults(settings: Settings = Depends(get_settings)) -> SettingsResponse:
    return build_settings_response(settings)


@router.put("/settings/defaults", response_model=SettingsSaveResponse)
async def settings_save(
    payload: SettingsUpdateRequest,
    settings: Settings = Depends(get_settings),
) -> SettingsSaveResponse:
    return save_system_settings(settings, payload)


@router.get("/settings/runtime-status", response_model=AutomationStatusResponse)
async def settings_runtime_status() -> AutomationStatusResponse:
    return automation_manager.get_status()


@router.get("/google/website/status", response_model=GoogleWebsiteStatusResponse)
async def google_website_status(settings: Settings = Depends(get_runtime_settings)) -> GoogleWebsiteStatusResponse:
    return get_google_website_status(settings)


@router.post("/google/website/sync", response_model=GoogleWebsiteSyncResponse)
async def google_website_sync(settings: Settings = Depends(get_runtime_settings)) -> GoogleWebsiteSyncResponse:
    try:
        return await sync_google_website_data(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Đồng bộ Google thất bại: {exc}") from exc


@router.get("/social/status", response_model=SocialPlatformsStatusResponse)
async def social_status(settings: Settings = Depends(get_runtime_settings)) -> SocialPlatformsStatusResponse:
    return get_social_platforms_status(settings)


@router.post("/social/sync", response_model=SocialPlatformsSyncResponse)
async def social_sync(settings: Settings = Depends(get_runtime_settings)) -> SocialPlatformsSyncResponse:
    try:
        return await sync_social_platforms(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Đồng bộ social thất bại: {exc}") from exc
