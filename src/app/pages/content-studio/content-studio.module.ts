import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { IonicModule } from '@ionic/angular';

import { ContentStudioPageRoutingModule } from './content-studio-routing.module';

import { ContentStudioPage } from './content-studio.page';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    ContentStudioPageRoutingModule
  ],
  declarations: [ContentStudioPage]
})
export class ContentStudioPageModule {}
