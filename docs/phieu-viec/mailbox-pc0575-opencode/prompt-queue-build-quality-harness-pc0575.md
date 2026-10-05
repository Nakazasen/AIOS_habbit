# Vé BUILD-QUALITY-HARNESS-PC0575 — Dựng khung đo chất lượng câu trả lời

**Máy thực hiện:** [CTY] KDTVN-PC0575 (thợ opencode).
**Role gợi ý:** DEFAULT (code + test).

## Bối cảnh

Vé `LSU-QUALITY-PC0575` (thợ OMP) sẽ đo chất lượng trả lời. Vé này dựng trước
khung đo để OMP tái dùng, khỏi đo tay từng câu.

## Việc cần làm

1. Viết `src/aios_habit/quality_harness.py`:
   - Nhập: danh sách câu hỏi (JSON) + rubric (thang điểm).
   - Chạy mỗi câu qua 1 lane do tham số chọn (`cagent` hoặc `rag`) — gọi qua interface
     lane có sẵn, KHÔNG đụng code lane hiện tại.
   - Xuất: bảng điểm CSV + JSON (mỗi câu: điểm từng tiêu chí, trích dẫn có/không).
2. Chạy thử với 5 câu mẫu × 2 lane, đối chiếu tay 5 câu để chắc khung chấm đúng.
3. Test `tests/test_quality_harness.py`: 5/5 pass (mock lane, không gọi mạng thật).
4. Tương thích Python 3.11. Không merge `main`.

## Rào cứng

- 1 file 1 đứa: chỉ tạo/sửa `quality_harness.py` + test của nó.
  Không sửa file lane, không sửa UI.
- Điểm đo là dữ liệu vận hành → chỉ ghi `local_cases/`, không ghi kho tri thức.
