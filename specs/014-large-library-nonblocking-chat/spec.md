# Đặc tả Tính năng: 014-large-library-nonblocking-chat

**Feature Branch**: `014-large-library-nonblocking-chat`  
**Ngày tạo**: 2026-09-14  
**Trạng thái**: `Approved`  
**Đầu vào**: Khắc phục triệt để sự cố nghẽn CPU, khóa SQLite và chặn hỏi trên thư viện tài liệu quy mô lớn (ví dụ: 988 tài liệu tại sổ điều tra lỗi LSU `NB-E35A7BEE`), loại bỏ việc tự động nạp toàn bộ thư viện vào hàng đợi nền (eager enqueue), chuyển đổi cơ chế kiểm soát nguồn từ All-or-Nothing sang Graceful Degradation, và chuẩn hóa xử lý câu hỏi rộng tuân thủ FR-006 & FR-011.

---

## Bối cảnh & Vấn đề Cốt lõi

Tại sổ tài liệu có quy mô lớn (như sổ `NB-E35A7BEE` với 988 tài liệu, cuộc trò chuyện bật 171 tài liệu, trong đó có 3 tài liệu bị lỗi chuẩn bị vector `failed`), hệ thống gặp 4 điểm nghẽn nghiêm trọng:

1. **Eager Enqueue toàn bộ thư viện khi mở trang**: Tại dòng 2181 và 3466 trong `workspace_chat_app.py`, hệ thống tự động gọi nạp toàn bộ 988 tài liệu vào hàng đợi nền ngay khi người dùng vừa truy cập, gây quá tải CPU, chiếm dụng luồng nền và khóa chặt tệp cơ sở dữ liệu SQLite ledger.
2. **Cơ chế chặn cứng All-or-Nothing**: Tại `_pending_source_submission_state` (L758-765) và các nhánh kiểm tra nguồn (L3001, L3018, L3058), chỉ cần có ít nhất 1 tài liệu trong tập được chọn bị trạng thái `failed`, hệ thống lập tức hủy câu hỏi đang chờ, báo lỗi đỏ chặn cứng người dùng: *"Các tài liệu đã chọn gặp lỗi khi chuẩn bị. Hãy bấm “Thử chuẩn bị lại” ở danh sách nguồn trước khi Hỏi."*, khiến người dùng hoàn toàn không thể trò chuyện dù có 168 tài liệu khác đã sẵn sàng.
3. **Vi phạm đặc tả FR-006 & FR-011 khi xử lý Broad Query**: Khi người dùng hỏi một câu hỏi rộng mà các nguồn chưa hoàn tất chuẩn bị, hệ thống tự ý nâng toàn bộ 171 tài liệu lên mức ưu tiên tương tác (`interactive`) và yêu cầu chuẩn bị tất cả (L3042-3052), vi phạm nghiêm trọng giới hạn chỉ chuẩn bị tối đa 1 nguồn tự động cho mỗi câu hỏi tương tác.
4. **Polling giao diện dồn dập trên tập dữ liệu lớn**: Fragment kiểm tra tiến độ giao diện (L3499) chạy chu kỳ 2.5 giây/lần quét toàn bộ 988 tài liệu trong SQLite, làm gia tăng xung đột khóa cơ sở dữ liệu.

---

## Kịch bản Người dùng & Kiểm thử *(Bắt buộc)*

### Kịch bản 1 - Mở sổ tài liệu lớn không bị đơ CPU và khóa SQLite (Độ ưu tiên: P1)

Người dùng mở sổ tài liệu có hàng trăm hoặc hàng nghìn tài liệu. Giao diện mở nhanh, phản hồi mượt mà, không tự ý nạp toàn bộ thư viện tài liệu vào hàng đợi chuẩn bị nền.

**Tiêu chí nghiệm thu**:
1. **Given** sổ tài liệu có 988 nguồn và cuộc trò chuyện bật 171 nguồn, **When** người dùng mở trang hoặc tải lại, **Then** hệ thống không gọi enqueue 988 nguồn tại sidebar (L2181) và chỉ kích hoạt chuẩn bị cho các nguồn đang bật hoặc theo nhu cầu tương tác thực tế (L3466).
2. **Given** tệp cơ sở dữ liệu SQLite ledger, **When** ứng dụng tải trang, **Then** không xảy ra xung đột khóa cơ sở dữ liệu `sqlite3.OperationalError: database is locked`.

---

### Kịch bản 2 - Graceful Degradation: Bỏ qua nguồn lỗi và tiếp tục hỏi đáp (Độ ưu tiên: P1)

Khi trong số các tài liệu được bật có một số tài liệu bị lỗi chuẩn bị (`failed`), câu hỏi của người dùng không bị hủy hay chặn cứng. Hệ thống tự động bỏ qua các nguồn lỗi, tiếp tục thực hiện tìm kiếm trên các nguồn đã sẵn sàng (`ready`), hoặc dùng cơ chế fallback văn bản nguồn / cầu nối Gemini khi chưa có nguồn vector sẵn sàng.

**Tiêu chí nghiệm thu**:
1. **Given** 171 tài liệu được bật trong đó có 3 tài liệu `failed` và các tài liệu khác `ready`, **When** người dùng gửi câu hỏi, **Then** hệ thống không hủy câu hỏi, không hiện thông báo lỗi đỏ chặn cứng, mà tiến hành tra cứu trên tập tài liệu đã sẵn sàng.
2. **Given** câu hỏi đang chờ trong hàng đợi (`pending_source_submission`), **When** một số nguồn hoàn tất chuẩn bị và một số nguồn bị lỗi, **Then** hàm `_pending_source_submission_state` không trả về `failed` mà chuyển sang `ready` để tự động tiếp tục câu hỏi trên các nguồn sẵn sàng.
3. **Given** tất cả các nguồn được chọn đều bị lỗi chuẩn bị vector nhưng có nội dung văn bản thuần, **When** người dùng gửi câu hỏi, **Then** hệ thống chuyển sang chế độ fallback trực tiếp qua nội dung văn bản nguồn / cầu nối Gemini thay vì từ chối phục vụ.

---

### Kịch bản 3 - Xử lý câu hỏi rộng tuân thủ FR-006 & FR-011 (Độ ưu tiên: P1)

Khi câu hỏi quá rộng không thể xác định phạm vi 1 tài liệu cụ thể và chưa có tài liệu nào sẵn sàng, hệ thống tuyệt đối không tự động nạp toàn bộ thư viện vào hàng đợi ưu tiên tương tác.

**Tiêu chí nghiệm thu**:
1. **Given** câu hỏi rộng (`source_scope.bounded == False`) và chưa có tài liệu nào sẵn sàng, **When** người dùng nhấn Hỏi, **Then** hệ thống không đưa hàng trăm tài liệu vào hàng đợi chuẩn bị tương tác, mà thông báo hướng dẫn người dùng thu hẹp câu hỏi hoặc chọn tài liệu cụ thể theo đúng FR-006.
2. **Given** câu hỏi chỉ liên quan đến 1 tài liệu chưa chuẩn bị, **When** gửi câu hỏi, **Then** hệ thống chỉ đưa đúng 1 tài liệu đó vào hàng đợi ưu tiên tương tác theo đúng FR-011.

---

### Kịch bản 4 - Tối ưu hóa chu kỳ polling tiến độ giao diện (Độ ưu tiên: P2)

Bảng hiển thị tiến độ chuẩn bị tài liệu chỉ theo dõi các tài liệu đang bật trong phạm vi làm việc, với chu kỳ polling giãn cách hợp lý nhằm giảm tải CPU và SQLite.

**Tiêu chí nghiệm thu**:
1. **Given** bảng tiến độ chuẩn bị tài liệu, **When** hiển thị trên giao diện, **Then** tiến độ chỉ tính toán trên tập tài liệu đang bật (`enabled_ctx_sources`) thay vì toàn bộ 988 tài liệu.
2. **Given** trạng thái chuẩn bị đang chạy, **When** fragment polling hoạt động, **Then** chu kỳ chạy được đặt ở mức 4.0 giây (thay vì 2.5 giây).

---

## Yêu cầu Kỹ thuật *(Bắt buộc)*

- **FR-014-01**: Hệ thống PHẢI loại bỏ eager enqueue toàn bộ thư viện tài liệu tại L2181 và chỉ enqueue các nguồn đang bật tại L3466.
- **FR-014-02**: Hàm `_pending_source_submission_state` PHẢI áp dụng Graceful Degradation: không trả về `failed` khi có nguồn lỗi nếu vẫn còn nguồn sẵn sàng hoặc còn nội dung văn bản nguồn để trả lời fallback.
- **FR-014-03**: Cổng kiểm tra câu hỏi trước khi gửi PHẢI bỏ qua các nguồn `failed` và cho phép tìm kiếm trên tập `ready_sources`.
- **FR-014-04**: Khi câu hỏi rộng và chưa có tài liệu nào sẵn sàng, hệ thống PHẢI yêu cầu thu hẹp phạm vi câu hỏi theo FR-006, không được tự ý enqueue toàn bộ tập tài liệu.
- **FR-014-05**: Bảng tiến độ chuẩn bị tài liệu PHẢI theo dõi phạm vi tài liệu đang bật và giãn chu kỳ polling lên 4.0 giây.
- **FR-014-06**: Trình kết nối AI (`antigravity_bridge.py`) PHẢI hỗ trợ đưa trích đoạn văn bản nguồn thuần túy vào ngữ cảnh khi tìm kiếm vector không áp dụng được (`retrieval_applied == False`).
