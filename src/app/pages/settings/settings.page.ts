import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { environment } from '../../../environments/environment';
import { ClientSettingsService } from '../../core/services/client-settings.service';
import {
  AutomationStatusResponse,
  MarketingData,
  SettingsUpdateRequest,
} from '../../core/services/marketing-data';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.page.html',
  styleUrls: ['./settings.page.scss'],
  standalone: false,
})
export class SettingsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly clientSettings = inject(ClientSettingsService);
  private readonly destroyRef = inject(DestroyRef);

  config = {
    apiBaseUrl: this.clientSettings.apiBaseUrl,
    ollamaBaseUrl: environment.ollama.baseUrl,
    ollamaModel: environment.ollama.model,
    spreadsheetId: environment.googleSheets.spreadsheetId,
    worksheet: environment.googleSheets.worksheet,
    syncInterval: environment.sync.intervalMinutes,
    autoSync: true,
    autoRecommend: true,
    autoSchedule: false,
  };

  saveMessage = '';
  errorMessage = '';
  isSaving = false;
  automationStatus: AutomationStatusResponse | null = null;

  ngOnInit(): void {
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
            syncInterval: response.syncIntervalMinutes,
            autoSync: response.autoSync,
            autoRecommend: response.autoRecommend,
            autoSchedule: response.autoSchedule,
          };
          this.clientSettings.update({ apiBaseUrl: response.apiBaseUrl });
        },
        error: () => {
          this.errorMessage = 'Không thể tải cài đặt hệ thống hiện tại.';
        },
      });

    this.loadAutomationStatus();
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
      syncIntervalMinutes: Number(this.config.syncInterval),
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
            syncInterval: response.settings.syncIntervalMinutes,
            autoSync: response.settings.autoSync,
            autoRecommend: response.settings.autoRecommend,
            autoSchedule: response.settings.autoSchedule,
          };
          this.clientSettings.update({ apiBaseUrl: response.settings.apiBaseUrl });
          this.saveMessage = response.message;
          this.isSaving = false;
          this.loadAutomationStatus();
        },
        error: (error) => {
          this.errorMessage = error?.error?.detail || 'Không thể lưu cài đặt hệ thống.';
          this.isSaving = false;
        },
      });
  }

  loadAutomationStatus(): void {
    this.marketingData
      .getAutomationStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.automationStatus = response;
        },
        error: () => {
          this.automationStatus = null;
        },
      });
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
}
