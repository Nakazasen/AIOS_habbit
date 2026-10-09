# VÉ: STAGE2-TRUTH-PC0575 (đính chính báo cáo chặng 2 theo đúng dữ kiện đã nộp)

- Mã vé: `STAGE2-TRUTH-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Phạm vi: chỉ sửa tài liệu báo cáo và chụp bổ sung ảnh; không sửa mã, không ghi chỉ mục.
- Bối cảnh: vé bổ sung bằng chứng đã nộp đủ tệp thật, nhưng điều phối kiểm chứng độc lập phát hiện phần chữ trong báo cáo vẫn chưa khớp với chính dữ kiện đã nộp. Vé này đính chính ba điểm đó cho xong, để hồ sơ chặng 2 trung thực tuyệt đối trước khi sang việc chẩn đoán mở sổ.

## Việc phải làm

1. **Đính chính thời gian phản hồi của 3 câu hỏi thật:** trong phần chính của báo cáo `app-source-model-pc0575-stage2.md`, các con số 3,80 / 5,14 / 3,95 giây không có dữ kiện nào chống lưng. Thay bằng số thật trong tệp dữ kiện phiên đã nộp (466,47 giây; 126,26 giây; 75,87 giây), ghi rõ đây là số đo của phiên bổ sung ngày 09/10/2026 và phần chính trước đây ghi sai. Nếu phân tích được thời gian gồm những phần chờ nào (nạp tiến trình nền, chờ dịch vụ trả lời) thì ghi thêm; chưa phân tích được thì ghi thẳng là chưa phân tích được — không ghi con số không có nguồn.
2. **Đính chính phần mô tả ảnh và chụp bổ sung:** viết lại phần mô tả hai ảnh đã nộp cho khớp nội dung thật trong ảnh (ảnh sổ LSU là một phiên trò chuyện đang mở, có ô nhập và bộ chọn khối tri thức, không có dòng trạng thái kho trong ảnh; ảnh sổ MOM là trang sổ chưa có ô nhập trong ảnh). Chụp bổ sung một ảnh có dòng trạng thái kho thật cho sổ LSU — dữ kiện đo thao tác thật cho thấy dòng này xuất hiện khi mở sổ, hãy chụp đúng vùng có dòng đó.
3. **Sửa kích thước tệp dữ kiện 3 câu trong báo cáo** cho khớp số đo trên bản đã nộp vào kho (22.906 byte), và rà lại mọi kích thước tệp khác được nhắc trong báo cáo theo đúng kỷ luật: đo trên bản đã nộp sau khi commit.

## Rào cứng

- Chỉ sửa tài liệu và chụp ảnh: không sửa mã chạy thật, không ghi chỉ mục, không merge `main`.
- Mọi con số ghi vào báo cáo phải có nguồn dữ kiện trong kho chỉ được đích danh.
