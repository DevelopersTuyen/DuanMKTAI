import { AfterViewInit, Component, DestroyRef, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

import { BackgroundSheetRefreshService } from '../../core/services/background-sheet-refresh.service';
import {
  ChannelShare,
  DashboardKpi,
  LocalAiAnalysisResponse,
  MarketingData,
  Recommendation,
  SyncChannel,
  TrendPoint,
  WebsiteSummary,
} from '../../core/services/marketing-data';
import { UiActionsService } from '../../core/services/ui-actions.service';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.page.html',
  styleUrls: ['./dashboard.page.scss'],
  standalone: false,
})
export class DashboardPage implements AfterViewInit, OnDestroy, OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly backgroundRefresh = inject(BackgroundSheetRefreshService);
  private readonly uiActions = inject(UiActionsService);
  private readonly destroyRef = inject(DestroyRef);
  private performanceCanvas?: HTMLCanvasElement;
  private distributionCanvas?: HTMLCanvasElement;

  @ViewChild('performanceChart')
  set performanceChartRefSetter(ref: ElementRef<HTMLCanvasElement> | undefined) {
    this.performanceCanvas = ref?.nativeElement;
    this.renderCharts();
  }

  @ViewChild('distributionChart')
  set distributionChartRefSetter(ref: ElementRef<HTMLCanvasElement> | undefined) {
    this.distributionCanvas = ref?.nativeElement;
    this.renderCharts();
  }

  kpis: DashboardKpi[] = [];
  channelBreakdown: ChannelShare[] = [];
  performanceTrend: TrendPoint[] = [];
  syncChannels: SyncChannel[] = [];
  recommendations: Recommendation[] = [];
  websiteSummaries: WebsiteSummary[] = [];
  localAiAnalysis?: LocalAiAnalysisResponse;

  isLoading = true;
  loadError = '';
  isAiLoading = true;
  aiAnalysisError = '';
  utilityMessage = '';
  utilityError = '';

  private performanceChartRef?: Chart<'line'>;
  private distributionChartRef?: Chart<'doughnut'>;
  private viewReady = false;

  ngOnInit(): void {
    this.backgroundRefresh.watch('dashboard:overview', () => this.marketingData.getDashboard())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.kpis = state.data.kpis;
          this.channelBreakdown = state.data.channelBreakdown;
          this.performanceTrend = state.data.performanceTrend;
          this.syncChannels = state.data.syncChannels;
          this.websiteSummaries = state.data.websiteSummaries;
          this.recommendations = state.data.recommendations;
          this.loadError = '';
          this.renderCharts();
        } else if (state.error && !this.kpis.length) {
          this.loadError = state.error || 'Không thể tải dữ liệu tổng quan từ backend.';
        }

        this.isLoading = state.loading && !state.data;
      });

    this.backgroundRefresh.watch('dashboard:local-ai', () => this.marketingData.getLocalAiAnalysis())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        if (state.data) {
          this.localAiAnalysis = state.data;
          this.aiAnalysisError = '';
        } else if (state.error && !this.localAiAnalysis) {
          this.aiAnalysisError = 'Không thể lấy bản phân tích từ AI cục bộ.';
        }

        this.isAiLoading = state.loading && !state.data;
      });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderCharts();
  }

  ngOnDestroy(): void {
    this.performanceChartRef?.destroy();
    this.distributionChartRef?.destroy();
  }

  refreshDashboard(): void {
    this.backgroundRefresh.refreshMany(['dashboard:overview', 'dashboard:local-ai']);
    this.setUtilityMessage('Đã yêu cầu làm mới dữ liệu tổng quan.');
  }

  async copyAiAnalysis(): Promise<void> {
    const text = this.localAiAnalysis?.analysis || '';
    const copied = await this.uiActions.copyText(text);
    if (copied) {
      this.setUtilityMessage('Đã sao chép bản phân tích AI.');
      return;
    }

    this.setUtilityError('Không có nội dung phân tích để sao chép.');
  }

  downloadAiAnalysis(): void {
    const analysis = this.localAiAnalysis?.analysis || '';
    const ok = this.uiActions.downloadText(
      `phan-tich-ai-${new Date().toISOString().slice(0, 10)}.txt`,
      this.buildAiAnalysisExport(analysis),
    );
    if (ok) {
      this.setUtilityMessage('Đã tải xuống bản phân tích AI.');
      return;
    }

    this.setUtilityError('Không có nội dung phân tích để tải xuống.');
  }

  async copySyncSummary(): Promise<void> {
    const summary = this.syncChannels.map((item) => (
      `${item.name}: ${item.status} | ${item.accounts} cụm | ${item.healthScore}% | ${item.lastSync}`
    )).join('\n');
    const copied = await this.uiActions.copyText(summary);
    if (copied) {
      this.setUtilityMessage('Đã sao chép tóm tắt đồng bộ.');
      return;
    }

    this.setUtilityError('Chưa có dữ liệu đồng bộ để sao chép.');
  }

  private renderCharts(): void {
    if (
      !this.viewReady
      || !this.performanceTrend.length
      || !this.channelBreakdown.length
      || !this.performanceCanvas
      || !this.distributionCanvas
    ) {
      return;
    }

    this.performanceChartRef?.destroy();
    this.distributionChartRef?.destroy();
    this.buildPerformanceChart();
    this.buildDistributionChart();
  }

  private buildPerformanceChart(): void {
    const element = this.performanceCanvas;
    if (!element) {
      return;
    }

    const config: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels: this.performanceTrend.map((item) => item.label),
        datasets: [
          {
            label: 'Phiên website 28 ngày',
            data: this.performanceTrend.map((item) => item.value),
            borderColor: '#c46f15',
            backgroundColor: 'rgba(196, 111, 21, 0.18)',
            borderWidth: 2,
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { display: false },
          },
          y: {
            grid: { color: 'rgba(148, 163, 184, 0.15)' },
          },
        },
      },
    };

    this.performanceChartRef = new Chart(element, config);
  }

  private buildDistributionChart(): void {
    const element = this.distributionCanvas;
    if (!element) {
      return;
    }

    const config: ChartConfiguration<'doughnut'> = {
      type: 'doughnut',
      data: {
        labels: this.channelBreakdown.map((item) => item.name),
        datasets: [
          {
            data: this.channelBreakdown.map((item) => item.value),
            backgroundColor: ['#c46f15', '#0f766e', '#f59e0b', '#334155', '#e2b089'],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        cutout: '72%',
      },
    };

    this.distributionChartRef = new Chart(element, config);
  }

  private buildAiAnalysisExport(analysis: string): string {
    const lines = [
      `Model: ${this.localAiAnalysis?.model || 'Chưa có'}`,
      `Nguồn: ${this.localAiAnalysis?.source || 'Chưa có'}`,
      `Tạo lúc: ${this.localAiAnalysis?.generatedAt || 'Chưa có'}`,
      '',
      analysis,
    ];

    return lines.join('\n');
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
