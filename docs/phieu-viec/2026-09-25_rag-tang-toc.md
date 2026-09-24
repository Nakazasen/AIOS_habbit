# PHIẾU VIỆC: Tăng tốc RAG v2 trên laptop i5 / 16GB RAM / không GPU

> Dành cho AI agent chạy local, làm trực tiếp trong repo `AIOS_habbit` trên máy
> người dùng. Repo local: `D:\Sandbox\AIOS_habbit`, nhánh `main`.
> Số dòng ghi trong phiếu là ước lượng từ lần đọc code trước — khi làm, hãy tự
> xác minh lại tên hàm/dòng trong code thực tế.

## 1. Bối cảnh

- Vùng code chính: `src/aios_habit/rag_v2/` (`index.py`, `semantic.py`,
  `retrieval_backends.py`, `bge_subprocess_worker.py`, `bge_subprocess_client.py`,
  `query_planning.py`, `pipeline.py`, `ingestion_service.py`, `ingestion_workers.py`)
  và `src/aios_habit/query_intent.py`, `src/aios_habit/rag_core_profiles.py`.
- Máy mục tiêu: laptop i5, 16GB RAM, không GPU, Windows, chạy app Streamlit.
- Reranker (`bge-reranker-v2-m3`) đã tắt, **không cần đụng tới**.
- Vector store hiện tại: SQLite + BLOB (bảng `chunk_embeddings`), **không** có
  FAISS/Chroma/PQ/IVF/HNSW. Dense search đang là vòng lặp Python thuần.

## 2. Mục tiêu đo được

1. Query latency với ~50k chunks: từ 30–120s → **dưới 5s** (câu hỏi chi tiết).
2. Câu hỏi chung chung: **có câu trả lời trong <10s**, không còn treo rồi abstain.
3. Ingest: embed nhanh hơn rõ rệt, **recall@10 chênh lệch <1%** so với trước.
4. Không làm đỏ test cũ (`pytest tests/`).

## 3. FIX 1 — Numpy-hoá dense search (làm trước, rủi ro thấp nhất)

**Hiện trạng:** `index.py::dense_candidates` (khoảng dòng 1775) SELECT từng blob
vector, `_unpack_vector`, rồi tính `cosine_similarity` bằng `sum(float(a)*float(b)...)`
thuần Python trong `semantic.py` (~dòng 300). Mỗi câu hỏi chạy tối đa 8 biến thể
(`query_planning.py::_MAX_VARIANTS=8`), mỗi biến thể quét toàn bộ chunk.

**Yêu cầu:**
- Load toàn bộ vector dense một lần thành numpy matrix `float32` (N×d), cache trong
  RAM của tiến trình (thêm config giới hạn, ví dụ chỉ cache khi N×d×4 byte < 2GB).
- Tính điểm bằng `scores = matrix @ qvec` (chuẩn hoá vector trước nếu chưa chuẩn hoá),
  dùng `argpartition` lấy top-k rồi sort. Giữ nguyên ngưỡng/loại trừ như code cũ.
- **Kết quả phải identical với code cũ**: viết test so sánh thứ tự top-k của hai
  implementation trên cùng dữ liệu, assert giống nhau 100%.
- Giữ nguyên interface hàm để `pipeline.py` và `adaptive_retrieval.py` không phải sửa.

**Nghiệm thu:** benchmark trên ≥10k chunks thật, nhanh hơn **≥50 lần**, kết quả top-k
giống hệt bản cũ.

## 4. FIX 2 — ONNX int8 cho BGE-M3 (đây mới là "lượng tử hoá" đúng nghĩa)

**Hiện trạng:** BGE-M3 (`BAAI/bge-m3`, 1024 chiều, ~2.3GB) chạy PyTorch qua
`FlagEmbedding.BGEM3FlagModel` trong subprocess (`bge_subprocess_client.py:122`,
`bge_subprocess_worker.py`). Mỗi lần init còn hash SHA-256 toàn bộ 2.3GB
(`retrieval_backends.py::verify_model_tree`, ~dòng 54). `max_length=2048` trong khi
chunk chỉ ~600–1000 ký tự.

**Yêu cầu:**
1. Viết `scripts/export_bge_m3_onnx.py`: dùng `optimum[onnxruntime]` export BGE-M3
   sang ONNX, rồi dynamic quantization int8 → lưu vào `models/bge-m3-onnx-int8/`.
   Repo đã có sẵn dependency `onnxruntime`.
2. Worker mới (hoặc nhánh trong `bge_subprocess_worker.py`) load model bằng
   onnxruntime `CPUExecutionProvider`, `intra_op_num_threads` = số core CPU.
   **Giữ nguyên interface** `embed_documents()` / `embed_query()` để backend gọi
   như cũ.
3. Đặt `max_length=512`. Kiểm chứng: embed thử 1 chunk với 512 vs 2048, cosine
   giữa hai vector phải ≈ 1.0 (vì chunk không bao giờ dài tới 2048 token).
4. Cache kết quả `verify_model_tree`: lưu (sha256, timestamp, kích thước file) vào
   file cạnh model, lần sau chỉ kiểm tra nhanh, không hash lại 2.3GB.
5. Thêm config flag, ví dụ `BGE_BACKEND=onnx_int8` (mặc định) / `pytorch` (rollback).
   Đường PyTorch cũ **giữ nguyên**, không xoá.

**Nghiệm thu:** tốc độ embed nhanh hơn **≥2 lần**; recall@10 trên tập câu hỏi test
chênh lệch **<1%** so với bản PyTorch.

## 5. FIX 3 — Định tuyến summary-first cho câu hỏi chung chung

**Hiện trạng:** mọi câu hỏi đều đi 8 biến thể × quét toàn bộ chunk. Câu hỏi chung
chung cho vector "nhạt", điểm evidence thấp → chậm mà cuối cùng hay bị abstain
(`EvidenceAnswerMode.ABSTAIN`), hệ được thiết kế fail-closed.

**Yêu cầu:**
1. Phân loại độ cụ thể của câu hỏi trong `query_planning.py` / `query_intent.py`:
   intent thuộc nhóm tổng quan (`summarize_document`, `open_ended_research`, hoặc
   query ngắn và không chứa entity/tên tài liệu cụ thể) → chế độ `overview`.
2. Chế độ `overview`: **chỉ search trên summary chunk** (ingest đã tạo 1 summary
   chunk cho mỗi document) để chọn top 10–15 tài liệu liên quan nhất, rồi tổng hợp
   câu trả lời từ các summary. Không quét toàn bộ chunk, chỉ dùng 2–3 biến thể.
3. Two-stage cho câu hỏi ở mức trung bình: stage 1 chọn top tài liệu từ summary,
   stage 2 deep-search (pipeline đầy đủ) **chỉ trong các tài liệu đó**.
4. Số biến thể query theo độ khó: câu đơn giản 2–3, câu mơ hồ mới dùng 8. Đưa vào config.
5. Với intent `overview`: nới lỏng ngưỡng abstain — cho phép tổng hợp từ summary
   thay vì từ chối, kèm ghi chú "trả lời ở mức tổng quan".

**Nghiệm thu:** 5 câu hỏi chung chung thật của người dùng đều có câu trả lời
<10s, không abstain oan; 5 câu hỏi chi tiết giữ nguyên chất lượng (so sánh thủ công).

## 6. Ràng buộc chung

- Mọi fix đều có config/flag, **mặc định giữ hành vi cũ** cho tới khi người dùng bật.
- Không xoá code đường cũ. Không đổi schema DB theo cách phá tương thích.
- Thêm log thời gian từng stage (embed / search / synthesis) để đo đạc.
- Chạy `pytest tests/` sau mỗi fix.

## 7. Thứ tự thực hiện (làm theo từng chặng, dừng chờ duyệt)

1. FIX 1 → benchmark → commit riêng → viết báo cáo (mục 9) → **DỪNG, hỏi người dùng
   có làm tiếp không**.
2. FIX 2 → so sánh recall → commit riêng → viết báo cáo → **DỪNG, hỏi người dùng**.
3. FIX 3 → test với câu hỏi thật → commit riêng → viết báo cáo.
4. Báo cáo cuối: bảng thời gian trước/sau + recall trước/sau cho từng fix.

Không tự ý làm fix kế tiếp khi chưa được người dùng đồng ý.

## 8. Bàn giao

- Commit từng fix riêng, message rõ ràng bằng tiếng Việt hoặc tiếng Anh.
- Báo cáo từng fix nằm ở `docs/phieu-viec/ket-qua/FIX{n}_bao-cao.md` (xem mục 9).
- Nếu fix nào không đạt tiêu chí nghiệm thu, giữ nguyên code cũ (flag tắt) và báo lại
  lý do, không cố "cho xong".

## 9. Mẫu báo cáo sau mỗi fix

Sau mỗi FIX, tạo file `docs/phieu-viec/ket-qua/FIX{n}_bao-cao.md` (ví dụ
`docs/phieu-viec/ket-qua/FIX1_bao-cao.md`) với đúng các mục sau:

1. **Tóm tắt thay đổi**: sửa file nào, hàm nào, ý tưởng chính (5–10 dòng).
2. **Bảng benchmark trước/sau**: latency (ghi rõ số chunks, số lần đo, trung bình),
   tốc độ embed (nếu có), đặt cạnh số liệu bản cũ.
3. **So sánh chất lượng**: top-k có giống hệt bản cũ không (FIX 1); recall@10 chênh
   lệch bao nhiêu (FIX 2); câu hỏi test nào, kết quả ra sao (FIX 3).
4. **Kết quả `pytest tests/`**: pass/fail, liệt kê test nào đỏ (nếu có).
5. **Flag rollback**: tên flag/config để tắt fix, giá trị mặc định.
6. **Điểm khác với phiếu việc**: nếu chỗ nào làm khác hoặc bỏ qua, ghi rõ lý do.
7. **Đánh giá đạt/không đạt** tiêu chí nghiệm thu của fix đó.

Viết ngắn gọn, số liệu thật từ lần chạy trên máy — không ước lượng, không làm tròn
quá mức.
