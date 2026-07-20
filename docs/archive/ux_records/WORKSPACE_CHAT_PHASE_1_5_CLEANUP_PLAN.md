# Phase 1.5 — Legacy Containment & Cleanup Plan

Mục tiêu của Phase 1.5 là xác định rõ ranh giới giữa giao diện cũ (Case Cockpit) và giao diện mới (Workspace Chat), thực hiện cô lập mã nguồn cũ để tránh làm bẩn mã nguồn mới, đồng thời chuẩn bị cho lộ trình chuyển đổi và loại bỏ dần các thành phần thừa.

## 1. Đánh dấu và Cô lập Case Cockpit (Legacy)
- Đánh dấu `src/aios_habit/case_cockpit.py` là **Legacy/Advanced Interface** (Giao diện cũ / Giao diện nâng cao).
- Di chuyển các tùy chọn cấu hình nâng cao, prompt thô, và liên kết kỹ thuật sang khu vực riêng biệt. Giao diện Workspace Chat mới sẽ là điểm chạm mặc định đầu tiên của chủ sở hữu (owner).

## 2. Ranh giới Kiến trúc & Sự phụ thuộc
- Mã nguồn của ứng dụng Workspace Chat mới (`workspace_chat_app.py`, `workspace_chat_store.py`, `workspace_chat_models.py`, `workspace_chat_ui.py`) **tuyệt đối không phụ thuộc** hoặc import bất kỳ thành phần nào từ `case_cockpit.py`.
- Mối liên kết duy nhất được phép giữa hai hệ thống là thông qua việc đọc/ghi chéo dữ liệu cấu trúc (ví dụ: chuyển từ cuộc trò chuyện đã phân tích thành Hồ sơ sự việc mới) bằng các lớp service/store trung gian.

## 3. Phân loại Module Legacy để Xử lý
Dưới đây là kế hoạch phân loại các tệp mã nguồn cũ:

### A. Module Giữ lại làm lõi chung (Core Services)
Các module này chứa thuật toán hoặc tiện ích hệ thống không có UI, sẽ được giữ lại làm thư viện dùng chung cho cả giao diện mới:
- `src/aios_habit/case_models.py` & `case_store.py` (Lõi quản lý hồ sơ và bằng chứng)
- `src/aios_habit/workspace_models.py` (Mô hình workspace cũ)
- `src/aios_habit/source_ingest.py` (Trình nạp tài liệu)
- `src/aios_habit/provider_catalog.py` & `ai_router.py` (Quản lý model AI an toàn)

### B. Module cần Cải tiến/Migrate (To be Refactored/Migrated)
Các thành phần chứa logic nghiệp vụ quan trọng nhưng hiện tại đang dính chặt với UI cũ, cần được tách riêng phần logic sang module độc lập trong các Phase tiếp theo:
- `src/aios_habit/strong_answer_ui.py` (Tách phần RAG/Answer Generation ra khỏi UI thành `strong_answer_service.py`)
- `src/aios_habit/visual_map_ui.py` (Chuyển đổi thành giao diện kiểm chứng không kỹ thuật "Xem vì sao AIOS kết luận")
- `src/aios_habit/ide_handoff_bridge.py` (Chuyển phần tích hợp IDE thành service chạy ngầm)

### C. Module Chờ xóa (To be Removed)
Các UI cũ không còn cần thiết sau khi giao diện mới hoàn thiện đầy đủ các tính năng:
- `src/aios_habit/case_cockpit.py` (Sẽ bị loại bỏ hoàn toàn sau khi kiểm thử thực tế với chủ sở hữu (owner pilot) thành công ở Phase 6)

## 4. Cập nhật Launchers & Hướng dẫn
- Cập nhật tài liệu hướng dẫn khởi chạy trong `README.md` để hướng dẫn chủ sở hữu chạy lệnh cho giao diện mới làm mặc định.
- Chỉ đặt liên kết "Mở giao diện cũ" trong mục Cấu hình nâng cao của giao diện mới, không để ở vị trí dễ gây nhầm lẫn trên trang chủ.
