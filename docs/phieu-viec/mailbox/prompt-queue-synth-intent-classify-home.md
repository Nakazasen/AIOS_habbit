# VÉ: SYNTH-INTENT-CLASSIFY-HOME (sửa bộ phân loại dạng câu hỏi để ngân sách luận điểm 10 kích hoạt đúng + đo lại kiểm chứng nhân-quả)

- Mã vé: `SYNTH-INTENT-CLASSIFY-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-intent-classify-home.md`
- Căn cứ: vé `SYNTH-CLAIMBUDGET-APPLY-HOME` đã áp ngân sách luận điểm 10 cho dạng câu hỏi chẩn đoán/tra cứu vào mã nguồn, nhưng điều phối đếm lại từ dữ kiện thô của chính lượt đo đó cho thấy **không câu nào trong 50 câu có ngân sách kế hoạch bằng 10** (19 câu ghi 5, 31 câu không ghi) — vì bộ phân loại dạng câu hỏi không gán dạng chẩn đoán/tra cứu cho các câu hỏi kỹ thuật LSU (phần lớn viết bằng tiếng Nhật/Trung, ngắn, chứa mã lỗi và ký hiệu kỹ thuật). Thay đổi ngân sách vì thế chưa hề tác động lên lượt đo; mức tăng điểm ở lượt áp dụng không được gán nhân-quả cho ngân sách. Vé này sửa đúng mắt xích còn thiếu đó rồi đo lại để kiểm chứng nhân-quả một cách trung thực.

## Việc phải làm

0. **Đính chính báo cáo vé trước:** bổ sung một mục đính chính ngắn vào cuối báo cáo `docs/phieu-viec/ket-qua/synth-claimbudget-apply-home.md`: (a) kết luận nhân-quả ở mục kết luận của báo cáo đó là vượt quá bằng chứng — ngân sách 10 chưa kích hoạt trên lượt đo do phân loại dạng câu hỏi; (b) khẳng định về ảnh nghiệm thu là chưa đúng — ảnh chụp các câu không chứa thân đáp án trong khung hình (nội dung đáp án thật nằm ở tệp dữ kiện đi kèm). Không sửa/xoá nội dung cũ, chỉ thêm mục đính chính có ngày giờ.
1. **Sửa bộ phân loại dạng câu hỏi:** mở rộng nhận diện dạng chẩn đoán (`diagnosis`) và tra cứu (`lookup`) cho câu hỏi kỹ thuật: dấu hiệu gồm mã lỗi/mã máy, từ khoá lỗi và hiện tượng ở cả tiếng Việt/Nhật/Trung/Anh, câu hỏi về bảng thông số/giá trị/ngưỡng/đơn vị, câu hỏi nguyên nhân/đối sách. Rào phân loại: phải có ca kiểm âm — câu hỏi tổng quan/khái niệm/giải thích chung vẫn giữ dạng chung, không bị nuốt sang chẩn đoán/tra cứu. Kèm bộ test phân loại chạy trên đúng 50 câu của bộ đề đo: báo tỉ lệ từng dạng trước/sau sửa.
2. **Đo lại 50 câu** bằng runner hiện hành, model chính Ling 3.1 Flash free, CPU-only, với ngân sách 10 đã áp: nộp file kết quả thô; bảng so sánh phải có cột ngân sách kế hoạch thực tế từng câu (đếm số câu thật sự nhận ngân sách 10) và đối chiếu validated/điểm với hai mốc đã có (lượt chẩn đoán biến thể 4 validated/63,51; lượt áp dụng 5 validated/64,17). Kết luận nhân-quả chỉ được viết khi dữ kiện cho thấy ngân sách 10 đã kích hoạt trên đa số câu chẩn đoán/tra cứu; nếu số đo không cải thiện sau khi kích hoạt đúng, khai thẳng là ngân sách không phải đòn bẩy ở điều kiện thật — không tô hồng.
3. **Nghiệm thu dùng thật trên giao diện** (CPU-only, ghi commit HEAD): 3 câu chuẩn; **ảnh chụp bắt buộc chứa trọn thân đáp án trong khung hình** (cuộn tới đúng vị trí đáp án trước khi chụp; nếu đáp án dài hơn một khung hình thì chụp 2 ảnh liên tiếp phủ hết thân đáp án). Ít nhất 1 câu phải do model tổng hợp phục vụ (ghi tên model từ dữ kiện nguồn gốc).

## Rào cứng

- Không nới các cổng kiểm định khác; không đổi ngân sách đã áp ở vé trước; không ghi chỉ mục (băm trước/sau khớp). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần. Kích thước tệp trong báo cáo: đo trên bản đã nộp vào kho sau khi commit (lấy bằng lệnh liệt kê trên cây đã đồng bộ), không đo trên bản nháp tại máy trước khi đẩy — tránh lệch do khác quy ước xuống dòng.
