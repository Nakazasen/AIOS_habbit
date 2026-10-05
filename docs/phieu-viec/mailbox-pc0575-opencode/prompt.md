# Vé PREP-WIRE-QA-MAPPING — Chuẩn bị dữ liệu 3.392 cặp hỏi đáp cho vé WIRE

**Thợ:** opencode
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
**Thư mục làm việc DUY NHẤT:** `D:\Sandbox\AIOS_habbit`
**Role OMP gợi ý:** DEFAULT (đọc nhiều file + build JSONL).
**Mục đích:** chuẩn bị sẵn dữ liệu sạch để vé `WIRE-QA-CAGENT-PC0575` (nối hỏi đáp vào giao diện qua lane C-Agent) chỉ còn việc nối UI, không phải xử lý dữ liệu thô.

## Bối cảnh

Khâu sinh + audit dữ liệu ChatGPT đã hoàn tất: **3.392 cặp duy nhất** (raw 3.393 trừ Q3214 trùng Q3124), verdict ĐẠT.
File fixed: `docs/phieu-viec/chatgpt-enrichment-fixed/` (3 nhóm: MOM, LSU, Điều-tra-lỗi).
Chi tiết audit: `docs/phieu-viec/ket-qua/audit-batch88-pc0575.md`.

## Việc cần làm

### Bước 1 — Đọc và build JSONL
- Đọc toàn bộ file fixed trong `docs/phieu-viec/chatgpt-enrichment-fixed/` (cả 3 nhóm).
- Build file `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl`: mỗi dòng 1 cặp, schema:
  `{"id": "Qxxxx", "question": "...", "answer": "...", "source": "<tên file fixed>", "category": "MOM|LSU|dieu-tra-loi", "batch": "<số batch>"}`
- Đọc schema thực tế từ file fixed (6 trường + nguồn đã audit) rồi map cho khớp, không bịa field.

### Bước 2 — Verify
- Đếm: đúng **3.392** dòng, id duy nhất không trùng.
- Kiểm tra ngẫu nhiên 20 cặp: question/answer không rỗng, mapping đúng file nguồn.
- Ghi kết quả verify vào báo cáo.

### Bước 3 — Báo cáo
- Viết `docs/phieu-viec/ket-qua/wire-qa-mapping.md`: số cặp theo từng category, ví dụ 3 cặp mẫu, ghi chú bất thường (nếu có).
- `xong-cho-duyet` khi JSONL đủ 3.392 cặp verified.

## Cấm kỵ
- Chỉ đọc file fixed, không sửa/xóa bất cứ file nguồn nào.
- Không cần runtime/app — vé này thuần xử lý file.
- Commit riêng nhánh `phieu-viec/rag-fix1`, không đụng `main`, không force-push.
