import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ClientSettingsService } from './client-settings.service';

export interface DashboardKpi {
  label: string;
  value: string;
  note: string;
  trend: string;
  trendTone: 'trend-up' | 'trend-flat' | 'trend-alert';
}

export interface TrendPoint {
  label: string;
  value: number;
}

export interface ChannelShare {
  name: string;
  value: number;
}

export interface Recommendation {
  title: string;
  detail: string;
  priority: 'High' | 'Medium';
}

export interface LocalAiChannelStatus {
  name: string;
  status: string;
  detail: string;
  rows: number;
}

export interface LocalAiAnalysisResponse {
  summary: string;
  analysis: string;
  model: string;
  source: 'ollama' | 'fallback';
  generatedAt: string;
  channels: LocalAiChannelStatus[];
}

export interface AiQueueStatusResponse {
  waitingJobs: number;
  currentJob: string | null;
  running: boolean;
  lastCompletedAt: string | null;
  lastError: string | null;
}

export interface SyncChannel {
  name: string;
  accounts: number;
  status: string;
  statusClass: string;
  lastSync: string;
  healthScore: number;
}

export interface ManagedAccount {
  platform: string;
  account: string;
  assets: string;
  destination: string;
}

export interface PlatformPerformance {
  platform: string;
  reach: string;
  engagementRate: number;
  ctr: number;
  conversionRate: number;
}

export interface ContentPerformance {
  title: string;
  platform: string;
  format: string;
  views: string;
  ctr: number;
  engagementRate: number;
  statusClass: string;
  statusLabel: string;
}

export interface ContentIdea {
  title: string;
  angle: string;
  channel: string;
}

export interface ScheduleItem {
  asset: string;
  channel: string;
  slot: string;
  bestWindow: string;
  audience: string;
}

export interface CampaignOverview {
  name: string;
  objective: string;
  spend: string;
  reach: string;
  forecast: string;
  nextMove: string;
}

export interface KeywordInsight {
  keyword: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  action: string;
}

export interface IntegrationStatus {
  name: string;
  status: string;
  statusClass: string;
  accounts: string;
  scope: string;
  lastSync: string;
}

export interface ReportSnapshot {
  title: string;
  cadence: string;
  target: string;
  summary: string;
}

export interface DashboardResponse {
  kpis: DashboardKpi[];
  performanceTrend: TrendPoint[];
  channelBreakdown: ChannelShare[];
  syncChannels: SyncChannel[];
  recommendations: Recommendation[];
}

export interface DataSyncResponse {
  syncChannels: SyncChannel[];
  accounts: ManagedAccount[];
}

export interface AnalyticsResponse {
  platforms: PlatformPerformance[];
  topContents: ContentPerformance[];
  recommendations: Recommendation[];
}

export interface ContentResponse {
  ideas: ContentIdea[];
}

export interface PublishTargetResult {
  platform: string;
  status: string;
  detail: string;
}

export interface ContentDraft {
  draftId: string;
  createdAt: string;
  updatedAt: string;
  status: string;
  requestedPlatforms: string;
  goal: string;
  tone: string;
  brief: string;
  generatedContent: string;
  markdownPath: string | null;
  markdownContent: string;
  model: string;
  outlineModel: string | null;
  imageModel: string | null;
  seoModel: string | null;
  source: 'ollama' | 'fallback';
  worksheet: string;
  confirmedAt: string | null;
  publishedAt: string | null;
  dispatchStatus: string;
  dispatchResults: PublishTargetResult[];
}

export interface ContentDraftGenerateResponse {
  message: string;
  draft: ContentDraft;
}

export interface ContentDraftConfirmResponse {
  message: string;
  draft: ContentDraft;
}

export interface ContentDraftListResponse {
  worksheet: string;
  drafts: ContentDraft[];
}

export interface SchedulerResponse {
  queue: ScheduleItem[];
}

export interface CampaignsResponse {
  campaigns: CampaignOverview[];
}

export interface SeoInsightsResponse {
  keywords: KeywordInsight[];
  recommendations: Recommendation[];
}

export interface IntegrationsResponse {
  integrations: IntegrationStatus[];
}

export interface ReportsResponse {
  reports: ReportSnapshot[];
}

export interface DailyReportSyncResponse {
  status: 'success';
  message: string;
  worksheet: string;
  reportDate: string;
  updatedRange: string;
  model: string;
  source: 'ollama' | 'fallback';
  generatedAt: string;
}

export interface DailyReportLatestResponse {
  reportDate: string;
  tongQuat: string;
  chiTietTungNenTang: string;
  vanDeGapPhai: string;
  deXuat: string;
  model: string;
  source: string;
  generatedAt: string;
  worksheet: string;
}

export interface SettingsDefaultsResponse {
  apiBaseUrl: string;
  ollamaBaseUrl: string;
  ollamaModel: string;
  spreadsheetId: string;
  worksheet: string;
  syncIntervalMinutes: number;
  autoSync: boolean;
  autoRecommend: boolean;
  autoSchedule: boolean;
}

export interface SettingsUpdateRequest {
  apiBaseUrl: string;
  ollamaBaseUrl: string;
  ollamaModel: string;
  spreadsheetId: string;
  worksheet: string;
  syncIntervalMinutes: number;
  autoSync: boolean;
  autoRecommend: boolean;
  autoSchedule: boolean;
}

export interface SettingsSaveResponse {
  status: 'success';
  message: string;
  settings: SettingsDefaultsResponse;
}

export interface AutomationJobStatus {
  name: string;
  enabled: boolean;
  lastRunAt: string | null;
  lastSuccessAt: string | null;
  lastStatus: string;
  lastMessage: string;
}

export interface AutomationStatusResponse {
  running: boolean;
  pollSeconds: number;
  effectiveSettings: SettingsDefaultsResponse;
  lastConfigReloadAt: string | null;
  jobs: AutomationJobStatus[];
}

export interface GoogleWebsiteStatusResponse {
  ready: boolean;
  hasApiKey: boolean;
  hasServiceAccountKey: boolean;
  wordpressSitesCount: number;
  spreadsheetId: string;
  worksheet: string;
  wordpressWorksheet: string;
  analyticsPropertyId: string | null;
  searchConsoleSiteUrl: string | null;
  message: string;
  warnings: string[];
}

export interface GoogleWebsiteSyncResponse {
  status: string;
  message: string;
  spreadsheetId: string;
  worksheet: string;
  wordpressWorksheet: string;
  wordpressPosts: number;
  analyticsRows: number;
  searchConsoleRows: number;
  updatedRanges: string[];
  warnings: string[];
}

export interface SocialPlatformStatus {
  name: string;
  worksheet: string;
  ready: boolean;
  configuredAssets: number;
  hasCredentials: boolean;
  message: string;
  warnings: string[];
}

export interface SocialPlatformsStatusResponse {
  spreadsheetId: string;
  statuses: SocialPlatformStatus[];
}

export interface SocialPlatformSyncResult {
  platform: string;
  worksheet: string;
  rows: number;
  updatedRange: string;
  status: 'success' | 'skipped' | 'warning';
  detail: string;
}

export interface SocialPlatformsSyncResponse {
  status: string;
  message: string;
  spreadsheetId: string;
  results: SocialPlatformSyncResult[];
  warnings: string[];
}

export interface OAuthProviderStatus {
  provider: string;
  label: string;
  worksheet: string;
  connected: boolean;
  ready: boolean;
  connectable: boolean;
  supportsRefresh: boolean;
  supportsAutoRefresh: boolean;
  status: string;
  statusClass: string;
  authType: string;
  accountLabel: string | null;
  accountId: string | null;
  configuredAssets: number;
  assetSummary: string;
  connectedAt: string | null;
  expiresAt: string | null;
  authNote: string;
  warnings: string[];
}

export interface OAuthProvidersResponse {
  frontendBaseUrl: string;
  backendBaseUrl: string;
  providers: OAuthProviderStatus[];
}

export interface OAuthStartResponse {
  provider: string;
  authorizationUrl: string;
}

export interface OAuthActionResponse {
  provider: string;
  status: string;
  message: string;
  connected: boolean;
  accountLabel: string | null;
  expiresAt: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class MarketingData {
  private readonly http = inject(HttpClient);
  private readonly clientSettings = inject(ClientSettingsService);

  private get apiBaseUrl(): string {
    return this.clientSettings.apiBaseUrl;
  }

  getDashboard(): Observable<DashboardResponse> {
    return this.http.get<DashboardResponse>(`${this.apiBaseUrl}/dashboard`);
  }

  getLocalAiAnalysis(): Observable<LocalAiAnalysisResponse> {
    return this.http.get<LocalAiAnalysisResponse>(`${this.apiBaseUrl}/ai/local-analysis`);
  }

  getAiQueueStatus(): Observable<AiQueueStatusResponse> {
    return this.http.get<AiQueueStatusResponse>(`${this.apiBaseUrl}/ai/queue-status`);
  }

  getDataSync(): Observable<DataSyncResponse> {
    return this.http.get<DataSyncResponse>(`${this.apiBaseUrl}/data-sync`);
  }

  getAnalytics(): Observable<AnalyticsResponse> {
    return this.http.get<AnalyticsResponse>(`${this.apiBaseUrl}/analytics`);
  }

  getContent(): Observable<ContentResponse> {
    return this.http.get<ContentResponse>(`${this.apiBaseUrl}/content`);
  }

  getContentDrafts(): Observable<ContentDraftListResponse> {
    return this.http.get<ContentDraftListResponse>(`${this.apiBaseUrl}/content/drafts`);
  }

  generateContentDraft(payload: {
    platform: string;
    goal: string;
    tone: string;
    brief: string;
  }): Observable<ContentDraftGenerateResponse> {
    return this.http.post<ContentDraftGenerateResponse>(`${this.apiBaseUrl}/content/drafts/generate`, payload);
  }

  confirmContentDraft(draftId: string): Observable<ContentDraftConfirmResponse> {
    return this.http.post<ContentDraftConfirmResponse>(`${this.apiBaseUrl}/content/drafts/${draftId}/confirm`, {});
  }

  getScheduler(): Observable<SchedulerResponse> {
    return this.http.get<SchedulerResponse>(`${this.apiBaseUrl}/scheduler`);
  }

  getCampaigns(): Observable<CampaignsResponse> {
    return this.http.get<CampaignsResponse>(`${this.apiBaseUrl}/campaigns`);
  }

  getSeoInsights(): Observable<SeoInsightsResponse> {
    return this.http.get<SeoInsightsResponse>(`${this.apiBaseUrl}/seo-insights`);
  }

  getIntegrations(): Observable<IntegrationsResponse> {
    return this.http.get<IntegrationsResponse>(`${this.apiBaseUrl}/integrations`);
  }

  getReports(): Observable<ReportsResponse> {
    return this.http.get<ReportsResponse>(`${this.apiBaseUrl}/reports`);
  }

  getLatestDailyReport(): Observable<DailyReportLatestResponse> {
    return this.http.get<DailyReportLatestResponse>(`${this.apiBaseUrl}/reports/daily/latest`);
  }

  syncDailyReport(): Observable<DailyReportSyncResponse> {
    return this.http.post<DailyReportSyncResponse>(`${this.apiBaseUrl}/reports/daily/sync`, {});
  }

  getSettingsDefaults(): Observable<SettingsDefaultsResponse> {
    return this.http.get<SettingsDefaultsResponse>(`${this.apiBaseUrl}/settings/defaults`);
  }

  saveSettings(payload: SettingsUpdateRequest): Observable<SettingsSaveResponse> {
    return this.http.put<SettingsSaveResponse>(`${this.apiBaseUrl}/settings/defaults`, payload);
  }

  getAutomationStatus(): Observable<AutomationStatusResponse> {
    return this.http.get<AutomationStatusResponse>(`${this.apiBaseUrl}/settings/runtime-status`);
  }

  getGoogleWebsiteStatus(): Observable<GoogleWebsiteStatusResponse> {
    return this.http.get<GoogleWebsiteStatusResponse>(`${this.apiBaseUrl}/google/website/status`);
  }

  syncGoogleWebsite(): Observable<GoogleWebsiteSyncResponse> {
    return this.http.post<GoogleWebsiteSyncResponse>(`${this.apiBaseUrl}/google/website/sync`, {});
  }

  getSocialStatus(): Observable<SocialPlatformsStatusResponse> {
    return this.http.get<SocialPlatformsStatusResponse>(`${this.apiBaseUrl}/social/status`);
  }

  syncSocialPlatforms(): Observable<SocialPlatformsSyncResponse> {
    return this.http.post<SocialPlatformsSyncResponse>(`${this.apiBaseUrl}/social/sync`, {});
  }

  getOAuthProviders(): Observable<OAuthProvidersResponse> {
    return this.http.get<OAuthProvidersResponse>(`${this.apiBaseUrl}/oauth/providers`);
  }

  getOAuthStart(provider: string, returnUrl?: string): Observable<OAuthStartResponse> {
    const encodedReturnUrl = returnUrl ? `?returnUrl=${encodeURIComponent(returnUrl)}` : '';
    return this.http.get<OAuthStartResponse>(`${this.apiBaseUrl}/oauth/${provider}/start${encodedReturnUrl}`);
  }

  refreshOAuthProvider(provider: string): Observable<OAuthActionResponse> {
    return this.http.post<OAuthActionResponse>(`${this.apiBaseUrl}/oauth/${provider}/refresh`, {});
  }

  disconnectOAuthProvider(provider: string): Observable<OAuthActionResponse> {
    return this.http.delete<OAuthActionResponse>(`${this.apiBaseUrl}/oauth/${provider}`);
  }
}
