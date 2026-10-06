# Vé RAG-CLAIM-BUDGET-HOME — Điều tra + xử lý nút thắt `claim_budget_exceeded` trong kiểm định tổng hợp, đo lại 50 câu LSU

**Máy thực hiện:** NHÀ h410asrock (thợ OMP).
**Role gợi ý:** DEFAULT (điều tra dữ liệu thật + sửa logic/hợp đồng có kiểm soát + test + đo lại).
**Nguồn:** báo cáo `docs/phieu-viec/ket-qua/rag-synth-validation-home.md` §5 + §7 (vé `RAG-SYNTH-VALIDATION-HOME`, verdict Muse ĐẠT phần cơ chế + validated 2026-10-07 ~05:28 +07).

## Bối cảnh (số đã kiểm chứng độc lập bởi Muse)

- Lane SYNTH (sau vé phối hợp cắt-dòng → sửa): **61,17/150, GPA 1,22**; qua kiểm định **9/50** (FIX1: 6/50); fallback 39, ABSTAIN/not_called 2; 0 lỗi kỹ thuật, 0 lỗi mạng, index chỉ-đọc SHA-256 `45eb0e07…b7c0` khớp trước/sau.
- GPA **giảm** so với FIX1 (1,29 → 1,22) dù validated tăng: 9 câu validated đều rubric 1,0; 2 câu lost (Q0703, Q0693) đều do lượt đo này provider trả thêm lỗi `claim_budget_exceeded` và lượt sửa **không nén nổi** xuống dưới ngân sách.
- Đếm lỗi theo 66 lượt gọi (SYNTH): `uncited_material_claim` 64, `missing_citations` 53, **`claim_budget_exceeded` 35 (+4 so với FIX1 — nút thắt lớn thứ ba và đang tăng)**, `unsupported_critical_literal` 25, `missing_required_facet_citation` 2, `missing_required_limitations` 2.
- 18 lượt sửa ở lane SYNTH: **0 lượt** có `literal`/`unknown` trong đầu vào (rào cứng của vé trước giữ đúng).

## Gốc cần soi trong code (đối chiếu `src/aios_habit/rag_v2/synthesis.py` tại HEAD `c94bcce`)

- Ngân sách claim: `max_claims` mặc định 8 (~dòng 242; có nhánh hiệu lực nâng lên 10 ~dòng 250–252); hợp đồng gửi provider đã ghi rõ "Maximum material claims: {plan.max_claims}" (~dòng 314).
- Hợp đồng sửa đã có hướng dẫn nén (~dòng 342: "If the draft exceeded the claim budget, COMPRESS related factual lines…") — nhưng thực tế lane thật cho thấy sửa xong vẫn vượt ngân sách (Q0703/Q0693).
- Kiểm định đếm dòng material: `len(material_lines) > plan.max_claims` → `provider_answer_claim_budget_exceeded` (~dòng 504). Đây là **chuẩn kiểm định — cấm nới** (xem rào cứng).

## Việc phải làm

1. **Điều tra trước (chỉ đọc, từ dữ liệu thật):** dùng `rows-synth.jsonl` + `rows-fix1.jsonl` (máy nhà, ngoài Git) + code hiện tại:
   - Đếm có bao nhiêu câu fallback mà lỗi **cuối cùng còn lại** (sau cắt-dòng/sửa) là `claim_budget_exceeded` (thuần hoặc phối hợp), tách theo lượt gọi 1/2.
   - Phân bố số dòng material thực tế so với `max_claims` của từng câu (vượt bao nhiêu dòng: +1, +2, hay vượt xa?).
   - Kiểm hợp đồng thực gửi trong lượt đo có thật chứa giới hạn claim + hướng dẫn nén không; lượt sửa nhận `repair_errors` gì và bản sửa trả về còn vượt bao nhiêu.
   - Kết luận gốc thuộc nhóm nào: (a) provider không tuân hợp đồng ngay từ lượt 1; (b) lượt sửa nén không đủ/không được kích hoạt đúng; (c) ngân sách không khớp hình dạng câu trả lời mà plan yêu cầu (facet/bắt buộc) — kèm bằng chứng từng nhóm.
2. **Sửa theo gốc đã chứng minh** — chỉ ở phía *tạo câu trả lời / hợp đồng / cơ chế sửa xác định*, ví dụ (thợ chọn theo bằng chứng mục 1, ghi rõ lựa chọn + lý do trong báo cáo): làm hợp đồng lượt 1 cụ thể hoá ngân sách theo từng mặt bắt buộc; tăng hiệu lực nén ở lượt sửa (nén xác định các dòng liên quan giữ nguyên trích dẫn/mã/số đúng nguyên văn); hoặc thêm đường xử lý riêng cho lỗi ngân sách còn lại sau sửa. Mọi phương án đều phải giữ nguyên kiểm định cuối: chỉ nhận khi `valid`.
3. **Rào cứng — KHÔNG nới chuẩn:**
   - **Không tăng `max_claims`**, không đổi cách đếm dòng material, không tắt/bỏ bất kỳ lỗi kiểm định nào, không hạ ngưỡng, không đổi rubric.
   - Không đưa `unsupported_critical_literal` / `unknown_citation` vào tập sửa-được (giữ nguyên hard stop vé trước: chỉ cắt bỏ).
   - Fail-closed giữ nguyên: hết đường xử lý → fallback/ABSTAIN như cũ. Không vì đạt số mà nhận câu chưa qua full validation.
4. **Test (bắt buộc, trong repo):**
   - Test mới: (a) ứng viên vượt ngân sách thuần → qua được nhờ cơ chế mới (kèm đối chứng FAIL trên code cũ nếu cơ chế là code mới); (b) ứng viên vượt ngân sách + chứa literal bịa/nguồn lạ → literal vẫn chỉ bị cắt, không được "nén/sửa cho có căn cứ", hết nội dung hợp lệ thì vẫn fail-closed; (c) hồi quy: 3 test của vé SYNTH + hành vi thuần cắt-được/thuần sửa-được giữ nguyên.
   - Chạy cụm synthesis + cụm rộng `tests/test_rag_v2_*.py` + cổng repo (compileall, `cli audit`, import app); fail ngoài phạm vi thì đối chứng trên code cũ và phân loại, không giấu. Tương thích Python 3.11, không syntax 3.12+.
5. **Đo lại trọn 50 câu** bằng đúng điều kiện FIX1/SYNTH (runner ngoài Git cùng logic: hybrid + `openai_compatible_local` qua cầu `127.0.0.1:8585`, CPU-only, index chỉ-đọc + SHA-256/md5 trước/sau, checkpoint từng câu, cùng bộ câu + rubric). Đối chiếu 4 cột: lượt này / SYNTH (GPA 1,22, validated 9/50) / FIX1 (1,29; 6/50) / C-Agent (2,16). Mục tiêu: validated tăng rõ so với 9/50 **và** GPA không giảm; nếu không đạt, báo cáo trung thực kèm đếm lỗi mới — không nới chuẩn để đạt số. Lưu ý provider trả nội dung khác nhau giữa các lượt: phân tích gain/lost từng câu như các báo cáo trước.
6. Không ghi index. Không merge `main`. Mọi commit trên `phieu-viec/rag-fix1`, commit code riêng, commit báo cáo riêng.

## Nhịp heartbeat (BẮT BUỘC)

Mỗi **15 phút** append mốc `` `ghi_chu` `` vào `trang-thai.md` mailbox này. Cấm im lặng quá 15 phút. Vé dài: checkpoint/resume được (runner đã có checkpoint từng câu).

## Báo cáo

`docs/phieu-viec/ket-qua/rag-claim-budget-home.md` — kết quả điều tra mục 1 (số đếm + phân bố + phân loại gốc), thay đổi code/hợp đồng (trước/sau, đúng file/dòng), test mới + hồi quy, bảng đo lại 50 câu (điểm + chế độ từng câu), đếm lỗi kiểm định trước/sau, tách staging khớp/không khớp như cũ, rào cứng (index chỉ-đọc, CPU-only).
