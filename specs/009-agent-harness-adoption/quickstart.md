# Hướng dẫn xác minh theo cổng

Tài liệu này là hướng dẫn nghiệm thu, không phải lệnh bật quyền ghi production.

## G0 — Kiểm tra kế hoạch

```powershell
uv run --no-sync --group dev python scripts/check_docs.py
git diff --check
```

Kỳ vọng: hợp đồng tài liệu đạt; ADR-0008 và Gate Card active dẫn đến feature 009; chưa có code runtime mới.

## G1 — Spike chỉ đọc

1. Pin phiên bản và checksum OpenCode trong evidence của Gate Card.
2. Chạy server chỉ trên `127.0.0.1` với xác thực cục bộ.
3. Chạy health/version/session/event/read/search probe trên repo fixture.
4. Thử edit và command khi policy `deny`.

Kỳ vọng: đọc/search đúng; write/command không chạy và file digest không đổi. Nếu thiếu session resume, event stream hoặc deny thực, ghi `BLOCKED` và dừng.

## G3–G4 — Vòng coding

Chạy lần lượt các tình huống trong `spec.md`: bug một file, refactor nhiều file, create/rename/delete, command dài/cancel, restart/resume, conflict, path traversal, secret, dirty workspace, Unicode và reject/cancel.

Kỳ vọng: main workspace không đổi trước duyệt; observed verifier xác nhận test; rollback sạch.

## G8 — Nghiệm thu cuối

Chạy 10 task cố định với cùng model, thời gian và quyền cho AIOS và baseline; 12/12 tình huống an toàn bắt buộc phải đạt. Sau đó chạy toàn bộ cổng AIOS:

```powershell
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

Chỉ sau clean-machine Windows E2E và các lệnh trên đạt mới được mô tả là đủ dùng hằng ngày trong phạm vi đã kiểm chứng.
