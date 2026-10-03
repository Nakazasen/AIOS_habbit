# Vé UX-CHAT-CORE — báo cáo máy nhà

- Ngày: 2026-10-03, khoảng 11:24–11:40 +07.
- Máy: `h410asrock`. Python `3.11.14` (`.venv` của repo).
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`. Không force-push.
- Mã Muse kiểm: `9298ee6` (router chat, dòng trạng thái sổ, cảnh báo ngưỡng) và phụ lục `601a3be`. Các commit đêm trước vẫn nằm trên nhánh: `90d1270` `84fce40` `6190f32` `846713e` `928e242`.
- OMP chỉ verify, không sửa code sản phẩm.
- Index production `local_runs/workspace_chat_rag_v2_production/.../tri_thuc/library.sqlite`: kích thước `2552659968` và mtime không đổi trước/sau. Không ghi index.

## 0. Cổng gate

- Watcher tự mở OMP lần 2/4 lúc 11:22:55 (`launchStallCount=2`). Lần 1/4 lúc 11:11:56 chưa có mã xong.
- Điều kiện mở đã tới: Muse đẩy mã `9298ee6` lúc 11:21:01 và phụ lục bảo kiểm trên app thật `601a3be` lúc 11:21:33.
- OMP nhận vé `dang-lam` (`65a3f95`). Không đặt `cho-muse`. Không quay no-op.

## 1. Kết luận ngắn

**Chưa đủ để gọi là ĐẠT toàn vé.** Phần vỏ chat V2 (bỏ radio, dòng trạng thái sổ, cảnh báo ngưỡng một câu, lane tự chọn khi cầu nối sống) chạy được trên app thật. Phần “một câu ra đủ 3 kết quả” (dán log + vẽ biểu đồ + đặt ngưỡng) **không đạt** trên máy nhà.

## 2. App thật

App cổng `8501` đang chạy từ 11:04, trước mã mới, watcher tắt — không dùng để nghiệm thu. OMP mở bản mã hiện tại ở `http://127.0.0.1:8515` (có `PYTHONPATH=src`). Lần mở thiếu `PYTHONPATH` thì app đổ lỗi `No module named aios_habit` — đã bỏ phiên đó.

Ảnh đính kèm (không có nội dung công ty):

- `docs/phieu-viec/ket-qua/ux-chat-core-anh/01-home.png` — trang đầu, không còn radio “Điều hướng”.
- `docs/phieu-viec/ket-qua/ux-chat-core-anh/04-tao-so.png` — sổ thử vừa tạo, một dòng trạng thái.

Ảnh sổ có câu trả lời tài liệu thật chỉ để đối chiếu tại chỗ, **không đưa vào git**.

### 2.1 Radio 3 nhánh

- Trong `workspace_chat_app.py` không còn `st.radio(`. Không còn chữ “Điều hướng” trên trang.
- Các `role=radio` còn lại trên trang sổ là nút thích/không thích của từng câu trả lời, không phải radio điều hướng.
- Sidebar chỉ còn lời “gõ vào ô chat”. Nút “Dạy AIOS điều tôi biết” vẫn còn — đó không phải radio 3 nhánh.

### 2.2 Ba câu phụ lục

| Câu | Kết quả trên app / mã |
|---|---|
| `cảnh báo khi nhiệt độ vượt 80` | App thật trả lời trong chat: đã lưu quy tắc `CB-6E5F1D`, chưa có dữ liệu thông số này nên không báo ảo. OMP đã xóa file quy tắc thử sau đó (file chỉ có đúng quy tắc này). |
| `tạo sổ BaoCaoTuan` | App tạo và mở sổ `NB-67DB7EFE`. Dòng trạng thái: `Sổ BaoCaoTuan — sẵn sàng, 0 tài liệu`. |
| `mở sổ BaoCaoTuan` | Router tách đúng tên sổ. Thoát trang rồi vào lại: vẫn một dòng sẵn sàng, không bắt “chuẩn bị tài liệu”, không có chữ phần trăm. |
| Câu hỏi tài liệu | Sổ cũ mở lại vẫn hiện câu trả lời đã có. Lane đang chạy: `Đang dùng: Gemini qua cầu nối (tự động)`. Cầu nối lúc đo là sẵn sàng, nên chọn Gemini là đúng. Không tắt cầu nối để thử rơi lane, vì app `8501` của người dùng đang dùng chung cầu nối. |

### 2.3 Dòng trạng thái sổ

- Sổ mới: đúng một dòng `Sổ BaoCaoTuan — sẵn sàng, 0 tài liệu`.
- Sổ cũ trên app: vẫn một dòng sẵn sàng kèm số tài liệu, không có phần trăm, nhưng có thêm tên thư viện trong ngoặc. Phụ lục ghi mẫu không có ngoặc thư viện.

### 2.4 Một câu nhiều ý — chưa đạt

Câu gộp “dán log + vẽ biểu đồ + cảnh báo khi nhiệt độ vượt 80” bị router xếp **chỉ** thành `canh_bao_nguong`. Hàm xử lý ý định trả về đúng rồi dừng, không chạy tiếp phần dán log / vẽ biểu đồ. App thật vì vậy không thể trả đủ 3 kết quả trong một câu.

Đường gộp nhiều ý có trong mã, nhưng:

- Cờ `AIOS_FEATURE_CHAT_ACTION` mặc định tắt. File `RUN_AIOS_WORKSPACE_CHAT.bat` không bật cờ này. App thật theo cách người dùng mở sẽ không chạy đường dán log.
- Khi bật cờ trong kiểm thử, dán CSV để vẽ biểu đồ ném lỗi thiếu `matplotlib`. Cả khối phân tích CSV bị bỏ, không còn bảng thống kê. Máy nhà có Pillow, không có matplotlib. `pyproject.toml` không khai báo matplotlib.
- Dán log chữ (không phải CSV) vẫn ra bảng dòng nghi lỗi, không cần matplotlib.

### 2.5 Cảnh báo ngưỡng và SMA(20)

- Một điểm xấu cuối chuỗi ổn định: không cảnh báo. Test một điểm xấu đạt.
- Chuỗi có xu hướng vượt ngưỡng `[70]*25 + [82, 84, 86, 88, 90]`: có cảnh báo, có chữ SMA(20). Test xu hướng đạt.
- Trên app thật, thông số “nhiệt độ” không có lịch sử nên câu trả lời nói chưa có dữ liệu, không báo giả.

### 2.6 Lane tự chọn

- Không còn selectbox đổi lane. Còn selectbox khác (mức tìm kiếm, cuộc trò chuyện, kho) — không phải đổi lane.
- Khi cầu nối sống: chọn Gemini và ghi “tự động”. Đã thấy trên app thật.
- Khi không có cầu nối / C-Agent / khóa Router: mã chọn cục bộ và nói rõ lý do. Chưa tắt cầu nối trên app đang chạy của người dùng.

### 2.7 Báo lỗi ảo

Muse không để trong mailbox một danh sách case báo lỗi ảo đã sửa. Case đã biết từ commit `928e242` (radio giữ lựa chọn cũ nên bấm “Hỏi tài liệu” không đóng cổng LSU) không còn đường radio đó. OMP không thể khẳng định mọi báo lỗi ảo khác đã hết.

## 3. Cổng lệnh

- `py_compile` Python 3.11 trên file mới/sửa của vé: đạt.
- `compileall` `src` và `tests`: đạt.
- Test liên quan (router, sổ, ngưỡng, đa ý định, dán dữ liệu, lane): **52 đạt, 3 trượt**. Cả 3 trượt vì thiếu matplotlib.
- `python -m aios_habit.cli audit` không có `PYTHONPATH`: lỗi không tìm thấy module. Chạy lại với `PYTHONPATH=src`: `"status": "PASS"`, không warning.
- `import aios_habit.workspace_chat_app`: đạt khi có `PYTHONPATH=src`.
- Bộ `pytest -q` đầy đủ, lần 2, 497,6 giây: **48 failed, 3793 passed, 39 skipped, 19 errors**. Không phải PASS. Phần lớn lỗi/error là nền máy nhà (thiếu file VM `/home/hatch/...`, worker BGE, graphify, khóa mạng), không do vé này.
- Lỗi chạm đúng thay đổi của vé:
  - 3 bài dán CSV: thiếu matplotlib.
  - `test_workspace_chat_composer_ui`: còn tìm selectbox lane cũ và nhãn radio “Hỏi tài liệu” — UI mới đã bỏ hai thứ đó, test chưa cập nhật.
  - `test_workspace_chat_app_wires_lsu_data_gate`: còn tìm tên `wsc_open_lsu_data_gate` đã mất cùng radio.
  - `test_save_case_callback_uses_only_the_existing_trace_and_no_provider`: quét thấy `save_notebook(` trong hàm tạo sổ mới. Đó là ghi sổ chat, không phải ghi index. Test cũ không chờ hàm này.

## 4. Việc OMP để lại trên máy

- Sổ thử `BaoCaoTuan` (`NB-67DB7EFE`) còn trong `local_cases/workspace_chat`. Người dùng xóa nếu không cần.
- Một câu thử “cảnh báo khi nhiệt độ vượt 80” đã ghi vào cuộc trò chuyện đang mở của sổ cũ trước khi OMP chuyển sang sổ thử. Quy tắc JSON đã xóa.
- Không gửi dữ liệu công ty ra ngoài. Không đụng `main`.

## 5. Đề nghị Muse

1. Một câu nhiều ý phải chạy hết các ý, không dừng ở ý cảnh báo.
2. Biểu đồ CSV cần thư viện có sẵn trên Python 3.11 máy nhà (Pillow đã có; matplotlib thì chưa), và không được làm rơi cả bảng thống kê khi vẽ lỗi.
3. Nếu đường dán log phải bật bằng cờ, file mở app máy nhà phải bật cờ đó — nếu không, người dùng mở app vẫn không vẽ được biểu đồ.
4. Chốt danh sách báo lỗi ảo đã sửa, để máy nhà đối chiếu lại từng case.
