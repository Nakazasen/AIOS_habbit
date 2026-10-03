# Vé: UX-CHAT-CORE-FIX1 — sửa 5 điểm chặn sau verify máy nhà lần 1

Lane: [VM] Muse code+test trên VM → [NHÀ] OMP verify trên app thật (dữ liệu thật). Không merge `main`; code tương thích Python 3.11; không force-push.

## Verdict lần 1 (CHƯA ĐẠT — 2026-10-03 ~12:00 +07, Muse verify độc lập code)

Báo cáo OMP: `docs/phieu-viec/ket-qua/ux-chat-core.md` (commit `9142fff`). **Giữ phần đạt:** bỏ radio "Điều hướng"; dòng trạng thái sổ đúng 1 dòng; cảnh báo ngưỡng + SMA(20) chạy đúng trên app thật; `py_compile` 3.11 + `compileall` + `cli audit` PASS; index production không đổi.

## 5 điểm chặn (bằng chứng độc lập từ code trên nhánh)

**F1. Router chỉ xử lý 1 ý định.** `src/aios_habit/chat_intent_router.py::classify_intent` duyệt keyword theo thứ tự ưu tiên, cụm nào trúng trước thì `return` ngay — chỉ trả về ĐÚNG 1 ý định. `_dieu_huong_chat_first` (`workspace_chat_app.py`, ~dòng 1470) `return True` ngay sau khi xử lý ý định đầu → câu gộp "dán log + vẽ biểu đồ + cảnh báo khi nhiệt độ vượt 80" chỉ chạy cảnh báo ngưỡng, phần log/biểu đồ không bao giờ chạy.
Yêu cầu: một câu chat tách được TẤT CẢ ý định, chạy hết, trả lời gộp có cấu trúc trong MỘT vùng trả lời (đúng spec gốc vé UX-CHAT-CORE mục 1). Thứ tự xử lý gợi ý: dán log/CSV (phân tích + biểu đồ) → cảnh báo ngưỡng → tạo/mở sổ → RAG hỏi tài liệu. Nếu một ý định không xử lý được thì ghi rõ trong câu trả lời gộp, không im lặng bỏ qua. Thêm test đa ý định (2–3 ý/câu) trên VM.

**F2. Vẽ biểu đồ lỗi thì mất cả phân tích CSV.** `src/aios_habit/chat_action_data_paste.py::_analyze_csv_block` gọi `_draw_line_chart` (import matplotlib BÊN TRONG hàm, dòng ~154, không try/except) → máy thiếu matplotlib thì exception bay lên, cả bảng thống kê mô tả + preview 10 dòng mất theo.
Yêu cầu: (a) bọc bước vẽ trong try/except — vẽ hỏng vẫn trả đầy đủ bảng thống kê + preview, kèm dòng chữ "không vẽ được biểu đồ vì <lý do>"; (b) vẽ bằng Pillow (`pyproject.toml` đã khai báo `Pillow>=10.0.0`, máy nhà có sẵn) thay vì bắt buộc matplotlib; giữ matplotlib làm đường ưu tiên NẾU đã cài (không bắt buộc). Test 3 bài dán CSV phải pass trên môi trường không có matplotlib.

**F3. Cờ chat_action tắt theo cách mở app thường.** `src/aios_habit/feature_flags.py:36` — `AIOS_FEATURE_CHAT_ACTION` mặc định tắt; `RUN_AIOS_WORKSPACE_CHAT.bat` (gốc repo) không bật cờ này → người dùng mở app bằng file .bat thì dán log/CSV vào chat không chạy đường phân tích.
Yêu cầu: sau vé này, mở app bằng `RUN_AIOS_WORKSPACE_CHAT.bat` thường thì dán log/CSV vẫn phân tích + vẽ biểu đồ được. Cách làm do Muse quyết (bật cờ trong .bat là đường đơn giản nhất; hoặc gộp đường dán log vào router không qua cờ) — phải fail-safe và ghi rõ quyết định trong báo cáo vé.

**F4. Chưa có danh sách báo lỗi ảo đã sửa.** OMP không đối chiếu được.
Yêu cầu: liệt kê TỪNG case vào báo cáo vé `docs/phieu-viec/ket-qua/ux-chat-core-fix1.md` — vị trí file/hàm, biểu hiện cũ, cách sửa, test tương ứng. OMP đối chiếu lại từng case trên app thật.

**F5. Test cũ bám UI đã bỏ.** `test_workspace_chat_composer_ui` (tìm selectbox lane + nhãn radio "Hỏi tài liệu"), `test_workspace_chat_app_wires_lsu_data_gate` (tìm tên `wsc_open_lsu_data_gate` đã mất), `test_save_case_callback_uses_only_the_existing_trace_and_no_provider` (quét `save_notebook(` trong hàm tạo sổ — đó là ghi sổ chat, không phải ghi index).
Yêu cầu: cập nhật assertion theo UI mới; CẤM xóa test để cho qua. Sau sửa, full `pytest` không còn lỗi nào do vé này gây ra (lỗi nền máy nhà thiếu file VM/worker/mạng được phép liệt kê riêng có bằng chứng baseline).

## Việc OMP verify [NHÀ]

- App thật (mở bằng `RUN_AIOS_WORKSPACE_CHAT.bat` thường): câu gộp "dán log thật + vẽ biểu đồ + đặt ngưỡng" → đủ 3 kết quả trong MỘT câu trả lời.
- Dán CSV vào chat → có bảng thống kê + biểu đồ PNG (không cần matplotlib).
- Từng case báo lỗi ảo trong danh sách F4 không còn tái diễn.
- `py_compile` Python 3.11 trên file mới/sửa; `compileall`; `pytest` các test liên quan PASS; `cli audit` PASS; index production không đổi (ghi kích thước + mtime trước/sau).
- Báo cáo `docs/phieu-viec/ket-qua/ux-chat-core-fix1.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- F1–F5 xong, có bằng chứng trên app thật (ít nhất 1 ảnh câu gộp ra đủ 3 kết quả trong 1 câu trả lời).
- Test liên quan PASS; full pytest không thêm lỗi mới do vé này.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.

Rào: không ghi index production, không merge main, không gửi dữ liệu công ty ra ngoài, code tương thích Python 3.11.

## Bổ sung 2026-10-03 ~12:45 — code [VM] ĐÃ XONG, OMP verify
- Commit `a75a1ee`: multi-intent (classify_all_intents, chạy hết ý, gộp trả lời), matplotlib vào pyproject + wrapper không ném lỗi (fallback Pillow), bật `AIOS_FEATURE_CHAT_ACTION=1` trong `RUN_AIOS_WORKSPACE_CHAT.bat`, cập nhật 3 test cũ theo UI mới.
- Commit `6f9e0b9`: `docs/phieu-viec/ket-qua/bao-loi-ao-da-sua.md` — 5 case báo lỗi ảo để đối chiếu.
- OMP verify: chạy app bằng `RUN_AIOS_WORKSPACE_CHAT.bat`; câu gộp "dán log + vẽ biểu đồ + cảnh báo" phải ra đủ 3 phần; dán CSV giả lập phải có biểu đồ (không cần matplotlib cài tay); đối chiếu 5 case báo lỗi ảo; `py_compile` Python 3.11.
