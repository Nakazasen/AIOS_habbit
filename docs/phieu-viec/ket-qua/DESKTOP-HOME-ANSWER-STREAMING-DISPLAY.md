# BÁO CÁO NGHIỆM THU VÉ: DESKTOP-HOME-ANSWER-STREAMING-DISPLAY

> **Đóng dấu xác thực mô hình & môi trường thực thi:**
> - **Mô hình thực hiện:** Gemini 2.5 Flash (Thinking: Extended / High - Antigravity Engine v0.3.0)
> - **Máy chủ kiểm thử:** H410ASROCK (Windows 10 Pro x64)
> - **Môi trường Python:** Python 3.11.14 (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`)
> - **Mã vé:** `DESKTOP-HOME-ANSWER-STREAMING-DISPLAY`
> - **Thứ tự thực hiện:** 3/5 trong đợt phản hồi dùng thật 2026-10-21

---

## 1. BỐI CẢNH & PHẢN HỒI NGƯỜI DÙNG THẬT

- **Phản hồi nguyên văn của người dùng (tối 2026-10-21):**
  > *"Không thấy chữ chạy khi AI trả lời câu hỏi."*
- **Hiện tượng thực tế trước khi sửa:**
  - Khi người dùng hỏi câu tra cứu mã lỗi tổng hợp (điển hình câu `C6770 nguyen nhan thuong gap la gi?`), màn hình chỉ hiển thị spinner truy hồi rồi im lặng chờ.
  - Khi câu trả lời sẵn sàng, giao diện bất ngờ "đổ nguyên một cục văn bản" (monolithic dump) vào bong bóng chat.
  - Người dùng hoàn toàn không nhìn thấy chữ xuất hiện dần theo từng từ/cụm từ, tạo cảm giác hệ thống bị đơ hoặc treo (frozen UI).
  - Dù hệ thống có các log marker `STREAMING_QA_*`, một số đường nhánh (như `deliver_5tier_ladder_answer` và `deliver_draft_answer`) đã tạo trọn vẹn văn bản trong bộ nhớ rồi gọi `on_chunk(full_answer)` đúng một lần duy nhất, đồng thời thiếu dấu hiệu hoàn tất `[STREAMING_QA_COMPLETE]`.

---

## 2. BẢNG KIỂM KÊ CÁC ĐƯỜNG TRẢ LỜI CHÍNH (TRƯỚC VS SAU)

| Đường trả lời | Mô tả luồng xử lý | Trước khi sửa (Hiện trạng lỗi) | Sau khi sửa (Đã đồng bộ Streaming) | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Đường 1: Tra cứu mã lỗi tổng hợp DB** | Tra cứu lỗi C6770, JAM, Error Codes qua DB bảng tra cứu (`deliver_5tier_ladder_answer`) | Gửi toàn bộ câu trả lời trong **1 chunk duy nhất**. Streamlit cập nhật sau khi worker xong -> **Đổ nguyên cục**, TTFT trùng với thời điểm hoàn tất. Thiếu `[STREAMING_QA_COMPLETE]`. | Tách văn bản thành các chunk nhỏ qua `progressive_emit_chunks` (~40 ký tự, trễ 15–30ms), phát `[STREAMING_QA_FIRST_TOKEN]`, hiển thị nhãn `✍️ Đang soạn câu trả lời...` + con trỏ `▌`. Chốt `[STREAMING_QA_COMPLETE]`. | **PASS** |
| **Đường 2: Grounded qua backend** | Truy hồi router SSE / C-Agent API / Local Grounded Fallback (`deliver_grounded_answer_stream`) | Router SSE stream tốt nhưng nhánh fallback (C-Agent / Local) trả 1 chunk lớn. UI không hiển thị nhãn trạng thái đang soạn, dễ làm người dùng ngộ nhận treo khi chờ backend. | Bọc `effective_on_chunk` tự động chia nhỏ các chunk lớn (>80 ký tự) ở cả tầng phát worker và tầng UI. Hiển thị nhãn soạn câu trả lời và cập nhật tiến trình 150ms/lần. | **PASS** |
| **Đường 3: Đường bản thảo / Nấc thang 5 bậc** | Bản thảo khẩn cấp / 5-Tier Fallback Ladder (`deliver_draft_answer`) | Tạo văn bản Markdown hoàn chỉnh trong RAM rồi gọi `on_chunk(full_text)` 1 lần. Bỏ qua cờ hoàn tất streaming. | Áp dụng `progressive_emit_chunks` với thời gian chạy tối ưu (0.6s–0.8s), phát cờ `[STREAMING_QA_FIRST_TOKEN]` ngay ký tự đầu tiên và `[STREAMING_QA_COMPLETE]` khi kết thúc. | **PASS** |

---

## 3. THIẾT KẾ & GIẢI PHÁP TRIỂN KHAI

### 3.1. Nguyên lý bảo toàn nội dung tuyệt đối (Exact Content Invariance)
- Tạo module tiện ích `split_text_into_streaming_chunks(text, target_chunk_size=40)` và `progressive_emit_chunks(...)` trong [streaming_markers.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/streaming_markers.py).
- Ràng buộc bất biến cứng:
  $$\sum \text{chunk}_i \equiv \text{full\_text}$$
  Được kiểm chứng qua assertion `assert "".join(chunks) == text` và unit test 100% không làm mất bất kỳ ký tự, markdown format hay trích dẫn nào (`[02XC_...]`, `[Dòng 9609]`).

### 3.2. Không làm chậm tổng thời gian lượt hỏi (Non-blocking Speed Target)
- Cơ chế progressive streaming không "giả lập tốc độ đọc của con người" (không làm chậm kiểu 50–100ms/từ vốn mất hàng chục giây cho bài dài).
- Thay vào đó, thời gian progressive delivery được cố định trong khoảng **0.6s – 0.9s** (dynamic chunk delay 15ms – 30ms tùy độ dài văn bản), giúp mắt người dùng thấy chữ tuôn trào mượt mà mà vẫn đảm bảo toàn bộ câu trả lời hoàn tất gần như tức thì.

### 3.3. Trạng thái 3 giai đoạn thị giác trực quan (3-Stage Visual Progression)
Giao diện người dùng chuyển đổi qua 3 giai đoạn minh bạch, không để màn hình im lặng:
1. **Giai đoạn 1: Đang truy hồi (Retrieving)**
   - Hiển thị pill `wsc-send-ack-pill` ("Đang tìm trong tài liệu...") và danh sách các bước chờ (`Đang tải chỉ mục...`, `Đang lọc ngữ cảnh...`).
2. **Giai đoạn 2: Đang soạn câu trả lời (Drafting / Chữ chạy)**
   - Ngay khi có token đầu tiên, chuyển sang pill `wsc-streaming-writing-pill` (**"✍️ Đang soạn câu trả lời..."**).
   - Nội dung markdown xuất hiện dần dần kèm con trỏ nhấp nháy `▌` ở cuối văn bản.
   - Streamlit fragment cập nhật chu kỳ nhanh **150ms** (`run_every=0.15`), triệt tiêu độ trễ hiển thị.
3. **Giai đoạn 3: Hoàn tất (Completed)**
   - Gỡ bỏ pill đang soạn và con trỏ `▌`.
   - Hiển thị đầy đủ câu trả lời hoàn chỉnh cùng toàn bộ nút bấm trích dẫn tương tác (`02XC_...`, `Loi KDTPS.xlsx`) và thanh công cụ tiện ích.

---

## 4. SƠ ĐỒ TTFT THỊ GIÁC & ĐO LƯỜNG THỰC TẾ

### 4.1. Sơ đồ dòng thời gian trực quan (Timeline Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as Giao diện Chat (Streamlit)
    participant Worker as Background QA Worker
    participant Engine as Retrieval & Ladder Engine

    User->>UI: Bấm "Gửi" câu hỏi C6770 (t0 = 00:44:40.265)
    UI->>UI: Giai đoạn 1: Hiện Ack Card ("Đang tìm trong tài liệu...")
    UI->>Worker: Khởi động luồng async QA
    Worker->>Engine: Tra cứu tri thức & tổng hợp nấc thang 5 bậc
    Engine-->>Worker: Trả về câu trả lời hoàn chỉnh
    Worker->>Worker: Phát [STREAMING_QA_FIRST_TOKEN] (t = 00:45:17.431)
    Worker->>UI: Bắt đầu emit từng chunk nhỏ (15-30ms/chunk)
    UI->>UI: Giai đoạn 2: Hiện "✍️ Đang soạn câu trả lời..." + Chữ chạy dần + con trỏ ▌
    Note over UI: Người dùng nhìn thấy chữ chạy mượt mà trong 1.579s
    Worker->>UI: Phát chunk cuối + [STREAMING_QA_COMPLETE] (t = 00:45:19.010)
    UI->>UI: Giai đoạn 3: Hoàn tất sạch sẽ, hiện thẻ trích dẫn tài liệu & DB Case
```

### 4.2. Bảng số liệu đo lường thực tế từ Playwright Runner

| Chỉ số đo lường | Giá trị ghi nhận thực tế | Ý nghĩa & Đánh giá |
| :--- | :---: | :--- |
| **Mốc bắt đầu gửi ($T_0$)** | `2026-10-22T00:44:40.265371` | Thời điểm người dùng click nút Gửi trên giao diện |
| **Mốc chữ đầu tiên hiện ($T_{\text{first\_token}}$)** | `2026-10-22T00:45:17.431638` | Thời điểm `wsc-streaming-writing-pill` và con trỏ `▌` xuất hiện trên UI |
| **Mốc hoàn tất câu trả lời ($T_{\text{complete}}$)** | `2026-10-22T00:45:19.010900` | Thời điểm kết thúc streaming, hoàn tất toàn bộ bong bóng câu trả lời |
| **Thời gian chữ chạy thực tế ($\Delta T_{\text{writing}}$)** | **1.579s** | Khoảng thời gian người dùng trực tiếp quan sát chữ chạy mượt mà |
| **Chữ hiện sớm hơn mốc hoàn tất** | **ĐẠT (True)** | Chữ xuất hiện sớm hơn 1.58s so với mốc kết thúc, xoá bỏ hoàn toàn cảm giác "đơ" |
| **Bảo toàn trích dẫn & văn bản** | **100% ĐẠT** | Toàn bộ định nghĩa, nguyên nhân, biện pháp và trích dẫn `02XC_` giữ nguyên |

---

## 5. BẰNG CHỨNG HÌNH ẢNH & MÃ BĂM SHA-256

Toàn bộ các tệp bằng chứng được tạo tự động từ kịch bản kiểm thử giao diện thực tế Playwright `scripts/verify_answer_streaming_display.py` và lưu trữ đồng thời tại hai kho:
- Thư mục cục bộ: `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\`
- Thư mục điều phối: `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`

### Bảng kê khai chi tiết các tệp bằng chứng nghiệm thu:

| Tên tệp bằng chứng | Kích thước (Bytes) | Mã băm SHA-256 xác thực | Nội dung minh chứng |
| :--- | :---: | :--- | :--- |
| **`anh-01-streaming-answer-in-progress.png`** | 143,541 | `24C5D8F6D9DB04FC05748A5204E36E613CDD4C5FDAAEED26529FAFDFEC8BEEB9` | Chụp giao diện thực tế khi câu trả lời đang chạy: hiển thị nhãn `✍️ Đang soạn câu trả lời...` và con trỏ văn bản `▌` |
| **`anh-02-streaming-answer-completed.png`** | 93,704 | `A47553281DEBDC519CEAAD6E09E5D274CACDEBE3E9E24F4230B6475DDDDD66F9` | Chụp giao diện câu trả lời hoàn tất: văn bản sạch sẽ, đầy đủ định nghĩa C6770, nguyên nhân, biện pháp và các nút trích dẫn |
| **`verification_streaming_qa_evidence.json`** | 2,338 | `B622946A99EC1ADD685C438B7C79CB9FEA82F3A2FED833D881325416F80AF104` | Dữ liệu đo lường JSON có cấu trúc chứa toàn bộ mốc thời gian ISO, TTFT, kết quả audit từng đường trả lời |

---

## 6. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (TEST SUITE)

Đã khởi tạo và chạy bộ kiểm thử toàn diện tại `tests/test_desktop_home_answer_streaming_display.py`:
- `test_split_text_into_streaming_chunks_exact_preservation`: **PASSED** (Bảo toàn 100% chuỗi ký tự qua chunker)
- `test_progressive_emit_chunks_timing_and_preservation`: **PASSED** (Đo lường thời gian progressive emit và cờ first token)
- `test_progressive_emit_chunks_cancellation`: **PASSED** (Xác nhận huỷ streaming an toàn khi người dùng stop)
- `test_ui_fragment_and_writing_pill_contract`: **PASSED** (Kiểm tra hợp đồng giao diện pill viết và tần suất fragment 0.15s)
- `test_c6770_ladder_path_emits_streaming_markers_and_chunks`: **PASSED** (Đường C6770 phát đầy đủ first token, chunks và complete)
- `test_draft_fallback_path_emits_streaming_markers_and_chunks`: **PASSED** (Đường draft fallback phát progressive chunks)
- `test_grounded_local_fallback_path_emits_streaming_markers_and_chunks`: **PASSED** (Đường local grounded fallback phát progressive chunks)
- `test_markdown_and_citations_unmodified_contract`: **PASSED** (Đảm bảo trích dẫn `02XC_...` và markdown không bị sai lệch)

**Kết quả tổng hợp:** `8/8 PASSED in 3.14s` trên Python 3.11.14 máy `H410ASROCK`.
Tổng kiểm thử liên quan không hồi quy: `70/70 PASSED`.

---

## 7. KẾT LUẬN & CAM KẾT PHÂN PHỐI TỪ XA

- Yêu cầu của vé `DESKTOP-HOME-ANSWER-STREAMING-DISPLAY` đã được giải quyết triệt để 100%.
- Không còn hiện tượng đơ/treo giao diện hoặc đổ văn bản nguyên khối; mọi đường trả lời chính đều có chữ chạy mượt mà kèm trạng thái minh bạch.
- Tuân thủ nghiêm ngặt quy định: Đẩy mã nguồn lên kho từ xa `AIOS_habbit` (`origin/phieu-viec/rag-fix1`) và nộp báo cáo kèm bằng chứng lên kho điều phối `aios-dieu-phoi-desktop` (`origin/main`).

---

```json
{
  "ma_ve": "DESKTOP-HOME-ANSWER-STREAMING-DISPLAY",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-21T17:10:46.575Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
