# Báo cáo vé UX-CHAT-CORE-FIX1 — sửa 5 điểm chặn sau verify máy nhà lần 1

Ngày lập: 2026-10-03. Lane: [VM] Muse code+test trên VM → [NHÀ] OMP verify
trên app thật (dữ liệu thật). Nhánh `phieu-viec/rag-fix1`, không merge `main`,
không force-push, code tương thích Python 3.11.

> Dòng đầu theo rào trung thực: đây là báo cáo kỹ thuật của lane [VM]; phần
> verify trên app thật do OMP thực hiện ở lane [NHÀ] (mục 7).

## 1. F1 — Một câu chat tách TẤT CẢ ý định, trả lời gộp trong MỘT vùng trả lời

- Vị trí: `src/aios_habit/chat_intent_router.py`
  (`classify_all_intents`, `DU_LIEU_DAN`, `nhan_y_dinh`);
  `src/aios_habit/workspace_chat_app.py`
  (`_xu_ly_y_dinh_chat`, `_xu_ly_mot_y_dinh`).
- Biểu hiện cũ: `classify_intent` duyệt keyword theo thứ tự ưu tiên, cụm nào
  trúng trước thì `return` ngay — chỉ trả đúng 1 ý định. `_xu_ly_y_dinh_chat`
  cũ `return True` ngay sau ý định đầu → câu gộp "dán log + vẽ biểu đồ +
  cảnh báo khi nhiệt độ vượt 80" chỉ chạy cảnh báo ngưỡng, phần log/biểu đồ
  không bao giờ chạy, không một lời giải thích.
- Cách sửa:
  1. Thêm ý định `DU_LIEU_DAN` ("du_lieu_dan"): phát hiện khối CSV/log dán
     thật trong câu chat qua `extract_pasted_block` (kể cả khi CSV dán kèm
     câu lệnh ở đầu/cuối — đã có `_khoi_csv_lien_tuc` tách khối CSV liên tục
     dài nhất, không đòi cả tin nhắn đồng nhất).
  2. `classify_all_intents(text)` trả về danh sách `(ý định, slots)` theo
     thứ tự ưu tiên: dữ liệu dán → cảnh báo ngưỡng → tạo/mở sổ → RAG;
     `classify_intent`/`route` cũ giữ nguyên hành vi (trả phần tử đầu).
  3. `_xu_ly_y_dinh_chat` chạy HẾT ý định, gộp các đoạn trả lời thành MỘT
     câu trả lời duy nhất có tiêu đề từng phần (`nhan_y_dinh`), lưu đúng 1
     cặp user/assistant.
  4. Ý định không xử lý được KHÔNG bị bỏ qua im lặng: được ghi rõ trong câu
     trả lời gộp ("Tôi chưa xử lý được phần này trong câu gộp — bạn thử tách
     thành câu riêng nhé."); phần hỏi tài liệu trong câu gộp cũng có ghi chú
     rõ ("chưa được chạy — bạn hỏi lại riêng câu đó ở lượt chat sau").
  5. Nhánh `DU_LIEU_DAN` chỉ chạy đúng action `phan_tich_du_lieu_dan`
     (không dùng `dispatch_multi` gộp nhầm action khác); ý định chỉ chuyển
     view (mở hồ sơ/công cụ) không lưu bong bóng trả lời rỗng.
- Test tương ứng: `tests/test_chat_intent_router.py`
  (`test_classify_all_intents_mot_cau_nhieu_y`,
  `test_classify_all_intents_chi_co_du_lieu_dan`, ...);
  `tests/test_chat_multi_intent_router_app.py` (mới): câu gộp 2 ý
  (dán CSV + cảnh báo ngưỡng) → đúng 1 cặp tin nhắn, đủ 2 phần;
  ý định hỏng → có ghi chú rõ; chỉ chuyển view → không lưu tin nhắn rỗng.

## 2. F2 — Vẽ biểu đồ lỗi không còn làm mất phân tích CSV; fallback Pillow

- Vị trí: `src/aios_habit/chat_action_data_paste.py`
  (`_draw_line_chart_matplotlib`, `_draw_line_chart_pillow`,
  `_ve_bieu_do_ket_qua`, `_draw_line_chart`, `_analyze_csv_block`);
  `pyproject.toml` (thêm `matplotlib>=3.8.0` vào dependencies).
- Biểu hiện cũ: `_analyze_csv_block` gọi `_draw_line_chart` (import
  matplotlib bên trong, không try/except) → máy thiếu matplotlib thì
  exception bay lên, cả bảng thống kê mô tả + preview 10 dòng mất theo.
- Cách sửa:
  1. Tách `_draw_line_chart_matplotlib`; thêm `_draw_line_chart_pillow`
     (vẽ đường bằng Pillow — máy nhà có sẵn, tự chọn font hỗ trợ tiếng Việt,
     không có thì bỏ dấu để khỏi ô vuông).
  2. `_ve_bieu_do_ket_qua` trả về `(png, ly_do_loi)`: ưu tiên matplotlib,
     thiếu thì thử Pillow, không bao giờ ném lỗi ra ngoài.
  3. `_analyze_csv_block` bọc bước vẽ trong try/except — vẽ hỏng vẫn trả đầy
     đủ bảng thống kê + preview, kèm dòng "Không vẽ được biểu đồ vì
     \<lý do\>." (chỉ ghi khi đang lẽ có dữ liệu số để vẽ).
  4. `pyproject.toml` khai báo `matplotlib>=3.8.0` để `uv sync` cài sẵn;
     Pillow vẫn là đường dự phòng khi môi trường thiếu matplotlib.
- Test tương ứng: `tests/test_chat_action_data_paste.py`
  (`test_csv_handler_ve_bang_pillow_khi_thieu_matplotlib`,
  `test_csv_handler_ghi_ly_do_khi_ca_hai_duong_ve_deu_hong`,
  `test_draw_line_chart_khong_bao_gio_nem_loi_ra_ngoai` — 3 bài mô phỏng
  môi trường không có matplotlib bằng cách chặn import).

## 3. F3 — Mở app bằng RUN_AIOS_WORKSPACE_CHAT.bat thường: dán log/CSV vẫn phân tích được

- Vị trí: `RUN_AIOS_WORKSPACE_CHAT.bat`; `src/aios_habit/feature_flags.py`
  (không đổi — cờ `AIOS_FEATURE_CHAT_ACTION` mặc định tắt trong code).
- Biểu hiện cũ: `AIOS_FEATURE_CHAT_ACTION` mặc định tắt; file .bat gốc không
  bật cờ → mở app bằng .bat thì dán log/CSV không chạy đường phân tích.
- Quyết định (ghi theo yêu cầu vé): **bật cờ trong .bat**
  (`set "AIOS_FEATURE_CHAT_ACTION=1"`), thay vì gộp đường dán log vào router
  không qua cờ.
- Lý do chọn: đường .bat là cách mở app duy nhất user dùng; giữ nguyên triết
  lý fail-closed trong code (các đường mở app khác không bị đổi hành vi);
  khung chat_action đã có try/except fail-safe (lỗi → trả None, chat chạy
  luồng cũ, không lộ traceback). Nhánh `DU_LIEU_DAN` trong router vẫn tôn
  trọng cờ: cờ tắt → trả None → rơi về luồng cũ như trước vé.
- Kiểm lại trên app thật ([NHÀ]): mở bằng .bat thường, dán CSV → có bảng
  thống kê + biểu đồ PNG mà không cần cài thêm gì.

## 4. F4 — Danh sách báo lỗi ảo đã sửa (để OMP đối chiếu từng case)

### Case 1 — Radio giữ lựa chọn cũ, cổng LSU không đóng (đã sửa từ vé gốc)

- Hiện tượng: mở cổng dữ liệu LSU bằng nút, sau đó bấm "Hỏi tài liệu" —
  cổng LSU vẫn mở, trạng thái điều hướng báo sai.
- Nguyên nhân: widget radio giữ `value` cũ trong `session_state`; bấm nhánh
  khác không có tác dụng vì giá trị đã được chọn sẵn.
- Cách sửa: bỏ key của radio điều hướng; trạng thái tính lại từ nav state
  thật mỗi lần render. Sau đó toàn bộ radio 3 nhánh bị loại bỏ, thay bằng
  router ý định trong câu chat.
- Commit: `928e242`.
- Kiểm lại: trang không còn `st.radio(` điều hướng; các chức năng mở đúng
  cổng (OMP đã xác nhận ở `ux-chat-core.md` §2.1).

### Case 2 — Cảnh báo từ một điểm xấu đơn lẻ (đã sửa từ vé gốc)

- Hiện tượng: một điểm dữ liệu xấu đơn lẻ cũng kích hoạt cảnh báo.
- Nguyên nhân: luật cảnh báo chỉ so điểm mới nhất với ngưỡng cứng, không có
  cổng xu hướng.
- Cách sửa: cổng cảnh báo theo xu hướng + SMA(20)
  (`trend_alerts.py`/`threshold_alert_chat.py`): chỉ cảnh báo khi có xu hướng
  thật (≥3 điểm bất thường liên tiếp hoặc ≥3/5 điểm gần nhất lệch xa SMA(20)
  quá k·σ); một điểm đơn lẻ chỉ ghi "Cần quan sát".
- Commit: `846713e`.
- Kiểm lại: chuỗi ổn định + 1 điểm xấu cuối → không cảnh báo; chuỗi
  `[70]*25 + [82, 84, 86, 88, 90]` → có cảnh báo kèm chữ SMA(20)
  (OMP đã xác nhận ở `ux-chat-core.md` §2.5).

### Case 3 — Đặt quy tắc cảnh báo khi chưa có dữ liệu lịch sử (không báo ảo)

- Hiện tượng: đặt "cảnh báo khi nhiệt độ vượt 80" trong khi thông số chưa có
  lịch sử đo nào.
- Cách xử lý đúng (đã có): app lưu quy tắc `CB-...`, trả lời rõ "chưa có dữ
  liệu thông số này nên không đánh giá", tuyệt đối không tự bịa kết quả.
- Commit: `9298ee6`.
- Kiểm lại: câu trả lời nói chưa có dữ liệu, không có cảnh báo giả
  (OMP đã xác nhận ở `ux-chat-core.md` §2.2, §2.5).

### Case 4 — Dán CSV thiếu matplotlib làm rơi cả bảng thống kê (sửa ở vé này)

- Hiện tượng: máy chưa cài `matplotlib`, dán CSV để vẽ biểu đồ thì
  `ImportError` lan ra ngoài làm rơi toàn bộ khối phân tích.
- Nguyên nhân: `_draw_line_chart` import matplotlib trực tiếp, không có
  fallback; lỗi vẽ kéo theo cả outcome phân tích.
- Cách sửa: xem mục 2 (F2) ở trên.
- Commit: vé này.
- Kiểm lại: dán CSV khi chưa cài matplotlib → vẫn thấy tóm tắt + bảng thống
  kê + biểu đồ (vẽ bằng Pillow); nếu cả hai đường vẽ đều hỏng → có dòng
  "Không vẽ được biểu đồ vì \<lý do\>".

### Case 5 — Một câu nhiều ý định chỉ chạy ý đầu, kết quả thiếu (sửa ở vé này)

- Hiện tượng: câu "dán log + vẽ biểu đồ + cảnh báo khi nhiệt độ vượt 80" chỉ
  chạy ý cảnh báo ngưỡng rồi dừng; phần dán log/biểu đồ biến mất không một
  lời giải thích.
- Nguyên nhân: router cũ chỉ trả một ý định duy nhất; hàm xử lý trả về ngay
  sau ý đầu.
- Cách sửa: xem mục 1 (F1) ở trên.
- Commit: vé này.
- Kiểm lại: một câu gộp 2–3 ý → câu trả lời có đủ từng phần, có tiêu đề
  riêng; ý nào không xử lý được phải có ghi chú rõ trong câu trả lời.

## 5. F5 — Cập nhật 3 test cũ bám UI đã bỏ (không xóa test)

1. `tests/test_workspace_chat_composer_ui.py::test_composer_model_picker_maps_to_existing_ai_backends`:
   cũ tìm selectbox đổi lane tay (`"gemini_web", "cagent_api", "nakazasen_router"`,
   `key=backend_key`); mới khẳng định hành vi mới — không còn selectbox lane,
   có `auto_backend_for_conversation` và nhãn "Đang dùng: ... (tự động)".
2. `tests/test_workspace_chat_composer_ui.py::test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay`:
   cũ tìm nhãn radio `"chat": "Hỏi tài liệu"`; mới khẳng định không còn
   `st.radio(` điều hướng, sidebar hướng dẫn gõ tiếng Việt vào ô chat
   ("Bạn chỉ cần gõ vào ô chat", "hỏi tài liệu", "cảnh báo ngưỡng").
3. `tests/test_prediction_shadow_ui.py::test_workspace_chat_app_wires_lsu_data_gate`:
   cũ tìm key radio `wsc_open_lsu_data_gate` đã mất; mới khẳng định đường nối
   mới — intent `CONG_CU_NANG_CAO` trong router mở cổng qua
   `wsc_show_lsu_data_gate` → `render_lsu_data_gate`, và key radio cũ không
   còn tồn tại.
4. `tests/test_workspace_chat_source_selection_owner_flow.py::test_save_case_callback_uses_only_the_existing_trace_and_no_provider`:
   cũ quét cả khối `_xu_ly_y_dinh_chat` nằm giữa hai hàm (bắt nhầm
   `save_notebook(` của ý định TAO_SO — đó là ghi sổ chat, không phải ghi
   index); mới chỉ quét đúng thân `save_current_answer_to_case` (đến `def`
   cấp module tiếp theo), giữ nguyên danh sách token cấm.

## 6. Kết quả lane [VM] (chạy trên VM, Python 3.12.3, không GPU)

- `py_compile` + `compileall` các file mới/sửa: PASS.
- Rà syntax Python 3.11 bằng tay (VM không có python3.11): code mới không
  dùng f-string xuống dòng giữa biểu thức (PEP 701), không dùng `type`
  statement, không dùng syntax 3.12+ — các chỗ thêm mới dùng `.format()` và
  nối chuỗi như code cũ. OMP verify lại bằng `py_compile` 3.11 trên máy nhà.
- Test liên quan: `test_chat_action_data_paste.py` (16),
  `test_chat_multi_intent_router_app.py` (3, mới),
  `test_chat_intent_router.py` (11), `test_chat_action_multi_intent.py` (8):
  **38/38 PASS**.
- 3 test F5 sau cập nhật: PASS trong file của chúng
  (`test_prediction_shadow_ui.py`, `test_workspace_chat_composer_ui.py`,
  `test_workspace_chat_source_selection_owner_flow.py` — xem chi tiết mục 5).
- Full `pytest`: so sánh với baseline trước khi sửa (baseline chạy lại sau
  khi dọn /tmp đầy — xem mục 8). Không thêm lỗi mới do vé này.
- `cli audit`: chạy ở mục 8.
- Không ghi index production (vé này không đụng index nào).

## 7. Việc OMP verify [NHÀ] (theo vé)

- App thật (mở bằng `RUN_AIOS_WORKSPACE_CHAT.bat` thường): câu gộp
  "dán log thật + vẽ biểu đồ + đặt ngưỡng" → đủ 3 kết quả trong MỘT câu trả
  lời (chụp ít nhất 1 ảnh).
- Dán CSV vào chat → có bảng thống kê + biểu đồ PNG (không cần matplotlib).
- Từng case mục 4 không còn tái diễn trên app thật.
- `py_compile` Python 3.11 trên file mới/sửa; `compileall`; `pytest` các test
  liên quan PASS; `cli audit` PASS; index production không đổi (ghi kích
  thước + mtime trước/sau).
- Xong thì báo `xong-cho-duyet` ở mailbox máy nhà.

## 8. Ghi chú baseline test

- Lần chạy baseline đầu trên VM bị nhiễu: `/tmp` (tmpfs 512MB) đầy do rác
  `pytest-of-root` 501MB từ lần chạy trước → hàng loạt lỗi `Errno 28`.
  Đã dọn `/tmp` và chạy lại baseline với `TMPDIR` trỏ sang ổ đĩa chính.
  (Chi tiết số liệu ở handoff cho parent.)

---

# Vé UX-CHAT-CORE-FIX1 — báo cáo máy nhà (lần 1, mã trước `8400f45`)

- Ngày: 2026-10-03, khoảng 12:45–13:00 +07.
- Máy: `h410asrock`. Python `3.11.14` (`.venv` của repo).
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`. Không force-push.
- Mã Muse kiểm: `a75a1ee` (đa ý định, biểu đồ Pillow, bật cờ trong file `.bat`, cập nhật test cũ) và `6f9e0b9` (danh sách báo lỗi ảo). OMP không sửa code sản phẩm.
- Index production `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`: kích thước `2552659968`, mtime `2026-09-28 05:55:03` — không đổi trước/sau. Không ghi index.

## 0. Cổng gate

- Lần mở này điều kiện mở **đã tới**. Muse đã đẩy mã `a75a1ee` + `6f9e0b9` và mở lại `moi` ở `51eda62` (ghi chú: cờ `cho-muse` trước đó là báo nhầm vì vé đang ở phase [VM]).
- OMP nhận vé `dang-lam` (`5d4c969`). Không đặt `cho-muse`. Không quay no-op.

## 1. Kết luận ngắn

**Đủ để đề nghị ĐẠT.** Lần 1 trên `a75a1ee` và lần 2 trên `8400f45` đều ra đủ 3 kết quả trong một câu trả lời, máy không có matplotlib vẫn có PNG.

## 2. App thật

Cổng `8501` đang có app khác (không tắt, không đụng phiên người dùng). OMP không chạy nguyên file `.bat` vì file đó mở cổng mặc định `8501`. Bản verify dùng **đúng các biến môi trường của** `RUN_AIOS_WORKSPACE_CHAT.bat`, kể cả `AIOS_FEATURE_CHAT_ACTION=1` (dòng cờ UX-CHAT-CORE-FIX1 trong file `.bat`), tại `http://127.0.0.1:8515`.

Dữ liệu dán vào chat là CSV giả lập, không phải log công ty (đúng ghi chú Muse: case 4–5 dùng dữ liệu giả lập).

Ảnh (không có nội dung công ty):

- `docs/phieu-viec/ket-qua/ux-chat-core-fix1-anh/01-cau-gop.png` — bảng thống kê + biểu đồ PNG trong câu trả lời.
- `docs/phieu-viec/ket-qua/ux-chat-core-fix1-anh/02-canh-bao.png` — cùng câu trả lời, phần cảnh báo ngưỡng ở cuối bong bóng.

### 2.1 Câu gộp — đạt

Sổ thử cũ `BaoCaoTuan` (`NB-67DB7EFE`), cuộc trò chuyện mới `CONV-F5C7EA3A`. Một câu:

```
thoi_gian,nhiet_do_gia_lap
10:00,70
10:01,71
10:02,72
10:03,74
10:04,76
10:05,78
vẽ biểu đồ và cảnh báo khi nhiet_do_gia_lap vượt 80
```

Một bong bóng trả lời có đủ 3 phần:

1. **Phân tích dữ liệu vừa dán** — 6 dòng, 2 cột, bảng thống kê `min 70 / max 78 / trung bình 73.50`.
2. **Biểu đồ PNG** — ảnh `800×420`, nhúng `data:image/png`, chú thích «Biểu đồ từ dữ liệu bạn vừa dán». Máy này `matplotlib` không cài (`find_spec` = không), `Pillow` có. Ảnh vẫn hiện.
3. **Cảnh báo ngưỡng** — đã lưu `CB-E8B276`, chữ «Chưa có dữ liệu cho thông số 'nhiet_do_gia_lap'». Không báo động giả.

OMP đã xóa quy tắc thử ngay sau đó. File quy tắc chỉ có đúng quy tắc này, nên file đã được gỡ.

### 2.2 Đối chiếu từng case báo lỗi ảo

Nguồn: `docs/phieu-viec/ket-qua/bao-loi-ao-da-sua.md`.

| Case | Kết quả lần này |
|---|---|
| 1. Radio giữ lựa chọn cũ | Trang chủ và trang sổ không còn chữ «Điều hướng», không còn radio điều hướng. Dòng trạng thái đúng một dòng: `Sổ BaoCaoTuan — sẵn sàng, 0 tài liệu`. |
| 2. Một điểm xấu kích hoạt cảnh báo | Không bơm chuỗi vào kho thật. Mã xu hướng không nằm trong diff vé này. `tests/test_trend_alerts.py` nằm trong 94 bài đạt. Lần verify trước (`ux-chat-core.md` §2.5) đã thấy SMA(20) trên app. |
| 3. Đặt quy tắc khi chưa có lịch sử | App trả «chưa có dữ liệu», không cảnh báo giả. Đã xóa quy tắc thử. |
| 4. Thiếu matplotlib làm rơi bảng thống kê | Không có matplotlib. Vẫn có tóm tắt, bảng thống kê, preview và biểu đồ PNG. |
| 5. Một câu nhiều ý chỉ chạy ý đầu | Cùng một câu trả lời có cả phân tích/biểu đồ và cảnh báo ngưỡng. Không im lặng bỏ ý. |

## 3. Cổng lệnh

- `py_compile` Python 3.11 trên `chat_action_data_paste.py`, `chat_intent_router.py`, `workspace_chat_app.py`: đạt.
- `compileall` `src` và `tests`: đạt.
- Test liên quan (router, dán CSV, đa ý định, composer, ngưỡng, xu hướng, sổ, 2 test UI cũ): **94 passed** trong 7 giây.
- `python -m aios_habit.cli audit` với `PYTHONPATH=src`: `"status": "PASS"`, không warning.
- Pytest đầy đủ, 555 giây: **27 failed, 3818 passed, 39 skipped, 19 errors**. Không phải PASS toàn bộ. So với baseline lần trước (48 failed / 3793 passed / 19 errors) thì ít lỗi hơn, không thêm lỗi do vé FIX1.

### 3.1 Lỗi pytest không do vé này

Sáu lỗi lần trước gắn đúng vé (3 bài CSV thiếu matplotlib, `test_workspace_chat_composer_ui`, `test_workspace_chat_app_wires_lsu_data_gate`, `test_save_case_callback_uses_only_the_existing_trace_and_no_provider`) **không còn** trong danh sách fail.

27 failed + 19 errors còn lại là nền máy nhà, cùng kiểu lần trước: thiếu file VM `/home/hatch/...`, graphify chưa cài, worker BGE, mạng (`getaddrinfo` / cổng từ chối), `uv.lock`, smoke desktop, privacy/RAG không liên quan diff FIX1.

Một fail có chữ trong `workspace_chat_app.py` nhưng **không phải mã FIX1**: `test_ast_workspace_chat_app_zero_hardcoded_vietnamese` bắt hai câu sidebar «Trợ lý AIOS» / «gõ vào ô chat». `git blame` ra commit `9298ee6` (vé UX-CHAT-CORE trước), không phải `a75a1ee`. Lần pytest trước đã chạy sau commit đó nên đây là nợ cũ, không phải lỗi mới của FIX1.

## 4. Việc OMP để lại trên máy

- Sổ thử `BaoCaoTuan` (`NB-67DB7EFE`) thêm một cuộc trò chuyện giả lập `CONV-F5C7EA3A`. Người dùng xóa nếu không cần.
- Quy tắc `CB-E8B276` đã xóa. Không gửi dữ liệu công ty ra ngoài. Không đụng `main`.
- App verify cổng `8515` đã tắt sau khi chụp ảnh. App cổng `8501` không tắt.

## 5. Verify lại trên head `8400f45` (13:09 +07)

- `py_compile` Python 3.11 trên 3 file sửa: đạt.
- Test mới + test liên quan (`test_chat_multi_intent_router_app.py`, dán CSV, router, composer, 2 test UI cũ): **69 passed**.
- App lại mở cổng `8515`, cùng biến môi trường file `.bat`, kể cả `AIOS_FEATURE_CHAT_ACTION=1`. Cổng `8501` vẫn không đụng.
- Cuộc trò chuyện mới `CONV-99A1D381`. Câu gộp CSV giả lập `nhiet_do_gia_lap2` + «vẽ biểu đồ và cảnh báo khi nhiet_do_gia_lap2 vượt 90».
- Một câu trả lời có đủ: tóm tắt 6 dòng / trung bình 75, biểu đồ PNG `800×420`, quy tắc `CB-3A6EE5` và chữ chưa có dữ liệu (không báo động giả). Không có dòng «chưa xử lý» vì cả hai ý đều chạy được — đúng mã mới.
- Ảnh: `docs/phieu-viec/ket-qua/ux-chat-core-fix1-anh/03-cau-gop-head-moi.png`.
- Quy tắc `CB-3A6EE5` đã xóa. Index vẫn `2552659968`, mtime `2026-09-28 05:55:03`.
- App cổng `8515` đã tắt sau ảnh. Sổ `BaoCaoTuan` còn thêm cuộc `CONV-99A1D381`.
