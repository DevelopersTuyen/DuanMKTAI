import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import {
  MarketingData,
  OAuthProviderStatus,
} from '../../core/services/marketing-data';

@Component({
  selector: 'app-integrations',
  templateUrl: './integrations.page.html',
  styleUrls: ['./integrations.page.scss'],
  standalone: false,
})
export class IntegrationsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  oauthProviders: OAuthProviderStatus[] = [];
  busyProvider = '';
  noticeMessage = '';
  noticeTone: 'success' | 'danger' = 'success';
  loadError = '';

  ngOnInit(): void {
    this.loadOAuthProviders();

    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const message = params.get('oauth_message');
        const status = params.get('oauth_status');

        if (message) {
          this.noticeMessage = message;
          this.noticeTone = status === 'success' ? 'success' : 'danger';
          this.loadOAuthProviders();
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

  loadOAuthProviders(): void {
    this.loadError = '';
    this.marketingData.getOAuthProviders()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.oauthProviders = response.providers;
        },
        error: (error) => {
          this.loadError = error?.error?.detail ?? 'Không thể tải trạng thái kết nối OAuth.';
        },
      });
  }

  connect(provider: OAuthProviderStatus): void {
    if (!provider.connectable) {
      this.noticeMessage = `Thiếu client ID hoặc client secret cho ${provider.label}.`;
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
          this.noticeMessage = error?.error?.detail ?? `Không thể khởi tạo kết nối cho ${provider.label}.`;
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
          this.loadOAuthProviders();
        },
        error: (error) => {
          this.noticeMessage = error?.error?.detail ?? `Không thể làm mới token cho ${provider.label}.`;
          this.noticeTone = 'danger';
          this.busyProvider = '';
          this.loadOAuthProviders();
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
          this.loadOAuthProviders();
        },
        error: (error) => {
          this.noticeMessage = error?.error?.detail ?? `Không thể gỡ kết nối ${provider.label}.`;
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
}
