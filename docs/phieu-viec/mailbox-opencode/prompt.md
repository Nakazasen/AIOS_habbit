# VÉ: TEST-HEALTH-ROUND2-HOME (chạy lại toàn bộ test ở máy nhà sau chùm sửa — đối chiếu vòng 1)

- Mã vé: `TEST-HEALTH-ROUND2-HOME`
- Role gợi ý: DEFAULT (chạy + phân loại, không sửa code ở vé này)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/test-health-round2-home.md`
- Căn cứ: vòng 1 (`test-health-home.md`): 4.200 test, 45 đỏ (23 môi trường / 0 flaky / 22 nghi code). Từ đó đến nay đã khép: nhóm riêng tư + eval_harness + dev_cli (TEST-RED22-FIX), CJK prefilter, composer synthesis, test index_status (đọc production thật). Vòng 2 để chốt sổ bằng số đo mới, không bằng niềm tin.

## Việc phải làm

1. Chạy lại TOÀN BỘ pytest ở máy nhà (một lượt tới khi xong như vòng 1; nếu giữa chừng có vé khác đang chạy nặng trên máy thì ghi rõ điều kiện chạy vào báo cáo).
2. Đối chiếu từng điểm đỏ với bảng phân loại vòng 1: (a) đỏ cũ thuộc nhóm môi trường — còn nguyên hay đã hết (chỉ rõ từng ca, vd test index_status phải XANH vì đã sửa đường đọc); (b) đỏ cũ nhóm code — xác nhận đã hết; (c) đỏ MỚI chưa từng xuất hiện ở vòng 1 — truy vết gốc rễ tới nơi tới chốn và phân loại (môi trường / flaky — chạy lại riêng lẻ để phân biệt / nghi code thật kèm bằng chứng).
3. Riêng 3 test synthesis_provider (vòng 1 đỏ ở nhà, xanh trên VM): kết luận lại ở vòng này — còn lệch máy không, và nếu còn thì truy vết khác biệt môi trường cụ thể.
4. Báo cáo kết: tổng số test, số xanh/đỏ, bảng đối chiếu vòng 1 → vòng 2, danh sách đỏ còn lại kèm phân loại cuối cùng. KHÔNG sửa code ở vé này; nếu còn đỏ nghi code thật thì mô tả đủ để điều phối phát vé sửa.

## Rào cứng

- Chỉ chạy + phân loại; không sửa src/tests; không ghi index; không merge `main`.
