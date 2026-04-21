import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { DataSyncPage } from './data-sync.page';

const routes: Routes = [
  {
    path: '',
    component: DataSyncPage
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class DataSyncPageRoutingModule {}
