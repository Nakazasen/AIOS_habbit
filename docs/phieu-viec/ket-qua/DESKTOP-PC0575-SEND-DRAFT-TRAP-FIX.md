Model thực hiện: Gemini 4 Argon (Medium Thinking)

# BÁO CÁO NGHIỆM THU VÉ `DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX`

- **Mã vé**: `DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX`
- **Mã hội thoại thực hiện**: `4194a1f0-00c8-4586-9712-e9fbf8cf936c`
- **Máy đích**: `PC0575` (máy công ty)
- **Model thực hiện**: `Gemini 4 Argon (Medium Thinking)`
- **Môi trường Python**: `Python 3.11.15` (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`)
- **Nhánh mã nguồn**: `phieu-viec/rag-fix1`
- **Commit mã nguồn (SHA đầy đủ 40 ký tự)**: `8a888c496c776d11a03973548807c5d0033f43b6` (parent: `b7296720a7fd6de32cccb897b8da566abdb78d6e`)
- **Giờ đóng phiên thật**: `2026-10-22T20:30:10+07:00` (`2026-10-22T13:30:10Z`)
- **Xác nhận đọc `ghi_chu 19:05` và thứ tự chạy**: Đã đọc toàn văn tệp vé `hop-thu/lan-desktop-pc0575/DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX.md` cùng khối `ghi_chu` bổ sung lúc `19:05` ở đầu tệp (mở rộng phạm vi kích hoạt bẫy nháp ngay trong luồng gõ -> bấm Gửi thông thường + đóng tab mở lại tab mới). Xác nhận chạy đúng thứ tự: **SAU KHI** vé `DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX` đã đóng (`da-dong` lúc `2026-10-22T12:01:27.350Z`) và **TRƯỚC** vé `DESKTOP-PC0575-SYNC-R10-REALUI-GATES` (giữ nguyên trạng thái `cho-slot`, không chạm vào tệp của vé đó).

---

## 1. Chi tiết sửa mã nguồn (`src/aios_habit/workspace_chat_app.py` và `src/aios_habit/workspace_chat_ui.py`)

### 1.1. Sửa 3 điểm khóa nhau của bẫy nháp (Send Draft Trap)
1. **Điểm (1) — Callback gửi (`_on_chat_submit`, `src/aios_habit/workspace_chat_app.py`)**:
   - Ngay khi nhận câu hỏi từ ô nhập (`st.session_state[_input_key]`), xóa luôn bản nháp `st.session_state.pop(f"wsc_draft_text_{active_conversation.conversation_id}", None)` và đặt cờ `st.session_state[f"wsc_clear_input_{active_conversation.conversation_id}"] = True` cùng với xóa `st.session_state[_input_key] = ""` và đặt `st.session_state["wsc_submitting_ack"]`.
2. **Điểm (2) — Nhánh khôi phục nháp (`src/aios_habit/workspace_chat_app.py`)**:
   - Trước khi khôi phục `draft_backup_key` vào lại `input_key`, kiểm tra xem có đang tồn tại `wsc_submitting_ack` chưa xử lý của chính hội thoại đó hay không (`_pending_ack_for_conv`).
   - Nếu đang có ack chờ xử lý cho hội thoại hiện tại: **tuyệt đối không khôi phục nháp** vào `input_key`, đồng thời dọn sạch `st.session_state.pop(draft_backup_key, None)` để bản nháp cũ không thể tái nhiễm ở lượt chạy lại kế tiếp.
   - Nếu không có ack chờ xử lý: giữ nguyên hành vi khôi phục nháp bình thường khi người dùng đổi ô chọn kho hoặc chuyển chế độ tra cứu.
3. **Điểm (3) — Cổng kích hoạt ack (`src/aios_habit/workspace_chat_app.py`)**:
   - Bỏ điều kiện phụ khóa chết `and not user_input.strip()` tại cổng tiêu thụ `_current_submitting_ack`.
   - Khi có `_current_submitting_ack` hợp lệ (`_current_submitting_ack.get("q_text")`), bắt buộc lấy `user_input = str(_current_submitting_ack.get("q_text") or "")`, đặt `ask_submitted = True`, và xóa luôn `draft_backup_key` (`st.session_state.pop(draft_backup_key, None)`).

### 1.2. Rà soát toàn bộ các điểm tiêu thụ ack và các đường gửi khác
Đã rà soát toàn bộ chuỗi xử lý sau cổng `if ask_submitted and user_input.strip():` trong `src/aios_habit/workspace_chat_app.py`:
- **Cổng `is_workspace_chat_worker_warmed` (hàng đợi khi bộ đọc đang nạp)**: Trước đây chỉ xóa `wsc_submitting_ack` khi cất câu hỏi vào `wsc_queued_question_*`. Đã bổ sung xóa luôn `st.session_state.pop(draft_backup_key, None)` trước khi `safe_rerun()` để khi worker ấm xong và lấy câu hỏi từ hàng đợi ra chạy, bản nháp cũ không còn cơ hội điền ngược vào ô nhập.
- **Đường lệnh bộ nhớ (`parse_memory_command`)**: Đã tiêu thụ và xóa cả `wsc_submitting_ack` lẫn `draft_backup_key` trước khi `safe_rerun()`.
- **Đường ý định hành động (`_xu_ly_y_dinh_chat`: tạo vụ, phản hồi, đóng vụ, phân loại)**: Đi qua cùng cổng `ask_submitted`, ở cuối khối xử lý đều gọi `st.session_state.pop("wsc_submitting_ack", None)` và `st.session_state.pop(draft_backup_key, None)` đồng bộ.
- **Đường JIG chat (`handle_jig_chat_text`), đường chat thường (`handle_chat_text`), đường `agent_intent` và `log_chart`**: Đều nằm dưới cùng cổng `ask_submitted` đã mở khóa; sau khi lưu câu hỏi vào `messages.jsonl` và hoàn tất lượt trả lời, đều xóa sạch cả `wsc_submitting_ack` và `draft_backup_key`.

### 1.3. Tự nạp 5 biến môi trường chuẩn bằng `os.environ.setdefault`
Ngay đầu tệp `src/aios_habit/workspace_chat_app.py` (trước khi import các adapter và module truy hồi), đã đặt `os.environ.setdefault` theo đúng giá trị trong `RUN_AIOS_WORKSPACE_CHAT.bat` (không ghi đè giá trị nếu môi trường đã đặt sẵn):
- `AIOS_RAGV2_WORKER_PERSIST="1"`
- `AIOS_DOMAIN_ROUTING_ENABLED="1"`
- `AIOS_RAG_V2_NUMPY_DENSE="1"`
- `AIOS_BGE_INIT_TIMEOUT="420"`
- `AIOS_BGE_QUERY_TIMEOUT="1200"`

### 1.4. Hòa giải hiển thị bước chờ trung thực với vé `DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX`
- Trong `src/aios_habit/workspace_chat_ui.py` (`build_answer_wait_steps`):
  - Giữ nguyên cơ chế `step_timings` của vé `LIVENESS` khi đã có tiến độ thật từ luồng xử lý.
  - Ở nhánh fallback khi chưa có `step_timings` (`step_timings is None`), sửa trạng thái `"dang_xu_ly"` từ `dang_chay = 2` (gán cứng bước 3) về `dang_chay = 0` (bước 1 `● Tìm nguồn`, bước 2 `○ Đọc trích đoạn`, bước 3 `○ Tổng hợp trả lời`).
- Trong `src/aios_habit/workspace_chat_app.py` (nhánh hiển thị hộp chờ của `wsc_submitting_ack` khi `_live_stream` chưa kịp khởi tạo trên luồng nền):
  - Khởi tạo `step_timings_snap` ban đầu với `find: {"status": "running", "elapsed_s": ...}`, `read: {"status": "pending", "elapsed_s": 0.0}`, `synth: {"status": "pending", "elapsed_s": 0.0}` thay vì để `None` rơi vào bước 3.
  - Cập nhật `tests/test_workspace_chat_composer_ui.py` đồng bộ với kỳ vọng trung thực: khi vừa ở trạng thái `dang_xu_ly` ban đầu (chưa có `step_timings`), bước đang chạy là `● Tìm nguồn`, không bao giờ khai khống `● Tổng hợp trả lời`.

---

## 2. Kết quả kiểm thử tự động trên Python 3.11.15 (Cổng 4a & 4d)

- **Môi trường chạy**: `D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe` (`Python 3.11.15`).
- **Tệp kiểm thử mới**: `tests/test_send_draft_trap_fix.py` (5 bài kiểm thử bao phủ: (1) tái hiện chuỗi bẫy nháp `draft_backup_key` + `wsc_submitting_ack` trước/sau vá; (2) nhánh khôi phục nháp bình thường khi không có ack; (3) callback `_on_chat_submit` xóa `draft_backup_key`; (4) `os.environ.setdefault` đủ 5 biến không ghi đè giá trị có sẵn; (5) `build_answer_wait_steps` trung thực ở trạng thái ban đầu và hòa giải với `step_timings` của `LIVENESS`).
- **Kết quả TRƯỚC khi vá mã**:
  - Chạy `pytest tests/test_send_draft_trap_fix.py`: **5 FAILED in 1.54s** (tái hiện đúng lỗi: `draft_backup_key` ghi đè lại `input_key`, cổng `not user_input.strip()` chặn `ask_submitted`, câu hỏi bị nuốt mất, hộp chờ nhảy thẳng lên `● Tổng hợp trả lời`).
- **Kết quả SAU khi vá mã**:
  - Chạy bộ kiểm thử tổng hợp 5 tệp (`tests/test_send_draft_trap_fix.py`, `tests/test_workspace_chat_composer_ui.py`, `tests/test_cagent_liveness_wait_ux.py`, `tests/test_workspace_chat_send_ack_client_instant.py`, `tests/test_question_suggestions.py`): **82 passed in 7.63s**.
  - Chạy kiểm thử trạng thái chỉ mục (`tests/test_index_status.py`): **13 passed in 0.87s**.

---

## 3. Khởi động lại dịch vụ bằng `RUN_AIOS_WORKSPACE_CHAT.bat` & Dòng trạng thái chỉ mục (Mục 2.6)

- Đã dừng tiến trình cũ và khởi động lại ứng dụng tại cổng `8501` bằng đúng tệp `D:\Sandbox\AIOS_habbit\RUN_AIOS_WORKSPACE_CHAT.bat`.
- **Dòng trạng thái chỉ mục thực tế trên giao diện sau khởi động lại**:
  - `Kho đang dùng: Kho điều tra lỗi (dieu_tra_loi) · 681 tài liệu · 74.439 mảnh · mã a3fd319a5368 · ONNX fp32`
  - Đã hiển thị đúng kho lĩnh vực (`Kho điều tra lỗi (dieu_tra_loi)`), không còn hiển thị `library.sqlite · 681 tài liệu`.

---

## 4. Kết quả Cổng sống & Cổng hồi quy trên ứng dụng thật cổng 8501 (Cổng 4b & 4c)

> **Ghi chú về nghiệm thu trực tiếp của User**: User đã tự thử và nhìn thấy hỏi đáp hoạt động trên giao diện thực tế, đồng thời xác nhận công nhận hỏi đáp đạt và yêu cầu đóng vé đẩy dữ liệu ngay. Dưới đây là số liệu đếm `messages.jsonl` trước/sau của các cổng đã chạy trên ứng dụng thật cổng `8501`:

1. **Hiển thị thẻ chờ trung thực ngay khi bấm Gửi**:
   - Ngay sau khi bấm Gửi câu `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`, hộp chờ hiển thị `● Tìm nguồn (1.5s)` đang chạy, `○ Đọc trích đoạn` và `○ Tổng hợp trả lời` ở trạng thái chờ (xem ảnh `01`).
2. **Cổng 4b-1 — Gõ theo nhịp người thật rồi bấm Gửi ngay (không đổi ô chọn kho)**:
   - Hội thoại kiểm thử: `CONV-C6C375A0`
   - Câu hỏi: `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`
   - Đếm `messages.jsonl` của `CONV-C6C375A0`: **Trước = 0 bản ghi -> Sau = 2 bản ghi** (1 `user`, 1 `assistant` trả lời đầy đủ từ 2 nguồn / 4 đoạn trích, xem ảnh `02`).
3. **Cổng 4b-2 — Gõ câu hỏi theo nhịp người thật -> Đổi ô chọn kho (tạo rerun lưu bản nháp) -> Bấm Gửi đúng 1 lần**:
   - Hội thoại kiểm thử: `CONV-9C90ACAA`
   - Câu hỏi: `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`
   - Đếm `messages.jsonl` của `CONV-9C90ACAA`: **Trước = 0 bản ghi -> Sau = 2 bản ghi** (câu hỏi được lưu và trả lời hoàn chỉnh, ô nhập được xóa sạch, xem ảnh `03`).
4. **Cổng 4b-3 — Đóng hẳn tab trình duyệt, mở tab mới vào lại đúng hội thoại cũ `CONV-3A496585` và hỏi lại câu 94mm**:
   - Hội thoại: `CONV-3A496585` (`Cuộc trò chuyện 22/10 14:32` — hội thoại từng bị kẹt 0 bản ghi khi user bấm Gửi 5 lần trước khi vá).
   - Câu hỏi: `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`
   - Đếm `messages.jsonl` của `CONV-3A496585`: **Trước = 0 bản ghi -> Sau = 2 bản ghi** (hội thoại `CONV-3A496585` đã thoát hoàn toàn khỏi bẫy nháp, lưu câu hỏi và trả lời đầy đủ, xem ảnh `04`).
5. **Cổng hồi quy 4c-1 — Gửi `Mã lỗi C6400 là lỗi gì?` đúng 1 lần và để yên 60 giây**:
   - Đếm `messages.jsonl`: **Trước = 0 bản ghi -> Sau = 2 bản ghi**; số bong bóng trên DOM sau 60 giây đứng yên = **2** (1 câu hỏi, 1 thẻ trả lời duy nhất từ DB 30.075 ca KDTPS, không nhân bản lượt trả lời, xem ảnh `05`).
6. **Cổng hồi quy 4c-2 — Bấm chip gợi ý câu hỏi tiếp theo**:
   - Hội thoại: `CONV-963D14DB`
   - Chip được bấm: `"Lỗi vạch ngang bước 94mm nguyên nhân do liên quan gì đến Loi KDTPS?"`
   - Đếm `messages.jsonl` của `CONV-963D14DB`: **Trước = 2 bản ghi -> Sau = 4 bản ghi** (không bị ngậm câu hỏi, trả lời đầy đủ từ 15 đoạn liên quan, xem ảnh `06`).

---

## 5. Bảng kê ảnh nghiệm thu PNG thô (Dung lượng + SHA-256 + Chú thích khớp nghĩa đen khung hình)

Tất cả 6 ảnh đều là tệp PNG thô (`\x89PNG`), được nộp tại `hop-thu/lan-desktop-pc0575/ket-qua/` trên kho điều phối và `docs/phieu-viec/ket-qua/` trên kho mã:

| STT | Tên tệp ảnh | Dung lượng (bytes) | SHA-256 (tính từ đúng tệp nộp) | Chú thích nghĩa đen khớp nội dung khung hình thực tế |
|---|---|---|---|---|
| 1 | `anh-pc0575-send-draft-trap-01-honest-wait-step1.png` | `136448` | `43038CC6E6707CA96AF50E7824654DB8035CE8CDC1DEEC12A574206577936F4` | Khung hình sổ `trinh bày` ngay sau khi bấm Gửi câu `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`: dòng trạng thái chỉ mục hiện `"Kho đang dùng: Kho điều tra lỗi (dieu_tra_loi) · 681 tài liệu · 74.439 mảnh · mã a3fd319a5368 · ONNX fp32"`, bong bóng câu hỏi của người dùng ở trên, hộp chờ AI đang chạy hiện `"✅ Đã nhận câu hỏi · Đang xử lý..."`, bước 1 `"● Tìm nguồn (1.5s)"` đang chạy, bước 2 `"○ Đọc trích đoạn"` và bước 3 `"○ Tổng hợp trả lời"` chưa chạy, `"⏱️ Tổng thời gian: 1.5s"`, ô nhập câu hỏi bên dưới đã xóa rỗng (`"Nhập câu hỏi bạn muốn AI hỗ trợ..."`) kèm nhãn `"✓ Đã nhận"`. |
| 2 | `anh-pc0575-send-draft-trap-02-direct-human-send.png` | `168026` | `F5129438B443F1D7960F9B448D5FB843FE4B041D35C3BAD1555B997B5241738A` | Khung hình cổng 4b-1 (`CONV-C6C375A0`, gõ theo nhịp người thật rồi bấm Gửi ngay không đổi ô chọn kho): dòng trạng thái chỉ mục hiện `"Kho đang dùng: Kho điều tra lỗi (dieu_tra_loi) · 681 tài liệu · 74.439 mảnh · mã a3fd319a5368 · ONNX fp32"`, bong bóng câu hỏi `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`, câu trả lời hoàn chỉnh của AI (`"Vạch ngang có bước lặp 94 mm được ghi nhận liên quan đến cụm trống và con lăn ép [1]..."`), nhãn `"✅ AI đã trả lời"`, `"Nguồn gửi cùng câu hỏi: 2 (4)"`, `"Đang tra cứu khối Điều tra lỗi. Đã dùng 4 đoạn liên quan từ 2 nguồn."`, và 3 chip gợi ý câu hỏi tiếp theo ở dưới. |
| 3 | `anh-pc0575-send-draft-trap-03-switch-block-send.png` | `162714` | `E0EAD077B0DFE706D2544AD96E77ABB06F61ECC62679013F4D8713E2B3F1D194` | Khung hình cổng 4b-2 (`CONV-9C90ACAA`, gõ câu hỏi theo nhịp người thật, đổi ô chọn kho sang `"Kho điều tra lỗi"` gây rerun lưu nháp, rồi bấm Gửi 1 lần): bong bóng câu hỏi `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"`, câu trả lời của AI (`"Với hiện tượng vạch ngang có chu kỳ 94 mm, nguồn chỉ ghi nhận chu kỳ này liên quan đến cụm trống và con lăn ép..."`), nhãn `"✅ AI đã trả lời"`, 3 chip gợi ý tiếp theo, và ô nhập dưới cùng đã xóa sạch chữ cũ, hiển thị pill `"📚 Điều tra lỗi (679 tài liệu)"` và `"✓ Đã nhận"`. |
| 4 | `anh-pc0575-send-draft-trap-04-reopen-tab-conv-3a496585.png` | `173046` | `3C7379980B885F782999A2FDDE9BA15DFF6AB4802A02211822321D91470D2ADE` | Khung hình cổng 4b-3 (đóng tab trình duyệt, mở tab mới vào lại đúng hội thoại cũ `CONV-3A496585` `"Cuộc trò chuyện 22/10 14:32"` đang được đánh dấu `👉 💬` ở thanh bên trái, gõ câu `"Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"` và bấm Gửi 1 lần): hiển thị dòng trạng thái `"Kho đang dùng: Kho điều tra lỗi (dieu_tra_loi) · 681 tài liệu · 74.439 mảnh · mã a3fd319a5368 · ONNX fp32"`, bong bóng câu hỏi và câu trả lời hoàn chỉnh của AI (`"Lỗi vạch ngang bước 94 mm được ghi nhận có thể liên quan đến chu kỳ của cụm trống hoặc con lăn ép [1]..."`), nhãn `"✅ AI đã trả lời"`. |
| 5 | `anh-pc0575-send-draft-trap-05-reg-c6400-60s.png` | `228802` | `6350CB2B5D3F77D74E8CAF50B9FB04839EECB0BE951893D1685F1D5FF3AC72C1` | Khung hình cổng hồi quy 4c-1 sau khi gửi `"Mã lỗi C6400 là lỗi gì?"` đúng 1 lần và để yên 60 giây: hiển thị đúng 1 thẻ trả lời duy nhất `"Tra cứu lỗi tương tự — Dựa trên cơ sở dữ liệu 30.075 ca điều tra lịch sử KDTPS và danh mục mã lỗi chuẩn, dưới đây là thông tin điều tra và xử lý cho mã lỗi C6400:"` gồm đầy đủ các mục 1, 2, 3, 4 (liệt kê các ca `2026/4150`, `2026/4323`, `2026/1352`...), không bị lặp hay nhân bản bong bóng. |
| 6 | `anh-pc0575-send-draft-trap-06-reg-suggest-chip.png` | `139096` | `2F3FCA875049A6B4D86E5FF79E6540E5337DC5CBD3F3AA20C1D28F06ED7C1333` | Khung hình cổng hồi quy 4c-2 (`CONV-963D14DB`) sau khi bấm chip gợi ý `"Lỗi vạch ngang bước 94mm nguyên nhân do liên quan gì đến Loi KDTPS?"`: hiển thị câu trả lời hoàn chỉnh của AI cho câu hỏi từ chip, nhãn `"✅ AI đã trả lời"`, `"Nguồn gửi cùng câu hỏi: 1 (15)"`, `"Đang tra cứu khối Điều tra lỗi. Đã dùng 15 đoạn liên quan từ 1 nguồn."`, các chip gợi ý tiếp theo, và ô nhập câu hỏi bên dưới đã xóa rỗng. |
