# Báo cáo vé UX-INTERVIEW-FEEDBACK — Phase A [VM] (backend items 1–3)

Ngày: 2026-10-03 ~14:30 +07. Người làm: Muse (VM). Lane tiếp: [NHÀ] OMP verify trên app thật.

## Tóm tắt

Đã code xong backend cho cả 3 items, 23/23 test mới pass, `compileall` OK, không đụng
DB/index production, code tương thích Python 3.11. **Item 4 (UI trong chat) CHƯA code**
— phương án UI ở mục 5 bên dưới, chờ user gật mới làm.

## 1. Đã code gì (file, hàm)

### Item 1 — Phiên phỏng vấn chuyên gia trong app: `src/aios_habit/expert_interview_session.py` (mới)

Tái dùng 100% bộ sinh deterministic của vé KNOWLEDGE-ENRICH-PILOT, không viết lại:

- `start_session(ctx, questions_per_session=3, min_score=55.0)` — nhận `PhenomenonContext`
  (gap + hiện tượng lỗi thật) → gọi `generate_candidates()` + `select_top_k()` của pilot
  (không LLM) → trả về `ExpertInterviewSession` với danh sách `GoldenQuestion` đã chấm điểm.
- `answer_question(session, question_id, answer_payload)` — đáp án đi qua validation
  `GoldenAnswer` đầy đủ: form "answered" thiếu nhân quả (giả thuyết, cơ chế, 4M) hoặc thiếu
  bằng chứng (cần thu thập gì, tiêu chí xác nhận) thì **bị từ chối** ngay; UI chỉ cần hỏi
  chuyên gia phần nội dung điều tra, các trường truy vết (mã lỗi, gap, case) tự điền sẵn.
- `unanswered_questions(session)`, `abandon_session(session)`, `session_summary(session)`
  — tiến độ phiên, thiết kế để UI chat gọi trực tiếp.
- `complete_session(session, staging_path=...)` — chỉ cho hoàn thành khi mọi câu đã có
  đáp án; ghi tất cả đáp án vào **staging duy nhất**: `local_cases/staging_enrichment.sqlite`
  (đúng convention + đúng schema + đúng cơ chế chống ghi production `assert_not_production`
  của `golden_answer_importer`), có dedup theo SHA nội dung. `reviewer_status` giữ
  `cho_chuyen_gia_phan_hoi`; không ghi DB/index production.

### Item 2 — Feedback theo từng gợi ý: `src/aios_habit/suggestion_feedback.py` (mở rộng)

Module đã có từ commit nền `07913b1` (log gợi ý, chấm đúng/sai/một phần, sai/một phần bắt
buộc đủ 3 trường, lưu `local_cases/suggestion_feedback.jsonl`, không vào kho tri thức).
Bổ sung trong vé này:

- `record_feedback_strict(...)` — biến thể **raise** `SuggestionFeedbackStrictError`
  (subclass của `ValueError`) thay vì trả `{"ok": False}`, đúng yêu cầu vé "thiếu thì từ
  chối lưu (raise ValueError rõ ràng)". Nhận cả tên trường tiếng Việt (`ly_do`,
  `nguyen_nhan_that`, `noi_dung_nan_lai`) lẫn tiếng Anh. API cũ `record_feedback` giữ
  nguyên, không vỡ test hiện có.

### Item 3 — Vòng lặp tự cải thiện: `src/aios_habit/self_improvement.py` (mới)

- `lesson_from_suggestion_feedback(feedback)` — feedback "sai"/"một phần" thành **bài học
  có truy vết**: tình huống → lỗi (lý do) → nguyên nhân thật → cách sửa (nội dung nắn lại),
  kèm `situation_fingerprint` (SHA-256 của tập từ khóa đã chuẩn hóa).
- `LessonStore` — lưu bài học append-only vào `local_cases/improvement_lessons.jsonl`
  (feedback store cục bộ, **không** ghi kho tri thức chính).
- `find_similar(situation_text, threshold=0.3)` / `consult_lessons(...)` — nhận diện tình
  huống tương tự bằng **Jaccard trên tập từ khóa** (bỏ stopword tiếng Việt, không cần
  embedding, deterministic). Lần sau gặp tình huống tương tự, UI gọi `consult_lessons`
  để nhắc "bài học đã rút ra" trước khi trả lời → không lặp lỗi cũ.
- Metric: `record_repetition_event(...)` ghi từng feedback sai/một phần kèm cờ `repeated`
  (lỗi đã có bài học mà vẫn lặp lại); `repetition_rates()` gom theo kỳ; `metric_trend()`
  trả `giam_dan` / `khong_giam` / `khong_du_du_lieu`. `improvement_overview()` cho UI
  một gói tổng quan vòng xem lại.

### Test: `tests/test_interview_feedback_loop.py` (mới, 23 test)

Bao phủ: phiên chạy trọn vòng gap → câu hỏi → đáp án → staging; form mơ hồ bị từ chối;
staging từ chối đường dẫn production; dedup; feedback đúng không cần thêm trường;
sai/một phần thiếu 3 trường raise `ValueError`; fingerprint ổn định + Jaccard; nhận diện
tình huống tương tự; **metric trên dữ liệu mẫu chứng minh tỉ lệ lặp lại lỗi giảm dần
(0.8 → 0.5 → 0.2 → 0.1 ⇒ `giam_dan`)**.

## 2. Cách dùng API (cho OMP verify ở nhà)

```python
from aios_habit.golden_question_export import fixture_phenomena  # hoặc phenomena thật từ DB
from aios_habit.expert_interview_session import (
    start_session, answer_question, unanswered_questions, complete_session,
)

ctx = ...  # PhenomenonContext: 1 hiện tượng lỗi thật + gap
session = start_session(ctx, questions_per_session=3)
for q in session.questions:
    print(q.question_id, q.text)          # hỏi chuyên gia từng câu
    answer_question(session, q.question_id, {
        "answer_text": "...",             # >= 20 ký tự
        "answer_state": "answered",        # hoặc uncertain/unknown + needs_expert_review
        "confidence": 0.8,
        "hypotheses": [...], "causal_mechanism": "...",
        "m4_branches": ["Machine"], "evidence_to_collect": [...],
        "confirm_criteria": "...",
    })
report = complete_session(session)        # ghi local_cases/staging_enrichment.sqlite
```

Feedback gợi ý + vòng cải thiện:

```python
from aios_habit.suggestion_feedback import record_feedback_strict
from aios_habit.self_improvement import (
    LessonStore, lesson_from_suggestion_feedback, consult_lessons,
    record_repetition_event, improvement_overview,
)

# Chuyên gia chê 1 gợi ý "một phần": thiếu 1 trong 3 trường -> raise ValueError
record_feedback_strict("G1", "chuyen-gia", "mot_phan",
    ly_do="...", nguyen_nhan_that="...", noi_dung_nan_lai="...")

# Lưu thành bài học; lần sau hỏi tình huống tương tự thì nhắc trước
store = LessonStore()
lesson = lesson_from_suggestion_feedback(feedback_record, situation_text="...")
store.add(lesson)
goi_y = consult_lessons("máy F100 dừng đột ngột...", store=store)

# Metric vòng lặp
record_repetition_event("G1", "mot_phan", repeated=False)
print(improvement_overview())  # xu_huong: giam_dan / khong_giam / khong_du_du_lieu
```

## 3. Kết quả kiểm chứng trên VM

- `tests/test_interview_feedback_loop.py`: **23/23 pass**.
- Các test liên quan cũ (`test_suggestion_feedback`, `test_answer_feedback`, golden pilot):
  **51/51 pass** — không vỡ API hiện có.
- Full suite: pass toàn bộ trừ 1 test `test_agent_code_worktree.py::test_e2e_code_fix_cycle`
  **đã fail sẵn trên cây sạch** (kiểm chứng bằng `git stash`), không liên quan vé này.
- `compileall` OK; không dùng f-string nhiều dòng (tương thích Python 3.11); không file
  nào ghi vào DB/index production trong test (dùng `AIOS_LOCAL_CASES_DIR` → tmp).
- `cli audit`: **PASS** (`{"status": "PASS", "errors": [], "warnings": []}`).

## 4. Việc OMP verify [NHÀ] (dữ liệu thật)

1. Chạy thử 1 phiên phỏng vấn ngắn: 1 hiện tượng lỗi thật → `start_session` →
   trả lời từng câu → `complete_session`; kiểm tra đáp án vào
   `local_cases/staging_enrichment.sqlite` đúng schema (`staging_answers`,
   `reviewer_status = cho_chuyen_gia_phan_hoi`).
2. Feedback 1 gợi ý "một phần" bằng `record_feedback_strict` kèm đủ 3 trường
   (lý do, nguyên nhân thật, nội dung nắn lại); thử thiếu 1 trường → phải raise
   `ValueError` với thông báo tiếng Việt rõ ràng.
3. Lưu feedback thành bài học (`lesson_from_suggestion_feedback` + `LessonStore`);
   hỏi lại tình huống tương tự → `consult_lessons` phải trả về bài học cũ;
   ghi 2 kỳ metric (`record_repetition_event`) → `improvement_overview`
   cho `xu_huong` hợp lý.
4. Nếu cả 3 đạt → báo `xong-cho-duyet` cho vé này.

## 5. Phương án UI đề xuất (CHỜ USER GẬT — chưa code)

Nói ngắn gọn, không kỹ thuật:

- **Phỏng vấn chuyên gia:** ngay trong khung chat, app mở một "phiên hỏi đáp" — mỗi lượt
  chat hiện **1 câu hỏi**, chuyên gia trả lời ngay dưới câu hỏi đó (không chuyển màn hình,
  không mở form riêng). Trả lời thiếu ý chính thì app nhắc ngay "còn thiếu phần nguyên
  nhân / bằng chứng" chứ không cho qua. Hết các câu, app báo "đã lưu nháp chờ duyệt".
- **Feedback từng gợi ý:** dưới mỗi gợi ý trong câu trả lời có 3 nút nhỏ: **Đúng** /
  **Một phần** / **Sai**. Bấm "Một phần" hoặc "Sai" thì ngay dưới gợi ý đó hiện 3 ô:
  *lý do*, *nguyên nhân thật*, *nắn lại thế nào* — bắt buộc điền đủ 3 ô mới lưu được,
  vẫn ở trong khung chat, không chuyển trang.
- **Vòng tự cải thiện (chạy ngầm):** khi chuyên gia đã chê một lỗi, lần sau gặp tình
  huống giống vậy, app tự nhắc một dòng nhỏ kiểu "lưu ý: lỗi này từng bị chê vì…,
  cách đúng là…" trước khi đưa gợi ý. Có một con số theo dõi "tỉ lệ lặp lại lỗi" —
  con số này phải giảm dần theo thời gian thì mới coi là vòng lặp đang chạy tốt.

Backend đã thiết kế sẵn API cho cả 3 màn hình trên (`session_summary`,
`record_feedback_strict`, `consult_lessons`, `improvement_overview`); khi user gật
phương án thì chỉ việc nối UI vào, không sửa backend.

## 6. Ghi chú kỹ thuật cho review

- Tái dùng, không viết lại: `generate_candidates`, `select_top_k`, `GoldenAnswer`,
  `init_staging_db`/`assert_not_production`/`dedup_key` (staging), `record_feedback`
  (feedback store). Không tạo cơ chế staging hay feedback store mới lạ.
- `select_top_k` có thể trả về **nhiều hơn** `k` khi cần bù đắp ràng buộc cứng
  (discriminator / bằng chứng đo được / đủ 3 nhánh 4M) — hành vi gốc của pilot, giữ nguyên;
  phiên phỏng vấn hỏi hết số câu được chọn.
- Dữ liệu vận hành (feedback, bài học, metric) nằm ở `local_cases/*.jsonl` — theo bài học
  2026-10-03, không ghi vào kho tri thức chính; nhãn `local_only` nội bộ, không commit.
- Commit: xem `git log` nhánh `phieu-viec/rag-fix1`.

## 7. Verify máy nhà (OMP, 2026-10-03 14:11 +07)

Lane [NHÀ]. Không sửa mã Phase A. Không merge `main`. Không force-push.
Watcher tự mở OMP `LAUNCH 1/4` lúc 14:04:36 (`launchStallCount=1`, chữ ký mới `||f02802f`). Điều kiện mở đã tới (mã `c7d2191`, báo cáo `b68fc17`). Không đặt `cho-muse`.

Lệch SHA: ghi chú Muse nói commit `f02802f`. SHA đó không có trên nhánh. Mã backend thật là `c7d2191`; báo cáo Phase A là `b68fc17`.

### 7.1 Phiên trên dữ liệu thật

- Nguồn: bản copy `C:/tmp/b0-dict/error_cases_dict.db` → `C:/tmp/ux-interview-feedback/error_cases_dict.copy.db`. SHA-256 gốc trước và sau: `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` (54.480.896 byte). Không mở DB gốc để ghi.
- `extract_phenomena_from_error_db` **không đọc được** DB này: cột `phenomenon` rỗng (0/15.707), không có cột nhóm lỗi, hàm báo không thấy F CALL. Đây là lệch schema máy nhà, không phải dữ liệu giả.
- OMP lấy 1 dòng thật bằng cách khác, chỉ đọc: `error_cases.id=2`, mã `error_code_i=F000`, hiện tượng lấy từ cột `investigation` (556 ký tự, SHA-256 rút gọn `a6de94113e5d`). Không dán nội dung hồ sơ vào báo cáo.
- `start_session` → 3 câu (`m4_man`, `m4_machine`, `m4_material`), phiên `IS-FF62685A`. Trả lời đủ 3 câu (nội dung đánh dấu là kiểm schema, chưa phải kết luận chuyên gia) → `complete_session`.
- Staging `C:/tmp/ux-interview-feedback/staging_enrichment.sqlite` (cùng tên `staging_enrichment.sqlite`, thư mục tách bằng `AIOS_LOCAL_CASES_DIR`, không commit): 3 dòng, cột đủ `answer_id/question_id/batch_id/payload_json/answer_sha/enrichment_label/reviewer_status/version/supersedes_answer_id/created_at`. `reviewer_status` chỉ có `cho_chuyen_gia_phan_hoi`. Nhãn `kiến thức đã được đào tạo bổ sung`. `batch_id=UX-IF-HOME-01`.
- Đường `workspace_chat.sqlite` bị `ProductionWriteRefusedError` (là `ValueError`). Đường staging thì được phép.

### 7.2 Feedback và vòng nhắc bài học

- `record_feedback_strict` chấm `mot_phan` thiếu nguyên nhân thật → `SuggestionFeedbackStrictError`, thông báo có chữ "nguyên nhân thật". Không ghi dòng nào.
- Đủ 3 trường (lý do, nguyên nhân thật, nội dung nắn lại) thì lưu 1 dòng, đủ `reason` / `true_cause` / `correction`.
- Bài học từ feedback đó. Hỏi lại tình huống cùng mã `F000` + "board điều khiển" → `consult_lessons` trả 1 bài, điểm Jaccard 0.6, có `cach_sua`. Tình huống khác (nhiệt độ buồng sấy) → 0 bài.
- Metric ghi 2 kỳ mẫu trong lúc verify (không phải số liệu nhiều tuần của xưởng): kỳ 2026-09-01 tỉ lệ 0.8, kỳ 2026-09-08 tỉ lệ 0.2, `xu_huong=giam_dan`. Cơ chế đo chạy. Chưa có chuỗi tỉ lệ thật theo thời gian vận hành.

### 7.3 Cổng và những gì chưa chạy trong app

- Python 3.11.14 (`D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe`).
- `compileall src tests`: xong, có biên dịch 3 file mới.
- `pytest` 5 file liên quan (`test_interview_feedback_loop`, `test_suggestion_feedback`, `test_golden_question_export`, `test_golden_question_schema`, `test_answer_feedback`): **65/65 pass**.
- `cli audit` với `PYTHONPATH=src`: `{"status": "PASS", "errors": [], "warnings": []}`. Lệnh trần không có `PYTHONPATH` thì thiếu module `aios_habit` vì venv chưa cài gói (máy nhà, không phải lỗi vé).
- `import aios_habit.workspace_chat_app`: được.
- Index production `local_runs/workspace_chat_rag_v2_production/.../library.sqlite`: 2.552.659.968 byte, mtime 2026-09-28 05:55:03, không đổi. DB app `C:/tmp/buoc0-deploy/error_cases_deploy.db`: 49.885.184 byte, mtime 2026-10-03 12:52:32, không đổi.
- **Chưa chạy trong khung chat.** `workspace_chat_app.py` không gọi `start_session` / `expert_interview_session`. Item 4 (UI) vẫn chờ user gật, đúng mục 5 của báo cáo Muse. Vòng phỏng vấn và feedback hiện là API, chưa phải nút trong app.

Kết luận OMP: backend items 1–3 chạy được trên 1 hiện tượng thật và đủ tiêu chí staging / 3 trường / nhắc bài học. Chưa đủ để nói "chạy được trong app" cho đến khi user gật phương án UI và có vé nối giao diện.

