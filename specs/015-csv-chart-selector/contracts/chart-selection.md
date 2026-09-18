# Hợp đồng: Chọn và vẽ biểu đồ từ gói dữ liệu đã nhập

**Ngày**: 18/09/2026 | **Tính năng**: `015-csv-chart-selector`

## Đầu vào

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `ma_goi` | Có | Mã gói dữ liệu đã báo hợp lệ trong phiên |
| `ma_jig` | Có | Mã JIG cần xem, chọn từ danh sách gợi ý |
| `ten_chi_so` | Có | Tên chỉ số đo, ưu tiên nhóm độ lệch và độ nghiêng 4 màu |
| `loai_bieu_do` | Có | Một trong 3 giá trị: xu hướng theo thời gian, phân bố giá trị, so sánh theo màu |
| `loai_anh` | Có | PNG hoặc SVG |

## Đầu ra

| Trường | Ý nghĩa |
|---|---|
| `anh_xem_truoc` | Ảnh đúng lựa chọn, có đường giới hạn và tem thông tin |
| `ma_truy_vet` | Mã truy vết về gói dữ liệu nguồn |
| `thong_bao` | Câu tiếng Việt báo thành công hoặc hướng dẫn khi lỗi |

## Mẫu câu chat được hiểu

- `vẽ biểu đồ độ lệch cho JIG-01`
- `xem phân bố độ nghiêng màu đen JIG-02`
- `so sánh 4 màu chỉ số độ lệch JIG-01`
- Khi thiếu mã JIG hoặc tên chỉ số, hệ thống hỏi lại đúng phần thiếu bằng tiếng Việt.

## Lỗi và cách báo

| Tình huống | Cách báo tiếng Việt |
|---|---|
| Chưa có gói hợp lệ | Báo chưa có dữ liệu và hướng dẫn quay lại bước tải tệp |
| Sai mã JIG hoặc chỉ số | Báo không tìm thấy và gợi ý danh sách gần đúng |
| Tệp trống hoặc vượt giới hạn | Báo nguyên nhân đơn giản và cách tách nhỏ tệp |
| Tệp đo sâu không tiêu đề nhưng rõ mẫu | Tự nhận diện, không bắt xuất lại |
| Trường hợp mơ hồ | Hỏi bổ sung ngắn gọn, không tự đoán mò |
