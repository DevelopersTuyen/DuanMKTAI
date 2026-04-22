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


class LocalAiChannelStatus(BaseModel):
    name: str
    status: str
    detail: str
    rows: int


class LocalAiAnalysisResponse(BaseModel):
    summary: str
    analysis: str
    model: str
    source: Literal["ollama", "fallback"]
    generatedAt: str
    channels: list[LocalAiChannelStatus]


class DailyReportSyncResponse(BaseModel):
    status: Literal["success"]
    message: str
    worksheet: str
    reportDate: str
    updatedRange: str
    model: str
    source: Literal["ollama", "fallback"]
    generatedAt: str


class DailyReportLatestResponse(BaseModel):
    reportDate: str
    tongQuat: str
    chiTietTungNenTang: str
    vanDeGapPhai: str
    deXuat: str
    model: str
    source: str
    generatedAt: str
    worksheet: str


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
    wordpressWorksheet: str
    analyticsPropertyId: str | None
    searchConsoleSiteUrl: str | None
    message: str
    warnings: list[str]


class GoogleWebsiteSyncResponse(BaseModel):
    status: str
    message: str
    spreadsheetId: str
    worksheet: str
    wordpressWorksheet: str
    wordpressPosts: int
    analyticsRows: int
    searchConsoleRows: int
    updatedRanges: list[str]
    warnings: list[str]


class SocialPlatformStatus(BaseModel):
    name: str
    worksheet: str
    ready: bool
    configuredAssets: int
    hasCredentials: bool
    message: str
    warnings: list[str]


class SocialPlatformsStatusResponse(BaseModel):
    spreadsheetId: str
    statuses: list[SocialPlatformStatus]


class SocialPlatformSyncResult(BaseModel):
    platform: str
    worksheet: str
    rows: int
    updatedRange: str
    status: Literal["success", "skipped", "warning"]
    detail: str


class SocialPlatformsSyncResponse(BaseModel):
    status: str
    message: str
    spreadsheetId: str
    results: list[SocialPlatformSyncResult]
    warnings: list[str]


class OAuthProviderStatus(BaseModel):
    provider: str
    label: str
    worksheet: str
    connected: bool
    ready: bool
    connectable: bool
    supportsRefresh: bool
    supportsAutoRefresh: bool
    status: str
    statusClass: str
    authType: str
    accountLabel: str | None
    accountId: str | None
    configuredAssets: int
    assetSummary: str
    connectedAt: str | None
    expiresAt: str | None
    authNote: str
    warnings: list[str]


class OAuthProvidersResponse(BaseModel):
    frontendBaseUrl: str
    backendBaseUrl: str
    providers: list[OAuthProviderStatus]


class OAuthStartResponse(BaseModel):
    provider: str
    authorizationUrl: str


class OAuthActionResponse(BaseModel):
    provider: str
    status: str
    message: str
    connected: bool
    accountLabel: str | None = None
    expiresAt: str | None = None
