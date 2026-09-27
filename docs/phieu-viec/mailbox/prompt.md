# Vé KHẨN — Dừng P1.3; commit 3 fix retrieval + push ngay

Ngày viết: 2026-09-28 (Muse VM). Lệnh TRỰC TIẾP của user lúc 06:51 +07: dừng mọi việc trên máy nhà.
Chế độ tự lái: Muse ra vé → OMP thực hiện độc lập trên Windows (luật "không vừa đá vừa thổi còi").
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Không force-push. Máy: `h410asrock` (Win 10 Pro).

## 1. Dừng P1.3 ngay
- P1.3 (đóng dấu kho thật) DỪNG NGAY ở bước hiện tại. Cấm chép canary đè production. Bước smoke test B1–B5 để vé sau.
- Đã an toàn trước khi dừng (không mất dữ liệu): backup production D→C xong — 32.452.608 byte, SHA-256 khớp file D cũ, `quick_check=ok`; file nguồn canary 2.552.659.968 byte, `quick_check=ok`. Backup nằm trên ổ C.
- Cấm ghi ổ D (lệnh cấm vĩnh viễn của user vẫn hiệu lực) — vé này không có ngoại lệ ghi nào.

## 2. Commit 3 fix retrieval còn treo + push NGAY
3 fix đã sửa trên máy OMP nhưng chưa commit (xác nhận 2026-09-27):
1. Worker subprocess chết vì `.venv` mất editable-install → spawn kèm `PYTHONPATH=<root>/src` (`bge_subprocess_client.py`);
2. `.env` thêm `BGE_BACKEND=pytorch` tường minh theo đúng quy tắc E-chain (không đụng default ONNX);
3. `RouterRequest` thiếu `safety_mode_label` → router chặn mọi provider (`auto:blocked`) → sửa `rag_v2_synthesis_provider.py` + 2 test.
- Commit thành commit RIÊNG trên nhánh `phieu-viec/rag-fix1` (không gộp với việc khác). Push nhánh NGAY sau commit.
- Không chạy thêm bất cứ việc gì khác: không B1–B5, không chép file, không embed, không benchmark.

## 3. Báo xong
Cập nhật `docs/phieu-viec/mailbox/trang-thai.md`: Trạng thái `xong-cho-duyet`, ghi SHA commit của 3 fix. Không cần báo cáo dài — commit + push là đủ.

## Ghi chú kỹ thuật (để vé sau)
- OMP báo lúc 06:45 +07 (ghi chú từng bị mất do sự cố commit `d2e2458`, đã khôi phục trong `trang-thai.md`): chưa chạy B1–B5 vì (1) chưa rõ tuyến trả lời nào được phép cho B1–B5 khi cầu nối Gemini Web `direct_ready` nhưng quy tắc dữ liệu cấm đưa `local_only` ra ngoài và C-AGENT cần user chọn rõ; (2) `runtime_root` production vẫn nằm trên ổ D — cần cách bảo đảm scheduler không ghi thêm lên D. Báo cáo OMP ở commit `b196d38` ("document safe-route blockers").
- Fingerprint ONNX ghim `onnxruntime==1.28.0` (xác nhận 2026-09-27): copy index sang máy khác phải đồng bộ đúng bản runtime.
