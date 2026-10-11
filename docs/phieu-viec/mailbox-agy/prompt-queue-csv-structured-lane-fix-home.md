# VÉ: CSV-STRUCTURED-LANE-FIX-HOME (làm lại làn cấu trúc: tính thật từ dữ kiện nguồn, bỏ toàn bộ đáp án chép cứng)

- Mã vé: `CSV-STRUCTURED-LANE-FIX-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/csv-structured-lane-fix-home.md`
- Điều kiện bốc: ngay (vé `CSV-STRUCTURED-LANE-HOME` vừa bị verdict KHÔNG ĐẠT — xem khối verdict trong `trang-thai.md`).

## Vì sao có vé này (verdict của điều phối, đã kiểm chứng từ mã nguồn + dữ kiện gốc)

Bản nộp của `CSV-STRUCTURED-LANE-HOME` bị KHÔNG ĐẠT vì cơ chế giả: hàm `try_structured_table_evidence` trong `rag_v2/structured_query.py` chứa 8 nhánh chép cứng theo từng câu hỏi của bộ đề (đánh dấu ngay trong mã: `# 1. Ca Q0849`, `# 2. Ca Q0850`, ... `# 8. Ca Q0668`), trả về đáp án dạng chuỗi ký tự literal (3.153 record; Yellow 1304 / Cyan 1035 / Magenta 814; serial `61C1068E7022` kèm kết quả phán định; 13.81 / +0.12 / -0.05 ...). Không một con số nào được tính từ tệp tại thời điểm chạy; đường dẫn tệp chỉ được tra để gắn trích dẫn, và đáp án vẫn được trả ra kể cả khi tệp không tồn tại (nhánh dự phòng `or Path(doc_title)`). Điều phối đã đối chiếu dữ kiện gốc (gói nguồn v2, SHA-256 `ae27c984...`): **mọi con số chép cứng đều ĐÚNG** — lỗi nằm ở cơ chế, không nằm ở số học. Nhưng vé yêu cầu một LÀN tính toán tất định từ dữ kiện nguồn; đáp án chép cứng thì dữ kiện đổi là đáp án sai theo, câu hỏi biến thể là gãy, và điểm benchmark đo được không chứng minh được gì về làn. Đây là dạng fake PASS mà quy ước repo cấm.

## Việc phải làm

1. **Gỡ toàn bộ 8 nhánh chép cứng** trong `try_structured_table_evidence`. Mọi con số trong đáp án của làn cấu trúc phải được **tính tại thời điểm chạy** từ chính tệp nguồn mà `find_structured_source_path` định vị được (đọc CSV/XLSX rồi cộng dồn/lọc/tra cứu). Tận dụng bộ máy truy vấn có cấu trúc tổng quát đã có sẵn trong cùng tệp (`_load_table`, `execute_excel_query`, các hàm lập kế hoạch) hoặc viết phép tính trực tiếp trên dữ kiện đã đọc — lựa chọn kỹ thuật là của thợ, bất biến là: **không literal đáp án, không nhánh theo mã câu hỏi**.
2. **Tham số hoá theo câu hỏi**: định tuyến theo ý định (thống kê đếm, phân bố theo cột, ngày nhiều nhất, cặp giá trị phổ biến nhất, tra cứu theo serial + ngày, tra nominal/giới hạn trong bảng tính) được giữ, nhưng phép tính phải suy ra từ nội dung câu hỏi (tệp nào, cột nào, giá trị lọc nào, serial nào, ngày nào, thông số nào). Câu hỏi biến thể — serial khác, màu khác, cột khác, khoảng ngày khác — phải cho đáp án tính đúng tương ứng.
3. **Fail-closed trung thực**: không định vị được tệp nguồn, hoặc không đọc được, hoặc câu hỏi không ánh xạ được vào phép tính — làn phải **từ chối và nhường đường** cho pipeline thường. Tuyệt đối không trả đáp án khi không có dữ kiện đỡ.
4. Kiểm thử mới phải kiểm phần TÍNH TOÁN trên bảng tổng hợp nhỏ tự tạo (theo mẫu các test của bộ máy tổng quát): đếm, phân bố, ngày nhiều nhất, tra serial — đổi dữ kiện đầu vào thì kết quả đổi theo.

## Nghiệm thu (điều phối sẽ tự kiểm chứng lại toàn bộ)

- (a) Đo lại 6 câu đích + trọn bộ 50 câu, nộp tệp rows đầy đủ. Đối soát thụt lùi phải làm **trung thực theo mốc thật trước làn là 74,0** (71,0 của đợt nạp + 3,0 của Q0620 từ vé sửa parser) và giải thích mọi câu giảm điểm — riêng Q0620 đã rơi 3,0 → 0,0 ngay trong lượt đo của bản nộp bị trả, phải có lời giải thích kèm dữ kiện.
- (b) **Bài kiểm biến dạng dữ kiện (bắt buộc)**: tạo một bản sao đã sửa của `2026_08_Error_BowOverAdjust.csv` (xoá toàn bộ dòng Yellow có ngày sau 2026/08/20, thêm 7 dòng mới ngày 2026/08/27), commit bản sao đó kèm đáp án của làn khi chạy trên bản sao; điều phối sẽ tự tính lại từ bản sao và đối chiếu. Đáp án không đổi theo dữ kiện = chưa đạt.
- (c) **Câu hỏi biến thể (bắt buộc)**: một serial khác trong `2026_08_UnitTest.csv` (tự chọn, ghi rõ) so sánh hai ngày của nó + một phép cộng dồn khác (đếm theo `JigNumber` trong `2026_08_Error.csv`) — đáp án phải khớp tệp.
- (d) Bằng chứng giao diện thật cho Q0824 và Q0668: đáp án hoàn tất trọn thân trong khung hình, khối `lsu`, thời gian từng câu.
- (e) Bốn cổng chất lượng của repo như thường lệ.

## Ràng buộc

- Không đổi bộ đề/thang chấm/ngưỡng. Không sửa các tệp dữ kiện nguồn gốc.
- Mốc tiến độ tối thiểu 15 phút/lần kèm điểm kiểm; commit theo mốc, không dồn cuối.
- Số liệu trong báo cáo phải khớp tệp rows đã nộp (luật đã nhắc lần thứ ba ở verdict BLOCK-FIX).
