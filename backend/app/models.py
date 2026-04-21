from typing import Literal

from pydantic import BaseModel, Field


class MarketingPromptRequest(BaseModel):
    platform: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    brief: str = Field(min_length=1)


class ContentGenerateResponse(BaseModel):
    response: str
    model: str
    source: Literal["ollama", "fallback"]


class DashboardKpi(BaseModel):
    label: str
    value: str
    note: str
    trend: str
    trendTone: Literal["trend-up", "trend-flat", "trend-alert"]


class TrendPoint(BaseModel):
    label: str
    value: int


class ChannelShare(BaseModel):
    name: str
    value: int


class Recommendation(BaseModel):
    title: str
    detail: str
    priority: Literal["High", "Medium"]


class SyncChannel(BaseModel):
    name: str
    accounts: int
    status: str
    statusClass: str
    lastSync: str
    healthScore: int


class ManagedAccount(BaseModel):
    platform: str
    account: str
    assets: str
    destination: str


class PlatformPerformance(BaseModel):
    platform: str
    reach: str
    engagementRate: float
    ctr: float
    conversionRate: float


class ContentPerformance(BaseModel):
    title: str
    platform: str
    format: str
    views: str
    ctr: float
    engagementRate: float
    statusClass: str
    statusLabel: str


class ContentIdea(BaseModel):
    title: str
    angle: str
    channel: str


class ScheduleItem(BaseModel):
    asset: str
    channel: str
    slot: str
    bestWindow: str
    audience: str


class CampaignOverview(BaseModel):
    name: str
    objective: str
    spend: str
    reach: str
    forecast: str
    nextMove: str


class KeywordInsight(BaseModel):
    keyword: str
    clicks: int
    impressions: int
    ctr: float
    position: float
    action: str


class IntegrationStatus(BaseModel):
    name: str
    status: str
    statusClass: str
    accounts: str
    scope: str
    lastSync: str


class ReportSnapshot(BaseModel):
    title: str
    cadence: str
    target: str
    summary: str


class DashboardResponse(BaseModel):
    kpis: list[DashboardKpi]
    performanceTrend: list[TrendPoint]
    channelBreakdown: list[ChannelShare]
    syncChannels: list[SyncChannel]
    recommendations: list[Recommendation]


class DataSyncResponse(BaseModel):
    syncChannels: list[SyncChannel]
    accounts: list[ManagedAccount]


class AnalyticsResponse(BaseModel):
    platforms: list[PlatformPerformance]
    topContents: list[ContentPerformance]
    recommendations: list[Recommendation]


class ContentResponse(BaseModel):
    ideas: list[ContentIdea]


class SchedulerResponse(BaseModel):
    queue: list[ScheduleItem]


class CampaignsResponse(BaseModel):
    campaigns: list[CampaignOverview]


class SeoInsightsResponse(BaseModel):
    keywords: list[KeywordInsight]
    recommendations: list[Recommendation]


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationStatus]


class ReportsResponse(BaseModel):
    reports: list[ReportSnapshot]


class SettingsResponse(BaseModel):
    apiBaseUrl: str
    ollamaBaseUrl: str
    ollamaModel: str
    spreadsheetId: str
    worksheet: str
    syncIntervalMinutes: int


class GoogleWebsiteStatusResponse(BaseModel):
    ready: bool
    hasApiKey: bool
    hasServiceAccountKey: bool
    wordpressSitesCount: int
    spreadsheetId: str
    worksheet: str
    analyticsPropertyId: str | None
    searchConsoleSiteUrl: str | None
    message: str
    warnings: list[str]


class GoogleWebsiteSyncResponse(BaseModel):
    status: str
    message: str
    spreadsheetId: str
    worksheet: str
    wordpressPosts: int
    analyticsRows: int
    searchConsoleRows: int
    updatedRanges: list[str]
    warnings: list[str]
