# Project Handover

## Mục đích

Tài liệu này là handover vận hành ngắn cho repository AIOS WorkLens. Trạng thái
Git, test và remote phải luôn được kiểm tra lại tại thời điểm nhận việc; không
coi một claim lịch sử là trạng thái runtime hiện tại.

## Trạng thái verified gần nhất

- **Primary UI:** Workspace Chat.
- **RAG v2 foundation:** element schema/adapters, converter adapters,
  structure-aware chunking và local SQLite lexical index đã hoàn thành.
- **Cleanup/legacy routes:** `DONE`. Phần triển khai nằm trong `9123caa`;
  compile, `892` tests và CLI audit đều đạt ngày 2026-07-25.
- **Nakazasen AI Router:** đã nâng từ `v0.2.2` lên `v0.4.0`.
  Public imports, focused regressions, live provider smoke và live call qua
  Workspace Chat adapter đều đạt. Live smoke dùng Gemini và dừng sau lần thành
  công đầu tiên.
- **Professionalization Baseline:** `DONE`. Bổ sung security/privacy, ADR,
  architecture/runtime views, quality/CI parity, recovery/release/risk và
  onboarding records; không thay đổi runtime, UI hay cloud-default behavior.
  Docs contract, compile, CLI audit (không errors/warnings), Workspace Chat import
  và full suite `896 passed` đã đạt; synthetic JSONL/SQLite restore drill đã PASS.
- **P0 follow-up:** real Workspace Chat provider route có guard label/consent riêng
  nhưng chưa được chứng minh dùng Gateway sanitizer/preflight như single
  enforcement point. Đây là Gate `PLANNED`, bắt buộc trước external-provider
  release claim.
- **Owner decisions còn chờ:** kênh báo security riêng tư, kênh phân phối/release,
  support matrix, retention/RTO-RPO, named reviewer/CODEOWNERS và dependency
  advisory enforcement.
- **Case Cockpit:** public routes đã gỡ; shared services vẫn được giữ lại để
  audit dependency riêng.
- **Gate RAG tiếp theo:** `RAG-V2-HYBRID-RETRIEVAL-MIN` vẫn `PLANNED`, chưa mở.
- **Known limitation:** lexical retrieval hiện tối giản; query song ngữ có thể
  xếp hạng yếu và PNG chưa có OCR/extraction.
- **AI Gateway:** A15 design, A16 và A17A–A17D đã hoàn thành; A18 chưa mở;
  P1.0 vẫn locked.

## Điều cần kiểm tra trước khi tiếp tục

```powershell
git status --short --branch
git log -1 --oneline
git diff --check
git diff --cached --check
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
```

- Không reset, stage, commit hoặc discard thay đổi không do gate hiện tại tạo ra.
- Đặc biệt xem xét lại staged documentation trước khi đưa vào lịch sử chính thức.
- Giữ `local_cases/`, `local_runs/`, dữ liệu gốc, secrets và runtime artifacts
  ngoài Git.

## Bước tiếp theo

1. Owner xem xét các policy `OWNER_DECISION_REQUIRED` còn mở: security disclosure,
   distribution/support, retention/RTO-RPO, named reviewer/CODEOWNERS và advisory
   enforcement.
2. Trước bất kỳ external-provider release claim nào, owner cần mở
   [AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md](docs/roadmap/backlog/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
   để hợp nhất/kiểm chứng policy boundary cho real route.
3. `RAG-V2-HYBRID-RETRIEVAL-MIN` vẫn `PLANNED`; chỉ owner quyết định thứ tự mở
   sau khi xem xét P0 privacy follow-up.
4. Case Cockpit dependency retirement vẫn là backlog; không xóa shared services
   trước khi dependency/capability matrix được duyệt.
