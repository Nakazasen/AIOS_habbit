# Vé RAG-SYNTH-VALIDATION-HOME — Phối hợp cắt-dòng → sửa trong kiểm định tổng hợp, đo lại 50 câu LSU

**Máy thực hiện:** NHÀ h410asrock (thợ OMP).
**Role gợi ý:** DEFAULT (sửa logic lõi có kiểm soát + test + đo lại).
**Nguồn:** báo cáo `docs/phieu-viec/ket-qua/rag-lane-investigate-home.md` §6 + §9.1 (vé `RAG-LANE-INVESTIGATE-HOME`, verdict Muse ĐẠT phần điều tra/sửa runner/đo lại 2026-10-07 ~03:42 +07).

## Bối cảnh (số đã kiểm chứng độc lập bởi Muse)

- Lane FIX1 (hybrid + cầu 8585): 64,5/150, GPA 1,29; gói bằng chứng 50/50 có mảnh (0 rỗng); 69 lượt gọi provider, **0 lỗi mạng**.
- Nhưng chỉ **6/50 câu** qua kiểm định nội dung (`provider_validated` 4 + `provider_validated_after_repair` 2); **42 câu** rớt `provider_validation_failed` về trích cục bộ; 2 câu ABSTAIN fail-closed (giữ nguyên, không thuộc vé này).
- Đếm lỗi theo 69 lượt gọi: `uncited_material_claim` 65, `missing_citations` 55, `claim_budget_exceeded` 31, `unsupported_critical_literal` 24, `missing_required_facet_citation` 2, `language_conformance_failed` 1.

## Gốc đã xác định trong code (đối chiếu `src/aios_habit/rag_v2/synthesis.py` tại HEAD `c54f42c`)

- Nhánh cắt-dòng (surgical, tối đa 4 lượt, ~dòng 822) chỉ chạy khi **toàn bộ** lỗi ⊆ `_LINE_DROPPABLE_PROVIDER_VALIDATION_ERRORS`.
- Nhánh sửa (repair, `provider_validation_is_repairable`, ~dòng 352) chỉ chạy khi lỗi ⊆ `_REPAIRABLE_PROVIDER_VALIDATION_ERRORS`; `provider_answer_unsupported_critical_literal` **không** nằm trong tập sửa được — đây là hard stop CÓ CHỦ Ý (comment ~dòng 115: sửa literal dễ sinh bịa nguồn).
- Hệ quả: câu vướng lỗi **phối hợp** (vd Q0699: `missing_citations` + `claim_budget_exceeded` + `uncited_material_claim` + `unsupported_critical_literal`) không đủ điều kiện cho cả hai nhánh → rớt thẳng fallback, dù từng phần đều xử lý được.

## Việc phải làm

1. **Luồng phối hợp:** khi tập lỗi ⊆ (cắt-được ∪ sửa-được) và có ít nhất 1 lỗi cắt-được: chạy cắt-dòng trước (giữ nguyên cơ chế + giới hạn 4 lượt hiện tại), kiểm định lại; nếu phần lỗi còn lại ⊆ sửa-được → chạy tiếp 1 lượt sửa như hiện tại; kiểm định lại lần cuối, chỉ nhận khi `valid`.
2. **Rào cứng — KHÔNG nới chuẩn kiểm định:**
   - Không đưa `unsupported_critical_literal` hay nguồn lạ (`unknown_citation`) vào tập "sửa được": dòng chứa literal không có căn cứ phải bị **cắt bỏ**, tuyệt đối không nhờ provider "sửa cho có căn cứ".
   - Không tắt/bỏ bất kỳ lỗi kiểm định nào, không hạ ngưỡng, không đổi rubric. Mọi câu nhận kết quả cloud vẫn phải qua **full validation** như hiện tại.
   - Hành vi fail-closed giữ nguyên: hết đường xử lý → fallback/ABSTAIN như cũ.
3. **Test (bắt buộc, trong repo):**
   - Test mới: (a) ứng viên vướng lỗi phối hợp cắt-được + sửa-được → qua được nhờ cắt-dòng rồi sửa; (b) ứng viên chỉ có literal bịa/nguồn lạ mà cắt xong không còn nội dung hợp lệ → vẫn fail-closed về fallback; (c) lỗi thuần sửa-được và thuần cắt-được giữ nguyên hành vi cũ (hồi quy).
   - Chạy cụm test liên quan synthesis/rag_v2 + cổng repo (compileall, `cli audit`, import app). Ghi rõ số pass/fail; fail ngoài phạm vi thì phân loại, không giấu.
   - Tương thích Python 3.11 (máy nhà/PC0575), không syntax 3.12+.
4. **Đo lại trọn 50 câu** bằng đúng điều kiện lượt FIX1 (runner `do_rag_50_fix1.py` ngoài Git: hybrid retrieval + provider `openai_compatible_local` qua cầu `127.0.0.1:8585`, CPU-only, index chỉ-đọc + SHA-256/md5 trước/sau, checkpoint từng câu, cùng rubric/bộ câu). Đối chiếu 3 cột: lượt này / FIX1 (GPA 1,29, validated 6/50) / C-Agent (2,16). Mục tiêu: số câu `provider_validated` + `provider_validated_after_repair` tăng rõ rệt so với 6/50 và GPA tăng; nếu không tăng, báo cáo trung thực kèm đếm lỗi mới — không nới chuẩn để đạt số.
5. Không ghi index. Không merge `main`. Mọi commit trên `phieu-viec/rag-fix1`, commit code riêng, commit báo cáo riêng.

## Nhịp heartbeat (BẮT BUỘC)

Mỗi **15 phút** append mốc `` `ghi_chu` `` vào `trang-thai.md` mailbox này. Cấm im lặng quá 15 phút. Vé dài: checkpoint/resume được (runner đã có checkpoint từng câu).

## Báo cáo

`docs/phieu-viec/ket-qua/rag-synth-validation-home.md` — thay đổi code (trước/sau, đúng file/dòng), test mới + hồi quy, bảng đo lại 50 câu (điểm + chế độ từng câu), đếm lỗi kiểm định trước/sau, tách staging khớp/không khớp như cũ, rào cứng (index chỉ-đọc, CPU-only).
