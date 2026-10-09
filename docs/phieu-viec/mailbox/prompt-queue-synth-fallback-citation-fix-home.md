# VÉ: SYNTH-FALLBACK-CITATION-FIX-HOME (sửa cơ chế dự phòng trích dẫn: đáp án dự phòng cho câu chẩn đoán phải luôn mang theo bằng chứng có nhãn trích dẫn)

- Mã vé: `SYNTH-FALLBACK-CITATION-FIX-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-fallback-citation-fix-home.md`
- Căn cứ: vé `SYNTH-INTENT-AUDIT-HOME` (đã verdict ĐẠT) đã chẩn đoán tới tận cơ chế và được điều phối đếm lại xác nhận: khi câu hỏi được xếp dạng chẩn đoán mà mô hình ngoài không qua được kiểm định, cơ chế dự phòng trích dẫn hiện tại in ra ba mục chẩn đoán rỗng (chỉ toàn dòng "không có bằng chứng") và đánh rơi mất đoạn bằng chứng dự phòng vốn có — 21/21 câu rơi vào đường này ở lượt đo gần nhất đều nhận 0 điểm và mất tổng cộng khoảng 23,7 điểm, dù bằng chứng thật có sẵn trong gói truy hồi. Đây không chỉ là chuyện điểm số: người dùng thật khi gặp tình huống này cũng sẽ nhận một đáp án rỗng mục thay vì đoạn trích có ích. Vé này sửa đúng khuyết tật đó.

## Việc phải làm

1. **Sửa cơ chế dự phòng trích dẫn** trong lớp tổng hợp: khi các mục bắt buộc của dạng chẩn đoán không có bằng chứng khớp, đáp án dự phòng vẫn phải xuất ra các đoạn trích nguyên văn kèm nhãn trích dẫn của gói bằng chứng (ở phần bằng chứng của đáp án), thay vì chỉ in các mục rỗng. Khi có bằng chứng khớp mục thì giữ nguyên hành vi hiện tại. Không nới lỏng bất kỳ cổng kiểm định nào; đáp án dự phòng vẫn phải trung thực về giới hạn của nó (giữ các dòng lưu ý khi một mục thật sự không có bằng chứng, nhưng không được để toàn bộ đáp án thành mục rỗng khi vẫn còn bằng chứng dùng được).
2. **Kiểm thử đơn vị:** thêm ca khẳng định — dự phòng cho dạng chẩn đoán khi bằng chứng không khớp mục nào vẫn chứa ít nhất một nhãn trích dẫn và nội dung trích nguyên văn từ gói bằng chứng; ca có bằng chứng khớp mục giữ nguyên cấu trúc hiện tại; chạy lại toàn bộ các tệp kiểm thử liên quan tới tổng hợp.
3. **Đo lại 50 câu** bằng runner hiện hành (model chính miễn phí, chỉ-CPU): nộp file dữ kiện thô và bảng so sánh với lượt phân loại gần nhất, đếm từ chính file thô — tổng điểm, điểm trung bình, số câu qua kiểm định (phải giữ nguyên hoặc tốt hơn, không được giảm), điểm của nhóm 21 câu từng rơi dự phòng trích dẫn. Kết luận chỉ viết theo số đã đếm được.
4. **Nghiệm thu dùng thật:** nếu tái hiện được tự nhiên một câu rơi về dự phòng trên giao diện thì nộp ảnh chứa trọn thân đáp án cho thấy đoạn trích có nhãn; nếu không tái hiện được tự nhiên thì khai rõ và thay bằng bằng chứng từ lượt đo (trích nguyên văn một đáp án dự phòng mẫu từ file thô).

## Rào cứng

- Không đụng vào cổng bằng chứng và các cổng kiểm định trong vé này. Không ghi chỉ mục (băm trước/sau khớp). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần. Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit — và mọi con số trong báo cáo phải đếm từ chính file nộp kèm.
