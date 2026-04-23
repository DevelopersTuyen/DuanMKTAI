import { Component } from '@angular/core';

interface GuideSection {
  id: string;
  title: string;
  icon: string;
  route: string;
  purpose: string;
  dataSource: string;
  steps: string[];
  actions: string[];
  issues: string[];
}

@Component({
  selector: 'app-guide',
  templateUrl: './guide.page.html',
  styleUrls: ['./guide.page.scss'],
  standalone: false,
})
export class GuidePage {
  readonly startupChecklist = [
    'Mở backend trước để hệ thống đọc được Google Sheet, WordPress, GA4, GSC, Ollama và ComfyUI.',
    'Sau khi backend chạy, mở frontend để các màn hình tự lấy cache nền và cập nhật không cần tải lại trang.',
    'Kiểm tra mục Tích hợp để xác nhận Google Web, YouTube và các kết nối OAuth đã sẵn sàng trước khi đồng bộ hoặc đăng bài.',
    'Chỉ xác nhận xuất bản bài viết sau khi phần generated content là bài hoàn chỉnh và ảnh đã có trạng thái sẵn sàng.',
  ];

  readonly sections: GuideSection[] = [
    {
      id: 'dashboard',
      title: 'Tổng quan',
      icon: 'grid-outline',
      route: '/dashboard',
      purpose: 'Theo dõi nhanh KPI website, trạng thái đồng bộ, phân tích AI local và tình hình từng website.',
      dataSource: 'Đọc dữ liệu thật từ worksheet website, Post_web, reportday và phân tích AI local qua backend.',
      steps: [
        'Quan sát 4 thẻ KPI đầu màn hình để xem phiên website, lượt xem trang, số bài WordPress và trạng thái SEO.',
        'Xem biểu đồ lưu lượng và tỷ trọng domain để biết website nào đang chiếm traffic chính.',
        'Đọc khối tổng hợp theo từng website để so sánh page views, sessions, posts, clicks, CTR và position.',
        'Dùng phần Phân tích AI cục bộ để xem nhận định tự động từ dữ liệu mới nhất.',
      ],
      actions: [
        'Làm mới toàn bộ dữ liệu tổng quan.',
        'Sao chép hoặc tải bản phân tích AI.',
        'Sao chép tóm tắt tình trạng đồng bộ để gửi nội bộ.',
      ],
      issues: [
        'Nếu biểu đồ trống, kiểm tra backend đã đồng bộ website và dashboard chưa.',
        'Nếu AI local báo lỗi, kiểm tra Ollama đang chạy và model được cấu hình đúng.',
      ],
    },
    {
      id: 'data-sync',
      title: 'Đồng bộ dữ liệu',
      icon: 'sync-outline',
      route: '/data-sync',
      purpose: 'Quản lý việc kéo dữ liệu từ website, social, GA4, GSC và đẩy vào Google Sheet.',
      dataSource: 'Lấy trạng thái thật từ backend sync services, Google Sheet và cấu hình nền tảng.',
      steps: [
        'Kiểm tra khối Google Web để xem spreadsheet, worksheet, GSC site và map từng website.',
        'Kiểm tra WordPress monitor để biết site nào auto sync và site nào cần xử lý thủ công.',
        'Bấm đồng bộ website khi cần ghi dữ liệu mới lên website và Post_web.',
        'Khi đã cấu hình social, dùng đồng bộ social để ghi riêng về facebook, linkedin, youtube, tiktok.',
      ],
      actions: [
        'Đồng bộ website.',
        'Đồng bộ social.',
        'Sao chép Sheet ID, cảnh báo và tóm tắt social.',
      ],
      issues: [
        'Nếu GSC vẫn thiếu dữ liệu, kiểm tra service account có quyền trên đúng property.',
        'Nếu WordPress site không kéo được JSON, site đó cần mở REST API hoặc điều chỉnh bảo mật.',
      ],
    },
    {
      id: 'analytics',
      title: 'Phân tích',
      icon: 'bar-chart-outline',
      route: '/analytics',
      purpose: 'So sánh hiệu suất nội dung và domain dựa trên dữ liệu thật từ website và WordPress.',
      dataSource: 'Đọc dữ liệu website và Post_web đã tổng hợp từ GA4, GSC và WordPress.',
      steps: [
        'Xem bảng domain để biết reach, engagement, CTR và conversion theo từng website.',
        'Kiểm tra danh sách top content để xác định bài nào đang có lượt xem và CTR tốt nhất.',
        'Dùng phân trang khi dữ liệu nhiều để không làm nặng màn hình.',
        'Kết hợp với phần SEO để chọn bài cần tối ưu lại tiêu đề hoặc meta.',
      ],
      actions: [
        'Làm mới dữ liệu phân tích.',
        'Sao chép nội dung nổi bật.',
        'Tải snapshot phân tích.',
      ],
      issues: [
        'Nếu số liệu thấp bất thường, đối chiếu lại ngày sync gần nhất trong phần Đồng bộ dữ liệu.',
      ],
    },
    {
      id: 'content-studio',
      title: 'Xưởng nội dung',
      icon: 'sparkles-outline',
      route: '/content-studio',
      purpose: 'Tạo bài viết hoàn chỉnh bằng AI, sinh ảnh theo nội dung, lưu draft và xác nhận trước khi đăng.',
      dataSource: 'Pipeline backend dùng llama3.2:3b, llava, qwen2.5:3b, ComfyUI và lưu kết quả vào post_create_by_ai.',
      steps: [
        'Nhập brief ngắn nhưng rõ chủ đề, mục tiêu và yêu cầu bài viết.',
        'Bấm tạo bài viết để backend chạy job nền theo từng bước và hiển thị % tiến độ.',
        'Đợi generated content hoàn tất, đọc lại để chắc đó là bài hoàn chỉnh chứ không phải dàn ý.',
        'Kiểm tra ảnh đã có trạng thái sẵn sàng và đúng với mô tả nội dung.',
        'Chỉ bấm xác nhận khi bài và ảnh đạt yêu cầu để chuyển sang bước xuất bản hoặc đưa vào lịch đăng.',
      ],
      actions: [
        'Tạo draft mới.',
        'Xóa draft lỗi hoặc không dùng.',
        'Tải bài viết, tải markdown pipeline, sao chép bài hoặc sao chép prompt ảnh.',
      ],
      issues: [
        'Nếu ảnh bị skipped, kiểm tra ComfyUI/AUTOMATIC1111 và checkpoint đã sẵn sàng.',
        'Nếu generated content còn là dàn ý, tạo lại draft mới sau khi backend đã nạp prompt sửa mới.',
      ],
    },
    {
      id: 'scheduler',
      title: 'Lên lịch',
      icon: 'calendar-outline',
      route: '/scheduler',
      purpose: 'Thiết lập đăng thủ công hoặc tự động, ngày giờ bắt đầu và quy tắc lặp lại.',
      dataSource: 'Lưu scheduler settings vào backend để hệ thống tự đọc và chạy theo cài đặt.',
      steps: [
        'Chọn chế độ mặc định là tự động hoặc thủ công.',
        'Tạo từng lịch đăng với thời gian bắt đầu, loại lặp và ngày trong tuần nếu cần.',
        'Bật hoặc tắt từng lịch để kiểm soát hàng đợi xuất bản.',
        'Khi cần đồng bộ với bài AI, chỉ xác nhận draft rồi đưa vào lịch phù hợp.',
      ],
      actions: [
        'Lưu cấu hình lên lịch.',
        'Bật hoặc tắt từng lịch.',
        'Theo dõi hàng đợi xuất bản.',
      ],
      issues: [
        'Nếu job nền chưa chạy, kiểm tra autoSchedule trong Cài đặt và trạng thái worker runtime.',
      ],
    },
    {
      id: 'campaigns',
      title: 'Chiến dịch',
      icon: 'rocket-outline',
      route: '/campaigns',
      purpose: 'Theo dõi mục tiêu, reach, spend và next move của từng chiến dịch marketing.',
      dataSource: 'Dùng dữ liệu backend tổng hợp để hiển thị campaign overview.',
      steps: [
        'Đọc từng chiến dịch theo mục tiêu chính.',
        'Đối chiếu với dữ liệu Tổng quan và Phân tích để quyết định tối ưu nội dung hoặc lịch đăng.',
      ],
      actions: [
        'Xem nhanh campaign overview.',
      ],
      issues: [
        'Nếu muốn dữ liệu chi tiết hơn, cần nối thêm social/ad platform thật ở backend.',
      ],
    },
    {
      id: 'seo-insights',
      title: 'Thông tin SEO',
      icon: 'search-outline',
      route: '/seo-insights',
      purpose: 'Xem keyword/page SEO thật từ GSC, nhận đề xuất tối ưu và tách riêng theo từng website.',
      dataSource: 'Đọc website worksheet đã đồng bộ nhiều GSC site cùng lúc.',
      steps: [
        'Xem khối tóm tắt theo website để biết site nào đang có SEO tốt hơn.',
        'Kiểm tra bảng cơ hội SEO theo trang với clicks, impressions, CTR và position.',
        'Chọn các trang có position tốt nhưng CTR thấp để tối ưu title và meta description.',
      ],
      actions: [
        'Làm mới dữ liệu SEO.',
        'Sao chép bảng SEO.',
        'Tải snapshot SEO.',
      ],
      issues: [
        'Nếu không có dữ liệu, kiểm tra quyền Search Console của service account và map site đúng domain.',
      ],
    },
    {
      id: 'integrations',
      title: 'Tích hợp',
      icon: 'layers-outline',
      route: '/integrations',
      purpose: 'Tách rõ kết nối Google Web với các kết nối OAuth như YouTube, TikTok, Facebook, LinkedIn.',
      dataSource: 'Google Web lấy từ trạng thái backend website sync, OAuth lấy từ token store và provider config.',
      steps: [
        'Xem khối Google Web để xác nhận spreadsheet, worksheet, GSC site và map WordPress.',
        'Xem từng provider OAuth để biết đã kết nối, hết hạn token hay thiếu client secret.',
        'Bấm kết nối hoặc làm mới token theo từng nền tảng khi cần.',
      ],
      actions: [
        'Kết nối OAuth.',
        'Làm mới token.',
        'Gỡ kết nối.',
        'Sao chép tóm tắt kết nối hoặc cảnh báo.',
      ],
      issues: [
        'Nếu YouTube chưa kết nối được, kiểm tra Google OAuth app và redirect URI.',
        'Nếu Google Web chưa sẵn sàng, kiểm tra service account, Sheet ID, GA4 và GSC site URL.',
      ],
    },
    {
      id: 'reports',
      title: 'Báo cáo',
      icon: 'document-text-outline',
      route: '/reports',
      purpose: 'Tạo báo cáo ngày bằng AI local, lưu vào reportday và quản lý lịch sử báo cáo.',
      dataSource: 'Báo cáo sinh từ dữ liệu thật trên website và các sheet social khi có dữ liệu.',
      steps: [
        'Bấm tạo báo cáo ngày để backend đọc dữ liệu mới nhất và ghi vào reportday.',
        'Xem ngay báo cáo mới nhất trên màn hình.',
        'Quản lý lịch sử báo cáo để đối chiếu theo từng ngày.',
      ],
      actions: [
        'Tạo báo cáo mới.',
        'Xóa báo cáo ngày.',
        'Sao chép hoặc tải báo cáo mới nhất.',
      ],
      issues: [
        'Nếu nội dung báo cáo cũ vẫn hiện, kiểm tra backend đã nạp patch xóa và cache đã được làm mới.',
      ],
    },
    {
      id: 'settings',
      title: 'Cài đặt',
      icon: 'settings-outline',
      route: '/settings',
      purpose: 'Điều khiển runtime toàn hệ thống: API, Ollama, đồng bộ dữ liệu, worker nền và lịch tự động.',
      dataSource: 'Lưu cấu hình runtime vào backend để worker đọc lại theo chu kỳ mà không cần sửa code.',
      steps: [
        'Cấu hình API backend, Ollama, spreadsheet và worksheet mặc định.',
        'Bật auto sync nếu muốn hệ thống tự đồng bộ không cần thao tác tay.',
        'Thiết lập sync mode, giờ chạy, chu kỳ lặp và các ngày trong tuần.',
        'Bật autoRecommend và autoSchedule nếu muốn AI và báo cáo ngày tự vận hành.',
        'Kiểm tra runtime status để biết worker đang dùng cấu hình nào và job gần nhất chạy ra sao.',
      ],
      actions: [
        'Lưu cấu hình hệ thống.',
        'Khôi phục biểu mẫu.',
        'Sao chép hoặc tải JSON cấu hình.',
      ],
      issues: [
        'Sau khi đổi cấu hình nặng như Sheet hoặc Ollama, nên restart backend nếu muốn làm sạch toàn bộ cache nóng.',
      ],
    },
  ];

  readonly faqs = [
    {
      question: 'Khi nào nên đồng bộ dữ liệu thủ công?',
      answer: 'Dùng đồng bộ thủ công khi bạn vừa đổi cấu hình kết nối, vừa cấp lại quyền Google hoặc vừa sửa nội dung website và muốn có dữ liệu mới ngay.',
    },
    {
      question: 'Vì sao chuyển tab mà dữ liệu không mất?',
      answer: 'Frontend đang giữ cache nền theo scope màn hình. Khi quay lại page, app dùng dữ liệu hiện có rồi mới làm mới nền.',
    },
    {
      question: 'Tại sao draft AI không nên xác nhận ngay?',
      answer: 'Vì xác nhận là bước chuẩn bị cho đăng hoặc đưa vào lịch. Cần chắc bài là bản hoàn chỉnh, ảnh đúng và nội dung không còn lỗi dàn ý.',
    },
  ];

  scrollToSection(sectionId: string): void {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }
}
