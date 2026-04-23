import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import {
  GoogleWebsiteStatusResponse,
  GoogleWebsiteSyncResponse,
  ManagedAccount,
  MarketingData,
  SocialPlatformStatus,
  SocialPlatformsSyncResponse,
  SyncChannel,
} from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

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
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);

  syncChannels: SyncChannel[] = [];
  accounts: ManagedAccount[] = [];
  googleStatus?: GoogleWebsiteStatusResponse;
  syncResult?: GoogleWebsiteSyncResponse;
  syncError = '';
  isSyncing = false;
  isLoading = true;
  loadError = '';

  socialStatuses: SocialPlatformStatus[] = [];
  socialSyncResult?: SocialPlatformsSyncResponse;
  socialSyncError = '';
  isSocialSyncing = false;
  utilityMessage = '';
  utilityError = '';

  readonly accountPageSize = 8;
  accountPage = 1;

  ngOnInit(): void {
    this.backgroundRefresh.watch('data-sync:overview', () => this.marketingData.getDataSync())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.syncChannels = state.data.syncChannels;
          this.accounts = state.data.accounts;
          this.loadError = '';
        } else if (state.error && !this.accounts.length) {
          this.loadError = state.error || 'Không thể tải bản đồ đồng bộ dữ liệu.';
        }

        this.isLoading = state.loading && !state.data;
      });

    this.backgroundRefresh.watch('data-sync:google-status', () => this.marketingData.getGoogleWebsiteStatus())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.googleStatus = state.data;
        }
      });

    this.backgroundRefresh.watch('data-sync:social-status', () => this.marketingData.getSocialStatus())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.socialStatuses = state.data.statuses;
        }
      });
  }

  get accountTotalPages(): number {
    return Math.max(1, Math.ceil(this.accounts.length / this.accountPageSize));
  }

  get pagedAccounts(): ManagedAccount[] {
    const start = (this.accountPage - 1) * this.accountPageSize;
    return this.accounts.slice(start, start + this.accountPageSize);
  }

  goToAccountPage(page: number): void {
    this.accountPage = Math.min(this.accountTotalPages, Math.max(1, page));
  }

  refreshAll(): void {
    this.backgroundRefresh.refreshMany(['data-sync:overview', 'data-sync:google-status', 'data-sync:social-status']);
    this.setUtilityMessage('Đã yêu cầu làm mới toàn bộ trạng thái đồng bộ.');
  }

  async copySpreadsheetId(): Promise<void> {
    const spreadsheetId = this.googleStatus?.spreadsheetId || '';
    const copied = await this.uiActions.copyText(spreadsheetId);
    if (copied) {
      this.setUtilityMessage('Đã sao chép Google Sheet ID.');
      return;
    }

    this.setUtilityError('Chưa có Google Sheet ID để sao chép.');
  }

  async copyWarnings(): Promise<void> {
    const socialWarnings = this.socialStatuses.reduce<string[]>((accumulator, item) => {
      accumulator.push(...item.warnings);
      return accumulator;
    }, []);

    const warnings = [
      ...(this.googleStatus?.warnings || []),
      ...socialWarnings,
    ].join('\n');
    const copied = await this.uiActions.copyText(warnings);
    if (copied) {
      this.setUtilityMessage('Đã sao chép danh sách cảnh báo đồng bộ.');
      return;
    }

    this.setUtilityError('Hiện chưa có cảnh báo để sao chép.');
  }

  async copySocialSummary(): Promise<void> {
    const summary = this.socialStatuses.map((item) => (
      `${item.name}: ${item.ready ? 'Sẵn sàng' : 'Chưa sẵn sàng'} | sheet ${item.worksheet} | tài nguyên ${item.configuredAssets}`
    )).join('\n');
    const copied = await this.uiActions.copyText(summary);
    if (copied) {
      this.setUtilityMessage('Đã sao chép tóm tắt social.');
      return;
    }

    this.setUtilityError('Chưa có trạng thái social để sao chép.');
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
          this.backgroundRefresh.refreshMany(['data-sync:overview', 'data-sync:google-status']);
        },
        error: (error) => {
          this.syncError = error?.error?.detail ?? 'Không thể đồng bộ dữ liệu website từ Google API.';
          this.isSyncing = false;
          this.backgroundRefresh.refresh('data-sync:google-status');
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
          this.backgroundRefresh.refreshMany(['data-sync:overview', 'data-sync:social-status']);
        },
        error: (error) => {
          this.socialSyncError = error?.error?.detail ?? 'Không thể đồng bộ dữ liệu social từ các API.';
          this.isSocialSyncing = false;
          this.backgroundRefresh.refresh('data-sync:social-status');
        },
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

  get wordpressSites(): WordPressUiSite[] {
    const mappedSites = this.googleStatus?.siteMappings?.map((mapping) => ({
      name: mapping.siteName,
      mode: mapping.gscSiteUrl ? 'auto' as const : 'manual' as const,
    })) || [];

    if (mappedSites.length) {
      return mappedSites;
    }

    return [
      { name: 'ssg-vietnam.com', mode: 'manual' },
      { name: 'fasolutions.vn', mode: 'manual' },
      { name: 'jssrv.com', mode: 'auto' },
    ];
  }

  getGscMappingState(siteName: string): { chipClass: string; label: string; detail: string } {
    const mapping = this.googleStatus?.siteMappings?.find((item) => item.siteName === siteName);
    if (!mapping) {
      return {
        chipClass: 'status-draft',
        label: 'Chưa có map',
        detail: 'Backend chưa trả về map GSC cho website này.',
      };
    }

    if (mapping.gscSiteUrl) {
      return {
        chipClass: 'status-live',
        label: 'Đã map',
        detail: `${mapping.wordpressBaseUrl} -> ${mapping.gscSiteUrl}`,
      };
    }

    return {
      chipClass: 'status-warning',
      label: 'Chưa map',
      detail: `${mapping.wordpressBaseUrl} chưa tìm thấy GSC site cùng domain trong quyền hiện tại.`,
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

  private setUtilityMessage(message: string): void {
    this.utilityMessage = message;
    this.utilityError = '';
  }

  private setUtilityError(message: string): void {
    this.utilityError = message;
    this.utilityMessage = '';
  }
}
