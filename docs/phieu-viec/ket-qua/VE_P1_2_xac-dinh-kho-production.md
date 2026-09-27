# Báo cáo Vé P1.2 — Xác định kho production thật của collection tri_thuc (chỉ đọc)

## Kết quả

**ĐẠT phạm vi chỉ đọc: đã xác định đường dẫn production bằng chuỗi phân giải đầy đủ.** Không backup, không copy, không chép đè, không chạy B1–B5 trong vé này (theo vé, đó là P1.3). Không ghi vào bất kỳ tệp chỉ mục nào. Mọi kiểm tra index đều mở read-only.

## 1. Repo root đã xác nhận + bằng chứng

- Repo root được xác nhận: `D:/Sandbox/AIOS_habbit` (máy `h410asrock`).
- Bằng chứng:
  - `git worktree list` (chạy tại `D:/Sandbox/AIOS_habbit`): dòng đầu `D:/Sandbox/AIOS_habbit 8f5ddfe [phieu-viec/rag-fix1]` — chính checkout đang làm mailbox. Checkout nghi vấn `C:/c/AIOS_ve03_worktree` ở commit cũ `c6aa083`, không phải checkout đang nhận vé.
  - `RUN_AIOS_WORKSPACE_CHAT.bat` làm `cd /d "%~dp0"` nên cwd = thư mục repo nơi user bấm file. File `.bat` tồn tại ở cả hai checkout nên riêng nó chưa phân biệt — phần phân biệt nằm dưới.
  - Chỉ `D:/Sandbox/AIOS_habbit` có đủ runtime thật: `.venv/Scripts/python.exe` tồn tại; `C:/c/AIOS_ve03_worktree/.venv/Scripts/python.exe` KHÔNG tồn tại.
  - Chỉ `D` có manifest `config/workspace_chat_rag_v2.local.json` (activated); ở `C` file này KHÔNG tồn tại.
  - Chỉ `D` có `.env` local và `local_runs/retrieval_models/bge-m3-5617a9f`; ở `C` cả hai đều KHÔNG tồn tại.
  - Biến môi trường máy/process đều trỏ `D`: `AIOS_WORKSPACE_RAG_V2_RUNTIME_ROOT=D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary`, `AIOS_BGE_M3_MODEL_PATH=D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f`.
  - Thư mục `tri_thuc` ở `C` (`C:/c/AIOS_ve03_worktree/local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc`) RỖNG (0 file); ở `D` có `library.sqlite` + backup. Nên `C` không thể là nơi app đang chạy kho thật.
  - Không tìm thấy shortcut AIOS trên Desktop/TaskBar (dò `*.lnk` Desktop và TaskBar, không có mục AIOS/Workspace) nên user mở app bằng cách bấm trực tiếp file `.bat` trong thư mục repo — kết hợp các bằng chứng trên, repo đó là `D:/Sandbox/AIOS_habbit`.
  - `collections.jsonl` ở `D` (`D:/Sandbox/AIOS_habbit/local_cases/workspace_chat/collections.jsonl`): bản ghi `tri_thuc` có `storage_root` rỗng (giống ở `C`). Vì vậy đường dẫn library đi theo nhánh fallback `profile/collections/tri_thuc`, không theo `storage_root`.

## 2. Output nguyên văn one-liner + chuỗi override kích hoạt

Lệnh chạy tại cwd = repo root đã xác nhận, KHÔNG mở Streamlit, chỉ đọc (lần đầu thiếu `PYTHONPATH` nên báo `ModuleNotFoundError: No module named 'aios_habit'`; chạy lại với `PYTHONPATH=<repo>/src` giống `.bat` thì đạt):

```python
from pathlib import Path
from aios_habit.workspace_chat_rag_v2_adapter import WorkspaceChatRagV2CanaryConfig
from aios_habit.workspace_chat_store import collection_runtime_layout, DEFAULT_COLLECTION_ID
cfg = WorkspaceChatRagV2CanaryConfig.from_env()
profile_root = cfg.runtime_root / cfg.requested_profile
root, name = collection_runtime_layout(DEFAULT_COLLECTION_ID, profile_root)
print("runtime_root:", cfg.runtime_root)
print("requested_profile:", cfg.requested_profile)
print("library:", root / name)
print("exists:", (root / name).is_file())
```

Output nguyên văn:

```text
runtime_root: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production
requested_profile: bge_m3_hybrid
library: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite
exists: True
```

Chuỗi override kích hoạt (theo code `workspace_chat_rag_v2_adapter.py::from_env` + `workspace_chat_rag_v2_deployment.py::load_workspace_chat_rag_v2_deployment`):

- Manifest `D:\Sandbox\AIOS_habbit\config\workspace_chat_rag_v2.local.json` TỒN TẠI và `activation_state=activated` → `runtime_root`/`requested_profile` lấy từ manifest. Kiểm tra độc lập: `state: activated`, `profile: bge_m3_hybrid`, `runtime_root: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production`, `manifest_path` đúng file trên.
- Env `AIOS_WORKSPACE_RAG_V2_MANIFEST` KHÔNG được set nên dùng manifest mặc định `<repo_root>/config/workspace_chat_rag_v2.local.json`.
- Env `AIOS_WORKSPACE_RAG_V2_RUNTIME_ROOT` (trỏ `..._canary`) và `AIOS_WORKSPACE_RAG_V2_PROFILE=bge_m3_hybrid` tồn tại ở cả process và `.env` local, NHƯNG BỊ manifest đè — khi manifest activated hợp lệ thì nhánh env không dùng tới. Đây là điểm mấu chốt giải thích vì sao máy có env canary mà app vẫn chạy production.
- `.env` local được nạp qua `load_env_file()` (chỉ điền key chưa có), trong đó có các key `AIOS_WORKSPACE_RAG_V2_*` trỏ `D:\Sandbox\AIOS_habbit\...`. Nội dung secret (API key) trong `.env` KHÔNG chép vào báo cáo này.
- `storage_root` rỗng → `collection_runtime_layout("tri_thuc", profile_root)` trả `<profile_root>/collections/tri_thuc` + `library.sqlite`, khớp công thức vé nêu và test `test_default_collection_uses_dedicated_folder`.

## 3. Tồn tại + quick_check + kích thước của library.sqlite production

- Đường dẫn production: `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
- Tồn tại: `True` (one-liner trên).
- `PRAGMA quick_check` (mở `mode=ro`, chỉ đọc): `ok`.
- Kích thước: `32452608` byte.
- Không backup/copy/chép đè trong vé này.

## 4. Hostname, thời điểm

- Máy: `h410asrock`.
- Thời điểm kiểm tra: 2026-09-28 05:34 giờ `+07` (quick_check xong lúc này; one-liner chạy ngay trước).
- Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`, không tạo merge (`git fetch` + làm trên nhánh vé).

## Ghi chú cho Vé P1.3

- Đường dẫn production đã chốt ở trên; kho canary `C:\AIOS_habit_index_ve03\library.sqlite` (bước 1 vé P1 đã đạt) là file khác, chưa copy đè trong vé này.
- P1.3 cần backup file production này trước khi thay, rồi so sha256 + kích thước 100% như vé P1.1 đã quy định.
