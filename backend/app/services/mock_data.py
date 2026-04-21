from app.models import (
    AnalyticsResponse,
    CampaignOverview,
    CampaignsResponse,
    ChannelShare,
    ContentIdea,
    ContentPerformance,
    ContentResponse,
    DashboardKpi,
    DashboardResponse,
    DataSyncResponse,
    IntegrationStatus,
    IntegrationsResponse,
    KeywordInsight,
    ManagedAccount,
    PlatformPerformance,
    Recommendation,
    ReportSnapshot,
    ReportsResponse,
    SchedulerResponse,
    ScheduleItem,
    SeoInsightsResponse,
    SettingsResponse,
    SyncChannel,
    TrendPoint,
)


def get_dashboard_data(wordpress_sites_count: int = 3) -> DashboardResponse:
    return DashboardResponse(
        kpis=[
            DashboardKpi(
                label="Tong reach 7 ngay",
                value="2.48M",
                note="Tong hop Facebook, LinkedIn, YouTube, TikTok va WordPress",
                trend="+18.4%",
                trendTone="trend-up",
            ),
            DashboardKpi(
                label="CTR trung binh",
                value="4.9%",
                note="Tang nho toi uu creative va CTA",
                trend="+0.8 pt",
                trendTone="trend-up",
            ),
            DashboardKpi(
                label="Noi dung dang cho duyet",
                value="14",
                note="Hang doi gom post, short video va landing page",
                trend="Can sap lich",
                trendTone="trend-flat",
            ),
            DashboardKpi(
                label="Keyword SEO dang giam",
                value="6",
                note="Can lam moi schema, title va internal link",
                trend="Canh bao",
                trendTone="trend-alert",
            ),
        ],
        performanceTrend=[
            TrendPoint(label="T2", value=120),
            TrendPoint(label="T3", value=146),
            TrendPoint(label="T4", value=171),
            TrendPoint(label="T5", value=168),
            TrendPoint(label="T6", value=214),
            TrendPoint(label="T7", value=238),
            TrendPoint(label="CN", value=252),
        ],
        channelBreakdown=[
            ChannelShare(name="Facebook", value=34),
            ChannelShare(name="YouTube", value=24),
            ChannelShare(name="TikTok", value=18),
            ChannelShare(name="LinkedIn", value=14),
            ChannelShare(name="WordPress", value=10),
        ],
        syncChannels=get_data_sync_data(wordpress_sites_count).syncChannels,
        recommendations=get_recommendations(),
    )


def get_recommendations() -> list[Recommendation]:
    return [
        Recommendation(
            title="Day ngan sach vao YouTube Shorts va TikTok 19:00-21:00",
            detail="Hai kenh nay dang tao view-to-click tot nhat cho nhom content how-to va social proof.",
            priority="High",
        ),
        Recommendation(
            title="Lam moi 6 bai SEO co vi tri trung binh 8-12",
            detail="Chi can toi uu title, FAQ schema va anchor link de day CTR va vi tri len top 5.",
            priority="High",
        ),
        Recommendation(
            title="Giu LinkedIn cho thought leadership, khong lay lead truc tiep",
            detail="CTR thap nhung completion rate tot, phu hop lam trust layer truoc remarketing.",
            priority="Medium",
        ),
    ]


def get_data_sync_data(wordpress_sites_count: int = 3) -> DataSyncResponse:
    return DataSyncResponse(
        syncChannels=[
            SyncChannel(
                name="Facebook Pages",
                accounts=6,
                status="Live",
                statusClass="status-live",
                lastSync="09:15",
                healthScore=96,
            ),
            SyncChannel(
                name="LinkedIn Company Pages",
                accounts=3,
                status="Live",
                statusClass="status-live",
                lastSync="09:05",
                healthScore=91,
            ),
            SyncChannel(
                name="YouTube Channels",
                accounts=2,
                status="Live",
                statusClass="status-live",
                lastSync="08:58",
                healthScore=94,
            ),
            SyncChannel(
                name="TikTok Profiles",
                accounts=4,
                status="Review",
                statusClass="status-draft",
                lastSync="08:41",
                healthScore=82,
            ),
            SyncChannel(
                name="WordPress Sites",
                accounts=wordpress_sites_count,
                status="Warning",
                statusClass="status-warning",
                lastSync="07:50",
                healthScore=74,
            ),
        ],
        accounts=[
            ManagedAccount(
                platform="Facebook",
                account="North Cluster",
                assets="3 pages / 2 ad accounts",
                destination="Google Sheets > social_overview",
            ),
            ManagedAccount(
                platform="WordPress",
                account="Brand Websites",
                assets=f"{wordpress_sites_count} sites / 1 GA4 property",
                destination="SEO + content sheets",
            ),
            ManagedAccount(
                platform="YouTube",
                account="Product Education",
                assets="2 channels / 38 playlists",
                destination="Video KPI sheet",
            ),
            ManagedAccount(
                platform="TikTok",
                account="Creator Pods",
                assets="4 profiles / 2 content buckets",
                destination="Shorts tracker",
            ),
        ],
    )


def get_analytics_data() -> AnalyticsResponse:
    return AnalyticsResponse(
        platforms=[
            PlatformPerformance(
                platform="Facebook",
                reach="820K",
                engagementRate=7.2,
                ctr=4.8,
                conversionRate=2.3,
            ),
            PlatformPerformance(
                platform="LinkedIn",
                reach="210K",
                engagementRate=5.4,
                ctr=2.6,
                conversionRate=1.9,
            ),
            PlatformPerformance(
                platform="YouTube",
                reach="540K",
                engagementRate=8.9,
                ctr=6.2,
                conversionRate=2.8,
            ),
            PlatformPerformance(
                platform="TikTok",
                reach="670K",
                engagementRate=9.3,
                ctr=4.1,
                conversionRate=1.5,
            ),
        ],
        topContents=[
            ContentPerformance(
                title="Case study automation cho B2B leadgen",
                platform="LinkedIn",
                format="Carousel",
                views="42K",
                ctr=3.8,
                engagementRate=6.1,
                statusClass="status-live",
                statusLabel="Evergreen",
            ),
            ContentPerformance(
                title="Short video 3 loi sai khi scale ads",
                platform="TikTok",
                format="Video",
                views="186K",
                ctr=4.7,
                engagementRate=10.4,
                statusClass="status-live",
                statusLabel="Winning",
            ),
            ContentPerformance(
                title="Landing page checklist 2026",
                platform="WordPress",
                format="Blog",
                views="29K",
                ctr=7.1,
                engagementRate=5.8,
                statusClass="status-draft",
                statusLabel="Refresh",
            ),
            ContentPerformance(
                title="YouTube walkthrough ve content engine",
                platform="YouTube",
                format="Long-form",
                views="73K",
                ctr=6.6,
                engagementRate=8.1,
                statusClass="status-live",
                statusLabel="Scale",
            ),
        ],
        recommendations=get_recommendations(),
    )


def get_content_data() -> ContentResponse:
    return ContentResponse(
        ideas=[
            ContentIdea(
                title="Before/after dashboard transformation",
                angle="So sanh KPI truoc va sau khi tu dong hoa",
                channel="Facebook + LinkedIn",
            ),
            ContentIdea(
                title="3 tactical SEO fixes in 60 seconds",
                angle="Micro education voi visual nhanh",
                channel="TikTok + YouTube Shorts",
            ),
            ContentIdea(
                title="CEO note on content moat",
                angle="Thought leadership cho decision maker",
                channel="LinkedIn",
            ),
            ContentIdea(
                title="Checklist marketing operations 2026",
                angle="Lead magnet + blog cluster",
                channel="WordPress",
            ),
        ]
    )


def get_scheduler_data() -> SchedulerResponse:
    return SchedulerResponse(
        queue=[
            ScheduleItem(
                asset="Video hook ve social proof",
                channel="TikTok",
                slot="Tue 19:30",
                bestWindow="19:00-21:00",
                audience="Cold reach",
            ),
            ScheduleItem(
                asset="Case study carousel",
                channel="LinkedIn",
                slot="Wed 08:15",
                bestWindow="07:30-09:00",
                audience="Decision makers",
            ),
            ScheduleItem(
                asset="Blog SEO refresh",
                channel="WordPress",
                slot="Thu 10:00",
                bestWindow="09:30-11:00",
                audience="Organic search",
            ),
            ScheduleItem(
                asset="Retargeting testimonial reel",
                channel="Facebook",
                slot="Fri 20:00",
                bestWindow="18:30-20:30",
                audience="Warm leads",
            ),
        ]
    )


def get_campaigns_data() -> CampaignsResponse:
    return CampaignsResponse(
        campaigns=[
            CampaignOverview(
                name="Spring Launch Funnel",
                objective="Lead generation",
                spend="$12.4K",
                reach="480K",
                forecast="+320 SQL if current CTR giu tren 4.5%",
                nextMove="Nhan doi budget cho 2 creative co hook du lieu",
            ),
            CampaignOverview(
                name="SEO Recovery Cluster",
                objective="Organic traffic",
                spend="$2.1K",
                reach="120K impressions",
                forecast="+18% clicks trong 30 ngay",
                nextMove="Lam moi bai co vi tri 8-12 va them FAQ schema",
            ),
            CampaignOverview(
                name="Thought Leadership Sprint",
                objective="Brand trust",
                spend="$1.5K",
                reach="76K",
                forecast="+22% follow rate tren LinkedIn",
                nextMove="Xuat ban 2 bai founder note va 1 carousel insight",
            ),
        ]
    )


def get_seo_insights_data() -> SeoInsightsResponse:
    return SeoInsightsResponse(
        keywords=[
            KeywordInsight(
                keyword="marketing automation workflow",
                clicks=1340,
                impressions=32400,
                ctr=4.1,
                position=6.2,
                action="Tang authority bang cluster noi dung lien quan",
            ),
            KeywordInsight(
                keyword="social media dashboard template",
                clicks=920,
                impressions=18400,
                ctr=5.0,
                position=5.3,
                action="Them comparison section va CTA tai template",
            ),
            KeywordInsight(
                keyword="content calendar for tiktok",
                clicks=610,
                impressions=20200,
                ctr=3.0,
                position=9.4,
                action="Can refresh title va mo rong FAQ",
            ),
            KeywordInsight(
                keyword="ga4 seo reporting",
                clicks=480,
                impressions=11600,
                ctr=4.2,
                position=7.8,
                action="Chen screenshots dashboard va schema HowTo",
            ),
        ],
        recommendations=get_recommendations(),
    )


def get_integrations_data() -> IntegrationsResponse:
    return IntegrationsResponse(
        integrations=[
            IntegrationStatus(
                name="Facebook Graph API",
                status="Healthy",
                statusClass="status-live",
                accounts="6 pages",
                scope="posts, insights, engagement",
                lastSync="09:15",
            ),
            IntegrationStatus(
                name="LinkedIn API",
                status="Healthy",
                statusClass="status-live",
                accounts="3 company pages",
                scope="ugcPosts, analytics",
                lastSync="09:05",
            ),
            IntegrationStatus(
                name="YouTube Data API",
                status="Healthy",
                statusClass="status-live",
                accounts="2 channels",
                scope="videos, comments, analytics",
                lastSync="08:58",
            ),
            IntegrationStatus(
                name="TikTok API",
                status="Review",
                statusClass="status-draft",
                accounts="4 profiles",
                scope="posts, video metrics",
                lastSync="08:41",
            ),
            IntegrationStatus(
                name="Google Search Console",
                status="Healthy",
                statusClass="status-live",
                accounts="5 properties",
                scope="queries, pages, CTR",
                lastSync="08:32",
            ),
            IntegrationStatus(
                name="Google Analytics 4",
                status="Healthy",
                statusClass="status-live",
                accounts="5 properties",
                scope="traffic, conversion, audience",
                lastSync="08:30",
            ),
        ]
    )


def get_reports_data() -> ReportsResponse:
    return ReportsResponse(
        reports=[
            ReportSnapshot(
                title="Executive weekly pulse",
                cadence="Weekly",
                target="CMO + founders",
                summary="Reach, CTR, SQL, revenue contribution va top 3 recommendations.",
            ),
            ReportSnapshot(
                title="SEO recovery board",
                cadence="Twice weekly",
                target="Content + SEO team",
                summary="Keyword movers, CTR gaps, landing pages can refresh.",
            ),
            ReportSnapshot(
                title="Content engine retrospective",
                cadence="Monthly",
                target="Marketing ops",
                summary="Asset throughput, queue aging, AI adoption va bottleneck.",
            ),
        ]
    )


def get_settings_data(api_base_url: str, ollama_base_url: str, ollama_model: str, spreadsheet_id: str, worksheet: str, sync_interval: int) -> SettingsResponse:
    return SettingsResponse(
        apiBaseUrl=api_base_url,
        ollamaBaseUrl=ollama_base_url,
        ollamaModel=ollama_model,
        spreadsheetId=spreadsheet_id,
        worksheet=worksheet,
        syncIntervalMinutes=sync_interval,
    )
