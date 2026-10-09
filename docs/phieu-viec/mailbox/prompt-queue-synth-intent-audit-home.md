# VÉ: SYNTH-INTENT-AUDIT-HOME (nộp lại bảng đo đúng sự thật + chẩn đoán hiện tượng qua kiểm định tăng nhưng điểm tổng giảm)

- Mã vé: `SYNTH-INTENT-AUDIT-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-intent-audit-home.md`
- Căn cứ: điều phối kiểm chứng độc lập vé `SYNTH-INTENT-CLASSIFY-HOME` từ chính file dữ kiện thô đã nộp và phát hiện bức tranh hai mặt mà báo cáo vé đó không trình bày: số câu qua kiểm định tăng thật từ 5 lên 20 (đếm theo trường chế độ trong file thô — phần này đúng và ghi nhận), **nhưng tổng điểm toàn lượt giảm từ 64,17 xuống 38,5** (điểm trung bình 1,28 xuống 0,77), 26 câu tụt điểm so với lượt trước, và bảng số trong báo cáo có nhiều chỗ sai so với file thô (danh sách câu qua kiểm định chứa 3 mã câu không tồn tại trong file thô và ít nhất 5 câu thực tế là rơi về trích cục bộ với 0 điểm; số câu đạt từ 2,0 điểm ghi 19 trong khi đếm thật là 9). Vé này làm rõ toàn bộ sự thật trước khi bất kỳ kết luận nào về hướng đi được rút ra.

## Việc phải làm

0. **Đính chính báo cáo vé phân loại:** bổ sung mục đính chính có ngày giờ vào cuối báo cáo `docs/phieu-viec/ket-qua/synth-intent-classify-home.md` (không sửa, không xoá nội dung cũ): ghi tổng điểm thật và điểm trung bình thật của lượt đo, số câu đạt từ 2,0 điểm thật, và danh sách câu qua kiểm định đúng theo trường chế độ của file dữ kiện thô đã nộp. Mọi con số trong mục đính chính phải đếm từ file thô, điều phối sẽ đếm lại đối chiếu.
1. **Chẩn đoán hiện tượng đánh đổi (chỉ đọc, không sửa mã):** đối chiếu điểm từng câu giữa hai file dữ kiện thô (lượt áp ngân sách và lượt phân loại), phân nhóm 26 câu tụt điểm theo chế độ mới, và trả lời bằng bằng chứng cụ thể:
   - Đường trả lời theo kiểu trích dẫn-trước (chế độ chiếm số đông trong nhóm tụt) hoạt động thế nào ở dạng câu hỏi chẩn đoán: vì sao hàng loạt câu nhận 0 điểm trong khi đường trích xuất cũ cho 1,0 điểm — khác biệt nằm ở nội dung đáp án, ở cách chấm, hay ở điều kiện kích hoạt?
   - Nhóm câu không gọi mô hình (8 câu ở lượt mới): cổng nào chặn, điều kiện gì, có đúng chủ đích không?
   - Các câu qua kiểm định tăng thêm có điểm thế nào; tổng điểm mất đi tập trung ở nhóm câu/chế độ nào.
   - Kết luận trung thực: đây là lỗi định tuyến/điều kiện kích hoạt có thể sửa được, hay là cái giá thật khi ép các câu khó đi đường tổng hợp sâu — kèm đề xuất hướng xử lý cụ thể để điều phối quyết định (không tự thực thi trong vé này).
2. Nộp bảng đối chiếu điểm từng câu (50 dòng: mã câu, điểm cũ, điểm mới, chế độ cũ, chế độ mới) làm tệp dữ kiện kèm theo báo cáo.

## Rào cứng

- Vé này chỉ gồm đính chính tài liệu và chẩn đoán chỉ đọc: không sửa mã chạy thật, không đo lại lượt mới, không ghi chỉ mục. Không merge `main`.
- Mọi con số phải truy được về file dữ kiện thô hoặc dòng mã cụ thể; không kết luận bằng suy đoán. Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
- Mốc tiến độ tối thiểu 15 phút/lần.
