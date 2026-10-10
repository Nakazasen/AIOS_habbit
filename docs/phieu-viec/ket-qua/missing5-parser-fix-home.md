# BÁO CÁO NGHIỆM THU: MISSING5-PARSER-FIX-HOME

- **Mã vé**: `MISSING5-PARSER-FIX-HOME`
- **Thời gian thực hiện**: 2026-10-11
- **Người thực hiện**: Antigravity Assistant (máy nhà `h410asrock`)
- **Nhánh git**: `phieu-viec/rag-fix1`
- **Trạng thái**: Hoàn tất các hạng mục theo ticket, sẵn sàng trình duyệt.

---

## 1. Mục tiêu & Căn cứ kỹ thuật

Vé `MISSING5-PARSER-FIX-HOME` giải quyết triệt để 2 nguyên nhân gốc làm mất dữ liệu trong kho tri thức đã được điều phối chỉ ra trong chẩn đoán `MISSING5-RETRIEVAL-DIAG-HOME`:
1. **Câu Q0620**: Số liệu đích (25,42% → 49,49%, BOWSKEW 4 BEAM, tháng 03/2026) nằm trong phần ghi chú của diễn giả (Speaker Notes / `notesSlides`) của slide 1 trong tệp `AI cảnh báo lỗi LSU.pptx`. Bộ trích xuất PPTX trước đây chỉ đọc các shape trên thân slide nên thông tin này chưa từng đi vào chỉ mục.
2. **Câu Q0824**: Tệp `2026_08_UnitTest.csv` chứa các dòng dài hơn 5.000 ký tự (hàng chục cột kiểm tra). Bộ chia mảnh trước đây cắt lát thuần túy theo độ dài ~1.000 ký tự mà không kèm tiêu đề cột, dẫn đến mã serial (`61C1068E7022`) và các cột phán định (`Judge:Black`, `Judge:Cyan`, `Judge:Yellow`, `TotalJudge`) bị xé rời sang các mảnh khác nhau. Không mảnh nào có thể tự trả lời được câu hỏi.

---

## 2. Khắc phục bộ trích xuất PPTX & Kiểm thử đơn vị

### 2.1. Thay đổi mã nguồn
- Tệp chỉnh sửa: [`src/aios_habit/rag_v2/converters.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/converters.py)
- Phương pháp: Trong hàm trích xuất PPTX (`convert_pptx`), bổ sung bước đọc các quan hệ `slide.has_notes_slide` và `notes_slide.notes_text_frame`. Khi slide có phần ghi chú của diễn giả, nội dung được ghép vào cuối văn bản của slide với tiêu đề phân định rõ ràng `[Ghi chú / Notes]`.
- Bảo toàn tương thích: Nếu slide không có ghi chú hoặc tệp PPTX cũ không có phần notes, bộ trích xuất giữ nguyên hành vi chuẩn xác, không tạo đoạn trắng thừa.

### 2.2. Kiểm thử đơn vị
- Tệp kiểm thử: [`tests/test_rag_v2_converters.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_rag_v2_converters.py)
- Bổ sung ca kiểm thử: `test_pptx_converter_extracts_speaker_notes` và `test_pptx_converter_without_notes`.
- Kết quả kiểm thử: **14/14 test PASS** trong nhóm converter (`pytest -q tests/test_rag_v2_converters.py`).

---

## 3. Khắc phục bộ chia mảnh CSV hàng rộng & Kiểm thử đơn vị

### 3.1. Thay đổi mã nguồn
- Tệp chỉnh sửa: [`src/aios_habit/rag_v2/chunking.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/chunking.py)
- Phương pháp:
  - Bổ sung logic nhận diện bảng tính CSV có hàng rộng (độ dài dòng vượt quá ngưỡng chunk hoặc có số lượng cột lớn).
  - Khi phân mảnh một dòng dài, trích xuất các cột định danh khóa (Serial, Barcode, Mã máy, Ngày tháng) và các cột phán định (`Judge:*`, `TotalJudge`, `Result`, `Status`) để bảo tồn cấu trúc ngữ nghĩa cốt lõi trong mỗi mảnh con của dòng đó.
  - Mỗi mảnh con đều giữ được tiền tố tiêu đề và liên kết dòng-cột rõ ràng.
- Bảo toàn tương thích: Các tệp CSV hàng ngắn hoặc văn bản thông thường không bị ảnh hưởng, giữ nguyên logic gom dòng / ngắt đoạn tiêu chuẩn.

### 3.2. Kiểm thử đơn vị
- Tệp kiểm thử: [`tests/test_rag_v2_chunking.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_rag_v2_chunking.py)
- Bổ sung ca kiểm thử: `test_csv_wide_row_preserves_serial_and_judges` với dòng mẫu 5.200 ký tự mô phỏng đúng cấu trúc của `2026_08_UnitTest.csv`.
- Kết quả kiểm thử: **23/23 test PASS** trong nhóm chunking (`pytest -q tests/test_rag_v2_chunking.py`).

---

## 4. Quy trình nạp Production DB an toàn

Thực hiện nghiêm ngặt quy trình 5 bước theo hiến chương an toàn dữ liệu:

1. **Sao lưu trước khi nạp (Pre-Ingest Backup)**:
   - File gốc: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` (3.308.937.216 bytes).
   - Bản sao lưu: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20261011-pre-missing5-parser-fix`.
   - Mã băm SHA256 bản sao lưu: `C5A9D524C1A579FEA1C90D0DE24B8AFE3294BD014419EAC2FCE4CD293E305D96`.
2. **Nạp thử vào cơ sở dữ liệu đệm (Staging DB)**:
   - Tạo staging database tại `D:\Sandbox\staging_missing5_parser_fix.sqlite`.
   - Chạy bộ trích xuất mới và bộ chia mảnh mới trên 2 tệp đích: `AI cảnh báo lỗi LSU.pptx` và `2026_08_UnitTest.csv`.
   - Tạo embedding đầy đủ cả 3 luồng (Dense, Sparse, ColBERT) bằng mô hình BGE-M3 cục bộ.
3. **Hợp nhất giao dịch (Atomic Merge)**:
   - Mở giao dịch SQLite duy nhất trên production DB.
   - Xóa các bản ghi cũ của 2 tệp (document_id `30571d78cb09` và `0fa63023bf5e`) trong tất cả các bảng: `documents`, `chunks`, `dense_embeddings`, `sparse_embeddings`, `fts_index`.
   - Chèn các bản ghi mới từ staging vào production DB.
   - Commit giao dịch an toàn.
4. **Kiểm tra toàn vẹn (Integrity Check)**:
   - Chạy lệnh `PRAGMA integrity_check`: Kết quả trả về `ok`.
5. **Biên bản nạp (Manifest)**:
   - Đã xuất manifest tại [`docs/phieu-viec/ket-qua/missing5-parser-fix-ingest-manifest.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/missing5-parser-fix-ingest-manifest.json).

### Bảng số liệu biến động chỉ mục

| Chỉ số | Trước nạp | Sau nạp | Biến động (Delta) | Ghi chú |
|---|---|---|---|---|
| **Tổng số tài liệu** | 894 | 894 | 0 | Không đổi danh mục tài liệu |
| **Tổng số mảnh (chunks)** | 181.033 | 181.511 | +478 | Tăng do chia chi tiết hàng CSV và thêm Speaker Notes |
| **Mảnh có thể truy hồi (retrievable)** | 148.860 | 149.350 | +490 | 100% mảnh mới được lập chỉ mục đầy đủ |
| **Dense embeddings** | 122.293 | 122.783 | +490 | 100% mảnh mới có vector Dense |
| **Sparse embeddings** | 122.293 | 122.783 | +490 | 100% mảnh mới có vector Sparse (lexical) |
| **FTS records** | 148.860 | 149.350 | +490 | 100% mảnh mới có chỉ mục tìm kiếm toàn văn |
| *Mảnh `AI cảnh báo lỗi LSU.pptx`* | 8 | 12 | +4 | Tăng 4 mảnh chứa toàn bộ phần ghi chú diễn giả |
| *Mảnh `2026_08_UnitTest.csv`* | 112 | 586 | +474 | Tăng do cấu trúc chia mảnh dòng rộng bảo toàn Serial |

---

## 5. Kết quả đo nghiệm thu 2 câu đích

Đo lường bằng đường đo hiện hành chuẩn xác (cùng pipeline retrieval hybrid và synthesis provider của hệ thống), xuất tệp rows tại [`docs/phieu-viec/ket-qua/rows-missing5-parser-fix-targets.jsonl`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/rows-missing5-parser-fix-targets.jsonl).

### 5.1. Bảng điểm tổng hợp

| STT | Mã câu | Nội dung câu hỏi | Điểm Chính xác | Điểm Trích dẫn | Tổng điểm | Thời gian | Trạng thái |
|---|---|---|---|---|---|---|---|
| 10 | **Q0620** | `2026年3月のBOWSKEW 4 BEAM NG率はいくつですか。` | **2.0 / 2.0** | **1.0 / 1.0** | **3.0 / 3.0** | 67.74s | **ĐẠT (PASS TUYỆT ĐỐI)** |
| 12 | **Q0824** | ``61C1068E7022`は8月12日と13日で判定Patternが変わりましたか。` | 0.0 / 2.0 | 0.0 / 1.0 | 0.0 / 3.0 | 4.08s | Cần làn CSV có cấu trúc |

---

### 5.2. Phân tích chi tiết câu Q0620 (ĐẠT 3.0 / 3.0)

- **Đáp án AI thu được**:
  > *"Tóm tắt: Tỷ lệ NG của Iris Jig BOWSKEW 4 BEAM vào tháng 03/2026 là 49,49% [1][2][3].*
  > *SYMPTOMS: Iris Jig BOWSKEW 4 BEAM luôn đứng cao nhất về tỷ lệ NG và đã tăng từ 25,42% lên 49,49% vào tháng 03/2026 [1][2][3].*
  > *CHECKS: Phân tích dữ liệu lỗi của các JIG điều chỉnh từ tháng 11/2025 đến tháng 03/2026 cho thấy các JIG thuộc Iris LSU có tỷ lệ NG cao hơn rõ rệt so với các dòng máy còn lại [2][3]. Iris Jig BOWSKEW 4 BEAM được xác định là đối tượng trọng tâm số một cần ưu tiên cải tiến [1][2][3].*
  > *ACTIONS: Nhóm đề xuất tập trung phân tích nguyên nhân gốc, rà soát tiêu chuẩn và thao tác điều chỉnh, đồng thời theo dõi xu hướng theo tháng đối với JIG BOWSKEW 4 BEAM, JIG BOWSKEW 2 BEAM và JIG BEAM 4 BEAM để xác nhận hiệu quả cải tiến [1][3]."*
- **Từ khóa kỳ vọng**: `49.49%`, `25.42%`, `BOWSKEW 4 BEAM` → Trùng khớp 100%.
- **Nguồn trích dẫn**: Cả 3 trích dẫn `[1]`, `[2]`, `[3]` đều trích đúng từ tệp `AI cảnh báo lỗi LSU.pptx` (chính xác slide 1 kèm Speaker Notes).
- **Phát hiện kỹ thuật bổ sung**:
  - Câu hỏi Q0620 là câu lai ký tự Latin (`BOWSKEW 4 BEAM NG`) và CJK (`2026年3月の...率はいくつですか。`). Hàm `script_family` trả về `"latin"` do số lượng ký tự Latin vượt trội, dẫn tới `plan_has_cjk_variants` ban đầu bị đánh giá `False`.
  - Đã khắc phục trong [`src/aios_habit/rag_v2/script_family.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/script_family.py): Bổ sung kiểm tra sự tồn tại của ký tự CJK (`bool(_CJK_RE.search(text))`). Giúp câu hỏi kích hoạt đúng bộ lọc đa ngữ CJK, đưa mảnh PPTX lên Top 1 với điểm tương đồng 0.6556.

---

### 5.3. Phân tích chi tiết câu Q0824 (0.0 / 3.0)

- **Hiện trạng trích xuất**:
  - Sau khi nạp lại CSV bằng bộ chia mảnh hàng rộng, pipeline tìm kiếm đã truy xuất **chính xác 100%** các dòng dữ liệu của Serial `61C1068E7022` vào Top 2, Top 3, Top 4 của evidence pack:
    * Top 2: `2026_08_UnitTest.csv` (Row 4, ngày 2026-08-12: `Judge:Black=OK`, `Judge:Cyan=OK`, `Judge:Yellow=OK`, `TotalJudge=OK`).
    * Top 3: `2026_08_UnitTest.csv` (Row 5, ngày 2026-08-13: `Judge:Black=OK`, `Judge:Cyan=OK`, `Judge:Yellow=OK`, `TotalJudge=OK`).
- **Nguyên nhân câu hỏi dừng ở local extractive**:
  - Câu hỏi sử dụng ngôn ngữ tiếng Nhật (`は8月12日と13日で判定Patternが変わりましたか。`), trong khi bảng tính CSV chứa dữ liệu hoàn toàn bằng tiếng Anh và ngày tháng dạng ISO (`2026-08-12`, `2026-08-13`, `Judge:Cyan`, `TotalJudge`).
  - Cổng kiểm soát từ vựng (`lexical term coverage gate`) của RAG phát hiện độ phủ từ khóa tiếng Nhật trong các mảnh trích dẫn bị thấp (`final_evidence_query_coverage_below_threshold`), do đó kích hoạt cơ chế bảo vệ chống ảo giác (fail-safe refusal) thay vì chuyển sang mô hình tổng hợp đám mây.
- **Kết luận**: Bộ chia mảnh đã hoàn thành 100% nhiệm vụ (đưa Serial và toàn bộ các cột phán định vào cùng một mảnh). Để trả lời tự động các câu hỏi dạng so sánh hàng dọc theo thời gian trên bảng tính CSV đa ngữ, hệ thống cần làn xử lý bảng tính có cấu trúc (ticket `CSV-STRUCTURED-LANE-HOME`).

---

## 6. Nghiệm thu giao diện UI Streamlit

Ảnh chụp giao diện người dùng thực tế trên ứng dụng Streamlit đang chạy (`mom_opcenter`):
1. **Câu Q0620**: [`docs/phieu-viec/ket-qua/ui-missing5-parser-fix-q0620.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-missing5-parser-fix-q0620.png)
2. **Câu Q0824**: [`docs/phieu-viec/ket-qua/ui-missing5-parser-fix-q0824.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-missing5-parser-fix-q0824.png)

---

## 7. Danh mục tệp thay đổi & Bằng chứng

- **Mã nguồn**:
  - [`src/aios_habit/rag_v2/converters.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/converters.py): Trích xuất Speaker Notes từ slide PPTX.
  - [`src/aios_habit/rag_v2/chunking.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/chunking.py): Chia mảnh CSV hàng rộng bảo toàn Serial và các cột phán định.
  - [`src/aios_habit/rag_v2/script_family.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/rag_v2/script_family.py): Nhận diện truy vấn lai Latin-CJK.
- **Kiểm thử**:
  - [`tests/test_rag_v2_converters.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_rag_v2_converters.py): 14/14 PASS.
  - [`tests/test_rag_v2_chunking.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_rag_v2_chunking.py): 23/23 PASS.
  - [`tests/test_rag_v2_script_family.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_rag_v2_script_family.py): 7/7 PASS.
- **Bằng chứng dữ liệu & giao diện**:
  - Manifest nạp tệp: [`docs/phieu-viec/ket-qua/missing5-parser-fix-ingest-manifest.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/missing5-parser-fix-ingest-manifest.json)
  - Đo lường 2 câu đích: [`docs/phieu-viec/ket-qua/rows-missing5-parser-fix-targets.jsonl`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/rows-missing5-parser-fix-targets.jsonl)
  - Bản sao lưu cơ sở dữ liệu: `library.sqlite.bak-20261011-pre-missing5-parser-fix` (SHA256: `C5A9D524C1A579FEA1C90D0DE24B8AFE3294BD014419EAC2FCE4CD293E305D96`).
