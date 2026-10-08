# Báo cáo vé AUDIT-DEEPSEEK-ROWS-HOME — Đếm lại độc lập file kết quả thô lượt đo DeepSeek

- **Máy làm:** NHÀ `h410asrock` (thợ OMP).
- **Thời điểm làm:** 2026-10-08 23:11 – 23:20 +07.
- **Nguồn đếm lại (chỉ đọc):** `C:/tmp/lsu-quality-rag-home/rows-synth-deepseek.jsonl` (ngoài kho, 50 dòng, 101.788 byte, ghi lúc 22:58 08/10) + file tổng `ket-qua-synth-deepseek.json` để đối chiếu chéo.
- **Báo cáo gốc đối chiếu:** `docs/phieu-viec/ket-qua/synth-deepseek-ab-home.md` (vé `SYNTH-DEEPSEEK-AB-HOME`).
- **Cách đếm:** đọc từng dòng JSON, cộng trường `tong`, đếm trường `che_do` / `uncited`, đếm điểm `tong` mốc 3,0 và ≥ 2,0, tính trung bình + số giữa hai trường `giay_cau` / `giay_tong`, cộng `prompt_tokens` / `completion_tokens` / `credits_cau`.

## 1. Bảng đối chiếu khai so với đếm lại

| Mục vé yêu cầu | Báo cáo gốc khai | Đếm lại từ file thô | Khớp hay lệch |
|---|---|---|---|
| Tổng số dòng / câu | 50 / 50 | 50 dòng | Khớp |
| Tổng điểm và GPA | 63,18 / 150 — GPA 1,26 | Cộng trường `tong` = 63,18 → GPA 1,2636 làm tròn 1,26 | Khớp |
| Chế độ validated | 3 (Q0851, Q0620, Q2157) | `provider_validated` = 3, đúng 3 mã Q0851, Q0620, Q2157; cờ `validated=true` cũng đúng 3 dòng này | Khớp |
| Chế độ fallback | 43 | `local_extractive_provider_fallback` = 43 | Khớp |
| Chế độ not-called | 4 (Q0824, Q0704, Q0718, Q0668) | `local_extractive_provider_not_called` = 4, đúng 4 mã Q0824, Q0704, Q0718, Q0668 | Khớp |
| Số câu không trích dẫn | 10 | Cờ `uncited=true` = 10 (Q0851, Q0620, Q0701, Q0635, Q0636, Q0693, Q1777, Q1827, Q2157, Q0662) | Khớp |
| Số câu đạt 3,0 điểm | 6 | `tong == 3,0` = 6 (Q0689, Q0695, Q0674, Q0693, Q1777, Q0680) | Khớp |
| Số câu ≥ 2,0 điểm | 7 | `tong >= 2,0` = 7 (6 câu trên + Q0636 đạt 2,33) | Khớp |
| Thời gian toàn câu trung bình / số giữa | 25,19 / 22,42 giây | Trường `giay_cau`: trung bình 25,19 — số giữa 22,42 | Khớp |
| Thời gian tổng hợp trung bình / số giữa | 19,37 / 16,96 giây | Trường `giay_tong`: trung bình 19,37 — số giữa 16,96 | Khớp |
| Tổng token vào / ra / tổng | 199.974 vào; 104.990 ra; 304.964 tổng | Cộng `prompt_tokens` = 199.974; `completion_tokens` = 104.990; `total_tokens` = 304.964 | Khớp |
| Chi phí | $0,092991 | Cộng `credits_cau` = 0,092991 | Khớp |
| File tổng `ket-qua-synth-deepseek.json` | (căn cứ phụ) | Mọi số trong file tổng trùng báo cáo gốc và trùng số đếm lại | Khớp |

## 2. Kết luận

**Kết luận một câu: mọi số đếm lại từ file thô khớp toàn bộ báo cáo gốc, không có lệch nào.**

## 3. Ghi nhận thêm (ngoài vé, chỉ đọc thấy)

- 3 câu validated đều có `uncited=true` (điểm validated 1,0 / 1,67 / 1,0 — qua kiểm định nhưng đáp án không trích dẫn theo cờ này).
- 4 câu not-called đều có `co_trich_dan=false` và `uncited=false` (không gọi nên không tính thiếu trích dẫn).
- Cờ `ok=true` cả 50/50 dòng, 0 lỗi kỹ thuật — khớp khai 0% lỗi.
- Số lần gọi provider mỗi câu (`so_lan_goi_provider`): 0 lần = 38 câu, 1 lần = 10 câu, 2 lần = 2 câu.

## 4. Rào cứng đã giữ

- Chỉ đọc file kết quả, không sửa file, không chạy lại lượt đo, không đụng cấu hình hay khóa.
- Không ghi chỉ mục, không chạm mã nguồn, không trộn nhánh chính.
