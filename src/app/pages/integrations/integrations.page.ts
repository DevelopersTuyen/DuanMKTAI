import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import { GoogleWebsiteStatusResponse, MarketingData, OAuthProviderStatus } from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

@Component({
  selector: 'app-integrations',
  templateUrl: './integrations.page.html',
  styleUrls: ['./integrations.page.scss'],
  standalone: false,
})
export class IntegrationsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  oauthProviders: OAuthProviderStatus[] = [];
  googleWebsiteStatus?: GoogleWebsiteStatusResponse;
  googleWebsiteError = '';
  busyProvider = '';
  noticeMessage = '';
  noticeTone: 'success' | 'danger' = 'success';
  loadError = '';
  isLoading = true;
  isWebsiteLoading = true;

  readonly pageSize = 6;
  currentPage = 1;

  ngOnInit(): void {
    this.backgroundRefresh.watch('integrations:oauth-providers', () => this.marketingData.getOAuthProviders())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.oauthProviders = state.data.providers;
          if (this.currentPage > this.totalPages) {
            this.currentPage = this.totalPages;
          }
          this.loadError = '';
        } else if (state.error && !this.oauthProviders.length) {
          this.loadError = state.error ?? 'Không thể tải trạng thái kết nối OAuth.';
        }

        this.isLoading = state.loading && !state.data;
      });

    this.backgroundRefresh.watch('integrations:google-web', () => this.marketingData.getGoogleWebsiteStatus())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.googleWebsiteStatus = state.data;
          this.googleWebsiteError = '';
        } else if (state.error && !this.googleWebsiteStatus) {
          this.googleWebsiteError = state.error ?? 'Không thể tải trạng thái Google Web.';
        }

        this.isWebsiteLoading = state.loading && !state.data;
      });

    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const message = params.get('oauth_message');
        const status = params.get('oauth_status');

        if (message) {
          this.noticeMessage = message;
          this.noticeTone = status === 'success' ? 'success' : 'danger';
          this.backgroundRefresh.refreshMany(['integrations:oauth-providers', 'integrations:google-web']);
          this.router.navigate([], {
            relativeTo: this.route,
            replaceUrl: true,
            queryParams: {
              oauth_provider: null,
              oauth_status: null,
              oauth_message: null,
            },
            queryParamsHandling: 'merge',
          });
        }
      });
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.oauthProviders.length / this.pageSize));
  }

  get pagedProviders(): OAuthProviderStatus[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.oauthProviders.slice(start, start + this.pageSize);
  }

  goToPage(page: number): void {
    this.currentPage = Math.min(this.totalPages, Math.max(1, page));
  }

  connect(provider: OAuthProviderStatus): void {
    if (!provider.connectable) {
      this.noticeMessage = `Thiếu client ID hoặc client secret cho ${this.getProviderLabel(provider)}.`;
      this.noticeTone = 'danger';
      return;
    }

    this.busyProvider = provider.provider;
    this.noticeMessage = '';
    const returnUrl = `${window.location.origin}/integrations`;
    this.marketingData.getOAuthStart(provider.provider, returnUrl)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          window.location.assign(response.authorizationUrl);
        },
        error: (error) => {
          this.noticeMessage = error?.error?.detail ?? `Không thể khởi tạo kết nối cho ${this.getProviderLabel(provider)}.`;
          this.noticeTone = 'danger';
          this.busyProvider = '';
        },
      });
  }

  refresh(provider: OAuthProviderStatus): void {
    this.busyProvider = provider.provider;
    this.noticeMessage = '';
    this.marketingData.refreshOAuthProvider(provider.provider)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.noticeMessage = response.message;
          this.noticeTone = 'success';
          this.busyProvider = '';
          this.backgroundRefresh.refresh('integrations:oauth-providers');
        },
        error: (error) => {
          this.noticeMessage = error?.error?.detail ?? `Không thể làm mới token cho ${this.getProviderLabel(provider)}.`;
          this.noticeTone = 'danger';
          this.busyProvider = '';
          this.backgroundRefresh.refresh('integrations:oauth-providers');
        },
      });
  }

  disconnect(provider: OAuthProviderStatus): void {
    this.busyProvider = provider.provider;
    this.noticeMessage = '';
    this.marketingData.disconnectOAuthProvider(provider.provider)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.noticeMessage = response.message;
          this.noticeTone = 'success';
          this.busyProvider = '';
          this.backgroundRefresh.refresh('integrations:oauth-providers');
        },
        error: (error) => {
          this.noticeMessage = error?.error?.detail ?? `Không thể gỡ kết nối ${this.getProviderLabel(provider)}.`;
          this.noticeTone = 'danger';
          this.busyProvider = '';
        },
      });
  }

  isBusy(provider: OAuthProviderStatus): boolean {
    return this.busyProvider === provider.provider;
  }

  formatDate(value: string | null): string {
    if (!value) {
      return 'Chưa có';
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  refreshIntegrations(): void {
    this.backgroundRefresh.refreshMany(['integrations:oauth-providers', 'integrations:google-web']);
    this.noticeMessage = 'Đã yêu cầu làm mới trạng thái kết nối.';
    this.noticeTone = 'success';
  }

  async copyConnectionSummary(): Promise<void> {
    const webSummary = this.googleWebsiteStatus
      ? [
          'Google Web:',
          `- Trạng thái: ${this.googleWebsiteStatus.ready ? 'Sẵn sàng' : 'Cần cấu hình'}`,
          `- Spreadsheet: ${this.googleWebsiteStatus.spreadsheetId}`,
          `- Website worksheet: ${this.googleWebsiteStatus.worksheet}`,
          `- Post worksheet: ${this.googleWebsiteStatus.wordpressWorksheet}`,
          `- WordPress sites: ${this.googleWebsiteStatus.wordpressSitesCount}`,
          `- GSC sites: ${this.googleWebsiteStatus.searchConsoleSites.join(', ') || 'Chưa có'}`,
        ].join('\n')
      : '';
    const oauthSummary = this.oauthProviders.map((provider) => (
      `${this.getProviderLabel(provider)}: ${provider.status} | ${provider.accountLabel || 'Chưa kết nối'} | ${provider.assetSummary}`
    )).join('\n');
    const content = [webSummary, oauthSummary].filter(Boolean).join('\n\n');
    const copied = await this.uiActions.copyText(content);
    if (copied) {
      this.noticeMessage = 'Đã sao chép tóm tắt kết nối.';
      this.noticeTone = 'success';
      return;
    }

    this.noticeMessage = 'Chưa có dữ liệu kết nối để sao chép.';
    this.noticeTone = 'danger';
  }

  async copyProviderWarnings(provider: OAuthProviderStatus): Promise<void> {
    const content = provider.warnings.join('\n');
    const copied = await this.uiActions.copyText(content);
    if (copied) {
      this.noticeMessage = `Đã sao chép cảnh báo của ${this.getProviderLabel(provider)}.`;
      this.noticeTone = 'success';
      return;
    }

    this.noticeMessage = `${this.getProviderLabel(provider)} hiện không có cảnh báo để sao chép.`;
    this.noticeTone = 'danger';
  }

  getProviderLabel(provider: OAuthProviderStatus): string {
    if (provider.provider === 'google-youtube') {
      return 'YouTube';
    }

    return provider.label;
  }
}
