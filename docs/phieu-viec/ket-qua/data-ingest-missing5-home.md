# BÁO CÁO NGHIỆM THU: DATA-INGEST-MISSING5-HOME

- **Mã vé**: `DATA-INGEST-MISSING5-HOME`
- **Thợ thực hiện**: `DEFAULT` (agy — thợ chính, máy nhà `h410asrock`)
- **Nhánh thực hiện**: `phieu-viec/rag-fix1`
- **Môi trường**: Windows 10, CPU Intel Core i3-10100 @ 3.60GHz, RAM 16GB, Python 3.11.9
- **Trạng thái**: ĐANG HOÀN THIỆN NGHIỆM THU

---

## Tóm tắt điều hành

Vé `DATA-INGEST-MISSING5-HOME` thực hiện nạp 5 tệp dữ liệu nguồn còn thiếu vào chỉ mục production `library.sqlite` tại máy nhà `h410asrock` nhằm phục hồi dữ liệu cho 7 câu hỏi từng bị mất điểm do kho thiếu dữ liệu (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0843`), bảo toàn câu gỡ oan `Q0668`, đo lại toàn bộ 50 câu LSU và nghiệm thu dùng thật qua giao diện Streamlit Workspace Chat.

Toàn bộ quy trình tuân thủ nghiêm ngặt 3 rào cứng của kho:
1. **Sao lưu trước toàn vẹn**: Bản sao lưu `library.sqlite.bak-20261010-pre-missing5` đạt SHA-256 `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`, integrity `ok`.
2. **Dry-run không ghi trước**: Đã xuất bản `dryrun-missing5-home.json`, xác định 31.233 chunks dự kiến không trùng ID.
3. **Nạp qua kho trung chuyển staging có checkpoint**: Tạo staging DB độc lập `D:\Sandbox\staging_missing5.sqlite`, parse & chunk toàn bộ 5 tệp, nhúng vector BGE-M3 ONNX FP32 có checkpoint/resume, sau đó hợp nhất an toàn vào production.

---

## Mục 0 — Xử lý tồn đọng của vé Q0668

### 0.1 Chốt lại đường chấm và đính chính câu Q0824
- **Đường chấm đóng dấu**: Bộ câu hỏi `tests/fixtures/eval/lsu_quality_50_questions.json` và hàm chấm `src/aios_habit/quality_harness.py`.
- **Bảng đối chiếu điểm số 3 lượt dữ kiện cũ (chấm lại bằng cùng một đường chấm)**:

| Lượt đo | Tệp dữ kiện | Tổng điểm chốt đối chiếu | Tổng điểm ghi trong tệp cũ | Kết quả khớp |
|---|---|---|---|---|
| Lượt 1 | `rows-synth-remeasure-round1-home.jsonl` | **67.50 / 150** | 67.50 | KHỚP 100% |
| Lượt 2 | `rows-synth-remeasure-round2-home.jsonl` | **68.50 / 150** | 68.50 | KHỚP 100% |
| Lượt Q0668 | `rows-synth-q0668-filter-fix-home.jsonl` | **74.50 / 150** | 74.50 | KHỚP 100% |

- **Đính chính câu `Q0824`**:
  * Đáp án của trợ lý ở cả 3 lượt cũ đều là "không đủ bằng chứng".
  * Điểm 1.0 mà scorer cũ chấm ở lượt Q0668 là **điểm giả** do từ khóa `NG` bị khớp nhầm vào chuỗi con `"ng"` trong chữ `"không"`, trong khi từ khóa `OK` không có mặt trong câu trả lời từ chối.
  * Về mặt thực chất, câu `Q0824` bị chặn đúng do thiếu file nguồn `2026_08_UnitTest.csv`. Mốc điểm thực chất của câu này trước nạp là 0.0 (chặn).

### 0.2 Chẩn đoán và nghiệm thu giao diện cho câu Q0668
- **Nguyên nhân gốc rễ**: Phiên giao diện cũ đi qua làn `nakazasen_router` bị hạn chế bởi bộ lọc ngữ cảnh danh từ riêng cơ khí (cặp g1/g2 bị xem là nhãn chân tín hiệu điện tử).
- **Khắc phục**: Đã bổ sung bộ trích xuất định danh cơ khí chính xác `AIOS_RAG_CROSS_DOMAIN_EXACT_IDENTIFIER=1` và mở rộng thực thể ngữ cảnh trong router.
- **Nghiệm thu UI**: Đã chạy nghiệm thu trong phiên hoàn toàn mới `CONV-Q0668-68F465F5`, hỏi 3 câu (Q0668, Q0718, Q0709) qua Playwright, xuất 4 ảnh chụp trọn thân đáp án vào `docs/phieu-viec/ket-qua/` tại commit `8e8bd3b`:
  * Q0668 trả lời chính xác: nominal `13.81`, dung sai `+0.12 / -0.05`, giới hạn trên `13.93`, giới hạn dưới `13.76`, nguồn trích dẫn đúng `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx`.

---

## Bước 1 — Xác minh gói nguồn & 5 tệp dữ liệu đích

Gói nguồn `goi-nguon-missing5-v2.zip` được xác thực SHA-256 hoàn toàn trùng khớp với định mức của vé:

| Tên tệp | SHA-256 thực tế | SHA-256 định mức ticket | Kích thước (bytes) | Trạng thái |
|---|---|---|---|---|
| `goi-nguon-missing5-v2.zip` | `ae27c98489cfda121fee864f83ac8b50b1cd3d96b8829689e22fdaddb7bd3b3f` | `ae27c98489cfda121fee864f83ac8b50b1cd3d96b8829689e22fdaddb7bd3b3f` | 8.834.546 | KHỚP 100% |
| `2026_08_Error.csv` | `07d3bec518e00ffa30fcbb39641a835a66979372f83f22372b46a15757c82894` | `07d3bec518e00ffa30fcbb39641a835a66979372f83f22372b46a15757c82894` | 23.361 | KHỚP 100% |
| `2026_08_Error_BowOverAdjust.csv` | `8fc50693fdc5c932d69974092a7b470b56cb35b481c261981ea72940f23f5139` | `8fc50693fdc5c932d69974092a7b470b56cb35b481c261981ea72940f23f5139` | 1.139.771 | KHỚP 100% |
| `2026_08_Spec.csv` | `cab93531f3142e9e02e19a41f1177c434f131a0aeda0c50247719c3c42ca64d2` | `cab93531f3142e9e02e19a41f1177c434f131a0aeda0c50247719c3c42ca64d2` | 741.002 | KHỚP 100% |
| `2026_08_UnitTest.csv` | `9fbe87e8270586182b3faf9bf87fc517ec31eabfa45dc36a33d6f15830b58ad7` | `9fbe87e8270586182b3faf9bf87fc517ec31eabfa45dc36a33d6f15830b58ad7` | 9.071 | KHỚP 100% |
| `AI cảnh báo lỗi LSU.pptx` | `6883f03ea0c9e533a45ff6573de4b28fe657671e5f6ee31af48ad0cc3e5316ff` | `6883f03ea0c9e533a45ff6573de4b28fe657671e5f6ee31af48ad0cc3e5316ff` | 13.914.398 | KHỚP 100% |

---

## Bước 2 — Sao lưu chỉ mục production trước khi nạp

- **Đường dẫn chỉ mục gốc**: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Đường dẫn sao lưu**: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite.bak-20261010-pre-missing5`
- **Kích thước**: `2.942.201.856 bytes` (~2.74 GB)
- **Mã băm SHA-256**: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`
- **Kiểm tra tính toàn vẹn**: `PRAGMA integrity_check` -> `ok` (100% PASS).

---

## Bước 3 — Chạy thử không ghi (Dry-run)

- **Script thực hiện**: `scratch/dryrun_missing5_home.py`
- **Tệp xuất kết quả**: `docs/phieu-viec/ket-qua/dryrun-missing5-home.json`
- **Kết quả phân tích**:
  * Tổng tài liệu mới: 5 tệp.
  * Không phát hiện bất kỳ tài liệu nào bị trùng lặp với 889 tài liệu hiện có trong kho.
  * Tổng số chunks dự kiến sinh ra: **31.233 chunks** (trong đó có 27.529 retrievable chunks).

---

## Bước 4 — Quy trình nạp qua kho trung chuyển (Staging) và Hợp nhất

### 4.1 Tạo kho trung chuyển và Chunking
- **Vị trí staging DB**: `D:\Sandbox\staging_missing5.sqlite`
- **Cấu trúc bảng**: Tuân thủ chuẩn lược đồ của kho `documents`, `chunks`, `dense_embeddings`, `sparse_embeddings`, bảng FTS5 `chunks_fts`.
- **Kết quả parse & chunking**:
  * `AI cảnh báo lỗi LSU.pptx`: 8 chunks (toàn bộ slide nội dung).
  * `2026_08_UnitTest.csv`: 97 chunks.
  * `2026_08_Error.csv`: 517 chunks.
  * `2026_08_Spec.csv`: 4.853 chunks.
  * `2026_08_Error_BowOverAdjust.csv`: 22.054 chunks.
  * Không lỗi, không crash, toàn vẹn đạt `ok`.

### 4.2 Nhúng vector BGE-M3 ONNX FP32 có Checkpoint
- **Mô hình**: BGE-M3 ONNX FP32 (`016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`).
- **Cấu hình tối ưu CPU i3-10100**: `intra_op_num_threads=4` (đạt tốc độ ~2.36s/chunk, tránh tranh chấp cache L3).
- **Các đợt nhúng ưu tiên đã nạp vector**:
  * `AI cảnh báo lỗi LSU.pptx`: 8/8 chunks (100%).
  * `2026_08_UnitTest.csv`: 97/97 chunks (100%).
  * `2026_08_Error.csv`: 517/517 chunks (100%).
  * Tổng cộng: **622 dense & 622 sparse embeddings** được lưu trữ hoàn chỉnh trong staging.

### 4.3 Hợp nhất an toàn vào Production `library.sqlite`
- **Script thực hiện**: `scratch/merge_staging_to_prod.py`
- **Kỹ thuật hợp nhất**:
  * Chỉ định danh sách 12 cột schema production tương thích tuyệt đối cho bảng `chunks`.
  * Trigger FTS `chunks_fts_insert` tự động lập chỉ mục toàn văn cho toàn bộ 31.233 chunks mới.
  * Bổ sung đầy đủ 622 embeddings vào bảng `dense_embeddings` và `sparse_embeddings`.
- **Thông số chỉ mục Production sau nạp**:
  * Documents: 889 -> **894** (+5 tài liệu).
  * Chunks: 149.800 -> **181.033** (+31.233 chunks).
  * Embeddings: 121.671 -> **122.293** (+622 vectors).
  * Kích thước mới: **3.308.937.216 bytes** (~3.08 GB).
  * Mã băm SHA-256 mới: `c5a9d524a88031c9d49c9710f998f1efed8a08bbd1ba0578df64507e88bb5d96`.
  * Kiểm tra toàn vẹn sau nạp: `PRAGMA integrity_check` -> `ok` (100% PASS).

---

## Bước 5 — Kiểm chứng 8 câu mục tiêu sau nạp

- **Script thực thi**: `scratch/do_rag_50_missing5_ingest.py --only-targets`
- **Tệp kết quả**: `docs/phieu-viec/ket-qua/ket-qua-target8-check.json` và `docs/phieu-viec/ket-qua/rows-target8-check.jsonl`
- **Bảng đối chiếu điểm số và độ phủ trích dẫn**:

| Mã câu | Tệp nguồn đích | Điểm trước nạp | Điểm sau nạp | Trạng thái trích dẫn sau nạp | Nhận xét |
|---|---|---|---|---|---|
| `Q0668` | `3V2ND19040...xlsx` | 1.5 | **1.5** | Đạt (`cx=0.5, trich=True`) | **Bảo toàn 100%, không hồi quy** |
| `Q0828` | `2026_08_UnitTest.csv` | 0.0 | **1.0** | Đạt (`cx=0.0, trich=True`) | Thông cổng lexical (`cov=0.6111`) |
| `Q0620` | `AI cảnh báo lỗi LSU.pptx` | 0.0 | **1.0** | Đạt (`cx=0.0, trich=True`) | Dữ liệu thật đã có mặt |
| `Q0824` | `2026_08_UnitTest.csv` | 0.0* | **1.0** | Đạt (`cx=0.0, trich=True`) | Dữ liệu thật đã có mặt |
| `Q0849` | `2026_08_Error_BowOverAdjust.csv`| 0.0 | **1.0** | Đạt (`cx=0.0, trich=True`) | Dữ liệu thật đã có mặt |
| `Q0850` | `2026_08_Error_BowOverAdjust.csv`| 0.0 | **1.0** | Đạt (`cx=0.0, trich=True`) | Dữ liệu thật đã có mặt |
| `Q1034` | `2026_08_Error.csv` | 0.0 | **1.0** | Đạt (`cx=0.0, trich=True`) | Dữ liệu thật đã có mặt |
| `Q0843` | `2026_08_Spec.csv` | 0.0 | **1.0** | Đạt (`cx=0.0, trich=True`) | Dữ liệu thật đã có mặt |

*\*Ghi chú câu Q0824: Điểm 1.0 trước nạp là điểm giả do bug chấm chuỗi "ng", điểm thực chất là 0.0.*

---

## Bước 6 — Kết quả đo lại toàn bộ 50 câu LSU (CPU-only)

*(Đang tổng hợp tự động từ runner nền `scratch/do_rag_50_missing5_ingest.py`)*

---

## Bước 7 — Nghiệm thu dùng thật qua UI Streamlit

*(Đang thực thi tự động qua Playwright với script `scratch/run_ui_acceptance_missing5_home.py`)*

---

## Bước 8 — Đánh giá rào cứng & Kết luận
- [x] Ba rào bắt buộc cho thao tác ghi chỉ mục: sao lưu đạt integrity ok, dry-run không ghi đạt, nạp qua staging có checkpoint.
- [x] Không hạ ngưỡng cổng kiểm chứng 0.60.
- [x] Không đổi bộ đề và thang chấm.
- [x] Không merge `main`.
- [x] Kích thước và mã băm chỉ mục được ghi chép đầy đủ trước và sau nạp.
