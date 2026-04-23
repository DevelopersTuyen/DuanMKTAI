import { Component, DestroyRef, OnDestroy, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, switchMap, timer } from 'rxjs';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import {
  AiQueueStatusResponse,
  ContentDraft,
  ContentDraftGenerationStatusResponse,
  ContentIdea,
  ImageProviderStatusResponse,
  MarketingData,
} from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

@Component({
  selector: 'app-content-studio',
  templateUrl: './content-studio.page.html',
  styleUrls: ['./content-studio.page.scss'],
  standalone: false,
})
export class ContentStudioPage implements OnInit, OnDestroy {
  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly generationStorageKey = 'marketing_ai_active_generation_job';
  private generationPollingSubscription?: Subscription;

  ideas: ContentIdea[] = [];
  drafts: ContentDraft[] = [];
  activeDraft: ContentDraft | null = null;
  currentGenerationJob: ContentDraftGenerationStatusResponse | null = null;
  aiQueueStatus: AiQueueStatusResponse | null = null;
  imageProviderStatus: ImageProviderStatusResponse | null = null;

  prompt = {
    platform: 'Website / Blog',
    goal: 'Viết bài chuẩn SEO bám sát brief',
    tone: 'Rõ ràng, giàu hình ảnh, tự nhiên',
    brief: '',
  };

  generatedCopy = 'Bài viết SEO hoàn chỉnh sẽ hiển thị ở đây sau khi pipeline chạy xong.';
  generationMessage = '';
  generationError = '';
  confirmMessage = '';
  confirmError = '';
  deleteMessage = '';
  deleteError = '';
  isGenerating = false;
  isConfirming = false;
  deletingDraftId = '';
  isDraftLoading = true;
  isIdeaLoading = true;
  isSystemLoading = true;
  draftsError = '';
  ideasError = '';
  utilityMessage = '';
  utilityError = '';

  readonly draftPageSize = 6;
  draftPage = 1;
  readonly ideaPageSize = 4;
  ideaPage = 1;

  ngOnInit(): void {
    this.backgroundRefresh.watch('content:ideas', () => this.marketingData.getContent())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.ideas = state.data.ideas;
          this.ideasError = '';
        } else if (state.error && !this.ideas.length) {
          this.ideasError = state.error || 'Không thể tải danh sách gợi ý nội dung.';
        }

        this.isIdeaLoading = state.loading && !state.data;
      });

    this.backgroundRefresh.watch('content:drafts', () => this.marketingData.getContentDrafts())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.drafts = state.data.drafts;
          const activeDraftId = this.activeDraft?.draftId;
          const refreshedActiveDraft = activeDraftId
            ? this.drafts.find((draft) => draft.draftId === activeDraftId)
            : undefined;

          if (refreshedActiveDraft) {
            this.selectDraft(refreshedActiveDraft);
          } else if (this.drafts.length > 0) {
            this.selectDraft(this.drafts[0]);
          } else {
            this.activeDraft = null;
            this.generatedCopy = 'Bài viết SEO hoàn chỉnh sẽ hiển thị ở đây sau khi pipeline chạy xong.';
          }

          if (this.draftPage > this.totalDraftPages) {
            this.draftPage = this.totalDraftPages;
          }
          this.draftsError = '';
        } else if (state.error && !this.drafts.length) {
          this.draftsError = state.error || 'Không thể đọc lịch sử draft từ backend.';
        }

        this.isDraftLoading = state.loading && !state.data;
      });

    this.backgroundRefresh.watch('content:queue', () => this.marketingData.getAiQueueStatus())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.aiQueueStatus = state.data;
        }
        this.updateSystemLoading();
      });

    this.backgroundRefresh.watch('content:image-provider', () => this.marketingData.getImageProviderStatus())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.imageProviderStatus = state.data;
        }
        this.updateSystemLoading();
      });

    this.resumeGenerationJob();
  }

  ngOnDestroy(): void {
    this.generationPollingSubscription?.unsubscribe();
  }

  get totalDraftPages(): number {
    return Math.max(1, Math.ceil(this.drafts.length / this.draftPageSize));
  }

  get pagedDrafts(): ContentDraft[] {
    const start = (this.draftPage - 1) * this.draftPageSize;
    return this.drafts.slice(start, start + this.draftPageSize);
  }

  get totalIdeaPages(): number {
    return Math.max(1, Math.ceil(this.ideas.length / this.ideaPageSize));
  }

  get pagedIdeas(): ContentIdea[] {
    const start = (this.ideaPage - 1) * this.ideaPageSize;
    return this.ideas.slice(start, start + this.ideaPageSize);
  }

  generateContent(): void {
    const normalizedBrief = this.prompt.brief.trim();
    if (!normalizedBrief) {
      this.generationError = 'Cần nhập mô tả yêu cầu hoặc chủ đề bài viết.';
      return;
    }

    this.isGenerating = true;
    this.generationMessage = '';
    this.generationError = '';
    this.confirmMessage = '';
    this.confirmError = '';
    this.deleteMessage = '';
    this.deleteError = '';

    this.marketingData
      .generateContentDraft({
        platform: this.prompt.platform.trim() || 'Website / Blog',
        goal: this.prompt.goal.trim() || 'Viết bài chuẩn SEO bám sát brief',
        tone: this.prompt.tone.trim() || 'Rõ ràng, giàu hình ảnh, tự nhiên',
        brief: normalizedBrief,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.generationMessage = response.message;
          this.isGenerating = true;
          this.currentGenerationJob = response.job;
          this.startGenerationJobPolling(response.job.jobId);
          this.backgroundRefresh.refreshMany(['content:queue', 'content:image-provider']);
        },
        error: (error) => {
          this.generationError = error?.error?.detail || 'Không thể tạo pipeline bài viết bằng AI local.';
          this.isGenerating = false;
          this.backgroundRefresh.refreshMany(['content:queue', 'content:image-provider']);
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
    this.deleteMessage = '';
    this.deleteError = '';

    this.marketingData
      .confirmContentDraft(this.activeDraft.draftId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.activeDraft = response.draft;
          this.generatedCopy = response.draft.generatedContent;
          this.confirmMessage = response.message;
          this.isConfirming = false;
          this.backgroundRefresh.refresh('content:drafts');
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

  clearPrompt(): void {
    this.prompt = {
      platform: 'Website / Blog',
      goal: 'Viết bài chuẩn SEO bám sát brief',
      tone: 'Rõ ràng, giàu hình ảnh, tự nhiên',
      brief: '',
    };
    this.setUtilityMessage('Đã xóa nhanh biểu mẫu tạo draft.');
  }

  useActiveDraftAsPrompt(): void {
    if (!this.activeDraft) {
      this.setUtilityError('Chưa có draft đang chọn để nạp lại vào biểu mẫu.');
      return;
    }

    this.prompt = {
      platform: this.activeDraft.requestedPlatforms || 'Website / Blog',
      goal: this.activeDraft.goal || 'Viết bài chuẩn SEO bám sát brief',
      tone: this.activeDraft.tone || 'Rõ ràng, giàu hình ảnh, tự nhiên',
      brief: this.activeDraft.brief || '',
    };
    this.setUtilityMessage('Đã nạp lại dữ liệu draft vào biểu mẫu.');
  }

  async copyGeneratedArticle(): Promise<void> {
    const copied = await this.uiActions.copyText(this.activeDraft?.generatedContent || '');
    if (copied) {
      this.setUtilityMessage('Đã sao chép bài viết hoàn chỉnh.');
      return;
    }

    this.setUtilityError('Chưa có bài viết hoàn chỉnh để sao chép.');
  }

  downloadGeneratedArticle(): void {
    const filename = `bai-viet-ai-${this.activeDraft?.draftId || 'draft'}.txt`;
    const ok = this.uiActions.downloadText(filename, this.activeDraft?.generatedContent || '');
    if (ok) {
      this.setUtilityMessage('Đã tải xuống bài viết hoàn chỉnh.');
      return;
    }

    this.setUtilityError('Chưa có bài viết hoàn chỉnh để tải xuống.');
  }

  downloadMarkdown(): void {
    const filename = `${this.activeDraft?.draftId || 'pipeline'}.md`;
    const ok = this.uiActions.downloadText(filename, this.activeDraft?.markdownContent || '', 'text/markdown;charset=utf-8');
    if (ok) {
      this.setUtilityMessage('Đã tải xuống Markdown pipeline.');
      return;
    }

    this.setUtilityError('Chưa có Markdown pipeline để tải xuống.');
  }

  async copyImagePrompt(slotId: string): Promise<void> {
    const asset = this.activeDraft?.generatedImages?.find((item) => item.slotId === slotId);
    const copied = await this.uiActions.copyText(asset?.prompt || '');
    if (copied) {
      this.setUtilityMessage(`Đã sao chép prompt ảnh ${slotId}.`);
      return;
    }

    this.setUtilityError('Chưa có prompt ảnh để sao chép.');
  }

  selectDraft(draft: ContentDraft): void {
    this.activeDraft = draft;
    this.generatedCopy = draft.generatedContent;
    this.generationMessage = '';
    this.generationError = '';
    this.confirmMessage = '';
    this.confirmError = '';
  }

  goToDraftPage(page: number): void {
    this.draftPage = Math.min(this.totalDraftPages, Math.max(1, page));
  }

  goToIdeaPage(page: number): void {
    this.ideaPage = Math.min(this.totalIdeaPages, Math.max(1, page));
  }

  loadDrafts(): void {
    this.backgroundRefresh.refresh('content:drafts');
  }

  loadQueueStatus(): void {
    this.backgroundRefresh.refresh('content:queue');
  }

  loadImageProviderStatus(): void {
    this.backgroundRefresh.refresh('content:image-provider');
  }

  deleteDraft(draft: ContentDraft, event?: Event): void {
    event?.stopPropagation();

    const confirmed = window.confirm(`Xóa draft ${draft.draftId} khỏi Google Sheet?`);
    if (!confirmed) {
      return;
    }

    this.deletingDraftId = draft.draftId;
    this.deleteMessage = '';
    this.deleteError = '';
    this.confirmMessage = '';
    this.confirmError = '';

    this.marketingData.deleteContentDraft(draft.draftId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.drafts = this.drafts.filter((item) => item.draftId !== draft.draftId);
          if (this.activeDraft?.draftId === draft.draftId) {
            this.activeDraft = null;
            this.generatedCopy = 'Bài viết SEO hoàn chỉnh sẽ hiển thị ở đây sau khi pipeline chạy xong.';
          }
          this.deleteMessage = response.message;
          this.deletingDraftId = '';
          this.backgroundRefresh.refresh('content:drafts');
        },
        error: (error) => {
          this.deleteError = error?.error?.detail || 'Không thể xóa bản nháp khỏi Google Sheet.';
          this.deletingDraftId = '';
        },
      });
  }

  isDeletingDraft(draftId: string): boolean {
    return this.deletingDraftId === draftId;
  }

  countReadyImages(draft: ContentDraft | null): number {
    return draft?.generatedImages?.filter((item) => item.status === 'ready').length ?? 0;
  }

  countImageSlots(draft: ContentDraft | null): number {
    return draft?.generatedImages?.length ?? 0;
  }

  providerStatusLabel(): string {
    if (!this.imageProviderStatus) {
      return 'Chưa xác định';
    }
    return this.imageProviderStatus.ready ? 'Đang bật' : 'Chưa sẵn sàng';
  }

  providerToneClass(): string {
    if (!this.imageProviderStatus) {
      return 'status-neutral';
    }
    return this.imageProviderStatus.ready ? 'status-online' : 'status-offline';
  }

  queueJobLabel(): string {
    return this.aiQueueStatus?.currentJob || 'Không có';
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

  generationProgressPercent(): number {
    return this.currentGenerationJob?.progress ?? 0;
  }

  private resumeGenerationJob(): void {
    const jobId = localStorage.getItem(this.generationStorageKey);
    if (!jobId) {
      return;
    }

    this.currentGenerationJob = {
      jobId,
      status: 'queued',
      progress: 0,
      currentStep: 'queued',
      stepLabel: 'Đang nối lại tiến độ',
      message: 'Đang kiểm tra lại job tạo bài viết từ backend.',
      startedAt: '',
      updatedAt: '',
      completedAt: null,
      error: null,
      draft: null,
    };
    this.isGenerating = true;
    this.startGenerationJobPolling(jobId);
  }

  private startGenerationJobPolling(jobId: string): void {
    localStorage.setItem(this.generationStorageKey, jobId);
    this.generationPollingSubscription?.unsubscribe();
    this.generationPollingSubscription = timer(0, 2000)
      .pipe(
        switchMap(() => this.marketingData.getContentDraftGenerationStatus(jobId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (job) => {
          this.currentGenerationJob = job;
          this.generationMessage = job.message;
          this.isGenerating = job.status === 'queued' || job.status === 'running';

          if (job.status === 'completed' && job.draft) {
            this.activeDraft = job.draft;
            this.generatedCopy = job.draft.generatedContent;
            this.finishGenerationTracking();
            this.backgroundRefresh.refreshMany(['content:drafts', 'content:queue', 'content:image-provider']);
          } else if (job.status === 'error') {
            this.generationError = job.error || job.message || 'Tạo bài viết thất bại.';
            this.finishGenerationTracking();
            this.backgroundRefresh.refreshMany(['content:queue', 'content:image-provider']);
          }
        },
        error: (error) => {
          this.generationError = error?.error?.detail || 'Không thể theo dõi tiến độ tạo bài viết.';
          this.finishGenerationTracking();
        },
      });
  }

  private finishGenerationTracking(): void {
    this.isGenerating = false;
    localStorage.removeItem(this.generationStorageKey);
    this.generationPollingSubscription?.unsubscribe();
    this.generationPollingSubscription = undefined;
  }

  private updateSystemLoading(): void {
    this.isSystemLoading = this.aiQueueStatus === null && this.imageProviderStatus === null;
  }

  private setUtilityMessage(message: string): void {
    this.utilityMessage = message;
    this.utilityError = '';
  }

  private setUtilityError(message: string): void {
    this.utilityError = message;
    this.utilityMessage = '';
  }
}
