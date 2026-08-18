# BÁO CÁO KIỂM TOÁN NGUỒN AIOS ROUTER (AIOS ROUTER SOURCE AUDIT REPORT)

Cổng: AIOS-Router-0 — Kiểm toán nguồn + Kế hoạch chính sách tự động Tiếng Việt

## Đường Cơ Sở AIOS (AIOS Baseline)

- HEAD: `8db94bb Add local AI provider bridge`
- HEAD kỳ vọng hiện tại: khớp `8db94bb`
- Kiểm thử: `py -3 -m pytest` => `197 passed in 8.01s`
- Import package: `package import ok`
- Kiểm toán CLI audit: `{"errors": [], "status": "PASS", "warnings": []}`
- Trạng thái sạch:
  - Cây làm việc được theo dõi trước tài liệu này: sạch (clean)
  - Dữ liệu runtime/cache bị bỏ qua hiện diện: `.pytest_cache/`, `local_cases/`, `src/aios_habit.egg-info/`, `__pycache__/`, và các thư mục đầu ra tự sinh của AIOS

## Tính Khả Dụng Của Các Repository Nguồn (Repo Availability)

### translation_app

- Đường dẫn cục bộ: `[LOCAL_WORKSPACE]\translation_app`
- Tồn tại: Có
- Remote: `https://github.com/Nakazasen/translation_app.git`
- Nhánh: `wip/phase-5n-f-ocr-benchmark`
- HEAD: `f105ffb3ac84b9ec38f03e882656826b2001d341`
- Trạng thái: Chỉ có `.vscode/` không được theo dõi
- Các tệp quan trọng: `core/provider_router.py`, `core/providers/`, `core/provider_health_checker.py`, `core/ai_service.py`, router/provider tests

### nvidia-server

- Đường dẫn cục bộ: `[LOCAL_WORKSPACE]\Nvidia`
- Tồn tại: Có
- Remote: `https://github.com/Nakazasen/nvidia-server`
- Nhánh: `main`
- HEAD: `77e45e44e8589d24618c5ea59ec1dd31945dcf89`
- Trạng thái: Không có thay đổi nào được báo cáo bởi `git status --short`
- Các tệp quan trọng: `tools/agent-core.mjs`, `electron-main.js`, `nvidia_playground.html`, `package.json`, `README.md`, `docs/`, `tests/`

### mat-the-website

- Đường dẫn cục bộ trước kiểm toán: Chưa có
- Hành động: Đã clone từ `https://github.com/Nakazasen/mat-the-website`
- Tồn tại sau khi clone: Có
- Remote: `https://github.com/Nakazasen/mat-the-website`
- Nhánh: `main`
- HEAD: `e393bd4b9e6b64cbc60f9abcf4970adf622ae636`
- Trạng thái: Sạch sau khi clone
- Các tệp quan trọng: `backend/ai_providers/router.py`, `backend/ai_providers/`, `backend/rate_limit.py`, `backend/security_utils.py`, `backend/main.py`

## Phát Hiện Từ translation_app

### Bộ Định Tuyến Provider (Provider Router)

- `core/provider_router.py` là nguồn router mạnh mẽ nhất được tìm thấy.
- Nó triển khai: đăng ký provider, lặp ứng viên (candidate iteration), trạng thái provider/model/key, thử lại/dự phòng (retry/fallback), sắp xếp thứ tự động, thời gian hồi (cooldown), hành vi ngắt mạch (circuit breaker) và theo vết lượt thử (attempt tracing).
- Nó chạy đồng bộ và đặc thù cho dịch thuật, do đó AIOS nên kế thừa các khái niệm thay vì sao chép trực tiếp module.

Phân loại:
- `PORT_NOW` (Kế thừa ngay): Mô hình trạng thái provider, ý tưởng phân loại lỗi, hành vi cooldown, hình thái ảnh chụp sức khỏe, mô hình theo vết lượt thử, khái niệm xoay vòng ứng viên key/model.
- `PORT_LATER` (Kế thừa sau): Ghim chặt provider/model nghiêm ngặt, hành vi cứu cánh cuối cùng của Google Translate chỉ khi AIOS có trường hợp sử dụng phù hợp.
- `NEEDS_REWRITE` (Cần viết lại): `TranslationRequest` / `TranslationResult` thành các kiểu yêu cầu / kết quả vụ việc và hỏi đáp của AIOS, và loại bỏ phụ thuộc trực tiếp vào `translation_app.core.ai_service`.
- `DO_NOT_PORT` (Không kế thừa): Xây dựng prompt chỉ dành riêng cho dịch thuật và văn bản UI làm lộ các nhãn router kỹ thuật.

### Các Nhà Cung Cấp (Providers)

Hỗ trợ provider rất rộng rãi theo phong cách router:
- Gemini
- Google Translate fallback
- ChatAnyWhere
- DeepSeek
- NVIDIA NIM
- generic OpenAI-compatible endpoint
- Groq
- Cerebras
- OpenRouter
- Mistral AI
- SambaNova
- Cloudflare Workers AI
- HuggingFace
- GitHub Models
- AI21 Studio

Danh mục provider tái sử dụng then chốt nằm tại `core/providers/profiles.py`.

Phân loại:
- `PORT_NOW`: Chuẩn hóa danh mục provider, khung nhìn cấu hình provider công khai đã làm sạch, tên hiển thị, base URL / model mặc định.
- `PORT_LATER`: Các adapter tùy biến cho Cloudflare và HuggingFace.
- `NEEDS_REWRITE`: Hợp đồng yêu cầu provider cho WorkLens và hỏi đáp có căn cứ của AIOS.
- `DO_NOT_PORT`: Tên provider đặc thù dịch thuật trong giao diện AIOS.

### Cơ Chế Dự Phòng (Fallback)

- Router thử các provider theo thứ tự đã giải quyết.
- Các lượt thử thất bại được ghi nhận và ứng viên / provider tiếp theo sẽ được thử.
- Lỗi cuối cùng bao gồm lượt thử cuối và thông báo cạn kiệt nguồn.

Phân loại: `PORT_NOW` sau khi điều chỉnh theo schema kết quả của AIOS.

### Thời Gian Hồi (Cooldown)

- Lỗi hạn ngạch / giới hạn tốc độ và lỗi tạm thời sẽ kích hoạt cooldown.
- Có hỗ trợ tiêu đề `Retry-After`.
- Một số provider có khoảng thời gian tối thiểu giữa các yêu cầu.

Phân loại: `PORT_NOW`.

### Bộ Ngắt Mạch (Circuit Breaker)

- Lỗi xác thực sẽ đánh dấu provider là không khả dụng.
- Router cố gắng vô hiệu hóa bền vững các provider không hợp lệ thông qua trình quản lý cấu hình.
- Trạng thái sức khỏe có thể chuyển thành: `dead`, `cooldown`, `degraded`, hoặc `healthy`.

Phân loại:
- `PORT_NOW`: Hành vi ngắt mạch trong lúc runtime.
- `PORT_LATER`: Tự động vô hiệu hóa bền vững, chỉ sau khi AIOS có giao diện cài đặt an toàn.

### Xoay Vòng Key / Thông Tin Bí Mật

- `ProviderProfile` hỗ trợ nhiều API key.
- `OpenAICompatibleProvider.iter_candidates()` mở rộng ứng viên theo tích model x key.
- `mark_success()` và `mark_failure()` thực hiện xoay vòng key/model.
- Key được che giấu qua phần đuôi (`****1234`) khi hiển thị trạng thái công khai.
- `AIConfigManager` tách biệt cấu hình và secret, hỗ trợ tải sao lưu và phủ lớp bí mật.

Phân loại:
- `PORT_NOW`: ID key đã che giấu trong log định tuyến, xoay vòng ứng viên key, khái niệm tách biệt cấu hình và secret.
- `PORT_LATER`: Di chuyển hoàn chỉnh sang kho lưu trữ secret.
- `DO_NOT_PORT`: Bất kỳ API key thật nào hoặc tệp cấu hình cục bộ tự sinh.

### Kiểm Tra Sức Khỏe (Health)

- `core/provider_health_checker.py` kiểm tra khả năng phản hồi của provider/model.
- Nó ánh xạ các lỗi cấp thấp thành thông điệp Tiếng Việt và gợi ý hành động cho người dùng.
- Nó cập nhật sức khỏe router khi có thể.

Phân loại:
- `PORT_NOW`: Khái niệm hiển thị trạng thái sức khỏe và thông điệp sức khỏe Tiếng Việt được viết lại theo thuật ngữ AIOS.
- `PORT_LATER`: Thăm dò provider live, vì quá trình kiểm toán này tuyệt đối không gọi các provider có key thật.

### Kiểm Thử (Tests)

Bộ kiểm thử mạnh mẽ liên quan đến router hiện có:
- `tests/test_provider_router.py`
- `tests/test_free_llm_pool.py`
- `tests/test_provider_health_checker.py`
- `tests/test_provider_model_catalog.py`
- `tests/test_provider_model_discovery.py`
- `tests/test_provider_priority_ui.py`
- `tests/test_specific_provider_fallback.py`

Phân loại: `PORT_NOW` dưới dạng tham chiếu thiết kế kiểm thử, không sao chép trực tiếp mã nguồn.

### Các Thành Phần Tái Sử Dụng

1. Danh mục provider với các hồ sơ đã chuẩn hóa.
2. Mẫu adapter tương thích OpenAI.
3. Mở rộng ứng viên qua bể model và bể key.
4. Phân loại lỗi cho cooldown và circuit breaker.
5. Ảnh chụp nhanh sức khỏe và theo vết các lượt thử.
6. Phong cách hiển thị trạng thái / gợi ý bằng Tiếng Việt cho người dùng phi kỹ thuật.
7. Các bài kiểm thử cho hành vi fallback, hạn ngạch, sức khỏe và độ ưu tiên.

## Phát Hiện Từ nvidia-server

### Trừu Tượng Hóa Provider

- Không tìm thấy bể provider đa dạng hoàn chỉnh tương đương như `translation_app`.
- Mã nguồn mạnh nhất không phải là định tuyến provider mà là hạ tầng runtime / workspace cho AI agent.
- `tools/agent-core.mjs` sử dụng provider từ vựng ngoại tuyến cho dự phòng chỉ mục ngữ nghĩa, không phải bộ định tuyến provider AI đầy đủ.

Phân loại:
- Sử dụng ngay cho router: Không
- Sử dụng sau cho AIOS Agent Runtime: Có

### Runtime MCP/CLI

`tools/agent-core.mjs` cung cấp các công cụ tệp, tìm kiếm, lập chỉ mục, công cụ git, các chỉnh sửa đang chờ (pending edits), thực thi lệnh, các tiến trình lệnh nền, trạng thái tiến trình và hủy bỏ tiến trình.

Phân loại: `PORT_LATER` cho `AIOS-Agent-Later`, không thuộc AIOS-Router-1.

### Bộ Chọn Ngữ Cảnh (Context Picker)

- Xây dựng cache chỉ mục với metadata tệp và các chunk dòng.
- Bỏ qua các thư mục nặng/không an toàn như `.git`, `.brain`, `.nvidia-agent`, `node_modules`, `.venv`, cache, thư mục build.
- Hỗ trợ tìm kiếm từ vựng trên các chunk và ưu tiên các tệp vừa thay đổi / gần đây.
- Làm sạch (redact) secret khi lập chỉ mục / trả về nội dung.

Phân loại: `PORT_LATER` cho bộ chọn ngữ cảnh WorkLens và agent runtime.

### Quản Lý Tiến Trình (Job Manager)

- `startCommandJobTool`, `commandJobStatusTool`, và `cancelCommandJobTool` quản lý các tiến trình shell chạy dài.
- Các tiến trình lưu giữ stdout/stderr và hỗ trợ phân trang theo offset.

Phân loại: `PORT_LATER` cho các tiến trình AI agent và dấu vết kiểm toán của AIOS.

### An Toàn và Kiểm Toán (Safety/Audit)

Các mẫu hữu ích:
- Cổng tin cậy workspace (workspace trust gate) trước các thao tác ghi / thực thi lệnh
- Kiểm tra bao bọc đường dẫn (path containment checks)
- Xác nhận các hành động có tính phá hủy (destructive actions)
- Hàng đợi chỉnh sửa chờ duyệt (pending edits) trước khi ghi
- Làm sạch secret cho đầu ra / log
- Định nghĩa quyền hạn với các mức độ rủi ro và yêu cầu phê duyệt

Phân loại: `PORT_LATER` cho AIOS Agent Runtime.

### Các Khái Niệm Tái Sử Dụng

1. Tin cậy workspace (Workspace trust).
2. Hàng đợi chỉnh sửa chờ duyệt (Pending edit queue).
3. Trình quản lý tiến trình lệnh (Command job manager).
4. Bảng quyền công cụ (Tool permission table).
5. Làm sạch secret (Secret redaction).
6. Lập chỉ mục và truy xuất ngữ cảnh (Context indexing and retrieval).

## Phát Hiện Từ mat-the-website

### AI Router

- Trái với dự đoán ban đầu, repo này có chứa mã nguồn AI router.
- `backend/ai_providers/router.py` nêu rõ rằng nó được chuyển đổi từ `translation_app.core.provider_router.ProviderRouter` sang dạng bất đồng bộ (async) cho FastAPI.
- Nó hỗ trợ fallback dạng thác nước (waterfall fallback), `ai_pool_auto`, trạng thái sức khỏe provider, cooldown, các lượt thử ứng viên key/model và theo vết lượt thử.
- Nó hữu ích như một tài liệu tham khảo về chuyển đổi sang async, nhưng ít toàn diện hơn router gốc của `translation_app`.

Phân loại:
- Liên quan đến AI router: Có, dưới dạng dẫn xuất bất đồng bộ.
- `PORT_LATER`: Mẫu API định tuyến async nếu AIOS sau này mở router qua backend web.
- `NEEDS_REWRITE`: Phụ thuộc và đặc thù lĩnh vực dịch truyện web.

### Các Thành Phần Backend / Bảo Mật

Các mẫu backend liên quan:
- `backend/rate_limit.py`
- `backend/security_utils.py`
- `backend/ai_providers/error_classifier.py`
- `backend/ai_providers/health.py`
- Ví dụ tích hợp trong `backend/main.py`

Phân loại: Chỉ là mẫu backend; không phải nguồn router chính.

### Khuyến Nghị (Recommendation)

- Không sử dụng `mat-the-website` làm nguồn chân lý chính cho router.
- Sử dụng nó để học cách chuyển đổi router sang async FastAPI và tích hợp tuyến backend.
- Giữ AIOS-Router-0 tập trung vào `translation_app` về độ hoàn thiện của router.

## Xếp Hạng Đánh Giá (Ranking)

1. `translation_app` — nguồn tốt nhất cho AI provider router.
2. `mat-the-website` — dẫn xuất async / backend hữu ích.
3. `nvidia-server` — nguồn tốt nhất cho agent runtime, không phải nguồn router.

## Ma Trận So Sánh (Comparative Matrix)

| Tiêu chí | translation_app | nvidia-server | mat-the-website |
|---|---:|---:|---:|
| Độ hoàn thiện AI provider router | Cao | Thấp | Trung bình |
| Số lượng provider được hỗ trợ | Cao | Thấp | Trung bình |
| Fallback / Cooldown / Circuit breaker | Cao | Thấp | TB-Cao |
| Xử lý key / Bảo mật | Cao | TB-Cao cho làm sạch runtime | Trung bình |
| Kiểm thử | Cao | Trung bình | Trung bình |
| Dễ chuyển đổi sang AIOS | Trung bình | Thấp cho router, TB cho agent runtime | Trung bình |
| Tính liên quan đến AIOS WorkLens router | Cao | Thấp hiện tại, Cao sau này cho agent | Trung bình |

## Chính Sách Giao Diện Người Dùng Tiếng Việt (Vietnamese UX Policy)

Giao diện người dùng bắt buộc chỉ sử dụng các chế độ và giải thích bằng Tiếng Việt hướng tới người dùng này. Tuyệt đối không làm lộ các thuật ngữ triển khai kỹ thuật thô.

### Tự Động
- AIOS tự đoán mức an toàn của tài liệu.
- Đường dẫn hoặc nội dung liên quan MOM, WMS, ERP, nhà máy, công ty, nội bộ, hợp đồng, nhân sự, tài chính, khách hàng mặc định được xử lý theo chế độ an toàn cho công ty.
- Nếu AIOS không chắc, hỏi người dùng: “Đây có phải tài liệu công ty hoặc tài liệu mật không?”
- Người dùng không cần hiểu nhà cung cấp AI, tuyến xử lý, endpoint, hay nhãn kỹ thuật.

### Tài Liệu Công Ty / Tài Liệu Mật
- Tuyệt đối không gửi ra ngoài.
- Chỉ dùng dữ liệu cục bộ, AI nội bộ, hoặc điểm kết nối đã được tin cậy.
- Nếu chưa có AI nội bộ, AIOS vẫn trả lời bằng dữ liệu cục bộ và nói rõ phần nào chưa đủ bằng chứng.
- Không âm thầm chuyển sang AI bên ngoài.

### Tài Liệu Thường
- Dùng toàn bộ nguồn AI đã cấu hình.
- Tự chọn nguồn AI tốt nhất.
- Tự đổi nguồn khi lỗi, hết lượt, quá tải, hoặc phản hồi chậm.
- Tự đổi key nếu người dùng đã cấu hình nhiều key.
- Có thể hỏi nhiều AI cùng lúc nếu bật chế độ nhanh.
- Ghi “Nhật ký AI đã dùng” để người dùng biết AIOS đã dùng nguồn nào.
- Không hạn chế giả tạo ngoài giới hạn thật về lượt dùng, chi phí, tốc độ, và cấu hình của người dùng.

### Các Thuật Ngữ Bị Loại Bỏ Khỏi Giao Diện Người Dùng

Các thuật ngữ kỹ thuật thô sau tuyệt đối không xuất hiện trên UX người dùng:
- `cloud_allowed`
- `local_only`
- `provider policy`
- `route policy`
- Tên enum thô
- Các thuật ngữ định tuyến provider thô khi đã có cụm từ Tiếng Việt phi kỹ thuật thay thế

Các cụm từ Tiếng Việt thay thế được chấp nhận:
- “Tự động”
- “Tài liệu công ty / tài liệu mật”
- “Tài liệu thường”
- “Không gửi ra ngoài”
- “Dùng toàn bộ nguồn AI đã cấu hình”
- “Nhật ký AI đã dùng”
- “Tự đổi nguồn khi lỗi/hết lượt/quá tải”

## Lộ Trình Tích Hợp (Integration Roadmap)

### AIOS-Router-1: UX Chế Độ An Toàn Tiếng Việt
- Bổ sung các chế độ hiển thị rõ ràng bằng Tiếng Việt: “Tự động”, “Tài liệu công ty / tài liệu mật”, “Tài liệu thường”.
- Ẩn toàn bộ các nhãn định tuyến kỹ thuật thô khỏi giao diện người dùng.
- Bổ sung phần giải thích phân loại tự động bằng Tiếng Việt dễ hiểu.
- Nếu không chắc chắn, hỏi: “Đây có phải tài liệu công ty hoặc tài liệu mật không?”

### AIOS-Router-2: Danh Mục Provider Từ translation_app
- Bổ sung danh mục provider AIOS dựa trên các khái niệm của `translation_app`.
- Hỗ trợ danh sách nguồn đã cấu hình và trạng thái sức khỏe.
- Giữ thông tin bí mật ngoài cấu hình được commit.
- Chỉ hiển thị đuôi key đã che giấu trong trạng thái người dùng có thể thấy.
- Không sao chép trực tiếp mã nguồn; viết lại cho các kiểu yêu cầu / phản hồi của AIOS.

### AIOS-Router-3: Router Tự Động Cho “Tài Liệu Thường”
- Sử dụng bể provider cho tài liệu thường.
- Bổ sung hành vi thử lại, dự phòng, xoay vòng key, cooldown và circuit breaker.
- Bảo tồn luồng dự phòng tất định / cục bộ nếu không có provider nào hoạt động.

### AIOS-Router-4: Giao Diện Nhật Ký Định Tuyến
- Bổ sung “Nhật ký AI đã dùng”.
- Hiển thị tên hiển thị provider, tên hiển thị model, đuôi key đã che giấu, trạng thái, độ trễ và lý do bằng Tiếng Việt.
- Tuyệt đối không bao giờ hiển thị API key thô.

### AIOS-Router-5: Đua Song Song Tùy Chọn (Parallel Race)
- Bổ sung tùy chọn “Hỏi nhiều AI cùng lúc để lấy câu nhanh/tốt hơn”.
- Chỉ áp dụng cho “Tài liệu thường”.
- Tôn trọng hạn ngạch / chi phí / giới hạn tốc độ đã cấu hình.

### AIOS-Router-6: Kiểm Toán Quyền Riêng Tư (Privacy Audit)
- Chứng minh tài liệu công ty / mật không bao giờ bị gửi tới AI bên ngoài.
- Chứng minh tài liệu thường có thể sử dụng bể provider.
- Chứng minh các secret đã được che giấu.
- Chứng minh theo vết định tuyến là chính xác.

### AIOS-Router-7: Kiểm Toán DOM / Đơn Vị (DOM/Unit Audit)
- Chứng minh người dùng không bao giờ thấy các nhãn kỹ thuật thô.
- Chứng minh chế độ tự động hoạt động chính xác.
- Chứng minh tài liệu thường sử dụng bể provider.
- Chứng minh tài liệu công ty chặn AI bên ngoài.
- Chứng minh nhật ký định tuyến hiển thị rõ ràng.

### AIOS-Agent-Later
Học hỏi từ `nvidia-server`:
- Bộ chọn ngữ cảnh (Context picker)
- Ý tưởng cầu nối MCP/CLI
- Trình quản lý tiến trình (Job manager)
- Phê duyệt công cụ (Tool approval)
- Chỉnh sửa chờ duyệt (Pending edits)
- Tin cậy workspace (Workspace trust)
- Dấu vết kiểm toán (Audit trail)
- Làm sạch secret (Secret redaction)

Phần này được xác định rõ ràng là làm sau và tuyệt đối không mở P1.0.

## An Toàn (Safety)

- Không commit secret: ĐẠT (PASS). Tài liệu kiểm toán này không chứa API key hay secret nào.
- Không dùng cloud cho tài liệu công ty/mật: Bắt buộc theo roadmap. Không có lệnh gọi provider thật nào được thực hiện trong đợt kiểm toán này.
- Cloud / bể miễn phí cho tài liệu thường: Chỉ lên kế hoạch sau khi đã có UX an toàn Tiếng Việt cho người dùng.
- Không mở P1.0: ĐẠT (PASS). Đợt kiểm toán này không mở P1.0.
- Không sao chép mã nguồn bên thứ ba vào AIOS: ĐẠT (PASS). Tài liệu này chỉ tóm tắt các phát hiện.
- Không tải tài liệu MOM/công ty lên: ĐẠT (PASS). Không có tài liệu công ty nào bị gửi lên cloud.
- Không giả mạo cầu nối Antigravity: ĐẠT (PASS). Kết quả hiện có của AIOS vẫn xác nhận API trực tiếp của Antigravity không có runtime HTTP/MCP/CLI có thể gọi cho ứng dụng này.

## Kết Luận Chung (Overall Verdict)

`TRANSLATION_APP_ROUTER_BEST_SOURCE` (translation_app là nguồn tốt nhất cho router).

Các kết luận đã được kiểm chứng bổ sung:
- `NVIDIA_RUNTIME_BEST_SOURCE` (nvidia-server là nguồn tốt nhất cho agent runtime).
- Nhận định ban đầu `MAT_WEBSITE_NOT_RELEVANT_FOR_ROUTER` không hoàn toàn đúng sau kiểm toán; nó có chứa router phái sinh, nhưng không phải nguồn tốt nhất.

## Khuyến Nghị Bước Tiếp Theo

1. Triển khai AIOS-Router-1 UX Chế Độ An Toàn Tiếng Việt.

Lý do:
- AIOS trước hết phải bảo vệ người dùng khỏi các khái niệm định tuyến kỹ thuật phức tạp.
- Phải đảm bảo tài liệu công ty / mật được xử lý an toàn trước khi kích hoạt bể provider rộng lớn cho tài liệu thường.
- Điều này tạo nền tảng an toàn và trải nghiệm người dùng chuẩn xác cho AIOS-Router-2 và AIOS-Router-3.


