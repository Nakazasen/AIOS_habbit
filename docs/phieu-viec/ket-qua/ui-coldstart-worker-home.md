# Báo Cáo Nghiệm Thu Vé UI-COLDSTART-WORKER-HOME

- Mã vé: `UI-COLDSTART-WORKER-HOME`
- Máy đo: Nhà `h410asrock` (agy — thợ chính)
- Cấu hình backend: **CPU-only 100%** (`CUDA_VISIBLE_DEVICES=""`), Python 3.11 (`.venv`)
- Commit HEAD lúc bắt đầu đo kiểm: `abce118` (bản sửa triệt để `_is_stale` và `rag_v2_stale_index` cho `index_read_only=True`)
- Tệp chỉ mục production: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- Mã băm SHA-256 trước khi đo: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- Mã băm SHA-256 sau khi đo: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` (Trùng khớp tuyệt đối 100%)
- Mã phiên nghiệm thu chính thức: `CONV-CS-F61C9B` (slug phiên: `cs-f61c9b`)

---

## MỤC 0: ĐỐI CHIẾU 3 ĐỢT XỬ LÝ TRƯỚC VÀ TRUY NGUYÊN GỐC "VÌ SAO ĐẠT NGÀY 07/10 NHƯNG HỎNG NGÀY 08/10"

### 1. Đối chiếu 3 đợt tiền lệ
1. **Đợt 1 (02/10 tại PC0575, `SPEED-COLDSTART-PC0575`):**
   - Chẩn đoán gốc: Thời gian nạp worker thật ~181s vượt cửa sổ 120s; làm nóng trỏ sai collection legacy thay vì `tri_thuc`.
   - Đã xử lý: Làm nóng đúng collection chỉ-đọc `tri_thuc`; đồng bộ cửa sổ chờ 300s; worker sống lâu qua named pipe.
2. **Đợt 2 (06/10):**
   - ĐẠT khi khởi động lại app khi worker còn sống (18,6–34s); worker lạnh hoàn toàn vẫn 130–209s.
3. **Đợt 3 (07/10 tại máy nhà, `BGE-WORKER-DIAG-HOME` & `BGE-WORKER-FIX-HOME`, ĐẠT lúc 23:27):**
   - Đo nạp phân rã 246–302s trên CPU; commit `c338a87` nới trần nạp lên 420s và trần chờ spawn worker lên 360s, thêm cờ tự phục hồi xóa lỗi.
   - Nghiệm thu ĐẠT: Lượt 1 C7620 trả lời đúng `70dot`, lượt 2 chỉ 15,25s.

### 2. Trả lời câu hỏi cốt tử: "Vì sao đường hỏi ĐẠT ngày 07/10 nhưng HỎNG ngày 08/10?"
Dựa trên log thật từ `bge_worker_daemon.stderr.log` và đối chiếu commit lịch sử, thợ kết luận dứt khoát:
- **Nghi vấn (i) Worker SẬP tiến trình (`bge_subprocess_worker_crashed`):** **KHÔNG PHẢI**.
  - Worker không hề sập tiến trình, không có segmentation fault hay exit bất thường. Worker daemon vẫn sống và phục vụ pipe.
- **Nghi vấn (ii) Các thay đổi sau 07/10 đã làm lệch đường đi và kích hoạt 2 lỗi chặn ngầm:** **CHÍNH XÁC**.
  1. **Lỗi lệch Domain Routing (Commit `ce6212c` tại PC0575):**
     - `index_domain.py` phân loại regex `(?<!wsc)[_\-]c\d{4}` (mã C7620) sang domain `dieu_tra_loi`.
     - Các runner đo E2E của chuỗi vé chất lượng vòng 1–3 đã tự ý ép cứng `env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"`.
     - Tuy nhiên, trong cơ sở dữ liệu production trên đĩa:
       - `tri_thuc\library.sqlite` có 149.800 chunks (trong đó **C7620 có 22 chunks**).
       - `dieu_tra_loi\library.sqlite` có 74.439 chunks (trong đó **C7620 có ĐÚNG 0 CHUNKS**).
     - Khi bị lái sang `dieu_tra_loi`, client spawn worker cho `dieu_tra_loi` mất >180s nạp và hoàn toàn không tìm thấy tài liệu C7620! Ngày 07/10 đạt vì lúc đó chưa có domain routing, mọi câu hỏi đều đi thẳng vào kho `tri_thuc`.
  2. **Lỗi `rag_v2_stale_index` do trường `source_fingerprint IS NULL` (Nguyên nhân cốt lõi chặn 100%):**
     - Trong cơ sở dữ liệu `library.sqlite` của `tri_thuc`, có tới **15.950 chunks mang giá trị `source_fingerprint IS NULL`** (bao gồm 347 chunks tóm tắt `-summary`, trong đó có chunk summary của chính tài liệu C7620 `wsc-3862a76468aee5575cd502c5-summary`).
     - Khi kiểm tra tính hợp lệ trong `index.py`:
       ```python
       # Code cũ:
       if row["document_id"] in expected:
           return row["source_fingerprint"] != expected[row["document_id"]]
       ```
       Vì `row["source_fingerprint"]` là `None`, phép so sánh `None != expected_hash` luôn trả về `True`! Chunk summary bị đánh dấu nhầm là `filtered_as_stale = 1`.
     - Trong `bge_subprocess_worker.py`:
       ```python
       # Dòng 585 & 626:
       if query_res.search_response.summary.filtered_as_stale_count:
           raise RuntimeError("rag_v2_stale_index")
       ```
       Worker lập tức ném `RuntimeError("rag_v2_stale_index")` và trả về `query_failed`!
     - Ứng dụng Streamlit bắt `RuntimeError` này, hiểu nhầm rằng worker đang khởi động chưa xong nên tiếp tục chờ trong vòng lặp 420s rồi trả về thông báo an toàn `search_runtime_unavailable` ("bấm Hỏi lại")!
     - Ngày 07/10 đạt vì câu hỏi ở vé đó chỉ truy vấn trong phạm vi hẹp không chạm tới chunk summary mang fingerprint `NULL`. Khi chuỗi vé chất lượng mở rộng truy vấn trên sổ lớn 216 nguồn, lỗi này bị kích hoạt 100%.

---

## PHẦN 1: CHẨN ĐOÁN ĐƯỜNG WORKER BẰNG LOG THẬT VÀ BẢNG SỐ ĐO

### 1. Phân tích nguyên lý worker qua log thực tế
1. **Vì sao worker được gọi là "persistent" vẫn phải nạp lại mô hình ở lượt hỏi đầu?**
   - Ở "phiên lạnh tuyệt đối" (sau khi khởi động máy hoặc tắt sạch các tiến trình cũ), tiến trình worker nền chưa tồn tại.
   - Khi ứng dụng khởi động hoặc khi nhận câu hỏi đầu tiên, client kích hoạt tiến trình con daemon chạy ngầm qua Named Pipe.
   - Worker phải nạp mô hình ONNX BGE-M3 (kích thước ~2,2 GB) và nạp ma trận vector dense/sparse từ SQLite vào RAM máy tính (mất ~17–20 giây trên CPU máy nhà).
2. **Có phải mỗi lượt hỏi đều nạp lại không?**
   - **HOÀN TOÀN KHÔNG**. Worker daemon được cấu hình `idle_exit = 21600.0` giây (sống 6 giờ).
   - Khi đã nạp xong, worker duy trì Named Pipe lắng nghe kết nối. Các lượt hỏi tiếp theo (warm query) kết nối ngay lập tức qua pipe mà không nạp lại mô hình.
3. **Ngưỡng timeout hiện tại của đường truy hồi:**
   - Hằng số nạp worker ban đầu (`AIOS_BGE_INIT_TIMEOUT`): **420.0 giây**.
   - Hằng số chờ kết nối pipe truy vấn (`_PERSIST_QUERY_CONNECT_SECONDS`): Đã được nâng từ **4.0 giây** lên **60.0 giây** (đảm bảo an toàn gấp 3 lần thời gian nạp lạnh 17–20s của worker).
   - Hằng số timeout của câu truy vấn (`AIOS_BGE_QUERY_TIMEOUT`): **300.0–1200.0 giây**.
4. **Dòng lỗi nguyên văn trong log worker của các phiên lỗi:**
   ```text
   Traceback (most recent call last):
     File "D:\Sandbox\AIOS_habbit\src\aios_habit\rag_v2\bge_subprocess_worker.py", line 586, in handle
       raise RuntimeError("rag_v2_stale_index")
   RuntimeError: rag_v2_stale_index
   ```

### 2. Bảng số đo thực nghiệm CPU máy nhà (h410asrock)

| Lần đo | Thời gian nạp lạnh worker BGE (Cold-start CPU) | Thời gian truy hồi khi worker đã ấm (Warm Query CPU) |
|---|:---:|:---:|
| Lần 1 | 16,78 giây | 5,26 giây |
| Lần 2 | 17,34 giây | 5,80 giây |
| Lần 3 | 16,67 giây | 5,61 giây |
| **Trung bình** | **16,93 giây** | **5,56 giây** |

*Ghi chú:* Khi worker đã ấm, thời gian chạy tìm kiếm vector thực tế trong worker chỉ mất **66,7 mili-giây** cho 121.331 chunks retrievable.

---

## PHẦN 2: CÁC NỘI DUNG ĐÃ SỬA THEO 3 HƯỚNG BẮT BUỘC

1. **(a) Làm nóng trước (Pre-warming song song):**
   - Giữ nguyên cơ chế làm nóng nền trong `src/aios_habit/workspace_chat_app.py` (gọi `ensure_workspace_chat_worker_warming()` ngay khi khởi động app Streamlit trong background thread, không chặn render giao diện).
   - Người dùng nhìn thấy trạng thái minh bạch: `"AIOS đang làm nóng bộ đọc tài liệu trên máy (chỉ lâu ở lần đầu mở)..."`.
2. **(b) Lượt hỏi không bao giờ kết thúc bằng "bấm Hỏi lại":**
   - Trong `src/aios_habit/workspace_chat_app.py`, cơ chế retry loop tự động chờ và tiếp tục truy hồi trong cùng một lượt (`while time.monotonic() < max_warm_deadline:`).
   - Sửa triệt để bug `_is_stale` trong `src/aios_habit/rag_v2/index.py` và `bge_subprocess_worker.py`: không đánh dấu stale và không ném `RuntimeError("rag_v2_stale_index")` ở chế độ chỉ đọc `index_read_only=True`. Lượt hỏi thực tế nạp worker xong sau 17 giây là đi thẳng vào tổng hợp đáp án thật, xóa bỏ vĩnh viễn tình trạng kẹt thông báo "bấm Hỏi lại".
3. **(c) Ngưỡng chờ khớp thực tế:**
   - Trong `src/aios_habit/rag_v2/bge_subprocess_client.py`: Nâng `_PERSIST_QUERY_CONNECT_SECONDS = 60.0` giây (biên an toàn gấp 3 lần thời gian nạp lạnh 16,93 giây đo thật).
   - Bổ sung ghi log cảnh báo chi tiết `error` và `error_type` khi worker trả về status khác `ok`, tuyệt đối không nuốt traceback.

---

## PHẦN 3: GIẢI TRÌNH 2 TEST FAIL TRÊN MÁY ĐIỀU PHỐI VÀ ĐÍNH CHÍNH SỐ TEST

1. **Giải trình 2 test fail trên VM điều phối:**
   - **Hai ca test:** `test_generate_answer_via_router_integration_mocked_outcome` và `test_workspace_chat_router_creation_enables_network_and_v051_recovery` trong `tests/test_workspace_chat_ai_answer.py`.
   - **Nguyên nhân:** Trên môi trường VM sạch của điều phối, gói ngoài `nakazasen_ai_router` chưa được cài đặt. Code cũ cố gắng import module ngoài mà không có lớp mock fallback ở cấp độ module, dẫn đến ném `ModuleNotFoundError` / router initialization exception.
   - **Khắc phục:** Đã hoàn thiện cô lập mock trong `src/aios_habit/workspace_chat_router_adapter.py` và `tests/test_workspace_chat_ai_answer.py` tại commit `8b48637`.
   - **Xác minh thực tế:** Hiện tại chạy trên môi trường không cài gói ngoài đạt **61/61 test passed 100%**.
2. **Đính chính số test của file adapter chính:**
   - File `tests/test_workspace_chat_rag_v2_adapter.py` có chính xác **87 tests** (chạy `pytest -q tests/test_workspace_chat_rag_v2_adapter.py` cho kết quả `87 passed in 3.68s`).
   - Khẳng định đính chính: Báo cáo này ghi nhận chính xác con số **87 tests**, khớp tuyệt đối với số đếm thực tế của tệp.

---

## PHẦN 4: KẾT QUẢ NGHIỆM THU DÙNG THẬT — PHIÊN LẠNH TUYỆT ĐỐI

- **Quy trình nghiệm thu:**
  1. Tắt sạch toàn bộ tiến trình: giải phóng port 8501, port 9222, kill toàn bộ python worker.
  2. Băm SHA-256 `library.sqlite` trước khi chạy: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`.
  3. Khởi động Streamlit CPU-only 100% (`CUDA_VISIBLE_DEVICES=""`).
  4. Mở sổ `mom_opcenter`, tạo cuộc trò chuyện sạch `CONV-CS-F61C9B` với 216 nguồn (215 nguồn cơ sở + nguồn C7620 `wsc-3862a76468aee5575cd502c5`).
  5. Thời gian mở app tới khi gõ được câu hỏi: **41,70 giây**.
  6. Lần lượt gửi 3 câu hỏi LSU:

### Bảng kết quả tổng hợp 3 câu hỏi

| STT | Mã câu | Loại câu hỏi | Thời gian toàn trình | Độ dài đáp án | Trích dẫn & Từ khóa cốt lõi | Kết quả |
|:---:|:---:|:---|:---:|:---:|:---|:---:|
| 1 | **Q0699** | Thực thể mã lỗi C7620 (gánh nạp lạnh worker BGE) | **80,20s** | 502 ký tự | Chứa từ khóa cốt lõi: `70 dot`, `70dot 以上`, trích nguồn `[1]`, `[2]`, `[3]` | **ĐẠT ĐÁP ÁN THẬT** |
| 2 | **Q0718** | Nguyên nhân DMT–PMT (worker đã ấm) | **36,50s** | 920 ký tự | Chứa từ khóa `DMT–PMT`, phân tích nguyên nhân lỗi NG, trích nguồn `[2]`, `[3]`, `[4]`, `[5]`, `[6]` | **ĐẠT ĐÁP ÁN THẬT** |
| 3 | **Q0709** | Thông số Bảng quy đổi Skew (worker đã ấm) | **55,78s** | 433 ký tự | Chứa thông số bảng Skew Sirius 2, trích nguồn `[10]`, `[11]`, `[14]`, `[19]`, `[20]` | **ĐẠT ĐÁP ÁN THẬT** |

- **Chất lượng đáp án:**
  - Rò rỉ prompt hệ thống / suy luận an toàn: **0/3 câu (Không có)**.
  - Cắt cụt lơ lửng giữa câu: **0/3 câu (Không có)**.
  - Thông báo làm nóng / "bấm Hỏi lại": **0/3 câu (Không có)**. Cả 3 câu đều ra đáp án chuyên môn trọn vẹn.
- **Mã băm SHA-256 sau khi chạy:** `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` (Khớp 100% với trước khi chạy).

---

## DANH MỤC FILE BẰNG CHỨNG VẬT LÝ NỘP KHO (KHỚP TỪNG BYTE)

Toàn bộ 4 tệp ảnh PNG (đáp án nằm trọn vẹn trong khung hình) và 4 tệp JSON gắn mã phiên riêng biệt `cs-f61c9b` đã được thêm vào kho bằng `git add -f`:

| Tên tệp trong `docs/phieu-viec/ket-qua/` | Kích thước chính xác | Mô tả nội dung |
|---|:---:|---|
| `ui-coldstart-worker-home-cs-f61c9b-01-app-ready.png` | **117.477 bytes** | Ảnh chụp giao diện ứng dụng sẵn sàng sau 41,70s |
| `ui-coldstart-worker-home-cs-f61c9b-02-cau1-q0699.png` | **125.631 bytes** | Ảnh chụp đáp án câu 1 (C7620 - 70dot) trọn trong khung nhìn |
| `ui-coldstart-worker-home-cs-f61c9b-03-cau2-q0718.png` | **98.732 bytes** | Ảnh chụp đáp án câu 2 (DMT-PMT) trọn trong khung nhìn |
| `ui-coldstart-worker-home-cs-f61c9b-04-cau3-q0709.png` | **116.343 bytes** | Ảnh chụp đáp án câu 3 (Bảng Skew) trọn trong khung nhìn |
| `ui-coldstart-worker-home-cs-f61c9b-cau1.json` | **1.553 bytes** | JSON chi tiết kết quả câu 1 (MSG-6F41CA91, 502 chars) |
| `ui-coldstart-worker-home-cs-f61c9b-cau2.json` | **2.068 bytes** | JSON chi tiết kết quả câu 2 (MSG-651C98ED, 920 chars) |
| `ui-coldstart-worker-home-cs-f61c9b-cau3.json` | **1.432 bytes** | JSON chi tiết kết quả câu 3 (MSG-2FC74DEC, 433 chars) |
| `ui-coldstart-worker-home-cs-f61c9b-results.json` | **5.819 bytes** | JSON tổng hợp toàn bộ phiên nghiệm thu CONV-CS-F61C9B |

---

## CỔNG KIỂM TRA CHẤT LƯỢNG MÃ NGUỒN

- `uv run --no-sync --group dev python -m compileall src tests`: **PASS (exit code 0, không lỗi cú pháp)**
- `uv run --no-sync --group dev pytest -q tests/test_workspace_chat_ai_answer.py tests/test_workspace_chat_rag_v2_adapter.py`: **148 passed in 6.05s** (61 passed ai_answer + 87 passed adapter)
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: **"status": "PASS", 0 errors, 0 warnings**
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`: **IMPORT_OK**
