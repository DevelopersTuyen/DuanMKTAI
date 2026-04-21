import { Component, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

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
export class AppComponent {
  private readonly router = inject(Router);

  readonly appPages: AppNavItem[] = [
    { title: 'Tổng quan', url: '/dashboard', icon: 'grid-outline', note: 'Toàn cảnh KPI' },
    { title: 'Đồng bộ dữ liệu', url: '/data-sync', icon: 'sync-outline', note: 'Mạng xã hội và Sheet' },
    { title: 'Phân tích', url: '/analytics', icon: 'bar-chart-outline', note: 'CTR và tương tác' },
    { title: 'Xưởng nội dung', url: '/content-studio', icon: 'sparkles-outline', note: 'AI copy và hình ảnh' },
    { title: 'Lên lịch', url: '/scheduler', icon: 'calendar-outline', note: 'Lịch đăng bài' },
    { title: 'Chiến dịch', url: '/campaigns', icon: 'rocket-outline', note: 'Theo dõi chiến dịch' },
    { title: 'Thông tin SEO', url: '/seo-insights', icon: 'search-outline', note: 'GSC và từ khóa' },
    { title: 'Tích hợp', url: '/integrations', icon: 'layers-outline', note: 'API và công cụ' },
    { title: 'Báo cáo', url: '/reports', icon: 'document-text-outline', note: 'Báo cáo tự động' },
    { title: 'Cài đặt', url: '/settings', icon: 'settings-outline', note: 'Ollama và cấu hình' },
  ];

  currentTitle = 'Tổng quan';
  currentPath = '/dashboard';

  constructor() {
    this.updateRouteState(this.router.url);
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => this.updateRouteState(event.urlAfterRedirects));
  }

  isActive(url: string): boolean {
    return this.currentPath === url;
  }

  private updateRouteState(url: string): void {
    const matchedPage = this.appPages.find((page) => url.startsWith(page.url));
    this.currentTitle = matchedPage?.title ?? 'Marketing AI Hub';
    this.currentPath = matchedPage?.url ?? '/dashboard';
  }
}
