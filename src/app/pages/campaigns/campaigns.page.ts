import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { CampaignOverview, MarketingData } from '../../core/services/marketing-data';

@Component({
  selector: 'app-campaigns',
  templateUrl: './campaigns.page.html',
  styleUrls: ['./campaigns.page.scss'],
  standalone: false,
})
export class CampaignsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  campaigns: CampaignOverview[] = [];

  ngOnInit(): void {
    this.marketingData.getCampaigns()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.campaigns = response.campaigns;
      });
  }
}
