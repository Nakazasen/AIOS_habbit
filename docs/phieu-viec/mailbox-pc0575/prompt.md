# Ticket deploy-fix-banner-0494 — Pull fix + restart app (máy công ty)

## Bối cảnh
- Vé dieutra-banner-0494 đã ĐẠT: banner "0/494" là do code fallback ở `workspace_chat_app.py:4657`.
- Muse đã sửa trên VM: banner chỉ theo dõi nguồn ĐANG BẬT; 0 nguồn bật → banner ẩn, nút "Tiếp tục" không còn đường enqueue 494 tài liệu đã tắt.
- Commit fix: `e5d37fc` trên nhánh `phieu-viec/rag-fix1` (đã push; test 44/44 pass trên VM).

## Việc cần làm
1. Trên `D:\Sandbox\AIOS_habbit`: `git fetch` + `git pull --rebase` nhánh `phieu-viec/rag-fix1`. Verify `git log --oneline -1` ra `e5d37fc`.
2. Restart app bằng đúng script LAN của vé P5 (`scratch/p5_run_lan.ps1`, giữ nguyên env `AIOS_BGE_ONNX_MODEL_CHECKSUM`). Xác nhận app listen `0.0.0.0:8501`, HTTP 200.
3. Mở sổ "Điều tra lỗi LSU" (0 nguồn đang bật): verify banner "0/494 tài liệu" **không còn hiện**, không còn nút "Tiếp tục chuẩn bị". Chụp màn hình.
4. Báo cáo: `docs/phieu-viec/ket-qua/deploy-fix-banner-0494.md` — HEAD commit, thời gian restart, ảnh chụp verify, app vẫn phục vụ LAN bình thường.

## Cấm
- Không bấm "Thử chuẩn bị lại" / "Tiếp tục chuẩn bị" / "Bật tất cả".
- Không sửa code thêm, không merge `main`. Không đụng ổ D máy nhà.
