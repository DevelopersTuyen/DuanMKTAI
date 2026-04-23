import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import { ContentPerformance, MarketingData, PlatformPerformance, Recommendation } from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

@Component({
  selector: 'app-analytics',
  templateUrl: './analytics.page.html',
  styleUrls: ['./analytics.page.scss'],
  standalone: false,
})
export class AnalyticsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);

  platforms: PlatformPerformance[] = [];
  topContents: ContentPerformance[] = [];
  recommendations: Recommendation[] = [];

  isLoading = true;
  loadError = '';
  utilityMessage = '';
  utilityError = '';
  readonly pageSize = 8;
  currentPage = 1;

  ngOnInit(): void {
    this.backgroundRefresh.watch('analytics:overview', () => this.marketingData.getAnalytics())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.platforms = state.data.platforms;
          this.topContents = state.data.topContents;
          this.recommendations = state.data.recommendations;
          this.loadError = '';
        } else if (state.error && !this.topContents.length) {
          this.loadError = state.error || 'Không thể tải dữ liệu phân tích từ backend.';
        }

        this.isLoading = state.loading && !state.data;
      });
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.topContents.length / this.pageSize));
  }

  get pagedContents(): ContentPerformance[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.topContents.slice(start, start + this.pageSize);
  }

  goToPage(page: number): void {
    this.currentPage = Math.min(this.totalPages, Math.max(1, page));
  }

  refreshAnalytics(): void {
    this.backgroundRefresh.refresh('analytics:overview');
    this.setUtilityMessage('Đã yêu cầu làm mới dữ liệu phân tích.');
  }

  async copyTopContentSummary(): Promise<void> {
    const content = this.topContents.map((item) => (
      `${item.title} | ${item.platform} | ${item.views} | CTR ${item.ctr}% | Tương tác ${item.engagementRate}%`
    )).join('\n');
    const copied = await this.uiActions.copyText(content);
    if (copied) {
      this.setUtilityMessage('Đã sao chép danh sách nội dung nổi bật.');
      return;
    }

    this.setUtilityError('Chưa có dữ liệu nội dung nổi bật để sao chép.');
  }

  downloadAnalyticsSnapshot(): void {
    const content = [
      'TỔNG QUAN NỀN TẢNG',
      ...this.platforms.map((item) => `${item.platform}: lượt xem ${item.reach}, CTR ${item.ctr}%, tương tác ${item.engagementRate}%`),
      '',
      'NỘI DUNG NỔI BẬT',
      ...this.topContents.map((item) => `${item.title} | ${item.platform} | ${item.format} | ${item.views}`),
      '',
      'ĐỀ XUẤT',
      ...this.recommendations.map((item) => `${item.title}: ${item.detail}`),
    ].join('\n');

    const ok = this.uiActions.downloadText(
      `analytics-snapshot-${new Date().toISOString().slice(0, 10)}.txt`,
      content,
    );
    if (ok) {
      this.setUtilityMessage('Đã tải xuống snapshot phân tích.');
      return;
    }

    this.setUtilityError('Chưa có dữ liệu phân tích để tải xuống.');
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
