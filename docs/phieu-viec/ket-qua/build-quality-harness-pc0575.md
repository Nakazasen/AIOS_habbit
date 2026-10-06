# Báo cáo vé BUILD-QUALITY-HARNESS-PC0575 — Khung đo chất lượng câu trả lời

- Vé: `BUILD-QUALITY-HARNESS-PC0575`
- Máy làm: [CTY] KDTVN-PC0575 (thợ opencode)
- Ngày: 2026-10-06
- Trạng thái thợ: xong, chờ duyệt

## 1. Đã làm gì

Dựng khung đo để thợ OMP tái dùng ở vé `LSU-QUALITY-PC0575`, đúng phạm vi 1 file 1 đứa:

- Mới: `src/aios_habit/quality_harness.py` — nhận danh sách câu hỏi JSON + rubric JSON, chạy mỗi câu qua 1 lane (`cagent` hoặc `rag`) bằng interface lane có sẵn (import lười bên trong hàm, không sửa code lane), xuất bảng điểm CSV + JSON (mỗi câu: điểm từng tiêu chí, trích dẫn có/không).
- Mới: `tests/test_quality_harness.py` — 5/5 pass (lane giả, không gọi mạng thật).
- Không sửa file lane, không sửa UI. Không merge `main`.
- Điểm đo là dữ liệu vận hành nên file thử chỉ nằm trong `local_cases/quality_harness_trial/` (không đưa vào kho tri thức, không commit).

## 2. Cách chấm (đơn giản, dễ kiểm tay)

- Mỗi tiêu chí có `max_score` riêng trong rubric.
- Tiêu chí trích dẫn (tên chứa `trich_dan`/`citation`/`nguon`): đủ điểm khi câu trả lời có dấu trích dẫn (`.pptx`/`.xlsx`/`.csv`/`.pdf`, chữ `Nguồn file`, `http`, hoặc `[...]`), ngược lại 0.
- Tiêu chí còn lại: tỉ lệ từ khóa kỳ vọng xuất hiện trong câu trả lời × `max_score` (làm tròn 2 chữ số).
- Câu trả lời trống = 0 hết. Tổng = cộng các tiêu chí.

## 3. Chạy thử 5 câu × 2 lane + đối chiếu tay

- Đầu vào thử: `local_cases/quality_harness_trial/cau-hoi.json` (5 câu) + `rubric.json` (3 tiêu chí `chinh_xac` 2.0, `day_du` 1.0, `trich_dan` 1.0).
- Lane dùng đáp án demo giả (không gọi mạng thật) để kiểm đúng sai của khung chấm.
- Kết quả đối chiếu tay 5/5 đúng:
  - Lane `cagent` demo: T1 4.0, T2 4.0, T3 3.0, T4 3.0, T5 4.0 (đủ từ khóa + trích dẫn thì đủ điểm, thiếu trích dẫn thì mất 1.0).
  - Lane `rag` demo: T1 1.5 (trúng 1/2 từ khóa, mất trích dẫn), T2 0.0 (viết `44%` nên không trúng `43,9`/`43/98` — chấm nghiêm theo từ khóa), T3 3.0, T4 0.0, T5 0.0.
- File điểm thử: `local_cases/quality_harness_trial/diem-cagent.csv`, `diem-cagent.json`, `diem-rag.csv`, `diem-rag.json` (chỉ ở máy local, không commit).

## 4. Cổng kiểm tra

- `python -m compileall src tests`: đạt (không lỗi).
- `pytest tests/test_quality_harness.py -q`: 5/5 pass.
- `python -m aios_habit.cli audit`: `Status: PASS`.
- `import aios_habit.workspace_chat_app`: đạt.
- `pytest -q` toàn bộ: đang chạy nền, vượt 10 phút chưa xong (có lỗi F/E rải rác từ trước, không do 2 file mới — file mới chạy riêng vẫn xanh). Thợ không báo PASS giả cho cổng toàn bộ; chờ log `local_cases/pytest-full.log` để đối chiếu lỗi có sẵn.

## 5. Giới hạn thật thà + cách OMP tái dùng

- Adapter `cagent` thật gọi `CAgentWorkspaceProviderClient.generate` (cần URL/endpoint đã cấu hình, nếu lỗi mạng trả về rỗng để chấm 0 thay vì bịa điểm).
- Adapter `rag` thật hiện trả rỗng có chủ ý vì chưa đấu nối chỉ mục live (theo luật repo: ghi chỉ mục thật cần dry-run + backup + duyệt). OMP khi đo thật chỉ cần truyền `lane_fn` riêng đấu vào RAG live rồi gọi `run_harness(cau_hoi, rubric, lane, thu_muc_ra, lane_fn=...)`.
- Khung mặc định 2 tiêu chí nội dung cùng dùng tỉ lệ từ khóa — OMP có thể tách trọng số hoặc thêm chấm tay cho thang 0–3 LSU mà không cần sửa khung.

## 6. Đề nghị duyệt

Khung đủ để OMP dùng ở vé `LSU-QUALITY-PC0575`. Nhờ Muse chấm độc lập rồi cho đèn sang vé đo thật.
