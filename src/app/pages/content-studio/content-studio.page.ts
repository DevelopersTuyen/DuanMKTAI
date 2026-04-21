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
    goal: 'Tang lead chat luong',
    tone: 'Tu tin, practical, data-driven',
    brief: 'Chien dich nham toi doanh nghiep can dashboard tong hop social, SEO va AI content.',
  };

  generatedCopy = 'Noi dung sinh boi Ollama se hien o day sau khi bam Generate.';
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
        this.generationError = 'Khong the ket noi Ollama. Da fallback sang mau noi dung offline.';
        this.isGenerating = false;
      },
    });
  }

  applyIdea(idea: ContentIdea): void {
    this.prompt = {
      platform: idea.channel,
      goal: 'Tang engagement va lead intent',
      tone: 'Sac net, huu ich, mang tinh huong dan',
      brief: `${idea.title}. Angle: ${idea.angle}.`,
    };
  }

  ngOnDestroy(): void {
    this.generationSubscription?.unsubscribe();
  }

}
