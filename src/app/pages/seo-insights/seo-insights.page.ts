import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import { KeywordInsight, MarketingData, Recommendation, WebsiteSummary } from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

@Component({
  selector: 'app-seo-insights',
  templateUrl: './seo-insights.page.html',
  styleUrls: ['./seo-insights.page.scss'],
  standalone: false,
})
export class SeoInsightsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);

  keywords: KeywordInsight[] = [];
  websiteSummaries: WebsiteSummary[] = [];
  recommendations: Recommendation[] = [];
  isLoading = true;
  loadError = '';
  utilityMessage = '';
  utilityError = '';
  readonly pageSize = 10;
  currentPage = 1;

  ngOnInit(): void {
    this.backgroundRefresh.watch('seo:insights', () => this.marketingData.getSeoInsights())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.keywords = state.data.keywords;
          this.websiteSummaries = state.data.websiteSummaries;
          this.recommendations = state.data.recommendations;
          this.loadError = '';
        } else if (state.error && !this.keywords.length) {
          this.loadError = state.error || 'Không thể tải dữ liệu SEO từ backend.';
        }

        this.isLoading = state.loading && !state.data;
      });
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.keywords.length / this.pageSize));
  }

  get pagedKeywords(): KeywordInsight[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.keywords.slice(start, start + this.pageSize);
  }

  goToPage(page: number): void {
    this.currentPage = Math.min(this.totalPages, Math.max(1, page));
  }

  refreshSeo(): void {
    this.backgroundRefresh.refresh('seo:insights');
    this.setUtilityMessage('Đã yêu cầu làm mới dữ liệu SEO.');
  }

  async copyKeywordSummary(): Promise<void> {
    const content = this.keywords.map((item) => (
      `${item.keyword} | clicks ${item.clicks} | impressions ${item.impressions} | CTR ${item.ctr}% | position ${item.position}`
    )).join('\n');
    const copied = await this.uiActions.copyText(content);
    if (copied) {
      this.setUtilityMessage('Đã sao chép bảng cơ hội SEO.');
      return;
    }

    this.setUtilityError('Chưa có dữ liệu SEO để sao chép.');
  }

  downloadSeoSnapshot(): void {
    const content = [
      'SEO KEYWORDS',
      ...this.keywords.map((item) => `${item.keyword} | ${item.clicks} | ${item.impressions} | ${item.ctr}% | ${item.position} | ${item.action}`),
      '',
      'RECOMMENDATIONS',
      ...this.recommendations.map((item) => `${item.title}: ${item.detail}`),
    ].join('\n');

    const ok = this.uiActions.downloadText(
      `seo-insights-${new Date().toISOString().slice(0, 10)}.txt`,
      content,
    );
    if (ok) {
      this.setUtilityMessage('Đã tải xuống snapshot SEO.');
      return;
    }

    this.setUtilityError('Chưa có dữ liệu SEO để tải xuống.');
  }

  private setUtilityMessage(message: string): void {
    this.utilityMessage = message;
    this.utilityError = '';
  }

  private setUtilityError(message: string): void {
    this.utilityError = message;
    this.utilityMessage = '';
  }
}
