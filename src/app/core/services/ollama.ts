import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of } from 'rxjs';

import { ClientSettingsService } from './client-settings.service';

export interface MarketingPromptRequest {
  platform: string;
  goal: string;
  tone: string;
  brief: string;
}

interface OllamaGenerateResponse {
  response: string;
  model: string;
  source: 'ollama' | 'fallback';
}

@Injectable({
  providedIn: 'root',
})
export class Ollama {
  private readonly http = inject(HttpClient);
  private readonly clientSettings = inject(ClientSettingsService);

  generateMarketingCopy(request: MarketingPromptRequest): Observable<string> {
    return this.http
      .post<OllamaGenerateResponse>(`${this.clientSettings.apiBaseUrl}/content/generate`, request)
      .pipe(
        map((response) => response.response?.trim() || this.buildFallbackResponse(request)),
        catchError(() => of(this.buildFallbackResponse(request))),
      );
  }

  private buildFallbackResponse(request: MarketingPromptRequest): string {
    return [
      `Tieu de de xuat cho ${request.platform}: ${request.goal}.`,
      '',
      `Mo bai: ${request.brief}`,
      '',
      'Hook 1: Mo ra bang mot pain point ro rang va con so cu the.',
      'Hook 2: Neu loi ich nhanh, de do va gan voi KPI.',
      'Hook 3: Chen bang chung social proof tu campaign truoc.',
      '',
      `CTA 1: Dang ky ngay de tang ${request.goal.toLowerCase()}.`,
      `CTA 2: Inbox de nhan ke hoach ${request.platform.toLowerCase()} ca nhan hoa.`,
      'CTA 3: Tai checklist de trien khai trong 7 ngay.',
      '',
      'Visual: Hero graphic, mini dashboard KPI, testimonial card.',
    ].join('\n');
  }
}
