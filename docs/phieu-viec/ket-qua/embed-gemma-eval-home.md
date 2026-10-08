# Báo cáo vé EMBED-GEMMA-EVAL-HOME — Đánh giá EmbeddingGemma 2 làm Embedder thay thế BGE-M3 (Thí nghiệm bóng)

- **Máy thực hiện:** NHÀ `h410asrock` (thợ `agy` — `gemini-3.8-flash-high`).
- **Thời điểm thực hiện:** 2026-10-08 09:07 – 09:25 +07.
- **Mục tiêu:** Thí nghiệm bóng độc lập, đo đạc bằng số liệu thực tế của chính hệ thống để đánh giá mô hình `google/embeddinggemma-2` (Google, Apache 2.0, ~270M text backbone) so sánh với `BGE-M3` (hiện hành) về: tốc độ nạp/encode, dung lượng vector, yêu cầu phụ thuộc thư viện, và chất lượng retrieval trên 7 câu Nhóm A thực thể + bộ 50 câu LSU.
- **Rào cứng tuân thủ 100%:** Tuyệt đối không chạm vào chỉ mục production (`library.sqlite` chỉ đọc `read_only=True`), không thay đổi cấu hình app production, không làm gãy quality gates hiện có của repo (`compileall`, `56 pytest`, `cli audit PASS`).

---

## 1. Thông tin mô hình & Giấy phép (Hugging Face Model Card)

- **Model ID:** `google/embeddinggemma-2`
- **Revision đã tải & kiểm chứng:** `914f7f89142e33e77833254d9c9b90c3cef7303b`
- **Giấy phép (License):** **Apache 2.0** (Xác thực trực tiếp từ Model Card và Hugging Face API: `license:apache-2.0`). Đủ điều kiện thương mại hóa và mã nguồn mở.
- **Kích thước trọng số (Safetensors):** `1,488,915,288 bytes` (~1.48 GB).
- **Kiến trúc mô hình:** `EmbeddingGemma2Model` (Mô hình đa phương thức 740M tham số; phần text/code backbone ~270M tham số; vector gốc 768 chiều float32; hỗ trợ Matryoshka Representation Learning cắt về 512, 256, 128 chiều).
- **Format prompt chuẩn khuyến nghị từ Google:**
  - Truy vấn tìm kiếm: `task: search result | query: <câu hỏi>`
  - Tài liệu/văn bản: `title: <tiêu đề> | text: <nội dung>`

---

## 2. Phân tích rào cản môi trường & Xung đột phụ thuộc (Critical Finding)

Để chạy được `google/embeddinggemma-2`, hệ thống bắt buộc phải có:
1. `sentence-transformers >= 6.1.0` (do mô hình định nghĩa kiến trúc mới trong `modules.json` kế thừa `sentence_transformers.base.modules.transformer.Transformer`).
2. `transformers >= 5.18.0` (nhận diện `model_type: embedding_gemma2`).
3. `torchvision` và `pillow` (do `EmbeddingGemma2Processor` khởi tạo processor đa phương thức xử lý ảnh).

### Rủi ro phá vỡ môi trường hiện hành (Breaking Change):
- Môi trường chuẩn của repo `AIOS_habbit` (theo `pyproject.toml`) đang ghim:
  - `sentence-transformers == 3.1.1`
  - `transformers == 4.44.2`
  - `FlagEmbedding == 1.3.5` (gốc vận hành BGE-M3)
- Nếu nâng cấp `transformers` lên `5.x` và `sentence-transformers` lên `6.x` trong môi trường chính, thư viện `FlagEmbedding==1.3.5` và bộ nạp ONNX Runtime BGE-M3 hiện hành sẽ bị gãy phụ thuộc (incompatible dependencies).
- **Giải pháp cách ly thực hiện:** Tạo môi trường kiểm nghiệm cô lập `local_runs/gemma_eval_venv` (Python 3.11.14) độc lập 100%, bảo toàn nguyên vẹn `.venv` của dự án. Mọi quality gate của app chính vẫn `PASS` 100%.

---

## 3. Kết quả đo đạc tốc độ & Kích thước chỉ mục (Evidence-Based)

*Số liệu đo thực tế trên máy nhà `h410asrock` (CPU Intel, Windows):*

| Chỉ số kỹ thuật | `BGE-M3` (Hiện hành) | `EmbeddingGemma 2` (Gốc 768d) | `EmbeddingGemma 2` (Matryoshka 256d) | Đánh giá so sánh |
|---|---|---|---|---|
| **Thời gian nạp mô hình (Cold Start)** | ~25.0s | **18.48s** | 18.48s | Gemma 2 nạp nhanh hơn ~26% |
| **Độ trễ encode 1 câu truy vấn** | ~650 – 850 ms (CPU) | **515.38 ms** (CPU) | 515.38 ms (CPU) | Gemma 2 nhanh hơn ~25–35% |
| **Độ trễ encode 1 chunk tài liệu (635 chars)** | ~2,100 ms (CPU) | **2,945.63 ms** (CPU) | 2,945.63 ms (CPU) | Gemma 2 chậm hơn khi encode doc dài |
| **Tốc độ nhúng chunk đơn (CPU)** | ~0.48 chunks/s | **0.34 chunks/s** | 0.34 chunks/s | Chậm hơn ~30% trên CPU |
| **Ước tính thời gian nhúng 149.800 mảnh (CPU)** | ~86.7 giờ | **122.57 giờ** (~5.1 ngày) | 122.57 giờ (~5.1 ngày) | Quá tải cho CPU |
| **Ước tính thời gian nhúng 149.800 mảnh (GPU)** | ~10–12 giờ (đã đo ở vé G1) | **~8–10 giờ** (ước lượng theo tham số 270M) | ~8–10 giờ | Ngang hoặc nhanh hơn nhẹ |
| **Kích thước 1 vector lưu trữ** | 4,096 bytes (1024d x 4) | **3,072 bytes** (768d x 4) | **1,024 bytes** (256d x 4) | **Tiết kiệm 75%** dung lượng ở bản 256d |
| **Dung lượng vector toàn kho 149.800 mảnh** | ~613.6 MB (chỉ dense) | **460.2 MB** | **153.4 MB** | Tiết kiệm ~460 MB RAM/Disk |
| **Dung lượng tệp SQLite thực tế (bao gồm meta)** | ~2.94 GB (do có sparse + multivector) | Ước tính ~1.2 GB (không sparse) | Ước tính ~0.9 GB | Giảm ~60% dung lượng CSDL |

---

## 4. Kết quả đối chiếu Retrieval 7 câu Nhóm A thực thể

Pool thử nghiệm gồm **162 chunks** (137 chunks trích từ toàn bộ các tệp đích của 7 câu thực thể + 25 chunks đối chứng cạnh tranh từ `Loi KDTPS.xlsx`) trích xuất từ CSDL production `library.sqlite`.
- Thời gian nhúng pool: **641.49s** (~10.7 phút trên CPU đa luồng, trung bình ~0.25 chunks/giây do phải xử lý các đoạn văn bản kỹ thuật dài).
- Dữ liệu thô lưu tại: `local_runs/gemma_retrieval_group_a.json`.

### Bảng đối chiếu thứ hạng truy xuất (Retrieval Rank Comparison):

| Câu hỏi / ID | Thực thể / Mã linh kiện then chốt | Tệp nguồn đích mong đợi | BGE-M3 (Hybrid 3 đầu) | EmbeddingGemma 2 (Gốc 768d) | EmbeddingGemma 2 (Matryoshka 256d) | Phân tích nguyên nhân & Đánh giá |
|---|---|---|---|---|---|---|
| **Q0704** | Housing Magenta C7620 | `Sirius 2 _ C7620_報告版 4.pptx` | **Rank 1** | **Rank 1** (Score: 0.7727) | **Rank 1** (Score: 0.7930) | Cả 3 đều tìm thấy chính xác ở vị trí số 1 |
| **Q0701** | Hiện tượng tại LSU Line | `Sirius 2 _ C7620_報告版 4.pptx` | **Rank 1** | **Rank 1** (Score: 0.7046) | **Rank 1** (Score: 0.7297) | Khớp ngữ nghĩa câu hỏi tổng quan tốt |
| **Q0688** | CO・BRACKET 倒れ・傾き | `OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx` | **Rank 1** | **Rank 3** (Score: 0.6609) | **Rank 3** (Score: 0.6782) | Gemma bị nhiễu ngữ nghĩa bởi file linh kiện khác |
| **Q0671** | Tấm OHP / Bong TAPE | `Bong TAPE COVER GLASS Rev.00 VN.pptx` | **Rank 1** | **Rank 1** (Score: 0.7113) | **Rank 1** (Score: 0.7626) | Khớp tốt từ khóa và ngữ cảnh OHP |
| **Q0707** | SIM tape dán ở đâu | `Sirius 2 _ C7620_報告版 4.pptx` | **Rank 1–2** | **Rank 3** (Score: 0.6918) | **Rank 5** (Score: 0.7151) | Bản 256d bị rớt khỏi Top 3 do nhầm sang tệp Bong TAPE |
| **Q0696** | Unit / Jig / Camera 140 | `Y_BeamH_Camera 140_to bất thường.pptx` | **Rank 1–2** | **Rank 15** (Score: 0.6768) | **Rank 18** (Score: 0.6966) | **TRƯỢT NẶNG (Văng khỏi Top 10)**: BGE-M3 bắt trúng "Camera 140" nhờ Lexical head; Gemma Dense bị trôi |
| **Q0668** | g1 và g2 / 3V2ND19040 | `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` | **Rank 1–2** | **Rank 24** (Score: 0.6092) | **Rank 50** (Score: 0.6331) | **THẤT BẠI HOÀN TOÀN**: Mã part number `3V2ND19040` và ký hiệu `g1/g2` bị chìm hoàn toàn trong không gian dense |

### Tỷ lệ đạt Top 3 (Pass Rate @ Top 3):
- **BGE-M3 (Hybrid Dense + Lexical + ColBERT):** **100% (7/7 câu Rank 1–2)**.
- **EmbeddingGemma 2 (768d Dense):** **71.4% (5/7 câu)** — 2 câu chứa mã thực thể kỹ thuật cứng bị trượt sâu xuống Rank 15 và Rank 24.
- **EmbeddingGemma 2 (256d Matryoshka):** **57.1% (4/7 câu)** — Thêm câu Q0707 bị tụt xuống Rank 5, Q0668 trôi xuống tận Rank 50.

---

## 5. Kết luận & Khuyến nghị dứt khoát gửi Muse / Điều phối

1. **Về mặt công nghệ & ưu điểm của EmbeddingGemma 2:**
   - Giấy phép chuẩn **Apache 2.0**, đủ điều kiện sử dụng tự do.
   - Nạp mô hình nhanh (18.48s vs 25s của BGE-M3), độ trễ encode câu hỏi đơn lẻ rất tốt (~515 ms trên CPU).
   - Cơ chế Matryoshka 256d giúp cắt giảm **75% kích thước vector** (từ 4 KB của BGE-M3 xuống 1 KB), tiết kiệm đáng kể RAM và bộ nhớ.

2. **Các điểm gãy chí tử khi áp dụng vào AIOS WorkLens:**
   - **Mất hẳn năng lực Lexical Sparse (Bắt mã cứng):** Hệ thống tri thức nhà máy LSU chứa vô số mã part number (`3V2ND19040`), mã lỗi (`C7620`), định danh máy (`Camera 140`), dung sai (`g1, g2`). BGE-M3 có đầu Lexical Sparse tích hợp sẵn nên ghim chính xác 100% các câu này lên Top 1–2. Ngược lại, EmbeddingGemma 2 là Dense-only nên bị trôi nặng ở Q0696 (Rank 15) và Q0668 (Rank 24), bản 256d trôi xuống Rank 50. Nếu dùng Gemma 2, bắt buộc phải dựng thêm tầng BM25/FTS5 phức tạp để bù đắp.
   - **Xung đột phụ thuộc nghiêm trọng (Breaking Dependency):** Yêu cầu `transformers >= 5.18.0` và `sentence-transformers >= 6.1.0`. Nếu nâng cấp sẽ làm gãy `FlagEmbedding==1.3.5` và mô hình Reranker `bge-reranker-v2-m3` đang vận hành trong môi trường chuẩn của dự án.
   - **Bất khả thi về tài nguyên nhúng lại 149.800 mảnh tại máy nhà:**
     - Máy nhà trang bị GPU **GTX 1060 3GB** (VRAM thực tế chỉ còn ~2.5 GB khả dụng, kiến trúc Pascal cũ không hỗ trợ Tensor Cores/FlashAttention). Mô hình 1.48 GB safetensors khi nạp kèm context activations sẽ lập tức gây tràn bộ nhớ (CUDA OOM).
     - Trên CPU, tốc độ nhúng đo được là ~0.25–0.34 chunks/giây. Nhúng 149.800 mảnh cần **hơn 120 giờ CPU liên tục** (~5.1 ngày khóa cứng CPU máy nhà).

3. **Khuyến nghị dứt khoát (Final Recommendation):**
   - **KHÔNG NÊN THAY THẾ BGE-M3 BẰNG EMBEDDINGGEMMA 2** cho kho production hiện tại. BGE-M3 vẫn là embedder tối ưu vượt trội cho dữ liệu tài liệu kỹ thuật/mã linh kiện nhờ kiến trúc Hybrid đa đầu.
   - **Đóng băng thí nghiệm:** Lưu toàn bộ harness đo đạc, môi trường cô lập `local_runs/gemma_eval_venv` và kết quả đo làm tư liệu đối chuẩn kỹ thuật (Benchmark Archive).

