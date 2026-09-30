# Ticket LSU-1 — Chạy pipeline Bước 0–5 trên list LSU thật (dữ liệu thật)

## Bối cảnh
Vé `buoc0-deploy` (ĐẠT) đã chạy pipeline Bước 0–5 E2E trên list điều tra lỗi thật
(15.707 ca từ `Loi KDTPS.xlsx`, 4 bảng mã lỗi thật 3.820 mục). List LSU
(log jig, log 6 pcs theo chuỗi, tài liệu LSU) chưa chạy qua pipeline lần nào.
Báo cáo mẫu làm đúng độ kỹ: `docs/phieu-viec/ket-qua/buoc0-deploy.md`.

## Việc cần làm
1. Chuẩn bị dữ liệu: kiểm tra `C:/tmp/aios-v14-data/` đã có gói LSU chưa.
   Nếu chưa: tải từ Drive AIOS_Data (thư mục LSU), đối chiếu SHA-256 từng file,
   ghi SHA vào báo cáo (theo mẫu Vé V1.4 đã làm với gói điều tra lỗi).
2. Chạy pipeline Bước 0–5 trên dữ liệu LSU thật: DB + output + log đặt trên ổ C
   (vd `C:/tmp/lsu1-deploy/`); tuyệt đối không ghi ổ D; không ghi index production RAG.
3. Nếu importer hiện tại chưa hỗ trợ định dạng log LSU (log jig / log 6 pcs):
   mở rộng importer (code + test, commit riêng), rồi chạy lại pipeline.
4. Kiểm tra output đúng format, đủ 6 mốc (Bước 0→5), không exception.

## Tiêu chí ĐẠT
- Pipeline exit 0, đủ Bước 0→5, số liệu thật từng bước ghi trong báo cáo
  (số dòng đọc/nhập, số ca, gate, cảnh báo).
- Bộ test error_cases (93 bài) vẫn pass trên Windows Python 3.11.
- Dữ liệu mô phỏng (nếu cần) gắn mác `SIMULATED_*`; dữ liệu thật không commit vào Git.

## Cấm
- Không ghi index production. Không đụng ổ D (mọi ghi trên ổ C).
- Không merge `main`. Không force-push.

## Báo cáo
`docs/phieu-viec/ket-qua/lsu1-deploy.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
