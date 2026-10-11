# VÉ: STRUCTURED-LANE-TEST-FIXTURE-HOME (chuyển test của làn cấu trúc sang dữ kiện tổng hợp)

- Mã vé: `STRUCTURED-LANE-TEST-FIXTURE-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/structured-lane-test-fixture-home.md`
- Điều kiện bốc: ngay (vé `DISK-CLEANUP-ROUND3-HOME` đã verdict ĐẠT).

## Việc phải làm

Test `test_structured_table_lane_targets` trong `tests/test_rag_v2_structured_query.py` hiện gọi làn cấu trúc lên các tệp dữ kiện THẬT tại máy (không có tệp là rớt — điều phối đã chứng kiến nó rớt trên máy không có dữ kiện, trong khi làn từ chối đúng thiết kế fail-closed). Một test phụ thuộc dữ kiện production tại máy sẽ rớt trên mọi máy sạch/CI và ở PC0575, làm nhiễu cổng chất lượng.

Chuyển test này (và mọi test nào khác trong cùng tệp có cùng bệnh — tự rà) sang dữ kiện tổng hợp nhỏ tự tạo trong thư mục tạm (theo đúng mẫu các test bộ máy truy vấn tổng quát đã có trong cùng tệp: dựng CSV/XLSX nhỏ, chạy làn qua tham số đường dẫn nguồn tuỳ chỉnh, khẳng định kết quả tính). Yêu cầu:
- Bộ khẳng định giữ nguyên độ phủ hành vi hiện có: đếm bản ghi + khoảng ngày, phân bố theo cột, ngày đông nhất, tra serial đa ngày, nominal/giới hạn bảng tính — mỗi hành vi ít nhất một ca trên dữ kiện tổng hợp, và ít nhất một ca khẳng định "đổi dữ kiện thì kết quả đổi theo".
- Sau khi sửa, toàn bộ tệp test phải đạt trên máy KHÔNG có các tệp dữ kiện production (tự kiểm bằng cách tạm đổi tên thư mục dữ kiện nguồn trong lúc chạy test, hoặc chạy trong thư mục làm việc sạch — ghi rõ cách kiểm vào báo cáo).
- Không đổi hành vi của làn; không nới lỏng khẳng định để lấy đạt.

## Nghiệm thu
- Chạy đủ 4 cổng chất lượng của repo; riêng tệp test trên phải đạt cả ở môi trường sạch dữ kiện như mô tả trên.
- Báo cáo liệt kê: test nào đã chuyển, dữ kiện tổng hợp của từng ca, kết quả trước/sau.
