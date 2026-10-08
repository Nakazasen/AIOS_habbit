# VÉ: TEST-SUITE-HYGIENE-HOME (dọn nốt nhóm ca đỏ môi trường để toàn bộ suite thành tín hiệu sạch)

- Mã vé: `TEST-SUITE-HYGIENE-HOME`
- Role gợi ý: DEFAULT (OMP — thợ phụ, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/test-suite-hygiene-home.md`
- Căn cứ: sau vé `TEST-STALE-GUARDS-HOME` (đã verdict ĐẠT), toàn bộ suite còn khoảng 24 ca đỏ đã phân loại sơ bộ là môi trường/thiếu tệp của máy khác (theo mục 6 báo cáo vé `SYNTH-DEEPSEEK-PROTOCOL-HOME`): nhóm thiếu tệp nguồn theo đường dẫn máy khác (báo lỗi thu thập), ca bảo vệ quyền riêng tư phụ thuộc phân giải tên miền, ca cần mô hình cục bộ không có trên máy, ca kho dữ liệu trên máy khác số lượng kỳ vọng của máy này, và vài ca đơn lẻ đã ghi tên trong các báo cáo trước. Mục tiêu của vé: mỗi ca hoặc xanh thật, hoặc được đánh dấu bỏ qua có điều kiện kèm lý do rõ ràng trong mã test — để từ nay bất kỳ ca đỏ mới nào trong suite đều là tín hiệu hồi quy thật cần điều tra, không còn nhiễu nền.

## Việc phải làm

1. **Lập bảng kê đầy đủ các ca đỏ còn lại** từ một lượt chạy toàn bộ suite tại đầu nhánh hiện tại: tên ca, nhóm nguyên nhân, bằng chứng (thông báo lỗi gốc). Không dựa vào danh sách cũ — chạy thật để lấy danh sách hiện hành.
2. **Xử lý theo nhóm, đúng nguyên tắc:**
   - Ca thiếu tệp/dữ liệu của máy khác: chuyển thành bỏ qua có điều kiện — chỉ bỏ qua khi tệp nguồn thật sự vắng mặt, và mã test phải ghi rõ đường dẫn điều kiện + lý do. Khi tệp có mặt, test phải chạy thật như cũ (không bỏ qua vô điều kiện).
   - Ca phụ thuộc môi trường ngoài (phân giải tên miền, dịch vụ cục bộ): tương tự — bỏ qua có điều kiện khi điều kiện vắng mặt, kèm lý do.
   - Ca kỳ vọng số lượng gắn với kho dữ liệu của một máy cụ thể: sửa kỳ vọng thành quan hệ đúng với dữ liệu đầu vào của chính test (tự dựng dữ liệu) nếu làm được mà không đổi ý nghĩa; nếu không, bỏ qua có điều kiện kèm lý do.
   - **Bất kỳ ca nào truy ra là hồi quy chức năng thật: DỪNG ở chẩn đoán chi tiết, không sửa test che lấp, không đổi mã chạy thật.**
3. Chạy lại toàn bộ suite sau khi dọn: báo cáo phải cho ra bảng kết quả cuối — số đạt / số bỏ qua có điều kiện / số còn đỏ (kỳ vọng 0 đỏ ngoài danh sách chẩn đoán hồi quy nếu có). Nộp bảng kê đối chiếu trước/sau từng ca.

## Rào cứng

- Chỉ sửa test và cơ chế bỏ qua có điều kiện; không đổi mã chạy thật; không nới lỏng bất kỳ khẳng định hành vi nào đang đúng. Không ghi chỉ mục. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần (lượt chạy toàn bộ suite dài — dùng checkpoint theo nhóm ca). Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
