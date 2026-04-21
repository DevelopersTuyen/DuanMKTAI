import { AfterViewInit, Component, DestroyRef, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

import { ChannelShare, DashboardKpi, MarketingData, Recommendation, SyncChannel, TrendPoint } from '../../core/services/marketing-data';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.page.html',
  styleUrls: ['./dashboard.page.scss'],
  standalone: false,
})
export class DashboardPage implements AfterViewInit, OnDestroy, OnInit {
  private readonly marketingData = inject(MarketingData);
  private readonly destroyRef = inject(DestroyRef);

  @ViewChild('performanceChart') performanceChart?: ElementRef<HTMLCanvasElement>;
  @ViewChild('distributionChart') distributionChart?: ElementRef<HTMLCanvasElement>;

  kpis: DashboardKpi[] = [];
  channelBreakdown: ChannelShare[] = [];
  performanceTrend: TrendPoint[] = [];
  syncChannels: SyncChannel[] = [];
  recommendations: Recommendation[] = [];

  private performanceChartRef?: Chart<'line'>;
  private distributionChartRef?: Chart<'doughnut'>;
  private viewReady = false;

  ngOnInit(): void {
    this.marketingData.getDashboard()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((response) => {
        this.kpis = response.kpis;
        this.channelBreakdown = response.channelBreakdown;
        this.performanceTrend = response.performanceTrend;
        this.syncChannels = response.syncChannels;
        this.recommendations = response.recommendations;
        this.renderCharts();
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

  private renderCharts(): void {
    if (!this.viewReady || !this.performanceTrend.length || !this.channelBreakdown.length) {
      return;
    }

    this.performanceChartRef?.destroy();
    this.distributionChartRef?.destroy();
    this.buildPerformanceChart();
    this.buildDistributionChart();
  }

  private buildPerformanceChart(): void {
    const element = this.performanceChart?.nativeElement;
    if (!element) {
      return;
    }

    const config: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels: this.performanceTrend.map((item) => item.label),
        datasets: [
          {
            label: 'Organic + social traffic (K)',
            data: this.performanceTrend.map((item) => item.value),
            borderColor: '#c46f15',
            backgroundColor: 'rgba(196, 111, 21, 0.18)',
            borderWidth: 3,
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
          },
          y: {
            grid: {
              color: 'rgba(148, 163, 184, 0.15)',
            },
          },
        },
      },
    };

    this.performanceChartRef = new Chart(element, config);
  }

  private buildDistributionChart(): void {
    const element = this.distributionChart?.nativeElement;
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
          legend: {
            display: false,
          },
        },
        cutout: '72%',
      },
    };

    this.distributionChartRef = new Chart(element, config);
  }
}
