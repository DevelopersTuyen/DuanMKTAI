import { NgModule } from '@angular/core';
import { PreloadAllModules, RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: 'home',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadChildren: () => import('./pages/dashboard/dashboard.module').then( m => m.DashboardPageModule)
  },
  {
    path: 'data-sync',
    loadChildren: () => import('./pages/data-sync/data-sync.module').then( m => m.DataSyncPageModule)
  },
  {
    path: 'analytics',
    loadChildren: () => import('./pages/analytics/analytics.module').then( m => m.AnalyticsPageModule)
  },
  {
    path: 'content-studio',
    loadChildren: () => import('./pages/content-studio/content-studio.module').then( m => m.ContentStudioPageModule)
  },
  {
    path: 'scheduler',
    loadChildren: () => import('./pages/scheduler/scheduler.module').then( m => m.SchedulerPageModule)
  },
  {
    path: 'integrations',
    loadChildren: () => import('./pages/integrations/integrations.module').then( m => m.IntegrationsPageModule)
  },
  {
    path: 'reports',
    loadChildren: () => import('./pages/reports/reports.module').then( m => m.ReportsPageModule)
  },
  {
    path: 'campaigns',
    loadChildren: () => import('./pages/campaigns/campaigns.module').then( m => m.CampaignsPageModule)
  },
  {
    path: 'seo-insights',
    loadChildren: () => import('./pages/seo-insights/seo-insights.module').then( m => m.SeoInsightsPageModule)
  },
  {
    path: 'settings',
    loadChildren: () => import('./pages/settings/settings.module').then( m => m.SettingsPageModule)
  },
  {
    path: '**',
    redirectTo: 'dashboard'
  },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, { preloadingStrategy: PreloadAllModules })
  ],
  exports: [RouterModule]
})
export class AppRoutingModule { }
