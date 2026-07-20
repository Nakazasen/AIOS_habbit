# AIOS WorkLens

AIOS WorkLens là môi trường tri thức công việc **local-first**. Luồng sử dụng
chính là: mở Workspace Chat, thêm hoặc chọn nguồn cục bộ, hỏi bằng ngôn ngữ tự
nhiên và nhận câu trả lời có ngữ cảnh nguồn.

> [!IMPORTANT]
> **Workspace Chat là giao diện duy nhất dành cho người dùng thông thường.**
> Case Cockpit và Habit Studio cũ đang được retirement; chúng không còn là một
> phần của quick start hay runbook vận hành.

## Bắt đầu nhanh trên Windows

1. Cài Python 3.11 trở lên.
2. Tại thư mục repository, cài môi trường local:

   ```powershell
   py -3 -m pip install -e .
   ```

3. Mở [RUN_AIOS_WORKSPACE_CHAT.bat](RUN_AIOS_WORKSPACE_CHAT.bat).

   Hoặc chạy PowerShell:

   ```powershell
   .\scripts\run_workspace_chat.ps1
   ```

4. Trong Workspace Chat: tạo/chọn workspace, thêm/chọn tài liệu, rồi đặt câu
   hỏi. Không cần nhớ thuật ngữ RAG, bridge, provider hoặc gate.

## Tài liệu chính thức

- [ROADMAP.md](ROADMAP.md) — roadmap/index canonical và gate đang mở.
- [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) — trạng thái bàn giao ngắn, rủi ro
  và bước kế tiếp.
- [WORKLENS_ARCHITECTURE.md](WORKLENS_ARCHITECTURE.md) — ranh giới kiến trúc
  hiện hành.
- [docs/roadmap/README.md](docs/roadmap/README.md) — quy ước Gate Card.
- [docs/runbooks/operator.md](docs/runbooks/operator.md) — quy trình dùng app.
- [docs/runbooks/developer.md](docs/runbooks/developer.md) — setup, validation
  và quy tắc release cho developer.
- [docs/legacy/RETIREMENT_MANIFEST.md](docs/legacy/RETIREMENT_MANIFEST.md) —
  inventory legacy và trạng thái dọn dẹp.

## Kiểm thử và audit

```powershell
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
git diff --check
git status --short --ignored
```

## An toàn dữ liệu local

Không commit dữ liệu runtime hoặc dữ liệu riêng tư: `local_cases/`,
`local_runs/`, JSONL evidence/memory, tài liệu gốc, ảnh/screenshot, `.env`,
tokens, credentials và cache. Cloud/NotebookLM không phải điều kiện để dùng
Workspace Chat local.
