import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { ContentStudioPage } from './content-studio.page';

const routes: Routes = [
  {
    path: '',
    component: ContentStudioPage
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class ContentStudioPageRoutingModule {}
