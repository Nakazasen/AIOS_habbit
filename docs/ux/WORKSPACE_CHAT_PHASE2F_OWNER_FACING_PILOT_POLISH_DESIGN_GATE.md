# WORKSPACE_CHAT_PHASE2F_OWNER_FACING_PILOT_POLISH_DESIGN_GATE

## 1. Ket luan ngan

Final status: `PASS_READY_FOR_GEMINI_PHASE2F_IMPLEMENTATION`.

Phase 2F nen la mot lop polish cho owner pilot cua Workspace Chat, khong phai engine moi. Phase 2A-2E da co notebook/conversation, nguon tam, `.xlsx` local ingest, local preview, va AI answer co privacy/consent gate. Viec can lam bay gio la lam cho owner tu mo UI, tao conversation, them nguon, bat/tat nguon, chon local preview hoac AI cloud, thay ro canh bao, va biet luc nao chua gui cloud.

Khuyen nghi:

- Them checklist pilot ngan trong Workspace Chat.
- Lam ro trang thai nguon va che do tra loi ngay trong sidebar/right panel.
- Doi copy owner-facing sang tieng Viet de hieu, tranh thuat ngu ky thuat.
- Them friendly error/status cho launcher va provider/source states.
- Them huong dan hoac nut tao du lieu test khong mat trong UI, nhung chi tao du lieu gia trong `local_cases/workspace_chat`.
- Khong mo Case Cockpit, khong tao RAG/vector/citation/source-use that, khong them dependency.

## 2. Baseline

Baseline da chay truoc khi tao report:

- Repo: `D:\Sandbox\AIOS_habbit`
- Branch: `main`
- HEAD: `e4159a5`
- `origin/main`: `e4159a5`
- `HEAD == origin/main`: YES
- Worktree truoc report: clean
- Latest commit: `e4159a5 Ignore local runtime outputs: fix test check-ignore path`
- Full pytest: `667 passed in 21.83s`
- CLI audit: `PASS`, no errors/warnings

Khong stage, commit, push, branch, reset, checkout, stash, clean, hoac update-index.

## 3. Current Workspace Chat user journey

Owner hien tai vao app qua `RUN_AIOS_HABIT_STUDIO.bat`, nhung launcher mo `src\aios_habit\studio.py`. `studio.py` hien chua co navigation vao Workspace Chat, nen owner co the phai biet CLI/path rieng neu muon dung `workspace_chat_app.py`.

Trong `workspace_chat_app.py`, flow hien tai:

1. Man hinh notebook: hien danh sach so tai lieu va nut mo so.
2. Trong notebook: sidebar co danh sach conversation, nut tao conversation, rename conversation.
3. Sidebar co source summary, che do tra loi, consent UI cho AI cloud, source trong so, source tam.
4. Main chat cho owner dat cau hoi.
5. Local mode luu user message va assistant placeholder tu `workspace_chat_answer_preview.py`.
6. Cloud mode can checkbox consent theo exact enabled-source set, goi `generate_workspace_ai_answer()`, roi chi luu successful AI answer.
7. Right panel hien cau tra loi, nguon dang bat, muc can kiem tra, va hanh dong tiep theo.
8. Owner co the dan text dai hoac them `.xlsx`; `.xlsx` duoc parse local khi upload va AI path chi dung `content_text` da luu.

Dieu nay du de pilot ve mat backend, nhung chua du mem cho owner neu khong co agent ngoi canh.

## 4. Pilot pain points

1. Man hinh can polish nhat la Workspace Chat app, dac biet:
   - first screen/entry tu launcher;
   - sidebar source and answer-mode area;
   - chat empty state;
   - right result panel;
   - paste/Excel source expanders.

2. Owner hien phai lam cac buoc:
   - mo `RUN_AIOS_HABIT_STUDIO.bat`;
   - tim duong vao Workspace Chat;
   - mo notebook;
   - tao/chon conversation;
   - them pasted text hoac `.xlsx`;
   - bat nguon;
   - chon local preview hoac AI cloud;
   - neu cloud, doc danh sach nguon va tick xac nhan;
   - gui cau hoi;
   - doc warning/answer va tu kiem tra lai.

3. Diem de gay nham:
   - Local preview vs AI answer: local preview van tao assistant message nen co the bi hieu la AI da tra loi.
   - Source enabled vs source included: owner thay source dang bat nhung khong biet source rong, bi rut gon, bi cap, hay bi chan cloud.
   - Consent cloud: checkbox co, nhung can noi ro day la cho lan gui hien tai, khong phai cho phep lau dai.
   - Warning rut gon source: can hien ro trong UI sau answer va trong source status, khong chi trong message ngan.
   - Provider chua cau hinh: can noi "AI chua duoc cau hinh", va khang dinh chua gui/khong mat nguon neu request bi block.

4. Copy tieng Viet can doi:
   - Giam cac cum nhu "placeholder", "provider", "preview" trong owner-facing UI.
   - Doi "Bản thử nghiệm" thanh copy ro hon: "Chỉ xem trước trên máy".
   - Doi "Nguồn đang dùng" thanh "Nguồn đang bật".
   - Doi "proven sources" label trong code/UI sang "Nguồn đang bật cho câu hỏi".
   - Doi "owner cần kiểm tra" thanh "Cần kiểm tra lại".

5. Pilot mode/test data mode: nen co nhe. Khuyen nghi khong tao mode rieng phuc tap; them checklist va mot action ro rang "Tạo dữ liệu test không mật" neu can. Action nay chi tao notebook/conversation/source gia trong store local, khong ghi `.ai`, khong dung `local_cases` test real trong unit tests, va khong gui cloud.

6. Checklist trong UI: co. Day la 2F.2 va nen hien o dau Workspace Chat conversation:
   - Them nguon.
   - Bat nguon can dung.
   - Hoi thu o che do chi xem truoc tren may.
   - Neu muon gui AI, kiem nguon va xac nhan.
   - Kiem tra cau tra loi truoc khi dung.

7. Onboarding panel: co, nhung ngan. Nen hien khi conversation chua co message/source, va co the collapse sau khi owner bat dau.

8. Health/status panel: co, nhung nen la status nho trong sidebar/right panel, khong lam dashboard moi. Can hien:
   - so nguon tong;
   - so nguon dang bat;
   - source rong;
   - source bi rut gon;
   - source bi chan cloud;
   - AI chua cau hinh.

9. Nut tao du lieu test khong mat: nen co neu implementation scope con nho. Neu lam, phai la explicit button, du lieu gia, va tests monkeypatch store path ve `tmp_path`.

10. Export/share pilot log: khong nen lam trong 2F MVP. Neu can, chi design truoc metadata-only: timestamp, mode, source count, warning count, provider configured yes/no, externally_sent yes/no. Khong luu raw prompt/source.

11. Update launcher `.bat`: co the can. `RUN_AIOS_HABIT_STUDIO.bat` dang set `PYTHONPATH=src`; Phase 2F nen uu tien chay bang package editable va mo dung Studio/Workspace Chat entry ma owner khong can biet `PYTHONPATH`.

12. Update ROADMAP/ARCHITECTURE: khong can trong implementation 2F dau tien. Chi update sau khi owner chap nhan pilot polish hoac khi commit phase status.

13. Tests can cover:
   - checklist copy/visibility;
   - default mode local preview;
   - consent checkbox unchecked;
   - source status counts;
   - blocked/privacy/source-empty/truncated friendly copy;
   - forbidden owner-facing technical terms;
   - launcher text/path behavior if launcher changed;
   - no Case Cockpit import;
   - no network in tests;
   - no `.ai` or real `local_cases` writes.

14. Non-goals cua Phase 2F:
   - RAG/vector/embedding/chunk/retrieval/citation/source-use provenance;
   - Excel extractor rewrite;
   - provider router/multi-provider optimization;
   - Case Cockpit redesign;
   - production permission sync;
   - background jobs;
   - cloud upload files directly;
   - new database schema unless strictly needed;
   - Work Stream Map, Today Brief, memory learning engine.

## 5. Phase 2F scope

### 2F.1 UI entry readiness

Goal: owner co the mo dung Workspace Chat pilot ma khong phai nho CLI.

Recommended implementation:

- Add Workspace Chat entry inside Studio navigation, or make launcher copy clearly say how to open Workspace Chat.
- Prefer adding a Studio page that imports/launches Workspace Chat only if it does not pull Case Cockpit or runtime data into tests.
- Improve launcher failure copy:
  - Python not found.
  - package/dependency missing.
  - Streamlit missing.
  - command owner can rerun.

Do not require owner to manually set `PYTHONPATH`.

### 2F.2 Workspace Chat pilot checklist

Add a short checklist in Workspace Chat, visible near the active conversation:

```text
1. Them nguon
2. Bat nguon can dung
3. Hoi thu o che do chi xem truoc tren may
4. Neu muon gui AI, kiem nguon va xac nhan
5. Kiem tra cau tra loi truoc khi dung
```

Owner-facing Vietnamese copy should use real Vietnamese with accents if the file/UI encoding is cleaned in the implementation. If the repo keeps current mojibake test fixtures, update tests consistently but do not perform a broad encoding rewrite in Phase 2F.

### 2F.3 Safe test data

Recommended: add either:

- an onboarding note telling owner to paste a fake/non-secret sample; or
- an explicit button to create one fake conversation and one fake source.

If button is added:

- source title should say it is fake test data;
- content must not resemble secrets, real company records, API keys, or private names;
- auto-enable the fake temporary source only inside the current conversation;
- tests must monkeypatch store paths.

### 2F.4 Source status clarity

Add or refine source status display so owner sees:

- total notebook sources;
- total temporary sources;
- enabled sources;
- empty enabled sources;
- sources excluded because unresolved/cross-scope;
- sources that may be shortened;
- sources blocked from AI cloud by privacy label.

Use owner copy such as:

```text
Nguon dang bat
Nguon chua co noi dung de gui
Noi dung co the bi rut gon de tranh qua dai
Nguon nay chi duoc dung tren may
Chua gui toi AI
```

### 2F.5 Consent UX polish

Keep the Phase 2E privacy rules:

- local preview default;
- cloud consent checkbox unchecked;
- exact enabled-source set listed before submit;
- if source set changes, owner must confirm again;
- `local_only`, `confidential`, unknown/blank labels hard-block cloud;
- no partial send when any enabled source is blocked.

Polish:

- state that confirmation is for one answer only;
- show source count and titles;
- show "Chua gui toi AI" when blocked;
- keep provider errors friendly and sanitized.

### 2F.6 Friendly errors

Owner-facing errors should cover:

- AI chua duoc cau hinh.
- Chua co nguon dang bat.
- Nguon dang bat chua co noi dung.
- Mot hoac nhieu nguon chi duoc dung tren may.
- Noi dung da duoc rut gon de tranh qua dai.
- File khong ho tro.
- Excel qua lon/bi rut gon.
- Launcher chua cai du package.

Avoid raw traceback, endpoint, model ID, API key, local file path, source ID, scope enum, or provider payload in UI.

### 2F.7 Pilot evidence log

Do not implement full pilot log in 2F unless owner explicitly asks. If included, keep it metadata-only:

- conversation id or title;
- mode: local preview/cloud;
- source counts;
- warning counts;
- provider configured yes/no;
- externally sent yes/no;
- timestamp.

Do not log raw prompt, raw source text, API key, provider response body, or sensitive file contents.

## 6. Proposed UI/copy changes

Recommended owner-facing copy:

```text
Chi xem truoc tren may
Cho phep gui noi dung nguon dang bat toi AI
Nguon dang bat
Nguon chua co noi dung de gui
Noi dung co the bi rut gon de tranh qua dai
Nguon nay chi duoc dung tren may
AI chua duoc cau hinh
Cau tra loi AI can kiem tra lai truoc khi dung
Chua gui toi AI
Xac nhan cho lan tra loi nay
```

Do not use these terms in production owner UI:

```text
RAG
vector
embedding
chunk
retrieval
citation
claim
provider router
Mermaid
grounding
source-use
evidence provenance
```

It is acceptable for these terms to appear in design docs, tests, and code comments where they are guardrails, not owner UI.

## 7. Privacy/consent UX rules

Phase 2F must not weaken Phase 2E:

1. Default is local preview.
2. Local preview must not call provider/network.
3. Cloud answer requires explicit mode plus unchecked-by-default confirmation.
4. Consent applies only to the exact enabled-source set shown to owner.
5. Changing enabled source set invalidates consent.
6. Blocked privacy label blocks the whole cloud request.
7. Empty/unknown privacy labels fail closed.
8. Source caps/truncation happen after privacy validation.
9. UI must distinguish:
   - source is enabled;
   - source content is included in prompt;
   - source was shortened;
   - source cannot be sent cloud;
   - answer was actually externally sent.
10. AI answer copy must remind owner to check before use.

## 8. Test plan

Focused tests:

- `py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q`
- `py -3 -m pytest tests/test_workspace_chat_source_selection_owner_flow.py -q`
- `py -3 -m pytest tests/test_workspace_chat_ui_copy.py -q`

Add or update tests for:

- pilot checklist appears in app/UI copy;
- local preview is default;
- cloud confirmation is unchecked;
- exact source list is shown before cloud confirm;
- source set change still invalidates consent;
- source summary counts total/enabled/empty/blocked where implemented;
- friendly messages for no source, empty source, blocked source, provider unconfigured, truncation, unsupported file;
- forbidden owner-facing terms absent from `workspace_chat_app.py` and `workspace_chat_ui.py`;
- no `case_cockpit.py` import from Workspace Chat;
- no `.xlsx` reparse in AI submit path;
- no new dependency;
- launcher behavior/copy if `RUN_AIOS_HABIT_STUDIO.bat` changes;
- no real `.ai`/`local_cases` writes in tests.

Final verification:

- `py -3 -m pytest -q`
- `py -3 -m aios_habit.cli audit`
- `git diff --check`
- `git status --short`

## 9. Non-goals

Phase 2F must not implement:

- RAG/vector/embedding/chunk/retrieval framework;
- citation/source-use provenance;
- multi-provider optimization;
- background jobs;
- Case Cockpit redesign;
- production permission sync;
- new database schema unless unavoidable;
- direct cloud file upload;
- Excel extractor rewrite;
- memory learning engine;
- Work Stream Map;
- Today Brief;
- NotebookLM parity claims;
- production readiness/P1.0 claims.

## 10. Files likely allowed for implementation

Likely allowed:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `src/aios_habit/workspace_chat_ai_answer.py` only for friendly status/result fields if strictly needed
- `src/aios_habit/workspace_chat_answer_preview.py` only for local preview copy polish
- `tests/test_workspace_chat_ai_answer.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `RUN_AIOS_HABIT_STUDIO.bat`

Optional only if owner wants Studio entry:

- `src/aios_habit/studio.py`
- focused Studio navigation test if an existing pattern exists or a small new test is needed

Avoid unless owner explicitly expands scope:

- `ROADMAP.md`
- `ARCHITECTURE.md`

Forbidden:

- `.ai`
- `local_cases`
- `src/aios_habit/case_cockpit.py`
- Case Cockpit modules
- RAG/vector/retrieval/citation/source-use modules
- dependency manifests
- Excel extractor rewrite files

## 11. Gemini implementation prompt

```text
You are Gemini. Implement WORKSPACE_CHAT_PHASE2F_OWNER_FACING_PILOT_POLISH based on:
docs/ux/WORKSPACE_CHAT_PHASE2F_OWNER_FACING_PILOT_POLISH_DESIGN_GATE.md

Baseline required before editing:
- Repo: D:\Sandbox\AIOS_habbit
- Branch: main
- HEAD == origin/main == e4159a5
- Worktree must be clean except this committed/accepted design report.
- Run:
  git branch --show-current
  git rev-parse --short HEAD
  git rev-parse --short origin/main
  git status --short
  py -3 -m pytest -q
  py -3 -m aios_habit.cli audit
- If baseline fails, STOP and report FAIL_BASELINE_NOT_READY.

Goal:
Polish Workspace Chat for an owner-facing pilot. Do not build a new answer engine. Make it clear how an owner opens Workspace Chat, creates/chooses a conversation, adds sources, enables/disables sources, uses local preview, optionally confirms AI cloud, sees privacy warnings, and knows when content was not sent to AI.

Allowed files:
- src/aios_habit/workspace_chat_app.py
- src/aios_habit/workspace_chat_ui.py
- src/aios_habit/workspace_chat_ai_answer.py only if needed for friendly status/result fields
- src/aios_habit/workspace_chat_answer_preview.py only if needed for local preview copy polish
- tests/test_workspace_chat_ai_answer.py
- tests/test_workspace_chat_source_selection_owner_flow.py
- tests/test_workspace_chat_ui_copy.py
- RUN_AIOS_HABIT_STUDIO.bat
- Optional: src/aios_habit/studio.py only to add a clear Workspace Chat entry if done without Case Cockpit coupling

Forbidden:
- Do not stage/commit/push/reset/checkout/stash/clean/update-index.
- Do not edit .ai.
- Do not edit or create real local_cases data.
- Do not import or edit case_cockpit.py.
- Do not redesign Case Cockpit.
- Do not add dependencies.
- Do not create RAG/vector/embedding/chunk/retrieval/citation/source-use provenance.
- Do not rewrite Excel parsing.
- Do not add network/provider calls in tests.
- Do not log raw prompt, raw source text, API key, provider raw response, or sensitive payloads.
- Do not update ROADMAP.md or ARCHITECTURE.md unless owner explicitly requests after implementation.

Required UX changes:
1. Add a short Workspace Chat pilot checklist:
   - Them nguon
   - Bat nguon can dung
   - Hoi thu o che do chi xem truoc tren may
   - Neu muon gui AI, kiem nguon va xac nhan
   - Kiem tra cau tra loi truoc khi dung
2. Improve owner copy for local preview vs AI answer.
3. Make source status clearer:
   - total sources
   - enabled sources
   - empty enabled sources
   - truncated/shortened content warning
   - cloud-blocked sources due to privacy
4. Keep cloud consent unchecked by default and exact to the current enabled-source set.
5. Show clear "not sent to AI" style messages when blocked or local-preview-only.
6. Friendly errors for:
   - AI not configured
   - no enabled source
   - empty source
   - source blocked by privacy
   - unsupported file
   - Excel too large/truncated
   - launcher dependency/package problem
7. If adding safe test data, it must be explicit, fake, local-only, and covered by tmp_path tests.

Owner UI copy rules:
- Use simple Vietnamese owner copy.
- Avoid technical words in production UI:
  RAG, vector, embedding, chunk, retrieval, citation, claim, provider router, Mermaid, grounding, source-use, evidence provenance.
- It is okay for those words to appear in tests/docs as guardrails.

Privacy rules that must stay true:
- Default mode is local preview.
- Local preview makes zero provider/network calls.
- Cloud answer requires explicit mode plus unchecked-by-default confirmation.
- Consent is for one exact enabled-source set.
- Source set changes invalidate consent.
- local_only, confidential, blank, and unknown privacy labels hard-block cloud.
- One blocked source blocks the whole cloud request.
- No partial cloud send.
- Do not claim the AI used/proved/cited a source; only say sources were enabled/included.

Required tests:
- checklist required copy appears;
- default local preview copy/state;
- cloud checkbox not prechecked;
- source counts/status copy;
- friendly no-source/empty-source/blocked-source/provider-unconfigured messages;
- source-set-change consent invalidation still covered;
- forbidden owner-facing technical copy absent from workspace_chat_app.py and workspace_chat_ui.py;
- no Case Cockpit import;
- no .xlsx reparse in AI submit path;
- launcher copy/behavior if launcher changed;
- tests use tmp_path/monkeypatch for store and do not write real local_cases or .ai.

Verification:
- Run focused Workspace Chat tests.
- Run py -3 -m pytest -q.
- Run py -3 -m aios_habit.cli audit.
- Run git diff --check.
- Report exact dirty files and test results.
- Do not stage, commit, or push.

Expected final status if all pass:
PASS_READY_FOR_OWNER_REVIEW_PHASE2F
```

## 12. Final recommendation

Proceed to Gemini implementation with a narrow Phase 2F owner-facing pilot polish. The app has enough backend safety to support this, and the baseline is clean. The highest-value work is not another engine layer; it is making the existing safe flow obvious to a non-CLI owner.

Recommended owner decisions before implementation:

- Approve adding a Workspace Chat entry or clearer path in `RUN_AIOS_HABIT_STUDIO.bat`/Studio.
- Approve whether to add a fake test-data button, or only onboarding guidance.
- Defer pilot evidence log unless owner specifically needs a metadata-only export.

Final status: `PASS_READY_FOR_GEMINI_PHASE2F_IMPLEMENTATION`.
