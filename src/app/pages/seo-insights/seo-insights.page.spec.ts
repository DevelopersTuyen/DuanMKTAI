import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SeoInsightsPage } from './seo-insights.page';

describe('SeoInsightsPage', () => {
  let component: SeoInsightsPage;
  let fixture: ComponentFixture<SeoInsightsPage>;

  beforeEach(() => {
    fixture = TestBed.createComponent(SeoInsightsPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
