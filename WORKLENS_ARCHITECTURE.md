# WorkLens Architecture & Modular Boundaries

## 1. Kiến trúc hiện tại

AIOS WorkLens là một ứng dụng **local-first** với **Workspace Chat** là primary
UI. Người dùng thêm/chọn nguồn cục bộ, hỏi tự nhiên và nhận phản hồi theo source
context. UI không được biến thành Case Cockpit mới.

```text
Workspace Chat UI
  → workspace/chat models + local stores
  → source ingestion + source selection
  → local retrieval / answer composition boundaries
  → privacy and safety policy
  → local runtime data (Git ignored)
```

RAG v2 được xây tách khỏi UI theo các boundary element → converter → chunk →
local index → retrieval → synthesis. Core RAG v2 phải generic, deterministic
khi có thể, privacy-preserving và không chứa hard-code domain/pilot.

## 2. Product boundaries

| Boundary | Trách nhiệm | Quy tắc |
|---|---|---|
| Workspace Chat | Luồng hàng ngày: workspace, nguồn, hỏi/đáp | Vietnamese-first, simple, không lộ technical workflow |
| Source & Notebook | Metadata, upload, parsing, source selection | Local-first, source privacy rõ ràng |
| RAG v2 | Element/converter/chunk/index/retrieval/synthesis | Không provider/network/UI import trong core |
| AI Gateway / Bridge | Export-import có policy, observed validation evidence | Không tự chạy lệnh do report đưa vào; owner-triggered verification |
| Case domain services | Case/evidence/audit/map/handover legacy-compatible | Audit dependency trước khi rename/migrate/delete |
| Runtime data | `local_cases/`, `local_runs/`, private source/assets | Luôn Git ignored, không bị cleanup source xóa |

## 3. Legacy boundary

`studio.py` và `case_cockpit.py` không được coi là primary UI. Workspace Chat
không được import chúng. Các direct launch routes, package scripts, tests và
documentation của legacy được inventory trong
[RETIREMENT_MANIFEST.md](docs/legacy/RETIREMENT_MANIFEST.md).

- Studio/public routes: retirement slice riêng, có launcher Workspace Chat thay
  thế và regression tests.
- Case Cockpit: không xóa cùng lúc với shared `case_*`/visual-map/handoff
  services. Dependency graph và capability replacement phải được audit trước.
- Git history là archive code đã xóa; documentation history được phân loại bằng
  [docs/archive/README.md](docs/archive/README.md).

## 4. Constraints không được phá

1. `local_only` evidence và raw local sources không được đi ra cloud/NotebookLM
   khi không có policy/owner permission phù hợp.
2. Runtime/private files không được stage hoặc commit.
3. Workspace Chat phải giữ boundary không import Studio/Case Cockpit.
4. Không claim `PASS` nếu không có command/test evidence của gate hiện tại.
5. Mọi migration/deletion có rollback rõ ràng và full validation sau slice.
