import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import {
  DailyReportDeleteResponse,
  DailyReportHistoryItem,
  DailyReportLatestResponse,
  DailyReportSyncResponse,
  MarketingData,
} from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

@Component({
  selector: 'app-reports',
  templateUrl: './reports.page.html',
  styleUrls: ['./reports.page.scss'],
  standalone: false,
})
export class ReportsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);

  reportHistory: DailyReportHistoryItem[] = [];
  latestDailyReport?: DailyReportLatestResponse;
  latestDailyReportError = '';
  dailyReportSyncResult?: DailyReportSyncResponse;
  dailyReportDeleteResult?: DailyReportDeleteResponse;
  dailyReportSyncError = '';
  dailyReportDeleteError = '';
  isSyncingDailyReport = false;
  isDeletingReport = false;
  deletingReportDate = '';
  isLoading = true;
  utilityMessage = '';
  utilityError = '';

  readonly pageSize = 6;
  currentPage = 1;

  ngOnInit(): void {
    this.backgroundRefresh.watch('reports:latest-daily', () => this.marketingData.getLatestDailyReport())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.latestDailyReport = state.data;
          this.latestDailyReportError = '';
        } else if (state.error) {
          this.latestDailyReport = undefined;
          this.latestDailyReportError = state.error || 'Chưa đọc được báo cáo ngày mới nhất.';
        }
      });

    this.backgroundRefresh.watch('reports:history', () => this.marketingData.getDailyReportHistory())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.reportHistory = state.data.reports;
          if (this.currentPage > this.totalPages) {
            this.currentPage = this.totalPages;
          }
        }
        this.isLoading = state.loading && !state.data;
      });
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.reportHistory.length / this.pageSize));
  }

  get pagedReports(): DailyReportHistoryItem[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.reportHistory.slice(start, start + this.pageSize);
  }

  goToPage(page: number): void {
    this.currentPage = Math.min(this.totalPages, Math.max(1, page));
  }

  syncDailyReport(): void {
    this.isSyncingDailyReport = true;
    this.dailyReportSyncError = '';
    this.dailyReportDeleteError = '';
    this.dailyReportDeleteResult = undefined;
    this.dailyReportSyncResult = undefined;

    this.marketingData.syncDailyReport()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.dailyReportSyncResult = response;
          this.isSyncingDailyReport = false;
          this.backgroundRefresh.refreshMany(['reports:latest-daily', 'reports:history']);
        },
        error: (error) => {
          this.dailyReportSyncError = error?.error?.detail ?? 'Không thể tạo báo cáo ngày.';
          this.isSyncingDailyReport = false;
        },
      });
  }

  deleteDailyReport(reportDate: string): void {
    const confirmed = window.confirm(`Xóa báo cáo ngày ${reportDate} khỏi Google Sheet?`);
    if (!confirmed) {
      return;
    }

    this.isDeletingReport = true;
    this.deletingReportDate = reportDate;
    this.dailyReportDeleteError = '';
    this.dailyReportDeleteResult = undefined;
    this.dailyReportSyncError = '';

    this.marketingData.deleteDailyReport(reportDate)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.dailyReportDeleteResult = response;
          this.isDeletingReport = false;
          this.deletingReportDate = '';
          if (this.latestDailyReport?.reportDate === reportDate) {
            this.latestDailyReport = undefined;
          }
          this.backgroundRefresh.refreshMany(['reports:latest-daily', 'reports:history']);
        },
        error: (error) => {
          this.dailyReportDeleteError = error?.error?.detail ?? 'Không thể xóa báo cáo ngày.';
          this.isDeletingReport = false;
          this.deletingReportDate = '';
        },
      });
  }

  loadHistory(): void {
    this.backgroundRefresh.refreshMany(['reports:latest-daily', 'reports:history']);
  }

  isDeleting(reportDate: string): boolean {
    return this.isDeletingReport && this.deletingReportDate === reportDate;
  }

  async copyLatestReport(): Promise<void> {
    const text = this.buildLatestReportText();
    const copied = await this.uiActions.copyText(text);
    if (copied) {
      this.setUtilityMessage('Đã sao chép báo cáo ngày mới nhất.');
      return;
    }

    this.setUtilityError('Chưa có báo cáo để sao chép.');
  }

  downloadLatestReport(): void {
    const text = this.buildLatestReportText();
    const filename = `bao-cao-ngay-${this.latestDailyReport?.reportDate || 'draft'}.txt`;
    const ok = this.uiActions.downloadText(filename, text);
    if (ok) {
      this.setUtilityMessage('Đã tải xuống báo cáo ngày.');
      return;
    }

    this.setUtilityError('Chưa có báo cáo để tải xuống.');
  }

  private buildLatestReportText(): string {
    if (!this.latestDailyReport) {
      return '';
    }

    return [
      `Ngày: ${this.latestDailyReport.reportDate}`,
      `Model: ${this.latestDailyReport.model}`,
      `Nguồn: ${this.latestDailyReport.source}`,
      `Tạo lúc: ${this.latestDailyReport.generatedAt}`,
      '',
      'TỔNG QUÁT',
      this.latestDailyReport.tongQuat,
      '',
      'CHI TIẾT TỪNG NỀN TẢNG',
      this.latestDailyReport.chiTietTungNenTang,
      '',
      'VẤN ĐỀ GẶP PHẢI',
      this.latestDailyReport.vanDeGapPhai,
      '',
      'ĐỀ XUẤT',
      this.latestDailyReport.deXuat,
    ].join('\n');
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
