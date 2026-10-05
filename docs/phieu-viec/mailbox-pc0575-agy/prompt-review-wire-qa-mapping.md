# VÉ: REVIEW-WIRE-QA-MAPPING (review chéo từ góc nhìn C-Agent)

- Mã vé: `REVIEW-WIRE-QA-MAPPING`
- Role OMP gợi ý: SMOL (review nhanh, ~15-20 phút)
- Máy: KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/review-wire-qa-mapping.md`

## Bối cảnh

Hai vé prep cho `WIRE-QA-CAGENT-PC0575` đã ĐẠT:
- agy (mày) viết spec C-Agent: `docs/phieu-viec/ket-qua/wire-cagent-spec.md`
- opencode build JSONL 3.392 cặp: `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl`

Trước khi nối hai thứ lại, cần một cặp mắt độc lập kiểm tra **tính tương thích** — mày review sản phẩm của opencode từ góc nhìn người sẽ gọi API.

## Việc cần làm

1. Đọc `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (3.392 dòng).
2. Đọc lại spec của mày `docs/phieu-viec/ket-qua/wire-cagent-spec.md`.
3. Kiểm tra tương thích, trả lời các câu hỏi:
   - JSONL có đủ field để build request đúng format spec không?
   - Có cặp nào sẽ gây khó cho API không: câu hỏi quá dài, ký tự đặc biệt, answer rỗng/mỏng, category không khớp 3 nhóm (MOM/LSU/dieu-tra-loi)?
   - 3 câu demo trong spec có tìm được cặp tương ứng tốt trong JSONL không?
   - Timeout 60s + 1 retry có hợp lý với độ dài answer trung bình trong JSONL không (lấy mẫu ~20 dòng tính độ dài trung bình)?
4. KHÔNG sửa JSONL, KHÔNG sửa spec — chỉ review, ghi nhận issue.

## Tiêu chí nghiệm thu

- Báo cáo `review-wire-qa-mapping.md` có: verdict OK/KHÔNG OK để nối, danh sách issue cụ thể (nếu có, kèm id dòng), hoặc "không phát hiện vấn đề tương thích".
- Verdict ĐẠT = đã đọc cả hai file, đã trả lời đủ 4 câu hỏi trên, báo cáo trung thực.
