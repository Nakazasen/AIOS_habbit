# Vé RAG-SYNTH-VALIDATION-HOME — Phối hợp cắt-dòng → sửa trong kiểm định tổng hợp + đo lại 50 câu

- Vé: `RAG-SYNTH-VALIDATION-HOME` (prompt `docs/phieu-viec/mailbox/prompt.md`).
- Máy: nhà `h410asrock`. Phiên 03:51–… +07 ngày 07/10/2026.
- Trạng thái: **XONG** (code + test + đo lại 50 câu; chờ Muse đối chứng).
- Nguồn vé: báo cáo `docs/phieu-viec/ket-qua/rag-lane-investigate-home.md` §6 + §9.1.

## 1. Tóm tắt

- Sửa logic lõi `src/aios_habit/rag_v2/synthesis.py` đúng phạm vi vé: nhánh cắt-dòng nay **phối hợp** với nhánh sửa —
  khi tập lỗi ⊆ (cắt-được ∪ sửa-được) và có ≥1 lỗi cắt-được: cắt-dòng trước (giữ nguyên cơ chế, tối đa 4 lượt),
  kiểm định lại; phần còn lại ⊆ sửa-được → 1 lượt sửa như cũ; chỉ nhận khi `valid`.
- Rào cứng giữ nguyên: `unsupported_critical_literal` + `unknown_citation` **không** vào tập sửa-được (chỉ cắt bỏ —
  không nhờ provider "sửa cho có căn cứ"); không tắt/hạ chuẩn kiểm định nào; hết đường → fallback/ABSTAIN như cũ.
- Test: 3 ca mới (`tests/test_rag_v2_synthesis.py`); ca lỗi phối hợp **FAIL trên code cũ** (rớt fallback, 0 lượt sửa) → PASS trên code mới; cụm synthesis+provider+evidence **96 đạt/4 lỗi** (4 lỗi đã đối chứng y hệt trên code cũ `6ed40ea` bằng cây làm việc tách riêng — nhóm privacy/nhãn, ngoài phạm vi vé).
- Đo lại 50 câu đúng điều kiện FIX1 (runner `do_rag_50_synth.py` ngoài Git: hybrid + `openai_compatible_local` qua cầu `127.0.0.1:8585`, CPU-only, index chỉ-đọc SHA-256 `45eb0e07…b7c0` khớp trước/sau, 0 lỗi kỹ thuật): tổng **61,17/150, GPA 1,22** (FIX1: 64,5/1,29 — giảm 3,33 do 2 câu provider trả nội dung khác giữa 2 lượt); số câu qua kiểm định nội dung **9/50** toàn `provider_validated` (**tăng +3** so với 6/50 FIX1 — đúng mục tiêu vé); không nới chuẩn nào.

## 2. Thay đổi code (trước/sau, đúng file/dòng)

File `src/aios_habit/rag_v2/synthesis.py` — commit `c7af43c`, +29/−3 dòng (không đổi API export):

**(a) Helper mới `_provider_validation_allows_line_surgery` (dòng 368–383, mới thêm):**

```python
def _provider_validation_allows_line_surgery(
    validation: ProviderSynthesisValidation,
) -> bool:
    errors = set(validation.errors)
    if not errors & _LINE_DROPPABLE_PROVIDER_VALIDATION_ERRORS:
        return False
    return errors <= (
        _LINE_DROPPABLE_PROVIDER_VALIDATION_ERRORS | _REPAIRABLE_PROVIDER_VALIDATION_ERRORS
    )
```

**(b) Điều kiện vào nhánh cắt-dòng (dòng 822):**

| | Trước (`c54f42c`) | Sau (`c7af43c`) |
|---|---|---|
| Vào cắt-dòng | `set(validation.errors) <= _LINE_DROPPABLE_…` (chỉ khi **toàn bộ** lỗi cắt-được) | `_provider_validation_allows_line_surgery(validation)` (⊆ hợp và có ≥1 lỗi cắt-được — nhận cả lỗi **phối hợp**) |
| Vòng lặp cắt (dòng 841) | tiếp tục khi phần lỗi còn lại ⊆ cắt-được | tiếp tục khi phần lỗi còn lại vẫn thoả helper (⊆ hợp + còn lỗi cắt-được để cắt tiếp) |
| Giới hạn | 4 lượt (giữ nguyên) | 4 lượt (giữ nguyên) |
| Hard stop literal/nguồn lạ | không vào tập sửa-được | **giữ nguyên** — không vào tập sửa-được |
| Kiểm định cuối | chỉ nhận khi `valid` | **giữ nguyên** — chỉ nhận khi `valid`; sửa xong vẫn phải qua full validation |

Việc dùng lại chính helper ở cả 2 điểm điều kiện làm luồng phối hợp liền mạch: cắt các dòng lỗi trước (không tốn lượt gọi),
khi chỉ còn lỗi trình bày (⊆ sửa-được) thì nhánh sửa hiện có (1 lượt, ~dòng 822–871) tự chạy tiếp; nếu không còn đường → fallback như cũ.

## 3. Test mới + hồi quy

3 test mới trong `tests/test_rag_v2_synthesis.py` (cuối file):

| Test | Kịch bản | Kỳ vọng | Thực tế |
|---|---|---|---|
| `test_combined_droppable_and_repairable_failure_recovers_via_surgery_then_repair` | Lượt 1 trả 3 dòng: 1 dòng nguồn lạ `[99]` + vượt ngân sách claim (`max_claims=1`) | cắt dòng `[99]`, còn lỗi ngân sách → gọi sửa 1 lượt → `provider_validated_after_repair` | **Trên code cũ: FAIL** (`assert 1 == 2` — rớt fallback, không có lượt sửa); **trên code mới: PASS** (2 lượt gọi, lượt 2 `repair_errors=("provider_answer_claim_budget_exceeded",)`) |
| `test_combined_failure_with_only_fabricated_lines_stays_fail_closed` | Lượt 1 chỉ có dòng bịa (`2026-01-01` sai nguồn + `[98]` nguồn lạ) | cắt xong không còn dòng hợp lệ → fallback, **0 lượt sửa** | PASS: `len(calls)==1`, mode `local_…`, không lộ nội dung bịa |
| `test_pure_repairable_and_pure_droppable_keep_previous_routing` | (1) lỗi thuần cắt-được (dòng `[99]`, không lỗi khác) → cắt, không gọi sửa; (2) lỗi thuần sửa-được (vượt ngân sách) → đúng 1 lượt sửa | giữ nguyên hành vi cũ | PASS cả 2 nhánh |

Đối chứng chứng minh fail→pass: chạy test (a) trên `synthesis.py` tại HEAD cũ (stash tạm đúng 1 file, đã khôi phục — `git status` sạch sau đó):
`1 failed` (`assert 1 == 2` — chỉ 1 lượt gọi, kết quả fallback); trên code mới: 3/3 PASS.

Cụm test + cổng repo:

| Hạng mục | Kết quả |
|---|---|
| Cụm synthesis+provider+evidence | 96 đạt / 4 lỗi — **4 lỗi có sẵn trên HEAD** (đã chạy lại đúng 4 test đó trên code cũ: lỗi y hệt; nhóm nhãn privacy, ngoài phạm vi vé) |
| Cụm rộng `tests/test_rag_v2_*.py` | 399 đạt / 7 lỗi — **7 lỗi có sẵn** (đối chứng HEAD khớp cả 7, đều nhóm privacy/nhãn: `test_provider_limitations_contain_accurate_reasons`, 3× `RouterSynthesisProvider` privacy/label, `dev_cli` privacy pass rate, 2× `eval_harness` privacy) |
| Full `pytest -q` (07/10, 901,75s) | **4115 đạt / 22 lỗi / 37 bỏ qua / 19 error** — phân loại trọn ca đỏ, không ca nào do code vé: (a) nhóm RAG 7/7 lỗi y hệt trên code cũ `6ed40ea` (limitations + 3 `RouterSynthesisProvider` + `dev_cli` + 2 `eval_harness`, đều nhãn privacy/pass-rate); (b) 10 lỗi ngoài RAG y hệt cũ (omnibar path-traversal, antigravity handoff, `chunk_evaluation` manifest, `commit_d` uv-lock, expert-e2e, mom-pilot, notebook-qa, phase4-owner, ai_answer xlsx, `missing_db` outcome); (c) 5 lỗi còn lại + 19 error thiếu file môi trường Windows (`\home\hatch\workspace\aios_data\...` — `error_lookup` 10 error, `error_cases_f4` 9 error) hoặc `local_cases` của cây tách; (d) đã `grep` — không test đỏ nào import `rag_v2.synthesis`. 3 test vé vẫn xanh (`-k "combined or pure_repairable"`: 3/3). Đối chứng bằng cây làm việc tách `C:/tmp/wt-old@6ed40ea` + `PYTHONPATH` trỏ đúng `src` cũ, đã xóa sau xong. |
| `compileall src tests` | PASS (exit 0, Python 3.11.14) |
| `cli audit` | PASS (`errors`/`warnings` rỗng) |
| `import aios_habit.workspace_chat_app` | OK |

## 4. Đo lại 50 câu (điều kiện FIX1)

Runner `C:/tmp/lsu-quality-rag-home/do_rag_50_synth.py` (ngoài Git, chỉ khác FIX1 ở tên file/log/checkpoint — so bằng `diff`, logic đo y hệt): hybrid retrieval + provider `openai_compatible_local` qua cầu `127.0.0.1:8585` (`model=gemini-2.5-flash`, `max_attempts=1`), CPU-only (`AIOS_RETRIEVAL_DEVICE=cpu`, backend ghim `CPUExecutionProvider`), index chỉ-đọc `library.sqlite` (SHA-256 `45eb0e07…b7c0`, md5 `23900967…` khớp trước/sau, size 2.942.201.856 byte), checkpoint từng câu (`rows-synth.jsonl`), cùng bộ 50 câu + rubric. Lane chạy 03:59:45→04:12:19 (~12,5 phút), 0 lỗi kỹ thuật, 0 lỗi mạng (66 lượt gọi provider đều có hồi đáp).

| Lượt | Tổng/150 | GPA | Đạt ≥2 | =3 | Qua kiểm định | Chế độ |
|---|---|---|---|---|---|---|
| Fallback lượt đầu | 37,68 | 0,75 | 3 | 3 | 0/50 | not_called 21 + fallback 29 |
| FIX1 | 64,50 | 1,29 | 8 | 5 | 6/50 (validated 4 + after_repair 2) | fallback 42 + validated 4 + after_repair 2 + not_called 2 |
| **SYNTH (lượt này)** | **61,17** | **1,22** | **6** | **4** | **9/50 (validated 9 + after_repair 0)** | **fallback 39 + validated 9 + not_called 2** |
| C-Agent (tham chiếu) | — | 2,16 | — | — | — | — |

Đối chiếu từng câu (fallback → FIX1 → SYNTH), tăng/giảm/nguyên so FIX1 = **0/2/48**:

- **7 câu gain** fallback → `provider_validated` (điểm `tong` giữ nguyên 1,0 nhưng đáp án nay qua full validation thay vì trích cục bộ): Q0849, Q0850, Q0621, Q0632, Q0662, Q0709, Q0924. Trong đó Q0621/Q0662/Q0924 vướng đúng lỗi phối hợp (có `unsupported_critical_literal` kèm lỗi trình bày) — lượt-1 SYNTH trả nội dung khác FIX1 (không còn `missing_citations`) nên vào cắt-dòng 1 lượt rồi `valid` ngay, không tốn lượt sửa.
- **4 câu lost** validation (do provider trả nội dung khác giữa 2 lượt, không phải do code mới làm hỏng): Q0703 (validated 2,33 → fallback 1,0; SYNTH lượt-1 thêm `claim_budget_exceeded`, sửa xong vẫn còn lỗi ngân sách → fallback), Q0685 (validated → fallback; SYNTH lượt-1 thành lỗi phối hợp 4 lỗi, cắt xong vẫn còn lỗi → fallback), Q0671 (after_repair → fallback; cả 2 lượt SYNTH đều `missing_citations`+`uncited` không sửa xong), Q0693 (validated 3,0 → fallback 1,0; SYNTH lượt-1 thêm `claim_budget_exceeded`, sửa còn lỗi ngân sách).
- 2 câu ABSTAIN fail-closed giữ nguyên (Q0824/Q0828, `local_extractive_provider_not_called`, 0 lượt gọi — cổng phủ truy vấn, ngoài phạm vi vé).
- Tách staging (đúng matcher `wire_qa_staging` như FIX1): khớp 38 câu 49,17 GPA 1,294 (đạt ≥2: 6, =3: 4) / không khớp 12 câu 12,0 GPA 1,0 (đạt ≥2: 0) — khớp y hệt FIX1 ở nhóm khớp.

Bảng điểm + chế độ từng câu (stt | id | điểm | trích | tìm(s) | tổng-hợp(s) | bằng-chứng | kết-quả | lượt-gọi | chế độ | limitation):

| # | ID | Điểm | Trích | Chế độ SYNTH | Lượt gọi | FIX1 |
|---|---|---|---|---|---|---|
| 1 | Q0699 | 1,0 | có | fallback | 1 | fallback |
| 2 | Q0700 | 1,0 | có | **validated** | 1 | validated |
| 3 | Q0703 | 1,0 | có | fallback | 2 | validated 2,33 |
| 4 | Q0708 | 1,0 | có | fallback | 1 | fallback |
| 5 | Q0849 | 1,0 | có | **validated** | 1 | fallback |
| 6 | Q0850 | 1,0 | có | **validated** | 1 | fallback |
| 7 | Q0851 | 1,0 | có | fallback | 1 | fallback |
| 8 | Q1029 | 1,5 | có | fallback | 2 | fallback |
| 9 | Q1034 | 1,0 | có | fallback | 2 | fallback |
| 10 | Q0620 | 1,0 | có | fallback | 1 | fallback |
| 11 | Q0621 | 1,0 | có | **validated** | 1 | fallback |
| 12 | Q0824 | 0,0 | không | not_called | 0 | not_called |
| 13 | Q0689 | 3,0 | có | fallback | 1 | fallback |
| 14 | Q0704 | 1,0 | có | fallback | 1 | fallback |
| 15 | Q0701 | 1,0 | có | fallback | 1 | fallback |
| 16 | Q0718 | 1,0 | có | fallback | 2 | fallback |
| 17 | Q0828 | 0,0 | không | not_called | 0 | not_called |
| 18 | Q0858 | 1,0 | có | fallback | 1 | fallback |
| 19 | Q0685 | 1,0 | có | fallback | 1 | validated |
| 20 | Q0688 | 1,0 | có | **validated** | 1 | after_repair |
| 21 | Q0695 | 3,0 | có | fallback | 1 | fallback |
| 22 | Q0632 | 1,0 | có | **validated** | 1 | fallback |
| 23 | Q0635 | 1,0 | có | fallback | 2 | fallback |
| 24 | Q0636 | 2,33 | có | fallback | 2 | fallback |
| 25 | Q1798 | 1,0 | có | fallback | 1 | fallback |
| 26 | Q0671 | 1,0 | có | fallback | 2 | after_repair |
| 27 | Q0674 | 2,33 | có | fallback | 1 | fallback |
| 28 | Q0677 | 1,0 | có | fallback | 1 | fallback |
| 29 | Q0706 | 1,0 | có | fallback | 1 | fallback |
| 30 | Q0707 | 1,0 | có | fallback | 2 | fallback |
| 31 | Q0693 | 1,0 | có | fallback | 2 | validated 3,0 |
| 32 | Q0696 | 1,0 | có | fallback | 2 | fallback |
| 33 | Q0633 | 1,67 | có | fallback | 2 | fallback |
| 34 | Q0787 | 1,0 | có | fallback | 1 | fallback |
| 35 | Q1777 | 3,0 | có | fallback | 2 | fallback |
| 36 | Q1827 | 1,0 | có | fallback | 2 | fallback |
| 37 | Q2157 | 1,0 | có | fallback | 1 | fallback |
| 38 | Q0662 | 1,0 | có | **validated** | 1 | fallback |
| 39 | Q0665 | 1,0 | có | fallback | 1 | fallback |
| 40 | Q0668 | 1,0 | có | fallback | 2 | fallback |
| 41 | Q0705 | 1,0 | có | fallback | 1 | fallback |
| 42 | Q0709 | 1,0 | có | **validated** | 1 | fallback |
| 43 | Q0843 | 1,0 | có | fallback | 2 | fallback |
| 44 | Q0864 | 1,0 | có | fallback | 1 | fallback |
| 45 | Q0680 | 3,0 | có | fallback | 2 | fallback |
| 46 | Q0684 | 1,0 | có | fallback | 1 | fallback |
| 47 | Q0924 | 1,0 | có | **validated** | 1 | fallback |
| 48 | Q0630 | 1,0 | có | fallback | 2 | fallback |
| 49 | Q0652 | 1,67 | có | fallback | 2 | fallback |
| 50 | Q0658 | 1,67 | có | fallback | 2 | fallback |

## 5. Đếm lỗi kiểm định trước/sau

Đếm theo lượt gọi provider đã ghi (mỗi câu lưu tối đa 3 lượt gần nhất; FIX1 69 lượt/21 sửa, SYNTH 66 lượt/18 sửa):

| Lỗi | FIX1 (69 lượt) | SYNTH (66 lượt) | Chênh |
|---|---|---|---|
| `uncited_material_claim` | 65 | 64 | −1 |
| `missing_citations` | 55 | 53 | −2 |
| `claim_budget_exceeded` | 31 | 35 | +4 |
| `unsupported_critical_literal` | 24 | 25 | +1 |
| `missing_required_facet_citation` | 2 | 2 | 0 |
| `language_conformance_failed` | 1 | 0 | −1 |
| `missing_required_limitations` | 0 | 2 | +2 |

Phân loại lượt gọi đầu (48 câu có gọi provider): **24 câu vướng lỗi phối hợp** đúng đối tượng vé (tập lỗi ⊆ cắt-được ∪ sửa-được và có ≥1 lỗi cắt-được — code cũ rớt thẳng fallback, code mới được vào cắt-dòng); 23 câu lỗi thuần sửa-được; 1 câu chỉ `uncited` (vừa ⊆ cắt vừa ⊆ sửa).

Rào sửa an toàn trên dữ liệu thật: 18 lượt sửa (`sua_loi=true`) chỉ nhận lỗi trình bày (`missing_citations` 16, `uncited` 16, `budget` 9, limitations/facet 1 mỗi loại) — **0 lượt sửa nào có `literal`/`unknown` trong đầu vào** (kiểm bằng script trên `rows-synth.jsonl`).

Vì sao validated tăng mà GPA giảm: 9 câu validated đều có điểm rubric 1,0 (đáp án qua kiểm định nhưng thiếu từ khóa đáp án tham chiếu — trích đúng nguồn nhưng rubric chấm 0 từ khóa + 1 điểm trích dẫn); 2 câu lost (Q0703 −1,33, Q0693 −2,0) đều do provider lượt này trả nội dung khác (thêm lỗi ngân sách/sửa không xong) — không phải code mới làm hỏng đường xử lý.

## 6. Rào cứng (index chỉ-đọc + CPU-only)

- Index `library.sqlite`: SHA-256 `45eb0e072893…b7c0` + md5 `239009676829…` **khớp trước/sau** lane (`SYNTH index sau: sha_khop=True md5_khop=True (chi doc: True)`), size 2.942.201.856 byte không đổi — 0 ghi index.
- CPU-only: `AIOS_RETRIEVAL_DEVICE=cpu`, pipeline log `profile=bge_m3_hybrid device=cpu strict=True`, backend ghim `CPUExecutionProvider`; preload dense 121.331 chunk/3,0s + sparse 121.331 chunk/12,6s.
- Cầu tổng hợp `127.0.0.1:8585` (`openai_compatible_local`, `model=gemini-2.5-flash`): 66/66 lượt gọi có hồi đáp, 0 lỗi mạng, 0 `provider_network_error`.
- Không merge `main`; mọi commit trên `phieu-viec/rag-fix1` (code `c7af43c` riêng, báo cáo riêng).

## 7. Ghi chú

- Kết quả trung thực: mục tiêu vé (validated+after_repair tăng rõ so với 6/50) **ĐẠT** (9/50, +3); GPA giảm nhẹ 1,29→1,22 do ngẫu nhiên provider giữa 2 lượt đo, không do nới chuẩn — mọi câu validated đều qua **full validation** như cũ.
- Việc còn lại cho vé sau (ngoài phạm vi vé này): lỗi `claim_budget_exceeded` tăng +4 và vẫn là nút thắt lớn nhất sau `uncited`/`missing_citations` (35/66 lượt); provider lặp lại nội dung khác nhau giữa các lượt đo nên so sánh A/B tuyệt đối cần nhiều lượt chạy.
- Sự cố giữa chừng: 1 lần `git stash pop` nhầm bật stash cũ làm bẩn cây (đã `reset --hard` về HEAD ngay, code vé còn nguyên — kiểm bằng `grep` helper = 3); đối chứng lỗi có sẵn dùng cây làm việc tách riêng tại `6ed40ea` thay vì stash, đã xóa sau xong.
