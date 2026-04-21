import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { MarketingData } from '../../core/services/marketing-data';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.page.html',
  styleUrls: ['./settings.page.scss'],
  standalone: false,
})
export class SettingsPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  config = {
    apiBaseUrl: environment.apiBaseUrl,
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

  ngOnInit(): void {
    this.marketingData.getSettingsDefaults()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.config = {
          ...this.config,
          apiBaseUrl: response.apiBaseUrl,
          ollamaBaseUrl: response.ollamaBaseUrl,
          ollamaModel: response.ollamaModel,
          spreadsheetId: response.spreadsheetId,
          worksheet: response.worksheet,
          syncInterval: response.syncIntervalMinutes,
        };
      });
  }

  saveSettings(): void {
    this.saveMessage = 'Đã cập nhật cấu hình cục bộ trên frontend. Nếu muốn lưu thật, hãy thêm endpoint backend cho phần cài đặt.';
  }

}
