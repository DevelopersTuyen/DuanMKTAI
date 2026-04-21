from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.models import (
    AnalyticsResponse,
    CampaignsResponse,
    ContentGenerateResponse,
    ContentResponse,
    DashboardResponse,
    DataSyncResponse,
    GoogleWebsiteStatusResponse,
    GoogleWebsiteSyncResponse,
    IntegrationsResponse,
    MarketingPromptRequest,
    ReportsResponse,
    SchedulerResponse,
    SeoInsightsResponse,
    SettingsResponse,
)
from app.services.mock_data import (
    get_analytics_data,
    get_campaigns_data,
    get_content_data,
    get_dashboard_data,
    get_data_sync_data,
    get_integrations_data,
    get_reports_data,
    get_scheduler_data,
    get_seo_insights_data,
    get_settings_data,
)
from app.services.google_website import get_google_website_status, sync_google_website_data
from app.services.ollama_client import generate_marketing_copy

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(settings: Settings = Depends(get_settings)) -> DashboardResponse:
    wordpress_sites_count = len(settings.get_wordpress_sites()) or 3
    return get_dashboard_data(wordpress_sites_count)


@router.get("/data-sync", response_model=DataSyncResponse)
async def data_sync(settings: Settings = Depends(get_settings)) -> DataSyncResponse:
    wordpress_sites_count = len(settings.get_wordpress_sites()) or 3
    return get_data_sync_data(wordpress_sites_count)


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics() -> AnalyticsResponse:
    return get_analytics_data()


@router.get("/content", response_model=ContentResponse)
async def content() -> ContentResponse:
    return get_content_data()


@router.post("/content/generate", response_model=ContentGenerateResponse)
async def content_generate(
    payload: MarketingPromptRequest,
    settings: Settings = Depends(get_settings),
) -> ContentGenerateResponse:
    return await generate_marketing_copy(payload, settings)


@router.get("/scheduler", response_model=SchedulerResponse)
async def scheduler() -> SchedulerResponse:
    return get_scheduler_data()


@router.get("/campaigns", response_model=CampaignsResponse)
async def campaigns() -> CampaignsResponse:
    return get_campaigns_data()


@router.get("/seo-insights", response_model=SeoInsightsResponse)
async def seo_insights() -> SeoInsightsResponse:
    return get_seo_insights_data()


@router.get("/integrations", response_model=IntegrationsResponse)
async def integrations() -> IntegrationsResponse:
    return get_integrations_data()


@router.get("/reports", response_model=ReportsResponse)
async def reports() -> ReportsResponse:
    return get_reports_data()


@router.get("/settings/defaults", response_model=SettingsResponse)
async def settings_defaults(settings: Settings = Depends(get_settings)) -> SettingsResponse:
    return get_settings_data(
        api_base_url="http://localhost:8000/api",
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        spreadsheet_id=settings.google_sheet_id,
        worksheet=settings.google_sheet_worksheet,
        sync_interval=settings.sync_interval_minutes,
    )


@router.get("/google/website/status", response_model=GoogleWebsiteStatusResponse)
async def google_website_status(settings: Settings = Depends(get_settings)) -> GoogleWebsiteStatusResponse:
    return get_google_website_status(settings)


@router.post("/google/website/sync", response_model=GoogleWebsiteSyncResponse)
async def google_website_sync(settings: Settings = Depends(get_settings)) -> GoogleWebsiteSyncResponse:
    try:
        return await sync_google_website_data(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google sync failed: {exc}") from exc
