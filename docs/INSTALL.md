# Cài đặt

Dùng Python 3.11 trở lên. AIOS WorkLens chạy local-first; không cần cloud service
để dùng Workspace Chat.

## Workspace Chat

1. Tại root repository, cài package local:

   ```powershell
   py -3 -m pip install -e .
   ```

2. Mở `RUN_AIOS_WORKSPACE_CHAT.bat`.

   Hoặc dùng PowerShell:

   ```powershell
   .\scripts\run_workspace_chat.ps1
   ```

Launcher sẽ kiểm tra Streamlit; nếu chưa có, nó cài dependencies local trước khi
mở Workspace Chat.

## CLI cho developer

```powershell
aios-habit --help
```

Xem validation/release workflow tại [runbooks/developer.md](runbooks/developer.md).
