import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { IonicModule } from '@ionic/angular';

import { DataSyncPageRoutingModule } from './data-sync-routing.module';

import { DataSyncPage } from './data-sync.page';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    DataSyncPageRoutingModule
  ],
  declarations: [DataSyncPage]
})
export class DataSyncPageModule {}
