import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { MarketingData, ScheduleItem } from '../../core/services/marketing-data';

@Component({
  selector: 'app-scheduler',
  templateUrl: './scheduler.page.html',
  styleUrls: ['./scheduler.page.scss'],
  standalone: false,
})
export class SchedulerPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  queue: ScheduleItem[] = [];

  ngOnInit(): void {
    this.marketingData.getScheduler()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.queue = response.queue;
      });
  }
}
