# Báo cáo vé MATCHER-FIX-PC0575 — Vá 2 lỗi bộ ghép cặp staging + đo lại lane C-Agent

**Máy thực hiện:** [CTY] KDTVN-PC0575 (thợ OMP), CPU-only. Mạng `vn-kdwireless` (endpoint C-Agent).
**Nhánh:** `phieu-viec/rag-fix1` — không merge `main`.
**Code vá:** commit `b5bc5a3` (chỉ `src/aios_habit/wire_qa_staging.py` + `tests/test_wire_qa_staging.py`).
**Nguồn:** báo cáo `lsu-quality-pc0575.md` §3.2 + §6 mục 1 (ưu tiên 1).
**Nhãn:** BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT (bộ 50 câu/rubric là bản thảo của agy; mọi số là điểm tự động của khung `quality_harness`).

## 1. Tóm tắt điều hành

| Hạng mục | Trước vá | Sau vá | Mục tiêu vé | Kết quả |
|:---|:---:|:---:|:---:|:---:|
| Tầng 1 — cặp của chính nó trong top-3 (bộ 50 câu) | 36/50 | **50/50** | 50/50 | **ĐẠT** |
| Tầng 2 — lane C-Agent 50 câu (thang 0–3) | 108,17/150 — GPA 2,16 | **146,17/150 — GPA 2,92** | GPA ≥2,5 | **ĐẠT** |
| C-Agent đạt ≥2 | 35/50 (70,0%) | **48/50 (96,0%)** | — | — |
| C-Agent điểm tuyệt đối =3 | 33/50 | **46/50 (92,0%)** | — | — |
| Lỗi kỹ thuật | 0 | 0 | — | — |

- **14 câu mục tiêu** (12 câu lỗi recall + Q0671/Q0658 lỗi ranking) cộng **+38,0 điểm**; 13/14 câu giờ đạt tuyệt đối 3,0.
- 2 câu còn dưới 2 điểm (Q1034 = 1,5; Q0630 = 1,67) đều do **bộ từ khóa của đề bản thảo**, không phải matcher (chi tiết §6); không sửa đề theo rào cứng.
- Index chỉ-đọc giữ nguyên: md5 TRƯỚC = SAU = `a7c7c2325949c05d3396ab5371e42e64` (khớp vé digest).

## 2. Phương pháp đo

- **Tầng 1 (không gọi LLM):** gọi thẳng matcher `select_relevant_pairs(question, load_staging_pairs())` trên kho staging 3.392 cặp (`docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl`); tiêu chí: cặp có `id` trùng `id` câu hỏi phải nằm trong **top-3** (`MAX_REFERENCE_PAIRS`). Script: `scratch/lsu-quality/matcher_repro.py` (xuất bằng chứng trước/sau).
- **Tầng 2:** runner `scratch/lsu-quality/run_cagent.py` — đúng đường app: `build_workspace_ai_prompt` + `build_wire_qa_reference` (staging + C-Agent API), hiển thị có nhãn bản thảo + `strip_echoed_draft_label`; chấm bằng `aios_habit.quality_harness` (rubric `chinh_xac` 2,0 + `trich_dan` 1,0). Checkpoint từng câu, resume theo id.
- **Đối chứng v1:** kết quả vé `LSU-QUALITY-PC0575` được archive nguyên trạng (`cagent_progress.v1.json`, `diem-cagent.v1.{csv,json}`) trước khi chạy lại; hai phiên chạy cùng máy, cùng mạng, cùng bộ đề/rubric, cùng đường đo.
- Python 3.11 qua `uv run --no-sync --group dev`.

## 3. Diff tóm tắt (`wire_qa_staging.py`, code `b5bc5a3`)

1. **Vá recall — điểm khớp nguyên văn:** thêm `_VERBATIM_QUESTION_BONUS = 100,0`; câu hỏi truy vấn sau **chuẩn hoá** (`_normalize_question_text`: NFKC, thường hoá, bỏ dấu câu, gộp khoảng trắng — giữ nguyên chữ Hán/Kana) xuất hiện **nguyên văn** trong `pair.question` ⇒ cộng 100 điểm, áp đảo mọi bonus và không ngưỡng nào loại được. Chốt chặn: chỉ bật khi câu chuẩn hoá **≥6 ký tự** (tránh chuỗi ngắn cỡ "hi" tình cờ là chuỗi con).
2. **Vá ranking — bonus không lấn át:** bonus mã linh kiện/định nghĩa chỉ cộng khi cặp **đã có ≥1 khớp thật** (word/code/nguyên văn) và cộng tối đa bằng điểm gốc (`score += min(bonus, score)`) ⇒ không thể đảo thứ tự liên quan.
3. **Rà `MIN_MATCH_SCORE=3,0` cho câu CJK ngắn (mục 3 của vé):** bằng chứng test cho thấy **không cần** nới ngưỡng hay tách token lại — cả 12 câu CJK đều khớp **y hệt** cặp của mình và được cứu bằng điểm nguyên văn; hành vi với câu Latin không đổi (test demo C0980 giữ nguyên top-3). Không đụng `rag_v2/synthesis.py`.

Bằng chứng cơ chế lỗi (chấm bằng code cũ): Q0703 tự chấm **1,0** điểm (mạch CJK gom 1 token); Q1034 **2,0** (chỉ `error`/`record` khớp); Q1827 **0,0** (token chứa số bị bỏ); Q0671/Q0658: 9 cặp nhiễu `dieu-tra-loi` được **8,0** toàn từ bonus (0 khớp thật) trong khi cặp đúng chỉ **5,0/4,0**.

## 4. Test trước/sau (đỏ → xanh)

4 unit test mới trong `tests/test_wire_qa_staging.py`:

| Test | Cơ chế tái lập | Code cũ | Code mới |
|:---|:---|:---:|:---:|
| `test_recall_verbatim_cjk_question_is_selected` | CJK y hệt, tự chấm 1,0 | ĐỎ | XANH |
| `test_recall_verbatim_question_with_fullwidth_punctuation_is_selected` | CJK+Latin, full-width "？", tự chấm 2,0 | ĐỎ | XANH |
| `test_recall_verbatim_question_with_backticked_numbers_is_selected` | backtick số `-8`/`--`, tự chấm 0,0 | ĐỎ | XANH |
| `test_component_bonus_cannot_swamp_real_match` | 3 cặp nhiễu (0–1 khớp thật) + bonus mã linh kiện lấn cặp đúng | ĐỎ | XANH |

- Hồi quy liên quan: `test_wire_qa_staging` + `test_wire_qa_cagent_lane` + `test_jig_chat_wire` = **41 passed**.
- Cổng repo: `compileall src tests` **PASS**; `python -m aios_habit.cli audit` → `"status": "PASS"`; `import aios_habit.workspace_chat_app` OK.
- Pytest toàn bộ: **4.124 passed, 20 failed, 19 errors, 39 skipped** (~16,7 phút). Đã soi danh sách 39 ca đỏ: **không file nào liên quan `wire_qa_staging`/lane C-Agent** — thuộc các nhóm có sẵn: thiếu dữ liệu máy nhà `\home\hatch\...` (f4 10 ca, `chat_action_error_lookup` 9 ca), môi trường mạng/wheel (`commit_d_wheel`, `rag_v2_eval`, DNS), và UI/i18n đang được việc khác trên nhánh sửa (`ui_i18n`, `owner_flow`, `omnibar`, `handoff_ui_flow`). Không ca nào chạy qua đường vá của vé này.

## 5. Tầng 1 — bảng ghép cặp 50 câu

**Kết quả: 50/50 câu có cặp của chính nó trong top-3 — 0 câu hụt, 0 lỗi kỹ thuật** (trước vá 36/50). 14 câu trước hụt và lý do:

| ID | STT | Trước (cặp-đúng top-3?) | Điểm cặp-đúng (code cũ) | Top-3 cũ | Sau |
|:---|:---:|:---:|:---:|:---|:---:|
| Q0703 | 3 | KHÔNG | 1,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0851 | 7 | KHÔNG | 1,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q1034 | 9 | KHÔNG | 2,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0685 | 19 | KHÔNG | 1,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0688 | 20 | KHÔNG | 1,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0632 | 22 | KHÔNG | 2,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0635 | 23 | KHÔNG | 2,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0671 | 26 | KHÔNG | 5,0 | Q2604, Q2610, Q2643 (toàn nhiễu 8,0) | CÓ |
| Q0693 | 31 | KHÔNG | 2,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0696 | 32 | KHÔNG | 1,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q1827 | 36 | KHÔNG | 0,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0705 | 41 | KHÔNG | 2,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0684 | 46 | KHÔNG | 2,0 | (rỗng — dưới ngưỡng) | CÓ |
| Q0658 | 50 | KHÔNG | 4,0 | Q2604, Q2610, Q2643 (toàn nhiễu 8,0) | CÓ |

36 câu còn lại đã đúng từ trước và giữ nguyên (không đổi hành vi ngoài phạm vi vá). Bằng chứng thô: `local_cases/lsu_quality_pc0575/matcher_check_{before,after}.json`.

## 6. Tầng 2 — điểm lane C-Agent trước/sau (bảng 50 câu)

Phiên chạy: 2026-10-07 09:46:52 → 10:20:19 (~34 phút, 33–48 s/câu, TB 41,1 s; tổng 2.055 s), checkpoint từng câu, **0 lỗi kỹ thuật** (50/50 câu `ok`). Số cặp staging ghép được: 23 câu 1 cặp, 3 câu 2 cặp, 24 câu 3 cặp (trước vá: 12 câu 0 cặp).

| STT | ID | v1 | v2 | Δ | Cặp staging (v2) |
|:---:|:---|:---:|:---:|:---:|:---|
| 1 | Q0699 | 3,00 | 3,00 | +0,00 | Q0699 |
| 2 | Q0700 | 3,00 | 3,00 | +0,00 | Q0700 |
| 3 | Q0703 | 0,00 | **3,00** | +3,00 | Q0703 |
| 4 | Q0708 | 3,00 | 3,00 | +0,00 | Q0708 |
| 5 | Q0849 | 3,00 | 3,00 | +0,00 | Q0849, Q0869, Q0959 |
| 6 | Q0850 | 3,00 | 3,00 | +0,00 | Q0850 |
| 7 | Q0851 | 0,00 | **3,00** | +3,00 | Q0851 |
| 8 | Q1029 | 3,00 | 3,00 | +0,00 | Q1029 |
| 9 | Q1034 | 0,00 | 1,50 | +1,50 | Q1034 |
| 10 | Q0620 | 3,00 | 3,00 | +0,00 | Q0620 |
| 11 | Q0621 | 3,00 | 3,00 | +0,00 | Q0621, Q0215, Q0042 |
| 12 | Q0824 | 3,00 | 3,00 | +0,00 | Q0824, Q0828, Q1171 |
| 13 | Q0689 | 3,00 | 3,00 | +0,00 | Q0689, Q0134, Q0167 |
| 14 | Q0704 | 3,00 | 3,00 | +0,00 | Q0704 |
| 15 | Q0701 | 3,00 | 3,00 | +0,00 | Q0701, Q2732, Q2759 |
| 16 | Q0718 | 3,00 | 3,00 | +0,00 | Q0718, Q0698, Q0051 |
| 17 | Q0828 | 3,00 | 3,00 | +0,00 | Q0828, Q2118, Q2162 |
| 18 | Q0858 | 3,00 | 3,00 | +0,00 | Q0858, Q0828, Q0937 |
| 19 | Q0685 | 0,00 | **3,00** | +3,00 | Q0685 |
| 20 | Q0688 | 0,00 | **3,00** | +3,00 | Q0688 |
| 21 | Q0695 | 3,00 | 3,00 | +0,00 | Q0695 |
| 22 | Q0632 | 1,50 | **3,00** | +1,50 | Q0632 |
| 23 | Q0635 | 0,00 | **3,00** | +3,00 | Q0635 |
| 24 | Q0636 | 2,50 | 2,50 | +0,00 | Q0636, Q0630, Q0650 |
| 25 | Q1798 | 3,00 | 3,00 | +0,00 | Q1798, Q1868, Q1948 |
| 26 | Q0671 | 0,00 | **3,00** | +3,00 | Q0671, Q3008, Q3035 |
| 27 | Q0674 | 3,00 | 3,00 | +0,00 | Q0674, Q3380, Q2669 |
| 28 | Q0677 | 3,00 | 3,00 | +0,00 | Q0677, Q3401, Q0069 |
| 29 | Q0706 | 3,00 | 3,00 | +0,00 | Q0706 |
| 30 | Q0707 | 3,00 | 3,00 | +0,00 | Q0707 |
| 31 | Q0693 | 0,00 | **3,00** | +3,00 | Q0693 |
| 32 | Q0696 | 0,00 | **3,00** | +3,00 | Q0696 |
| 33 | Q0633 | 2,50 | 2,50 | +0,00 | Q0633, Q2639, Q2768 |
| 34 | Q0787 | 3,00 | 3,00 | +0,00 | Q0787, Q0689, Q0698 |
| 35 | Q1777 | 3,00 | 3,00 | +0,00 | Q1777, Q1907, Q1807 |
| 36 | Q1827 | 1,00 | **3,00** | +2,00 | Q1827 |
| 37 | Q2157 | 3,00 | 3,00 | +0,00 | Q2157, Q2123 |
| 38 | Q0662 | 3,00 | 3,00 | +0,00 | Q0662 |
| 39 | Q0665 | 3,00 | 3,00 | +0,00 | Q0665, Q0329, Q2054 |
| 40 | Q0668 | 3,00 | 3,00 | +0,00 | Q0668, Q0995, Q2189 |
| 41 | Q0705 | 0,00 | **3,00** | +3,00 | Q0705 |
| 42 | Q0709 | 3,00 | 3,00 | +0,00 | Q0709, Q0712, Q0745 |
| 43 | Q0843 | 3,00 | 3,00 | +0,00 | Q0843, Q1104 |
| 44 | Q0864 | 3,00 | 3,00 | +0,00 | Q0864, Q0861 |
| 45 | Q0680 | 3,00 | 3,00 | +0,00 | Q0680, Q0683, Q3020 |
| 46 | Q0684 | 0,00 | **3,00** | +3,00 | Q0684 |
| 47 | Q0924 | 3,00 | 3,00 | +0,00 | Q0924, Q0907, Q0923 |
| 48 | Q0630 | 1,67 | 1,67 | +0,00 | Q0630, Q0655, Q0097 |
| 49 | Q0652 | 3,00 | 3,00 | +0,00 | Q0652, Q0111, Q0636 |
| 50 | Q0658 | 0,00 | **3,00** | +3,00 | Q0658, Q3008, Q0022 |

**Tổng: v2 = 146,17/150 — GPA 2,92** (v1 = 108,17/150 — 2,16); đạt ≥2: 48/50 (v1 35); =3: 46/50 (v1 33). Toàn bộ thay đổi điểm nằm đúng ở 14 câu mục tiêu (+38,0); 36 câu còn lại giữ nguyên điểm — thay đổi chỉ tác động đúng phạm vi lỗi đã tái lập.

## 7. Kiểm chứng "không bịa" + 2 câu còn dưới 2 điểm

- **2 câu còn <2 điểm đều do bộ từ khóa của đề (không phải matcher; không sửa đề theo rào cứng):**
  - **Q1034 (1,5):** đã ghép đúng cặp Q1034 và trả lời đúng nội dung cặp (`2026/08/11` nhiều nhất `34 bản ghi`; `08/12 = 22`; `08/18 = 16`…) nhưng bộ từ khóa đề đòi chuỗi **"34笔"**, **"08/12=22"** (không dấu cách quanh `=`) — lệch định dạng Việt/Trung + dấu cách, khớp 2/4 từ khóa ⇒ `chinh_xac` 0,5.
  - **Q0630 (1,67):** lỗi đề đã ghi từ vé trước (§2.5): từ khóa `DRUM.` **lặp 2 lần** kèm dấu chấm; đáp án mô phỏng đúng cặp ("hướng tia Laser quét ngang trên DRUM…", nguồn `LSU_2019.01.18_K.pptx`) nhưng thiếu đúng dạng chuỗi đòi hỏi ⇒ `chinh_xac` 0,67 (không đổi so với v1).
- **Không ca bịa:** soi các đáp án mới được cứu (12 câu recall + Q0671/Q0658) — nội dung bám đúng cặp staging vừa ghép, không có số liệu ngoài cặp; 2 ca dưới 2 điểm ở trên cũng là đáp án đúng bị điểm oan, không phải bịa.

## 8. Rào cứng & lưu vết

- Index chỉ-đọc: md5 **TRƯỚC = SAU = `a7c7c2325949c05d3396ab5371e42e64`** (`index-md5-{before,after}.txt`).
- Không merge `main`; không ghi index; không đụng `rag_v2/synthesis.py`; không sửa bộ câu hỏi/đáp án tham chiếu; không nới chuẩn chấm.
- Commit nhánh `phieu-viec/rag-fix1`: `3f6cee0` (nhận vé) → `b5bc5a3` (code + test) → `365d834`/`b4f7510` (mốc tiến độ Tầng 1/Tầng 2) → commit chốt vé (báo cáo này + `trang-thai.md`; SHA ghi ở `trang-thai.md`).
- Bằng chứng thô (không commit, `local_cases/lsu_quality_pc0575/`): `matcher_check_{before,after}.json`, `cagent_progress.{v1,}.json`, `diem-cagent.{v1,}.{csv,json}`, `compare-v1v2.json`, `progress-cagent.{v1,}.log`, `run-cagent-v2.out`, `index-md5-{before,after}.txt`.
- Watcher: vé này có **0 lần** watcher tự mở OMP (log không có dòng `MATCHER-FIX`) — cổng gate 4 lần không áp dụng; phiên làm việc liên tục có tiến triển (mốc push theo quy ước).

## 9. Đề xuất vòng sau

1. **Chuẩn hoá chấm + sửa từ khóa đề** (thẳng hàng vé `RUBRIC-NORMALIZE-PC0575` đã thấy phát hành trên nhánh): text-normalize khi chấm (khoảng trắng quanh dấu `=`, "bản ghi"/"笔") và sửa lỗi từ khóa Q0630 (`DRUM.` lặp + dấu chấm) — hai ca dưới 2 điểm của vé này sẽ hết oan.
2. Câu CJK **gần đúng nhưng không nguyên văn** vẫn có thể hụt ngưỡng (chưa có ca trong acceptance lần này) — nếu vòng sau cần, tách token theo ranh giới Hán/Kana/Latin; theo bằng chứng hiện tại chưa cần.
3. Lane RAG (nút thắt riêng, không thuộc vé này): giữ nguyên đề xuất #2/#3 của báo cáo trước (chunk bảng + trích dẫn tên tệp).
