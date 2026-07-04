# Workspace Chat Phase 2I Notebook Lifecycle Owner Smoke Result

## Baseline

- Branch: `main`
- HEAD: `062afbb4247f747f3f9dcb4115b0714f36ba8daa`
- `origin/main`: `062afbb4247f747f3f9dcb4115b0714f36ba8daa`
- Scope baseline: pushed Phase 2I notebook lifecycle implementation commit.

## Scope

This owner smoke covered Workspace Chat Phase 2I notebook lifecycle behavior:

- notebook archive, hide, and restore flow;
- no hard delete UI or destructive lifecycle path;
- privacy regression quick smoke after archive/restore;
- targeted check for stale active session behavior when an archived notebook is active.

## Results summary

| Check | Result |
| --- | --- |
| Core archive/restore smoke | `PASS` |
| Privacy quick smoke | `PASS` |
| Runtime import issue | Resolved by Streamlit restart, no code change |
| Targeted stale-session smoke | `PASS_WITH_ACCEPTED_GAP` |
| Overall owner smoke result | `PASS_WITH_ACCEPTED_GAP_ACCEPTED_FOR_PHASE2I` |

## Exact UI copy verified

The owner smoke verified these exact strings in the UI:

- `Sổ đã lưu trữ`
- `Lưu trữ sổ`
- `Sổ này sẽ được ẩn khỏi danh sách chính. Dữ liệu bên trong không bị xóa.`
- `Không xóa dữ liệu trong Phase 2I.`
- `Khôi phục sổ`
- `Đã khôi phục sổ.`
- `Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư.`

## First smoke failure

The first browser smoke failed with this runtime import error:

```text
ImportError: cannot import name 'load_active_notebooks' from 'aios_habit.workspace_chat_store'
```

Runtime diagnosis showed this was not a code bug:

- direct `workspace_chat_store` import passed;
- direct helper import passed;
- app import passed;
- `compileall` passed;
- `workspace_chat_store.py` exposed the required helpers:
  - `load_active_notebooks`
  - `load_archived_notebooks`
  - `archive_notebook`
  - `restore_notebook`

Root cause was a stale Streamlit process or old module cache from the pre-restart runtime.
After Streamlit restart, the app loaded and the smoke proceeded successfully.
No code change was required or made for this issue.

## Core smoke evidence

After Streamlit restart:

- app loaded successfully;
- notebook list was visible;
- `Sổ đã lưu trữ` section was visible;
- `Lưu trữ sổ` action was visible;
- archive confirmation displayed the exact safety copy;
- cancel action worked;
- archive action worked;
- archived notebook appeared in the archived section;
- archived notebook showed `Khôi phục sổ`;
- archived notebook did not show the normal open action;
- restore action worked;
- restored notebook reopened normally;
- no hard delete UI was observed;
- no provider or cloud auto-call was observed.

## Data and privacy evidence

The smoke preserved data and privacy expectations:

- restored notebook opened normally after restore;
- notebook sources remained visible;
- local-only enabled source still blocked AI;
- the block message matched exactly:
  `Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư.`
- no partial send was observed;
- archive/restore did not call the provider;
- archive/restore did not trigger cloud behavior.

## Accepted gap

Targeted stale-session smoke result: `PASS_WITH_ACCEPTED_GAP`.

The stale two-session browser path was not browser-verified end to end.
Reason: two independent browser sessions could not be safely reproduced with the available tool without runtime or session manipulation.

Evidence supporting expected behavior remains sufficient for Phase 2I MVP acceptance:

- active notebook is resolved through `load_active_notebooks()`;
- if a notebook is archived or otherwise not active, the app clears `wsc_active_notebook_id`;
- the app also clears `wsc_active_conversation_id`;
- the app calls `safe_rerun()` and then `st.stop()`;
- automated tests cover the stale-session path structurally;
- no browser crash was observed;
- Streamlit health/load stayed OK;
- validation stayed PASS;
- worktree and runtime dirty checks stayed clean.

Recommended future hardening task:

```text
HARDEN_WORKSPACE_CHAT_PHASE2I_STALE_SESSION_BROWSER_AUTOMATION
```

## Final decision

Phase 2I Notebook Lifecycle can be marked owner-smoke `PASS_WITH_ACCEPTED_GAP`.
The stale two-session browser automation gap is accepted for the Phase 2I MVP.
This gap should not block the next roadmap item or gate.
