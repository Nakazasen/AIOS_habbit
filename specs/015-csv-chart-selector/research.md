# Nghiên cứu giai đoạn 0: Chọn biểu đồ khi nhập tệp CSV LSU

**Ngày**: 18/09/2026 | **Tính năng**: `015-csv-chart-selector`

## Quyết định 1 — Ba loại biểu đồ dùng chung một hàm dựng dữ liệu

- **Quyết định**: Giữ một hàm dựng dữ liệu dùng chung cho cả ô chọn và câu chat; hỗ trợ 3 loại là xu hướng theo thời gian, phân bố giá trị, so sánh theo màu; mỗi lần xem chọn 1 loại.
- **Vì sao**: Hai đường vào cùng một lõi thì ảnh xem trước và ảnh email giống nhau, ít code mới, dễ kiểm thử, hợp ý người dùng đã chốt.
- **Phương án đã cân nhắc**: Chỉ làm 1 loại xu hướng cho nhanh; làm 3 lõi riêng cho 3 loại. Phương án 1 loại bị loại vì người dùng muốn chọn 1 trong 3; phương án 3 lõi riêng bị loại vì trùng lặp và khó giữ nhất quán với email.

## Quyết định 2 — Vẽ bằng thư viện ảnh nhẹ sẵn có, không thêm thư viện biểu đồ nặng

- **Quyết định**: Mở rộng `spc_chart.py` hiện có để vẽ cả 3 loại, xuất PNG 300 DPI và SVG, tái dùng cho cả xem trước và email.
- **Vì sao**: Lõi hiện tại đã có kiểm thử, chạy tốt trên máy CPU, bề mặt kiểm toán nhỏ; ảnh email và ảnh xem trước là một thì không phải vẽ lại.
- **Phương án đã cân nhắc**: Thêm thư viện biểu đồ nặng để vẽ nhanh. Bị loại vì tăng phụ thuộc, nặng máy demo và trái luật chống thiết kế quá mức.

## Quyết định 3 — Danh sách chỉ số ưu tiên nhóm độ lệch và độ nghiêng 4 màu

- **Quyết định**: Khi tệp rộng hàng trăm cột, liệt kê trước nhóm độ lệch và độ nghiêng theo 4 màu (đen, hồng, xanh, vàng) bằng tên tiếng Việt kèm mã gốc; các nhóm đường kính chùm tia, vị trí, thời gian nhịp để ở nhóm sau.
- **Vì sao**: Khớp đích BOWSKEW 4 BEAM đã chốt trong hợp đồng, khớp manifest 49 tệp vừa khảo sát (cột độ lệch, độ nghiêng theo màu và vị trí chiếm đa số), giúp demo 23/09 đi thẳng vào trọng tâm.
- **Phương án đã cân nhắc**: Liệt kê toàn bộ cột theo thứ tự bảng chữ cái. Bị loại vì người không chuyên khó tìm, dễ chọn nhầm cột kỹ thuật nội bộ.

## Quyết định 4 — Hỗ trợ cả CSV và Excel ngay từ đầu

- **Quyết định**: Nhận cả CSV và Excel (XLSX, XLSM) bằng đường đọc hiện có của cổng dữ liệu; giữ nguyên giới hạn máy đã công bố.
- **Vì sao**: Log JIG thực tế có cả hai dạng; màn hình hiện tại đã nhận cả hai nên không tốn thêm nhiều công.
- **Phương án đã cân nhắc**: Chỉ CSV trước, Excel để nhịp sau. Bị loại vì người dùng đã chốt hỗ trợ cả hai và dữ liệu thử nghiệm có tệp Excel đi kèm.

## Quyết định 5 — Tệp đo sâu không tiêu đề được tự nhận diện linh hoạt

- **Quyết định**: Với tệp đo sâu 3 cột không có dòng tiêu đề, tự nhận diện theo vị trí cột thường gặp (ngày giờ, mã sản phẩm, chuỗi giá trị đo); chỉ khi mơ hồ mới hỏi bổ sung ngắn gọn, không bắt xuất lại từ đầu.
- **Vì sao**: Đúng mong muốn “linh hoạt và thông minh nhất” của người dùng; tránh cảm giác ức chế khi bị bắt làm lại; vẫn an toàn vì trường hợp mơ hồ không tự đoán mò.
- **Phương án đã cân nhắc**: Bắt xuất lại tệp đúng mẫu trong mọi trường hợp. Bị loại vì gây ức chế và không cần thiết khi mẫu 3 cột đã ổn định qua khảo sát.

## Quyết định 6 — Không thêm màn hình hay kho mới

- **Quyết định**: Khối chọn nằm gọn dưới kết quả cổng dữ liệu ở Thẻ 1; câu chat gọi đúng hàm dựng chung; không thêm trang cài đặt, bảng DB hay tác vụ nền.
- **Vì sao**: Giữ triết lý một khung chat và màn hình gọn, đủ cho demo và hạn bù 15/10, dễ hoàn tác.
- **Phương án đã cân nhắc**: Dựng trang biểu đồ riêng. Bị loại vì thừa phạm vi và tăng công kiểm thử tiếng Việt.
