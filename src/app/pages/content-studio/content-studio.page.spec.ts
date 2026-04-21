import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContentStudioPage } from './content-studio.page';

describe('ContentStudioPage', () => {
  let component: ContentStudioPage;
  let fixture: ComponentFixture<ContentStudioPage>;

  beforeEach(() => {
    fixture = TestBed.createComponent(ContentStudioPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
