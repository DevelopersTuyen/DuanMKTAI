import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import {
  AiQueueStatusResponse,
  ContentDraft,
  ContentIdea,
  MarketingData,
} from '../../core/services/marketing-data';

@Component({
  selector: 'app-content-studio',
  templateUrl: './content-studio.page.html',
  styleUrls: ['./content-studio.page.scss'],
  standalone: false,
})
export class ContentStudioPage implements OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  ideas: ContentIdea[] = [];
  drafts: ContentDraft[] = [];
  activeDraft: ContentDraft | null = null;
  aiQueueStatus: AiQueueStatusResponse | null = null;

  prompt = {
    platform: 'Facebook, LinkedIn',
    goal: 'Tăng lead chất lượng',
    tone: 'Tự tin, thực tế, dựa trên dữ liệu',
    brief: 'Bài viết giới thiệu giải pháp dashboard marketing AI cho doanh nghiệp, nhấn vào hiệu quả SEO và khả năng quản trị đa kênh.',
  };

  generatedCopy = 'Bài viết SEO hoàn chỉnh sẽ hiển thị ở đây sau khi pipeline 3 bước chạy xong.';
  generationMessage = '';
  generationError = '';
  confirmMessage = '';
  confirmError = '';
  isGenerating = false;
  isConfirming = false;

  ngOnInit(): void {
    this.loadIdeas();
    this.loadDrafts();
    this.loadQueueStatus();
  }

  loadIdeas(): void {
    this.marketingData
      .getContent()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.ideas = response.ideas;
      });
  }

  loadDrafts(): void {
    this.marketingData
      .getContentDrafts()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.drafts = response.drafts;
        if (!this.activeDraft && this.drafts.length > 0) {
          this.selectDraft(this.drafts[0]);
        }
      });
  }

  loadQueueStatus(): void {
    this.marketingData
      .getAiQueueStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.aiQueueStatus = response;
        },
        error: () => {
          this.aiQueueStatus = null;
        },
      });
  }

  generateContent(): void {
    this.isGenerating = true;
    this.generationMessage = '';
    this.generationError = '';
    this.confirmMessage = '';
    this.confirmError = '';

    this.marketingData
      .generateContentDraft(this.prompt)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.activeDraft = response.draft;
          this.generatedCopy = response.draft.generatedContent;
          this.generationMessage = response.message;
          this.isGenerating = false;
          this.loadDrafts();
          this.loadQueueStatus();
        },
        error: (error) => {
          this.generationError = error?.error?.detail || 'Không thể tạo pipeline bài viết bằng AI local.';
          this.isGenerating = false;
          this.loadQueueStatus();
        },
      });
  }

  confirmDraft(): void {
    if (!this.activeDraft) {
      return;
    }

    this.isConfirming = true;
    this.confirmMessage = '';
    this.confirmError = '';

    this.marketingData
      .confirmContentDraft(this.activeDraft.draftId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.activeDraft = response.draft;
          this.generatedCopy = response.draft.generatedContent;
          this.confirmMessage = response.message;
          this.isConfirming = false;
          this.loadDrafts();
        },
        error: (error) => {
          this.confirmError = error?.error?.detail || 'Không thể xác nhận bản nháp.';
          this.isConfirming = false;
        },
      });
  }

  applyIdea(idea: ContentIdea): void {
    this.prompt = {
      platform: idea.channel,
      goal: 'Tăng tương tác và ý định chuyển đổi',
      tone: 'Sắc nét, hữu ích, mang tính hướng dẫn',
      brief: `${idea.title}. Góc triển khai: ${idea.angle}.`,
    };
  }

  selectDraft(draft: ContentDraft): void {
    this.activeDraft = draft;
    this.generatedCopy = draft.generatedContent;
    this.generationMessage = '';
    this.generationError = '';
    this.confirmMessage = '';
    this.confirmError = '';
  }

  formatDate(value: string | null): string {
    if (!value) {
      return 'Chưa có';
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleString('vi-VN');
  }
}
