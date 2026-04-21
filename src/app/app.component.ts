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
    { title: 'Dashboard', url: '/dashboard', icon: 'grid-outline', note: 'Toan canh KPI' },
    { title: 'Data Sync', url: '/data-sync', icon: 'sync-outline', note: 'Social va Sheets' },
    { title: 'Analytics', url: '/analytics', icon: 'bar-chart-outline', note: 'CTR va engagement' },
    { title: 'Content Studio', url: '/content-studio', icon: 'sparkles-outline', note: 'AI copy va visual' },
    { title: 'Scheduler', url: '/scheduler', icon: 'calendar-outline', note: 'Lich dang bai' },
    { title: 'Campaigns', url: '/campaigns', icon: 'rocket-outline', note: 'Theo doi chien dich' },
    { title: 'SEO Insights', url: '/seo-insights', icon: 'search-outline', note: 'GSC va keyword' },
    { title: 'Integrations', url: '/integrations', icon: 'layers-outline', note: 'API va tools' },
    { title: 'Reports', url: '/reports', icon: 'document-text-outline', note: 'Bao cao tu dong' },
    { title: 'Settings', url: '/settings', icon: 'settings-outline', note: 'Ollama va cau hinh' },
  ];

  currentTitle = 'Dashboard';
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
