import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import {
  Observable,
  Subject,
  catchError,
  concat,
  filter,
  interval,
  map,
  merge,
  of,
  scan,
  shareReplay,
  startWith,
  switchMap,
  tap,
} from 'rxjs';

import { ClientSettingsService } from './client-settings.service';
import { LoadingOrchestratorService } from './loading-orchestrator.service';

export interface LiveDataState<T> {
  data: T | null;
  loading: boolean;
  refreshing: boolean;
  error: string;
  updatedAt: string | null;
}

type RefreshReason = 'initial' | 'interval' | 'visible' | 'manual';

type LoadEvent<T> =
  | { type: 'loading'; background: boolean }
  | { type: 'success'; data: T }
  | { type: 'error'; message: string };

@Injectable({
  providedIn: 'root',
})
export class BackgroundSheetRefreshService {
  private readonly document = inject(DOCUMENT);
  private readonly clientSettings = inject(ClientSettingsService);
  private readonly loadingOrchestrator = inject(LoadingOrchestratorService);
  private readonly streams = new Map<string, Observable<LiveDataState<unknown>>>();
  private readonly refreshTriggers = new Map<string, Subject<void>>();

  private readonly visibilityResume$ = new Observable<RefreshReason>((observer) => {
    if (!this.document?.addEventListener) {
      observer.complete();
      return undefined;
    }

    const handleVisibility = () => {
      if (this.document.visibilityState === 'visible') {
        observer.next('visible');
      }
    };

    this.document.addEventListener('visibilitychange', handleVisibility);
    return () => this.document.removeEventListener('visibilitychange', handleVisibility);
  });

  watch<T>(key: string, loader: () => Observable<T>): Observable<LiveDataState<T>> {
    const existing = this.streams.get(key);
    if (existing) {
      return existing as Observable<LiveDataState<T>>;
    }

    const scopeKey = this.resolveScopeKey(key);
    this.loadingOrchestrator.registerTask(scopeKey, key);

    const manualRefresh$ = new Subject<void>();
    this.refreshTriggers.set(key, manualRefresh$);

    const refresh$ = merge(
      this.clientSettings.refreshIntervalMinutes$.pipe(
        switchMap((minutes) => {
          const intervalMs = this.resolveIntervalMs(minutes);
          return concat(
            of<RefreshReason>('initial'),
            interval(intervalMs).pipe(map(() => 'interval' as const)),
          );
        }),
      ),
      this.visibilityResume$,
      manualRefresh$.pipe(map(() => 'manual' as const)),
    ).pipe(
      filter((reason) => reason === 'initial' || reason === 'manual' || this.document.visibilityState === 'visible'),
    );

    const initialState: LiveDataState<T> = {
      data: null,
      loading: true,
      refreshing: false,
      error: '',
      updatedAt: null,
    };

    const stream$ = refresh$.pipe(
      switchMap((reason) => concat(
        of<LoadEvent<T>>({ type: 'loading', background: reason !== 'initial' }),
        loader().pipe(
          map((data) => ({ type: 'success', data }) as LoadEvent<T>),
          catchError((error) => of<LoadEvent<T>>({
            type: 'error',
            message: this.resolveErrorMessage(error),
          })),
        ),
      ).pipe(
        tap((event) => this.syncLoadingState(scopeKey, key, reason, event)),
      )),
      scan<LoadEvent<T>, LiveDataState<T>>((state, event) => {
        if (event.type === 'loading') {
          return {
            ...state,
            loading: state.data === null,
            refreshing: state.data !== null || event.background,
          };
        }

        if (event.type === 'success') {
          return {
            data: event.data,
            loading: false,
            refreshing: false,
            error: '',
            updatedAt: new Date().toISOString(),
          };
        }

        return {
          ...state,
          loading: false,
          refreshing: false,
          error: event.message,
        };
      }, initialState),
      startWith(initialState),
      shareReplay({ bufferSize: 1, refCount: false }),
    );

    this.streams.set(key, stream$ as Observable<LiveDataState<unknown>>);
    return stream$;
  }

  refresh(key: string): void {
    this.refreshTriggers.get(key)?.next();
  }

  refreshMany(keys: string[]): void {
    keys.forEach((key) => this.refresh(key));
  }

  private resolveIntervalMs(minutes: number): number {
    const configuredMs = Number.isFinite(minutes) && minutes > 0 ? minutes * 60_000 : 60_000;
    return Math.max(30_000, Math.min(configuredMs, 90_000));
  }

  private resolveScopeKey(key: string): string {
    const [scope] = key.split(':');
    return scope || 'global';
  }

  private resolveErrorMessage(error: unknown): string {
    if (typeof error === 'string' && error.trim()) {
      return error;
    }

    if (error && typeof error === 'object') {
      const detail = (error as { error?: { detail?: unknown } }).error?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
    }

    return 'Không thể làm mới dữ liệu từ backend.';
  }

  private syncLoadingState<T>(scopeKey: string, key: string, reason: RefreshReason, event: LoadEvent<T>): void {
    if (event.type === 'loading') {
      this.loadingOrchestrator.beginLoad(scopeKey, key, reason);
      return;
    }

    if (event.type === 'success') {
      this.loadingOrchestrator.completeLoad(scopeKey, key, reason, true);
      return;
    }

    this.loadingOrchestrator.completeLoad(scopeKey, key, reason, false, event.message);
  }
}
