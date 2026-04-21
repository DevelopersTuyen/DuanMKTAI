import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SchedulerPage } from './scheduler.page';

describe('SchedulerPage', () => {
  let component: SchedulerPage;
  let fixture: ComponentFixture<SchedulerPage>;

  beforeEach(() => {
    fixture = TestBed.createComponent(SchedulerPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
