import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { IntegrationStatus, MarketingData } from '../../core/services/marketing-data';

@Component({
  selector: 'app-integrations',
  templateUrl: './integrations.page.html',
  styleUrls: ['./integrations.page.scss'],
  standalone: false,
})
export class IntegrationsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  integrations: IntegrationStatus[] = [];

  ngOnInit(): void {
    this.marketingData.getIntegrations()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.integrations = response.integrations;
      });
  }
}
