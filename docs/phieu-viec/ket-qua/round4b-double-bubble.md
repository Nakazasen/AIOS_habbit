# Báo cáo ROUND4B-DOUBLE-BUBBLE — sửa lỗi 2 bubble khi hỏi kèm ảnh (máy nhà)

- Trạng thái: **OMP báo xong — chờ Muse duyệt.** Mã + test + cổng repo + 5 điểm nghiệm thu trên app thật đều đạt.
- Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Mã sửa + test: `e900f0c`.
- Ngày: 2026-10-04, 10:38–12:00 +07. Các commit tiến độ theo quy ước: `9c7732f` (nhận vé), `165dd6a` (mã + test xong), `edab7bd` (cổng repo xong).
- Cổng gate: watcher `LAUNCH 1/4` lúc 10:36:14 (`launchStallCount=1`); **điều kiện mở đã tới ngay** (vé CODE, thiết kế Muse chốt sẵn, máy nhà có mã `c317d84`) → nhận vé lúc 10:38. **Không** dùng nhánh “4 lần watcher”/`cho-muse`, không quay no-op.

## Kết luận

Đủ 5 điểm nghiệm thu (mục 3): hỏi kèm ảnh **không còn bubble thứ hai**; trace trỏ đúng bubble gộp OCR; câu không ảnh và cặp câu giống nhau giữ nguyên hành vi cũ (2 bubble riêng). Hướng sửa đúng chỉ đạo: truyền thẳng id tin nhắn đã lưu xuống tầng cầu nối, **không** dùng so khớp tiền tố; thiết kế one-shot-inline giữ nguyên.

## 1. Thay đổi mã (đúng hướng Muse chốt)

- `src/aios_habit/workspace_chat_app.py`:
  - Composer khi submit truyền thêm `user_message_id=user_msg.id` vào `_run_chat_turn_async` (param mới optional).
  - `_run_chat_turn_async` nhận param và chuyển tiếp vào `route_workspace_chat_submission`.
- `src/aios_habit/antigravity_bridge.py`:
  - `route_workspace_chat_submission` thêm param optional `user_message_id`; cả **4 điểm gọi** cũ (dòng 1113/1199/1333/1419 cũ) đổi thành `_get_or_create_user_message(conversation_id, user_raw_input, reuse_message_id=user_message_id)` — chỉ đổi hành vi khi có id.
  - `_get_or_create_user_message` thêm param optional `reuse_message_id`: nếu có và tìm thấy tin nhắn đó trong hội thoại → **trả về luôn, không tạo mới**; không truyền id → giữ nguyên hành vi cũ (khớp đúng tin cuối / tạo mới).
- Không đổi thiết kế one-shot-inline: bubble 1 vẫn hiện câu hỏi + khối OCR như vòng 4.
- Không đụng index, không đổi SHA khối.

## 2. Cổng repo (Python 3.11.14)

- `compileall src tests`: OK.
- `pytest -q` đối chiếu **baseline** (chạy full 2 lượt: có vá và stash-bỏ-vá):
  - With vá: **3978 passed** (+3 test mới) / 37 skipped / 44 failed / 19 errors.
  - Baseline (không vá): 3975 passed / 37 skipped / 44 failed / 19 errors.
  - **0 fail mới, 0 fail cũ đổi** — đối chiếu theo tên từng node: 71/71 giống hệt. 44F/19E là lỗi sẵn môi trường máy này (thiếu file dữ liệu `/home/hatch/...`, DNS, DB test, packaging…).
- `python -m aios_habit.cli audit`: `"status": "PASS"`, `errors`/`warnings` rỗng (chạy kèm `PYTHONPATH=src` theo cách máy này).
- `import aios_habit.workspace_chat_app`: OK. `git diff --check`: sạch.

## 3. Nghiệm thu trên app thật — 5 điểm

Thiết lập: app cổng `8501` (mở 11:16, mở lại 11:41 sau khi xử lý lỗi thao tác môi trường ở mục 6), cầu nối Gemini `127.0.0.1:8585` xanh, hội thoại `CONV-D7ACE777`, nguồn `NGUON-UX-7741` đang bật, ảnh `07-cau1-ocr-fail.png`.

| Lượt | Thời điểm | Câu hỏi | Ảnh | Tin user mới | Trả lời | Trace |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 11:23:40 | câu mặc định khi chỉ có ảnh | có | `MSG-D94F974F` (gộp OCR) | `MSG-5B01F29C` (báo làm nóng bộ đọc) | — |
| S2 | 11:32:55 | câu mặc định khi chỉ có ảnh | có | `MSG-E66F1FC2` (gộp OCR) | `MSG-251FFF1B` (báo làm nóng bộ đọc) | — |
| A | 11:42:49 | chữ gõ lỗi dấu `ỗààì` (lỗi IME công cụ) | có | `MSG-B211026A` (gộp OCR) | `MSG-EF80D96D` | `trc_aab8241cb85e` → `MSG-B211026A` |
| B | 11:46:22 | `lỗi này là gì?` | có | `MSG-DD070867` (gộp OCR) | `MSG-E3A61434` | `trc_c28dac50d665` → `MSG-DD070867` |
| C | 11:47:44 | `lỗi này là gì?` | không | `MSG-U-FA6FD53E` (chữ trơn) | `MSG-A-CAC49A18` | (đường tra cứu lỗi, không có trace cầu nối) |

1. **ĐẠT — hỏi kèm ảnh = đúng 1 bubble, làm 2 lần độc lập.** Bốn lượt gửi ảnh S1/S2/A/B: mỗi lượt store chỉ tăng đúng **1 tin user** (không có bubble trơn trùng như lỗi vòng 4). A và B có câu trả lời thật + trace; S1/S2 (app trước khi mở lại) trả lời bằng thông báo làm nóng nhưng vẫn đúng 1 bubble.
2. **ĐẠT — câu không kèm ảnh = 1 bubble như cũ.** Lượt C: `MSG-U-FA6FD53E`, nội dung chữ trơn `lỗi này là gì?`.
3. **ĐẠT — hai câu liên tiếp giống nhau (câu 2 không ảnh) = 2 bubble riêng, không gộp nhầm.** B (`MSG-DD070867`, bản gộp OCR) và C (`MSG-U-FA6FD53E`, chữ trơn) là hai tin riêng biệt khác id — đúng tinh thần “cấm so khớp tiền tố”.
4. **ĐẠT — trace trỏ đúng bubble gộp OCR.** `trc_aab8241cb85e` → `user_message_id = MSG-B211026A`; `trc_c28dac50d665` → `user_message_id = MSG-DD070867` (cả hai là bubble đã gộp khối OCR).
5. **ĐẠT — bằng chứng ảnh + trích store/trace.** Ảnh: `01-composer-anh-07cau1.png` (composer đã chọn ảnh trước khi gửi), `02-luot-B-1-bubble-gop-ocr.png` (bubble B + khối OCR), `03-luot-C-chu-giong-nhau-bubble-rieng.png` (bubble C chữ trơn tách khỏi B). Trích store/trace ở mục 4.

Chuỗi bằng chứng đếm tin của hội thoại `CONV-D7ACE777`: 2 tin (trước phiên) → S1 +2 (1 user + 1 trả lời) → S2 +2 → A +2 → B +2 → C +2. Mỗi lượt gửi luôn chỉ +1 tin user.

## 4. Trích `local_cases/workspace_chat/messages.jsonl` / `traces.jsonl` (rút gọn)

```
MSG-D94F974F | user | 11:23:40 | 'Phân tích và giải thích nội dung trong ảnh chụp màn hình đính kèm.\n\n---\n[Nội dung chữ đọc được từ ảnh đính kèm "07-cau1-ocr-fail.png"]: …'
MSG-5B01F29C | assistant | 11:27:41 | '⚠️ AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong. …'
MSG-E66F1FC2 | user | 11:32:55 | 'Phân tích và giải thích nội dung trong ảnh chụp màn hình đính kèm.\n\n---\n[Nội dung chữ đọc được từ ảnh đính kèm "07-cau1-ocr-fail.png"]: …'
MSG-251FFF1B | assistant | 11:37:11 | '⚠️ AIOS đã tự làm nóng bộ đọc …'
MSG-B211026A | user | 11:42:49 | 'ỗààì\n\n---\n[Nội dung chữ đọc được từ ảnh đính kèm "07-cau1-ocr-fail.png"]: …'
MSG-EF80D96D | assistant | 11:43:36 | 'Không'
MSG-DD070867 | user | 11:46:22 | 'lỗi này là gì?\n\n---\n[Nội dung chữ đọc được từ ảnh đính kèm "07-cau1-ocr-fail.png"]: …'
MSG-E3A61434 | assistant | 11:46:30 | 'Dựa trên nội dung trong ảnh chụp màn hình `07-cau1-ocr-fail.png` và ngữ cảnh được cung cấp, …'
MSG-U-FA6FD53E | user | 11:47:44 | 'lỗi này là gì?'
MSG-A-CAC49A18 | assistant | 11:47:45 | '**Tra cứu lỗi tương tự** — Tìm thấy 5 ca lỗi liên quan trong 15.707 ca lịch sử. …'
```

```
trc_aab8241cb85e | user_message_id=MSG-B211026A | assistant_message_id=MSG-EF80D96D | created=2026-10-04T04:43:36Z
trc_c28dac50d665 | user_message_id=MSG-DD070867 | assistant_message_id=MSG-E3A61434 | created=2026-10-04T04:46:30Z
```

Ghi chú trung thực: S1/S2 chỉ đính ảnh (chữ gõ chưa kịp chốt vào widget), app dùng câu mặc định khi chỉ có ảnh; lượt A chữ có dấu gõ qua công cụ lái bị lỗi IME (`ỗààì`). Không ảnh hưởng kết luận bubble; lượt B/C đã dùng đúng câu `lỗi này là gì?` cho tiêu chí số 3.

## 5. Test bổ sung

Trong `tests/test_antigravity_bridge.py`, lớp `TestRound4BUserMessageReuse`:

- `test_reuse_id_returns_saved_message_without_duplicate` — có id trỏ tới bản gộp OCR → trả về đúng tin đó, store không tăng.
- `test_without_id_keeps_legacy_behavior` — không id: khớp đúng tin cuối thì tái dùng, không khớp thì tạo mới (hành vi cũ giữ nguyên).
- `test_direct_route_reuses_saved_merged_question` — chạy thật `route_workspace_chat_submission` (mock server direct): store chỉ có 1 tin user, trace trỏ đúng bản gộp.

Cả 3 pass; không sửa/xóa test cũ nào.

## 6. Môi trường & ghi chú thao tác (ngoài phạm vi mã vé)

- Lỗi thao tác phiên: lần mở app đầu tôi dùng `PYTHONPATH=src` (tương đối) → tiến trình worker BGE tách rời (`cwd` khác) không thấy gói → `bge_worker_persist_unavailable`, hai lượt S1/S2 trả về thông báo làm nóng. Mở lại app với PYTHONPATH tuyệt đối (`D:\Sandbox\AIOS_habbit\src`, như `RUN_AIOS_WORKSPACE_CHAT.bat`) là hết. **Không phải lỗi mã vé.**
- Khi lái app bằng công cụ tự động: ô chat chỉ commit giá trị khi blur; chữ có dấu gõ qua công cụ dễ sai IME — đã xử lý trong phiên và ghi lại ở mục 4.
- App đang để mở lại ở cổng `8501` (worker BGE persist đang ấm) cho Muse/user tiện kiểm.

## 7. Index (ràng buộc cấm đụng)

- Không ghi index, không embed, không sửa nguồn. SHA-256 `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`:
  - Sau phiên: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`
  - Vòng 4: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` → **khớp, không đổi**.

Hết.
