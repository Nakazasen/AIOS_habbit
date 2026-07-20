# Project Handover

## Mục đích

Tài liệu này là handover vận hành ngắn cho repository AIOS WorkLens. Trạng thái
Git, test và remote phải luôn được kiểm tra lại tại thời điểm nhận việc; không
coi một claim lịch sử là trạng thái runtime hiện tại.

## Trạng thái verified gần nhất

- **Primary UI:** Workspace Chat.
- **RAG v2 foundation:** element schema/adapters, converter adapters,
  structure-aware chunking và local SQLite lexical index đã hoàn thành.
- **Gate tiếp theo sau cleanup:** `RAG-V2-HYBRID-RETRIEVAL-MIN`.
- **Known limitation:** lexical retrieval hiện tối giản; query song ngữ có thể
  xếp hạng yếu và PNG chưa có OCR/extraction.
- **AI Gateway:** A17A–A17D đã được ghi nhận hoàn thành trong roadmap/changelog;
  A18 chưa mở; P1.0 vẫn locked.
- **Legacy:** Studio/Case Cockpit không phải UI chính. Studio và public legacy
  routes đang được retirement theo manifest; Case Cockpit cần một dependency
  slice riêng trước khi xóa monolith/shared services.

## Điều cần kiểm tra trước khi tiếp tục

```powershell
git status --short --branch
git log -1 --oneline
git diff --check
git diff --cached --check
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
```

- Không reset, stage, commit hoặc discard thay đổi không do gate hiện tại tạo ra.
- Đặc biệt xem xét lại staged documentation trước khi đưa vào lịch sử chính thức.
- Giữ `local_cases/`, `local_runs/`, dữ liệu gốc, secrets và runtime artifacts
  ngoài Git.

## Bước tiếp theo

1. Hoàn thành documentation reset và Studio/public-route retirement theo
   [RETIREMENT_MANIFEST.md](docs/legacy/RETIREMENT_MANIFEST.md).
2. Chạy full validation sau mỗi retirement slice.
3. Mở slice dependency/migration riêng cho Case Cockpit; không xóa các
   `case_*`/visual-map/handoff services còn được dùng ở nơi khác.
4. Sau cleanup, mở Gate Card
   [RAG-V2-HYBRID-RETRIEVAL-MIN.md](docs/roadmap/active/RAG-V2-HYBRID-RETRIEVAL-MIN.md).
