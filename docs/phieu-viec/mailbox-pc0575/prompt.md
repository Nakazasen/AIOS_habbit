# Vé RESTORE-DRIVE-PC0575 — Khôi phục runtime TẠM từ Drive (bản cũ 30/09)

**Mức ưu tiên:** cao nhất (app chết hoàn toàn khi không có runtime).
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Role OMP gợi ý:** DEFAULT (tải file lớn + verify + audit).
**Xếp hàng:** vé này xong (audit PASS) → phát hành lại `SPEED-COLDSTART-PC0575` từ `prompt-queue-speed-coldstart-pc0575.md` (lưu ý: index đã đổi sang bản 062ec090, mọi số đo phải ghi rõ).

## Bối cảnh

Vé `RECOVER-RUNTIME-PC0575` đã verdict **KHÔNG KHÔI PHỤC ĐƯỢC** (báo cáo `docs/phieu-viec/ket-qua/recover-runtime-pc0575.md`): bản production `e54c7745…` (2.842.415.104 B) không còn ở đâu trên máy; Recycle Bin trống; quét 1.536.807 file chỉ thấy backup cũ.

Đây là vé khôi phục **TẠM** bằng bản cũ trên Drive để app chạy lại được. **Nhãn bắt buộc trong mọi báo cáo sau này: bản TẠM `062ec090` (30/09), KHÔNG phải bản production `e54c7745` đã mất.**

## File nguồn (Muse đã verify trực tiếp trên Drive 05/10 ~16:50)

Thư mục Drive AIOS_Data, tải bằng **command line** (curl/Python — KHÔNG dùng Chrome vì policy công ty từng chặn):

1. **library.sqlite** — index cũ
   - Link: `https://drive.google.com/uc?export=download&id=1cbydCaMAvO9eBRJg5YhZ1T2tj66C10hv`
   - Size: **2.552.659.968 byte** | md5: `7392ef9a54d82926f59569a9e664458f`
2. **bge-m3-onnx-fp32.zip** — cây ONNX đã nghiệm thu
   - Link: `https://drive.google.com/uc?export=download&id=1CnTrdYLfv1ZpbZMo8zivSOxuD1cVDIrG`
   - Size: **1.326.939.447 byte** | md5: `db7baa786e5d485a57eb95619ea6eb7b`

Lưu ý: file lớn qua `uc?export=download` có thể gặp trang cảnh báo virus-scan của Google (trả về HTML thay vì binary) — nếu gặp, thử thêm `&confirm=t` hoặc báo lại. Verify **size + md5** sau tải, sai số nào cũng DỪNG và báo.

## Việc cần làm

### Bước 1 — Tải 2 file về PC0575
- Tải bằng command line vào thư mục tạm (vd `D:\Sandbox\AIOS_habbit\scratch\restore-drive\`).
- Verify size (byte chính xác) + md5 khớp bảng trên. Không khớp → DỪNG, báo `cho-muse`.
- Nếu command line bị chặn hoàn toàn → báo `cho-muse` ghi rõ lỗi (user đã từng tải tay ngày 30/09, đó là đường dự phòng cuối).

### Bước 2 — Đặt đúng path app mong đợi
- **Không hardcode path.** Đọc từ deployment module (`aios_habit.workspace_chat_rag_v2_deployment`) + `config/workspace_chat_rag_v2.local.json` để biết đúng path production index và model mà audit kiểm tra.
- Đặt `library.sqlite` vào đúng path index production (ghi rõ path đã đặt trong báo cáo).
- Giải nén `bge-m3-onnx-fp32.zip` vào đúng thư mục cây ONNX (`models/bge-m3-onnx-fp32` hoặc theo config).
- Nếu audit còn đòi cây `retrieval_models/bge-m3-5617a9f` (30 file HF): tải từ Hugging Face `BAAI/bge-m3` @ `5617a9f` (đã verify tải được ở vé trước), verify `sha256_model_tree` theo manifest.

### Bước 3 — Audit + smoke
- Chạy `python -B -m aios_habit.workspace_chat_rag_v2_deployment` → phải `Status: PASS`.
- Smoke: app khởi động được, hỏi 1 câu đơn giản có trả lời (không cần đo tốc độ ở vé này).

### Bước 4 — Báo cáo
- Viết `docs/phieu-viec/ket-qua/restore-drive-pc0575.md`: path đã đặt, size + md5/SHA đã verify, kết quả audit, nhãn **bản TẠM 062ec090**.
- Audit PASS → `xong-cho-duyet`. Audit FAIL hoặc tải không được → `cho-muse` kèm lỗi chính xác.

## Cấm kỵ
- Không xóa/ghi đè bất cứ dữ liệu nào khác trên máy.
- Không đụng `C:\AIOS_p5\library.sqlite.bak-20260930`.
- Không báo "đã khôi phục production" — luôn ghi rõ **bản TẠM**.
- Commit riêng nhánh `phieu-viec/rag-fix1`, không đụng `main`, không force-push.
