import { TestBed } from '@angular/core/testing';

import { Ollama } from './ollama';

describe('Ollama', () => {
  let service: Ollama;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Ollama);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
