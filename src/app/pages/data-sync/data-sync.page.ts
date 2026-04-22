import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import {
  GoogleWebsiteStatusResponse,
  GoogleWebsiteSyncResponse,
  ManagedAccount,
  MarketingData,
  SocialPlatformStatus,
  SocialPlatformsSyncResponse,
  SyncChannel,
} from '../../core/services/marketing-data';

interface WordPressUiSite {
  name: string;
  mode: 'auto' | 'manual';
}

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

  socialStatuses: SocialPlatformStatus[] = [];
  socialSyncResult?: SocialPlatformsSyncResponse;
  socialSyncError = '';
  isSocialSyncing = false;

  readonly wordpressSites: WordPressUiSite[] = [
    { name: 'ssg-vietnam.com', mode: 'manual' },
    { name: 'fasolutions.vn', mode: 'manual' },
    { name: 'jssrv.com', mode: 'auto' },
  ];

  ngOnInit(): void {
    this.marketingData.getDataSync()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.syncChannels = response.syncChannels;
        this.accounts = response.accounts;
      });

    this.loadGoogleStatus();
    this.loadSocialStatus();
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
          this.syncError = error?.error?.detail ?? 'Không thể đồng bộ dữ liệu website từ Google API.';
          this.isSyncing = false;
          this.loadGoogleStatus();
        },
      });
  }

  syncSocialPlatforms(): void {
    this.isSocialSyncing = true;
    this.socialSyncError = '';
    this.socialSyncResult = undefined;
    this.marketingData.syncSocialPlatforms()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.socialSyncResult = response;
          this.isSocialSyncing = false;
          this.loadSocialStatus();
        },
        error: (error) => {
          this.socialSyncError = error?.error?.detail ?? 'Không thể đồng bộ dữ liệu social từ các API.';
          this.isSocialSyncing = false;
          this.loadSocialStatus();
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

  private loadSocialStatus(): void {
    this.marketingData.getSocialStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.socialStatuses = response.statuses;
      });
  }

  getWordPressSiteState(siteName: string): { chipClass: string; label: string; detail: string } {
    const warnings = this.syncResult?.warnings ?? [];
    const siteWarning = warnings.find((warning) => warning.includes(siteName));

    if (siteWarning) {
      return {
        chipClass: 'status-warning',
        label: 'Theo dõi thủ công',
        detail: 'Tạm thời theo dõi ngoài giao diện. Kết nối của site này chưa cần xử lý gấp.',
      };
    }

    if (siteName === 'jssrv.com' && (this.syncResult?.wordpressPosts ?? 0) > 0) {
      return {
        chipClass: 'status-live',
        label: 'Tự động đồng bộ',
        detail: `Đã lấy được dữ liệu bài viết. Tổng số bài đồng bộ lần gần nhất: ${this.syncResult?.wordpressPosts}.`,
      };
    }

    if (siteName === 'jssrv.com') {
      return {
        chipClass: 'status-live',
        label: 'Sẵn sàng',
        detail: 'Site này đang được ưu tiên đồng bộ tự động vào trang tính Post_web.',
      };
    }

    return {
      chipClass: 'status-draft',
      label: 'Chờ kiểm tra',
      detail: 'Hiện đang được đưa vào quy trình theo dõi thủ công trên giao diện.',
    };
  }

  getSocialStatusClass(status: SocialPlatformStatus): string {
    if (status.ready) {
      return 'status-live';
    }
    if (status.hasCredentials || status.configuredAssets > 0) {
      return 'status-warning';
    }
    return 'status-draft';
  }

  hasReadySocialPlatform(): boolean {
    return this.socialStatuses.some((item) => item.ready);
  }
}
