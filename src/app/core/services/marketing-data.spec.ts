import { TestBed } from '@angular/core/testing';

import { MarketingData } from './marketing-data';

describe('MarketingData', () => {
  let service: MarketingData;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(MarketingData);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
