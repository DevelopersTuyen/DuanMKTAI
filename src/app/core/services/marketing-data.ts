import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

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

export interface SettingsDefaultsResponse {
  apiBaseUrl: string;
  ollamaBaseUrl: string;
  ollamaModel: string;
  spreadsheetId: string;
  worksheet: string;
  syncIntervalMinutes: number;
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

@Injectable({
  providedIn: 'root',
})
export class MarketingData {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  getDashboard(): Observable<DashboardResponse> {
    return this.http.get<DashboardResponse>(`${this.apiBaseUrl}/dashboard`);
  }

  getLocalAiAnalysis(): Observable<LocalAiAnalysisResponse> {
    return this.http.get<LocalAiAnalysisResponse>(`${this.apiBaseUrl}/ai/local-analysis`);
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

  getSettingsDefaults(): Observable<SettingsDefaultsResponse> {
    return this.http.get<SettingsDefaultsResponse>(`${this.apiBaseUrl}/settings/defaults`);
  }

  getGoogleWebsiteStatus(): Observable<GoogleWebsiteStatusResponse> {
    return this.http.get<GoogleWebsiteStatusResponse>(`${this.apiBaseUrl}/google/website/status`);
  }

  syncGoogleWebsite(): Observable<GoogleWebsiteSyncResponse> {
    return this.http.post<GoogleWebsiteSyncResponse>(`${this.apiBaseUrl}/google/website/sync`, {});
  }
}
