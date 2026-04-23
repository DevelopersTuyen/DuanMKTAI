import { Injectable } from '@angular/core';
import { BehaviorSubject, distinctUntilChanged, map } from 'rxjs';

import { environment } from '../../../environments/environment';

interface ClientRuntimeSettings {
  apiBaseUrl: string;
  syncIntervalMinutes: number;
}

const STORAGE_KEY = 'marketing-ai-client-settings';

@Injectable({
  providedIn: 'root',
})
export class ClientSettingsService {
  private readonly defaults: ClientRuntimeSettings = {
    apiBaseUrl: environment.apiBaseUrl,
    syncIntervalMinutes: environment.sync.intervalMinutes,
  };
  private readonly settingsSubject = new BehaviorSubject<ClientRuntimeSettings>(this.readSettings());

  readonly settings$ = this.settingsSubject.asObservable();
  readonly refreshIntervalMinutes$ = this.settings$.pipe(
    map((settings) => settings.syncIntervalMinutes),
    distinctUntilChanged(),
  );

  get apiBaseUrl(): string {
    return this.settingsSubject.value.apiBaseUrl;
  }

  get syncIntervalMinutes(): number {
    return this.settingsSubject.value.syncIntervalMinutes;
  }

  update(settings: Partial<ClientRuntimeSettings>): void {
    const merged = {
      ...this.settingsSubject.value,
      ...settings,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
    this.settingsSubject.next(merged);
  }

  private readSettings(): ClientRuntimeSettings {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { ...this.defaults };
      }

      const parsed = JSON.parse(raw) as Partial<ClientRuntimeSettings>;
      const apiBaseUrl = String(parsed.apiBaseUrl || '').trim();
      const syncIntervalMinutes = Number(parsed.syncIntervalMinutes);

      return {
        apiBaseUrl: apiBaseUrl || this.defaults.apiBaseUrl,
        syncIntervalMinutes: Number.isFinite(syncIntervalMinutes) && syncIntervalMinutes > 0
          ? syncIntervalMinutes
          : this.defaults.syncIntervalMinutes,
      };
    } catch {
      return { ...this.defaults };
    }
  }
}
