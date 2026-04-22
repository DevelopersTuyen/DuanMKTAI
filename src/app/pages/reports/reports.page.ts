import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import {
  DailyReportLatestResponse,
  DailyReportSyncResponse,
  MarketingData,
  ReportSnapshot,
} from '../../core/services/marketing-data';

@Component({
  selector: 'app-reports',
  templateUrl: './reports.page.html',
  styleUrls: ['./reports.page.scss'],
  standalone: false,
})
export class ReportsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  reports: ReportSnapshot[] = [];
  latestDailyReport?: DailyReportLatestResponse;
  latestDailyReportError = '';
  dailyReportSyncResult?: DailyReportSyncResponse;
  dailyReportSyncError = '';
  isSyncingDailyReport = false;

  ngOnInit(): void {
    this.marketingData.getReports()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.reports = response.reports;
      });

    this.loadLatestDailyReport();
  }

  syncDailyReport(): void {
    this.isSyncingDailyReport = true;
    this.dailyReportSyncError = '';
    this.dailyReportSyncResult = undefined;

    this.marketingData.syncDailyReport()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.dailyReportSyncResult = response;
          this.isSyncingDailyReport = false;
          this.loadLatestDailyReport();
        },
        error: (error) => {
          this.dailyReportSyncError = error?.error?.detail ?? 'Không thể tạo báo cáo ngày.';
          this.isSyncingDailyReport = false;
        },
      });
  }

  private loadLatestDailyReport(): void {
    this.latestDailyReportError = '';
    this.marketingData.getLatestDailyReport()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.latestDailyReport = response;
        },
        error: (error) => {
          this.latestDailyReport = undefined;
          this.latestDailyReportError = error?.error?.detail ?? 'Chưa đọc được báo cáo ngày mới nhất.';
        },
      });
  }
}
