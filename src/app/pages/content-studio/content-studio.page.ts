import { Component, DestroyRef, OnDestroy, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription } from 'rxjs';

import { ContentIdea, MarketingData } from '../../core/services/marketing-data';
import { MarketingPromptRequest, Ollama } from '../../core/services/ollama';

@Component({
  selector: 'app-content-studio',
  templateUrl: './content-studio.page.html',
  styleUrls: ['./content-studio.page.scss'],
  standalone: false,
})
export class ContentStudioPage implements OnDestroy, OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly ollama = inject(Ollama);
  private readonly destroyRef = inject(DestroyRef);
  private generationSubscription?: Subscription;

  ideas: ContentIdea[] = [];

  prompt: MarketingPromptRequest = {
    platform: 'Facebook + LinkedIn',
    goal: 'Tăng lead chất lượng',
    tone: 'Tự tin, thực tế, dựa trên dữ liệu',
    brief: 'Chiến dịch nhắm tới doanh nghiệp cần bảng điều khiển tổng hợp social, SEO và nội dung AI.',
  };

  generatedCopy = 'Nội dung do Ollama tạo sẽ hiển thị ở đây sau khi bấm Tạo nội dung.';
  generationError = '';
  isGenerating = false;

  ngOnInit(): void {
    this.marketingData.getContent()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.ideas = response.ideas;
      });
  }

  generateContent(): void {
    this.isGenerating = true;
    this.generationError = '';
    this.generationSubscription?.unsubscribe();
    this.generationSubscription = this.ollama.generateMarketingCopy(this.prompt).subscribe({
      next: (response) => {
        this.generatedCopy = response;
        this.isGenerating = false;
      },
      error: () => {
        this.generationError = 'Không thể kết nối tới Ollama. Hệ thống đã chuyển sang mẫu nội dung ngoại tuyến.';
        this.isGenerating = false;
      },
    });
  }

  applyIdea(idea: ContentIdea): void {
    this.prompt = {
      platform: idea.channel,
      goal: 'Tăng tương tác và ý định chuyển đổi',
      tone: 'Sắc nét, hữu ích, mang tính hướng dẫn',
      brief: `${idea.title}. Angle: ${idea.angle}.`,
    };
  }

  ngOnDestroy(): void {
    this.generationSubscription?.unsubscribe();
  }

}
