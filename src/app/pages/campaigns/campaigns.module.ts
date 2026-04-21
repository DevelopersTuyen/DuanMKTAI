import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { IonicModule } from '@ionic/angular';

import { CampaignsPageRoutingModule } from './campaigns-routing.module';

import { CampaignsPage } from './campaigns.page';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    CampaignsPageRoutingModule
  ],
  declarations: [CampaignsPage]
})
export class CampaignsPageModule {}
