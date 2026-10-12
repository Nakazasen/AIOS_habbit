# BÁO CÁO NGHIỆM THU: RAG-RETRIEVAL-NUMPY-COMPLETE-HOME

- **Mã vé**: `DESKTOP-RAG-NUMPY-COMPLETE-HOME` / `RAG-RETRIEVAL-NUMPY-COMPLETE-HOME`
- **Tên nhiệm vụ**: Numpy hoá nốt hai hàm chấm điểm của khâu truy hồi (`cosine_similarity` và `sparse_dot_similarity`) + Đo phân bổ thời gian từng chặng trước/sau + Đo lại 4 câu chuẩn trên giao diện thật
- **Trạng thái**: `HOAN_THANH`
- **Máy thực hiện**: `May nha - h410asrock` (môi trường chỉ-CPU, Windows 10, Python 3.11.14, NumPy 1.26.4)
- **Cấu hình thực thi**: Biên bản BB-CONFIG-PARITY-01 (CPU-only, OMP_NUM_THREADS=1, MKL_NUM_THREADS=1, KMP_DUPLICATE_LIB_OK=TRUE)
- **Kho mã sản phẩm**: `D:\Sandbox\AIOS_habbit` (nhánh `phieu-viec/rag-fix1`, commit HEAD: `f88c62cc472d2f0bb2780e3a972ad9e7ebcf6352`)
- **Kho điều phối & Bằng chứng**: `D:\Sandbox\aios-dieu-phoi` (nhánh `main`, commit bộ ảnh/kết quả: `37d03c0b00a582ac4166c718364017299a101903`)
- **Thời điểm nghiệm thu**: `2026-10-12T11:15:00+07:00` (UTC: `2026-10-12T04:15:00Z`)

---

## 1. Bối cảnh & Mục tiêu kỹ thuật

- **Bối cảnh**: Lõi quét dense trong `rag_v2/index.py` đã được numpy hoá trước đó (matmul float32 + argpartition), tuy nhiên hai hàm chấm điểm trong `rag_v2/semantic.py` (`cosine_similarity` và `sparse_dot_similarity`) vẫn chạy bằng vòng lặp Python thuần. Việc này gây nghẽn CPU cục bộ khi thực hiện chấm điểm lại hàng nghìn ứng viên (như ở khâu fuse/rerank).
- **Phân quyền thực hiện**: Tuân thủ tuyệt đối ranh giới vé:
  - Chỉ sửa đổi tệp mã nguồn `src/aios_habit/rag_v2/semantic.py` và viết bộ kiểm thử mới liên quan (`tests/test_rag_v2_numpy_scoring.py`).
  - Không sửa đổi chỉ mục production (`C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\lsu\library.sqlite`).
  - Không thay đổi ngưỡng lọc hay cổng bằng chứng của hệ thống.
  - Giữ nguyên đường tính Python thuần làm dự phòng an toàn thông qua biến môi trường `AIOS_RAG_V2_NUMPY_SCORING`.

---

## 2. Chi tiết giải pháp kỹ thuật (src/aios_habit/rag_v2/semantic.py)

1. **Cờ môi trường kiểm soát & Cơ chế tự chữa lành (Self-Healing / Fallback)**:
   - Thêm hằng số `NUMPY_SCORING_FLAG = "AIOS_RAG_V2_NUMPY_SCORING"`.
   - Hàm `numpy_scoring_enabled()`:
     - Tự động bật mặc định khi môi trường có thư viện `numpy`.
     - Cho phép rollback ngay lập tức về đường Python thuần bằng cách đặt `AIOS_RAG_V2_NUMPY_SCORING` bằng `0`, `false`, `no`, hoặc `off`.
     - Khi `numpy` không có sẵn trong môi trường, hệ thống tự động rơi về đường Python cũ mà không phát sinh lỗi sập app.
2. **Numpy hoá `cosine_similarity`**:
   - Thêm hàm `_cosine_similarity_numpy(left, right)`: Chuyển đổi vector sang `np.float32` và thực hiện `np.dot` tối ưu trên CPU.
   - Giữ lại hàm tham chiếu nguyên bản `_cosine_similarity_python(left, right)`.
   - Bổ sung hàm vector hoá theo lô `batch_cosine_similarity(query_vector, candidate_vectors)` sử dụng phép nhân ma trận - vector `mat @ q`.
3. **Numpy hoá `sparse_dot_similarity`**:
   - Thêm hàm `_sparse_dot_similarity_numpy(left, right)`: Lọc nhanh các token giao nhau giữa hai vector thưa, chuyển trọng số của các token này sang mảng `np.float32` qua `np.fromiter` và tính tích vô hướng bằng `np.dot`.
   - Giữ lại hàm tham chiếu nguyên bản `_sparse_dot_similarity_python(left, right)`.
   - Bổ sung hàm theo lô `batch_sparse_dot_similarity(query_vector, candidate_vectors)`.
4. **Bảo toàn ngữ nghĩa & Ngưỡng dung sai số học**:
   - Sai lệch số học giữa float32 matmul/dot và Python accumulator:
     - Đối với dense cosine: sai lệch $\le 1 \times 10^{-6}$ (thực tế đo được $\approx 1 \times 10^{-7}$).
     - Đối với sparse dot: sai lệch $\le 1 \times 10^{-4}$ (thực tế đo được $\approx 1 \times 10^{-5}$).
   - **Thứ hạng top-k bảo toàn 100%**: Thứ tự xếp hạng của toàn bộ ứng viên không hề thay đổi.

---

## 3. Kết quả Kiểm thử Tương đương & 4 Cổng Chất lượng Repo

### 3.1. Bộ kiểm thử tương đương (`tests/test_rag_v2_numpy_scoring.py`)
Toàn bộ **8/8 test cases** đã được chạy và vượt qua 100% (`0.37s`):
1. `test_numpy_scoring_flag_defaults_on_when_numpy_available`: Kiểm tra cờ mặc định bật khi có numpy -> **PASSED**.
2. `test_numpy_scoring_flag_explicit_off`: Kiểm tra tắt tường minh qua các giá trị cờ -> **PASSED**.
3. `test_numpy_scoring_missing_numpy_fallback`: Kiểm tra fallback an toàn khi thiếu numpy -> **PASSED**.
4. `test_cosine_similarity_dimension_mismatch`: Kiểm tra ngoại lệ khi lệch số chiều vector -> **PASSED**.
5. `test_cosine_similarity_synthetic_equivalence`: So sánh dữ liệu tổng hợp trên 3 kích thước chiều (16, 128, 1024), xác nhận sai lệch $\le 10^{-6}$ và top-10 ranking trùng khớp 100% -> **PASSED**.
6. `test_sparse_dot_similarity_synthetic_equivalence`: So sánh dữ liệu tổng hợp sparse dot, xác nhận sai lệch $\le 10^{-4}$ và top-10 ranking trùng khớp 100% -> **PASSED**.
7. `test_batch_cosine_and_sparse_similarity`: Kiểm tra các hàm batch cosine và batch sparse dot -> **PASSED**.
8. `test_real_index_sample_equivalence`: Trích mẫu chỉ mục thật ở chế độ chỉ-đọc (`PRAGMA query_only=ON`) từ thư viện `lsu`, xác nhận sai lệch thực tế và top-k hoàn toàn trùng khớp -> **PASSED**.

### 3.2. 4 Cổng chất lượng của Repository
- **Cổng 1 (`compileall`)**:
  - Lệnh: `python -m compileall src tests`
  - Kết quả: **0 lỗi** cú pháp trên toàn bộ kho mã.
- **Cổng 2 (`cli audit`)**:
  - Lệnh: `python -m aios_habit.cli audit`
  - Kết quả: `{"status": "PASS", "errors": [], "warnings": []}`.
- **Cổng 3 (`import app`)**:
  - Lệnh: `python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`
  - Kết quả: `IMPORT_OK`.
- **Cổng 4 (`pytest`)**:
  - Lệnh: `python -m pytest tests/test_rag_v2_index.py tests/test_rag_v2_pipeline.py tests/test_rag_v2_semantic.py tests/test_rag_v2_numpy_scoring.py tests/test_rag_v2_numpy_dense.py -q`
  - Kết quả: **96 passed** trong `6.30s`.

---

## 4. Bảng Phân Bổ Thời Gian Từng Chặng: TRƯỚC vs SAU

Đo kiểm độc lập trên khối `lsu` với bộ 8 câu hỏi cố định (4 câu khối tri thức + 4 câu LSU 50 câu) theo 5 chặng:
(a) Nhúng câu hỏi (`nhung`); (b) Quét dense (`dense`); (c) Quét sparse (`sparse`); (d) Chấm lại / Hợp nhất / Rerank (`fuse`); (e) Tổng thời gian truy hồi (`tong`).
Đo tối thiểu 2 lượt cho mỗi câu: Lượt 1 (Lạnh) và Lượt 2 (Ấm). Tệp dữ liệu thô:
- Trước: `docs/phieu-viec/ket-qua/stage-breakdown-before.json`
- Sau: `docs/phieu-viec/ket-qua/stage-breakdown-after.json`

| Mã câu hỏi | Nội dung tóm tắt | Lượt | Tổng TRƯỚC (ms) | Tổng SAU (ms) | Chặng Fuse TRƯỚC (ms) | Chặng Fuse SAU (ms) | Top-1 Chunk ID | Top-1 Score |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **KB-QA-1** | Ý nghĩa thông số DMT và PMT | L1 (Lạnh)<br>L2 (Ấm) | 6,694.5<br>750.8 | 6,661.6<br>766.8 | 421.2<br>416.5 | 414.4<br>429.5 | `6afe8d0531...` | 15.0<br>(Khớp 100%) |
| **KB-QA-2** | Mã lỗi C7620 Kyocera | L1 (Lạnh)<br>L2 (Ấm) | 2,696.2<br>674.8 | 1,062.6<br>659.9 | 1,960.4<br>338.0 | 404.6<br>330.3 | `43e901b53d...` | 8.0<br>(Khớp 100%) |
| **KB-QA-3** | Xuất kho AGV & MOM | L1 (Lạnh)<br>L2 (Ấm) | 25,499.0<br>838.5 | **1,017.7**<br>**799.0** | **24,814.6**<br>562.5 | **627.0**<br>**541.9** | `4f1e4392c6...` | 5.0<br>(Khớp 100%) |
| **KB-QA-4** | Tối ưu hiệu suất thiết bị | L1 (Lạnh)<br>L2 (Ấm) | 1,164.4<br>533.9 | 670.0<br>596.2 | 651.8<br>275.9 | 298.6<br>348.3 | `5264d1dcf3...` | 17.0<br>(Khớp 100%) |
| **Q0699** | C7620 Magenta vs Black | L1 (Lạnh)<br>L2 (Ấm) | 1,129.7<br>917.2 | 1,007.8<br>788.6 | 505.3<br>477.1 | 483.0<br>461.3 | `wsc-3862a7...` | 17.75<br>(Khớp 100%) |
| **Q0700** | C23 và C24 Trend | L1 (Lạnh)<br>L2 (Ấm) | 1,709.6<br>1,353.2 | 1,524.7<br>1,411.1 | 1,048.4<br>1,020.7 | 1,029.8<br>1,072.6 | `f67f76d9a4...` | 0.4521<br>(Khớp 100%) |
| **Q0703** | B khoảng cách dài ra | L1 (Lạnh)<br>L2 (Ấm) | 1,434.0<br>1,168.6 | 1,435.0<br>1,154.4 | 858.0<br>850.4 | 857.8<br>843.0 | `3fa252b053...` | 11.0<br>(Khớp 100%) |
| **Q0708** | Quang lộ 1.15 mm | L1 (Lạnh)<br>L2 (Ấm) | 1,819.3<br>1,559.7 | 1,665.8<br>1,546.2 | 1,199.7<br>1,217.2 | 1,210.0<br>1,204.0 | `14bdf5563c...` | 44.75<br>(Khớp 100%) |

---

## 5. Kết Quả Đo Lại Trên Giao Diện Thật (Playwright Chromium)

- **Môi trường đo**: Trình duyệt Chromium điều khiển bằng Playwright kết nối Streamlit port 8538.
- **Sổ đo kiểm**: `NB-C26E1C84` ("Sổ nghiệm thu DESKTOP 2026-10-10").
- **Mốc so sánh đối chiếu** (theo vé nghiệm thu làn tổng hợp `DESKTOP-SYNTH-LANE-FIX-HOME`):
  - LSU: `116.69s`
  - Điều tra lỗi: `40.56s`
  - MOM: `120.00s`
  - Tự động (Mơ hồ): `139.46s`

### 5.1. Bảng số liệu thời gian giao diện và trạng thái đáp án

| STT | Khối tri thức | Nội dung câu hỏi | Mốc cũ (s) | Đo lại (s) | Chênh lệch | Trạng thái UI | Độ dài đáp án | Backend thực thi |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| 0 | Khởi động app | Mở app và sẵn sàng hội thoại mới | - | - | - | **HOÀN TẤT** | - | - |
| 1 | **LSU** | `Ý nghĩa thông số DMT và PMT trong đo kiểm quang học Iris LSU là gì?` | 116.69 | 171.43 | +54.74s (+46.9%) | **HOÀN TẤT** | 206 ký tự | Bản thảo ChatGPT (`draft_fallback`) |
| 2 | **Điều tra lỗi** | `Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, nguyên nhân và đối sách xử lý ra sao?` | 40.56 | **3.12** | **-37.44s (-92.3%)** | **HOÀN TẤT** | 1,476 ký tự | Nakazasen Router |
| 3 | **MOM** | `Quy trình xuất kho qua AGV và liên kết với bảng staging oricon trong hệ thống MOM Opcenter như thế nào?` | 120.00 | 153.31 | +33.31s (+27.8%) | **HOÀN TẤT** | 1,365 ký tự | Cục bộ từ trích đoạn (`local_grounded`) |
| 4 | **Tự động (Mơ hồ)** | `Làm thế nào để kiểm tra và tối ưu hiệu suất làm việc hàng ngày của thiết bị?` | 139.46 | 299.51 | +160.05s (+114.8%) | **HOÀN TẤT** | 347 ký tự | Bản thảo ChatGPT (`draft_fallback`) |

---

## 6. Bảng Kiểm Kê Ảnh Minh Chứng (SHA-256 Unique Gate)

Toàn bộ 5 ảnh chụp giao diện đã được lưu trữ vào kho `aios-dieu-phoi` tại commit `37d03c0b00a582ac4166c718364017299a101903`. Cổng kiểm tra tính độc nhất (không trùng byte) đạt 100%:

| STT | Tên tệp ảnh | Kích thước (bytes) | Mã băm SHA-256 | Mô tả nội dung trên giao diện |
|:---:|:---|:---:|:---|:---|
| 0 | `anh-desktop-rag-numpy-01-app-ready.png` | 116,580 | `0F1F616756366AF8A1301A2AA63F843A0A3DC2692C702B69ED11C1E98A8BE9C7` | Giao diện hội thoại mới sẵn sàng, thanh công cụ khối tri thức `LSU (99 tài liệu)` |
| 1 | `anh-desktop-rag-numpy-02-lsu.png` | 143,514 | `7A6FCB2C5B364BC0EE7ECBE738F0A3B7C2930F275A29E267FBD62001E7E3795E` | Trọn thân câu trả lời cho câu DMT/PMT khối LSU kèm nguồn trích dẫn bản thảo |
| 2 | `anh-desktop-rag-numpy-03-dieu-tra-loi.png` | 203,337 | `E3D7490A9438FE52461471FC4EE683659B0D8454927F0830A3B8EB77D449F303` | Trọn thân câu trả lời tra cứu lỗi C7620 (5 ca lỗi lịch sử chi tiết từ DB) |
| 3 | `anh-desktop-rag-numpy-04-mom.png` | 172,789 | `4FB68C61FC6F6E4DB532DD525560574FA6AB63E780479A34CD45B6E350BC3193` | Trọn thân câu trả lời quy trình xuất kho AGV và liên kết staging oricon |
| 4 | `anh-desktop-rag-numpy-05-cau-mo-ho.png` | 148,201 | `BC4B9E635FFA518A25EF5B2FE1357369F2D8AD2D6EDC9CF50EEF210CB5894E39` | Trọn thân câu trả lời câu hỏi mở / mơ hồ với hướng dẫn chia context |

- **Kết quả kiểm định trùng byte SHA-256**: **ĐẠT (100% độc nhất)**.

---

## 7. Khối JSON Kết Quả Nghiệm Thu Bắt Buộc

```json
{
  "ma_ve": "DESKTOP-RAG-NUMPY-COMPLETE-HOME",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-12T04:15:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
