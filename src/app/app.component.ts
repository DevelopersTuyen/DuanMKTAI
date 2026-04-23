import { Component, OnDestroy, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';

import {
  GlobalLoadingState,
  LoadingOrchestratorService,
  ScopeLoadingState,
} from './core/services/loading-orchestrator.service';

interface AppNavItem {
  title: string;
  url: string;
  icon: string;
  note: string;
}

@Component({
  selector: 'app-root',
  templateUrl: 'app.component.html',
  styleUrls: ['app.component.scss'],
  standalone: false,
})
export class AppComponent implements OnDestroy {
  private readonly router = inject(Router);
  private readonly loadingOrchestrator = inject(LoadingOrchestratorService);
  private readonly collapseStorageKey = 'mktai_menu_collapsed';
  private pageLoadingSubscription?: Subscription;

  readonly appPages: AppNavItem[] = [
    { title: 'Tổng quan', url: '/dashboard', icon: 'grid-outline', note: 'KPI và tín hiệu chính' },
    { title: 'Đồng bộ dữ liệu', url: '/data-sync', icon: 'sync-outline', note: 'Website, social, Google Sheet' },
    { title: 'Phân tích', url: '/analytics', icon: 'bar-chart-outline', note: 'Hiệu suất và nội dung nổi bật' },
    { title: 'Xưởng nội dung', url: '/content-studio', icon: 'sparkles-outline', note: 'AI viết bài và sinh ảnh' },
    { title: 'Lên lịch', url: '/scheduler', icon: 'calendar-outline', note: 'Khung đăng và vận hành' },
    { title: 'Chiến dịch', url: '/campaigns', icon: 'rocket-outline', note: 'Theo dõi mục tiêu chiến dịch' },
    { title: 'Thông tin SEO', url: '/seo-insights', icon: 'search-outline', note: 'Từ khóa, CTR, thứ hạng' },
    { title: 'Tích hợp', url: '/integrations', icon: 'layers-outline', note: 'OAuth và kết nối nền tảng' },
    { title: 'Báo cáo', url: '/reports', icon: 'document-text-outline', note: 'Báo cáo ngày và lịch sử' },
    { title: 'Cài đặt', url: '/settings', icon: 'settings-outline', note: 'Cấu hình runtime hệ thống' },
    { title: 'Hướng dẫn sử dụng', url: '/guide', icon: 'help-circle-outline', note: 'Mô tả chi tiết từng chức năng' },
  ];

  currentTitle = 'Tổng quan';
  currentPath = '/dashboard';
  currentNote = 'KPI và tín hiệu chính';
  menuCollapsed = false;
  globalLoading: GlobalLoadingState = {
    progress: 0,
    totalTasks: 0,
    completedTasks: 0,
    activeTasks: 0,
    bootstrapping: false,
    statusText: 'Đang chờ khởi tạo dữ liệu hệ thống',
  };
  pageLoading: ScopeLoadingState = {
    scope: 'dashboard',
    progress: 0,
    activeTasks: 0,
    registeredTasks: 0,
    updatedAt: null,
    lastError: '',
    loading: false,
    statusText: 'Đang chờ dữ liệu màn hình',
  };

  constructor() {
    this.menuCollapsed = localStorage.getItem(this.collapseStorageKey) === 'true';
    this.updateRouteState(this.router.url);

    this.loadingOrchestrator.globalState$.subscribe((state) => {
      this.globalLoading = state;
    });

    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => this.updateRouteState(event.urlAfterRedirects));
  }

  ngOnDestroy(): void {
    this.pageLoadingSubscription?.unsubscribe();
  }

  isActive(url: string): boolean {
    return this.currentPath === url;
  }

  toggleMenuCollapsed(): void {
    this.menuCollapsed = !this.menuCollapsed;
    localStorage.setItem(this.collapseStorageKey, String(this.menuCollapsed));
  }

  private updateRouteState(url: string): void {
    const matchedPage = this.appPages.find((page) => url.startsWith(page.url));
    this.currentTitle = matchedPage?.title ?? 'Marketing AI Hub';
    this.currentPath = matchedPage?.url ?? '/dashboard';
    this.currentNote = matchedPage?.note ?? 'Điều phối dữ liệu marketing tập trung';
    this.bindPageLoading(this.resolveScopeFromRoute(this.currentPath));
  }

  private bindPageLoading(scope: string): void {
    this.pageLoadingSubscription?.unsubscribe();
    this.pageLoadingSubscription = this.loadingOrchestrator.scopeState$(scope).subscribe((state) => {
      this.pageLoading = state;
    });
  }

  private resolveScopeFromRoute(path: string): string {
    return path.replace(/^\//, '').split('/')[0] || 'dashboard';
  }
}
