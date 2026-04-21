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


def get_dashboard_data(wordpress_sites_count: int = 3, analytics_property_count: int = 1) -> DashboardResponse:
    return DashboardResponse(
        kpis=[
            DashboardKpi(
                label="Tổng lượt tiếp cận 7 ngày",
                value="2.48M",
                note="Tổng hợp Facebook, LinkedIn, YouTube, TikTok và WordPress",
                trend="+18.4%",
                trendTone="trend-up",
            ),
            DashboardKpi(
                label="CTR trung bình",
                value="4.9%",
                note="Tăng nhờ tối ưu sáng tạo và CTA",
                trend="+0.8 pt",
                trendTone="trend-up",
            ),
            DashboardKpi(
                label="Nội dung đang chờ duyệt",
                value="14",
                note="Hàng đợi gồm bài đăng, video ngắn và landing page",
                trend="Cần sắp lịch",
                trendTone="trend-flat",
            ),
            DashboardKpi(
                label="Từ khóa SEO đang giảm",
                value="6",
                note="Cần làm mới schema, tiêu đề và liên kết nội bộ",
                trend="Cảnh báo",
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
        syncChannels=get_data_sync_data(wordpress_sites_count, analytics_property_count).syncChannels,
        recommendations=get_recommendations(),
    )


def get_recommendations() -> list[Recommendation]:
    return [
        Recommendation(
            title="Day ngan sach vao YouTube Shorts va TikTok 19:00-21:00",
            detail="Hai kênh này đang tạo tỷ lệ xem sang nhấp tốt nhất cho nhóm nội dung hướng dẫn và social proof.",
            priority="High",
        ),
        Recommendation(
            title="Làm mới 6 bài SEO có vị trí trung bình 8-12",
            detail="Chỉ cần tối ưu tiêu đề, FAQ schema và liên kết neo để đẩy CTR và vị trí lên top 5.",
            priority="High",
        ),
        Recommendation(
            title="Giữ LinkedIn cho nội dung chuyên gia, không lấy lead trực tiếp",
            detail="CTR thấp nhưng tỷ lệ đọc hết tốt, phù hợp làm lớp tạo niềm tin trước remarketing.",
            priority="Medium",
        ),
    ]


def get_data_sync_data(wordpress_sites_count: int = 3, analytics_property_count: int = 1) -> DataSyncResponse:
    return DataSyncResponse(
        syncChannels=[
            SyncChannel(
                name="Trang Facebook",
                accounts=6,
                status="Đang chạy",
                statusClass="status-live",
                lastSync="09:15",
                healthScore=96,
            ),
            SyncChannel(
                name="Trang doanh nghiệp LinkedIn",
                accounts=3,
                status="Đang chạy",
                statusClass="status-live",
                lastSync="09:05",
                healthScore=91,
            ),
            SyncChannel(
                name="Kênh YouTube",
                accounts=2,
                status="Đang chạy",
                statusClass="status-live",
                lastSync="08:58",
                healthScore=94,
            ),
            SyncChannel(
                name="Hồ sơ TikTok",
                accounts=4,
                status="Cần xem lại",
                statusClass="status-draft",
                lastSync="08:41",
                healthScore=82,
            ),
            SyncChannel(
                name="Website WordPress",
                accounts=wordpress_sites_count,
                status="Cảnh báo",
                statusClass="status-warning",
                lastSync="07:50",
                healthScore=74,
            ),
        ],
        accounts=[
            ManagedAccount(
                platform="Facebook",
                account="Cụm phía Bắc",
                assets="3 trang / 2 tài khoản quảng cáo",
                destination="Google Sheets > social_overview",
            ),
            ManagedAccount(
                platform="WordPress",
                account="Website thương hiệu",
                assets=f"{wordpress_sites_count} site / {analytics_property_count} thuộc tính GA4",
                destination="Sheet SEO và nội dung",
            ),
            ManagedAccount(
                platform="YouTube",
                account="Giáo dục sản phẩm",
                assets="2 kênh / 38 danh sách phát",
                destination="Sheet KPI video",
            ),
            ManagedAccount(
                platform="TikTok",
                account="Nhóm người sáng tạo",
                assets="4 hồ sơ / 2 nhóm nội dung",
                destination="Theo dõi video ngắn",
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
                title="Case study tự động hóa cho leadgen B2B",
                platform="LinkedIn",
                format="Băng chuyền",
                views="42K",
                ctr=3.8,
                engagementRate=6.1,
                statusClass="status-live",
                statusLabel="Bền vững",
            ),
            ContentPerformance(
                title="Video ngắn về 3 lỗi khi mở rộng quảng cáo",
                platform="TikTok",
                format="Video",
                views="186K",
                ctr=4.7,
                engagementRate=10.4,
                statusClass="status-live",
                statusLabel="Hiệu quả",
            ),
            ContentPerformance(
                title="Landing page checklist 2026",
                platform="WordPress",
                format="Bài viết",
                views="29K",
                ctr=7.1,
                engagementRate=5.8,
                statusClass="status-draft",
                statusLabel="Làm mới",
            ),
            ContentPerformance(
                title="Hướng dẫn YouTube về bộ máy nội dung",
                platform="YouTube",
                format="Dài hạn",
                views="73K",
                ctr=6.6,
                engagementRate=8.1,
                statusClass="status-live",
                statusLabel="Mở rộng",
            ),
        ],
        recommendations=get_recommendations(),
    )


def get_content_data() -> ContentResponse:
    return ContentResponse(
        ideas=[
            ContentIdea(
                title="So sánh dashboard trước và sau chuyển đổi",
                angle="So sánh KPI trước và sau khi tự động hóa",
                channel="Facebook + LinkedIn",
            ),
            ContentIdea(
                title="3 cách sửa SEO thực chiến trong 60 giây",
                angle="Nội dung giáo dục ngắn với hình ảnh nhanh",
                channel="TikTok + YouTube Shorts",
            ),
            ContentIdea(
                title="Ghi chú của CEO về lợi thế nội dung",
                angle="Nội dung chuyên gia dành cho người ra quyết định",
                channel="LinkedIn",
            ),
            ContentIdea(
                title="Checklist vận hành marketing 2026",
                angle="Lead magnet và cụm bài blog",
                channel="WordPress",
            ),
        ]
    )


def get_scheduler_data() -> SchedulerResponse:
    return SchedulerResponse(
        queue=[
            ScheduleItem(
                asset="Video hook về social proof",
                channel="TikTok",
                slot="Thứ Ba 19:30",
                bestWindow="19:00-21:00",
                audience="Nhóm tiếp cận mới",
            ),
            ScheduleItem(
                asset="Băng chuyền case study",
                channel="LinkedIn",
                slot="Thứ Tư 08:15",
                bestWindow="07:30-09:00",
                audience="Người ra quyết định",
            ),
            ScheduleItem(
                asset="Làm mới bài SEO",
                channel="WordPress",
                slot="Thứ Năm 10:00",
                bestWindow="09:30-11:00",
                audience="Tìm kiếm tự nhiên",
            ),
            ScheduleItem(
                asset="Reel testimonial retargeting",
                channel="Facebook",
                slot="Thứ Sáu 20:00",
                bestWindow="18:30-20:30",
                audience="Lead ấm",
            ),
        ]
    )


def get_campaigns_data() -> CampaignsResponse:
    return CampaignsResponse(
        campaigns=[
            CampaignOverview(
                name="Spring Launch Funnel",
                objective="Tạo lead",
                spend="$12.4K",
                reach="480K",
                forecast="+320 SQL nếu CTR hiện tại giữ trên 4.5%",
                nextMove="Nhân đôi ngân sách cho 2 mẫu sáng tạo có hook dữ liệu",
            ),
            CampaignOverview(
                name="Cụm phục hồi SEO",
                objective="Lưu lượng tự nhiên",
                spend="$2.1K",
                reach="120K lượt hiển thị",
                forecast="+18% lượt nhấp trong 30 ngày",
                nextMove="Làm mới bài có vị trí 8-12 và thêm FAQ schema",
            ),
            CampaignOverview(
                name="Nước rút nội dung chuyên gia",
                objective="Niềm tin thương hiệu",
                spend="$1.5K",
                reach="76K",
                forecast="+22% tỷ lệ theo dõi trên LinkedIn",
                nextMove="Xuất bản 2 bài founder note và 1 băng chuyền insight",
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
                action="Tăng độ uy tín bằng cụm nội dung liên quan",
            ),
            KeywordInsight(
                keyword="social media dashboard template",
                clicks=920,
                impressions=18400,
                ctr=5.0,
                position=5.3,
                action="Thêm phần so sánh và CTA trong template",
            ),
            KeywordInsight(
                keyword="content calendar for tiktok",
                clicks=610,
                impressions=20200,
                ctr=3.0,
                position=9.4,
                action="Cần làm mới tiêu đề và mở rộng FAQ",
            ),
            KeywordInsight(
                keyword="ga4 seo reporting",
                clicks=480,
                impressions=11600,
                ctr=4.2,
                position=7.8,
                action="Chèn ảnh dashboard và schema HowTo",
            ),
        ],
        recommendations=get_recommendations(),
    )


def get_integrations_data() -> IntegrationsResponse:
    return IntegrationsResponse(
        integrations=[
            IntegrationStatus(
                name="Facebook Graph API",
                status="Ổn định",
                statusClass="status-live",
                accounts="6 pages",
                scope="bài viết, insight, tương tác",
                lastSync="09:15",
            ),
            IntegrationStatus(
                name="LinkedIn API",
                status="Ổn định",
                statusClass="status-live",
                accounts="3 company pages",
                scope="ugcPosts, phân tích",
                lastSync="09:05",
            ),
            IntegrationStatus(
                name="YouTube Data API",
                status="Ổn định",
                statusClass="status-live",
                accounts="2 channels",
                scope="video, bình luận, phân tích",
                lastSync="08:58",
            ),
            IntegrationStatus(
                name="TikTok API",
                status="Cần xem lại",
                statusClass="status-draft",
                accounts="4 profiles",
                scope="bài đăng, chỉ số video",
                lastSync="08:41",
            ),
            IntegrationStatus(
                name="Google Search Console",
                status="Ổn định",
                statusClass="status-live",
                accounts="5 properties",
                scope="truy vấn, trang, CTR",
                lastSync="08:32",
            ),
            IntegrationStatus(
                name="Google Analytics 4",
                status="Ổn định",
                statusClass="status-live",
                accounts="5 properties",
                scope="lưu lượng, chuyển đổi, đối tượng",
                lastSync="08:30",
            ),
        ]
    )


def get_reports_data() -> ReportsResponse:
    return ReportsResponse(
        reports=[
            ReportSnapshot(
                title="Nhịp báo cáo tuần cho điều hành",
                cadence="Hàng tuần",
                target="CMO + founders",
                summary="Lượt tiếp cận, CTR, SQL, đóng góp doanh thu và 3 đề xuất hàng đầu.",
            ),
            ReportSnapshot(
                title="Bảng phục hồi SEO",
                cadence="Hai lần mỗi tuần",
                target="Đội nội dung và SEO",
                summary="Biến động từ khóa, khoảng cách CTR, landing page cần làm mới.",
            ),
            ReportSnapshot(
                title="Tổng kết bộ máy nội dung",
                cadence="Hàng tháng",
                target="Vận hành marketing",
                summary="Thông lượng nội dung, độ già của hàng đợi, mức độ dùng AI và điểm nghẽn.",
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
