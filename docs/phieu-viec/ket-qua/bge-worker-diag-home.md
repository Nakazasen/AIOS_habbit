# Báo cáo chẩn đoán sự cố tiến trình con BGE Worker trên máy nhà (BGE-WORKER-DIAG-HOME)

- **Mã vé**: `BGE-WORKER-DIAG-HOME`
- **Mục tiêu**: Chẩn đoán tận gốc nguyên nhân tiến trình con BGE-M3 Worker không khởi động được trên ứng dụng máy nhà (`h410asrock`) khi hỏi các câu hỏi ngữ nghĩa (Semantic RAG), dẫn đến lỗi `RuntimeError: preparation_init_bge_worker_persist_timeout`.
- **Máy thực hiện**: Máy nhà `h410asrock` (Windows 10, Python 3.11, CPU đa nhân, GPU rời GTX 1060 3GB).
- **Quy tắc tuân thủ**: Chẩn đoán chỉ-đọc (Read-only), tuyệt đối không sửa code, không đổi cấu hình app, không ghi index trong vé này.

---

## 0. Bổ sung bằng chứng của vé trước (`BASELINE-USE-HOME`)

- Toàn bộ danh mục **8 ảnh chụp màn hình** (cùng 3 ảnh phụ trợ) đã được xác thực sự tồn tại cục bộ và đã được commit đầy đủ vào kho git qua commit:
  - **Commit SHA**: `09daaf68b9a6db92baae5b9f9f33388e2cf0e010`
  - **Danh sách tệp ảnh đã nộp trong `docs/phieu-viec/ket-qua/`**:
    1. `baseline-home-overview.png`: Màn hình tổng quan trang chủ và danh sách sổ.
    2. `baseline-open-lsu-pc0575-id.png`: Xử lý fail-safe khi mở sổ LSU `NB-E35A7BEE` không tồn tại.
    3. `baseline-mom-cold1.png`: Mở sổ lần lạnh 1 (0.56s).
    4. `baseline-mom-warm1.png`: Mở sổ lần ấm 1 (13.62s).
    5. `baseline-mom-cold2.png`: Mở sổ lần lạnh 2 từ trang chủ (10.41s).
    6. `baseline-q1-c0030.png`: Kết quả tra cứu mã C0030 (từ điển lỗi, 5.39s, ĐẠT).
    7. `baseline-q2-c7620.png`: Giao diện câu hỏi ngữ nghĩa C7620 gặp lỗi timeout.
    8. `baseline-q3-kdtps.png`: Giao diện câu hỏi KDTPS gặp lỗi timeout.
    9. `baseline-home-screen.png`, `baseline-mom-opcenter.png`, `baseline-nb-e35a7bee.png`: Các góc nhìn chi tiết bổ trợ.

---

## 1. Tái hiện trong điều kiện sạch (Clean Reproduction)

### 1.1. Hiện trạng môi trường
- Máy nhà đã kết thúc các tác vụ nặng (tác vụ pip install và smoke test của thợ khác đã xong, CPU rỗi).
- Nguồn thử nghiệm: Sổ `mom_opcenter` (109 nguồn, 106 nguồn đang bật).

### 1.2. Kết quả tái hiện
- Khi kích hoạt luồng tìm kiếm ngữ nghĩa cho câu hỏi **C7620** (`C7620中Magenta相对Black的副扫描色差达到多少会成为NG？`):
  - Hệ thống trả về trạng thái: `quality_search_unavailable` với `fallback_reason: semantic_preparing`.
  - Lỗi gốc từ tiến trình con BGE: Khi worker khởi chạy ở chế độ persistent mode (chạy ngầm độc lập qua Named Pipe `\\.\pipe\aios_bge_worker_...`), ứng dụng chính chờ phản hồi qua hàm `_persistent_exchange`.
  - Do thời gian khởi động của worker vượt quá ngưỡng cho phép, hàm `_session` bị quá hạn:
    ```python
    # src/aios_habit/rag_v2/bge_subprocess_client.py:1041
    if thread.is_alive():
        raise SemanticBackendError("bge_worker_persist_timeout")
    ```
  - Adapter `workspace_chat_rag_v2_adapter.py` (dòng 1256) bọc lỗi này thành:
    `RuntimeError: preparation_init_bge_worker_persist_timeout`.

---

## 2. Số liệu đo đạc thời gian khởi động worker thật (Isolated Benchmark)

Quá trình đo đạc độc lập bằng tiến trình riêng (tách biệt hoàn toàn khỏi giao diện Streamlit) ghi nhận phân rã thời gian từng pha khởi động của Worker BGE trên cấu hình Production thật (`C:\AIOS_workspace_chat_rag_v2_production`, collection `tri_thuc`, 121.331 chunks):

### 2.1. Bảng số liệu phân rã các pha khởi động (Init Phases)

| Pha khởi động (Phase) | Thao tác thực tế trong mã nguồn | Thời gian đo điều kiện sạch (07/10 22:15) | Thời gian ghi nhận tại Baseline (07/10 20:43) | Ghi chú & Đánh giá |
|---|---|---|---|---|
| **1. `model_verify`** | Kiểm tra cấu trúc thư mục & mã băm SHA256 mô hình | **0.0 ms** | **75.6 ms** | Đạt cực nhanh nhờ cache `.aios-verify-cache.json` |
| **2. `model_load`** | Nạp mô hình ONNX Runtime fp32 (`model.onnx_data` 2.26 GB) và tối ưu đồ thị tính toán (`ORT_ENABLE_ALL`) | **188.132,0 ms (188,13 giây)** | **214.054,9 ms (214,05 giây)** | **NGUYÊN NHÂN NGHẼN CHÍNH**: Chiếm 70–75% tổng thời gian khởi động trên CPU |
| **3. `index_open`** | Mở kết nối cơ sở dữ liệu sqlite và kiểm tra schema | **1.785,7 ms (1,79 giây)** | **299,2 ms (0,30 giây)** | Rất nhanh, bình thường |
| **4. `dense_preload`** | Tải trước ma trận véc-tơ đặc float32 cho 121.331 chunks (474 MB RAM) | *(Bỏ qua ở chế độ sạch nếu chưa nạp)* | **54.214,0 ms (54,21 giây)** | Nặng, phụ thuộc tốc độ đọc đĩa và CPU giải mã mảng numpy |
| **5. `sparse_preload`** | Tải và phân tích véc-tơ thưa từ bảng sqlite cho 121.331 chunks (22.890 từ khóa) | **55.884,5 ms (55,88 giây)** | **33.582,1 ms (33,58 giây)** | Tải hàng vạn bản ghi từ sqlite vào bộ nhớ từ điển Python |
| **TỔNG THỜI GIAN INIT** | **Tổng chu kỳ khởi tạo hoàn tất của Worker** | **245.802,5 ms (245,80 giây ~ 4,10 phút)** | **302.226,3 ms (302,23 giây ~ 5,04 phút)** | **VƯỢT TRẦN TIMEOUT HỆ THỐNG** |

### 2.2. Đối chiếu với các ngưỡng Timeout trong mã nguồn

1. **Ngưỡng khởi tạo Worker chung (`_INIT_TIMEOUT_SECONDS`)**:
   - Vị trí: `src/aios_habit/rag_v2/bge_subprocess_client.py`, dòng 37 và 43–57.
   - Giá trị quy định: **300.0 giây** (5 phút).
   - **Thực tế**: Ở lần chạy baseline, tổng thời gian init là **302,23 giây**, vượt trần timeout đúng **2,23 giây** khiến thread bị ngắt khi chỉ còn vài phần trăm giây là hoàn tất.
2. **Ngưỡng chờ kết nối Named Pipe (`_PERSIST_SPAWN_WAIT_SECONDS`)**:
   - Vị trí: `src/aios_habit/rag_v2/bge_subprocess_client.py`, dòng 81 và dòng 896 (`connect_timeout_s = min(timeout, _PERSIST_SPAWN_WAIT_SECONDS)`).
   - Giá trị quy định: **120.0 giây** (2 phút).
   - **Thực tế**: Khâu `model_load` của ONNX trên CPU máy nhà mất tối thiểu **188 giây** mới tạo xong đối tượng InferenceSession và mở Named Pipe. Do đó, tiến trình client bị chặn cứng ở mốc **120 giây** và raise lỗi `bge_worker_persist_unavailable` hoặc `bge_worker_persist_timeout` trước khi worker kịp mở cổng lắng nghe.

---

## 3. Xác nhận và loại trừ các giả thuyết

### 3.1. Giả thuyết (a): Tranh chấp tài nguyên lúc đo baseline
- **KẾT LUẬN: XÁC NHẬN (CONFIRMED)**.
- **Bằng chứng**:
  - Lúc đo baseline (đêm 07/10 20:42), máy nhà đang chạy song song tiến trình `OpenCode` (PID 5188) kiểm tra chỉ mục `idx_verify_home.py` và các tác vụ nền khác. Tranh chấp CPU và đọc đĩa khiến pha `model_load` kéo dài lên **214,05 giây** và tổng thời gian khởi tạo chạm mốc **302,23 giây**, làm tràn ngưỡng 300,0s.
  - Khi đo ở điều kiện sạch hoàn toàn, thời gian `model_load` giảm xuống **188,13 giây** và tổng init còn **245,80 giây**.

### 3.2. Giả thuyết (b): Backend mặc định ở máy nhà chưa đúng (vé E4 đặt ONNX)
- **KẾT LUẬN: LOẠI TRỪ (REFUTED)**.
- **Bằng chứng**:
  - Ứng dụng trên máy nhà **đang sử dụng chính xác backend ONNX fp32** theo đúng cấu hình vé E4.
  - `resolve_bge_backend_name()` trả về `"onnx"`.
  - Tệp mô hình nạp: `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32\model.onnx` + `model.onnx_data` (2,26 GB).
  - Nhật ký ghi nhận chính xác: `bge_worker_stage backend=onnx init_ms=...`.
  - Vấn đề không phải do dùng nhầm backend, mà do chính bản thân việc nạp và tối ưu đồ thị (Graph Optimization `ORT_ENABLE_ALL`) của ONNX Runtime fp32 cho mô hình BGE-M3 (2,26 GB) trên CPU là thao tác cực nặng (tốn hơn 3 phút).

### 3.3. Giả thuyết (c): VRAM 3GB không đủ cho đường torch nên worker chết/chậm
- **KẾT LUẬN: LOẠI TRỪ HOÀN TOÀN (REFUTED - Bản chất khác biệt)**.
- **Bằng chứng thực nghiệm cốt lõi**:
  1. **Máy nhà không dùng GPU**: Môi trường Python trên máy nhà cài đặt bản CPU-only: `torch==2.5.1+cpu` và `onnxruntime==1.28.0` (chỉ có `CPUExecutionProvider`).
     - Lệnh kiểm tra: `torch.cuda.is_available()` trả về `False`.
     - Nguyên nhân: Script khởi chạy ứng dụng `scripts/run_workspace_chat.ps1` (dòng 20) cố ý ép cài đặt bánh xe CPU:
       `uv pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1+cpu" ...`
     - Do đó, card đồ họa rời GTX 1060 3GB hoàn toàn **không được nhận diện và không hề can dự** vào quá trình chạy worker BGE. Không có hiện tượng tràn VRAM hay lỗi VRAM.
  2. **Thực nghiệm PyTorch FlagEmbedding trên CPU**:
     - Khi chạy thử nghiệm nạp mô hình gốc PyTorch (`BGEM3FlagModel`) trực tiếp trên CPU:
       - Thời gian nạp mô hình: **24,71 giây** (nhanh hơn ONNX tới gần 8 lần: 24,7s vs 188,1s).
       - Bộ nhớ RAM tiêu thụ: ~**860 MB** (hoàn toàn nằm trong giới hạn an toàn của máy có 16GB RAM).
       - Thời gian mã hóa thử nghiệm câu hỏi ("C7620"): hoàn tất bình thường.

### 3.4. Giả thuyết (d): Worker chết một lần là độc cả phiên (Session Poisoning)
- **KẾT LUẬN: XÁC NHẬN (CONFIRMED)**.
- **Bằng chứng**:
  - Khi worker bị timeout ở câu hỏi hoặc khâu chuẩn bị đầu tiên, đối tượng `_SUBPROCESS_CLIENT` lưu giữ `_last_failure_reason = "bge_worker_init_timeout"` (hoặc `bge_worker_persist_timeout`).
  - Toàn bộ danh sách 106 nguồn trong phiên làm việc bị kẹt ở trạng thái chưa hoàn tất (`semantic_preparing`).
  - Khi gửi câu hỏi thứ 2 ngay sau đó (`Lịch sử lỗi KDTPS...`), hệ thống kiểm tra trạng thái nguồn thấy chưa sẵn sàng nên lập tức trả về `quality_search_unavailable` trong vòng **0,01 giây** mà **không hề kích hoạt lại worker hay thử nạp lại**.
  - Người dùng bị "mất trắng" khả năng tìm kiếm ngữ nghĩa cho toàn bộ các lượt trò chuyện tiếp theo trong phiên làm việc đó, trừ khi ứng dụng được khởi động lại hoàn toàn.

---

## 4. Kết luận chẩn đoán & Đề xuất hướng sửa (Kiến nghị cho vé sau)

### 4.1. Tóm tắt nguyên nhân gốc (Root Cause)
1. **Lệch pha giữa thời gian nạp thực tế và trần Timeout**:
   - Khâu nạp mô hình ONNX fp32 (2,26 GB) trên CPU máy nhà mất từ **188s đến 214s**, cộng với việc preload cache dense (54s) và sparse (34–56s) của 121.331 đoạn dữ liệu khiến tổng thời gian khởi tạo thực tế dao động từ **245s đến 302s**.
   - Ngưỡng timeout khởi tạo `_INIT_TIMEOUT_SECONDS` trong code là **300.0s** (chỉ cần máy có tải nhẹ là bị tràn ngưỡng 2.2s).
   - Ngưỡng kết nối pipe `_PERSIST_SPAWN_WAIT_SECONDS` là **120.0s**, thấp hơn rất nhiều so với thời gian nạp ONNX trên CPU (188s).
2. **Thiếu cơ chế tự phục hồi (Self-healing)**:
   - Khi worker khởi tạo trễ và ném ngoại lệ timeout một lần, mã nguồn không có cơ chế hủy đánh dấu nguồn lỗi hoặc thử kết nối lại, dẫn đến tình trạng độc toàn bộ phiên làm việc.
3. **Môi trường máy nhà chưa tận dụng GPU**:
   - Máy có GPU GTX 1060 nhưng script khởi chạy đang ép dùng `torch==2.5.1+cpu` và `onnxruntime` CPU.

### 4.2. Đề xuất phương án kỹ thuật cho vé xử lý tiếp theo

- **Phương án 1 (Sửa timeout tức thì — Chi phí thấp, an toàn cao)**:
  - Nâng `_INIT_TIMEOUT_SECONDS` từ `300.0` lên **`420.0`** giây (7 phút) để tạo vùng đệm an toàn khi máy có tải nền.
  - Sửa `_PERSIST_SPAWN_WAIT_SECONDS` từ `120.0` lên **`360.0`** giây trong `bge_subprocess_client.py` (dòng 81) để client kiên nhẫn chờ worker nạp xong mô hình và mở named pipe.
- **Phương án 2 (Đổi backend khởi động nhanh hơn trên CPU máy nhà)**:
  - Xem xét kích hoạt mô hình lượng tử hóa **ONNX INT8** (`models/bge-m3-onnx-int8`) đã có sẵn trong repo hoặc cho phép fallback về PyTorch CPU (`BGE_BACKEND=pytorch`) vì thực nghiệm đã chứng minh PyTorch nạp chỉ mất **24,7 giây** (nhanh gấp 8 lần ONNX fp32).
- **Phương án 3 (Khắc phục tính độc phiên)**:
  - Trong `workspace_chat_rag_v2_adapter.py`, khi bắt gặp `preparation_init_bge_worker_persist_timeout`, tự động xóa cờ lỗi của registry chuẩn bị nguồn và cho phép retry ngầm trong lượt hỏi tiếp theo thay vì fail-fast vĩnh viễn với `semantic_preparing`.
