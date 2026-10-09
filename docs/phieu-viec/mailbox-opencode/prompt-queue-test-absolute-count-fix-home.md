# VÉ: TEST-ABSOLUTE-COUNT-FIX-HOME (đổi hai ca còn ghim số tuyệt đối của kho sang khẳng định quan hệ)

- Mã vé: `TEST-ABSOLUTE-COUNT-FIX-HOME`
- Role gợi ý: DEFAULT (opencode — thợ phụ tạm thời, máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/test-absolute-count-fix-home.md`
- Bối cảnh: vé rà soát `TEST-NESTED-GUARD-SCAN-HOME` đã lập bảng toàn bộ thư mục kiểm thử và chỉ ra hai ca còn ghim con số tuyệt đối của kho hiện tại — khi kho lớn lên một cách hợp lệ, hai ca này sẽ đỏ oan dù hành vi đúng. Vé này sửa đúng hai ca đó, theo cùng cách vé dọn dẹp trước đây đã xử lý các ca tương tự.

## Việc phải làm

1. **Ca đếm trên chỉ mục production thật** (`test_production_index_counts` trong `tests/test_index_status.py`): bỏ phần ghim `== 149800` và `== 889`. Giữ nguyên phần khẳng định có giá trị: số hiển thị phải khớp số đọc trực tiếp từ cơ sở dữ liệu ở cả hai con số. Phần vân tay cũng đổi sang quan hệ: hai đường đọc phải cho cùng một vân tay và đúng độ dài hiển thị, không ghim chuỗi cụ thể của kho hiện tại. Điều kiện bỏ qua khi vắng chỉ mục production giữ nguyên.
2. **Ca bản đồ miền** (`test_domain_document_map_counts` trong `tests/test_workspace_chat_production_index_filtering.py`): bỏ các con số ghim 889 / 92 / 681 / 44 / 72. Đổi sang khẳng định quan hệ: bốn miền rời nhau hoàn toàn, tổng số tài liệu của bốn miền bằng tổng số của bản đồ, mỗi miền có ít nhất một tài liệu, và số đọc qua hàm lấy theo miền phải khớp số đọc trực tiếp từ bản đồ đã nạp. Không giữ lại bất kỳ con số tuyệt đối nào của kho hiện tại trong ca này.
3. **Kiểm chứng sau sửa:** chạy lại hai tệp chứa hai ca trên tại máy nhà và ghi kết quả đầy đủ vào báo cáo; nếu có ca nào khác trong hai tệp này đỏ, dừng và báo cáo nguyên văn thay vì sửa tiếp ngoài phạm vi.

## Rào cứng

- Chỉ sửa hai ca nêu trên; không sửa mã chạy thật, không sửa ca nào khác. Không ghi chỉ mục (băm trước/sau khớp nếu có đọc tới). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần.
