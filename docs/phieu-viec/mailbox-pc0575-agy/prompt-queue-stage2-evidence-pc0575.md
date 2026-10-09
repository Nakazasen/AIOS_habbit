# VÉ: STAGE2-EVIDENCE-PC0575 (bổ sung bằng chứng còn thiếu của chặng 2 vé APP-SOURCE-MODEL-PC0575)

- Mã vé: `STAGE2-EVIDENCE-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Báo cáo: bổ sung trực tiếp vào `docs/phieu-viec/ket-qua/app-source-model-pc0575-stage2.md` (thêm mục bổ sung có ngày giờ, không sửa nội dung cũ) + các tệp bằng chứng kèm theo.
- Bối cảnh: điều phối kiểm chứng độc lập chặng 2 và kết luận chưa đạt ở phần bằng chứng, dù phần việc chính có tín hiệu tốt (số đo mở sổ giảm mạnh, chỉ mục nguyên vẹn, phần code lọc chạy đạt khi điều phối chạy lại trên máy sạch). Bốn việc dưới đây khép đúng các lỗ hổng đã chỉ ra. Vé này xếp sẵn trong hộp thư và chạy khi trần model của tài khoản dùng chung mở lại.

## Việc phải làm

1. **Nộp ảnh thật sau khi sửa:** khởi động lại ứng dụng, mở sổ LSU và sổ MOM, chụp ảnh thật cho mỗi sổ sao cho ảnh chứa vùng trạng thái kho và bộ chọn khối tri thức. Nộp tệp ảnh vào đúng thư mục kết quả và ghi tên tệp vào báo cáo. Điều phối sẽ kiểm tra sự tồn tại của tệp trong kho trước tiên — báo cáo trước ghi hai tệp ảnh kèm kích thước cụ thể nhưng cả hai không tồn tại trong kho, lần này tuyệt đối không ghi tên tệp chưa nộp.
2. **Bổ sung đáp án nguyên văn của 3 câu hỏi thật:** nộp tệp dữ kiện của phiên hỏi đáp chứa nguyên văn đủ 3 đáp án (không tóm tắt, không diễn giải lại), kèm thông tin nguồn gốc phục vụ của từng câu. Nội dung tóm tắt tự viết trong báo cáo trước không được tính là bằng chứng đáp án.
3. **Giải trình thay đổi ở tệp pipeline trong commit (b):** viết rõ vì sao cần thay đổi đó cho cơ chế tài liệu trong chỉ mục được coi là sẵn sàng, và bổ sung ca kiểm thử khẳng định hành vi ngoài chế độ chỉ đọc không thay đổi (nếu đã có ca như vậy thì chỉ rõ tên ca). Điều phối đã tự đọc thay đổi: ở chế độ chỉ đọc, khi tệp nguồn không còn trên đĩa thì lấy trạng thái từ chỉ mục thay vì báo unavailable — cần lời giải trình và kiểm thử bảo vệ chính thức trong hồ sơ.
4. **Đo thời gian mở sổ bằng thao tác thật trên ứng dụng:** sau khi khởi động lại ứng dụng, bấm vào từng sổ như người dùng thật và ghi số giây tới khi gõ được câu hỏi, kèm ảnh tại thời điểm sổ sẵn sàng. Con số đo bằng script ở tầng sau trong báo cáo trước được giữ làm tham khảo, không thay cho đo thao tác thật theo yêu cầu nghiệm thu của vé gốc.

## Rào cứng

- Không sửa thêm logic chạy thật trong vé này (ngoại trừ bổ sung ca kiểm thử ở việc 3 nếu thiếu). Không ghi chỉ mục (băm trước/sau khớp). Không merge `main`.
- Mọi tệp được nhắc tên trong báo cáo phải tồn tại thật trong kho tại thời điểm nộp. Mốc tiến độ tối thiểu 15 phút/lần.
