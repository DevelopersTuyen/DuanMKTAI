import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

type LoadReason = 'initial' | 'interval' | 'visible' | 'manual';

interface ScopeTracker {
  activeKeys: Set<string>;
  registeredKeys: Set<string>;
  startedInCycle: Set<string>;
  completedInCycle: Set<string>;
  updatedAt: string | null;
  lastError: string;
  lastReason: LoadReason | null;
}

export interface GlobalLoadingState {
  progress: number;
  totalTasks: number;
  completedTasks: number;
  activeTasks: number;
  bootstrapping: boolean;
  statusText: string;
}

export interface ScopeLoadingState {
  scope: string;
  progress: number;
  activeTasks: number;
  registeredTasks: number;
  updatedAt: string | null;
  lastError: string;
  loading: boolean;
  statusText: string;
}

@Injectable({
  providedIn: 'root',
})
export class LoadingOrchestratorService {
  private readonly registeredKeys = new Set<string>();
  private readonly initiallyLoadedKeys = new Set<string>();
  private readonly scopeTrackers = new Map<string, ScopeTracker>();
  private readonly scopeSubjects = new Map<string, BehaviorSubject<ScopeLoadingState>>();
  private readonly globalSubject = new BehaviorSubject<GlobalLoadingState>({
    progress: 0,
    totalTasks: 0,
    completedTasks: 0,
    activeTasks: 0,
    bootstrapping: false,
    statusText: 'Đang chờ khởi tạo dữ liệu hệ thống',
  });

  readonly globalState$ = this.globalSubject.asObservable();

  registerTask(scope: string, key: string): void {
    const tracker = this.ensureScope(scope);
    tracker.registeredKeys.add(key);

    if (!this.registeredKeys.has(key)) {
      this.registeredKeys.add(key);
      this.emitGlobal();
    }

    this.emitScope(scope);
  }

  beginLoad(scope: string, key: string, reason: LoadReason): void {
    const tracker = this.ensureScope(scope);
    tracker.registeredKeys.add(key);

    if (tracker.activeKeys.size === 0) {
      tracker.startedInCycle.clear();
      tracker.completedInCycle.clear();
    }

    tracker.activeKeys.add(key);
    tracker.startedInCycle.add(key);
    tracker.lastReason = reason;
    tracker.lastError = '';

    this.emitScope(scope);
    this.emitGlobal();
  }

  completeLoad(scope: string, key: string, reason: LoadReason, success: boolean, errorMessage = ''): void {
    const tracker = this.ensureScope(scope);
    tracker.activeKeys.delete(key);

    if (tracker.startedInCycle.has(key)) {
      tracker.completedInCycle.add(key);
    }

    tracker.lastReason = reason;
    tracker.updatedAt = new Date().toISOString();
    tracker.lastError = success ? '' : errorMessage;

    if (success) {
      this.initiallyLoadedKeys.add(key);
    }

    this.emitScope(scope);
    this.emitGlobal();
  }

  scopeState$(scope: string): Observable<ScopeLoadingState> {
    return this.ensureScopeSubject(scope).asObservable();
  }

  private ensureScope(scope: string): ScopeTracker {
    const existing = this.scopeTrackers.get(scope);
    if (existing) {
      return existing;
    }

    const tracker: ScopeTracker = {
      activeKeys: new Set<string>(),
      registeredKeys: new Set<string>(),
      startedInCycle: new Set<string>(),
      completedInCycle: new Set<string>(),
      updatedAt: null,
      lastError: '',
      lastReason: null,
    };

    this.scopeTrackers.set(scope, tracker);
    this.ensureScopeSubject(scope);
    return tracker;
  }

  private ensureScopeSubject(scope: string): BehaviorSubject<ScopeLoadingState> {
    const existing = this.scopeSubjects.get(scope);
    if (existing) {
      return existing;
    }

    const subject = new BehaviorSubject<ScopeLoadingState>({
      scope,
      progress: 0,
      activeTasks: 0,
      registeredTasks: 0,
      updatedAt: null,
      lastError: '',
      loading: false,
      statusText: 'Đang chờ dữ liệu màn hình',
    });

    this.scopeSubjects.set(scope, subject);
    return subject;
  }

  private emitGlobal(): void {
    const totalTasks = this.registeredKeys.size;
    const completedTasks = this.initiallyLoadedKeys.size;
    const activeTasks = Array.from(this.scopeTrackers.values()).reduce((sum, tracker) => sum + tracker.activeKeys.size, 0);
    const bootstrapping = totalTasks > 0 && completedTasks < totalTasks;
    const progress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

    let statusText = 'Đang chờ dữ liệu hệ thống';
    if (bootstrapping) {
      statusText = `Đang tải dữ liệu toàn hệ thống ${progress}%`;
    } else if (activeTasks > 0) {
      statusText = 'Đang cập nhật nền';
    } else if (completedTasks > 0) {
      statusText = 'Dữ liệu hệ thống đã sẵn sàng';
    }

    this.globalSubject.next({
      progress,
      totalTasks,
      completedTasks,
      activeTasks,
      bootstrapping,
      statusText,
    });
  }

  private emitScope(scope: string): void {
    const tracker = this.ensureScope(scope);
    const startedCount = tracker.startedInCycle.size;
    const completedCount = tracker.completedInCycle.size;
    const progress = startedCount > 0 ? Math.round((completedCount / startedCount) * 100) : tracker.updatedAt ? 100 : 0;
    const loading = tracker.activeKeys.size > 0;
    const updatedLabel = tracker.updatedAt ? `Đã cập nhật ${this.formatTime(tracker.updatedAt)}` : 'Đang chờ dữ liệu màn hình';

    let statusText = updatedLabel;
    if (loading) {
      statusText = tracker.lastReason === 'interval'
        ? `Đang cập nhật nền ${progress}%`
        : `Đang tải dữ liệu màn hình ${progress}%`;
    } else if (tracker.lastError) {
      statusText = 'Có lỗi khi tải dữ liệu';
    }

    this.ensureScopeSubject(scope).next({
      scope,
      progress,
      activeTasks: tracker.activeKeys.size,
      registeredTasks: tracker.registeredKeys.size,
      updatedAt: tracker.updatedAt,
      lastError: tracker.lastError,
      loading,
      statusText,
    });
  }

  private formatTime(iso: string): string {
    return new Intl.DateTimeFormat('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(new Date(iso));
  }
}
