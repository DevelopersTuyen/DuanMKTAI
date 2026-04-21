import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { KeywordInsight, MarketingData, Recommendation } from '../../core/services/marketing-data';

@Component({
  selector: 'app-seo-insights',
  templateUrl: './seo-insights.page.html',
  styleUrls: ['./seo-insights.page.scss'],
  standalone: false,
})
export class SeoInsightsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  keywords: KeywordInsight[] = [];
  recommendations: Recommendation[] = [];

  ngOnInit(): void {
    this.marketingData.getSeoInsights()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.keywords = response.keywords;
        this.recommendations = response.recommendations;
      });
  }
}
