import { Injectable } from '@angular/core';

import { environment } from '../../../environments/environment';

interface ClientRuntimeSettings {
  apiBaseUrl: string;
}

const STORAGE_KEY = 'marketing-ai-client-settings';

@Injectable({
  providedIn: 'root',
})
export class ClientSettingsService {
  private readonly defaults: ClientRuntimeSettings = {
    apiBaseUrl: environment.apiBaseUrl,
  };

  get apiBaseUrl(): string {
    return this.readSettings().apiBaseUrl;
  }

  update(settings: Partial<ClientRuntimeSettings>): void {
    const merged = {
      ...this.readSettings(),
      ...settings,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  }

  private readSettings(): ClientRuntimeSettings {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { ...this.defaults };
      }

      const parsed = JSON.parse(raw) as Partial<ClientRuntimeSettings>;
      const apiBaseUrl = String(parsed.apiBaseUrl || '').trim();
      return {
        apiBaseUrl: apiBaseUrl || this.defaults.apiBaseUrl,
      };
    } catch {
      return { ...this.defaults };
    }
  }
}
