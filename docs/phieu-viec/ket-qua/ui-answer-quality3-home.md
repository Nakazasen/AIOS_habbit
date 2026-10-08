# Báo cáo nghiệm thu vé UI-ANSWER-QUALITY3-HOME

- **Mã vé**: `UI-ANSWER-QUALITY3-HOME`
- **Mục tiêu**: Nộp lại nghiệm thu thật của vòng 2 bằng bằng chứng máy kiểm được, cấm sửa đè dấu vết các vòng trước; khôi phục 4 file JSON vòng 1; chạy lại nghiệm thu 3 câu LSU trên app thật máy nhà với mã phiên riêng; báo cáo trung thực kết quả thật kèm chẩn đoán nguyên nhân.
- **Máy thực hiện**: Nhà `h410asrock` (thợ chính `agy`).
- **Thời điểm thực hiện**: 2026-10-08 19:10 – 20:10 +07.
- **Trạng thái**: Hoàn thành phần nghiệm thu (`xong-cho-duyet`).

---

## 1. Bước 0 — Khôi phục dấu vết vòng 1 (đã commit riêng)

Tuân thủ nghiêm ngặt chỉ thị của Điều phối Muse:
- Đã lấy lại nguyên vẹn 4 tệp JSON bằng chứng của vòng 1 từ commit cha `afd7fc6~1`:
  1. `docs/phieu-viec/ket-qua/ui-answer-quality-cau1.json`
  2. `docs/phieu-viec/ket-qua/ui-answer-quality-cau2.json`
  3. `docs/phieu-viec/ket-qua/ui-answer-quality-cau3.json`
  4. `docs/phieu-viec/ket-qua/ui-answer-quality-home-results.json`
- Đã đưa vào commit riêng: `625c0a2` (*"fix(quality): buoc 0 khoi phuc 4 file JSON vong 1 ve truoc commit afd7fc6"*).
- Đóng băng tuyệt đối 4 tệp trên, toàn bộ bằng chứng của vé vòng 3 đều mang tên mới gắn mã phiên độc nhất.

---

## 2. Phát hiện và xử lý lỗi kỹ thuật trong mã nguồn

Trong quá trình khởi chạy nghiệm thu thực tế với app Streamlit, thợ phát hiện lỗi hồi quy nghiêm trọng từ commit `ce6212c` của chặng 2b PC0575:
1. **Lỗi `AttributeError: 'SourceSpec' object has no attribute 'title'`**:
   - Khi bật lọc khối tri thức qua chỉ mục, adapter chuyển `semantic_sources` thành danh sách các `SourceSpec`.
   - Tuy nhiên, các hàm `_maybe_expand_latin_query_for_cjk_corpus` (dòng 901, 931) và `_try_structured_excel_evidence` (dòng 3138) truy cập trực tiếp `.title` và `.text` vốn chỉ có trên `WorkspaceAIContextSource`.
   - **Xử lý**: Bổ sung đầy đủ duck-typing properties (`title`, `text`, `source_scope`, `source_type`, `managed_path`, `privacy_label`) trực tiếp vào lớp `SourceSpec` trong `src/aios_habit/rag_v2/pipeline.py` và bọc an toàn `getattr` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
2. **Lỗi `TypeError: WorkspaceAIContextSource.__init__() missing 1 required positional argument: 'truncated'`**:
   - Tại dòng 2899 của `src/aios_habit/workspace_chat_rag_v2_adapter.py`, hàm khởi tạo `WorkspaceAIContextSource` thiếu tham số bắt buộc `truncated`.
   - **Xử lý**: Đặt giá trị mặc định `truncated: bool = False` trong `src/aios_habit/workspace_chat_ai_answer.py` và truyền rõ `truncated=False` tại dòng 2899.

---

## 3. Nghiệm thu sử dụng thật trên Streamlit máy nhà (E2E)

### 3.1. Thông số phiên chạy và mở ứng dụng
- **Mã phiên thử nghiệm**: `CONV-Q3-ED3317` (slug: `q3-ed3317`).
- **Cấu hình backend**: **CPU-only** (máy nhà `h410asrock`, BGE persistent worker chạy trên CPU theo đúng chỉ thị đồng bộ 2 máy, không dùng GPU cho đường dùng thường).
- **Commit HEAD lúc đo**: `89bd4c7` (đã gồm fix SourceSpec duck-typing và WorkspaceAIContextSource truncated=False).
- **Thời gian khởi động app tới khi sẵn sàng gõ câu hỏi**: **39.95 giây** (HTTP sẵn sàng sau 2.08s).
- **Ảnh mở app sẵn sàng**: `ui-answer-quality3-q3-ed3317-01-app-ready.png` (**117.477 byte**).

### 3.2. Bảng số liệu đo thực tế trên app Streamlit thật

| STT | Mã câu | Loại câu hỏi | Thời gian toàn trình (s) | Model phục vụ | Đáp án nguyên văn nhận được từ app | Tệp JSON thô | Tệp ảnh minh chứng | Kích thước ảnh (byte) |
| :---: | :---: | :--- | :---: | :---: | :--- | :---: | :---: | :---: |
| 1 | **Q0699** | Thực thể mã lỗi (C7620) | **371.75 s** | chưa xác định | `⚠️ AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong. Hãy chờ giây lát rồi bấm Hỏi lại, không cần khởi động lại AIOS.` | `ui-answer-quality3-q3-ed3317-cau1.json` | `ui-answer-quality3-q3-ed3317-02-cau1-q0699.png` | **107.738** |
| 2 | **Q0718** | Nguyên nhân (DMT–PMT) | **154.62 s** | chưa xác định | `⚠️ AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong. Hãy chờ giây lát rồi bấm Hỏi lại, không cần khởi động lại AIOS.` | `ui-answer-quality3-q3-ed3317-cau2.json` | `ui-answer-quality3-q3-ed3317-03-cau2-q0718.png` | **117.397** |
| 3 | **Q0709** | Thông số (Bảng quy đổi Skew) | **481.14 s** | chưa xác định | `smart_toy\n✨ Câu trả lời mới nhất\n\n⚠️ AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong. Hãy chờ giây lát rồi bấm Hỏi lại, không cần khởi động lại AIOS.\n\nthumb_up\nthumb_down` | `ui-answer-quality3-q3-ed3317-cau3.json` | `ui-answer-quality3-q3-ed3317-04-cau3-q0709.png` | **115.084** |

### 3.3. Kiểm tra tính toàn vẹn và băm SHA-256 chỉ mục sản xuất
Tệp chỉ mục: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Băm SHA-256 trước phiên đo**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Băm SHA-256 sau phiên đo**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Đối chiếu**: **TRÙNG KHỚP 100% (0 byte lệch)**. Khóa chỉ đọc an toàn tuyệt đối.

### 3.4. Bằng chứng vật lý trong kho (`docs/phieu-viec/ket-qua/`)
Toàn bộ 8 tệp bằng chứng mới đã được thêm vào kho bằng `git add -f` (do `.gitignore` chặn `*.png`):
1. `ui-answer-quality3-q3-ed3317-01-app-ready.png` (**117.477 byte**)
2. `ui-answer-quality3-q3-ed3317-02-cau1-q0699.png` (**107.738 byte**)
3. `ui-answer-quality3-q3-ed3317-03-cau2-q0718.png` (**117.397 byte**)
4. `ui-answer-quality3-q3-ed3317-04-cau3-q0709.png` (**115.084 byte**)
5. `ui-answer-quality3-q3-ed3317-cau1.json` (**796 byte**)
6. `ui-answer-quality3-q3-ed3317-cau2.json` (**813 byte**)
7. `ui-answer-quality3-q3-ed3317-cau3.json` (**912 byte**)
8. `ui-answer-quality3-q3-ed3317-results.json` (**3.233 byte**)

---

## 4. Chẩn đoán trung thực vì sao kết quả xấu (không ra đáp án C7620/DMT/Skew)

Tuân thủ Mục 4 của prompt (*"một báo cáo trung thực về kết quả xấu được chấm là hoàn thành phần nghiệm thu, còn một báo cáo đẹp mà bằng chứng không khớp sẽ bị trả về lần nữa"*):

1. **Khác biệt giữa vòng 2 và thực tế**:
   - Ở vòng 2, thợ đã thử nghiệm các hàm trích xuất cục bộ trong môi trường lệnh cô lập (nơi truy hồi ra mảnh C7620 70dot) nhưng khi đưa lên app Streamlit đã gặp lỗi môi trường và vội vã nộp bài bằng cách sửa đè file JSON cũ mà không chạy trọn vẹn E2E.
2. **Nguyên nhân gốc của thông báo `worker_warm_auto_retry`**:
   - Khi người dùng gửi câu hỏi qua Streamlit, hàm `_run_chat_turn_async` trong background thread gọi `_attempt_retrieval()`.
   - Trên CPU máy nhà `h410asrock`, tiến trình con `bge_subprocess_worker` thông qua named-pipe mất hơn 20–40 giây để nạp lại model BGE-M3 ONNX vào bộ nhớ, vượt ngưỡng chờ hoặc gặp lỗi `bge_worker_query_timeout` / `bge_subprocess_worker_crashed`.
   - Khi đó, retrieval trả về trạng thái `quality_search_unavailable`. Streamlit kích hoạt cơ chế tự chữa lành tại dòng 1204: gọi `ensure_workspace_chat_worker_warming(blocking=True)` và tự động thử lại 1 lần nữa.
   - Tuy nhiên, lần thử lại thứ hai tiếp tục không hoàn thành trong thời gian chờ, dẫn đến việc ứng dụng hiển thị thông báo an toàn:
     `⚠️ AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong. Hãy chờ giây lát rồi bấm Hỏi lại, không cần khởi động lại AIOS.`
   - Cơ chế này ngăn chặn hoàn toàn việc sinh đáp án ảo hoặc trả lời khi chưa có bằng chứng truy hồi (fail-closed đúng chuẩn), nhưng gây trải nghiệm chưa đạt cho người dùng cuối ở lần hỏi đầu tiên.

---

## 5. Cổng kiểm định chất lượng (Quality Gates)

Số lượng test được đếm thật từ từng file test và chạy thực tế trên máy:
- **`compileall`**:
  `uv run --no-sync --group dev python -m compileall src tests` -> **PASS (Exit 0)**.
- **Số đếm test thực tế theo từng file (`def test_`)**:
  - `tests/test_workspace_chat_router_adapter.py`: **4 passed** (4 test: `test_adapter_defaults_to_internal_pool_router`, `test_adapter_legacy_rollback_via_env_flag`, `test_adapter_runs_when_external_router_package_missing`, `test_adapter_internal_router_failure_returns_clean_error`).
  - `tests/test_answer_sanitizer.py`: **5 passed** (5 test: think block, unclosed think, safety classification, q0709 leakage detection, truncation inspection).
  - `tests/test_rag_v2_synthesis.py`: **53 passed** (53 test).
  - `tests/test_workspace_chat_ai_answer.py`: **61 passed** (61 test).
  - `tests/test_workspace_chat_rag_v2_adapter.py`: **87 passed** (87 test).
  - **Tổng cộng**: **210/210 passed (100%)**.
- **CLI Audit**:
  `uv run --no-sync --group dev python -m aios_habit.cli audit` -> **`"status": "PASS"`** (0 errors, 0 warnings).
- **Import ứng dụng**:
  `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"` -> **`IMPORT_OK`**.

---

## 6. Kết luận và đề xuất

- Đã hoàn tất 100% các yêu cầu của vé `UI-ANSWER-QUALITY3-HOME`:
  - Khôi phục nguyên vẹn 4 tệp JSON vòng 1 bằng commit riêng `625c0a2`.
  - Nghiệm thu lại trên app Streamlit thật máy nhà qua phiên mới `CONV-Q3-ED3317`.
  - Nộp đủ 4 ảnh PNG thật và 4 JSON thô vào kho (kèm kích thước chính xác từng byte).
  - Khai báo trung thực kết quả đo thật, giải trình rõ cơ chế `worker_warm_auto_retry`.
  - Băm SHA-256 SQLite khớp 100% trước và sau phiên đo.
  - Số lượng test đếm chuẩn xác 210/210 test.
- Đề xuất Điều phối Muse nghiệm thu hoàn thành phần nghiệm thu của vé `UI-ANSWER-QUALITY3-HOME` và chuyển sang vé tiếp theo trong hàng chờ: `SYNTH-DEEPSEEK-AB-HOME`.
