# Vé P2 (mẫu) — Mang kho production sang máy công ty (KDTVN-PC0575)

Trạng thái: **CHỜ** — chạy SAU Vé P1 (kho production đã đóng dấu).

Ngày viết: 2026-09-27 (Muse, theo lệnh user 22:43).

## Bối cảnh

- Máy công ty `KDTVN-PC0575`: i5, RAM 16GB, **không GPU** — chạy CPU-only.
- Chỉ copy đúng **1 file sqlite**; mọi thứ khác cài/pin tại chỗ, không copy tay.

## Cấm kỵ

- Cấm hardcode GPU. Backend tự chọn: có GPU → `CUDAExecutionProvider`,
  không GPU → `CPUExecutionProvider`; máy không GPU phải chạy ngay.
- Không copy index đang nhúng dở — chỉ copy kho đã đóng dấu ở P1.
- Không đụng `main`.

## Cách làm (đúng thứ tự)

1. Copy đúng 1 file `workspace_chat.sqlite` (production đã đóng dấu ở P1)
   sang máy công ty; so sha256 + kích thước hai đầu — phải khớp 100%.
2. Cài đúng 3 thứ, pin version (ghi rõ vào báo cáo):
   a. mã code đúng commit (ghi SHA),
   b. `onnxruntime==1.28.0` (fingerprint ghim đúng version này),
   c. model BGE-M3 đúng revision `5617a9f61b028005a4858fdac845db406aefb181`
      (kéo qua mạng, không copy tay).
3. Xác nhận chạy CPU-only (ExecutionProvider = CPU).
4. Smoke test B1–B5 trên máy công ty → **đạt mới đóng vé**.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_P2_may-cong-ty.md` gồm:
sha256 file hai đầu, 3 thứ đã pin (commit / onnxruntime / revision),
provider CPU, kết quả B1–B5 + latency, hostname `KDTVN-PC0575`.
Test "tắt GPU vẫn chạy" là điều kiện bắt buộc (máy này không có GPU).
