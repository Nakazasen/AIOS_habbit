# Vé FIX-J1CSV-FIXTURE-HOME — Cập nhật fixture test JIG cho đúng cổng SMA(20)

**Máy thực hiện:** NHÀ h410asrock (thợ agy).
**Role gợi ý:** DEFAULT (sửa test + chạy test).

## 0. ĐIỀU KIỆN BẮT ĐẦU (cổng gate — đọc trước khi làm gì khác)

Vé này CHỈ được bắt đầu SAU khi `docs/phieu-viec/mailbox/trang-thai.md` (thợ OMP)
có dòng `` `ghi_chu` (verdict Muse) `` với verdict **ĐẠT** cho vé `SMA-IMPROVE-HOME`.
Lý do: OMP đang sửa `trend_alerts.py` (deadband + k linh hoạt); fixture test phải
khớp hành vi cổng gate CUỐI CÙNG, viết sớm sẽ phải làm lại.

- Kiểm tra ngay khi nhận vé. Nếu chưa có verdict ĐẠT: append một dòng
  `` `ghi_chu`: <giờ> +07 — chờ OMP xong SMA-IMPROVE-HOME, chưa đủ điều kiện bắt đầu. ``
  vào `trang-thai.md` của mailbox này, GIỮ NGUYÊN `Trạng thái: `moi``, rồi DỪNG
  (watcher sẽ mở lại vé ở vòng sau — kiểm lại cổng gate mỗi lần mở).

## Bối cảnh

Báo cáo `AUDIT-BUOC2-JIG-HOME` (vừa ĐẠT) phát hiện 1 điểm lệch (mục P0 #2):
test `test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh` trong `tests/test_j1_csv.py`
dùng 1 điểm vi phạm đơn lẻ `99.9` trên nền 20 điểm `10.0`. Từ commit `846713e`
(03/10), cổng gate SMA(20) chặn đúng điểm xấu đơn lẻ (`canh_bao = False`) nên
biểu đồ cảnh báo không tự vẽ → test lệch với hành vi cổng hiện tại.

## Việc cần làm

1. Cập nhật fixture của test trên: thay 1 điểm xấu đơn lẻ bằng CHUỖI 3 ĐIỂM XẤU
   LIÊN TIẾP để kích hoạt cảnh báo xu hướng đúng logic cổng SMA(20) sau vé
   `SMA-IMPROVE-HOME` (đọc kỹ hành vi gate mới trong `trend_alerts.py` sau khi
   OMP xong — nhưng KHÔNG SỬA file đó).
2. Chỉ sửa fixture/kỳ vọng trong `tests/test_j1_csv.py`; không sửa logic gate,
   không sửa code sản phẩm.
3. Chạy: `tests/test_j1_csv.py` phải xanh 100%; hồi quy `tests/test_trend_alerts.py`
   không được đỏ thêm so với trước vé.
4. Báo cáo `docs/phieu-viec/ket-qua/fix-j1csv-fixture-home.md`: fixture cũ/mới,
   số test trước/sau, xác nhận khớp hành vi gate sau SMA-IMPROVE.

## Rào cứng

- Không merge `main`. Python 3.11 (không dùng syntax 3.12+).
- 1 file 1 đứa: KHÔNG đụng `trend_alerts.py` (của OMP) và không đụng UI.
- Heartbeat: mốc tiến độ tối thiểu 15 phút/lần trong `trang-thai.md`
  (vé ngắn, chỉ cần 1-2 mốc + chốt).

