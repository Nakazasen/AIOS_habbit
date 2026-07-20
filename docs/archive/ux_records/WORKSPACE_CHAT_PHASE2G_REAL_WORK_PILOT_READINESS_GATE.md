# WORKSPACE_CHAT_PHASE2G_REAL_WORK_PILOT_READINESS_GATE

## 1. Ket luan ngan

Final status: `PASS_WITH_WARNINGS_STUDIO_ENTRY_STILL_MANUAL`.

Workspace Chat Phase 2 is ready to start a real-work pilot on a company machine, using fake data first, then non-sensitive work data, and only then optional cloud AI with exact per-request consent.

Phase 2G does not add a new engine. It freezes the pilot-readiness checks for:

- UI launch and Workspace Chat navigation.
- Safe test data.
- Local preview.
- Cloud consent.
- Privacy hard-block.
- Source status and warning copy.
- Excel `.xlsx` local ingest.
- Provider-not-configured behavior.
- Owner-facing pilot checklist.

Main warning: Studio has a Workspace Chat entry, but it still tells the owner to open Workspace Chat with a terminal command or separate launcher. This is acceptable for starting the pilot if the owner is comfortable with one manual launch step. It should become a Phase 2G-fix follow-up, not a Phase 2 close blocker.

Pilot can start: YES.

Owner decision needed: YES, accept the manual Studio-entry warning for the first pilot run.

## 2. Baseline

Baseline commands run for this gate:

```text
git branch --show-current
git rev-parse --short HEAD
git rev-parse --short origin/main
git status --short
git log --oneline -10
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
```

Observed baseline:

- Branch: `main`
- HEAD: `0d5b300`
- `origin/main`: `0d5b300`
- HEAD equals origin/main: YES
- Worktree before this report: clean
- Latest commit: `0d5b300 Polish Workspace Chat owner pilot flow`
- Full pytest: `668 passed in 22.00s`
- CLI audit: `PASS`, no errors or warnings

Baseline verdict: PASS.

No stage, commit, push, branch, reset, checkout, stash, clean, or update-index action was performed.

## 3. Phase 2 current state

Phase 2A through 2F are complete and pushed in commit `0d5b300`.

Current implemented capability:

- Workspace Chat has notebook/conversation flow.
- Owner can create or choose a conversation.
- Owner can add temporary pasted-text sources.
- Owner can ingest `.xlsx` locally into a temporary source.
- Owner can enable/disable notebook and temporary sources per conversation.
- Local preview is the default answer mode.
- Cloud AI path requires explicit mode and unchecked per-request consent.
- Consent is tied to the exact enabled-source set.
- Privacy labels `local_only`, `confidential`, blank, `None`, whitespace, and unknown hard-block cloud.
- One blocked source blocks the whole cloud request.
- Safe fake test data can be generated from the UI.
- Studio navigation includes Workspace Chat, with a manual command warning.
- Phase 2F copy clarifies `Chỉ xem trước trên máy`, `Nguồn đang bật`, source warnings, and `Chưa gửi tới AI`.

Known accepted warning:

- Studio entry is safer than the old second-Streamlit-spawn idea, but still not fully owner-friendly because opening Workspace Chat requires a terminal command or separate launcher.

## 4. Pilot goals

Phase 2G pilot goal is not production readiness. The goal is to let the owner safely prove that Workspace Chat can support real work in a controlled local-first flow.

Pilot must answer these questions:

1. Can the owner open Studio and find Workspace Chat?
2. Can the owner create or choose a conversation?
3. Can the owner create fake safe test data without touching confidential data?
4. Can the owner ask a local-preview question and understand that no AI/cloud was used?
5. Can the owner see which sources are enabled?
6. Can the owner ingest a non-secret `.xlsx` locally and use it in local preview?
7. Can the owner understand when a source is empty, shortened, or machine-only?
8. Can the owner choose cloud mode only with exact per-request consent?
9. Does provider-not-configured behavior fail safely and clearly?
10. Do privacy labels hard-block cloud without partial send?
11. Are remaining UX issues small enough to track as follow-up?
12. Can Phase 2 close, or does it need a Phase 2G-fix before close?

Recommended pilot data order:

1. Fake safe data created by the app.
2. Non-sensitive work notes that are already safe to inspect locally.
3. A sample `.xlsx` that contains no confidential company data.
4. Cloud mode only with fake or clearly non-sensitive data and exact source confirmation.

Do not use confidential company documents in cloud pilot.

## 5. Pilot scenarios

### Scenario 1 - Fresh clone health

Owner runs:

```powershell
cd D:\Sandbox\AIOS_habbit
git status -sb
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
```

PASS:

- Worktree is clean before pilot changes.
- Tests pass.
- CLI audit passes.

FAIL:

- Worktree has unexpected dirty runtime/sensitive files.
- Tests fail.
- CLI audit fails.

Severity if fail: BLOCKER.

### Scenario 2 - UI launch

Owner runs:

```powershell
.\RUN_AIOS_HABIT_STUDIO.bat
```

Then owner opens Workspace Chat using the Studio guidance.

PASS:

- Studio opens.
- Workspace Chat entry is visible.
- Entry copy is understandable.
- Manual command warning is clear.
- Studio does not spawn a second unmanaged Streamlit app from inside the app.

FAIL:

- Studio does not open.
- Workspace Chat is not discoverable.
- Owner cannot understand how to open Workspace Chat.
- Streamlit subprocess launch loop appears.

Severity if fail: BLOCKER for crash/loop, WARNING for manual command.

### Scenario 3 - Safe test data

In Workspace Chat:

1. Create or open a conversation.
2. Click `Tạo dữ liệu test không mật`.
3. Confirm the new source appears and is enabled.
4. Ask a simple question in local-preview mode.

PASS:

- Fake test source appears.
- Fake test source is enabled for the active conversation.
- Copy says the data is fake/non-secret.
- Tests keep store paths monkeypatched and do not write real `.ai` or `local_cases`.
- No provider/network call is involved.

FAIL:

- Safe-data button crashes.
- Fake source is not enabled.
- Test data looks like real company data, secret, credential, or private record.
- Tests write real `.ai` or `local_cases`.

Severity if fail: BLOCKER.

### Scenario 4 - Local preview

Owner asks in mode:

```text
Chỉ xem trước trên máy
```

PASS:

- No provider call.
- No network/cloud claim.
- Answer says it is a local preview.
- Source status is visible.
- Copy does not overclaim analysis, proof, citation, or final conclusion.

FAIL:

- Provider/network call happens.
- UI implies cloud AI answered when local preview was selected.
- Owner cannot tell which sources are enabled.

Severity if fail: BLOCKER for provider call, WARNING for minor copy ambiguity.

### Scenario 5 - Cloud consent blocked / provider not configured

Owner selects cloud mode but either:

- does not confirm consent; or
- provider is not configured.

PASS:

- No cloud send without confirmation.
- Message includes `Chưa gửi tới AI` or clear provider-not-configured copy.
- No raw exception, endpoint, model ID, API key, provider payload, or local path is shown.
- No blanket consent is persisted.

FAIL:

- Provider call happens before consent.
- Raw provider exception leaks to UI.
- Consent remains valid after source set changes.

Severity if fail: BLOCKER.

### Scenario 6 - Excel `.xlsx` local ingest

Owner uses a non-secret `.xlsx` file:

1. Upload/ingest `.xlsx`.
2. Confirm temporary source is created and enabled.
3. Ask in local-preview mode.
4. Optionally test cloud blocked/consent behavior with the same source.

PASS:

- `.xlsx` ingest is local.
- AI submit path uses persisted `content_text`/preview and does not re-parse workbook.
- Source preview/status is clear.
- Large/truncated content warning appears when applicable.

FAIL:

- Valid `.xlsx` crashes ingest.
- AI submit path re-runs Excel parsing.
- Raw workbook error leaks to UI.

Severity if fail: BLOCKER for crash/reparse, WARNING for minor copy issue.

### Scenario 7 - Privacy hard-block

Use a test source with privacy label:

- `local_only`
- `confidential`
- blank / whitespace / `None` / unknown

PASS:

- Cloud hard-blocks.
- Provider call count is zero.
- No partial send.
- Friendly message tells owner it was not sent.

FAIL:

- Any blocked source is sent.
- App silently drops the blocked source and sends the rest.
- Unknown/blank privacy label becomes cloud-allowed.

Severity if fail: BLOCKER.

### Scenario 8 - Vietnamese/Japanese Unicode

Use non-secret Vietnamese and Japanese text.

PASS:

- Text remains readable in preview and answer.
- UI does not break.
- Source/title display does not corrupt the workflow.

FAIL:

- Unicode breaks source creation, preview, prompt packing, or display.

Severity if fail: WARNING, unless it blocks a normal pilot file.

## 6. Readiness matrix

| Area | PASS criteria | FAIL criteria | Evidence command/UI check | Severity |
|---|---|---|---|---|
| Repo health | `main`, HEAD and origin at `0d5b300`, clean before report | Wrong branch, wrong commit, dirty unexpected files | `git branch --show-current`; `git rev-parse --short HEAD`; `git status --short` | BLOCKER |
| Launcher/UI entry | Studio opens; Workspace Chat entry visible; manual warning clear | Studio crash, no entry, launch loop | `.\RUN_AIOS_HABIT_STUDIO.bat`; inspect Studio page | BLOCKER/WARNING |
| Workspace Chat navigation | Owner can find open path from Studio | Owner cannot identify next step | Studio Workspace Chat page | WARNING |
| Source creation | Pasted or fake source can be created | Source creation crashes or stores secret-like fake data | Workspace Chat UI | BLOCKER |
| Source selection | Owner can enable/disable sources per conversation | Enabled state wrong or unclear | Source sidebar + source summary | BLOCKER |
| Safe test data | Fake non-secret source created and enabled; tests use monkeypatch store paths | Real `.ai/local_cases` writes or unsafe fake data | UI button; `tests/test_workspace_chat_source_selection_owner_flow.py` | BLOCKER |
| Local preview | Default mode; no provider/network call; clear local copy | Provider call in local mode or overclaim | `tests/test_workspace_chat_ai_answer.py`; UI mode check | BLOCKER |
| Cloud consent | Explicit cloud mode plus unchecked per-request confirmation | Send before consent or stale consent accepted | Cloud UI + consent tests | BLOCKER |
| Privacy hard-block | `local_only`, `confidential`, blank, `None`, whitespace, unknown block cloud | Partial send or fallback to allowed label | AI answer privacy tests | BLOCKER |
| Excel ingest | `.xlsx` parsed locally once, saved as source, enabled | Reparse in AI path or raw Excel error | Excel UI; no-reparse tests | BLOCKER |
| Warning/error copy | Friendly `Chưa gửi tới AI`, source empty/truncated/provider messages | Raw exception, provider internals, secret-like details | UI copy tests and code scan | BLOCKER/WARNING |
| Test suite | Full pytest passes | Any failing test | `py -3 -m pytest -q` | BLOCKER |
| CLI audit | Audit returns PASS | Any audit error | `py -3 -m aios_habit.cli audit` | BLOCKER |
| Runtime data safety | No sensitive runtime files become dirty | `.ai`, `local_cases`, secret report content dirty | `git status --short .ai local_cases` | BLOCKER |
| Owner usability | Owner can follow checklist with at most manual launch warning | Owner cannot complete basic flow without developer help | Pilot checklist run | WARNING |

Severity definitions:

- BLOCKER: must fix before closing Phase 2 or sending any real pilot data.
- WARNING: pilot may start if owner accepts the limitation.
- FOLLOW_UP: track after pilot start.
- OUT_OF_SCOPE: belongs to Phase 3 or later.

## 7. Owner-facing pilot checklist

Owner checklist file:

```text
docs/ux/WORKSPACE_CHAT_PHASE2G_OWNER_PILOT_CHECKLIST.md
```

Short checklist:

1. Mo AIOS Habit Studio.
2. Mo Workspace Chat theo huong dan trong Studio.
3. Tao hoac chon cuoc tro chuyen.
4. Tao du lieu test khong mat.
5. Bat nguon can dung.
6. Hoi thu o che do `Chỉ xem trước trên máy`.
7. Kiem tra `Nguồn đang bật`.
8. Neu muon dung AI cloud, chi xac nhan khi dung nguon va du lieu khong mat.
9. Khong dung tai lieu mat trong pilot cloud.
10. Ghi lai loi, cho kho hieu, va buoc nao bi ket.

## 8. Privacy rules for pilot

Pilot privacy rules:

- Start with fake data or non-sensitive data.
- Do not use confidential company documents in cloud pilot.
- Do not paste raw confidential content into reports.
- `local_only`, `confidential`, blank, `None`, whitespace, and unknown privacy labels must hard-block cloud.
- `machine_only` may be sent to cloud only after exact per-request consent for the current enabled-source set.
- Consent is not blanket consent.
- If enabled sources change, consent must be confirmed again.
- One blocked source blocks the whole cloud request.
- No partial cloud send.
- Pilot logs, if any, should record only metadata/status, not secret content.

## 9. Phase 2 close criteria

Phase 2 can close if:

- Full pytest PASS.
- CLI audit PASS.
- Workspace Chat can be opened.
- Safe test data flow PASS.
- Local preview PASS.
- Cloud blocked path PASS.
- Privacy hard-block PASS.
- Excel ingest local PASS.
- Owner can follow checklist and understand copy.
- No runtime dirty sensitive data.

Phase 2 does not need to stay open for:

- Studio entry still being manual, if owner accepts the warning.
- Small copy polish after pilot.
- Absence of real RAG/citation/source-use provenance.
- Absence of NotebookLM parity.
- Absence of production onboarding.

Phase 2 must stay open or move to Phase 2G-fix if:

- Provider call occurs without consent.
- Privacy hard-block can be bypassed.
- Tests create real `.ai` or `local_cases` data.
- UI crashes when safe test data is used.
- Excel ingest crashes on a valid `.xlsx`.
- Raw exception or secret-like content leaks to UI.
- Worktree, tests, or audit are not clean.

Current close recommendation:

- Phase 2 can close after owner runs the pilot checklist and accepts the manual Studio-entry warning.
- If owner does not accept manual launch, create a small Phase 2G-fix for a cleaner owner-friendly Workspace Chat launch path.

## 10. Risks / warnings

### Warning 1 - Studio entry still manual

Studio now exposes Workspace Chat, and the app does not spawn a second Streamlit process from inside Studio. However, owner still needs to run:

```powershell
py -3 -m streamlit run src/aios_habit/workspace_chat_app.py
```

or use a separate launcher.

Severity: WARNING.

Recommendation: do not block pilot if owner accepts this. Track a Phase 2G-fix or Phase 3 launch-polish item.

### Warning 2 - Pilot is not production onboarding

The checklist is enough for a controlled owner pilot. It is not a full guided onboarding flow.

Severity: FOLLOW_UP.

### Warning 3 - No real citation/source-use

Workspace Chat shows sources that were enabled/included. It does not prove which source the model truly used.

Severity: OUT_OF_SCOPE for Phase 2G.

### Warning 4 - Cloud pilot data must stay non-sensitive

The consent gate prevents accidental send paths, but owner must still avoid confidential cloud test data.

Severity: BLOCKER if violated during pilot.

## 11. Files / commands for pilot

Key files:

- `RUN_AIOS_HABIT_STUDIO.bat`
- `RUN_AIOS_CASE_COCKPIT.bat`
- `src/aios_habit/studio.py`
- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `src/aios_habit/workspace_chat_ai_answer.py`
- `src/aios_habit/workspace_chat_answer_preview.py`
- `src/aios_habit/workspace_chat_excel.py`
- `tests/test_workspace_chat_ai_answer.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `docs/ux/WORKSPACE_CHAT_PHASE2F_OWNER_FACING_PILOT_POLISH_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2F_IMPLEMENTATION_AUDIT.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_OWNER_PILOT_CHECKLIST.md`

Owner health commands:

```powershell
git status -sb
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
```

Owner Studio launch:

```powershell
.\RUN_AIOS_HABIT_STUDIO.bat
```

Manual Workspace Chat launch, if needed:

```powershell
py -3 -m streamlit run src/aios_habit/workspace_chat_app.py
```

## 12. Final recommendation

Final recommendation: start Phase 2G pilot execution with warning accepted.

Phase 2 is stable enough for a controlled real-work pilot if the owner:

- starts with fake or non-sensitive data;
- confirms local preview before cloud;
- uses cloud only with exact source confirmation;
- avoids confidential cloud data;
- records UX problems without pasting confidential content;
- accepts the manual Studio-entry warning for this pilot run.

No Phase 2G-fix is required before the first pilot unless the owner rejects the manual launch step.

Suggested next step after pilot:

- If pilot passes: close Phase 2 and start Phase 3 with owner acceptance evidence and a narrow first item, likely owner-friendly launch/onboarding polish or pilot feedback fixes.
- If pilot finds a blocker: create Phase 2G-fix only for the blocker, keep scope narrow, and do not expand into RAG/citation/source-use or Case Cockpit redesign.
