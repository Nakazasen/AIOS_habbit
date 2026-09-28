# E1 — Điều tra khâu synthesis làm rớt dữ kiện (đợt 2)

Ngày: 2026-09-28. Người chạy: subagent E1 (VM). Repo: `~/workspace/aios_verify`, branch `phieu-viec/rag-fix1` (head `197f7f5`).
Phạm vi: CHỈ ĐỌC. Không sửa code, không commit.

## Tóm tắt

E1 đợt 1 (2026-09-26, `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`) đã chỉ ra 3 điểm rớt ở đường local.
Đợt này xác nhận cả 3 vẫn còn nguyên trong code hiện tại, và phát hiện thêm **6 điểm rớt mới** —
chủ yếu ở **đường provider** (đợt 1 chưa đụng tới vì router đang `auto:blocked`) và ở tầng dựng evidence pack.
Tất cả điểm mới đều đã repro bằng script (không cần index thật).

---

## A. Điểm rớt đã biết từ E1 đợt 1 — VẪN CÒN

### A1. Budget 5 claim + duyệt pack theo thứ tự
- `src/aios_habit/rag_v2/synthesis.py:760` — `synthesize_evidence(..., max_claims: int = 5)`.
- `src/aios_habit/rag_v2/synthesis.py:636` — `synthesize_with_provider(..., max_claims: int = 5)`.
- `_compose_grounded_claims` (dòng 1403) duyệt `pack.items` theo thứ tự, dừng khi `len(claims) >= max_claims` (dòng 1427, 1565, 1573).
- **Repro:** pack 7 mục (5 summary chung đứng đầu + 2 chunk thân chứa đáp án `11922/12860/12626`) → 5 claim toàn là summary, đáp án thật bị rớt 100%. `ANSWER HAS 11922: False`.

### A2. Summary bị đẩy lên đầu pack với intent `general`
- `src/aios_habit/rag_v2/index.py:2451-2463` (`hybrid_search_with_summary`):
  ```python
  if plan.intent_category in ("cross_source_synthesis", "general"):
      ...
      combined = (
          filtered + tuple(summary_chunks)
          if retrieval_mode == "full"
          else tuple(summary_chunks) + filtered   # <-- summary ĐỨNG TRƯỚC khi không phải full
      )
  ```
- Kết hợp với A1: 5 summary đầu chiếm hết budget trước khi tới chunk thân.

### A3. Chấm điểm fragment chỉ đếm token overlap (mặc định)
- `src/aios_habit/rag_v2/synthesis.py:1071-1091` (`_fragment_score`):
  ```python
  return (typed_value_count, answer_value_count, literal_overlap,
          len(terms & query_terms), -len(fragment))
  ```
- Khi `prioritize_literals=False` (mặc định), 3 thành phần đầu = 0 → chỉ còn đếm token trùng với câu hỏi.
- Hệ quả (đã ghi ở E1 đợt 1, code không đổi): câu mô tả tiếng Việt chung chung thắng câu tiếng Nhật chứa đáp án (`nvarchar(4000)`).

---

## B. Điểm rớt MỚI (đường provider + evidence pack)

### B1. Provider viết đáp án tốt nhưng vượt budget → repair XÓA DỮ KIỆN
- `src/aios_habit/rag_v2/synthesis.py:389` (`validate_provider_synthesis_answer`):
  ```python
  if len(material_lines) > plan.max_claims:
      errors.append("provider_answer_claim_budget_exceeded")
  ```
- Lỗi này thuộc `_REPAIRABLE_PROVIDER_VALIDATION_ERRORS` (dòng 112-122) nên được repair — nhưng contract repair (dòng 311, `format_provider_synthesis_repair_contract`) ghi rõ:
  > "If the draft exceeded the claim budget, **remove factual lines until the contract is satisfied**; do not merge multiple unsupported facts into one sentence."
- **Repro:** provider viết 7 dòng đầy đủ citation, budget=5 → `valid: False`, errors=`('provider_answer_claim_budget_exceeded',)`, `repairable: True` → repair sẽ xóa 2 dòng dữ kiện.
- Nghịch lý: provider NHÌN THẤY toàn bộ evidence (`_format_evidence_context` gửi full snippet, `rag_v2_synthesis_provider.py:37-47`) nhưng validation bắt phải vứt bớt.

### B2. Một dòng lỗi → cả đáp án provider bị vứt
- `src/aios_habit/rag_v2/synthesis.py:400-408`: nếu một dòng chứa "critical literal" (ngày, số, mã) không có trong evidence được cite → `provider_answer_unsupported_critical_literal` — **không thuộc tập repairable** → cả đáp án bị loại → fallback về local (budget 5).
- Tương tự `provider_answer_unknown_citation` (dòng 371): 1 citation lạ → vứt toàn bộ.
- `synthesize_with_provider` (dòng 735-754): validation fail không repairable → `return replace(fallback, ...)` — mọi dòng đúng khác cũng mất theo.

### B3. Facet sections: mỗi facet đúng 1 claim, evidence ngoài facet bị vứt hết
- `src/aios_habit/rag_v2/synthesis.py:1421-1429` (`_compose_grounded_claims`):
  ```python
  for facet_id in facet_sections.values():
      ...
      if candidate is not None:
          ...add(item, facet_id, fragment=fragment)   # 1 claim / facet
      if len(claims) >= max_claims:
          return tuple(claims)
  if facet_sections:
      return tuple(claims)   # <-- có facet sections thì CHỈ trả claim theo facet
  ```
- Áp dụng cho `cross_source_synthesis`, `architecture`, `integration`, `compare_change`.

### B4. Mỗi evidence item chỉ lấy 1 fragment
- `src/aios_habit/rag_v2/synthesis.py:1108-1134` (`_best_fragment`): `max(candidates, key=...)` — chọn đúng 1 fragment điểm cao nhất; các fragment khác trong cùng chunk bị bỏ.
- `_combine_answer_value_fragments` (dòng 1137) gộp nhiều fragment nhưng **chỉ khi `prioritize_body_evidence=True`** (opt-in, mặc định False).

### B5. Evidence pack giới hạn 5 chunk / document
- `src/aios_habit/rag_v2/evidence.py:88` — `EvidencePackConfig.per_document_limit: int = 5`.
- Document có nhiều chunk liên quan → chunk thứ 6+ không vào pack, synthesis không bao giờ thấy.

### B6. Default `max_claims` không nhất quán
- `synthesize_evidence`: 5 · `synthesize_with_provider`: 5 · `build_synthesis_plan`: 8 (dòng 219).
- Thực tế provider luôn nhận budget 5 (do `synthesize_with_provider` truyền xuống), nhưng contract mẫu/test dùng 8 — dễ gây nhầm khi đọc code.

---

## C. Đề xuất fix cho E2 (chưa thực hiện)

1. **Chọn claim theo giá trị, không theo thứ tự pack.** Trong `_compose_grounded_claims`: chấm điểm mọi ứng viên claim (ưu tiên literal/mã/số trùng câu hỏi) rồi lấy top-N theo budget, thay vì lấy 5 mục đầu tiên. Hoặc: dành quota riêng — tối đa 2 summary, còn lại cho chunk thân.
2. **Đừng prepend summary cho truy vấn chi tiết.** `index.py:2457-2461`: mở rộng nhánh `retrieval_mode == "full"` (summary đứng sau) cho cả intent lookup/detail; hoặc đánh dấu summary để synthesis hạ ưu tiên.
3. **Bật `prioritize_body_evidence` mặc định** cho các shape lookup/diagnosis, hoặc ít nhất khi câu hỏi chứa identifier/mã/số (`_query_has_exact_values` đã có sẵn, dòng 1001).
4. **Sửa contract repair: nén thay vì xóa.** Đổi câu "remove factual lines" thành "gộp các dữ kiện liên quan vào ít dòng hơn nhưng giữ nguyên mọi giá trị đã cite". Hoặc tăng budget động cho câu hỏi dạng liệt kê.
5. **Validation: loại dòng lỗi, giữ dòng đúng.** Thay vì vứt cả đáp án khi 1 dòng lỗi, lọc bỏ dòng lỗi rồi re-validate phần còn lại.
6. **Facet: cho nhiều claim mỗi facet** trong giới hạn budget, thay vì đúng 1.

## Phụ lục — script repro

Chạy với `PYTHONPATH=src python3` tại repo (không cần index, không ghi đĩa):

- Repro A1: dựng 7 `SearchResult` (5 summary chung + 2 chunk đáp án) → `build_evidence_pack` → `synthesize_evidence` → kiểm tra `"11922" in res.answer` → `False`.
- Repro B1: dựng 7 evidence distinct-doc → `build_synthesis_plan(pack, max_claims=5)` → đáp án provider 7 dòng đủ citation → `validate_provider_synthesis_answer` → `valid=False`, `errors=('provider_answer_claim_budget_exceeded',)`, `repairable=True`.

Test hiện có liên quan: `tests/test_rag_v2_synthesis.py` (35 passed).
