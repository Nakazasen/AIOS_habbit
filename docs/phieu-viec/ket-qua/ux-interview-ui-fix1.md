# Báo cáo vé UX-INTERVIEW-UI-FIX1-VERIFY — verify [NHÀ]

Ngày: 2026-10-03 17:53–18:15 +07. Người làm: OMP (máy `h410asrock`). Không sửa code. Không merge `main`. Không force-push.

## 1. Cổng gate

- Vé yêu cầu commit fix `f521566` là tổ tiên của HEAD nhánh `phieu-viec/rag-fix1`.
- Lúc nhận: HEAD `44b069c`, merge-base với `f521566` chính là `f521566` (2 commit sau). Điều kiện mở đã tới ngay lần kiểm đầu.
- Không đặt `cho-muse`. Không rơi nhánh 4 lần watcher tự mở.

## 2. Cách chạy

- Python `3.11.14` (`.venv`).
- App thử `http://127.0.0.1:8515`, đúng biến môi trường của `RUN_AIOS_WORKSPACE_CHAT.bat`, kể cả `AIOS_FEATURE_CHAT_ACTION=1`.
- Không đụng app người dùng cổng `8501` (PID `5828` giữ nguyên suốt lượt). Cầu nối `8585` (PID `17204`) không tắt.
- Sổ `E2EUxApp` (`NB-922E3730`). Hội thoại mới `CONV-681D501D`.
- Điều khiển UI bằng Chrome headless cục bộ (profile `C:/tmp/fix1-chrome`), gõ thật vào ô chat rồi bấm `Hỏi`. Không F5 giữa các câu.

## 3. Index production

File `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`:

| | Trước | Sau |
|---|---|---|
| Size | `2552659968` | `2552659968` |
| SHA-256 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` |

Không đổi.

## 4. Kết quả từng mục

| Mục | Kết quả | Bằng chứng rút gọn |
|---|---|---|
| 2. Mở phiên F000, câu 1 + ô ngay dưới, không đổi màn | **PASS** | `IS-744426A0`, "Câu 1/3" + 5 ô + "Gửi đáp án" trong bong bóng chat; ô chat vẫn còn |
| 3. Trả lời đủ hết câu, không F5, chữ lưu nháp ổn định + sqlite | **PASS** | Chữ "✅ Đã lưu nháp chờ duyệt (phiên IS-744426A0, 3 đáp án)." giữ sau rerun (8 lần poll, không rơi "hết hạn"). Sqlite 3 đáp án mới, `reviewer_status=cho_chuyen_gia_phan_hoi` |
| 4. Regression mục 1, 2, 4, 5, 6 | **PASS** | Mục 1–2 trên cùng phiên. Mục 4–6 bên dưới. Ô chat cũ còn, không traceback |
| Reload sau khi hoàn thành | **Đúng giới hạn đã ghi** | Widget báo "Phiên phỏng vấn đã hết hạn trong bộ nhớ." Chữ lưu nháp chỉ sống trong cùng phiên trình duyệt |

### Mục 2 và regression mục 1

Lệnh "mở phiên phỏng vấn F000" mở phiên `IS-744426A0`, hiện tượng `F010`, 3 câu. Câu 1 hiện kèm các ô trả lời ngay dưới, không chuyển màn hình.

### Regression mục 2

Bỏ trống "Cơ chế gây lỗi", các ô khác đã điền, nhóm 4M chọn `Man`. App vẫn ở "Câu 1/3" và nhắc:

"Còn thiếu phần nguyên nhân — bổ sung rồi gửi lại nhé. Chi tiết: … thiếu: causal_mechanism (cơ chế gây lỗi)."

Không có cụm "/ bằng chứng" vì ô bằng chứng đã điền. Không qua câu mới.

### Mục 3

Điền đủ câu 1, 2, 3 (không F5). Sau câu cuối, widget hiện ổn định:

"✅ Đã lưu nháp chờ duyệt (phiên IS-744426A0, 3 đáp án)."

Sqlite `local_cases/staging_enrichment.sqlite`, cả 3 dòng `reviewer_status` = `cho_chuyen_gia_phan_hoi`:

- `GA-GQ-1-06-IS-744426A0` / `GQ-1-06` / `2026-10-03T11:08:41.381397+00:00`
- `GA-GQ-1-07-IS-744426A0` / `GQ-1-07` / `2026-10-03T11:08:41.411938+00:00`
- `GA-GQ-1-13-IS-744426A0` / `GQ-1-13` / `2026-10-03T11:08:41.411938+00:00`

### Regression mục 4

Gợi ý cũ "Nạp tài liệu nguồn vào Sổ tri thức." trên sổ này đã được chấm ở vé trước nên widget hiện "Đã ghi nhận", không còn 3 nút — đúng vì mã gợi ý ổn định theo sổ + nội dung.

Để chấm lại đường nút trên cùng sổ `E2EUxApp`, thêm tạm 1 nguồn `SRC-FIX1-VERIFY` (chỉ chữ verify, không phải tài liệu công ty) rồi hỏi lại. Gợi ý mới "Bấm Cập nhật chỉ mục." có 3 nút 👍/😐/👎. Bấm 👎 hiện 3 ô. Lưu khi bỏ trống bị chặn:

"Chấm 'sai' thì phải nhập đủ: lý do, nguyên nhân thật, nội dung nắn lại."

Điền đủ 3 ô thì "Đã ghi nhận đánh giá cho gợi ý này. Cảm ơn chuyên gia." Nguồn tạm đã xóa sau lượt kiểm (sổ trở lại không còn nguồn verify).

### Regression mục 5

Hỏi lại "tiếp theo nên làm gì?" sau khi chê: dòng lưu ý đứng trước gợi ý:

"💡 Lưu ý: tình huống này từng bị chê vì “Goi y khong noi buoc cap nhat chi muc o dau.” — cách đúng là “Chi ro menu cap nhat chi muc truoc khi hoi tiep.”."

Lượt hỏi trước khi thêm nguồn cũng đã thấy dòng lưu ý của lần chê cũ ("Goi y qua chung, khong noi ro cach nap tai lieu.").

### Regression mục 6

"báo cáo cải thiện gợi ý" có dòng:

"📉 Tỉ lệ lặp lại lỗi: 0.0% (kỳ 2026-10-03: 2 lượt bị chê, 0 lượt lặp lại) — xu hướng chưa đủ dữ liệu."

## 5. Cổng lệnh

- `compileall src tests`: OK (Python `3.11.14`, `.venv`, `PYTHONPATH=src`).
- `pytest` liên quan (`tests/test_chat_interview_ui.py`, `tests/test_interview_feedback_loop.py`, `tests/test_suggestion_feedback.py`, `tests/test_chat_action.py`): **75 passed**.
- `PYTHONPATH=src .venv/Scripts/python.exe -m aios_habit.cli audit`: `"status": "PASS"`, `warnings` rỗng. `import aios_habit.workspace_chat_app` được. Trên máy này `uv run` không thấy gói trong `.venv` nếu thiếu `PYTHONPATH` — cùng cách vé `UX-INTERVIEW-UI` đã ghi.

## 6. Kết luận

Mục 3 **ĐẠT**: chữ "Đã lưu nháp chờ duyệt" giữ trên màn sau khi trả lời hết, không còn rơi vào "hết hạn trong bộ nhớ" trong cùng phiên trình duyệt. Sqlite đúng. Các mục regression không vỡ. Index production không đổi.

Dữ liệu test để lại (không commit): 3 đáp án `IS-744426A0` trong `local_cases/staging_enrichment.sqlite`, thêm dòng chấm gợi ý `SG-NEXT-B96C5D011B` trong `local_cases/suggestion_feedback.jsonl` và bài học tương ứng, hội thoại `CONV-681D501D` trong sổ `E2EUxApp`. App thử `8515` đã tắt. App `8501` không đụng.
