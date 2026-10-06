# Vé RAG-LANE-INVESTIGATE-HOME — Điều tra lane RAG máy nhà: gốc 21 câu gói bằng chứng rỗng + 29 lượt tổng hợp lỗi, đo lại 50 câu

- Vé: `RAG-LANE-INVESTIGATE-HOME` (prompt `docs/phieu-viec/mailbox/prompt.md`).
- Máy: nhà `h410asrock`, user `Vinh`. Điều tra trong phiên 02:08–03:17 +07 ngày 07/10; lượt đo chính thức 03:05:10–03:17:03 +07.
- Trạng thái: **XONG 50/50, 0 lỗi kỹ thuật.** Sửa ở mức **runner/env** (ngoài Git) đúng phạm vi vé; không sửa logic lõi, không ghi index, không merge `main`.
- Nguồn vé: báo cáo `docs/phieu-viec/ket-qua/lsu-quality-rag-home.md` §6–§7.

## 1. Tóm tắt kết quả

| Chỉ số | Lượt này (FIX1) | Lượt fallback trước | C-Agent PC0575 (đối chiếu) |
|---|---|---|---|
| Tổng /150 | **64,5** | 37,68 | 108,2 |
| GPA (/3) | **1,29** | 0,75 | 2,16 |
| Câu đạt ≥2 | **8/50 (16%)** | 3/50 (6%) | 35/50 (70%) |
| Câu =3 | **5/50 (10%)** | 3/50 (6%) | 33/50 (66%) |
| Lỗi kỹ thuật | **0/50** | 0/50 | 0/50 |

- **Gốc lỗi A đã tìm ra và sửa (mức runner):** 21 câu gói rỗng do runner cũ đi đường lexical thuần,
  tokenizer `_TOKEN_RE=[\w]+` gộp chuỗi CJK (Nhật/Trung) không dấu cách thành 1 token dài → 0 mảnh.
  Chuyển sang `hybrid_search_with_summary`: **50/50 câu đều có gói mảnh (0 gói rỗng)**; câu Q0699
  (0 mảnh trước) nay 26 mảnh trả về (fusion 25) / gói 8 mảnh — khớp pilot PC0575 (26 item).
- **Gốc lỗi B đã tìm ra và sửa (mức runner):** runner cũ lọc `provider_id == "gemini"` nên gọi thẳng
  cloud Google bằng khóa `.env` → khóa bị `rate_limited` (bắt được log thật). Chuyển sang provider
  `openai_compatible_local` qua cầu `127.0.0.1:8585`: **69 lượt gọi, 0 lỗi mạng** trong suốt lane.
- **Điểm nghẽn mới (thuộc logic lõi → dừng ở đề xuất, §9):** cầu trả lời được nhưng chỉ **6/50 câu
  qua được kiểm định nội dung** của pipeline (`provider_validated` 4 + `provider_validated_after_repair` 2);
  42 câu rớt về trích cục bộ (`provider_validation_failed`), 2 câu ABSTAIN fail-closed.
  Vì vậy GPA 1,29 chủ yếu vẫn đo retrieval + trích cục bộ, chưa đạt kỳ vọng "đa số tổng hợp cloud thành công" của vé.

## 2. Gốc lỗi A — 21/50 câu gói bằng chứng rỗng

**Triệu chứng lượt trước:** 21 câu `provider_not_called` (0 điểm), trong đó:
- 17 câu gói **0 mảnh** (bằng chứng rỗng thật sự);
- 4 câu có mảnh (bc=8) nhưng bị ABSTAIN: `Q0632, Q0635, Q0709, Q0864`.

**Tái hiện ở mức runner (cùng index, cùng câu Q0699):**
- Đường cũ `search_with_summary` (lexical thuần): **0 mảnh**, lý do `no_lexical_or_metadata_match`
  (log runner điều tra 02:40).
- Đường `hybrid_search_with_summary` (dense+sparse+lexical): **26 mảnh trả về** (`returned_count`
  sau fusion = 25; nhánh intent `general` ghép thêm 1 chunk tóm tắt tài liệu), gói 8 mảnh — khớp
  pilot PC0575 cùng câu (26 item, retrieval 198,4s).

**Gốc rễ:**
- Runner cũ gọi `pipe.index.search_with_summary(...)` (`do_rag_50.py:175`) — đường lexical thuần.
- Tokeniser `_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)` (`query_planning.py:16`; bản dùng chung ở
  `index.py:53`) cắt theo khoảng trắng/`\w`; câu Nhật/Trung không dấu cách bị gộp thành **một token lai
  duy nhất** — Q0699: `extract_content_terms` trả đúng 1 token 35 ký tự
  `c7620中magenta相对black的副扫描色差达到多少会成为ng`.
- Đường quét lexical CJK lọc trước bằng `LIKE` theo **1–2 token dài nhất** (`_cjk_like_prefilter_rows`,
  `index.py:4161`); token lai trên không trùng nguyên chuỗi trong chunk nào → prefilter trả **0 hàng**
  (`like_prefilter_ms` chạy, `score_candidate_calls=0`) → `candidate_count=0` →
  `no_lexical_or_metadata_match` → gói rỗng. Đây là lý do 8 câu thuộc nhóm staging-khớp vẫn rỗng —
  tức nguyên nhân **độc lập** với matcher staging.

**Phân biệt 2 cơ chế (theo yêu cầu vé, không gộp):**
- **(a) Matcher staging loại câu** (`wire_qa_staging.py`, `MIN_MATCH_SCORE=3.0`, kho 3.392 cặp):
  tái lập đúng 12 câu không khớp (danh sách §5). Đây là cơ chế chọn cặp tham khảo cho lane C-Agent —
  **không phải** nguyên nhân gói rỗng của lane RAG.
- **(b) Retrieval toàn kho không trả mảnh:** thủ phạm là đường lexical bị tokenizer CJK chặn (trên).
  Trong 21 câu not_called lượt trước: 11 thuộc nhóm staging-không-khớp, 10 thuộc nhóm khớp;
  trong 17 câu rỗng hẳn: 9 không khớp / **8 khớp** — khẳng định (b) không phụ thuộc (a).

**Sửa (trước/sau, mức runner — không đụng `src/`):**

| Hạng mục | Trước (`do_rag_50.py`) | Sau (`do_rag_50_fix1.py`) |
|---|---|---|
| Đường retrieval | `search_with_summary` (lexical thuần) | `hybrid_search_with_summary` (dense+sparse+lexical; câu CJK được nới `limit` 15→25) |
| Gói bằng chứng | 21 câu rỗng / abstain | **50/50 câu có mảnh** (bc 5–25); còn đúng 2 câu ABSTAIN fail-closed (Q0824, Q0828 — §6) |

Ghi chú điều kiện pilot: **không cần** hạ `strict_semantic`/2 cổng vân tay như pilot — hybrid mặc định
đã trả 26 mảnh (fusion 25) bằng pilot (26 item; pilot chậm 198,4s vì hạ cổng). Ghi rõ để Muse đối chiếu điều kiện.

## 3. Gốc lỗi B — 29/29 lượt tổng hợp cloud lỗi

**Triệu chứng lượt trước:** 29/29 lượt `RouterSynthesisProvider` lỗi, dù gọi thử cầu `8585` đạt 2,7s
trước khi đo.

**Bắt lỗi thật (không đoán):** lượt gọi đại diện qua script bắt lỗi ngoài Git (`bat_loi_provider.py`,
02:13:56) trả về:
- `WARNING … All synthesis providers failed: gemini:failed(rate_limited)`
- `RuntimeError: All synthesis providers failed (terminal=local_renderer, attempts=1)` — lỗi sau 0,59s.

**Gốc rễ:** runner cũ lọc `provider_configs_from_env()` theo `provider_id == "gemini"` (`do_rag_50.py:128`)
→ gọi thẳng cloud Google bằng khóa `.env`, **không đi qua cầu** `127.0.0.1:8585`; khóa cloud bị
rate-limit nên mọi lượt đều rớt về trích cục bộ.

**Sửa (trước/sau, mức runner — không đụng `src/`):**

| Hạng mục | Trước | Sau |
|---|---|---|
| Provider tổng hợp | `gemini` trực tiếp (khóa `.env`) | `openai_compatible_local` → cầu `http://127.0.0.1:8585/v1/chat/completions` (ghim trong runner, ghi đè `.env`), model `gemini-2.5-flash` |
| Kết quả | 29/29 lượt `rate_limited` | **69 lượt gọi, 0 lỗi mạng**; không lượt nào có `provider_network_error`; không cảnh báo "All synthesis providers failed" trong suốt lane |

## 4. Bộ ghi bằng chứng của runner (mức runner, ngoài Git)

Để lượt đo có bằng chứng từng câu (phục vụ chính vé này), runner `do_rag_50_fix1.py` ghi thêm mỗi hàng:
`limitation_reasons`, `so_ket_qua`/`so_ung_vien`/`ly_do_thieu` (từ `SearchSummary`),
`nhat_ky_provider` (cảnh báo của `RouterSynthesisProvider`), và bộ bọc provider ghi lại **từng lượt gọi**:
lỗi validation thô, cờ lượt sửa, độ dài + 300 ký tự đầu câu trả lời. Không thay đổi logic đo.

## 5. Đo lại 50 câu (lượt chính thức, CPU-only)

- Thời gian: index trước 03:05:10 → khởi tạo pipeline 2,4s → preload dense 121.331 chunk (2,9s)
  + sparse 121.331 chunk (12,2s) → câu 1 lúc 03:05:38 → câu 50 lúc 03:16:39 → kiểm index sau 03:17:03.
- Retrieval tổng **379,3s** (TB 7,59s/câu) + tổng hợp tổng **291,7s** (TB 5,83s/câu) + tổng câu
  **671,2s** (TB 13,42s; nhanh nhất Q0824 7,12s; chậm nhất Q0700 35,16s).
- 69 lượt gọi provider (TB 1,38/câu; 21 lượt là gọi sửa).
- Tách theo staging khớp/không khớp (cùng định nghĩa, tái lập bằng `select_relevant_pairs`,
  `MIN_MATCH_SCORE=3.0`, kho 3.392 cặp):

| Nhóm | Số câu | Lượt này | Lượt fallback trước | C-Agent PC0575 |
|---|---|---|---|---|
| Staging khớp | 38 | tổng 49,17 GPA **1,294** (≥2: 6; =3: 4) | tổng 34,68 GPA 0,913 | GPA 2,78 |
| Staging không khớp | 12 | tổng 15,33 GPA **1,278** (≥2: 2; =3: 1) | tổng 3,0 GPA 0,25 | GPA 0,21 |

- 12 câu không khớp: `Q0703, Q0851, Q1034, Q0685, Q0688, Q0632, Q0635, Q0693, Q0696, Q1827, Q0705, Q0684`.
- Đổi điểm so lượt trước: **25 câu tăng / 2 câu giảm / 23 câu giữ nguyên**. Tăng mạnh: `Q0693 0→3`,
  `Q0689 1→3`, `Q0695 1→3`, `Q0703 0→2,33`; giảm: `Q1827 3→1`, `Q0828 1→0` (lý do ở §6).
- Chi tiết từng câu (giây: tìm = retrieval, tổng hợp, câu = cả câu; `bc` = số mảnh bằng chứng;
  `KQ` = `returned_count` sau fusion — mảnh tóm tắt ghép thêm không tính, xem §2):

| STT | ID | Điểm | Trích | Tìm | Tổng hợp | Câu | bc | KQ | Chế độ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Q0699 | 1 | có | 6,81 | 4,28 | 11,09 | 8 | 25 | `local_extractive_provider_fallback` |
| 2 | Q0700 | 1 | có | 6,7 | 28,45 | 35,16 | 8 | 25 | `provider_validated` |
| 3 | Q0703 | 2,33 | có | 4,89 | 3,39 | 8,28 | 8 | 25 | `provider_validated` |
| 4 | Q0708 | 1 | có | 7,91 | 4,74 | 12,64 | 8 | 25 | `local_extractive_provider_fallback` |
| 5 | Q0849 | 1 | có | 8,8 | 3,86 | 12,67 | 8 | 15 | `local_extractive_provider_fallback` |
| 6 | Q0850 | 1 | có | 6,81 | 7,09 | 13,91 | 8 | 15 | `local_extractive_provider_fallback` |
| 7 | Q0851 | 1 | có | 5,95 | 3,84 | 9,81 | 8 | 15 | `local_extractive_provider_fallback` |
| 8 | Q1029 | 1,5 | có | 6,89 | 7,86 | 14,75 | 8 | 15 | `local_extractive_provider_fallback` |
| 9 | Q1034 | 1 | có | 6,84 | 6,84 | 13,69 | 8 | 15 | `local_extractive_provider_fallback` |
| 10 | Q0620 | 1 | có | 7,88 | 4,08 | 11,95 | 8 | 15 | `local_extractive_provider_fallback` |
| 11 | Q0621 | 1 | có | 12,64 | 4,47 | 17,12 | 5 | 25 | `local_extractive_provider_fallback` |
| 12 | Q0824 | 0 | không | 7,11 | 0 | 7,12 | 8 | 25 | `local_extractive_provider_not_called` |
| 13 | Q0689 | 3 | có | 9,75 | 4,44 | 14,19 | 7 | 15 | `local_extractive_provider_fallback` |
| 14 | Q0704 | 1 | có | 8,5 | 3,03 | 11,53 | 8 | 15 | `local_extractive_provider_fallback` |
| 15 | Q0701 | 1 | có | 7,42 | 7,94 | 15,36 | 6 | 15 | `local_extractive_provider_fallback` |
| 16 | Q0718 | 1 | có | 8,76 | 4,03 | 12,81 | 8 | 15 | `local_extractive_provider_fallback` |
| 17 | Q0828 | 0 | không | 15,11 | 0 | 15,11 | 5 | 25 | `local_extractive_provider_not_called` |
| 18 | Q0858 | 1 | có | 7,09 | 4,72 | 11,81 | 8 | 15 | `local_extractive_provider_fallback` |
| 19 | Q0685 | 1 | có | 6,45 | 4,08 | 10,53 | 7 | 25 | `provider_validated` |
| 20 | Q0688 | 1 | có | 4,67 | 6,67 | 11,34 | 8 | 25 | `provider_validated_after_repair` |
| 21 | Q0695 | 3 | có | 9,27 | 4,62 | 13,91 | 8 | 15 | `local_extractive_provider_fallback` |
| 22 | Q0632 | 1 | có | 7,34 | 8,06 | 15,41 | 8 | 25 | `local_extractive_provider_fallback` |
| 23 | Q0635 | 1 | có | 10,42 | 8,53 | 18,95 | 8 | 25 | `local_extractive_provider_fallback` |
| 24 | Q0636 | 2,33 | có | 6,97 | 7,34 | 14,31 | 8 | 15 | `local_extractive_provider_fallback` |
| 25 | Q1798 | 1 | có | 7,72 | 4,31 | 12,03 | 8 | 15 | `local_extractive_provider_fallback` |
| 26 | Q0671 | 1 | có | 13,52 | 6,75 | 20,28 | 8 | 25 | `provider_validated_after_repair` |
| 27 | Q0674 | 2,33 | có | 6,27 | 7,33 | 13,62 | 8 | 15 | `local_extractive_provider_fallback` |
| 28 | Q0677 | 1 | có | 7,72 | 6,38 | 14,11 | 8 | 15 | `local_extractive_provider_fallback` |
| 29 | Q0706 | 1 | có | 6 | 4,86 | 10,91 | 8 | 25 | `local_extractive_provider_fallback` |
| 30 | Q0707 | 1 | có | 6,47 | 7,19 | 13,66 | 6 | 15 | `local_extractive_provider_fallback` |
| 31 | Q0693 | 3 | có | 6,69 | 2,97 | 9,66 | 8 | 15 | `provider_validated` |
| 32 | Q0696 | 1 | có | 5,72 | 8,95 | 14,67 | 8 | 25 | `local_extractive_provider_fallback` |
| 33 | Q0633 | 1,67 | có | 7,84 | 9,09 | 16,95 | 8 | 15 | `local_extractive_provider_fallback` |
| 34 | Q0787 | 1 | có | 8,67 | 4,23 | 12,91 | 8 | 15 | `local_extractive_provider_fallback` |
| 35 | Q1777 | 3 | có | 10,64 | 7,61 | 18,25 | 8 | 15 | `local_extractive_provider_fallback` |
| 36 | Q1827 | 1 | có | 12,81 | 8,09 | 20,91 | 25 | 25 | `local_extractive_provider_fallback` |
| 37 | Q2157 | 1 | có | 5,52 | 3,59 | 9,11 | 8 | 15 | `local_extractive_provider_fallback` |
| 38 | Q0662 | 1 | có | 6,42 | 3,66 | 10,09 | 8 | 15 | `local_extractive_provider_fallback` |
| 39 | Q0665 | 1 | có | 6,22 | 3,83 | 10,05 | 8 | 15 | `local_extractive_provider_fallback` |
| 40 | Q0668 | 1 | có | 6,03 | 8,61 | 14,64 | 8 | 15 | `local_extractive_provider_fallback` |
| 41 | Q0705 | 1 | có | 7,34 | 4,38 | 11,72 | 8 | 25 | `local_extractive_provider_fallback` |
| 42 | Q0709 | 1 | có | 5,72 | 8,16 | 13,88 | 8 | 15 | `local_extractive_provider_fallback` |
| 43 | Q0843 | 1 | có | 6,22 | 7,8 | 14,02 | 8 | 15 | `local_extractive_provider_fallback` |
| 44 | Q0864 | 1 | có | 5,19 | 4,14 | 9,33 | 8 | 15 | `local_extractive_provider_fallback` |
| 45 | Q0680 | 3 | có | 7,26 | 5,66 | 12,92 | 8 | 15 | `local_extractive_provider_fallback` |
| 46 | Q0684 | 1 | có | 6,92 | 4,7 | 11,62 | 8 | 15 | `local_extractive_provider_fallback` |
| 47 | Q0924 | 1 | có | 6,48 | 4,06 | 10,55 | 8 | 15 | `local_extractive_provider_fallback` |
| 48 | Q0630 | 1 | có | 6,08 | 6,36 | 12,44 | 8 | 15 | `local_extractive_provider_fallback` |
| 49 | Q0652 | 1,67 | có | 6,28 | 3,23 | 9,51 | 8 | 15 | `local_extractive_provider_fallback` |
| 50 | Q0658 | 1,67 | có | 6,56 | 3,39 | 9,95 | 8 | 15 | `local_extractive_provider_fallback` |

## 6. Phát hiện mới khi đo lại — kiểm định nội dung chặn phần lớn câu trả lời cloud

- Qua kiểm định: **6/50 câu** — `provider_validated`: Q0700, Q0703, Q0685, Q0693;
  `provider_validated_after_repair`: Q0688, Q0671 (tổng điểm 6 câu này: 9,33/150).
- Rớt về trích cục bộ: **42/50 câu**, tất cả đều `provider_validation_failed`,
  **không câu nào lỗi mạng** (không có `provider_network_error`) → lỗi B đã hết ở tầng vận chuyển.
- ABSTAIN fail-closed: **2 câu** — Q0824, Q0828. Probe chỉ-đọc xác nhận lý do cứng:
  Q0824 `no_direct_query_evidence`; Q0828 `no_target_query_evidence`, `no_direct_query_evidence`,
  `final_evidence_query_coverage_below_threshold` (gói có 5–8 mảnh, không rỗng).
- Lỗi validation thô đếm theo **69 lượt gọi** (gồm lượt sửa): `uncited_material_claim` 65;
  `missing_citations` 55; `claim_budget_exceeded` 31; `unsupported_critical_literal` 24;
  `missing_required_facet_citation` 2; `language_conformance_failed` 1.
- Cơ chế (`src/aios_habit/rag_v2/synthesis.py`): khi **toàn bộ** lỗi nằm trong tập "cắt được dòng"
  → cắt các dòng lỗi rồi kiểm lại (tối đa 4 lượt); khi **toàn bộ** lỗi nằm trong tập "sửa được"
  → gọi thêm 1 lượt sửa; còn lại → rớt fallback. Ví dụ Q0699 có lỗi phối hợp
  {`missing_citations`, `claim_budget_exceeded`, `uncited_material_claim`, `unsupported_critical_literal`}:
  vừa không đủ điều kiện cắt-dòng, vừa không đủ điều kiện sửa (`unsupported_critical_literal` không nằm
  trong tập repairable) → rớt thẳng fallback. Trong lane có 21 lượt gọi sửa; 2 lượt kết thúc đạt.
- Hệ quả điểm: 9,33 điểm thuộc 6 câu cloud đạt; **55,17 điểm còn lại thuộc 44 câu fallback/abstain** —
  GPA 1,29 chủ yếu vẫn là retrieval + trích cục bộ.
- Biến động cần Muse biết: `Q0828` 1→0 (nay ABSTAIN fail-closed do cổng phủ truy vấn);
  `Q1827` 3→1 (trước đạt 3 nhờ fallback giữ nguyên giá trị `--`, nay 1).

## 7. Bằng chứng CPU-only + index chỉ-đọc (khóa cứng theo vé)

- `CUDA_VISIBLE_DEVICES=""`, `AIOS_RETRIEVAL_DEVICE=cpu` (ghim từ đầu runner; log
  `pipeline: profile=bge_m3_hybrid device=cpu strict=True`). Backend nhúng ghim cứng
  `providers=["CPUExecutionProvider"]` (`src/aios_habit/rag_v2/bge_onnx_backend.py`); máy không có
  provider CUDA trong `onnxruntime`.
- Index: `C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`,
  pipeline mở `read_only=True` (assert tên file + assert đường resolve khớp trong runner).
- Trước đo: 2.942.201.856 byte, SHA-256 `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`
  (khớp ghim gốc), md5 `239009676829484049738866329de9f2`.
- Sau đo: SHA **khớp 100%**, md5 khớp, size không đổi → **không ghi index**
  (log: `index sau: … sha_khop=True md5_khop=True (chi doc: True)`).

## 8. Checkpoint, lịch sử lượt chạy, heartbeat

- Runner `C:/tmp/lsu-quality-rag-home/do_rag_50_fix1.py` (ngoài Git) — checkpoint từng câu
  `rows-fix1.jsonl` (50 hàng, resume được khi đứt).
- Lịch sử: phiên trước đứt sau 2 câu (02:53, `rows-fix1-lan0.jsonl` — nguyên nhân: phiên OMP bị đóng
  giữa chừng, watcher tự mở lại 02:54); lượt lan1 dừng ở 6 câu khi nâng cấp bộ ghi (`rows-fix1-lan1.jsonl`);
  lượt chính thức 50/50 là `rows-fix1.jsonl`.
- Heartbeat mailbox: 02:27 nhận lại vé (cổng MỞ) → 02:35/02:40/02:45 điều tra → 02:50 bắt đầu đo →
  03:08/03:17/03:19 resume + nâng cấp bộ ghi + xong lane (2 mốc ghi lệch giờ máy vài phút do gõ tay,
  đã đính chính trong `trang-thai.md`).
- Phiên chốt báo cáo (từ 03:24 07/10): kiểm chứng độc lập lại toàn bộ số liệu từ dữ liệu thô — 50/50
  hàng khớp bảng §5, staging 38/12 khớp, đối chiếu lượt trước 25/2/23 khớp; chạy lại 3 probe chỉ-đọc:
  lexical Q0699 0 kết quả + `no_lexical_or_metadata_match`, hybrid 26 mảnh (fusion 25)/gói 8,
  ABSTAIN Q0824 `no_direct_query_evidence` + Q0828 3 lý do cứng — khớp §2/§6.
- Bộ câu + rubric: như vé trước — `cau-hoi-50.json` (50/50 có keywords, 50/50 yêu cầu trích dẫn),
  rubric `chinh_xac` 2.0 + `trich_dan` 1.0 (thang 0–3/câu), giống PC0575.

## 9. Đề xuất (chạm logic lõi — DỪNG, chờ Muse quyết)

1. **Nâng tỷ lệ qua kiểm định** (điểm nghẽn chính, §6): xem xét trong `src/aios_habit/rag_v2/synthesis.py`
   hướng xử lý **phối hợp** — khi câu trả lời vướng cả lỗi "cắt được dòng" lẫn lỗi khác thì thử cắt-dòng
   trước rồi mới xét sửa; và/hoặc bổ sung `provider_answer_unsupported_critical_literal` vào luồng sửa
   (cân nhắc: `synthesis.py:116` ghi hard stop này là chủ ý — sửa literal dễ sinh bịa nguồn);
   và/hoặc siết contract prompt (lỗi `claim_budget_exceeded` xuất hiện 31 lượt). Chỉ đề xuất — không tự sửa.
2. `max_attempts=1` và `timeout=120s` **giữ nguyên** suốt lượt đo này; nếu Muse muốn thử cấu hình khác cho
   lượt sau thì ghi rõ trước/sau và đo lại.
3. 12 câu staging-không-khớp nay hết bất lợi điểm số (GPA 1,278 ≈ nhóm khớp 1,294) nhờ hybrid retrieval;
   nếu muốn nâng recall của matcher staging (`MIN_MATCH_SCORE`) thì nên mở vé riêng, ngoài phạm vi vé này.
4. `Q0828`/`Q1827` biến động như ghi ở §6 — đề nghị ghi nhận khi đối chứng, không tự vá trong vé này.

## 10. Rào cứng

- Không sửa code repo: mọi thay đổi là runner/probe **ngoài Git** (`C:/tmp/lsu-quality-rag-home/`),
  không đụng `src/`, `tests/`.
- Không ghi index (mục 7); không merge `main` (mọi commit trên `phieu-viec/rag-fix1`).
- Dữ liệu thô ở lại máy nhà, không commit (toàn bộ trong `C:/tmp/lsu-quality-rag-home/`):
  `rows-fix1.jsonl`, `rows-fix1-lan0.jsonl`, `rows-fix1-lan1.jsonl`, `ket-qua-fix1.json`,
  `tien-trinh-fix1.log`, `phan-tich-fix1.txt`, `bang-50-cau.md`, `do_rag_50_fix1.py`, `do_rag_50.py`,
  `phan_tich_fix1.py`, `thu_fix1.py`, `thu_hybrid_q0699.py`, `chan_doan_q0699.py`,
  `thu_abstain_2cau.py`, `bat_loi_provider.py`, `loi-provider.log`, `thu-hybrid-21.json`.
- Bộ câu là bản thảo (`lsu-quality-set.md` ghi `BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT`).
