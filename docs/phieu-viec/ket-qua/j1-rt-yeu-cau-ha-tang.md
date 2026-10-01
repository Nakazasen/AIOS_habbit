# Yêu cầu hạ tầng phía công ty cho JIG realtime (J1-RT)

Danh sách cụ thể để user/công ty quyết và chuẩn bị. Phần mềm (spec API +
prototype) đã xong trong vé này; các mục dưới đây là việc triển khai thật tại
xưởng, không thuộc phạm vi vé.

## 1. Máy chủ (server)

- Một máy chạy 24/7 trong mạng LAN công ty để host cổng nhận log
  (`POST /api/v1/jig/stream-log`) và cổng phục vụ AI (`GET /api/v1/jig/events`).
  Có thể tận dụng máy đang chạy app AIOS LAN hiện tại.
- Cấu hình tối thiểu: CPU 4 nhân, RAM 8 GB, ổ cứng trống ≥ 20 GB cho SQLite +
  log quay vòng. Không cần GPU.
- Hệ điều hành: Windows 10/11 hoặc Linux; Python 3.11; service tự khởi động lại
  khi mất điện/khởi động lại máy.
- Backup SQLite định kỳ (theo quy trình backup chung của công ty).

## 2. Mạng

- Jig và server nằm chung LAN nội bộ (không cần internet, không mở port ra ngoài).
- Mở 1 port TCP nội bộ cho cổng nhận log (mặc định prototype: 8765; đổi được
  khi cấu hình).
- IP tĩnh (hoặc tên máy cố định) cho server để agent trên jig không phải sửa
  cấu hình khi DHCP đổi IP.

## 3. Agent thu log trên jig (phía xưởng)

- Trên mỗi máy đo/jig (vd máy Iris): một agent nhỏ (script/service) đọc file
  log CSV mà máy xuất ra, chuyển thành bản tin JSON theo format ở
  `j1-rt-api-spec.md` và POST theo lô về server mỗi 5–30 giây.
- Agent cần biết: mã jig (`jig_id`), token xác thực riêng của jig đó, địa chỉ
  server. Token do quản trị cấp, lưu trong file cấu hình trên máy jig, không
  hardcode trong code.
- Xử lý khi mất mạng: agent giữ hàng đợi trên đĩa tại chỗ, gửi bù khi mạng
  trở lại (không để mất dữ liệu đo).

## 4. Bảo mật

- Mỗi jig một Bearer token riêng; thu hồi/đổi token khi thay người phụ trách.
- Server chỉ bind IP LAN, không bind `0.0.0.0` ra internet.
- Log vận hành không ghi token ra file.

## 5. Vận hành và giám sát

- Người phụ trách: khi AI phát cảnh báo drift, ai nhận và xử lý (gắn với quy
  trình cảnh báo qua mail đã có ở J1-CSV).
- Giám sát: kiểm tra mỗi ngày agent còn gửi log (server ghi nhận số dòng/phút);
  cảnh báo khi một jig im lặng quá 30 phút trong giờ sản xuất.
- Dữ liệu phát lại mô phỏng (`SIMULATED_REALTIME`) chỉ dùng khi kiểm thử;
  vận hành thật luôn dùng nhãn `that`.

## 6. Thứ tự triển khai gợi ý

1. Chốt máy chủ + IP tĩnh + port.
2. Cài agent thử trên 1 jig (vd 2ND-1035), chạy 1 ca, đối chiếu số dòng
   server nhận với file log gốc.
3. Bật AI consumer poll sự kiện + cảnh báo mail cho jig thử.
4. Nhân rộng ra các jig còn lại sau khi ca thử ổn định.
