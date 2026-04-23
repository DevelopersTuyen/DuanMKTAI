import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { environment } from '../../../environments/environment';
import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import { ClientSettingsService } from '../../core/services/client-settings.service';
import {
  AutomationStatusResponse,
  MarketingData,
  SettingsUpdateRequest,
} from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.page.html',
  styleUrls: ['./settings.page.scss'],
  standalone: false,
})
export class SettingsPage implements OnInit {
  readonly weekdayOptions = [
    { value: 0, label: 'T2' },
    { value: 1, label: 'T3' },
    { value: 2, label: 'T4' },
    { value: 3, label: 'T5' },
    { value: 4, label: 'T6' },
    { value: 5, label: 'T7' },
    { value: 6, label: 'CN' },
  ];

  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly clientSettings = inject(ClientSettingsService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);

  config = {
    apiBaseUrl: this.clientSettings.apiBaseUrl,
    ollamaBaseUrl: environment.ollama.baseUrl,
    ollamaModel: environment.ollama.model,
    spreadsheetId: environment.googleSheets.spreadsheetId,
    worksheet: environment.googleSheets.worksheet,
    syncMode: 'interval' as 'interval' | 'scheduled',
    syncStartTime: '08:00',
    syncInterval: this.clientSettings.syncIntervalMinutes,
    syncDaysOfWeek: [0, 1, 2, 3, 4, 5, 6],
    syncLoopEnabled: true,
    syncWebsiteEnabled: true,
    syncSocialEnabled: true,
    autoSync: true,
    autoRecommend: true,
    autoSchedule: false,
  };

  saveMessage = '';
  errorMessage = '';
  utilityMessage = '';
  utilityError = '';
  isSaving = false;
  isLoading = true;
  automationStatus: AutomationStatusResponse | null = null;
  private lastLoadedConfig = { ...this.config };

  ngOnInit(): void {
    this.loadSettings();

    this.backgroundRefresh.watch('settings:automation-status', () => this.marketingData.getAutomationStatus())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.automationStatus = state.data;
        } else if (state.error && !this.automationStatus) {
          this.automationStatus = null;
        }
      });
  }

  saveSettings(): void {
    this.isSaving = true;
    this.saveMessage = '';
    this.errorMessage = '';

    const payload: SettingsUpdateRequest = {
      apiBaseUrl: this.config.apiBaseUrl.trim(),
      ollamaBaseUrl: this.config.ollamaBaseUrl.trim(),
      ollamaModel: this.config.ollamaModel.trim(),
      spreadsheetId: this.config.spreadsheetId.trim(),
      worksheet: this.config.worksheet.trim(),
      syncMode: this.config.syncMode,
      syncStartTime: this.config.syncStartTime,
      syncIntervalMinutes: Number(this.config.syncInterval),
      syncDaysOfWeek: [...this.config.syncDaysOfWeek].sort((left, right) => left - right),
      syncLoopEnabled: this.config.syncLoopEnabled,
      syncWebsiteEnabled: this.config.syncWebsiteEnabled,
      syncSocialEnabled: this.config.syncSocialEnabled,
      autoSync: this.config.autoSync,
      autoRecommend: this.config.autoRecommend,
      autoSchedule: this.config.autoSchedule,
    };

    this.marketingData
      .saveSettings(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.config = {
            apiBaseUrl: response.settings.apiBaseUrl,
            ollamaBaseUrl: response.settings.ollamaBaseUrl,
            ollamaModel: response.settings.ollamaModel,
            spreadsheetId: response.settings.spreadsheetId,
            worksheet: response.settings.worksheet,
            syncMode: response.settings.syncMode,
            syncStartTime: response.settings.syncStartTime,
            syncInterval: response.settings.syncIntervalMinutes,
            syncDaysOfWeek: [...response.settings.syncDaysOfWeek].sort((left, right) => left - right),
            syncLoopEnabled: response.settings.syncLoopEnabled,
            syncWebsiteEnabled: response.settings.syncWebsiteEnabled,
            syncSocialEnabled: response.settings.syncSocialEnabled,
            autoSync: response.settings.autoSync,
            autoRecommend: response.settings.autoRecommend,
            autoSchedule: response.settings.autoSchedule,
          };
          this.lastLoadedConfig = { ...this.config };
          this.clientSettings.update({
            apiBaseUrl: response.settings.apiBaseUrl,
            syncIntervalMinutes: response.settings.syncIntervalMinutes,
          });
          this.saveMessage = response.message;
          this.isSaving = false;
          this.backgroundRefresh.refresh('settings:automation-status');
        },
        error: (error) => {
          this.errorMessage = error?.error?.detail || 'Không thể lưu cài đặt hệ thống.';
          this.isSaving = false;
        },
      });
  }

  loadAutomationStatus(): void {
    this.backgroundRefresh.refresh('settings:automation-status');
  }

  refreshSettings(): void {
    this.loadSettings(true);
    this.backgroundRefresh.refresh('settings:automation-status');
  }

  resetForm(): void {
    this.config = { ...this.lastLoadedConfig };
    this.setUtilityMessage('Đã khôi phục biểu mẫu theo cấu hình đã nạp gần nhất.');
  }

  async copySettingsJson(): Promise<void> {
    const copied = await this.uiActions.copyText(JSON.stringify(this.config, null, 2));
    if (copied) {
      this.setUtilityMessage('Đã sao chép JSON cấu hình hiện tại.');
      return;
    }

    this.setUtilityError('Không thể sao chép cấu hình hiện tại.');
  }

  downloadSettingsJson(): void {
    const ok = this.uiActions.downloadText(
      `settings-${new Date().toISOString().slice(0, 10)}.json`,
      JSON.stringify(this.config, null, 2),
      'application/json;charset=utf-8',
    );
    if (ok) {
      this.setUtilityMessage('Đã tải xuống JSON cấu hình.');
      return;
    }

    this.setUtilityError('Không thể tải xuống cấu hình hiện tại.');
  }

  formatDate(value: string | null): string {
    if (!value) {
      return 'Chưa có';
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString('vi-VN');
  }

  toggleSyncWeekday(day: number): void {
    const selectedDays = new Set(this.config.syncDaysOfWeek);
    if (selectedDays.has(day)) {
      if (selectedDays.size === 1) {
        return;
      }
      selectedDays.delete(day);
    } else {
      selectedDays.add(day);
    }

    this.config.syncDaysOfWeek = [...selectedDays].sort((left, right) => left - right);
  }

  isSyncWeekdaySelected(day: number): boolean {
    return this.config.syncDaysOfWeek.includes(day);
  }

  formatSyncWeekdays(days: number[]): string {
    const labels = this.weekdayOptions
      .filter((option) => days.includes(option.value))
      .map((option) => option.label);
    return labels.length ? labels.join(', ') : 'Tất cả các ngày';
  }

  private loadSettings(showRefreshMessage = false): void {
    this.marketingData
      .getSettingsDefaults()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.config = {
            apiBaseUrl: response.apiBaseUrl,
            ollamaBaseUrl: response.ollamaBaseUrl,
            ollamaModel: response.ollamaModel,
            spreadsheetId: response.spreadsheetId,
            worksheet: response.worksheet,
            syncMode: response.syncMode,
            syncStartTime: response.syncStartTime,
            syncInterval: response.syncIntervalMinutes,
            syncDaysOfWeek: [...response.syncDaysOfWeek].sort((left, right) => left - right),
            syncLoopEnabled: response.syncLoopEnabled,
            syncWebsiteEnabled: response.syncWebsiteEnabled,
            syncSocialEnabled: response.syncSocialEnabled,
            autoSync: response.autoSync,
            autoRecommend: response.autoRecommend,
            autoSchedule: response.autoSchedule,
          };
          this.lastLoadedConfig = { ...this.config };
          this.clientSettings.update({
            apiBaseUrl: response.apiBaseUrl,
            syncIntervalMinutes: response.syncIntervalMinutes,
          });
          if (showRefreshMessage) {
            this.setUtilityMessage('Đã tải lại cấu hình từ backend.');
          }
          this.isLoading = false;
        },
        error: () => {
          this.errorMessage = 'Không thể tải cài đặt hệ thống hiện tại.';
          this.isLoading = false;
        },
      });
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
