import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DataSyncPage } from './data-sync.page';

describe('DataSyncPage', () => {
  let component: DataSyncPage;
  let fixture: ComponentFixture<DataSyncPage>;

  beforeEach(() => {
    fixture = TestBed.createComponent(DataSyncPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
