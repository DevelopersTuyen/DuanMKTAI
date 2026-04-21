import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { MarketingData, ReportSnapshot } from '../../core/services/marketing-data';

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

  ngOnInit(): void {
    this.marketingData.getReports()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.reports = response.reports;
      });
  }
}
