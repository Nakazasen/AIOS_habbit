# Báo cáo Phase A [VM] — fix cho-muse vé UX-E2E-APP

- Ngày: 2026-10-03 ~15:35–16:05 +07. Người làm: Muse (VM). Không nhúng, không ghi index.
- Nhánh: `phieu-viec/rag-fix1`. Commit fix: `58d1245` (local `0de46ae`, push qua Git Data API — SHA khác do timestamp, cùng tree). Không đụng `main`, không force-push.

## Lỗi (từ báo cáo OMP `ux-e2e-app.md`)

1. Router chat-first không có ý định "vẽ biểu đồ" → câu gộp chart + ngưỡng chỉ chạy nhánh ngưỡng, phần chart bị bỏ im lặng.
2. Bộ tách ngưỡng nhận từ rác ("trên") làm tên thông số khi câu thiếu tên hợp lệ → lưu quy tắc sai (`CB-D0EDE6`).

## Sửa (3 file src + 2 file test)

1. `src/aios_habit/chat_intent_router.py`: thêm ý định `VE_BIEU_DO` + cụm từ khóa "ve bieu do" (khớp không dấu, không phân biệt hoa thường); loại trừ "bieu do gui mail" (thuộc lệnh cấu hình cảnh báo, không phải vẽ); bổ sung vào `TAT_CA_Y_DINH`, `giai_thich_y_dinh`, `nhan_y_dinh`.
2. `src/aios_habit/workspace_chat_app.py`: `_xu_ly_mot_y_dinh` thêm nhánh `VE_BIEU_DO` gọi `_quyet_dinh_ve_bieu_do` (đúng logic luồng JIG cũ); dữ liệu qua helper chung mới `_hang_ve_tu_lsu_gate()` (đọc `wsc_last_lsu_traces`); PNG nhúng data-URI vào câu trả lời gộp; lỗi → trả `None` (hiện ghi chú "chưa xử lý được", không crash). Closure `_chart_rows` của luồng cũ trỏ về helper chung (gọn, không trùng logic).
3. `src/aios_habit/threshold_alert_chat.py`: `xu_ly_cau_lenh` kiểm tra tên thông số rác (`trên/dưới/vượt/lớn hơn/...`) → trả lời hỏi lại tên thông số, KHÔNG lưu quy tắc.

## Kiểm chứng (VM, Python 3.12.3; code tương thích Python 3.11 — không dùng cú pháp 3.12+)

- `pytest tests/test_chat_intent_router.py tests/test_threshold_alert_chat.py tests/test_chat_action_multi_intent.py tests/test_chat_multi_intent_router_app.py`: **39 passed**.
- Test mới: câu gộp "vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12" → đủ 2 ý định (`canh_bao_nguong`, `ve_bieu_do`); "biểu đồ gửi mail" không rơi vào nhánh vẽ; "đặt ngưỡng trên 12" → hỏi lại + kho quy tắc trống; "đặt ngưỡng nhiệt độ 80" → vẫn lưu bình thường.
- `test_j1_csv.py::test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh` FAIL và `test_mom_local_pilot.py::test_ocr_image_object_rejects_below_confidence_threshold` FAIL — kiểm bằng `git stash` chạy lại trên base: cả 2 fail sẵn (nền máy, không do sửa).
- `compileall` OK.

## Phạm vi cố tình chưa làm (Muse tự quyết theo bằng chứng)

- Nguồn dữ liệu chart JIG hiện chỉ từ phiên LSU gate; nối thêm kho log archive là tính năng mới → vé riêng sau (thông điệp hướng dẫn khi chưa có dữ liệu vẫn đúng, đã được OMP xác nhận ở vé E2E).
- Không đổi hành vi câu chart một mình (vẫn qua đúng `_quyet_dinh_ve_bieu_do` như luồng cũ).

## Tiếp theo

Vé Phase B `UX-E2E-APP-R2` [NHÀ]: OMP verify fix trên app thật (chạy lại mục (a) theo đúng kỳ vọng sau fix + kiểm không regression) và chạy nốt các mục (c)–(h).
