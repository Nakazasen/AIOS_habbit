# Vé P1.2 — Xác định kho production thật của collection tri_thuc (chỉ đọc)

Ngày viết: 2026-09-28 (Muse). Chế độ tự lái: Muse ra vé → OMP thực hiện độc lập
trên Windows (luật "không vừa đá vừa thổi còi").
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Máy: `h410asrock` (Win 10 Pro).
Thuộc chuỗi P1 (đóng dấu kho thật); bước 1 của P1 đã đạt, không làm lại.

## Verdict Vé P1.1: CHƯA ĐẠT đóng dấu — nhưng KHÔNG phải lỗi OMP

- OMP dừng đúng theo vé (fail-closed): `storage_root` của collection `tri_thuc`
  rỗng, chưa có bằng chứng xác định runtime/profile production; không bịa đường
  dẫn, không backup mù, không chép đè, không chạy B1–B5, không ghi index nào.
  Báo cáo `docs/phieu-viec/ket-qua/VE_P1_1_dong-dau-kho-that.md` (commit `bdda73c`).
- Lỗi ở phía Muse: vé P1.1 bảo OMP "mở app → xem storage root" mà không cho chuỗi
  phân giải chính xác. Vé này đính chính bằng code thật (đã tra độc lập).

## Sự thật từ code (Muse đã verify từ repo + test, không đoán)

1. App chạy từ repo root: `RUN_AIOS_WORKSPACE_CHAT.bat` làm `cd /d "%~dp0"`
   → cwd = thư mục repo mà user thật sự mở app.
2. `WorkspaceChatRagV2CanaryConfig.from_env()`
   (`src/aios_habit/workspace_chat_rag_v2_adapter.py`):
   - Deployment manifest: env `AIOS_WORKSPACE_RAG_V2_MANIFEST`, nếu không có thì
     `<repo_root>/config/workspace_chat_rag_v2.local.json`. Nếu tồn tại VÀ activated
     thì `runtime_root`/`requested_profile` lấy từ manifest.
   - Nếu không: env `AIOS_WORKSPACE_RAG_V2_RUNTIME_ROOT` (mặc định
     `local_runs/workspace_chat_rag_v2_canary`, tương đối so với cwd) và
     `AIOS_WORKSPACE_RAG_V2_PROFILE` (mặc định `bge_m3_hybrid`).
   - `.env` local cũng được nạp (`load_env_file()` trong `workspace_paths.py`).
3. Collection `tri_thuc` = `DEFAULT_COLLECTION_ID` (`workspace_chat_models.py`),
   `storage_root` rỗng → `collection_runtime_layout("tri_thuc", profile_root)`
   (`workspace_chat_store.py`) trả về `<profile_root>/collections/tri_thuc`,
   file = `library.sqlite`. Test `test_default_collection_uses_dedicated_folder`
   trong `tests/test_workspace_chat_store.py` khẳng định đúng công thức này.
4. Với mặc định và cwd = repo root:
   `<repo_root>\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
5. Gợi ý từ lượt dò trước: `collections.jsonl` nằm ở
   `C:\c\AIOS_ve03_worktree\local_cases\workspace_chat\collections.jsonl`
   → repo root nghi vấn là `C:\c\AIOS_ve03_worktree`. CẦN XÁC NHẬN đây có phải
   checkout mà user mở app hay không (`git worktree list` + shortcut mở app).
   LƯU Ý: vẫn có khả năng user mở app từ checkout khác — xác nhận, không đoán.

## Cách làm (chỉ đọc, đúng thứ tự)

1. Xác nhận checkout app: `git worktree list` trên máy; đối chiếu với shortcut/
   cách user mở app (file .bat nào được bấm). Ghi rõ repo root được xác nhận.
2. Từ repo root đã xác nhận, chạy one-liner CHỈ ĐỌC bằng `.venv` của repo
   (cwd = repo root, KHÔNG mở Streamlit):
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
   Ghi nguyên output vào báo cáo.
3. Ghi rõ chuỗi override nào đã kích hoạt: manifest tồn tại + activated?
   (đường dẫn manifest nào), env nào được set (kiểm tra cả `.env` local)?
   Hay toàn bộ mặc định?
4. Nếu file library tồn tại: kiểm tra read-only `PRAGMA quick_check` + kích thước,
   ghi vào báo cáo. Nếu KHÔNG tồn tại: DỪNG fail-closed, báo lại, không suy đoán
   sang đường dẫn khác.

## Cấm kỵ

- Chỉ đọc. Không backup, không copy, không chép đè, không chạy B1–B5 trong vé này
  (đó là P1.3 sau khi đường dẫn được xác nhận).
- Cấm vĩnh viễn GHI ổ D. Mọi thao tác trên ổ C.
- Không `git pull` tạo merge — `git fetch` + checkout commit rõ ràng. Không đụng `main`.
- Không sửa code/test để "cho qua" — fail thì báo nguyên vẹn kèm số đo.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_P1_2_xac-dinh-kho-production.md` gồm:
1. Repo root đã xác nhận + bằng chứng (worktree list / shortcut).
2. Output nguyên văn của one-liner + chuỗi override kích hoạt (manifest/env/mặc định).
3. Kết quả tồn tại + quick_check + kích thước của `library.sqlite` production.
4. Hostname máy chạy, thời điểm kiểm tra.

Tiêu chí ĐẠT: đường dẫn production được xác định bằng chuỗi phân giải đầy đủ
(repo root → manifest/env → runtime_root/profile → collections/tri_thuc/library.sqlite),
có bằng chứng từng bước. Không cần đoán.

## Sau vé này

Vé P1.2 đạt → Muse phát hành Vé P1.3 "backup + chép canary đè production +
B1–B5 + đóng dấu". Không tự mở P1.3 trước verdict.
