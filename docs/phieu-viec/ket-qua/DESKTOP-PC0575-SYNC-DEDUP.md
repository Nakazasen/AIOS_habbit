# BÁO CÁO THỰC THI VÉ DESKTOP-PC0575-SYNC-DEDUP

**Mã vé:** `DESKTOP-PC0575-SYNC-DEDUP`  
**Trạng thái:** `HOAN_THANH`  
**Thời điểm hoàn thành:** `2026-10-16T06:36:40.000Z`  
**Máy thực thi:** KDTVN-PC0575 (Intel Core i5-8265U @ 1.60GHz, 16.0 GB RAM, Windows 11 Pro 64-bit, CPU-only)  
**Nhánh công tác:** `phieu-viec/rag-fix1`  
**Mô hình chỉ định:** Gemini 3.8 Flash High (Gemini Web Engine qua Antigravity Bridge Daemon direct mode)  
**Cấu hình tuân thủ:** BB-CONFIG-PARITY-01 (`AIOS_RAGV2_WORKER_PERSIST=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `AIOS_RETRIEVAL_DEVICE=cpu`, `AIOS_RAG_V2_NUMPY_DENSE=1`, Streamlit port 8501, Sidecar port 8585).

---

## 1. Tổng quan & Kết quả đồng bộ Git

- **Nguồn gốc cụm sửa:** Cụm sửa khử trùng hiển thị đáp án máy nhà (`DESKTOP-ANSWER-DISPLAY-DEDUP-HOME`, commit `0990aadf` trên nhánh `phieu-viec/rag-fix1`).
- **Bối cảnh cụm sửa:**
  1. Dòng miễn trừ `Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng.` bị in 2 lần liên tiếp dưới đáp án AI (gốc: render cả trong hàm `render_ai_answer_header` lẫn tại điểm gọi trong `workspace_chat_app.py`).
  2. Biểu đồ JIG (`BOW_B` / `JIG-01`) hiển thị 2 lần trong cùng một đáp án (gốc: luồng JIG đã nhúng sẵn biểu đồ data URI base64 vào thân đáp án `assistant_text`, ứng dụng lại nối thêm một lần nữa ở `_xu_ly_mot_y_dinh`).
  3. Kèm sửa nhận diện mã JIG dài trước mã ngắn trong `chart_selection.py` (`sorted(..., key=lambda s: len(str(s)), reverse=True)`).
- **Thực thi đồng bộ & Vá tại chỗ (Tuân thủ nguyên tắc "Lỗi đâu vá đấy trong phạm vi vé, vá tại chỗ commit lên nhánh"):**
  - Nhánh `phieu-viec/rag-fix1` tại PC0575 đã chứa commit `0990aadf`.
  - Khi chạy kiểm thử ban đầu, phát hiện lỗi hồi quy do commit `2327a8aa` sau đó vô tình đè mất câu lệnh `return van_ban or None` của nhánh `VE_BIEU_DO` trong `_xu_ly_mot_y_dinh` thuộc `src/aios_habit/workspace_chat_app.py` khiến `_xu_ly_mot_y_dinh` trả về `None` cho lệnh vẽ biểu đồ JIG.
  - **Đã vá tại chỗ:** Phục hồi câu lệnh `return van_ban or None` ngay sau khối xử lý `VE_BIEU_DO` trong `src/aios_habit/workspace_chat_app.py`.
  - Bổ sung bộ test tự động riêng của vé: `tests/test_desktop_pc0575_sync_dedup.py`.
  - Bổ sung kịch bản đo thực nghiệm tự động Playwright: `scripts/run_desktop_pc0575_sync_dedup.py`.
  - Commit và push trực tiếp lên nhánh `phieu-viec/rag-fix1`, đảm bảo **HEAD khớp origin với độ lệch = 0**.

---

## 2. Kết quả kiểm thử tự động (Pytest)

Toàn bộ các bộ test liên quan đến khử trùng hiển thị, chọn biểu đồ, luồng JIG chat và bất biến hệ thống đều xanh 100%:

1. **Bộ test mục tiêu của vé:**
   - Lệnh: `pytest tests/test_desktop_pc0575_sync_dedup.py tests/test_desktop_answer_display_dedup_home.py -v`
   - Kết quả: **16/16 PASSED** (3.18s).
   - Nội dung kiểm tra:
     - Sắp xếp mã JIG và chỉ số đo dài trước ngắn (`test_jig_code_sorting_longest_first_parity`).
     - `_xu_ly_mot_y_dinh` nhúng biểu đồ đúng 1 lần duy nhất, không trùng lặp (`test_xu_ly_mot_y_dinh_returns_chart_without_duplication`).
     - Khóa AST mã nguồn đảm bảo không gọi đúp disclaimer caption sau header (`test_workspace_chat_app_source_dedup_lock`).
     - Bất biến FR-030 Local Fallback không mang header hay disclaimer AI (`test_local_fallback_no_disclaimer_invariant`).
     - Tính lũy đẳng (idempotent) khi re-render header và re-run pipeline biểu đồ.

2. **Bộ test mở rộng (JIG chat wire & Chart selection):**
   - Lệnh: `pytest tests/test_desktop_pc0575_sync_dedup.py tests/test_desktop_answer_display_dedup_home.py tests/test_csv_chart_selector.py tests/test_jig_chat_wire.py -q`
   - Kết quả: **50/50 PASSED** (3.27s).

---

## 3. Kết quả kiểm chứng thực nghiệm trên ứng dụng thật PC0575

- **Môi trường đo:** Streamlit port 8501, Antigravity Sidecar port 8585 (`mode=direct`), Playwright Chromium headless.
- **Tài liệu nguồn trích xuất:** `Sirius 2 _ C7620_報告版 4.pptx` (Bộ sưu tập `lsu`).
- **Dữ liệu JIG kiểm chứng:** Kho log đo JIG thực tế với 250.149 bản ghi (gồm `JIG-01` với 132 bản ghi chỉ số `bowskew`).

### Bảng tổng hợp đối chiếu 3 hạng mục kiểm chứng

| STT | Hạng mục kiểm chứng | Yêu cầu tiêu chí | Kết quả đo thực tế | Trạng thái | Minh chứng giao diện UI (SHA256) |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 0 | **Khởi động ứng dụng** | App load thành công, kết nối kho LSU | Sẵn sàng sau 10.06s (Worker LSU đã ấm) | **ĐẠT** | `anh-pc0575-dedup-00-app-ready.png`<br>`B552454EEBEFDF07CCFBBBDB5900BF72506773F21F3617EF8E9702C8CFCC9C4D` |
| 1 | **Khử trùng Disclaimer AI** | Dưới đáp án AI chỉ hiển thị đúng 1 dòng miễn trừ | Chính xác **1 dòng** miễn trừ AI dưới header | **ĐẠT 100%** | `anh-pc0575-dedup-01-ai-disclaimer.png`<br>`55CD73676AE646978C7480247FC75B3AEA1B3339D158FBDD9C7E8DD298EE7884` |
| 2 | **Khử trùng Biểu đồ JIG** | Đáp án có biểu đồ JIG chỉ hiển thị đúng 1 biểu đồ | Đúng **1 biểu đồ** trong text lưu và **1 thẻ img** trên DOM | **ĐẠT 100%** | `anh-pc0575-dedup-02-jig-chart.png`<br>`3394BE062CD74021E7B6D97BC602C55533E670C3BF373AE723F3A000F22E2EC9` |
| 3 | **Bất biến Local Fallback** | Đáp án dự phòng cục bộ không có dòng miễn trừ AI | Đúng **0 dòng** disclaimer trong bubble, AST đạt | **ĐẠT 100%** | `anh-pc0575-dedup-03-local-fallback.png`<br>`3DC0C4510B474C75FDFB95C6DC3D4E7E9738FCF19E0BEFDC0260711EB872B519` |

---

## 4. Chi tiết kiểm chứng từng hạng mục

### 4.1. Hạng mục 1: Khử trùng dòng miễn trừ AI
- **Câu hỏi kiểm tra:** `C23とC24ではどのような発生Trendでしたか。` (Conversation: `CONV-PC0575-DEDUP-AI-6E9560`).
- **Hành vi trước khi sửa:** Dưới đáp án AI in 2 dòng liên tiếp:
  - Dòng 1 do `render_ai_answer_header()` in ra.
  - Dòng 2 do câu lệnh thừa `st.caption(t("ai_disclaimer", locale=current_ui_locale))` tại điểm gọi trong `workspace_chat_app.py`.
- **Hành vi sau khi sửa:**
  - Điểm gọi đã loại bỏ lệnh gọi thừa.
  - Header AI trả lời hiển thị thông tin trích dẫn trung thực kèm đúng **1 dòng disclaimer duy nhất**:
    > *Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng.*
  - Kết quả kiểm đếm Playwright: `disclaimer_count = 1` -> **ĐẠT 100%**.

### 4.2. Hạng mục 2: Khử trùng biểu đồ JIG
- **Câu lệnh kiểm tra:** `vẽ biểu đồ bowskew cho JIG-01` (Conversation: `CONV-PC0575-DEDUP-JIG-E4A83B`).
- **Hành vi trước khi sửa:** Luồng xử lý JIG trong `_quyet_dinh_ve_bieu_do` đã nhúng chuỗi Markdown ảnh base64 (`![biểu đồ](data:image/png;base64,...)`) vào `assistant_text`, nhưng `_xu_ly_mot_y_dinh` lại vô điều kiện cộng dồn thêm chuỗi `![biểu đồ](...)` một lần nữa, dẫn đến việc cùng 1 ảnh hiển thị 2 lần liên tiếp.
- **Hành vi sau khi sửa:**
  - `_xu_ly_mot_y_dinh` bổ sung kiểm tra kiểm tra tồn tại `if chart_md not in van_ban and f"data:image/png;base64,{ma_hoa}" not in van_ban:` trước khi cộng thêm.
  - Kết quả kiểm đếm Playwright: `chart_count_text = 1`, `chart_count_dom = 1` -> **ĐẠT 100%**.

### 4.3. Hạng mục 3: Bất biến đáp án dự phòng cục bộ (Local Grounded Fallback)
- **Hội thoại kiểm tra:** `CONV-PC0575-DEDUP-LOCAL-4DECFD`.
- **Hành vi tuân thủ:**
  - Đáp án tổng hợp cục bộ từ trích đoạn tài liệu trên máy (`operational_mode == "local_grounded_fallback"`) không đi qua mô hình AI, do đó theo tiêu chuẩn FR-030 bắt buộc KHÔNG mang AI header và KHÔNG mang AI disclaimer.
  - Kết quả kiểm tra AST mã nguồn: Khối `local_grounded_fallback` hoàn toàn không chứa `ai_disclaimer` và `render_ai_answer_header`.
  - Kết quả kiểm đếm Playwright: `disclaimer_count = 0` -> **ĐẠT 100%**.

---

## 5. Tệp dữ liệu & Artifacts lưu trữ

1. **Báo cáo kết quả:**
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\DESKTOP-PC0575-SYNC-DEDUP.md`
   - `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\DESKTOP-PC0575-SYNC-DEDUP.md`
2. **Dữ liệu JSON đo thực nghiệm chi tiết:**
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\ket-qua-do-desktop-pc0575-sync-dedup.json`
   - `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\ket-qua-do-desktop-pc0575-sync-dedup.json`
3. **Ảnh minh chứng giao diện thực tế:**
   - `anh-pc0575-dedup-00-app-ready.png` (Khởi động ứng dụng sẵn sàng)
   - `anh-pc0575-dedup-01-ai-disclaimer.png` (1 dòng disclaimer AI duy nhất)
   - `anh-pc0575-dedup-02-jig-chart.png` (1 biểu đồ JIG duy nhất)
   - `anh-pc0575-dedup-03-local-fallback.png` (Bất biến local fallback 0 disclaimer)
4. **Nhật ký thực thi phiên:**
   - `session_desktop_pc0575_sync_dedup.log`
   - `server_desktop_pc0575_sync_dedup.log`

---

```json
{
  "ma_ve": "DESKTOP-PC0575-SYNC-DEDUP",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-16T06:36:40.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
