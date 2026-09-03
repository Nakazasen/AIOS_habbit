# Nhiệm vụ đang thực thi: Khóa phần nền và pilot điều tra line đầu tiên

**Mã tính năng**: `008-evidence-case-loop`

**Ngày cập nhật**: 04/09/2026

**Phạm vi hiện tại**: Đợt 0 và Đợt 1 trong [plan.md](plan.md)

## Quy tắc dùng danh sách này

- Chỉ các việc đủ điều kiện thực hiện ngay mới có ô đánh dấu.
- Code Gate 1A, US1 và chuẩn bị nguồn đã tồn tại; không làm lại, chỉ kiểm chứng và sửa lỗi thật quan sát được.
- Mỗi task triển khai chạy test tập trung. Bộ kiểm thử toàn bộ chỉ bắt buộc khi đóng một đợt hoặc trước commit/push phát hành.
- Dữ liệu/log/SOP/mapping thật chỉ dùng cục bộ, không ghi vào Git hoặc báo cáo công khai.
- Trạng thái `DONE`, `PARTIAL` hoặc `BLOCKED` chỉ được cập nhật từ bằng chứng vừa chạy.

## Giai đoạn 1 — Đối soát và khóa phần nền

**Mục tiêu**: biết chính xác phần nào đã chạy được trên cây code hiện tại trước khi thêm luồng mới.

- [ ] T001 Ghi baseline nhánh, commit, diff cục bộ và các thay đổi phải bảo toàn vào `PROJECT_HANDOVER.md`
- [ ] T002 [P] Chạy test tập trung cho migration/kho/quyền/dịch vụ case trong `tests/test_workspace_case_migrations.py`, `tests/test_workspace_case_store.py`, `tests/test_workspace_case_authorization.py` và `tests/test_workspace_case_service.py`
- [ ] T003 [P] Chạy test tập trung cho tiến độ chuẩn bị nguồn và trạng thái sẵn sàng trong `tests/test_workspace_chat_rag_v2_adapter.py` cùng các test giao diện liên quan
- [ ] T004 [P] Chạy test tập trung cho danh sách/chi tiết/trạng thái/kết luận/mở trace trong `tests/test_workspace_case_ui.py`
- [ ] T005 Chỉ sửa lỗi được T002–T004 tái hiện trong các module tương ứng; không đổi schema hoặc kiến trúc ngoài hợp đồng đã duyệt

## Giai đoạn 2 — Smoke trình duyệt phần nền

**Mục tiêu**: người dùng thật hiểu trạng thái hệ thống và mở lại được hồ sơ.

- [ ] T006 [US1] Kiểm tra trình duyệt khi thư viện chưa sẵn sàng: phải có phần trăm, trạng thái tiếng Việt, hướng dẫn tiếp tục/thử lại và không lộ tên engine nội bộ
- [ ] T007 [US1] Kiểm tra trình duyệt khi chuẩn bị bị dừng hoặc có nguồn lỗi: nút tiếp tục/thử lại hoạt động và tiến độ không đứng im giả
- [ ] T008 [US1] Tạo case từ một câu trả lời có citation, mở từ mục “Hồ sơ vụ việc”, đổi trạng thái, ghi kết luận rồi khởi động lại để đọc lại
- [ ] T009 [US1] Kiểm tra trace bị thiếu và tham chiếu evidence không còn: UI phải báo thiếu bằng chứng bằng tiếng Việt, không bịa lại nội dung và không lộ traceback
- [ ] T010 Ghi kết quả smoke đã làm sạch vào `PROJECT_HANDOVER.md`; nếu thiếu tài liệu hoặc môi trường thật thì ghi `PARTIAL`, không đánh dấu đạt thay thế bằng fixture

## Giai đoạn 3 — Xác nhận tối thiểu trong case

**Mục tiêu**: người điều tra kiêm chuyên gia có thể xác nhận/bác bỏ manh mối; vẫn hỗ trợ người thứ hai khi thật sự cần.

- [ ] T011 [P] [US2] Viết test cho xác nhận cùng người đúng scope, tùy chọn chuyên gia thứ hai, lý do bắt buộc, review append-only và AI không có quyền duyệt trong `tests/test_workspace_case_expert_review.py`
- [ ] T012 [US2] Bổ sung mô hình và migration nhỏ nhất cho yêu cầu/xác nhận chuyên gia trong `src/aios_habit/workspace_case_models.py` và `src/aios_habit/workspace_case_migrations.py`; không tạo hệ quản trị vai trò mới
- [ ] T013 [US2] Thêm thao tác tạo/xác nhận/bác bỏ/yêu cầu thêm bằng chứng qua service hiện có trong `src/aios_habit/workspace_case_service.py`, tái dùng `workspace_case_authorization.py`
- [ ] T014 [US2] Thêm khối xác nhận tiếng Việt ngay trong chi tiết case tại `src/aios_habit/workspace_case_ui.py`; chưa tạo hàng chờ chuyên gia riêng
- [ ] T015 [US2] Chạy test T011, restart/readback, sai scope/sai digest và kiểm tra không có đường update/delete review cũ

## Giai đoạn 4 — Pilot C-call hoặc Jam

**Mục tiêu**: hoàn thành một vụ thật từ log đến kết luận, không tuyên bố chẩn đoán tự động.

- [ ] T016 [P] [US4] Viết test cho timezone Việt Nam, source digest, event `suspected`, không-match trả rỗng và không fallback event gần nhất trong `tests/test_line_log_parser.py`
- [ ] T017 [P] [US4] Viết test timeline, nhóm lặp, câu hỏi còn thiếu, xác nhận relevance và mapping có phiên bản trong `tests/test_workspace_case_line_pilot.py`
- [ ] T018 [US4] Sửa tối thiểu parser tại `src/aios_habit/line_log_parser.py` để đạt T016 mà không thay đổi dữ liệu nguồn
- [ ] T019 [US4] Tạo logic tất định dựng timeline/nhóm lặp/câu hỏi thiếu trong `src/aios_habit/line_investigation_service.py`; chưa dùng model hoặc suy đoán nguyên nhân
- [ ] T020 [US4] Thêm manifest mapping có version và trạng thái duyệt trong `src/aios_habit/line_mapping_service.py`; không hiển thị mapping chưa duyệt
- [ ] T021 [US4] Hiển thị timeline, manh mối, phần thiếu và mapping đã duyệt trong `src/aios_habit/workspace_case_ui.py`
- [ ] T022 [US4] Chạy một pilot C-call hoặc Jam bằng dữ liệu được phép; ghi evidence đã làm sạch, người xác nhận và outcome vào `PROJECT_HANDOVER.md`

## Giai đoạn 5 — Báo cáo và SOP nháp có duyệt

**Mục tiêu**: tạo đúng hai loại đầu ra cần cho pilot, không xây registry tổng quát.

- [ ] T023 [P] [US5] Viết test bản nháp báo cáo/SOP phải có evidence, version, người duyệt; chặn overwrite và đường dẫn bảo vệ trong `tests/test_workspace_case_artifact.py`
- [ ] T024 [US5] Tái dùng `src/aios_habit/agent_draft_sop.py` và thêm `src/aios_habit/workspace_case_report.py` để tạo bản nháp báo cáo điều tra/SOP từ case; không thêm capability registry
- [ ] T025 [US5] Thêm xem trước, chỉnh sửa và duyệt báo cáo/SOP trong `src/aios_habit/workspace_case_ui.py`; sửa sau duyệt phải tạo version mới và duyệt lại
- [ ] T026 [US5] Hoàn tất pilot bằng một báo cáo được người có thẩm quyền duyệt; ghi đường dẫn artifact đã làm sạch và giới hạn còn lại vào `PROJECT_HANDOVER.md`

## Giai đoạn 6 — Đóng đợt vận hành

- [ ] T027 [P] Đồng bộ trạng thái thật của 005, 007 và 008 trong `ROADMAP.md`, tài liệu người dùng và `PROJECT_HANDOVER.md`
- [ ] T028 Chạy `py -3 -m compileall src tests`, toàn bộ `py -3 -m pytest -q`, CLI audit, import Workspace Chat, kiểm tra tài liệu và `git diff --check`
- [ ] T029 Thực hiện kiểm toán độc lập theo tiêu chí Đợt 0/1; chỉ đánh dấu hoàn tất các mục có bằng chứng hiện tại

## Backlog có điều kiện — chưa phải task thực thi

Các mục sau vẫn thuộc US1–US11 trong [spec.md](spec.md), nhưng chưa có ô đánh dấu để tránh tạo cảm giác đang triển khai đồng thời:

| Năng lực | Điều kiện kích hoạt |
|---|---|
| Promotion và tìm lại bài học | Có ít nhất một case thật đã kết luận |
| Hàng chờ chuyên gia nhiều người/phân xử | Pilot phát sinh nhu cầu bàn giao hoặc ý kiến trái chiều thật |
| Artifact ngoài báo cáo/SOP | Có ít nhất ba loại đầu ra thật cần chung một cơ chế |
| Agent lập trình | Có nhu cầu riêng, workspace cách ly, allowlist và người duyệt |
| Kho/model LSU | Data Gate LSU/Iris đạt |
| Scheduler/shadow tự động | Phát lại lịch sử hoặc shadow thủ công ổn định |
| Cảnh báo vận hành | Shadow đạt ngưỡng, có kill switch và chủ sở hữu duyệt |
| NAS nhiều người | Có môi trường thật để thử backup/restore và một writer–nhiều reader |
| Drum/DLP | LSU chứng minh giá trị; mỗi miền có Data Gate riêng |

Khi một điều kiện được đáp ứng, tạo nhóm task nhỏ cho đúng năng lực đó; không khôi phục danh sách 100 task cùng lúc.
