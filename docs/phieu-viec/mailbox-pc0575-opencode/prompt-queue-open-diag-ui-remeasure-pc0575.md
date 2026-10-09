# VÉ: OPEN-DIAG-UI-REMEASURE-PC0575 (đo lại thời gian mở sổ qua giao diện trong điều kiện máy rảnh hẳn)

- Mã vé: `OPEN-DIAG-UI-REMEASURE-PC0575`
- Role gợi ý: TINY (opencode — thợ phụ tạm thời, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/open-diag-ui-remeasure-pc0575.md`
- Bối cảnh: lượt kiểm chứng chéo `OPEN-DIAG-XCHECK-PC0575` đã xác nhận độc lập cơ chế ở tầng mã (khâu trạng thái chỉ mục chỉ mất 0,0055 giây khi dùng đệm; toàn bộ kiểm thử liên quan đạt 13/13; đường hoàn lui hoạt động; đệm tự hủy đúng khi cơ sở dữ liệu thay đổi). Nhưng phần đo qua giao diện của lượt đó không hợp lệ: trong lúc đo, làn nạp dữ liệu của thợ chính đang ghi vào chính chỉ mục đang đo (cơ sở dữ liệu đổi kích thước và thời gian sửa đổi giữa cửa sổ đo, kèm khóa đọc), khiến đệm mất hiệu lực sau mỗi điểm ghi và máy chịu tải nặng. Vé này đo lại phần giao diện trong điều kiện sạch để có con số đầu-cuối độc lập.

## Điều kiện bắt buộc trước khi đo (thiếu thì không đo)

1. Vé `SRC-RECEIVE-2GOI-PC0575` của thợ chính đã ở trạng thái xong hẳn (không còn làn nạp nào chạy), và trên máy không có tiến trình nào đang ghi vào tệp chỉ mục — kiểm tra bằng cách ghi lại kích thước và thời gian sửa đổi của tệp chỉ mục ở đầu và cuối cửa sổ đo: hai lần ghi phải giống hệt nhau, nếu khác thì toàn bộ lượt đo không hợp lệ và phải ghi rõ điều đó.
2. Người dùng không đang dùng ứng dụng trên máy (theo lệnh khẩn của điều phối: không chạy việc đo nặng đồng thời với phiên ứng dụng của người dùng).
3. Nếu hai điều kiện trên chưa đạt: ghi mốc chờ vào trang trạng thái rồi dừng, không đo. Vé sẽ được phát hành lại khi điều kiện đạt.

## Việc phải làm khi điều kiện đạt

1. Khởi động lại ứng dụng, đo thời gian mở lạnh sổ MOM và sổ LSU tới khi gõ được câu hỏi (mỗi sổ một lượt), rồi đo thời gian mở ấm của hai sổ.
2. Ghi băm của tệp chỉ mục trước và sau toàn bộ lượt đo (phải khớp nhau), kèm tệp dữ kiện đo và ảnh tại thời điểm mỗi sổ sẵn sàng.
3. Đối chiếu số đo với báo cáo gốc của thợ chính (mở lạnh khoảng 3 giây, mở ấm dưới 1 giây) và ghi rõ mục nào khớp, mục nào lệch.

## Rào cứng

- Chỉ đo và ghi: không sửa mã, không sửa kiểm thử, không ghi chỉ mục. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần trong lúc chờ điều kiện hoặc đang đo.
