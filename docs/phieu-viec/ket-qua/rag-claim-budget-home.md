# Báo cáo RAG-CLAIM-BUDGET-HOME — nút thắt `claim_budget_exceeded` + đo lại 50 câu

Ngày đo: 2026-10-07; ngày chốt + kiểm chứng lại: 2026-10-08 (máy nhà `h410asrock`).
Trạng thái: `xong-cho-duyet` (chốt 08/10), chờ Muse đối chứng.
Vé: `RAG-CLAIM-BUDGET-HOME` — prompt `docs/phieu-viec/mailbox/prompt.md` (bản xếp hàng `prompt-queue-rag-claim-budget-home.md`).

## 1. Kết quả điều tra (mục 1 vé — từ dữ liệu lane thật)

Dữ liệu: `rows-synth.jsonl` + `rows-fix1.jsonl` (ngoài Git) + code tại `6dc717d` + probe mới 4 câu (`probe_budget.json`, ngoài Git).

- 27/50 câu dính `budget` ở bất kỳ lượt nào (FIX1: 22 → SYNTH: 27, tăng).
- Fallback + budget ở lượt CUỐI: **18 câu** —
  thuần budget chỉ 2 (`Q0703`, `Q0693`, đều sau sửa);
  10 câu vướng `unsupported_critical_literal` ngay lượt 1 = hard-stop (không cắt/sửa được);
  6 câu còn lại vướng phối hợp budget + uncited/missing sau sửa.
- 8 lượt sửa nhận `repair_errors` chứa budget: **8/8 TRƯỢT** (chỉ `Q0696` hết budget nhưng còn lỗi khác).
  Nghĩa là hướng dẫn COMPRESS trong hợp đồng sửa không đủ hiệu lực với provider thật.
- Phân bố material (đếm từ `dau_ans` lưu trong log, `max_claims=8` vì toàn lane `general`):
  `Q0703` lượt 1 ≥5 dòng → sửa còn ≥3; `Q0693` lượt 1 ≥3 → sửa còn ≥3.
  Vượt nhẹ (+1..+3), không vượt xa — dạng provider viết thừa dòng mở đầu không trích dẫn + không nén.
- Hợp đồng thực gửi: ĐÃ chứa `Maximum material claims: 8` + repair ĐÃ chứa COMPRESS
  (probe mới 4 câu xác nhận `contract_has_budget=True`, `repair_has_compress=True`).
- Kết luận gốc: **(a) provider không tuân hợp đồng là chính** (viết dòng mở đầu không trích dẫn,
  lượt sửa không nén) + **(b) lượt sửa nén không đủ là phụ** (8/8 trượt).
  **(c) loại trừ**: ngân sách khớp hình dạng câu trả lời (49/50 `general`, `max_claims=8` đủ, `required_facets` rỗng).

## 2. Thay đổi code / hợp đồng (mục 2 + rào cứng mục 3)

File: `src/aios_habit/rag_v2/synthesis.py` (commit `cb9356d`, +109 dòng). Không tăng `max_claims`,
không đổi cách đếm, không tắt lỗi nào, không đổi rubric; literal/nguồn lạ giữ hard stop.

1. **Hợp đồng lượt 1 cụ thể hoá ngân sách** (`format_provider_synthesis_contract`):
   trước chỉ ghi `Maximum material claims: N`; sau thêm `budget_rule` —
   đếm từng dòng factual là 1 claim, tối đa N dòng, **dòng mở đầu không trích dẫn vẫn tốn ngân sách**.
2. **Nén xác định sau sửa trượt** (`merge_cited_provider_answer_lines` + móc trong `synthesize_with_provider`):
   chỉ khi lỗi còn lại sau 1 lượt sửa là THUẦN `provider_answer_claim_budget_exceeded`;
   gộp dòng kề cùng đúng 1 nhãn (nối bằng `; `, bỏ dấu bullet thừa, giữ nguyên từng chữ/số/mã đã trích dẫn).
   Dòng khác nhãn / thiếu trích dẫn / nhãn lạ / literal không căn cứ KHÔNG gộp.
   Chỉ nhận bản gộp khi qua **full validation** (`valid`), không thì fallback như cũ.

## 3. Test mới + hồi quy (mục 4)

File: `tests/test_rag_v2_synthesis.py` (+83 dòng, 3 test vé):

- (a) `test_budget_contract_counts_lines_and_bans_uncited_openers` — hợp đồng có đếm dòng + cấm dòng mở đầu không trích dẫn.
  **FAIL trên cũ** (`assert 'at most 1 such lines' in ...` — hợp đồng cũ không có câu này).
- (b) `test_pure_budget_miss_after_repair_recovers_via_deterministic_merge` — thuần budget qua nén xác định
  (`- Verify access before release [1]; Deploy the release package [1]`).
  **FAIL trên cũ** (`provider_used=False`, rớt fallback).
- (c) `test_budget_miss_with_fabricated_literal_never_merges` — budget + literal bịa:
  dòng bịa vẫn chỉ bị cắt (`- Deploy the release package [1]`, `provider_validated` qua surgery),
  toàn dòng bịa/nguồn lạ thì fail-closed 0 lượt sửa. PASS cả cũ lẫn mới (giữ hành vi đúng).
- Hồi quy: 3 test vé SYNTH xanh; cụm hẹp synthesis+provider+evidence **99 đạt / 4 lỗi có sẵn ngoài vé**
  (đối chứng cây cũ `6dc717d` đúng 4 lỗi này: limitations + 3 provider privacy/label);
  cụm rộng `tests/test_rag_v2_*.py`: **402 đạt / 7 lỗi** đúng nhóm vé SYNTH đã phân loại
  (limitations + 3 provider + dev_cli + 2 eval_harness).
- Cổng repo: Python 3.11 (qua `uv`), `compileall` sạch, `cli audit` PASS (warnings rỗng), import app OK.
- **Kiểm chứng lại tại HEAD phiên 08/10** (`f8f2670`, sau các commit khác của máy nhà/agy/opencode):
  code budget nguyên vẹn (đọc trực tiếp 3 đoạn — `budget_rule`, `merge_cited_provider_answer_lines`,
  móc thuần-budget sau sửa); 3 test vé **xanh**; cụm hẹp synthesis+evidence+provider **102 đạt/1 lỗi lẻ**;
  cụm rộng `tests/test_rag_v2_*.py` **408 đạt/1 lỗi lẻ**. Lỗi lẻ
  `test_provider_limitations_contain_accurate_reasons` đã đối chứng trên cây cũ `6dc717d`
  (worktree tách, chỉ-đọc): rớt **y hệt** → có sẵn (nhóm nhãn privacy), ngoài phạm vi vé,
  không do `cb9356d` hay commit sau. `synthesis.py` sau vé có thêm thay đổi lọc nhiễu của opencode
  (`39608db`: cân bằng ngoặc + ưu tiên item một-facet — phía retrieval), không đụng `max_claims`,
  cách đếm hay điều kiện nén; cổng phiên 08/10 giữ nguyên: compileall sạch, `cli audit` PASS, import app OK.

## 4. Đo lại 50 câu (mục 5 — đúng điều kiện SYNTH)

Runner `do_rag_50_budget.py` (ngoài Git, cùng logic SYNTH: hybrid limit=15 + gói 8,
`openai_compatible_local` qua cầu `127.0.0.1:8585` `direct_ready`, CPU-only, index chỉ-đọc,
checkpoint `rows-budget.jsonl`). 50/50, 0 lỗi kỹ thuật, 0 lỗi mạng.

| Cột | Tổng /150 | GPA | Qua kiểm định | Ghi chú |
|---|---|---|---|---|
| BUDGET (lượt này) | **63,84** | **1,28** | **11/50** (10 validated + 1 after_repair) | fallback 37, not_called 2 |
| SYNTH | 61,17 | 1,22 | 9/50 | baseline vé |
| FIX1 | 64,5 | 1,29 | 6/50 | — |
| C-Agent PC0575 | — | 2,16 | — | tham khảo |

- Gain/lost vs SYNTH: **tăng 2 / giảm 0 / nguyên 48**.
  Gain đúng 2 câu lost vé trước do budget: `Q0703` 1,0→1,67 (fallback→validated),
  `Q0693` 1,0→3,0 (fallback→validated). **0 câu lost.**
- Đếm lỗi kiểm định (theo lượt gọi): budget **35→7 lượt (−80%)**;
  `uncited` 64→62, `missing_citations` 53→54, `literal` 25→23,
  còn `facet` 2, `language` 1. Tổng lượt gọi 67 (sửa 19).
- Budget còn lại 7 lượt ở 7 câu: `Q0700/Q0708/Q0668/Q0924` (validated dù lượt 1 vướng budget —
  provider viết thừa nhưng surgery/repair cứu được phần hợp lệ),
  `Q0632/Q0696` (fallback, sửa hết budget nhưng còn uncited/missing),
  `Q0688` (**after_repair**: lượt 1 thuần budget → sửa hết budget → nhận).
- Tách staging (cùng định nghĩa vé trước, 12 câu không khớp:
  `Q0703, Q0851, Q1034, Q0685, Q0688, Q0632, Q0635, Q0693, Q0696, Q1827, Q0705, Q0684`):
  khớp 38 câu tổng 49,17 GPA 1,294 (≥2: 6, =3: 4);
  không khớp 12 câu tổng 14,67 GPA 1,222 (≥2: 1, =3: 1).
- Mục tiêu vé: validated **tăng rõ 9→11 (+2, ĐẠT)**;
  GPA 1,22→1,28 (tăng, nhưng chưa vượt FIX1 1,29 — chênh lệch do provider ngẫu nhiên giữa lượt,
  báo cáo trung thực, không nới chuẩn).
- Bảng 50 câu (stt id điểm-trích-chếđộ):

| stt | id | BUDGET | SYNTH | FIX1 | chế độ lượt này |
|---|---|---|---|---|---|
| 1 | Q0699 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 2 | Q0700 | 1.0 | 1.0 | 1.0 | provider_validated |
| 3 | Q0703 | 1.67 | 1.0 | 2.33 | provider_validated |
| 4 | Q0708 | 1.0 | 1.0 | 1.0 | provider_validated |
| 5 | Q0849 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 6 | Q0850 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 7 | Q0851 | 1.0 | 1.0 | 1.0 | provider_validated |
| 8 | Q1029 | 1.5 | 1.5 | 1.5 | local_extractive_provider_fallback |
| 9 | Q1034 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 10 | Q0620 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 11 | Q0621 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 12 | Q0824 | 0.0 | 0.0 | 0.0 | local_extractive_provider_not_called |
| 13 | Q0689 | 3.0 | 3.0 | 3.0 | local_extractive_provider_fallback |
| 14 | Q0704 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 15 | Q0701 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 16 | Q0718 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 17 | Q0828 | 0.0 | 0.0 | 0.0 | local_extractive_provider_not_called |
| 18 | Q0858 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 19 | Q0685 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 20 | Q0688 | 1.0 | 1.0 | 1.0 | provider_validated_after_repair |
| 21 | Q0695 | 3.0 | 3.0 | 3.0 | local_extractive_provider_fallback |
| 22 | Q0632 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 23 | Q0635 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 24 | Q0636 | 2.33 | 2.33 | 2.33 | local_extractive_provider_fallback |
| 25 | Q1798 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 26 | Q0671 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 27 | Q0674 | 2.33 | 2.33 | 2.33 | local_extractive_provider_fallback |
| 28 | Q0677 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 29 | Q0706 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 30 | Q0707 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 31 | Q0693 | 3.0 | 1.0 | 3.0 | provider_validated |
| 32 | Q0696 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 33 | Q0633 | 1.67 | 1.67 | 1.67 | local_extractive_provider_fallback |
| 34 | Q0787 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 35 | Q1777 | 3.0 | 3.0 | 3.0 | local_extractive_provider_fallback |
| 36 | Q1827 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 37 | Q2157 | 1.0 | 1.0 | 1.0 | provider_validated |
| 38 | Q0662 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 39 | Q0665 | 1.0 | 1.0 | 1.0 | provider_validated |
| 40 | Q0668 | 1.0 | 1.0 | 1.0 | provider_validated |
| 41 | Q0705 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 42 | Q0709 | 1.0 | 1.0 | 1.0 | provider_validated |
| 43 | Q0843 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 44 | Q0864 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 45 | Q0680 | 3.0 | 3.0 | 3.0 | local_extractive_provider_fallback |
| 46 | Q0684 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 47 | Q0924 | 1.0 | 1.0 | 1.0 | provider_validated |
| 48 | Q0630 | 1.0 | 1.0 | 1.0 | local_extractive_provider_fallback |
| 49 | Q0652 | 1.67 | 1.67 | 1.67 | local_extractive_provider_fallback |
| 50 | Q0658 | 1.67 | 1.67 | 1.67 | local_extractive_provider_fallback |

## 5. Rào cứng

- Index chỉ-đọc: SHA-256 `45eb0e07…b7c0` khớp trước/sau, md5 khớp, size không đổi → **không ghi index**.
- CPU-only (`CUDA_VISIBLE_DEVICES=""`, `AIOS_RETRIEVAL_DEVICE=cpu`).
- Không tăng `max_claims`, không đổi đếm, không tắt lỗi, không đổi rubric; fail-closed giữ nguyên.
- Không merge `main`. Commit code riêng (`cb9356d`), commit báo cáo riêng (vé này).
- Full `pytest -q`: đang chạy nền, bổ sung số khi xong (cụm rộng RAG v2 đã có 402/7 như §3).

## 6. Phụ lục — kiểm chứng lại từ dữ liệu thô + nghiệm thu dùng thật (phiên 08/10)

- **Tính lại toàn bộ số đầu từ `rows-budget.jsonl`** (50/50 hàng thô, ngoài Git, đọc trực tiếp bằng Python):
  tổng **63,84/150, GPA 1,28**; ≥2: 7, =3: 5; chế độ đúng phân bố 37 fallback + 10 `validated`
  + 1 `after_repair` + 2 `not_called`; 67 lượt gọi/19 lượt sửa; lỗi theo lượt gọi khớp từng mã:
  budget **7** (SYNTH 35 → −80%), uncited 62, missing_citations 54, literal 23, facet 2, language 1;
  `ok=True` cả 50 hàng (0 lỗi kỹ thuật). **Khớp 100% bảng §4.**
- **Nghiệm thu bằng dùng thật** (đúng tinh thần QUY-UOC 07/10): 50 câu hỏi thật của bộ đề LSU chạy
  **đầu-cuối qua đúng pipeline trả lời của app** — index production chỉ-đọc
  (`C:/AIOS_workspace_chat_rag_v2_production/.../tri_thuc`, SHA-256 `45eb0e07…b7c0` khớp trước/sau),
  hybrid retrieval thật (dense+sparse+lexical, limit=15), gọi `synthesize_with_provider`
  (cùng hàm app dùng) qua provider thật `openai_compatible_local` (cầu `127.0.0.1:8585`).
  Đáp án thật + thời gian thật từng câu lưu trong `rows-budget.jsonl` (`dap_an`, `giay_cau`):
  **TB 15,88s/câu, nhanh nhất 7,66s, chậm nhất 55,58s** (câu đơn giản ~8–15s, câu cần sửa/thử lại lâu hơn).
  Bằng chứng kèm: log `tien-trinh-budget.log` (từng câu + dòng chốt `tong=63.84/150 GPA=1.28`),
  `ket-qua-budget.json`, `probe_budget.json` — toàn bộ trên máy nhà (ngoài Git), Muse đối chứng lại được.
- **Giới hạn trung thực:** phiên 08/10 **không chạy lại lane** — cầu `8585` đã tắt sau lượt đo 07/10
  (netstat không còn LISTEN; agy đang chiếm CPU cho lane ROUTER của họ), nên số liệu là của lượt đo 07/10
  được kiểm chứng lại từ dữ liệu thô + chạy lại toàn bộ test/cổng tại HEAD 08/10.
  Vé này không đụng UI nên không có ảnh chụp màn hình; bằng chứng là file thô + log trên máy nhà.
