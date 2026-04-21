import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ContentPerformance, MarketingData, PlatformPerformance, Recommendation } from '../../core/services/marketing-data';

@Component({
  selector: 'app-analytics',
  templateUrl: './analytics.page.html',
  styleUrls: ['./analytics.page.scss'],
  standalone: false,
})
export class AnalyticsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  platforms: PlatformPerformance[] = [];
  topContents: ContentPerformance[] = [];
  recommendations: Recommendation[] = [];

  ngOnInit(): void {
    this.marketingData.getAnalytics()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.platforms = response.platforms;
        this.topContents = response.topContents;
        this.recommendations = response.recommendations;
      });
  }
}
