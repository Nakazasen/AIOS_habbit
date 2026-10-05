# VÉ: REVIEW-WIRE-CAGENT-SPEC (review chéo từ góc nhìn dữ liệu)

- Mã vé: `REVIEW-WIRE-CAGENT-SPEC`
- Role OMP gợi ý: SMOL (review nhanh, ~15-20 phút)
- Máy: KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/review-wire-cagent-spec.md`

## Bối cảnh

Hai vé prep cho `WIRE-QA-CAGENT-PC0575` đã ĐẠT:
- agy viết spec C-Agent: `docs/phieu-viec/ket-qua/wire-cagent-spec.md`
- opencode (mày) build JSONL 3.392 cặp: `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl`

Trước khi nối hai thứ lại, cần một cặp mắt độc lập kiểm tra **tính tương thích** — mày review sản phẩm của agy từ góc nhìn người nắm dữ liệu.

## Việc cần làm

1. Đọc `docs/phieu-viec/ket-qua/wire-cagent-spec.md` (spec của agy).
2. Đọc lại JSONL của mày `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (không cần đọc hết, lấy mẫu).
3. Kiểm tra tương thích, trả lời các câu hỏi:
   - Spec có tính đến shape thực tế của data không (6 trường id/question/answer/source/category/batch)?
   - 3 câu demo trong spec có khả thi với data hiện có không (tìm được cặp tương tự trong JSONL)?
   - 5 kịch bản lỗi tiếng Việt trong spec có kịch bản nào data có thể trigger không (vd câu quá dài, ký tự đặc biệt)?
   - Nhãn "Bản thảo — chưa qua chuyên gia duyệt" có được spec yêu cầu hiển thị ở demo không?
4. KHÔNG sửa JSONL, KHÔNG sửa spec — chỉ review, ghi nhận issue.

## Tiêu chí nghiệm thu

- Báo cáo `review-wire-cagent-spec.md` có: verdict OK/KHÔNG OK để nối, danh sách issue cụ thể (nếu có), hoặc "không phát hiện vấn đề tương thích".
- Verdict ĐẠT = đã đọc cả hai file, đã trả lời đủ 4 câu hỏi trên, báo cáo trung thực.
