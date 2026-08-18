# Nhiệm Vụ: Chuẩn Bị Giai Đoạn A Có Khả Năng Tiếp Tục (Tasks: Resumable Stage A Preparation)

**Đầu vào**: Các tài liệu thiết kế từ `/specs/001-stage-a-resume-guard/`

**Điều kiện tiên quyết**: plan.md, spec.md, research.md, data-model.md, contracts/stage-a-checkpoint.md, quickstart.md

## Giai đoạn 1: Thiết lập (Setup)

- [X] T001 Xác nhận các artifact runtime bị bỏ qua vẫn được loại trừ trong `.gitignore` và không thêm placeholder bằng chứng đã niêm phong nào.

## Giai đoạn 2: Nền tảng (Foundational)

- [X] T002 Thêm tùy chọn hạn chót theo từng nguồn có giới hạn vào `scripts/battle_notebooklm_rag_v2.py` và chỉ truyền vào bước chuẩn bị Giai đoạn A cục bộ.
- [X] T003 Thêm các hàm trợ giúp xác thực ghi/đọc checkpoint ràng buộc định danh trong `scripts/battle_notebooklm_rag_v2.py` sử dụng JSON nguyên tử và ID tài liệu mờ.

## Giai đoạn 3: Câu chuyện người dùng 1 - Tiếp tục chuẩn bị cục bộ bị gián đoạn (Ưu tiên: P1)

**Mục tiêu**: Tiếp tục một lượt chạy Giai đoạn A khớp mà không cần chuẩn bị lại các nguồn đã commit thành công.

**Kiểm thử độc lập**: Một sự cố giả lập sau 1 lần commit tạo ra một checkpoint khớp; lượt chạy lại chỉ gọi chuẩn bị cho các nguồn còn lại.

- [X] T004 [US1] Viết kiểm thử tiến trình / tiếp tục của adapter trong `tests/test_workspace_chat_rag_v2_adapter.py`.
- [X] T005 [US1] Mở rộng `prepare_workspace_chat_sources` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py` với khả năng bỏ qua tài liệu đã hoàn thành đã được xác thực và sự kiện tiến trình sau khi commit.
- [X] T006 [US1] Viết kiểm thử tiếp tục / checkpoint staging trong `tests/test_battle_notebooklm_rag_v2.py`.
- [X] T007 [US1] Triển khai tiếp tục checkpoint khớp và cập nhật hoàn thành nguyên tử trong `scripts/battle_notebooklm_rag_v2.py`.

## Giai đoạn 4: Câu chuyện người dùng 2 - Xác định và giới hạn nguồn bị đình trệ (Ưu tiên: P2)

**Mục tiêu**: Giữ lại điểm khởi động lại an toàn và lỗi tất định khi một nguồn cục bộ bị đình trệ.

**Kiểm thử độc lập**: Sự cố hết hạn chót giả lập đánh dấu giai đoạn là thất bại, chỉ ghi lại danh mục lỗi an toàn và không tạo ra manifest sẵn sàng.

- [X] T008 [US2] Viết kiểm thử registry sẵn sàng một phần và hạn chót trong `tests/test_workspace_chat_rag_v2_adapter.py`.
- [X] T009 [US2] Thực thi ngân sách thời gian cấp nguồn trong `src/aios_habit/rag_v2/bge_subprocess_client.py` và kết nối qua `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [X] T010 [US2] Viết kiểm thử nhịp tim (heartbeat) không chứa nội dung và hạn chót staging fail-closed trong `tests/test_battle_notebooklm_rag_v2.py`.
- [X] T011 [US2] Lưu trạng thái checkpoint thất bại và tiến trình nhịp tim theo từng nguồn trong `scripts/battle_notebooklm_rag_v2.py`.

## Giai đoạn 5: Câu chuyện người dùng 3 - Bảo toàn ranh giới cổng chẩn đoán (Ưu tiên: P3)

**Mục tiêu**: Giữ tính năng tiếp tục tách biệt khỏi tính hợp lệ của artifact niêm phong và sự ủy quyền provider trực tiếp.

**Kiểm thử độc lập**: Các bài kiểm thử tập trung chứng minh Giai đoạn A cục bộ không khởi tạo provider và một artifact bất biến bị thiếu vẫn giữ trạng thái bị chặn.

- [X] T012 [US3] Thêm độ bao phủ bộ chặn artifact bị thiếu và chỉ dùng cục bộ / không dùng provider trong `tests/test_battle_notebooklm_rag_v2.py`.
- [X] T013 [US3] Đảm bảo metadata kết quả Giai đoạn A trong `scripts/battle_notebooklm_rag_v2.py` gắn nhãn các trạng thái bị chặn và tiếp tục mà không đưa ra kết luận chất lượng.

## Giai đoạn 6: Xác thực và vệ sinh (Validation and hygiene)

- [X] T014 Chạy các bài kiểm thử tập trung và toàn bộ bộ kiểm thử liên quan từ `specs/001-stage-a-resume-guard/quickstart.md`.
- [X] T015 Chạy `python -m compileall src scripts`, `git diff --check`, và `graphify update .` sau khi triển khai.
- [X] T016 Xem xét diff; báo cáo trạng thái phục hồi artifact niêm phong riêng biệt khỏi xác thực mã nguồn và không chạy BQ01/BQ02 cho đến khi các artifact hiện diện.
- [X] T017 Thêm kiểm thử hồi quy cho việc xây dựng adapter Giai đoạn A sản xuất và loại bỏ cấu hình dự phòng từ vựng không hỗ trợ khỏi `scripts/battle_notebooklm_rag_v2.py`.
- [X] T018 Thêm hợp đồng chẩn đoán mở niêm phong BQ01/BQ02 chỉ dùng cục bộ rõ ràng trong `src/aios_habit/workspace_chat_rag_v2_deployment.py`, `scripts/battle_notebooklm_rag_v2.py`, và các bài kiểm thử tập trung.

## Phụ Thuộc & Thứ Tự Thực Thi

- T001-T003 đi trước toàn bộ các công việc câu chuyện người dùng.
- T004-T007 tạo nên MVP của P1.
- T008-T011 phụ thuộc vào hành vi checkpoint và adapter của P1.
- T012-T013 phụ thuộc vào hành vi Giai đoạn A đã hoàn thành.
- T014-T016 đi sau toàn bộ các nhiệm vụ triển khai.

## Chiến Lược Triển Khai

Triển khai và kiểm chứng P1 trước, sau đó bổ sung chốt chặn hạn chót. Chẩn đoán chính vẫn chưa chạy cho đến khi các artifact niêm phong được khôi phục độc lập; không có nhiệm vụ nào ủy quyền cho Giai đoạn B.

