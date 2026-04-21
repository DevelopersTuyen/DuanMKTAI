import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { SeoInsightsPage } from './seo-insights.page';

const routes: Routes = [
  {
    path: '',
    component: SeoInsightsPage
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class SeoInsightsPageRoutingModule {}
