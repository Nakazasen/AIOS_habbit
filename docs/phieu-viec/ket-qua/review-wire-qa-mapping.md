# Báo cáo review chéo tương thích Q&A Mapping và C-Agent Spec (REVIEW-WIRE-QA-MAPPING)

- **Người thực hiện:** agy (Antigravity CLI) — Role: Reviewer / Technical Auditor
- **Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
- **Ngày thực hiện:** 2026-10-05
- **Mã vé:** `REVIEW-WIRE-QA-MAPPING`
- **Đối tượng thẩm định:**
  1. Dữ liệu Q&A Mapping: `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (do `opencode` trích xuất, 3.392 dòng).
  2. Đặc tả kỹ thuật C-Agent: `docs/phieu-viec/ket-qua/wire-cagent-spec.md` (do `agy` lập theo vé `PREP-WIRE-CAGENT-SPEC`).
- **Phán quyết tổng quan (Verdict):** **ĐẠT — OK ĐỂ NỐI** (Không phát hiện xung đột hay lỗi cản trở kết nối).

---

## 1. Kiểm tra tính đầy đủ trường dữ liệu (Field Completeness)

### 1.1. So khớp Schema thực tế
Kiểm tra toàn bộ 3.392 dòng trong file `wire-qa-mapping.jsonl`:
- **Số dòng hợp lệ JSON:** 3.392 / 3.392 (100% parse thành công, không có dòng rác hoặc lỗi cú pháp).
- **Tập hợp trường (Keys) xuất hiện:** 100% bản ghi đều chứa đúng 6 trường:
  - `id`: Định danh duy nhất theo format `Q\d{4}` (từ `Q0001` đến `Q3406`).
  - `question`: Chuỗi nội dung câu hỏi kỹ thuật.
  - `answer`: Chuỗi nội dung câu trả lời kỹ thuật trích xuất từ tài liệu gốc.
  - `source`: Đường dẫn file nguồn (vd: `mom/batch-01.md`, `lsu/batch-21.md`, `dieuchinh/batch-88.md`).
  - `category`: Phân loại khối tri thức (`MOM`, `LSU`, `dieu-tra-loi`).
  - `batch`: Số hiệu batch tương ứng (từ `01` đến `88`).

### 1.2. Đối chiếu với yêu cầu Payload trong Đặc tả kỹ thuật
Trong `wire-cagent-spec.md` (Mục 1.2), cấu trúc ghép prompt tham khảo có dạng:
```text
--- DỮ LIỆU THAM KHẢO (BẢN THẢO) ---
[Nguồn: batch-{id}.md | CÂU HỎI {số} | Khối: {MOM/LSU/Điều-tra-lỗi}]
- Bối cảnh: {bối cảnh gốc}
- Câu hỏi gốc: {hỏi gốc}
- Trả lời gốc: {đáp gốc}
```

**Đánh giá tương thích:**
- Các trường `id`, `question`, `answer`, `source`, `category` trong JSONL cung cấp đầy đủ thông tin để ánh xạ vào prompt tham khảo.
- **Lưu ý kỹ thuật (Non-blocker):** Trong file JSONL không có trường riêng biệt tên là `context` hoặc `bối cảnh` như bản thảo prompt dự kiến, vì dữ liệu thô đã được tổng hợp trực tiếp vào cặp `question` và `answer`.
- **Khuyến nghị cho vé WIRE:** Khi ghép prompt, chỉ cần format dòng tiêu đề tham khảo:
  `[Nguồn: {source} | ID: {id} | Khối: {category}]`  
  `- Câu hỏi gốc: {question}`  
  `- Trả lời gốc: {answer}`  
  mà không cần tìm trường `Bối cảnh` riêng, hoàn toàn đủ thông tin để C-Agent tham chiếu.

---

## 2. Rà soát các trường hợp bất thường và nguy cơ với API (Edge Cases & Hazards)

Toàn bộ 3.392 bản ghi đã được quét tự động nhằm phát hiện các yếu tố có thể làm lỗi C-Agent API:

| Tiêu chí kiểm tra | Kết quả quét | Đánh giá & Rủi ro |
|---|---|---|
| **Câu hỏi quá dài (>1.000 ký tự)** | **0 câu** | Câu dài nhất chỉ **148 ký tự**, trung bình **49,3 ký tự**. Hoàn toàn không gây tràn context hay nghẽn prompt của Flowise. |
| **Câu hỏi rỗng / mỏng (<10 ký tự)** | **1 câu** (`Q0489`) | `Q0489` là *"PLM是什么？"* (PLM là gì? - 7 ký tự). Nội dung rõ ràng, không phải chuỗi rác. |
| **Câu trả lời rỗng / mỏng (<15 ký tự)** | **0 câu** | Không có câu trả lời nào rỗng. Câu ngắn nhất là 35 ký tự, dài nhất 505 ký tự, trung bình 132 ký tự. |
| **Ký tự điều khiển / Byte rỗng (`\x00`)** | **0 lỗi** | Toàn bộ dữ liệu sạch, không chứa byte nhị phân lạ. |
| **Ký tự xuống dòng thô (`\n`) trong field** | **0 lỗi** | Tất cả `question` và `answer` đều nằm trên 1 dòng đơn, không làm vỡ định dạng JSONL. |
| **Ký tự markdown / backticks (`)** | **3.392 / 3.392** | Toàn bộ bản ghi đều sử dụng dấu backticks để bọc mã linh kiện, số đo hoặc serial (vd: `F401`, `61C999999902`). C-Agent API và UI Chat Markdown xử lý an toàn. |
| **Trùng lặp ID** | **0 ID trùng** | 3.392 ID duy nhất từ `Q0001` đến `Q3406` (14 ID khuyết do đã lọc sạch ở các bước trước). |
| **Phân loại Khối (Category)** | Khớp **100%** | Gồm 3 nhóm chuẩn: `MOM` (608 câu), `LSU` (1.790 câu), `dieu-tra-loi` (994 câu). Không có category ngoài luồng. |
| **Dữ liệu đa ngữ (Nhật / Trung / Việt)** | 2.281 Q / 2.374 A chứa CJK | Phản ánh đúng đặc thù tài liệu kỹ thuật Kyocera. C-Agent và `cagent_api.py` truyền UTF-8 an toàn. |

---

## 3. Đối chiếu 3 câu hỏi Demo trong Spec với Dữ liệu JSONL

Trong `wire-cagent-spec.md` (Mục 5), 3 kịch bản demo mẫu được đưa ra để kiểm thử nghiệm thu cho vé WIRE. Đối chiếu trực tiếp với `wire-qa-mapping.jsonl` cho kết quả:

### 3.1. Demo 1: Khối Điều-tra-lỗi — Tra cứu mã lỗi C0980
- **Cặp tìm thấy trong JSONL:**
  - `Q3401` (Dòng 3387, `dieuchinh/batch-88.md`):
    - *Hỏi:* Service manual định nghĩa C0980 phát sinh theo những điều kiện thời gian nào?
    - *Đáp:* `C0980 là 24V電源断検知. File ghi hai điều kiện: phát hiện liên tục tín hiệu mất nguồn 24V trong 1 giây; hoặc sau 0.1 giây kể từ khi phát hiện tín hiệu mất 24V thì phát sinh service call khác...`
  - `Q3317` (Dòng 3303, `dieuchinh/batch-85.md`):
    - *Hỏi:* Investigation chính ghi các bất thường nào?
    - *Đáp:* `File ghi đứt cầu chì F401; Q402 và Q403 short 3 cực với nhau. Nguồn file: KTD-2025-03-0315-Iris2024-C34-A6-C0980.xlsx...`
- **Đánh giá:** Khớp 100% với nội dung và thông số kỹ thuật (cầu chì F401, transistor Q402/Q403, 24V) được nêu trong spec.

### 3.2. Demo 2: Khối MOM — Quy trình vận hành & Tham số điều khiển Matecon
- **Cặp tìm thấy trong JSONL:**
  - `Q0001` (Dòng 1, `mom/batch-01.md`):
    - *Hỏi:* Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?
    - *Đáp:* `ctrlMode quy định trạng thái truyền thông SLMP giữa Matecon, hệ thống cấp trên MOM và thiết bị. ctrlMode = 0 là chế độ sản xuất tự động, truyền thông được kích hoạt; Matecon gửi lệnh input/output đến ACR/CTU... ctrlMode = 1 là chế độ thủ công...`
- **Đánh giá:** Khớp chính xác từng từ ngữ chuyên môn với kỳ vọng của câu hỏi Demo 2 trong spec.

### 3.3. Demo 3: Khối LSU — Thông số đo kiểm Jig 2ND-1004
- **Cặp tìm thấy trong JSONL:**
  - `Q0825` (Dòng 815, `lsu/batch-21.md`):
    - *Hỏi:* Serial `61C999999902` xuất hiện bao nhiêu lần và pattern NG ra sao?
    - *Đáp:* `Serial này xuất hiện 4 lần. Cả 4 lần đều Total=NG, Black=NG, Magenta=NG, Cyan=OK, Yellow=NG. Nguồn file: 2026_08_UnitTest.csv...`
- **Đánh giá:** Khớp chính xác 100% với Raw value và bảng đánh giá NG 4 màu của câu Demo 3 trong spec.

---

## 4. Đánh giá tính hợp lý của Timeout (60s) và Retry (max 1)

### 4.1. Bảng đo mẫu 20 dòng phân bố đều (Mẫu thực tế)

| STT | Dòng | ID | Khối | Batch | Độ dài Câu hỏi (ký tự) | Độ dài Trả lời (ký tự) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 1 | `Q0001` | MOM | 01 | 76 | 337 |
| 2 | 170 | `Q0170` | MOM | 04 | 33 | 165 |
| 3 | 339 | `Q0339` | MOM | 08 | 25 | 101 |
| 4 | 508 | `Q0508` | MOM | 11 | 32 | 108 |
| 5 | 677 | `Q0687` | LSU | 17 | 32 | 130 |
| 6 | 846 | `Q0856` | LSU | 21 | 23 | 115 |
| 7 | 1015 | `Q1025` | LSU | 25 | 13 | 109 |
| 8 | 1184 | `Q1194` | LSU | 29 | 59 | 126 |
| 9 | 1353 | `Q1363` | LSU | 33 | 87 | 78 |
| 10 | 1522 | `Q1532` | LSU | 36 | 42 | 99 |
| 11 | 1691 | `Q1701` | LSU | 39 | 68 | 71 |
| 12 | 1860 | `Q1870` | LSU | 43 | 69 | 72 |
| 13 | 2029 | `Q2039` | LSU | 46 | 68 | 92 |
| 14 | 2198 | `Q2208` | LSU | 50 | 74 | 102 |
| 15 | 2367 | `Q2377` | LSU | 53 | 49 | 176 |
| 16 | 2536 | `Q2546` | dieu-tra-loi | 59 | 74 | 139 |
| 17 | 2705 | `Q2715` | dieu-tra-loi | 65 | 30 | 86 |
| 18 | 2874 | `Q2884` | dieu-tra-loi | 71 | 23 | 129 |
| 19 | 3043 | `Q3053` | dieu-tra-loi | 76 | 52 | 177 |
| 20 | 3212 | `Q3226` | dieu-tra-loi | 82 | 72 | 144 |

- **Trung bình mẫu 20 dòng:** Câu hỏi 50,0 ký tự; Câu trả lời 127,8 ký tự.

### 4.2. Thống kê toàn bộ kho 3.392 dòng
- **Độ dài câu hỏi:** Min = 7 ký tự | Max = 148 ký tự | Trung vị = 47,0 | Trung bình = **49,3 ký tự**.
- **Độ dài câu trả lời:** Min = 35 ký tự | Max = 505 ký tự | Trung vị = 120,0 | Trung bình = **132,0 ký tự**.
- **Theo từng khối:**
  - `MOM` (608 dòng): Câu hỏi trung bình 42,4 ký tự | Trả lời trung bình 174,8 ký tự (max 505).
  - `LSU` (1.790 dòng): Câu hỏi trung bình 52,4 ký tự | Trả lời trung bình 108,3 ký tự (max 305).
  - `dieu-tra-loi` (994 dòng): Câu hỏi trung bình 47,8 ký tự | Trả lời trung bình 148,5 ký tự (max 468).

### 4.3. Kết luận về Thông số Thời gian
1. **Dung lượng context rất tối ưu:**
   Khi worker trích xuất top 1–3 cặp tham khảo để ghép vào prompt:
   - 1 cặp Q&A ≈ 200 – 250 ký tự.
   - 3 cặp Q&A ≈ 600 – 800 ký tự.
   - Toàn bộ payload gửi lên C-Agent (gồm System Prompt + 3 cặp ngữ cảnh + câu hỏi người dùng) chỉ dao động khoảng **1.000 – 1.500 ký tự (khoảng 250 – 400 token)**.
2. **Khả thi về Timeout:**
   Với prompt đầu vào cực kỳ ngắn gọn và câu trả lời đầu ra mục tiêu cũng ngắn gọn, thời gian suy luận của Flowise AgentFlow trên CMCTS sẽ ổn định trong khoảng **20 – 40 giây** (khớp với thực tế đo probe 30,76s).
   - Ngưỡng **`timeout = 60s`** là hoàn toàn hợp lý, vừa đủ biên an toàn dự phòng mạng mà không gây treo lâu cho người dùng.
3. **Khả thi về Retry:**
   - Cơ chế **`max_retries = 1`** với giãn cách **`2–3 giây`** là chính xác. Nếu đặt retry 2–3 lần thì tổng thời gian chờ có thể lên đến 90s–120s, vi phạm SLA giao diện người dùng.

---

## 5. Kết luận & Khuyến nghị cho vé WIRE-QA-CAGENT-PC0575

### 5.1. Phán quyết nghiệm thu
- **Kết quả:** **ĐẠT (OK ĐỂ NỐI)**.
- Dữ liệu `wire-qa-mapping.jsonl` do `opencode` trích xuất và bản đặc tả `wire-cagent-spec.md` do `agy` lập **hoàn toàn tương thích kỹ thuật**, sạch sẽ, không có lỗi cấu trúc hay dữ liệu cản trở.

### 5.2. Khuyến nghị cho thợ triển khai vé WIRE
1. **Ghép template tham khảo linh hoạt:** Trong prompt gửi C-Agent, dùng trực tiếp `source`, `category`, `id`, `question`, `answer` từ JSONL. Không cần gượng ép trường `Bối cảnh:` riêng biệt.
2. **Cấu hình mã hóa UTF-8:** Khi đọc file JSONL hoặc in nhật ký terminal trên Windows (máy KDTVN-PC0575 dùng bảng mã hệ thống), phải luôn khai báo tường minh `encoding="utf-8"` để không phát sinh `UnicodeEncodeError` với tiếng Việt và tiếng Nhật/Trung.
3. **Tái sử dụng nguyên vẹn 3 câu demo:** Kịch bản demo trong Mục 5 của spec đã được xác nhận khớp 100% với các bản ghi `Q3401`/`Q3317`, `Q0001`, `Q0825`. Có thể đưa ngay vào test case tự động hoặc kịch bản kiểm thử giao diện.
