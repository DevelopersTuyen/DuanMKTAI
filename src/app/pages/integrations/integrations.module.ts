import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { IonicModule } from '@ionic/angular';

import { IntegrationsPageRoutingModule } from './integrations-routing.module';

import { IntegrationsPage } from './integrations.page';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    IntegrationsPageRoutingModule
  ],
  declarations: [IntegrationsPage]
})
export class IntegrationsPageModule {}
