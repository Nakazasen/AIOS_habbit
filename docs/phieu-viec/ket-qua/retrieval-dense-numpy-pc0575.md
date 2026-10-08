# Báo cáo Nghiệm thu: Bật đường Dense Numpy + Cache ma trận RAM (RETRIEVAL-DENSE-NUMPY-PC0575)

- **Mã vé:** `RETRIEVAL-DENSE-NUMPY-PC0575`
- **Người thực hiện:** thợ `agy` (Antigravity CLI)
- **Máy thực thi:** KDTVN-PC0575 (Windows 11, Intel Core i5-8400 @ 2.80GHz, 16GB RAM, CPU-only)
- **Thời gian hoàn thành:** 2026-10-08 11:45 +07
- **Nhánh làm việc:** `phieu-viec/rag-fix1`
- **File kết quả chi tiết:** `local_runs/retrieval_dense_numpy_results.json`

---

## 1. Tuyên bố Tuân thủ Rào cứng

1. **Chỉ-đọc cơ sở dữ liệu:** Mở `library.sqlite` hoàn toàn ở chế độ chỉ đọc (`mode=ro&immutable=1`).
   - Kích thước trước và sau nghiệm thu: **2.853.646.336 bytes** (khớp chính xác 100%, không ghi 1 byte nào vào index).
2. **Không merge `main`:** Toàn bộ công việc thực hiện trên nhánh `phieu-viec/rag-fix1`.
3. **Cổng Parity tuyệt đối:** Đạt **100% PASS** trên toàn bộ 8/8 câu (7 câu nhóm A + 1 câu chẩn đoán) với Top 15 Chunk IDs trùng khớp tuyệt đối, độ lệch điểm tối đa `0.00e+00`.
4. **Không đụng khâu Lexical/Sparse:** Giữ nguyên vẹn mã nguồn chặng Lexical FTS5 và Sparse inverted index theo đúng phân định phạm vi vé.

---

## 2. Kết quả Cổng Parity Top 15 Tuyệt đối (BẮT BUỘC)

Kiểm tra đối chứng trực tiếp giữa **quét tuyến tính Python thuần** và **Numpy BLAS** trên toàn bộ **121.331 vector** thực tế của `library.sqlite`:

| STT | Mã câu | Nội dung câu hỏi tóm tắt | Python scan (ms) | Numpy scan (ms) | Tăng tốc (lần) | Khớp Top 15 IDs | Độ lệch điểm tối đa | Kết quả Parity |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `Q0704` | Bảo dưỡng khuôn 14/2, Housing Magenta tỷ lệ NG C7620 | 285.807,7 | 1.407,1 | **203,1x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 2 | `Q0701` | Hiện tượng tại LSU Line được mô tả như thế nào? | 286.558,5 | 1.421,2 | **201,6x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 3 | `Q0688` | Data nguyên nhân cần chú ý gì (tiếng Nhật) | 298.523,4 | 1.317,2 | **226,6x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 4 | `Q0671` | Kết quả kiểm tra bằng tấm OHP trước đối sách | 291.761,7 | 1.768,1 | **165,0x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 5 | `Q0707` | SIM tape dán ở đâu, dày bao nhiêu | 315.974,1 | 2.182,3 | **144,8x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 6 | `Q0696` | 排查时应先调整Unit还是确认Jig相关性？ | 276.398,8 | 1.494,4 | **185,0x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 7 | `Q0668` | g1 và g2 có nominal và giới hạn nào? | 263.753,0 | 1.165,6 | **226,3x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |
| 8 | `Q0704_perf_diag` | Đối chứng câu chẩn đoán hiệu năng Q0704 | 272.861,9 | 1.117,3 | **244,2x** | 100% (15/15) | 0,00e+00 | **ĐẠT (PASS)** |

- **Kết luận Cổng Parity:** **8/8 câu ĐẠT TUYỆT ĐỐI (100% PASS)**. Không có bất kỳ sai lệch nào về thứ tự hay ID của ứng viên Top 15. Tốc độ quét vector tăng trung bình **199,6 lần**.

---

## 3. Kiến trúc Cache Ma trận Dense RAM Cấp Tiến trình

- **Vị trí cài đặt:** `src/aios_habit/rag_v2/index.py`.
- **Cơ chế lưu trữ:**
  - Khởi tạo cấu trúc `_DenseMatrixCache` lưu trữ ma trận `float32` 2 chiều `(121331, 1024)` cùng bộ mảng ID/metadata song song.
  - Sử dụng biến toàn cục cấp tiến trình `_PROCESS_DENSE_MATRIX_CACHE: dict[str, _DenseMatrixCache]` bảo vệ bằng khóa tái nhập `_PROCESS_DENSE_MATRIX_LOCK = threading.RLock()`.
  - Khởi tạo hàm xóa an toàn `clear_process_dense_matrix_cache()` phục vụ cho unit test và kiểm thử cô lập.
- **Số liệu đo đạc thực tế:**
  - **Mức tiêu thụ RAM thực tế:** **473,95 MB** (121.331 vector $\times$ 1024 số thực float32 $\times$ 4 bytes), hoàn toàn nằm dưới ngân sách cho phép (~497 MB).
  - **Thời gian nạp lần đầu từ SQLite:** 87,0 – 110,4 giây (đọc 121.331 blob nhị phân từ ổ cứng).
  - **Thời gian tái sử dụng ở các truy vấn sau (Warm):** **0,08 – 0,16 ms** (đọc trực tiếp con trỏ ma trận trong bộ nhớ RAM tiến trình).
- **Cơ chế Fallback & Rollback an toàn:**
  - Mặc định bật `numpy` dense khi có thư viện `numpy`.
  - Hỗ trợ rollback 1 dòng về đường Python cũ bằng biến môi trường: `AIOS_RAG_V2_NUMPY_DENSE=0`.
  - Bọc khối `try...except` an toàn: nếu thiếu `numpy` hoặc xảy ra lỗi tính toán BLAS, hệ thống tự động rơi về đường quét Python kèm thông báo nhật ký tiếng Việt rõ ràng, tuyệt đối không gây sập ứng dụng.

---

## 4. Đo Hiệu năng Phân rã 8 Chặng Trước và Sau khi Sửa

So sánh đối chứng với số liệu đo tại vé `RETRIEVAL-PERF-DIAG-PC0575` (trên cùng 3 câu chẩn đoán ở trạng thái warm):

### 4.1 Bảng so sánh chặng Dense Warm (Tiêu chí then chốt $\le$ 2.0s/câu)

| Mã câu | Dense trước sửa (Python scan) | Dense sau sửa (Numpy BLAS + Cache RAM) | Tỷ lệ tăng tốc chặng Dense | Tiêu chuẩn $\le$ 2.0s |
| :---: | :---: | :---: | :---: | :---: |
| `Q0704` | 108,67 s (108.670,7 ms) | **0,511 s** (511,3 ms) | **212,5 lần** | **ĐẠT (PASS)** |
| `Q0701` | 104,53 s (104.529,5 ms) | **0,762 s** (761,6 ms) | **137,2 lần** | **ĐẠT (PASS)** |
| `Q0671` | 106,82 s (106.822,4 ms) | **0,557 s** (556,8 ms) | **191,8 lần** | **ĐẠT (PASS)** |
| **Trung bình** | **106,67 s** | **0,610 s** | **180,5 lần** | **ĐẠT XUẤT SẮC** |

### 4.2 Bảng phân rã 8 chặng chi tiết (đơn vị: mili-giây / giây)

| Chặng thực thi | Câu Q0704 (Warm) | Câu Q0701 (Warm) | Câu Q0671 (Warm) | Ghi chú & Đánh giá |
| :--- | :---: | :---: | :---: | :--- |
| **1. Query Plan** | 16,7 ms | 6,0 ms | 0,6 ms | Coerce query plan nhanh, không tải model |
| **2. Embed Query (ONNX)** | 199,6 ms | 277,4 ms | 109,3 ms | Model nạp sẵn trong phiên, embed 1 câu ~0.2s |
| **3. Dense Candidates** | **511,3 ms** | **761,6 ms** | **556,8 ms** | **Cắt giảm từ ~106.000 ms xuống dưới 762 ms** |
| **4. Sparse Candidates** | 341,9 ms | 414,9 ms | 361,7 ms | Warm cache RAM, ổn định ~0.35–0.41s |
| **5. Lexical FTS5** | 71.711,5 ms | 83.814,8 ms | 82.095,4 ms | Ngốn thời gian do bảng tính `Loi KDTPS.xlsx` (vé sau) |
| **6. Fusion & Capping** | 73,1 ms | 45,2 ms | 36,8 ms | Hợp nhất RRF + Diversity cap $\le$ 3 mảnh |
| **7. Evidence Pack** | 17,4 ms | 8,5 ms | 11,5 ms | Trích xuất 15 mảnh bằng chứng |
| **8. Synthesis** | 147,2 ms | 45,2 ms | 55,6 ms | Tổng hợp câu trả lời offline |
| **TỔNG THỜI GIAN WARM SAU SỬA** | **73,02 giây** | **85,37 giây** | **83,23 giây** | **Trung bình: 80,54 giây/câu** |
| *Tổng thời gian warm trước sửa* | *158,10 giây* | *158,11 giây* | *160,05 giây* | *Trung bình: 158,75 giây/câu* |
| **Thời gian tiết kiệm được** | **-85,08 giây** | **-72,73 giây** | **-76,83 giây** | **Tiết kiệm trung bình: 78,21 giây/câu** |

- **Nhận xét hiệu năng:**
  - Chặng quét dense đã hoàn toàn biến mất khỏi danh sách điểm nghẽn (từ 106s xuống còn **0.61s**).
  - Tổng thời gian truy vấn warm của hệ thống giảm gần một nửa (giảm **49,2%**, tiết kiệm hơn **78 giây** mỗi câu hỏi).
  - Thời gian còn lại (~71–83s) nằm trọn vẹn ở khâu Lexical FTS5 và tính điểm hàng nghìn dòng ứng viên từ tệp bảng tính Excel — khâu này sẽ được giải quyết dứt điểm ở các vé tối ưu Lexical tiếp theo như điều phối đã định hướng.

---

## 5. Nghiệm thu Dùng thật & Chất lượng Tìm kiếm

Chạy kiểm tra qua đường thực tế của ứng dụng (`RagV2DevPipeline` / adapter trên kho dữ liệu thật):

### 5.1 Câu Q0704
- **Câu hỏi:** *"Sau ngày bảo dưỡng khuôn 14/2, Housing màu Magenta có điểm gì đáng chú ý về tỷ lệ NG C7620?"*
- **Tài liệu nguồn mong đợi:** `Sirius 2 _ C7620_報告版 4.pptx`
- **Kết quả Rank:** **Rank 1** (Hit chính xác tuyệt đối).
- **Top Contexts:**
  1. `[Rank 1]` `Sirius 2 _ C7620_報告版 4.pptx` (Chunk `wsc-3862a76468aee5575cd502c5-summary`, Điểm: 31.0)
  2. `[Rank 2]` `Sirius 2 _ C7620_報告版 4.pptx` (Chunk `43e901b53d95d57a2f683a00a9bfa06d7e58b8aea8afe4b0b1b39089169d2ea1`, Điểm: 20.0)
  3. `[Rank 3]` `Loi KDTPS.xlsx` (Chunk `a60c3f871de7eea74d51dd549df01ad577ba34dd108d5bb54a58b8e209c46e7d`)
- **Trích đoạn câu trả lời:**
  > *"2 Sirius 2 C7620 発生状況 : 調整工程 発生状況：色補正後に、 Bk に対する副走査方向の色差値が 70dot 以上 発生 LINE ： C23/24 ：２月１９日→ NG 率が同じ傾向→同時に上昇 発生色： Magenta..."*

### 5.2 Câu Q0701
- **Câu hỏi:** *"Hiện tượng tại LSU Line được mô tả như thế nào?"*
- **Tài liệu nguồn liên quan:** `Tài liệu đào tạo LSU_2019.01.18_K.pptx` (Rank 1), `Loi KDTPS.xlsx` (Rank 2), `2xd_smkdj_jpnサービスアニュアル.pdf` (Rank 3).
- **Kết quả:** Tìm thấy đúng tài liệu đào tạo chuyên sâu về LSU Line và các ghi chép lỗi đọng sương gương LSU.

### 5.3 Câu Q0671
- **Câu hỏi:** *"Kết quả kiểm tra bằng tấm OHP trước đối sách là bao nhiêu?"*
- **Tài liệu nguồn mong đợi:** `Bong TAPE COVER GLASS Rev.00 VN.pptx`
- **Kết quả Rank:** **Rank 3** (Hit chuẩn xác trong Top 3).
- **Top Contexts:**
  1. `[Rank 1]` `Loi KDTPS.xlsx` (Chunk `e83682f9c0572e3e6a61ad59bbcaa6340fd3e898ddbf9d7d3124f05b84d60538`)
  2. `[Rank 2]` `Loi KDTPS.xlsx` (Chunk `742cf84b09b10e2a6a8ed9b3824b8d9348a22000a941ebb3028974e0b3b1928c`)
  3. `[Rank 3]` `Bong TAPE COVER GLASS Rev.00 VN.pptx` (Chunk `wsc-cc13a93c2c2cd621a8487e05-summary`, Điểm: 23.5)
  4. `[Rank 4]` `Bong_TAPE_COVER_GLASS_Rev.00_VN.pptx` (Chunk `15f403bac495f305906ec2ecbf04af7cdf71c158dc1331143b68f6ed5833a951`)
- **Trích đoạn câu trả lời:**
  > *"※ Kiểm tra bằng tấm OHP 43/98 pcs NG = 43.9%. KT Chế tạo ban hành ĐƯKC (No.35764): Miết lại 2 lần và kiểm tra bằng OHP. Tỷ lệ NG: 0/546 pcs NG..."* (Trích xuất chính xác con số nghiệp vụ).

---

## 6. Kết quả Cổng Kiểm thử Repo (Quality Gates)

| Cổng kiểm thử | Lệnh thực thi | Kết quả | Ghi chú |
| :--- | :--- | :---: | :--- |
| **1. Biên dịch** | `uv run --no-sync --group dev python -m compileall src tests` | **PASS** | Biên dịch sạch toàn bộ tệp nguồn và bài test |
| **2. Unit test** | `uv run --no-sync --group dev pytest -q tests/test_rag_v2_numpy_dense.py` | **PASS** | **8/8 passed** (1.49s): test mặc định bật, cờ rollback, fallback khi thiếu numpy, parity vector nhỏ, cache tiến trình |
| **3. CLI Audit** | `uv run --no-sync --group dev python -m aios_habit.cli audit` | **PASS** | `{"errors": [], "status": "PASS", "warnings": []}` |
| **4. Import App** | `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` | **PASS** | Import sạch, không phụ thuộc chéo, không sập |

---

## 7. Kết luận & Đề xuất Bàn giao

- **Kết luận:** Vé `RETRIEVAL-DENSE-NUMPY-PC0575` đã hoàn thành trọn vẹn 100% tất cả các mục tiêu và vượt qua tất cả các rào cứng khắt khe:
  1. Cổng Parity 8/8 câu đạt tuyệt đối (100% ID + thứ tự, độ lệch 0.00e+00).
  2. Chặng dense warm rút ngắn xuống **0,61 giây/câu** (đạt chuẩn $\le$ 2.0s).
  3. Tiết kiệm trung bình **78,2 giây/câu** khi dùng thật.
  4. Cache RAM ma trận chiếm **473,95 MB**, truy xuất trong **0,1 ms**.
  5. 4 cổng kiểm thử repo đạt chuẩn PASS.
- Sẵn sàng bàn giao cho Điều phối Muse nghiệm thu và mở đường cho vé tiếp theo trong hàng chờ (`RAG-REMEASURE-PC0575`).
