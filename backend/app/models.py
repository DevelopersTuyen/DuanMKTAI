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


class AiQueueStatusResponse(BaseModel):
    waitingJobs: int
    currentJob: str | None
    running: bool
    lastCompletedAt: str | None
    lastError: str | None


class ImageProviderStatusResponse(BaseModel):
    provider: str
    ready: bool
    message: str
    endpoint: str | None = None
    workflowFile: str | None = None


class PublishTargetResult(BaseModel):
    platform: str
    status: str
    detail: str


class GeneratedImageAsset(BaseModel):
    slotId: str
    placement: str
    prompt: str
    caption: str
    altText: str
    provider: str
    status: str
    imageUrl: str | None = None
    localPath: str | None = None
    error: str | None = None


class ContentDraft(BaseModel):
    draftId: str
    createdAt: str
    updatedAt: str
    status: str
    requestedPlatforms: str
    goal: str
    tone: str
    brief: str
    generatedContent: str
    markdownPath: str | None = None
    markdownContent: str = ""
    model: str
    outlineModel: str | None = None
    imageModel: str | None = None
    seoModel: str | None = None
    source: Literal["ollama", "fallback"]
    worksheet: str
    generatedImages: list[GeneratedImageAsset] = Field(default_factory=list)
    confirmedAt: str | None = None
    publishedAt: str | None = None
    dispatchStatus: str = "draft"
    dispatchResults: list[PublishTargetResult] = Field(default_factory=list)


class ContentDraftGenerateResponse(BaseModel):
    message: str
    draft: ContentDraft


class ContentDraftGenerationStatusResponse(BaseModel):
    jobId: str
    status: Literal["queued", "running", "completed", "error"]
    progress: int
    currentStep: str
    stepLabel: str
    message: str
    startedAt: str
    updatedAt: str
    completedAt: str | None = None
    error: str | None = None
    draft: ContentDraft | None = None


class ContentDraftGenerationStartResponse(BaseModel):
    message: str
    job: ContentDraftGenerationStatusResponse


class ContentDraftConfirmResponse(BaseModel):
    message: str
    draft: ContentDraft


class ContentDraftListResponse(BaseModel):
    worksheet: str
    drafts: list[ContentDraft]


class ContentDraftDeleteResponse(BaseModel):
    status: Literal["success"]
    message: str
    draftId: str
    worksheet: str


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


class DailyReportHistoryItem(BaseModel):
    reportDate: str
    tongQuat: str
    model: str
    source: str
    generatedAt: str


class DailyReportHistoryResponse(BaseModel):
    worksheet: str
    reports: list[DailyReportHistoryItem]


class DailyReportDeleteResponse(BaseModel):
    status: Literal["success"]
    message: str
    reportDate: str
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


class ScheduleRule(BaseModel):
    id: str
    title: str
    channel: str
    publishMode: Literal["manual", "auto"]
    startAt: str
    repeatType: Literal["none", "daily", "weekly", "monthly"]
    repeatInterval: int
    daysOfWeek: list[int]
    active: bool
    note: str | None = None


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


class WebsiteSummary(BaseModel):
    site: str
    siteUrl: str | None = None
    gaPropertyId: str | None = None
    gscSiteUrl: str | None = None
    pageViews: str
    sessions: str
    posts: int
    trackedPages: int
    clicks: int
    ctr: float
    position: float
    syncStatus: str


class DashboardResponse(BaseModel):
    kpis: list[DashboardKpi]
    performanceTrend: list[TrendPoint]
    channelBreakdown: list[ChannelShare]
    syncChannels: list[SyncChannel]
    websiteSummaries: list[WebsiteSummary]
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
    mode: Literal["manual", "auto"]
    timezone: str
    schedules: list[ScheduleRule]
    queue: list[ScheduleItem]


class SchedulerUpdateRequest(BaseModel):
    mode: Literal["manual", "auto"]
    timezone: str = Field(min_length=1)
    schedules: list[ScheduleRule]


class SchedulerSaveResponse(BaseModel):
    status: Literal["success"]
    message: str
    scheduler: SchedulerResponse


class CampaignsResponse(BaseModel):
    campaigns: list[CampaignOverview]


class SeoInsightsResponse(BaseModel):
    keywords: list[KeywordInsight]
    websiteSummaries: list[WebsiteSummary]
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
    syncMode: Literal["interval", "scheduled"]
    syncStartTime: str
    syncIntervalMinutes: int
    syncDaysOfWeek: list[int]
    syncLoopEnabled: bool
    syncWebsiteEnabled: bool
    syncSocialEnabled: bool
    autoSync: bool
    autoRecommend: bool
    autoSchedule: bool


class SettingsUpdateRequest(BaseModel):
    apiBaseUrl: str = Field(min_length=1)
    ollamaBaseUrl: str = Field(min_length=1)
    ollamaModel: str = Field(min_length=1)
    spreadsheetId: str = Field(min_length=1)
    worksheet: str = Field(min_length=1)
    syncMode: Literal["interval", "scheduled"] = "interval"
    syncStartTime: str = Field(default="08:00", pattern=r"^\d{2}:\d{2}$")
    syncIntervalMinutes: int = Field(ge=1, le=1440)
    syncDaysOfWeek: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    syncLoopEnabled: bool = True
    syncWebsiteEnabled: bool = True
    syncSocialEnabled: bool = True
    autoSync: bool = True
    autoRecommend: bool = True
    autoSchedule: bool = False


class SettingsSaveResponse(BaseModel):
    status: Literal["success"]
    message: str
    settings: SettingsResponse


class AutomationJobStatus(BaseModel):
    name: str
    enabled: bool
    lastRunAt: str | None
    lastSuccessAt: str | None
    lastStatus: str
    lastMessage: str


class AutomationStatusResponse(BaseModel):
    running: bool
    pollSeconds: int
    effectiveSettings: SettingsResponse
    lastConfigReloadAt: str | None
    jobs: list[AutomationJobStatus]


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
    searchConsoleSites: list[str]
    message: str
    siteMappings: list[dict[str, str]]
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
