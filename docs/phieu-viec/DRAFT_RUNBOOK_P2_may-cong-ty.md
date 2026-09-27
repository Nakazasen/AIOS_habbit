# DRAFT — Runbook P2: Mang kho production sang máy công ty (KDTVN-PC0575)

Trạng thái: **DRAFT** — chạy SAU Vé P1 (kho production đã đóng dấu) và sau G2.
Một lúc một vé. Không merge `main`.

Ngày viết: 2026-09-28 (Muse).

## 0. Điều kiện vào

- [ ] P1 ĐẠT: production `library.sqlite` đã đóng dấu (integrity_check=ok,
      SHA-256 đã ghi trong báo cáo P1).
- [ ] G2 ĐẠT trên máy nhà (gate fingerprint + 10 câu query thật).
- [ ] Máy công ty `KDTVN-PC0575` bật, vào được mạng LAN, đủ chỗ đĩa
      (file ~1,8GB + chỗ thở).

## 1. Chuẩn bị trên máy công ty (KDTVN-PC0575)

Máy này **không GPU** — mọi bước dưới là CPU-only.

1. Cài Python 3.11 (khớp máy nhà: 3.11.14).
2. Checkout đúng commit đã ghi trong báo cáo P1/G2
   (`git fetch && git checkout <SHA>` — ghi SHA vào báo cáo).
3. Cài `onnxruntime==1.28.0` **đúng version** (fingerprint ghim version này;
   lệch version là lệch fingerprint → gate báo pending).
4. Kéo model BGE-M3 **qua mạng**, đúng revision
   `5617a9f61b028005a4858fdac845db406aefb181`. Cấm copy tay file model.
5. KHÔNG đặt `BGE_BACKEND` (giữ default ONNX). Cấm hardcode GPU.

## 2. Copy kho (đúng 1 file)

1. Copy `library.sqlite` production từ máy nhà sang máy công ty.
2. So **SHA-256 + kích thước** hai đầu — phải khớp 100% mới làm tiếp.
3. `PRAGMA integrity_check` trên file đã copy → phải `ok`.
4. Cấm copy kho đang nhúng dở; chỉ copy kho đã đóng dấu ở P1.

## 3. Smoke test B1–B5 trên máy công ty

1. Xác nhận `ExecutionProvider = CPU` (log khởi động backend).
2. Chạy B1–B5 (bộ câu hỏi chuẩn đã dùng ở P1) → ghi latency từng câu.
3. Đạt mới đóng vé. Câu nào fail → ghi nguyên văn lỗi, không sửa vội.

## 4. Báo cáo đóng vé

`docs/phieu-viec/ket-qua/VE_P2_may-cong-ty.md` gồm:
SHA-256 file hai đầu, 3 thứ đã pin (commit code / onnxruntime 1.28.0 /
revision BGE-M3), provider CPU, kết quả B1–B5 + latency, hostname
`KDTVN-PC0575`, người thực hiện, ngày giờ.

## Rollback

Xóa file đã copy trên máy công ty là xong (máy nhà giữ bản production).
Không có gì để "hoàn tác" thêm.
