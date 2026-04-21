import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { IonicModule } from '@ionic/angular';

import { SeoInsightsPageRoutingModule } from './seo-insights-routing.module';

import { SeoInsightsPage } from './seo-insights.page';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    SeoInsightsPageRoutingModule
  ],
  declarations: [SeoInsightsPage]
})
export class SeoInsightsPageModule {}
