# Báo cáo vé UX-INTERVIEW-UI — Phase A [VM] (nối UI vào backend, không sửa backend)

Ngày: 2026-10-03 ~17:00 +07. Người làm: Muse (VM). Lane tiếp: [NHÀ] OMP verify trên app thật.
Phương án UI đã được user gật 2026-10-03 ~16:10 (mục 5 của `ux-interview-feedback.md`).

## 1. Đã code gì (file, hàm)

**Mới: `src/aios_habit/chat_interview_ui.py`** — lớp nối UI vào backend (không sửa backend):

- Marker trong markdown câu trả lời (theo đúng pattern thẻ đính kèm có sẵn):
  `interview_marker()` / `suggestion_marker()` để nhúng, `extract_*` để đọc,
  `strip_interactive_markers()` để ẩn marker khi render chữ.
- `InterviewSessionStore` — sổ phiên trong bộ nhớ (giới hạn 20 phiên, tự loại
  phiên cũ nhất). Đáp án vẫn chỉ ghi vào staging sqlite khi hoàn thành, đúng
  backend cũ.
- `build_answer_payload()` — gom giá trị các ô nhập thành payload GoldenAnswer;
  các trường truy vết (mã lỗi, gap, case) backend tự điền sẵn nên UI chỉ hỏi
  phần nội dung điều tra: nội dung điều tra, giả thuyết nguyên nhân, cơ chế
  gây lỗi, nhóm 4M, bằng chứng cần thu thập, tiêu chí xác nhận (+ ô "cách phân
  biệt với giả thuyết khác" khi câu hỏi loại discriminator).
- `submit_interview_answer()` — gọi `answer_question` của backend; đáp án thiếu
  ý thì trả về False kèm câu nhắc "⚠️ Còn thiếu phần nguyên nhân / bằng chứng
  — bổ sung rồi gửi lại nhé" (không cho qua); hết câu thì gọi
  `complete_session()` và báo "✅ Đã lưu nháp chờ duyệt".
- `render_interview_widget(st, session_id)` — vẽ câu hỏi hiện tại + các ô trả
  lời + nút "Gửi đáp án" ngay dưới câu hỏi (không chuyển màn hình).
- `emit_suggestion_card()` — log gợi ý (không trùng lặp) và trả markdown thẻ
  gợi ý kèm marker; nếu tình huống giống lỗi từng bị chê thì **chèn trước**
  một dòng "💡 Lưu ý: tình huống này từng bị chê vì … — cách đúng là …".
- `save_suggestion_feedback()` — gọi `record_feedback_strict`; thiếu 3 trường
  khi chê thì chặn ngay tại chỗ nhập. Khi chê "sai"/"một phần", vòng cải thiện
  chạy ngầm: tạo bài học (`lesson_from_suggestion_feedback` + `LessonStore`)
  và ghi sự kiện lặp lại (`record_repetition_event`).
- `render_suggestion_widget(st, suggestion_id)` — 3 nút nhỏ 👍 Đúng / 😐 Một
  phần / 👎 Sai dưới mỗi gợi ý; bấm "Một phần"/"Sai" thì hiện ngay 3 ô
  (lý do, nguyên nhân thật, nắn lại thế nào), bắt buộc đủ 3 ô mới lưu.
- `repetition_metric_line()` — một dòng "📉 Tỉ lệ lặp lại lỗi: … — xu hướng …".

**Mới: `src/aios_habit/chat_action_interview_chat.py`** — action
`phien_phong_van_chat` (lệnh "mở phiên phỏng vấn F000"): lấy mã lỗi trong câu,
tra ca lỗi thật (chỉ đọc), dựng PhenomenonContext, `start_session()`, trả
markdown kèm marker để UI vẽ widget. Không có mã thì hỏi lại mã lỗi.

**Sửa:**

- `src/aios_habit/chat_action.py` — đăng ký action mới (đứng trước fallback
  tra cứu mã lỗi; hint không giao với action phỏng vấn cũ chỉ-đọc).
- `src/aios_habit/workspace_chat_ui.py` — `render_chat_bubble` đọc marker,
  ẩn marker khỏi chữ, vẽ widget phỏng vấn + widget chấm gợi ý ngay trong bong
  bóng chat (trước hàng feedback có sẵn).
- `src/aios_habit/chat_action_next_actions.py` — mỗi gợi ý "việc nên làm"
  thành một thẻ gợi ý có nút chấm (giữ nguyên bảng cũ, chỉ thêm thẻ bên dưới;
  log gợi ý vào `local_cases`, không vào kho tri thức).
- `src/aios_habit/chat_action_suggestion_review.py` — báo cáo vòng cải thiện
  thêm dòng metric "tỉ lệ lặp lại lỗi".

## 2. Test

`tests/test_chat_interview_ui.py` — **24/24 pass** (st được giả lập):

- Marker nhúng/đọc/xóa đúng; sổ phiên giới hạn 20.
- Đáp án thiếu → bị nhắc "Còn thiếu", không ghi; đáp án đủ → qua câu tiếp;
  trả lời hết → "Đã lưu nháp chờ duyệt", phiên rời khỏi bộ nhớ.
- Widget vẽ đúng: câu hỏi hiện tại + 5 ô text + 1 multiselect 4M (+ ô phụ khi
  câu discriminator) + nút gửi; bấm gửi thiếu → cảnh báo tại chỗ, không rerun.
- Thẻ gợi ý log đúng 1 lần; tình huống giống lỗi đã bị chê → dòng "💡 Lưu ý"
  đứng trước gợi ý.
- Bấm "Sai" → hiện 3 ô; lưu thiếu ô → chặn "⚠️"; đủ 3 ô → ghi nhận + tạo bài
  học + sự kiện metric. Bấm "Đúng" → ghi ngay.
- Action mới match đúng lệnh, không đụng action cũ; thẻ gợi ý được thêm vào
  action việc-tiếp-theo mà bảng cũ vẫn nguyên (test cũ không vỡ).

## 3. Xác minh tối thiểu (VM)

- `compileall src tests`: OK.
- `pytest` các test liên quan (interview_ui, agent_report_artifact, chat_action,
  interview_feedback_loop, suggestion_feedback, chat_action_agent_report,
  workspace_chat_ui_copy): **đỗ hết**.
- `cli audit`: `"status": "PASS"`.
- `import aios_habit.workspace_chat_app`: được.
- Không ghi index production; dữ liệu test dùng `AIOS_LOCAL_CASES_DIR` tạm.

## 4. OMP cần verify [NHÀ] trên app thật

1. Mở app, gõ "mở phiên phỏng vấn F000" (mã lỗi thật trong kho): thấy phiên
   mở ra, **câu hỏi 1 hiện kèm các ô trả lời ngay dưới**, không chuyển màn hình.
2. Gửi đáp án thiếu (bỏ trống cơ chế gây lỗi): app **nhắc "Còn thiếu phần
   nguyên nhân / bằng chứng"** và không qua câu mới.
3. Điền đủ → qua câu 2; trả lời hết các câu → app báo **"Đã lưu nháp chờ duyệt"**;
   kiểm tra file `local_cases/staging_enrichment.sqlite` có đáp án mới,
   `reviewer_status` là `cho_chuyen_gia_phan_hoi`.
4. Gõ "tiếp theo nên làm gì?" (mở sổ tri thức trước): mỗi gợi ý có **3 nút**
   👍/😐/👎; bấm 👎 → hiện 3 ô; bỏ trống 1 ô rồi lưu → bị chặn; điền đủ → ghi nhận.
5. Chê 1 gợi ý "sai", rồi hỏi lại việc tương tự: thấy dòng **"💡 Lưu ý: tình
   huống này từng bị chê vì …"** đứng trước gợi ý.
6. Gõ "báo cáo cải thiện gợi ý": thấy dòng **"📉 Tỉ lệ lặp lại lỗi"**.
7. Ghi SHA index production trước/sau (phải không đổi), rồi `xong-cho-duyet`.

## 5. Giới hạn đã biết (không chặn verify)

- Phiên phỏng vấn sống trong bộ nhớ tiến trình app: restart app thì phiên đang
  dở mất (đáp án đã gửi từng câu vẫn nằm trong bộ nhớ phiên, chưa vào staging
  cho tới khi hoàn thành).
- `select_top_k` có ràng buộc cứng (≥1 câu discriminator, phủ 4M) nên số câu
  thực tế có thể nhiều hơn số yêu cầu.
