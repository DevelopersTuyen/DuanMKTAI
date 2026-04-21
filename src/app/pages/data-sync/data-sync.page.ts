import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { GoogleWebsiteStatusResponse, GoogleWebsiteSyncResponse, ManagedAccount, MarketingData, SyncChannel } from '../../core/services/marketing-data';

@Component({
  selector: 'app-data-sync',
  templateUrl: './data-sync.page.html',
  styleUrls: ['./data-sync.page.scss'],
  standalone: false,
})
export class DataSyncPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  syncChannels: SyncChannel[] = [];
  accounts: ManagedAccount[] = [];
  googleStatus?: GoogleWebsiteStatusResponse;
  syncResult?: GoogleWebsiteSyncResponse;
  syncError = '';
  isSyncing = false;

  ngOnInit(): void {
    this.marketingData.getDataSync()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.syncChannels = response.syncChannels;
        this.accounts = response.accounts;
      });

    this.loadGoogleStatus();
  }

  syncGoogleWebsite(): void {
    this.isSyncing = true;
    this.syncError = '';
    this.syncResult = undefined;
    this.marketingData.syncGoogleWebsite()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.syncResult = response;
          this.isSyncing = false;
          this.loadGoogleStatus();
        },
        error: (error) => {
          this.syncError = error?.error?.detail ?? 'Khong the dong bo website data tu Google APIs.';
          this.isSyncing = false;
          this.loadGoogleStatus();
        },
      });
  }

  private loadGoogleStatus(): void {
    this.marketingData.getGoogleWebsiteStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.googleStatus = response;
      });
  }
}
