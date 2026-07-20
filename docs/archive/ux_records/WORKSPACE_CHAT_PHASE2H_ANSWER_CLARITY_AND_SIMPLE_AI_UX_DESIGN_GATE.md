# WORKSPACE_CHAT_PHASE2H_ANSWER_CLARITY_AND_SIMPLE_AI_UX_DESIGN_GATE

## 1. Final recommendation and status

Final status: `PASS_READY_FOR_GEMINI_PHASE2H_ANSWER_CLARITY_IMPLEMENTATION`.

Recommended option: **Option B — một luồng hỏi AI chính, kèm công cụ kiểm tra nguồn phụ**.

Phase 2H phải bỏ khái niệm hai “chế độ trả lời”. Chỉ output từ provider/model mới được xuất hiện như một câu trả lời trong chat. Kiểm tra nguồn là một thao tác phụ, render ngoài lịch sử chat và luôn mang nhãn `AI chưa trả lời`.

Đây là thay đổi UX nhỏ nhất xử lý đúng rủi ro niềm tin:

- AI là hành động chính, dễ tìm và dễ dùng;
- local source check không còn giả dạng assistant answer;
- owner thấy số/tên nguồn trước khi gửi;
- hệ thống vẫn giữ exact-source consent, privacy block và fail-closed behavior ở phía sau;
- không đổi provider, engine, store hoặc schema.

Không cần owner quyết định thêm trước implementation. Option C/D được giữ cho giai đoạn sau.

## 2. Baseline

Audit-only baseline:

- Branch: `main`
- HEAD: `860c51cf158bc694c883d36a3425171d3e94b345`
- `origin/main`: `860c51cf158bc694c883d36a3425171d3e94b345`
- Commit: `860c51c Clarify Workspace Chat save placeholder feedback`
- HEAD == `origin/main`: YES
- Worktree trước design: sạch
- `.ai`, `local_cases`, `task.md`, `walkthrough.md`, `implementation_plan.md`: sạch

Phase 2G owner smoke evidence:

- tạo và mở lại sổ/cuộc trò chuyện được;
- bật nguồn trong sổ và nguồn tạm được;
- local preview hoạt động;
- save placeholder phản hồi trung thực;
- thay đổi nguồn vẫn dễ hiểu.

## 3. Owner problem statement

Owner cần AI hỗ trợ công việc thật, nhưng UI hiện buộc owner chọn giữa hai mục trong `Chế độ trả lời`:

- `Chỉ xem trước trên máy`;
- `Cho phép gửi nội dung nguồn đang bật tới AI`.

Khi owner nhập câu hỏi ở local mode, hệ thống:

1. lưu câu hỏi như user message;
2. tạo một chuỗi source preview;
3. lưu chuỗi đó như `assistant` message;
4. render trong cùng lịch sử chat với câu trả lời AI thật.

Dù copy có nói “chưa phải câu trả lời”, hình thức interaction vẫn là hỏi rồi nhận assistant bubble. Owner phải đọc kỹ disclaimer để đoán AI có được gọi hay không. Đây là một conceptual safety defect, không chỉ là copy chưa đẹp.

## 4. Why the current design is risky

1. **Cùng hình thức, khác bản chất:** source checklist và provider answer đều xuất hiện như assistant message.
2. **Tên nhóm sai kỳ vọng:** `Chế độ trả lời` làm local preview nghe như một loại trả lời.
3. **Câu hỏi kích hoạt non-answer:** owner đặt câu hỏi nhưng local branch không phân tích câu hỏi; nó chủ yếu liệt kê nguồn/preview.
4. **Disclaimers phải gánh quá nhiều:** người dùng có thể bỏ qua dòng `AIOS chưa nối AI thật`.
5. **Niềm tin giảm:** output nhìn như answer nhưng không giải quyết câu hỏi làm owner nghi ngờ cả answer thật.
6. **AI path bị đặt sau friction:** owner phải hiểu mode, checkbox và consent trước khi được hỗ trợ.
7. **Nguồn đã bật chưa đồng nghĩa nguồn đủ:** đếm nguồn không chứng minh có nội dung phù hợp; UI hiện chưa nói rõ mức thiếu context trước khi gửi.

Rủi ro không phải local preview gọi cloud—tests chứng minh nó không gọi. Rủi ro là owner hiểu sai bản chất output.

## 5. Definitions that Phase 2H must enforce

### Source preview/check

`Kiểm tra nguồn trước khi hỏi AI` là thao tác local-only:

- không gọi provider/cloud;
- không tạo “câu trả lời”;
- không lưu output dưới role `assistant`;
- chỉ hiển thị nguồn đang bật, loại nguồn, trạng thái nội dung và đoạn preview đã giới hạn;
- luôn có badge `AI chưa trả lời`;
- nếu không đủ context, có badge `Thiếu ngữ cảnh`.

### AI answer

`AI đã trả lời` chỉ được dùng khi:

- owner thực hiện explicit AI action;
- exact enabled-source set qua privacy gate;
- provider/model thực sự trả về answer thành công;
- answer được lưu/render trong chat;
- UI hiển thị source summary của context đã gửi.

`Nguồn đã dùng` trong Phase 2H nghĩa là **nguồn được đóng gói và gửi cùng request**, không phải citation hoặc bằng chứng model thật sự dựa vào từng nguồn. Copy/report phải giữ distinction này.

## 6. Options evaluated

| Option | Đánh giá | Quyết định |
|---|---|---|
| A — Hai mode đổi tên | Rõ hơn hiện tại nhưng owner vẫn phải quản lý mode; vẫn dễ tạo hai output paths trong chat. | Không chọn. Có thể là fallback nếu Option B vượt scope. |
| B — Một AI flow chính + source checker phụ | AI-first, ít gây hiểu nhầm, dùng lại provider/privacy engine hiện có, không cần schema mới. | **Chọn cho Phase 2H.** |
| C — Smart intent trong một chat box | Tự nhiên hơn nhưng cần intent/state/action branching và nhiều edge cases. | Future, không làm Phase 2H. |
| D — Paste box NotebookLM-like + badge | UX tốt dài hạn nhưng gộp ingest, split và answer orchestration; scope lớn. | Future, không làm Phase 2H. |

## 7. Recommended target flow

### Màn chính

1. Owner mở conversation.
2. UI luôn cho thấy compact source summary:

   ```text
   AI sẽ dùng 3 nguồn đang bật.
   ```

3. Ngay cạnh summary có secondary action:

   ```text
   Kiểm tra nguồn trước
   ```

4. Owner nhập câu hỏi.
5. Primary explicit action:

   ```text
   Hỏi AI với nguồn đang bật
   ```

6. Hệ thống chụp exact source-set fingerprint tại action.
7. Privacy validation chạy trước provider call.
8. Nếu pass và provider trả lời, chat render:

   ```text
   AI đã trả lời
   Nguồn gửi cùng câu hỏi: 3
   ```

   rồi mới render answer.
9. Nếu blocked/insufficient/provider error, không tạo fake answer bubble; hiển thị owner-safe status và next action.

### Secondary source check

`Kiểm tra nguồn trước` mở một panel/expander local ngoài lịch sử chat:

- badge `AI chưa trả lời`;
- source count và friendly titles;
- empty/truncated/machine-only warnings;
- preview đã cap;
- không cần owner nhập câu hỏi;
- không save `ChatMessage(role="assistant")`.

### No mode switch

Xóa khỏi owner-facing primary UX:

- heading `Chế độ trả lời`;
- radio local/cloud;
- câu `Chỉ xem trước trên máy` như một answer mode;
- blanket-looking consent checkbox tách rời action.

Underlying privacy constants và gates có thể giữ nguyên để giảm risk.

## 8. Exact Vietnamese UI copy proposal

### Primary area

- Heading: `Hỏi AI bằng nguồn đang bật`
- Context summary, N > 0: `AI sẽ dùng {N} nguồn đang bật.`
- Context summary, N = 0: `Chưa có nguồn nào đang bật.`
- Primary action: `Hỏi AI với nguồn đang bật`
- Secondary action: `Kiểm tra nguồn trước`
- Question placeholder: `Nhập câu hỏi bạn muốn AI hỗ trợ...`

### Local source check

- Badge: `AI chưa trả lời`
- Explanation: `Đây chỉ là danh sách nguồn và đoạn xem trước sẽ dùng nếu bạn hỏi AI.`
- Heading: `Kiểm tra nguồn trước khi hỏi AI`
- Count: `Nguồn đang bật: {N}`
- Empty: `Chưa có nguồn để kiểm tra. Hãy bật nguồn hoặc dán thêm dữ liệu.`

### AI answer

- Badge: `AI đã trả lời`
- Context line: `Nguồn gửi cùng câu hỏi: {N}`
- Expandable list: `Xem nguồn gửi cùng câu hỏi`
- Disclaimer: `Đây là câu trả lời do AI tạo. Hãy kiểm tra lại trước khi dùng.`

Không dùng `Nguồn đã dùng` như một claim citation. Nếu product muốn dùng suggested phrase, copy an toàn là:

```text
Nguồn đã dùng làm ngữ cảnh gửi AI: {N}
```

`Nguồn gửi cùng câu hỏi` ngắn và chính xác hơn.

### Insufficient context

- Badge: `Thiếu ngữ cảnh`
- No enabled source: `Hãy bật nguồn hoặc dán thêm dữ liệu trước khi hỏi AI.`
- Enabled but empty: `Nguồn đang bật chưa có nội dung để hỏi AI.`
- All previews/content too weak for a deterministic precheck: `Nguồn đang bật có rất ít nội dung. Bạn vẫn có thể kiểm tra nguồn và bổ sung dữ liệu trước khi hỏi AI.`

Phase 2H không được claim semantic relevance. “Thiếu ngữ cảnh” chỉ dựa trên deterministic facts như zero source, empty content hoặc content removed by existing caps—not một evaluator/RAG mới.

### Privacy block

`Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi quyền riêng tư.`

Nếu owner không có UI đổi privacy label trong scope hiện tại, tránh dead-end copy:

`Có nguồn không được gửi AI. Hãy tắt nguồn đó rồi thử lại.`

### Errors

- Provider unavailable: `AI chưa phản hồi. Nội dung nguồn vẫn được giữ trên máy; vui lòng thử lại sau.`
- Provider unconfigured: `AI chưa được cấu hình. Chưa gửi dữ liệu ra ngoài.`
- Source changed: `Nguồn đang bật đã thay đổi. Hãy xem lại danh sách rồi bấm Hỏi AI lần nữa.`

Không hiển thị exception, provider payload, fingerprint, IDs hoặc privacy enum.

## 9. Output badges and rendering rules

| State | Badge | Chat assistant bubble? | Provider called? |
|---|---|---:|---:|
| Source checker opened | `AI chưa trả lời` | NO | NO |
| No/empty sources | `Thiếu ngữ cảnh` | NO | NO |
| Privacy blocked | `Chưa gửi AI` | NO | NO |
| Source set changed | `Chưa gửi AI` | NO | NO |
| Provider error/no answer | `AI chưa trả lời` | NO | attempted only after gates |
| Provider answer success | `AI đã trả lời` | YES | YES |

Badge phải nằm ngay trên output, không chỉ trong sidebar hoặc tooltip.

Historical Phase 2G local-preview messages có thể vẫn tồn tại trong persisted chat. Phase 2H không rewrite history/schema. Khi render message cũ, copy sẵn có vẫn nói chưa phải answer; migration là out of scope.

## 10. Showing active sources used by AI

Trước action:

- show count and friendly titles in compact expander;
- show privacy/empty warnings without technical labels;
- highlight source-set changes by requiring a fresh click.

Sau successful answer:

- derive display list from `included_source_titles` returned by existing AI-answer result;
- show `Nguồn gửi cùng câu hỏi: N`;
- list friendly titles in collapsed expander;
- do not expose IDs/scopes;
- do not say the model cited or proved the answer;
- if context was truncated, show existing friendly truncation warning.

If no provider success, never label the list as sources used by AI.

## 11. AI-first send UX without unsafe hidden sending

Recommended consent model:

- The explicit click `Hỏi AI với nguồn đang bật` is the per-request owner action.
- Immediately adjacent copy states `AI sẽ dùng {N} nguồn đang bật`.
- At click, system records the exact current `(scope, source_id)` set internally.
- Backend receives `cloud_consent_confirmed=True` only for that click and exact set.
- Consent/action is consumed after success/failure; it is never blanket consent.
- If the set changes before request validation, request is blocked.
- No separate persistent mode or technical confirmation checkbox is shown.

This preserves the intent of Phase 2E while reducing bureaucracy. It is not hidden sending: typing alone never calls AI; only the explicit AI-labeled action does.

If implementation cannot safely bind the button click to the exact source snapshot without weakening existing tests, Gemini must keep a compact one-shot confirmation in the same form:

```text
AI sẽ dùng 3 nguồn đang bật.
[Hỏi AI với nguồn đang bật]
```

It must not fall back to remembered/global consent.

## 12. Multi-source input and “Dán nhanh nhiều nguồn”

### Owner need

Owner often has 2–3 emails, logs or chat snippets. Repeating title + paste + submit for each source is slow.

### Minimal Phase 2H UX

Add a collapsed section near the question:

```text
Dán nhanh nhiều nguồn
```

Inside:

- one optional title: `Tên nhóm nguồn`
- one large text box: `Dán 2–3 email, log hoặc đoạn chat vào đây`
- primary add action: `Thêm làm 1 nguồn`
- help: `Có thể dán nhiều đoạn liên tiếp. AIOS sẽ giữ chúng trong một nguồn tạm cho cuộc trò chuyện này.`

Default behavior:

- save the entire pasted block as one existing temporary text source;
- auto-enable it for the conversation;
- do not ask AI automatically;
- show `Đã thêm 1 nguồn tạm. Bạn có thể hỏi AI khi sẵn sàng.`

This reduces steps without parser/schema work.

### Different titles

For Phase 2H:

- owner can use one group title such as `3 email về lỗi ca đêm`;
- if distinct source titles matter, existing one-source form remains under `Tùy chọn nâng cao`;
- do not auto-detect email/log boundaries.

`Tách thử thành nhiều nguồn` is **future**, not Phase 2H acceptance. Automatic splitting introduces heuristics, preview/error states and ambiguous titles. The design may show future intent in docs, but UI must not expose a non-functional control.

## 13. What the owner sees vs what the system tracks

| Owner sees | System tracks internally |
|---|---|
| `AI sẽ dùng 3 nguồn đang bật` | exact sorted `(source_scope, source_id)` snapshot |
| friendly source titles/types | IDs, scopes and privacy labels |
| `Hỏi AI với nguồn đang bật` | one-shot consent/action for current request |
| `Nguồn đang bật đã thay đổi` | fingerprint mismatch |
| `Có nguồn không được gửi AI` | fail-closed privacy-label validation |
| `Nguồn gửi cùng câu hỏi: 3` | packed/included source titles and caps |
| `AI đã trả lời` | successful provider result |
| owner-safe error | sanitized exception state |

Owner không thấy:

- hash/fingerprint;
- enum `local_only`, `machine_only`, `cloud_allowed`;
- source IDs/scopes;
- provider payload;
- internal caps;
- raw exceptions.

## 14. Phase 2E safety compatibility

Phase 2H design preserves:

- source check is local-only and never calls provider;
- typing/pasting alone never sends cloud;
- AI send requires an explicit AI-labeled per-request action;
- consent/action is tied to exact enabled-source set;
- source changes invalidate old action;
- `local_only`, `confidential`, blank, `None`, whitespace and unknown privacy labels hard-block;
- one blocked source blocks the whole request;
- no partial send;
- no blanket remembered consent;
- provider exceptions remain sanitized;
- AI submit uses persisted Excel content and does not reparse `.xlsx`;
- no technical IDs/privacy enum leak.

Required implementation invariant:

```text
UI simplification may remove a checkbox, but must not remove or weaken backend request validation.
```

## 15. Minimal implementation scope for Gemini

### 2H.1 — Separate source check from chat answer

- Replace visible two-mode radio with AI-first action plus secondary source checker.
- Do not save source-check output as assistant message.
- Reuse preview helper data, but render as a panel/expander.
- Add explicit `AI chưa trả lời` badge.

### 2H.2 — Explicit AI result identity

- Successful provider response gets `AI đã trả lời`.
- Show packed/included source count and friendly titles.
- Keep AI disclaimer.
- Failed/blocked paths do not create answer bubbles.

### 2H.3 — Compact one-shot AI action

- Bind explicit AI button action to exact source snapshot.
- Preserve backend privacy/consent validation.
- Hide fingerprint/technical consent copy.

### 2H.4 — Deterministic context readiness

- `Thiếu ngữ cảnh` for zero enabled sources or no sendable content.
- No semantic sufficiency scoring.
- Privacy-block message is distinct from insufficient context.

### 2H.5 — Quick multi-source paste

- One textarea saved as one existing temporary source.
- Optional group title.
- Auto-enable after save.
- Existing detailed paste form becomes `Tùy chọn nâng cao`.
- No splitting heuristics.

No store/model/engine/schema changes are expected.

## 16. Exact allowed files for future Gemini implementation

Production allowlist:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `src/aios_habit/workspace_chat_answer_preview.py`

Test allowlist:

- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_answer_preview.py`
- `tests/test_workspace_chat_ai_answer.py`

Documentation allowlist:

- `docs/ux/WORKSPACE_CHAT_PHASE2H_ANSWER_CLARITY_AND_SIMPLE_AI_UX_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2H_ANSWER_CLARITY_IMPLEMENTATION_AUDIT.md`

`workspace_chat_ai_answer.py` is intentionally not allowed: existing backend privacy/consent gates are sufficient. If Gemini proves a production change there is necessary, stop and request owner approval with exact justification.

`workspace_chat_store.py` and `workspace_chat_models.py` are not allowed. Quick paste must use existing temporary-source semantics.

## 17. Forbidden files and capabilities

Forbidden files:

- `.ai`
- `local_cases`
- `task.md`
- `walkthrough.md`
- `implementation_plan.md`
- `case_cockpit.py` and Case Cockpit modules/tests
- `src/aios_habit/workspace_chat_store.py`
- `src/aios_habit/workspace_chat_models.py`
- `src/aios_habit/workspace_chat_ai_answer.py` unless owner expands allowlist
- provider/router/network modules
- `requirements.txt`
- `pyproject.toml`
- Excel extractor files

Forbidden capabilities:

- real save-to-case;
- new provider/cloud/network behavior;
- PDF/Word/PPTX/image/OCR;
- RAG/vector/embedding/chunk/retrieval;
- citation/source-use provenance;
- semantic context evaluator;
- automatic multi-source splitting;
- schema migration/rewrite;
- new dependency;
- Case Cockpit redesign/import;
- history migration;
- hidden/automatic cloud send.

## 18. Tests that must be added or updated

### Source-check identity

- No `Chế độ trả lời` owner-facing heading.
- No local/cloud radio.
- Source checker shows `AI chưa trả lời`.
- Source checker output is not persisted as `assistant` message.
- Source checker never constructs/calls provider client.
- Source titles/previews are capped and IDs/scopes remain hidden.

### AI action and answer identity

- Primary action copy is `Hỏi AI với nguồn đang bật`.
- Typing alone does not send.
- Button action snapshots exact current source set.
- Successful provider result shows `AI đã trả lời`.
- Successful output shows count/titles from packed/included context.
- Blocked/error paths never show `AI đã trả lời`.

### Context states

- Zero enabled source -> `Thiếu ngữ cảnh`; no provider call.
- Enabled sources with empty content -> `Thiếu ngữ cảnh`; no provider call.
- Blocked source -> friendly privacy block; no partial send.
- Source set changed -> old action invalid; fresh click required.

### Quick paste

- Multiple pasted snippets create exactly one temporary source.
- Group title and Unicode preserved.
- Source is auto-enabled.
- Paste does not call AI automatically.
- Empty paste shows friendly error.
- Test paths are monkeypatched; no real `.ai`/`local_cases` writes.

### Phase 2E regression

- Local source check no provider call.
- Exact-set consent/action matching.
- All fail-closed privacy-label cases.
- One blocked source blocks all.
- No partial/blanket consent.
- Provider exception sanitization.
- No `.xlsx` reparse.
- Full suite and CLI audit PASS.

Required commands:

```powershell
py -3 -m pytest tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_answer_preview.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md
```

## 19. Risks and anti-overengineering guardrails

1. **Consent simplification risk:** treating AI button click as consent is safe only if exact-set snapshot and backend validation remain. Never infer consent from typing.
2. **Chat input mechanics:** Streamlit `st.chat_input` may not expose a custom submit label. Prefer a small explicit form/button if necessary; do not create a complex state machine.
3. **Historical previews:** old local-preview assistant messages remain. Do not migrate history in Phase 2H.
4. **“Sources used” overclaim:** show sources sent as context, not citations or proven model usage.
5. **Insufficient-context overclaim:** use deterministic empty/count checks only, not semantic scoring.
6. **Quick paste scope:** one pasted block becomes one source. No auto-splitting/parser.
7. **UI density:** source titles live in a collapsed compact list; do not recreate the long sidebar problem.
8. **Failure handling:** blocked/privacy/provider states stay outside answer bubbles and use owner-safe Vietnamese.
9. **No engine drift:** do not modify AI-answer backend merely to accommodate presentation.
10. **No formal workflow:** owner should see one obvious AI action and one optional source check, not a multi-step wizard.

## 20. Gemini implementation prompt

```text
Implement Phase 2H from:
docs/ux/WORKSPACE_CHAT_PHASE2H_ANSWER_CLARITY_AND_SIMPLE_AI_UX_DESIGN_GATE.md

Baseline must be main at HEAD == origin/main == 860c51c with a clean worktree.
If baseline is wrong or dirty, STOP and report FAIL_BASELINE_NOT_READY.

Core outcome:
- Option B: one primary AI flow plus secondary local source checker.
- Remove owner-facing "Chế độ trả lời" and the two-mode radio.
- Source check is outside chat, says "AI chưa trả lời", and is never saved as assistant message.
- Main explicit action says "Hỏi AI với nguồn đang bật".
- Successful provider answer says "AI đã trả lời".
- Show friendly count/titles of sources sent with the request; do not claim citation.
- Show "Thiếu ngữ cảnh" for deterministic zero/empty-source cases.
- Preserve exact-source consent/action, all privacy hard-blocks, no partial send, sanitized errors and no XLSX reparse.
- Add minimal "Dán nhanh nhiều nguồn": one textarea -> one existing temporary source -> auto-enable; no automatic AI send and no splitting.

Exact production files allowed:
- src/aios_habit/workspace_chat_app.py
- src/aios_habit/workspace_chat_ui.py
- src/aios_habit/workspace_chat_answer_preview.py

Exact test files allowed:
- tests/test_workspace_chat_ui_copy.py
- tests/test_workspace_chat_source_selection_ui_copy.py
- tests/test_workspace_chat_source_selection_owner_flow.py
- tests/test_workspace_chat_answer_preview.py
- tests/test_workspace_chat_ai_answer.py

Exact docs allowed:
- docs/ux/WORKSPACE_CHAT_PHASE2H_ANSWER_CLARITY_AND_SIMPLE_AI_UX_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2H_ANSWER_CLARITY_IMPLEMENTATION_AUDIT.md

Do not modify workspace_chat_ai_answer.py, store, models, provider/router/network, dependencies, Excel extractor, Case Cockpit, .ai or local_cases.
Do not implement real save-to-case, new formats, OCR, RAG/vector/retrieval/citation, semantic evaluator, source splitting or schema migration.
Do not stage, commit or push.

Run every command in section 18 and create the implementation audit.
```
