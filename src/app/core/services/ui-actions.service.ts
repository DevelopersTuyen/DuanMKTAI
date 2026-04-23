import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class UiActionsService {
  async copyText(text: string): Promise<boolean> {
    const normalized = text.trim();
    if (!normalized) {
      return false;
    }

    if (navigator?.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(normalized);
        return true;
      } catch {
        // Fallback below.
      }
    }

    const textarea = document.createElement('textarea');
    textarea.value = normalized;
    textarea.setAttribute('readonly', 'true');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
      return document.execCommand('copy');
    } finally {
      document.body.removeChild(textarea);
    }
  }

  downloadText(filename: string, content: string, mimeType = 'text/plain;charset=utf-8'): boolean {
    if (!content.trim()) {
      return false;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    return true;
  }
}
