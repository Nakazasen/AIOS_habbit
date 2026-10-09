# VÉ: SRC-RECEIVE-2GOI-PC0575 (nhận và nạp hai gói nguồn vào chỉ mục tại máy công ty)

- Mã vé: `SRC-RECEIVE-2GOI-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/src-receive-2goi-pc0575.md`
- Bối cảnh: hai gói nguồn còn thiếu tại máy công ty đã được đưa lên Drive và kiểm chứng băm tuyệt đối ở vé đưa lên. Vé điều tra kênh tải tại máy công ty đã chứng minh kênh tải tệp từ Drive thông ngay trên mạng công ty qua liên kết trực tiếp (gói nhỏ tải xong trong 3,4 giây và khớp băm), nên vé này tải ngay tại máy, không cần đổi mạng Wi-Fi. Mục đích: nạp đủ nguồn còn thiếu để đường hỏi đáp cục bộ tại máy công ty bao phủ đủ tài liệu như máy nhà.

## Dữ kiện hai gói (đã kiểm chứng ở vé đưa lên)

1. Gói 90 tài liệu: 430.510 byte; băm SHA-256 `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403`; liên kết tải trực tiếp: `https://drive.usercontent.google.com/download?id=1z-fOzVmvq47JL2BRfH2JU3lW8st-BXWl&export=download&confirm=t`
2. Gói 421 tài liệu: 9.153.022 byte; băm SHA-256 `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5`; liên kết tải trực tiếp: `https://drive.usercontent.google.com/download?id=1U_M3SxY4gdIFSsk6r_PwRbJ_K6xgeLWK&export=download&confirm=t`

## Việc phải làm

1. Tải cả hai gói về thư mục làm việc riêng trên máy; đối chiếu băm của từng gói ngay sau khi tải — lệch băm thì dừng và báo cáo, không nạp.
2. **Sao lưu mới** chỉ mục production hiện tại (kèm kiểm tra toàn vẹn đạt) trước khi nạp bất cứ thứ gì; ghi rõ đường dẫn bản sao lưu và băm của nó trong báo cáo.
3. Chạy thử không ghi (dry-run) cho từng gói: báo số tài liệu mới, số tài liệu đã có, số tài liệu thuộc nhóm có vân tay trống cần xác minh cách tính trên 3 mã đại diện của nhóm 90 trước khi nạp thật.
4. Nạp theo đợt có khả năng chạy tiếp khi bị ngắt, theo đúng cơ chế nạp hiện có của hệ thống; sau mỗi gói, ghi lại số đếm tài liệu và mảnh trong chỉ mục, vân tay logic mới, và kết quả kiểm tra toàn vẹn.
5. Nghiệm thu dùng thật sau khi nạp đủ: mở ứng dụng ở chế độ chỉ dùng bộ xử lý trung tâm, hỏi ít nhất 2 câu thuộc phần tài liệu vừa nạp và 1 câu thuộc phần cũ, nộp đáp án nguyên văn và ảnh chứa đáp án trong ảnh. Ghi rõ mã commit đang chạy.

## Rào cứng

- Ba điều kiện bắt buộc trước khi nạp thật: sao lưu mới toàn vẹn, chạy thử không ghi trước, nạp theo đợt có chạy tiếp. Thiếu một trong ba thì dừng.
- Không chạy việc nặng đồng thời với phiên ứng dụng của người dùng trên cùng máy (lệnh khẩn của điều phối ngày 08/10) — phần nạp nặng làm khi máy rảnh. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần; mỗi đợt nạp xong phải commit mốc để ngắt giữa chừng vẫn tiếp tục được.
