# Vé AUDIT-BUOC2-JIG-HOME — Rà soát readiness Bước 2 tool JIG (hạn 15/10)

**Máy thực hiện:** NHÀ h410asrock (thợ agy).
**Role gợi ý:** PLAN (rà soát + lập danh sách việc, không code).

## Bối cảnh

Lộ trình tool JIG: Bước 2 (hạn 15/10, còn 9 ngày) — "xác nhận/chỉnh sửa chức năng
Bước 1 trước khi đưa người dùng thử". Cần một danh sách chốt: cái gì đã xong,
cái gì còn thiếu.

## Việc cần làm (chỉ đọc + rà soát, không sửa code)

1. Liệt kê toàn bộ chức năng Bước 1 theo kế hoạch công ty (ảnh 30/09):
   nhập CSV, watch từng dòng, 9 biểu đồ, cảnh báo ngưỡng, cảnh báo xu hướng,
   mail kèm biểu đồ, API realtime, thu thập dữ liệu từ user.
2. Với từng chức năng: đã có test không? đã chạy trên dữ liệu thật không?
   Ghi rõ bằng chứng (tên test / báo cáo).
3. LOẠI TRỪ cổng SMA(20) khỏi phạm vi (thợ OMP đang sửa ở vé `SMA-IMPROVE-HOME` —
   không rà trùng, không đụng file).
4. Chốt danh sách việc còn thiếu cho Bước 2, xếp theo độ gấp, ước lượng độ lớn.
5. Báo cáo `docs/phieu-viec/ket-qua/audit-buoc2-jig-home.md`.

## Rào cứng

- Không sửa code. Không merge `main`.
- Chỉ nêu sự thật có bằng chứng; chỗ nào không kiểm được thì ghi "chưa rõ".
