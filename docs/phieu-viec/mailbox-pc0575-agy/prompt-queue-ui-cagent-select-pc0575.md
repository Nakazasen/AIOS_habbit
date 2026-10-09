# VÉ: UI-CAGENT-SELECT-PC0575 (mở lựa chọn đích C-Agent trong giao diện tại máy công ty)

- Mã vé: `UI-CAGENT-SELECT-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-cagent-select-pc0575.md`
- Bối cảnh: lúc 21:29 ngày 09/10, người dùng dùng thật tại máy công ty và phản ánh không chọn được AI của C-Agent trong giao diện — phần chọn đích chỉ hiện "Gemini qua cầu nối (tự động)". Theo mã nguồn `src/aios_habit/ai_lane.py`, đích C-Agent chỉ xuất hiện trong danh sách lựa chọn khi địa chỉ dịch vụ C-Agent đã được cấu hình tại máy (biến cấu hình endpoint khác rỗng thì đích mới được đưa vào danh sách và được đánh dấu khả dụng). Dịch vụ C-Agent của công ty đã được dùng ổn định trong các vé đo tại chính máy này (điểm chất lượng 2,937 ở lượt đo chuẩn), nên đích này phải chọn được trong giao diện khi máy ở mạng công ty.

## Việc phải làm

1. Kiểm tra tại máy: ứng dụng đang chạy nạp cấu hình từ đâu, và cấu hình đó đã có địa chỉ dịch vụ C-Agent hay chưa. Ghi căn cứ vào báo cáo (tên biến cấu hình và trạng thái có/không có — không in bất kỳ khoá hay thông tin nhạy cảm nào nếu có).
2. Nếu thiếu cấu hình: bổ sung đúng địa chỉ dịch vụ C-Agent của công ty (đường prediction đã dùng trong các vé đo tại máy này) vào đúng nơi cấu hình mà ứng dụng đang chạy thực tế đọc, rồi khởi động lại ứng dụng và xác nhận đích C-Agent xuất hiện trong phần chọn đích. Nếu cấu hình đã có mà đích vẫn không xuất hiện: tìm nguyên nhân trong mã đường liệt kê đích và sửa, kèm kiểm thử bảo vệ.
3. Kiểm tra điều kiện mạng tới máy chủ dịch vụ từ máy công ty tại thời điểm làm vé và ghi kết quả vào báo cáo.
4. Nghiệm thu dùng thật qua giao diện: chọn đích C-Agent, hỏi 1 câu và nhận đáp án thật; nộp đáp án nguyên văn và ảnh trong đó thấy rõ đích đã chọn là C-Agent cùng đáp án trong khung hình. Ghi rõ mã commit đang chạy.

## Rào cứng

- Tệp cấu hình tại máy không được commit nếu chứa bất kỳ thông tin nhạy cảm nào; báo cáo chỉ ghi tên biến và trạng thái. Không ghi vào chỉ mục chính.
- Không chạy việc nặng đồng thời với phiên ứng dụng của người dùng trên cùng máy; nghiệm thu khi người dùng không đang dùng ứng dụng, nếu chưa được thì ghi mốc chờ.
- Mốc tiến độ tối thiểu 15 phút/lần.
