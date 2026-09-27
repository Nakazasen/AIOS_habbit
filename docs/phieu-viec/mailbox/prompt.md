# Vé 0 — Điều tra nhịp rơi (KHẨN, làm trước mọi thứ — CHỈ ĐỌC, không sửa)

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Mẻ migration GPU (Vé B) đang chạy trên máy nhà (h410asrock), ghi vector bằng GPU theo mẻ 2.
- Số liệu commit tiến độ 16:04–16:34 cho thấy: **nhịp 10 phút rơi một nửa trong nửa tiếng**.
- Vé B vẫn chạy nền. Vé này CHỈ TÌM BỆNH, KHÔNG SỬA. Sửa là vé khác.

## Nghi phạm (điều tra theo đúng thứ tự ưu tiên)

1. DB phình làm upsert chậm
2. Nóng máy giảm xung (thermal throttling)
3. Batch nghẽn
4. Overhead kiểm tra mỗi batch
5. VRAM cạn

## Cách làm — CHỈ ĐỌC, CẤM ĐỤNG MẺ ĐANG CHẠY

- `nvidia-smi`: nhiệt độ, xung nhịp, VRAM đã dùng/trống — ghi số liệu theo thời gian, không chỉ chụp 1 điểm.
- Kích thước file DB theo giờ (dir / `ls -la` kèm timestamp).
- Timing từng batch trong log migration: thời gian/batch, batch size, xu hướng chậm dần hay rơi đột ngột.
- CẤM TUYỆT ĐỐI: restart/pause mẻ, sửa code, vacuum DB, pull code mới, ghi index, đụng backup.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE0_dieu-tra-nhip-roi.md` gồm đúng 3 mục:
1. Chỉ mặt nguyên nhân (1 nghi phạm chính + bằng chứng số liệu, loại trừ các nghi phạm còn lại bằng số).
2. Cách sửa/giảm đề xuất (để vé sau làm — vé này KHÔNG sửa).
3. Nhịp đã hồi lại hay chưa; nếu chưa, ETA mới cho mẻ migration.

## Ràng buộc

- Commit riêng trên branch `phieu-viec/rag-fix1`, không đụng `main`.
- Không embed thêm, không ghi index, không chạy `--apply` bất cứ thứ gì.
- Số liệu từ lần đo thật trên máy h410asrock, ghi hostname + thời gian đo.
