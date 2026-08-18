# Kế Hoạch Triển Khai: Chuẩn Bị Giai Đoạn A Có Khả Năng Tiếp Tục (Implementation Plan: Resumable Stage A Preparation)

**Nhánh**: `001-stage-a-resume-guard` | **Ngày**: 2026-08-14 | **Đặc tả**: [spec.md](spec.md)

**Đầu vào**: Đặc tả tính năng từ `/specs/001-stage-a-resume-guard/spec.md`

## Tóm Tắt (Summary)

Đảm bảo luồng Giai đoạn A không dùng provider của Workspace Chat có tính bền vững tại các ranh giới nguồn. Một checkpoint định địa chỉ theo nội dung và ràng buộc theo định danh chỉ ghi nhận tiến trình nguồn mờ. Adapter phát ra tiến trình sau mỗi lần commit thành công, chấp nhận tập nguồn đã hoàn thành được kiểm chứng và thực thi hạn chót cho từng nguồn do người gọi cung cấp. Trình chạy benchmark tiếp tục các giai đoạn chưa hoàn thành khớp chính xác, cập nhật nhịp tim (heartbeat) theo từng nguồn và áp dụng fail-closed trong các trường hợp khác. Chế độ mở niêm phong rõ ràng chỉ cho phép chẩn đoán BQ01/BQ02 cục bộ; tuyệt đối không bao giờ kích hoạt Giai đoạn B hoặc tạo bằng chứng niêm phong giả mạo.

## Ngữ Cảnh Kỹ Thuật (Technical Context)

**Ngôn ngữ/Phiên bản**: Python 3.11

**Phụ thuộc chính**: Thư viện chuẩn và adapter tiến trình con RAG v2 hiện có

**Lưu trữ**: Checkpoint JSON nguyên tử trong cache staging cục bộ bị gitignore; chỉ mục SQLite workspace hiện có

**Kiểm thử**: pytest

**Nền tảng mục tiêu**: Máy trạm của người vận hành Windows cục bộ

**Loại dự án**: Ứng dụng Python đơn lẻ và CLI benchmark

**Mục tiêu hiệu năng**: Lưu một checkpoint cho mỗi nguồn thành công và tránh các lệnh gọi chuẩn bị lặp lại cho các nguồn đã hoàn thành sau khi bị gián đoạn

**Ràng buộc**: Giai đoạn A chỉ dùng cục bộ không có provider; chế độ mở niêm phong giới hạn ở BQ01/BQ02; không có văn bản nguồn, tên tệp, credential hoặc phản hồi của provider trong checkpoint; hạn chót cho từng nguồn áp dụng fail-closed; Giai đoạn B bị khóa

**Quy mô/Phạm vi**: Ngữ liệu sản xuất 70 nguồn; các fixture giả lập gọn nhẹ cho kiểm thử đơn vị

## Kiểm Tra Hiến Pháp (Constitution Check)

*CỔNG: Phải đạt trước khi nghiên cứu Giai đoạn 0. Kiểm tra lại sau khi thiết kế Giai đoạn 1.*

- Quyền riêng tư được bảo toàn: metadata của checkpoint chỉ chứa các ID mờ có nguồn gốc từ nội dung, tuyệt đối không chứa văn bản nguồn, tiêu đề, đường dẫn, credential hay dữ liệu provider.
- Giai đoạn A vẫn chỉ dùng cục bộ và không có provider. Thiết kế không mở tuyến provider hay thay đổi nhãn ngữ liệu.
- Hành vi adapter công khai hiện có giữ nguyên cơ chế fail-closed cho các nguồn chưa được chuẩn bị; yêu cầu các bài kiểm thử hồi quy tập trung.
- Thay đổi được đặc tả, lập kế hoạch, phân chia nhiệm vụ và sẽ cập nhật biểu đồ mã nguồn sau khi triển khai theo yêu cầu của hiến pháp dự án.

**Kết quả: ĐẠT (PASS).** Đã kiểm tra lại sau thiết kế: ĐẠT (PASS).

## Cấu Trúc Dự Án (Project Structure)

### Tài liệu

```text
specs/001-stage-a-resume-guard/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/stage-a-checkpoint.md
└── tasks.md
```

### Mã nguồn

```text
src/aios_habit/workspace_chat_rag_v2_adapter.py
scripts/battle_notebooklm_rag_v2.py
tests/test_workspace_chat_rag_v2_adapter.py
tests/test_battle_notebooklm_rag_v2.py
```

**Quyết định cấu trúc**: Mở rộng adapter Workspace Chat hiện có và CLI benchmark hiện có. Thêm các bài kiểm thử hồi quy tập trung bên cạnh phạm vi bao phủ hiện tại; các artifact chạy cục bộ vẫn ở trạng thái bị gitignore.

## Theo Dõi Độ Phức Tạp (Complexity Tracking)

Không có vi phạm hiến pháp nào.

