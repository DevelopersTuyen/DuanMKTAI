import { ComponentFixture, TestBed } from '@angular/core/testing';
import { IntegrationsPage } from './integrations.page';

describe('IntegrationsPage', () => {
  let component: IntegrationsPage;
  let fixture: ComponentFixture<IntegrationsPage>;

  beforeEach(() => {
    fixture = TestBed.createComponent(IntegrationsPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
