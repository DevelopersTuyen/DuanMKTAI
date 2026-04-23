import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import {
  MarketingData,
  ScheduleItem,
  ScheduleRule,
  SchedulerResponse,
  SchedulerUpdateRequest,
} from '../../core/services/marketing-data';

type RepeatType = 'none' | 'daily' | 'weekly' | 'monthly';
type PublishMode = 'manual' | 'auto';

@Component({
  selector: 'app-scheduler',
  templateUrl: './scheduler.page.html',
  styleUrls: ['./scheduler.page.scss'],
  standalone: false,
})
export class SchedulerPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  readonly weekdayOptions = [
    { label: 'CN', value: 0 },
    { label: 'T2', value: 1 },
    { label: 'T3', value: 2 },
    { label: 'T4', value: 3 },
    { label: 'T5', value: 4 },
    { label: 'T6', value: 5 },
    { label: 'T7', value: 6 },
  ];

  readonly channelOptions = ['Facebook', 'LinkedIn', 'TikTok', 'YouTube', 'WordPress'];

  isLoading = true;
  isSaving = false;
  saveMessage = '';
  saveError = '';

  mode: PublishMode = 'manual';
  timezone = 'Asia/Saigon';
  queue: ScheduleItem[] = [];
  schedules: ScheduleRule[] = [];
  editingRuleId: string | null = null;

  ruleForm: ScheduleRule = this.createEmptyRule();

  ngOnInit(): void {
    this.loadScheduler();
  }

  loadScheduler(): void {
    this.isLoading = true;
    this.marketingData
      .getScheduler()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.applySchedulerResponse(response);
          this.isLoading = false;
        },
        error: () => {
          this.saveError = 'Không tải được cấu hình lên lịch.';
          this.isLoading = false;
        },
      });
  }

  applySchedulerResponse(response: SchedulerResponse): void {
    this.mode = response.mode;
    this.timezone = response.timezone;
    this.queue = response.queue;
    this.schedules = response.schedules.map((rule) => ({
      ...rule,
      daysOfWeek: [...rule.daysOfWeek],
      note: rule.note ?? null,
    }));
    this.resetRuleForm();
  }

  createEmptyRule(): ScheduleRule {
    return {
      id: '',
      title: '',
      channel: 'WordPress',
      publishMode: 'manual',
      startAt: this.buildDefaultStartAt(),
      repeatType: 'none',
      repeatInterval: 1,
      daysOfWeek: [],
      active: true,
      note: null,
    };
  }

  buildDefaultStartAt(): string {
    const current = new Date();
    current.setMinutes(current.getMinutes() + 30);
    current.setSeconds(0, 0);
    const localTime = new Date(current.getTime() - current.getTimezoneOffset() * 60000);
    return localTime.toISOString().slice(0, 16);
  }

  resetRuleForm(): void {
    this.editingRuleId = null;
    this.ruleForm = this.createEmptyRule();
  }

  editRule(rule: ScheduleRule): void {
    this.editingRuleId = rule.id;
    this.ruleForm = {
      ...rule,
      daysOfWeek: [...rule.daysOfWeek],
      note: rule.note ?? null,
    };
  }

  removeRule(ruleId: string): void {
    this.schedules = this.schedules.filter((item) => item.id !== ruleId);
    if (this.editingRuleId === ruleId) {
      this.resetRuleForm();
    }
  }

  toggleWeekday(day: number): void {
    const exists = this.ruleForm.daysOfWeek.includes(day);
    this.ruleForm.daysOfWeek = exists
      ? this.ruleForm.daysOfWeek.filter((value) => value !== day)
      : [...this.ruleForm.daysOfWeek, day].sort((left, right) => left - right);
  }

  isWeekdaySelected(day: number): boolean {
    return this.ruleForm.daysOfWeek.includes(day);
  }

  onRepeatTypeChange(repeatType: RepeatType): void {
    this.ruleForm.repeatType = repeatType;
    if (repeatType !== 'weekly') {
      this.ruleForm.daysOfWeek = [];
    }
    if (repeatType === 'none') {
      this.ruleForm.repeatInterval = 1;
    }
  }

  saveRuleDraft(): void {
    this.saveError = '';
    this.saveMessage = '';

    const normalizedTitle = this.ruleForm.title.trim();
    if (!normalizedTitle) {
      this.saveError = 'Cần nhập tên nội dung hoặc chiến dịch cần lên lịch.';
      return;
    }
    if (!this.ruleForm.startAt) {
      this.saveError = 'Cần chọn ngày giờ đăng.';
      return;
    }
    if (this.ruleForm.repeatType === 'weekly' && this.ruleForm.daysOfWeek.length === 0) {
      this.saveError = 'Lịch lặp hàng tuần cần chọn ít nhất một ngày trong tuần.';
      return;
    }

    const normalizedRule: ScheduleRule = {
      ...this.ruleForm,
      id: this.ruleForm.id || this.generateRuleId(),
      title: normalizedTitle,
      channel: this.ruleForm.channel,
      publishMode: this.ruleForm.publishMode,
      startAt: this.ruleForm.startAt,
      repeatType: this.ruleForm.repeatType,
      repeatInterval: Math.max(1, Number(this.ruleForm.repeatInterval) || 1),
      daysOfWeek: [...this.ruleForm.daysOfWeek].sort((left, right) => left - right),
      active: this.ruleForm.active,
      note: this.ruleForm.note?.trim() || null,
    };

    const currentIndex = this.schedules.findIndex((item) => item.id === normalizedRule.id);
    if (currentIndex >= 0) {
      this.schedules = this.schedules.map((item, index) => (index === currentIndex ? normalizedRule : item));
    } else {
      this.schedules = [...this.schedules, normalizedRule];
    }

    this.resetRuleForm();
  }

  generateRuleId(): string {
    return `schedule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  persistScheduler(): void {
    this.isSaving = true;
    this.saveError = '';
    this.saveMessage = '';

    const payload: SchedulerUpdateRequest = {
      mode: this.mode,
      timezone: this.timezone.trim() || 'Asia/Saigon',
      schedules: this.schedules,
    };

    this.marketingData
      .saveScheduler(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.applySchedulerResponse(response.scheduler);
          this.saveMessage = response.message;
          this.isSaving = false;
        },
        error: () => {
          this.saveError = 'Không lưu được cấu hình lên lịch.';
          this.isSaving = false;
        },
      });
  }

  trackRule(_: number, rule: ScheduleRule): string {
    return rule.id;
  }
}
