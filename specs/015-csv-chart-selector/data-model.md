# Mô hình dữ liệu: Chọn biểu đồ khi nhập tệp CSV LSU

**Ngày**: 18/09/2026 | **Tính năng**: `015-csv-chart-selector`

## Thực thể 1 — Gói dữ liệu đã nhập

- **Là gì**: Tập hợp các tệp người dùng vừa tải trong phiên, đã qua kiểm tra cổng dữ liệu.
- **Thuộc tính**: mã gói, thời điểm nhập, danh sách mã JIG có trong gói, trạng thái hợp lệ, digest truy vết.
- **Quy tắc**: Chỉ dùng gói đang ở trạng thái hợp lệ hoặc hợp lệ có cảnh báo để vẽ; gói bị chặn phải báo và hướng dẫn sửa, không cho vẽ.

## Thực thể 2 — Chỉ số đo

- **Là gì**: Một đại lượng đo từ JIG có thể vẽ được.
- **Thuộc tính**: mã gốc trong tệp, tên tiếng Việt dễ hiểu, đơn vị đo, mã JIG sở hữu, nhóm ưu tiên (ưu tiên nhóm độ lệch và độ nghiêng 4 màu).
- **Quy tắc**: Chỉ liệt kê chỉ số đo được; cột ngày giờ, mã sản phẩm, kết quả đạt/lỗi, thời gian nhịp và mã nội bộ không được liệt kê làm chỉ số vẽ. Tệp đo sâu không tiêu đề được nhận diện theo vị trí cột thường gặp.

## Thực thể 3 — Lựa chọn biểu đồ

- **Là gì**: Bộ lựa chọn của người dùng cho một lần xem.
- **Thuộc tính**: mã JIG, tên chỉ số, 1 trong 3 loại (xu hướng theo thời gian, phân bố giá trị, so sánh theo màu), loại ảnh (PNG hoặc SVG).
- **Quy tắc**: Đổi bất kỳ thành phần nào cũng vẽ lại mà không tải lại tệp; câu chat thiếu thành phần nào thì hỏi lại đúng thành phần đó.

## Thực thể 4 — Ảnh biểu đồ xem trước

- **Là gì**: Ảnh kết quả đúng lựa chọn, dùng chung cho xem trước, tải về và email.
- **Thuộc tính**: ảnh PNG 300 DPI hoặc SVG, tem thông tin (mã JIG, tên chỉ số, loại biểu đồ, ngày giờ, mã gói nguồn), digest truy vết.
- **Quy tắc**: Ảnh chỉ chứa số liệu tổng hợp đã vẽ, không đính kèm dòng dữ liệu thô hay đường dẫn tuyệt đối; tệp tạm phải dọn sau khi dùng.

## Quan hệ

```text
Gói dữ liệu đã nhập ── chứa ──► Chỉ số đo
Lựa chọn biểu đồ ── trỏ tới ──► 1 Gói + 1 JIG + 1 Chỉ số + 1 Loại
Ảnh xem trước ── vẽ từ ──► 1 Lựa chọn biểu đồ
```
