# Thiết kế "bộ sinh câu hỏi vàng" cho pilot làm giàu tri thức

> Tài liệu thiết kế (chưa phải code cuối). Theo quy tắc repo: plan trước – code sau.
> Phạm vi: phục vụ pilot làm giàu tri thức 5 hiện tượng F CALL thật — AIOS sinh câu hỏi vàng → trả lời theo lô (Copilot 365 đóng vai chuyên gia trước, chuyên gia thật phản hồi sau) → nhập vào staging → đo chất lượng trước/sau.
> Nhãn duy nhất trên tri thức nhập: **"kiến thức đã được đào tạo bổ sung"**. Không lưu nguồn LLM dưới bất kỳ hình thức nào.

## 1. Cái đã có trong code hiện tại (tóm tắt)

Đọc kỹ 6 file chính + `knowledge_claim_extractor.py`, `controlled_knowledge_artifact.py`, `error_cases/investigation_tree.py` và các test liên quan. Kết quả:

### 1.1. `knowledge_coverage.py` — phát hiện khoảng trống

- `KnowledgeGapCandidate`: dataclass frozen, có `gap_id`, `collection_id`, `scope`, `title`, `description`, `gap_type`, `evidence_refs` (bắt buộc ≥ 1), `status`, `priority` (high/medium/low), `digest` SHA-256. Gap loại `conflict` bắt buộc ≥ 2 evidence.
- 6 loại gap: `missing_threshold`, `missing_condition`, `missing_exception`, `missing_example`, `conflict`, `stale_knowledge`.
- `generate_deterministic_gap_signals`: sinh gap từ receipt (thiếu nguồn, metadata cũ, điểm phủ < 0.7, mâu thuẫn). Không cần AI vẫn chạy được.
- `evaluate_coverage`: chạy bộ câu hỏi kiểm tra trên kho, trả về `CoverageMetric` (`coverage_ratio`, `gaps_count`) + danh sách gap. **Tái dùng trực tiếp cho bộ đo trước/sau.**
- `rank_and_cluster_gaps`: xếp theo priority → scope → gap_id. Chưa có chấm điểm theo giá trị thông tin.
- `CAgentGatewayClient.explain_and_rank_gaps`: C-AGENT giải thích + xếp hạng gap qua Brain Gateway, chống bịa citation (chỉ nhận `snippet_id` có thật), fail-closed khi offline, chặn cứng `local_only` ra kênh ngoài.
- Test: `tests/test_knowledge_coverage.py` (15 test: chống gap bịa, 2 nguồn cho conflict, fallback offline, local_only...).

### 1.2. `adaptive_interview_engine.py` — sinh câu hỏi nền + guardrail

- `generate_seed_questions(gap)`: sinh câu hỏi nền theo loại gap. Thực tế chỉ phủ 4 nhánh: `missing_threshold` → 3 câu (ngưỡng, đơn vị/dung sai, ngoại lệ); `conflict` → 2 câu (thực tế xưởng theo chuẩn nào, căn cứ phân định); `missing_condition` → 2 câu (điều kiện tiên quyết, tiêu chí nghiệm thu); còn lại → 2 câu chung chung (thao tác, dấu hiệu bất thường). **Đây mới là khung "điều kiện → ngưỡng → ngoại lệ → xử lý", chưa phải câu hỏi vàng.**
- Guardrail có sẵn và dùng tốt: `detect_leading_question` (9 mẫu regex câu hỏi dẫn dắt), `detect_semantic_duplicate` (Jaccard ≥ 0.85), `validate_candidate_question` (chống trống/dẫn dắt/trùng/vượt budget).
- `propose_next_action`: máy trạng thái thích ứng — hết budget → complete; "không rõ" lặp → escalate; C-AGENT (nếu có) → fallback deterministic (mâu thuẫn → hỏi làm rõ; thiếu số + gap ngưỡng → đòi số; thiếu ngoại lệ → hỏi ngoại lệ; đủ → xin xác nhận).
- Test: `tests/test_adaptive_expert_interview.py` (seed theo loại gap, guardrail dẫn dắt/trùng lặp...).

### 1.3. `expert_interview_models.py` + `repository.py` + `service.py` — vòng đời phỏng vấn

- Model: `SeedQuestion`, `InterviewBudget` (max_turns/max_minutes/token), `CompletionRubric` (required_aspects, min_grounded_claims, stop_on_repeated_unknowns, escalation_owner), `InterviewPlan`/`Session`/`Turn`/`Checkpoint` (đều có digest chống sửa), `NextActionDecision`.
- `ExpertInterviewService`: chỉ lập plan cho gap đã `accepted`; `submit_interview_turn` xử lý lệnh pause/stop, phân loại `answer_state` (answered/uncertain/unknown/skipped/corrected), tính next action, checkpoint append-only; `create_draft_from_session` dựng bản nháp từ các turn đã trả lời; `submit_artifact_approval` gắn quyết định vào đúng digest bản đã duyệt + bắt buộc khai máy/độ tự tin/nguồn đã kiểm tra/xác nhận trách nhiệm.
- `ExpertInterviewRepository`: SQLite, idempotency key mọi ghi, transcript thô cách ly ở `local_only`.
- `knowledge_claim_extractor.extract_claim_from_turn`: trích claim nguyên tử từ turn, **bắt buộc provenance** (turn ID...), chặn token số/đơn vị chưa xác nhận, claim mâu thuẫn giữ trạng thái `conflicted` + escalate (không tự chọn bên thắng).
- `chat_action_expert_interview.py`: action chat **chỉ đọc** — preview plan/session/câu hỏi tiếp theo, không tạo mới.

### 1.4. `error_cases/investigation_tree.py` — khung 4M/Why-Why có sẵn

- `TEMPLATES_4M`: 16 cặp (câu hỏi xác nhận, dữ liệu/hiện vật cần thu thập) cho 4 nhánh Man/Machine/Material/Method. **Tái dùng làm nguyên liệu sinh câu hỏi**, nhưng hiện là câu hỏi chung chung, chưa gắn vào hiện tượng cụ thể.
- `build_why_chain`: khung 5-Why, đáp án để trống cho chuyên gia điền. **Tái dùng làm khung đào sâu Why.**

### 1.5. Cái còn thiếu (đúng như yêu cầu)

1. Không có chấm điểm câu hỏi theo giá trị thông tin (phân biệt giả thuyết, lấp gap quan trọng, bằng chứng đo được).
2. Không có batch export chuẩn để trả lời theo lô.
3. Không có form trả lời chuẩn nhân quả (4M/Why-Why/cơ chế/bằng chứng xác nhận-bác bỏ).
4. Không có importer vào staging (dedup, gắn nhãn, map sang claim).
5. Không có bộ đo chất lượng trước/sau khi nhập tri thức.

## 2. Luồng tổng thể đề xuất

```
Ca lỗi F CALL thật (DB lỗi)
  → Gom cụm 5 hiện tượng pilot + trích giả thuyết nguyên nhân đã ghi
  → generate_deterministic_gap_signals / evaluate_coverage → gap (6 loại, có evidence)
  → [MỚI] golden_question_generator: sinh ứng viên câu hỏi
        (seed hiện có + TEMPLATES_4M gắn hiện tượng + khung Why + template nhân quả mới)
  → [MỚI] golden_question_scorer: chấm điểm 6 tiêu chí + chọn top-K (greedy phủ khía cạnh)
  → [MỚI] golden_question_export: batch JSONL + Markdown (+ manifest digest)
  → Người trả lời theo lô (Copilot 365 trước, chuyên gia thật phản hồi sau)
  → [MỚI] golden_answer_importer: validate → dedup → gắn nhãn
        "kiến thức đã được đào tạo bổ sung" → map sang KnowledgeClaim (candidate)
        → staging_enrichment.sqlite (tách khỏi index production)
  → [MỚI] golden_question_quality: đo trước/sau (coverage, retrieval, form, phân biệt giả thuyết, độ lệch chuyên gia)
  → Chuyên gia phản hồi → reviewer_status = "chuyen_gia_da_phan_hoi" → vé duyệt merge riêng
```

## 3. Thiết kế chi tiết

### 3.1. Schema form hỏi/đáp chuẩn nhân quả

Hai dataclass mới (đề xuất file `src/aios_habit/golden_question_schema.py`).

**`GoldenQuestion`** — một câu hỏi vàng trong batch:

| Field | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `question_id` | str | Có | `GQ-<batch_id>-<n>` |
| `text` | str | Có | Tiếng Việt, không dẫn dắt (đã qua guardrail) |
| `target_gap_id` | str | Có | Nối về `KnowledgeGapCandidate.gap_id` |
| `target_case_ids` | list[str] | Có | ≥ 1 ca lỗi thật trong DB |
| `loai_cau_hoi` | str | Có | Thuộc bộ từ vựng khép kín bên dưới |
| `muc_tieu` | str | Có | Khía cạnh cần lấp, vd "ngưỡng điện áp cho phép của cảm biến" |
| `gia_thuyet_lien_quan` | list[str] | Không | ID các giả thuyết nguyên nhân mà câu này nhắm tới |
| `expected_evidence` | list[str] | Có | Loại bằng chứng kỳ vọng, vd `["numerical_threshold", "unit"]` |
| `diem` | float | Có | Điểm 0–100 do scorer chấm |
| `diem_thanh_phan` | dict | Có | 6 điểm thành phần để truy vết vì sao câu này được chọn |

Bộ từ vựng `loai_cau_hoi` (khép kín, không tự bịa thêm khi chạy pilot):
`phenomenon` (hiện tượng chính xác), `timeline` (thời điểm/điều kiện xuất hiện),
`before_after` (trước–sau thay đổi), `m4_man`, `m4_machine`, `m4_material`, `m4_method`,
`causal_mechanism` (cơ chế gây lỗi), `evidence_confirm` (bằng chứng xác nhận),
`evidence_refute` (bằng chứng bác bỏ), `discriminator` (phân biệt các giả thuyết),
`exception` (ngoại lệ), `temp_countermeasure` (đối sách tạm thời),
`perm_countermeasure` (đối sách lâu dài), `recurrence` (điều kiện tái phát),
`related_case` (ca/tài liệu liên quan).

**`GoldenAnswer`** — phiếu trả lời chuẩn nhân quả (người trả lời theo lô điền):

| Nhóm | Field | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| Định danh | `answer_id` | str | Có | `GA-<question_id>-<n>` |
| | `question_id` | str | Có | |
| | `gap_id` | str | Có | |
| | `case_ids` | list[str] | Có | ≥ 1 |
| Bối cảnh ca | `error_code` | str | Có | Mã thật; nhóm không có mã thì `"UNKNOWN"` + phân loại H (theo QĐ1 B0-MEASURE) |
| | `error_group` | str | Có | Mặc định `"F CALL"` cho pilot này |
| | `phenomenon` | str | Có | Hiện tượng, copy nguyên văn cột I nếu có |
| | `model_line_station` | str | Không | Model/line/công đoạn |
| | `occurrence_time` | str | Không | ISO, nếu biết |
| Nội dung | `answer_text` | str | Có | ≥ 20 ký tự |
| | `answer_state` | str | Có | Tái dùng: `answered`/`uncertain`/`unknown` (không dùng `skipped` ở batch) |
| Nhân quả | `hypotheses` | list[str] | Có khi `answered` | Các giả thuyết nguyên nhân |
| | `causal_mechanism` | str | Có khi `answered` | Cơ chế gây lỗi: A → B → C |
| | `m4_branches` | list[str] | Có khi `answered` | ≥ 1 trong `Man`/`Machine`/`Material`/`Method` |
| Bằng chứng | `evidence_to_collect` | list[str] | Có khi `answered` | Bằng chứng cần thu thập để kiểm chứng |
| | `confirm_criteria` | str | Có khi `answered` | Tiêu chí xác nhận giả thuyết |
| | `refute_criteria` | str | Khuyến nghị | Tiêu chí bác bỏ giả thuyết |
| | `discriminate_notes` | str | Có nếu câu loại `discriminator` | Cách phân biệt với giả thuyết khác |
| Định lượng | `thresholds` | list[dict] | Không | `{name, value, unit, tolerance}` |
| | `exceptions` | list[str] | Không | Ngoại lệ đã biết |
| Đối sách | `temp_countermeasure` | str | Không | Cho phép `"chua_xac_dinh"` |
| | `perm_countermeasure` | str | Không | Cho phép `"chua_xac_dinh"` |
| | `recurrence_condition` | str | Khuyến nghị | Điều kiện tái phát |
| Liên kết | `related_cases` | list[str] | Không | Mã ca liên quan |
| | `related_docs` | list[str] | Không | Tài liệu/SOP liên quan |
| Phản hồi CG | `needs_expert_review` | list[str] | Có nếu `answer_state != answered` hoặc `confidence < 0.7` | Liệt kê field cần chuyên gia phản hồi |
| | `confidence` | float | Có | 0.0–1.0 |
| | `reviewer_status` | str | Có | `cho_chuyen_gia_phan_hoi` (mặc định) / `chuyen_gia_da_phan_hoi`. **Đây là trạng thái nghiệp vụ, không phải nguồn LLM.** |
| Nhãn | `enrichment_label` | str | Hệ thống tự gắn | Hằng `"kiến thức đã được đào tạo bổ sung"`, người điền không sửa |

Quy tắc validate (viết mới, đặt trong schema module):
- `answer_state == "answered"` mà thiếu `hypotheses`/`causal_mechanism`/`m4_branches`/`evidence_to_collect`/`confirm_criteria` → từ chối, yêu cầu điền hoặc chuyển `answer_state` sang `uncertain`/`unknown` + ghi `needs_expert_review`.
- `confidence` ngoài [0.0, 1.0] → từ chối.
- Không có bất kỳ field nào ghi nguồn LLM (không `answered_by`, không `model_name`, không `provenance`).

### 3.2. Thuật toán sinh + chấm điểm câu hỏi vàng

Đề xuất 3 module mới: `golden_question_generator.py`, `golden_question_scorer.py` (có thể gộp 2 file nếu nhỏ, nhưng tách scorer để test độc lập).

**Bước 1 — sinh ứng viên** (không dùng LLM ở bước này, deterministic):

1. Seed hiện có: `generate_seed_questions(gap)` — tái dùng nguyên.
2. 4M gắn hiện tượng: với mỗi nhánh trong `TEMPLATES_4M` (tái dùng), bind `{hien_tuong}` vào câu hỏi, vd: `"Thông số vận hành tại thời điểm '{hien_tuong}' (tốc độ, nhiệt độ, áp suất...) có bất thường không?"`. Mỗi cặp template sinh 1 câu loại `m4_<nhanh>`, `expected_evidence` lấy từ cột "dữ liệu cần thu thập" của template.
3. Khung Why: `build_why_chain(hien_tuong)` (tái dùng) — mỗi `WhyNode` sinh 1 câu `"Vì sao <đáp án why trước>? Bằng chứng đo được là gì?"`, loại `causal_mechanism`, đi sâu dần theo level.
4. Template nhân quả mới (viết mới, ~10 mẫu, gắn hiện tượng + giả thuyết):
   - `discriminator`: `"Giữa các giả thuyết {H1} và {H2}, dấu hiệu đo được nào phân biệt được hai khả năng này?"`
   - `evidence_confirm`: `"Bằng chứng đo được nào (số đo/log/ảnh) sẽ XÁC NHẬN giả thuyết {H}?"`
   - `evidence_refute`: `"Kết quả đo nào sẽ BÁC BỎ giả thuyết {H}?"`
   - `before_after`: `"Trước và sau thời điểm phát sinh, {thong_so} thay đổi thế nào (giá trị cụ thể)?"`
   - `timeline`: `"'{hien_tuong}' xuất hiện ở thời điểm/điều kiện nào: khởi động, đang chạy, đổi lot, đổi ca?"`
   - `recurrence`: `"Điều kiện nào thì '{hien_tuong}' tái phát 100%? Điều kiện nào thì không?"`
   - `exception`: `"Trường hợp nào '{hien_tuong}' KHÔNG xảy ra dù điều kiện tương tự?"`
   - `temp_countermeasure` / `perm_countermeasure`: `"Đối sách tạm thời/lâu dài cho '{hien_tuong}' là gì? Ai làm, khi nào xong?"`
   - `related_case`: `"Ca lỗi nào trước đây giống '{hien_tuong}' nhất? Kết luận điều tra khi đó là gì?"`
   - `phenomenon`: `"Mô tả chính xác '{hien_tuong}': mã hiển thị, tiếng kêu, mùi, vị trí, tần suất?"`
   Tập giả thuyết `{H}` lấy từ: nguyên nhân đã ghi trong ca lỗi + các claim `conflicted` cùng scope (nếu có).

**Bước 2 — chấm điểm.** Mỗi câu `q` được 6 điểm thành phần trong [0, 1], tổng:

```
diem(q) = 100 * (0.30*D + 0.20*G + 0.20*E + 0.15*W + 0.10*N + 0.05*F)
```

| Ký hiệu | Tiêu chí | Trọng số | Cách tính (deterministic) |
|---|---|---|---|
| D | Phân biệt giả thuyết | 0.30 | Số cặp giả thuyết mà câu này phân biệt được / tổng số cặp. Template `discriminator` khai báo `discriminant_pairs`; các loại khác D = 0 trừ khi `gia_thuyet_lien_quan` ≥ 2 (D = 0.3). |
| G | Lấp gap quan trọng | 0.20 | `w_priority(gap)` × (số khía cạnh required_aspects mà q nhắm và chưa ai phủ / tổng khía cạnh). `w_priority`: high = 1.0, medium = 0.6, low = 0.3. |
| E | Bằng chứng đo được | 0.20 | 1.0 nếu `expected_evidence` chứa loại đo được (`numerical_threshold`, `unit`, `log`, `photo`, `trend`) và câu hỏi đòi giá trị cụ thể; 0.5 nếu chỉ đòi mô tả; 0 nếu không. |
| W | Đào sâu Why-Why/4M | 0.15 | 1.0 nếu q thuộc nhánh 4M chưa có câu nào trong batch, hoặc đi tiếp level Why sâu hơn; 0.5 nếu cùng nhánh nhưng khía cạnh khác; 0 nếu trùng. |
| N | Tính mới | 0.10 | 1 − max Jaccard(q, batch hiện tại ∪ câu hỏi lịch sử). Jaccard ≥ 0.85 → **loại luôn** (tái dùng `detect_semantic_duplicate`). |
| F | Khả thi trả lời theo lô | 0.05 | 1.0 mặc định; −0.5 nếu chứa từ khóa "phá hủy", "tháo máy chạy thử", "dừng line"; câu hỏi dẫn dắt → **loại luôn** (tái dùng `detect_leading_question`). |

Trọng số đề xuất trên ưu tiên đúng thứ user chốt: phân biệt nguyên nhân (0.30) cao nhất, sau đó là lấp gap quan trọng + bằng chứng đo được (0.20 mỗi cái). Có thể hiệu chỉnh sau vòng pilot đầu bằng M5 (độ lệch chuyên gia).

**Bước 3 — chọn top-K** (greedy phủ khía cạnh, ngân sách batch):

- Ngân sách đề xuất pilot: **3 câu/hiện tượng × 5 hiện tượng = 15 câu/batch**.
- Sắp xếp ứng viên theo điểm giảm dần, duyệt và chọn câu nếu nó phủ thêm (loại_cau_hoi, nhánh 4M, khía cạnh) chưa có; bỏ qua nếu điểm < 55.
- Ràng buộc cứng mỗi hiện tượng: ≥ 1 câu `discriminator` (D > 0), ≥ 1 câu E = 1.0 (bằng chứng đo được), phủ ≥ 3 nhánh 4M. Nếu top-K thiếu, ép thêm câu D/E điểm cao nhất chưa được chọn.
- `validate_candidate_question` (tái dùng) chạy cuối: chống vượt budget batch.

### 3.3. Định dạng batch export

Module mới `golden_question_export.py`. Mỗi batch gồm 3 file:

1. `batch_<id>_questions.jsonl` — mỗi dòng 1 JSON:
```json
{"batch_id": "KB-20261002-FCALL-01", "batch_version": 1,
 "question": {"question_id": "GQ-KB-20261002-FCALL-01-03", "text": "...", "target_gap_id": "GAP-...", "target_case_ids": ["2023/183"], "loai_cau_hoi": "discriminator", "muc_tieu": "...", "gia_thuyet_lien_quan": ["H1", "H2"], "expected_evidence": ["measurement", "log"], "diem": 82.5, "diem_thanh_phan": {"D": 1.0, "G": 0.8, "E": 1.0, "W": 0.5, "N": 0.9, "F": 1.0}},
 "case_context": {"error_code": "F000", "error_group": "F CALL", "phenomenon": "...", "model_line_station": "..."},
 "gap_context": {"gap_id": "GAP-...", "gap_type": "missing_condition", "title": "...", "priority": "high"},
 "hypotheses": [{"hypothesis_id": "H1", "text": "..."}, {"hypothesis_id": "H2", "text": "..."}],
 "answer_form_schema": {"type": "object", "required": ["answer_text", "answer_state", ...], "note": "xem mục 3.1"}}
```
2. `batch_<id>_phieu_hoi.md` — phiếu đọc được cho người: mỗi hiện tượng 1 section (mã lỗi, hiện tượng, 5W tóm tắt từ ca), mỗi câu 1 block gồm: câu hỏi, mục tiêu, loại, bằng chứng kỳ vọng, và **form trống** theo đúng field `GoldenAnswer` để điền (Markdown checklist). Dùng khi đưa vào Copilot 365 / gửi chuyên gia.
3. `batch_<id>_manifest.json` — `batch_id`, `version`, `created_at`, danh sách `question_id`, `sha256` từng file, `sha256` toàn batch. Importer kiểm tra manifest trước khi nhập.

Không file nào chứa provenance LLM.

### 3.4. Importer vào staging

Module mới `golden_answer_importer.py`. Đầu vào: `batch_<id>_answers.jsonl` (người trả lời điền theo form, 1 dòng/đáp án) + manifest.

1. **Kiểm toàn vẹn**: đối chiếu digest manifest; lệch → dừng, báo.
2. **Validate schema**: từng đáp án qua validator của `GoldenAnswer` (mục 3.1). Không đạt → ghi `import_errors.jsonl`, không nhập nửa chừng đáp án đó.
3. **Chống trùng**: `key = sha256(question_id + "|" + chuan_hoa(answer_text))`; key đã có trong staging → skip + log `duplicate_skip`. Cùng `question_id` nhưng text khác → cho qua, đánh dấu `supersedes` nếu người điền ghi đè đáp án cũ.
4. **Gắn nhãn**: `enrichment_label = "kiến thức đã được đào tạo bổ sung"` (hệ thống tự gắn); `reviewer_status` mặc định `"cho_chuyen_gia_phan_hoi"`. Không tạo, không đọc, không lưu bất kỳ field nguồn LLM nào.
5. **Map sang claim**: đáp án `answered` → `extract_claim_from_turn` (tái dùng, `require_confirmed_tokens=True` để số/đơn vị phải xác nhận) → `KnowledgeClaim` status `candidate`, `source_refs = (answer_id, question_id, *case_ids)`. Claim mâu thuẫn với kho hiện có → giữ `conflicted` + escalate theo luật hiện hành (không tự chọn bên thắng).
6. **Lưu staging**: SQLite riêng `local_cases/staging_enrichment.sqlite` (đề xuất), bảng `staging_answers` + `staging_claims`. **Tách khỏi index production** — cấm merge trực tiếp.
7. **Chuyên gia phản hồi**: chuyên gia sửa/bổ sung → cập nhật đáp án (version + 1, giữ bản cũ), `reviewer_status = "chuyen_gia_da_phan_hoi"`, ghi `DecisionRecord` gắn đúng digest bản đã duyệt (tái dùng pattern `submit_artifact_approval`: máy, độ tự tin, nguồn đã kiểm tra, xác nhận trách nhiệm). Merge vào kho thật là vé riêng, sau khi đủ 5 hiện tượng đều `chuyen_gia_da_phan_hoi`.

### 3.5. Bộ đo chất lượng trước/sau

Module mới `golden_question_quality.py`. Chạy 2 lượt trên cùng bộ chuẩn, snapshot SHA index trước khi đo.

| Metric | Đo gì | Cách đo | Ngưỡng đạt đề xuất (pilot) |
|---|---|---|---|
| M1 phủ tri thức | Gap còn lại | `evaluate_coverage` (tái dùng) với bộ câu hỏi chuẩn/gap trước và sau khi nhập staging → `coverage_ratio`, `gaps_count`, số gap `high` còn lại | gap `high` giảm ≥ 60% |
| M2 truy hồi | Chunk mới có vào top-5 không | Với mỗi hiện tượng, hỏi RAG câu chuẩn ("hiện tượng X: nguyên nhân, cơ chế, đối sách?") trước/sau → `top5_has_new_chunk` (0/1), `citation_precision@5` | hit ≥ 4/5 hiện tượng |
| M3 đầy form | Chất lượng phiếu trả lời | % field bắt buộc điền được; % đáp án có `evidence_to_collect` đo được; % có đủ `causal_mechanism` + `m4_branches` | ≥ 80% |
| M4 phân biệt giả thuyết | Giá trị câu hỏi vàng | Số cặp giả thuyết được đáp án phân biệt (checklist 0/1 từng cặp theo rubric, chấm tay hoặc C-AGENT hỗ trợ) | ≥ 70% cặp được phân biệt |
| M5 độ lệch chuyên gia | Batch đầu lệch bao nhiêu | Sau khi chuyên gia phản hồi: % nội dung bị sửa/bác (`chuyen_gia_da_phan_hoi` vs bản batch đầu) | < 30%; nếu cao → hiệu chỉnh trọng số scorer cho vòng 2 |

Báo cáo: `bao_cao_chat_luong_<batch_id>.md` — bảng trước/sau từng metric, delta, kết luận đạt/chưa đạt, đề xuất hiệu chỉnh.

## 4. Tái dùng được vs viết mới

**Tái dùng nguyên (không viết lại):**
- `KnowledgeGapCandidate`, `generate_deterministic_gap_signals`, `evaluate_coverage`, `rank_and_cluster_gaps` (`knowledge_coverage.py`) — phát hiện gap + đo M1.
- `generate_seed_questions`, `detect_leading_question`, `detect_semantic_duplicate`, `validate_candidate_question` (`adaptive_interview_engine.py`) — sinh seed + guardrail.
- `TEMPLATES_4M`, `BRANCH_LABELS_VI`, `build_why_chain` (`error_cases/investigation_tree.py`) — nguyên liệu 4M/Why-Why.
- `answer_state` (`answered`/`uncertain`/`unknown`), `extract_claim_from_turn`, vòng đời `KnowledgeClaim` — map đáp án sang claim, xử lý conflict.
- Pattern `DecisionRecord` + digest binding của `submit_artifact_approval` — chuyên gia phản hồi có trách nhiệm.
- `ExpertInterviewRepository` — mở thêm bảng staging (không sửa bảng hiện có).

**Viết mới:**
- `src/aios_habit/golden_question_schema.py` — `GoldenQuestion`, `GoldenAnswer`, validator (tương thích Python 3.11).
- `src/aios_habit/golden_question_generator.py` — sinh ứng viên (seed + 4M bind hiện tượng + Why + 10 template nhân quả).
- `src/aios_habit/golden_question_scorer.py` — 6 tiêu chí + trọng số + greedy chọn top-K + ràng buộc phủ.
- `src/aios_habit/golden_question_export.py` — JSONL + Markdown + manifest digest.
- `src/aios_habit/golden_answer_importer.py` — validate/dedup/gắn nhãn/map claim/staging SQLite.
- `src/aios_habit/golden_question_quality.py` — harness đo M1–M5 + báo cáo.
- `tests/test_golden_question.py` — test scorer (thứ tự điểm), guardrail (loại câu dẫn dắt/trùng), importer (dedup, nhãn đúng, không field nguồn LLM), quality (M1/M2 trên fake adapter).

**Ràng buộc kỹ thuật:** code tương thích Python 3.11 (không f-string nhiều dòng trong biểu thức — PEP 701, không `type` statement); giữ `from __future__ import annotations` + dataclass frozen như code hiện có; UI/doc tiếng Việt.

## 5. Ví dụ cụ thể — 1 hiện tượng F CALL mẫu

> Ví dụ minh họa cấu trúc. Số liệu thật (mã ca, hiện tượng nguyên văn, nguyên nhân đã ghi) lấy từ DB lỗi khi chạy pilot, không dùng số liệu dưới đây làm dữ liệu thật.

**Hiện tượng:** mã `F000` (nhóm `F CALL` — lỗi hệ thống, theo bảng mã UWCA), hiện tượng: "Khi khởi động, màn hình LCD hiển thị F000, máy dừng không vào chế độ vận hành". Giả thuyết từ ca: H1 — lỗi bo mạch điều khiển; H2 — sụt áp nguồn cấp lúc khởi động.

**Gap phát hiện:** `missing_condition` (thiếu điều kiện tiên quyết kiểm tra nguồn trước khi kết luận bo mạch lỗi, priority high) + `missing_threshold` (thiếu ngưỡng điện áp cho phép lúc khởi động, priority medium).

**3 câu hỏi vàng được chọn (mỗi câu kèm điểm thành phần):**

1. `[discriminator, 87.5]` "Giữa hai giả thuyết 'lỗi bo mạch điều khiển' (H1) và 'sụt áp nguồn cấp lúc khởi động' (H2), dấu hiệu đo được nào phân biệt được hai khả năng này? (D=1.0, G=0.8, E=1.0, W=0.5, N=0.9, F=1.0)"
   - Mục tiêu: buộc người trả lời đưa ra phép thử phân biệt, không trả lời chung chung "kiểm tra cả hai".
2. `[m4_machine, 78.0]` "Điện áp nguồn cấp đo tại đầu vào bo mạch lúc khởi động là bao nhiêu V? Ngưỡng cho phép theo spec là bao nhiêu, dung sai bao nhiêu?" (D=0.3, G=1.0, E=1.0, W=1.0, N=0.8, F=1.0)
   - Mục tiêu: lấp gap `missing_threshold` bằng số đo cụ thể.
3. `[before_after, 71.5]` "Trước khi xuất hiện F000, máy/công đoạn có thay đổi gì (thay linh kiện, đổi lot, chỉnh thông số, mất điện)? Giá trị trước–sau cụ thể?" (D=0.3, G=0.6, E=0.5, W=1.0, N=0.9, F=1.0)
   - Mục tiêu: bắt timeline thay đổi — manh mối nhân quả hay bị bỏ sót nhất.

**Phiếu trả lời mẫu (câu 1, rút gọn):**

```json
{"answer_id": "GA-GQ-KB-20261002-FCALL-01-03-1", "question_id": "GQ-KB-20261002-FCALL-01-03",
 "gap_id": "GAP-...", "case_ids": ["2023/183"], "error_code": "F000", "error_group": "F CALL",
 "phenomenon": "Khi khởi động, màn hình LCD hiển thị F000, máy dừng không vào chế độ vận hành",
 "answer_text": "Đo điện áp tại đầu vào bo mạch lúc khởi động: nếu ≥ 21.6V mà vẫn F000 thì loại H2, giữ H1; nếu < 21.6V thì ưu tiên H2, kiểm tra nguồn trước khi thay bo.",
 "answer_state": "answered",
 "hypotheses": ["H1: lỗi bo mạch điều khiển", "H2: sụt áp nguồn cấp lúc khởi động"],
 "causal_mechanism": "Sụt áp lúc khởi động → bo mạch reset giữa chừng → firmware báo F000 và khóa máy",
 "m4_branches": ["Machine"],
 "evidence_to_collect": ["Số đo điện áp lúc khởi động (đồng hồ/kẹp dòng)", "Log nguồn nếu có"],
 "confirm_criteria": "Đo < 21.6V tại 3 lần khởi động liên tiếp",
 "refute_criteria": "Đo ≥ 21.6V ổn định mà vẫn F000",
 "discriminate_notes": "Ngưỡng 21.6V phân biệt H1/H2: dưới ngưỡng → H2, trên ngưỡng mà lỗi → H1",
 "thresholds": [{"name": "điện áp khởi động tối thiểu", "value": "21.6", "unit": "V", "tolerance": "±5%"}],
 "temp_countermeasure": "Khởi động lại sau khi kiểm tra CB nguồn; ghi lại số đo",
 "perm_countermeasure": "chua_xac_dinh",
 "recurrence_condition": "Tái phát khi nguồn tổng xưởng sụt lúc giờ cao điểm",
 "needs_expert_review": ["perm_countermeasure", "recurrence_condition"],
 "confidence": 0.75, "reviewer_status": "cho_chuyen_gia_phan_hoi",
 "enrichment_label": "kiến thức đã được đào tạo bổ sung"}
```

Đáp án này đạt M3 (đủ mechanism + 4M + bằng chứng đo được + tiêu chí xác nhận/bác bỏ), M4 (phân biệt được cặp H1/H2), và `needs_expert_review` chỉ rõ 2 field chờ chuyên gia thật phản hồi.

## 6. Đề xuất thứ tự triển khai (chưa code)

1. `golden_question_schema.py` + test validator (xong mới làm tiếp — schema là hợp đồng của cả chuỗi).
2. `golden_question_generator.py` + `golden_question_scorer.py` + test (chạy trên 5 hiện tượng thật, OMP/user kiểm tra batch mẫu bằng mắt trước khi trả lời lô).
3. `golden_question_export.py` (JSONL + Markdown + manifest).
4. `golden_answer_importer.py` + staging SQLite (chạy khô trên đáp án mẫu, kiểm tra dedup + nhãn).
5. `golden_question_quality.py` (M1–M5) + báo cáo.
6. Vòng chuyên gia phản hồi → vé merge vào kho thật (vé riêng, ngoài phạm vi thiết kế này).

## 7. Rủi ro và câu hỏi mở

- **Tập giả thuyết H từ đâu?** Hiện lấy từ nguyên nhân đã ghi trong ca lỗi + claim `conflicted` cùng scope. Nếu ca ghi sơ sài, D bị bóp méo. Giảm thiểu: cho phép người chạy pilot bổ sung H thủ công trong `case_context` của batch (ghi rõ nguồn bổ sung).
- **Trọng số scorer** là đề xuất ban đầu; hiệu chỉnh bằng M5 sau vòng pilot 1 (nếu chuyên gia bác nhiều → tăng W/E, giảm D...).
- **Copilot 365 trả lời theo lô bằng cách nào**: mặc định dùng app Copilot trên máy công ty, **chế độ Work IQ + Think deeper** (user chốt 2026-10-02, có ảnh minh họa hai nút trên thanh chat) — copy-paste phiếu Markdown theo lô, mỗi hiện tượng một lượt chat. API/automation chưa xác minh — không hứa tự động hoàn toàn.
- **Không merge staging vào production** trong pilot này; vé merge là việc riêng sau khi đủ `chuyen_gia_da_phan_hoi`.
