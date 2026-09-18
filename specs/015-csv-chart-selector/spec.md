# Đặc tả tính năng: Chọn biểu đồ khi nhập tệp CSV LSU

**Mã tính năng**: `015-csv-chart-selector`

**Ngày tạo**: 18/09/2026

**Trạng thái**: Bản nháp

**Đầu vào**: Người dùng mô tả: “Chưa chọn được biểu đồ trong giao diện khi nhập file CSV (hạn bù 15/10/2026). Kết hợp cách ô chọn gọn và cách gõ câu chat tự nhiên. Thông minh, thân thiện với người không chuyên, tùy biến cao.” Kết quả nghiên cứu thư mục `D:\Sandbox\Iris LSU`: 49 tệp CSV thuộc 3 nhóm JIG 2ND-1002, 2ND-1004, 2ND-1035 cùng thư mục `log/`; tệp hẹp 3–23 cột cho đo sâu biên dạng, tệp tổng hợp rộng 572–1153 cột cho kiểm tra đơn vị, lỗi, thông số; cột chung gồm ngày, giờ, mã JIG, mã sản phẩm, kết quả đạt/lỗi theo màu, độ lệch, độ nghiêng, thời gian nhịp, thông số giới hạn.

## Làm rõ

### Phiên 2026-09-18

- Q: Nhịp đầu tiên nên hỗ trợ những loại biểu đồ nào cho buổi demo ngày 23/09? → A: Hỗ trợ cả 3 loại, mỗi lần xem người dùng chọn 1 trong 3: xu hướng theo thời gian, phân bố giá trị, so sánh theo màu.
- Q: Khi tệp tổng hợp có hàng trăm cột, nên ưu tiên nhóm chỉ số nào hiện trước cho demo ngày 23/09? → A: Ưu tiên nhóm độ lệch và độ nghiêng theo 4 màu (đen, hồng, xanh, vàng).
- Q: Nhịp đầu có cần hỗ trợ cả tệp Excel ngoài tệp CSV không? → A: Có, hỗ trợ cả CSV và Excel (XLSX, XLSM) ngay từ đầu.
- Q: Ảnh biểu đồ đã chọn có cần dùng luôn cho email cảnh báo không? → A: Có, dùng chung ảnh cho cả xem trước và email cảnh báo.
- Q: Với tệp đo sâu không có dòng tiêu đề thì hệ thống nên xử lý thế nào? → A: Ưu tiên linh hoạt và thông minh nhất: tự nhận diện vị trí cột thường gặp, chỉ khi mơ hồ mới hướng dẫn bổ sung, không bắt người dùng xuất lại từ đầu.

## Tình huống người dùng và kiểm thử

### Câu chuyện 1 — Chọn biểu đồ bằng ô chọn gọn sau khi nhập tệp (Ưu tiên: P1)

Người không chuyên mở màn hình kiểm tra dữ liệu LSU, tải lên tệp CSV vừa đo từ JIG, chờ hệ thống báo dữ liệu hợp lệ, sau đó chọn mã JIG, chọn chỉ số cần xem, chọn 1 trong 3 loại biểu đồ (xu hướng theo thời gian, phân bố giá trị, so sánh theo màu), chọn loại ảnh, bấm xem trước và tải ảnh về để đưa vào báo cáo hoặc buổi demo.

**Vì sao ưu tiên này**: Đây là đường dùng chính cho buổi demo ngày 23/09/2026 và cho hạn bù 15/10/2026. Người dùng nhìn thấy ngay, làm được trong 1–2 thao tác, không cần nhớ cú pháp.

**Kiểm thử độc lập**: Chỉ với một bộ tệp mẫu đã làm sạch, người dùng tải tệp lên, chọn JIG và chỉ số từ danh sách gợi ý, nhận được ảnh biểu đồ xem trước đúng chỉ số đã chọn.

**Tình huống nghiệm thu**:

1. **Cho** đã tải đủ tệp và hệ thống báo dữ liệu hợp lệ, **khi** người dùng chọn mã JIG và tên chỉ số từ danh sách gợi ý, **thì** hệ thống hiện ảnh biểu đồ đúng JIG và đúng chỉ số trong cùng màn hình.
2. **Cho** đang xem ảnh biểu đồ, **khi** người dùng đổi sang chỉ số khác hoặc đổi loại ảnh, **thì** ảnh xem trước cập nhật theo lựa chọn mới mà không phải tải lại tệp.
3. **Cho** tệp có hàng trăm cột chỉ số, **khi** người dùng mở danh sách chỉ số, **thì** danh sách chỉ hiện các chỉ số đo được, có tên tiếng Việt dễ hiểu kèm theo, không hiện cột kỹ thuật nội bộ.

---

### Câu chuyện 2 — Vẽ biểu đồ bằng câu chat tự nhiên (Ưu tiên: P2)

Người dùng gõ một câu tiếng Việt đơn giản vào khung chat duy nhất, ví dụ hỏi vẽ biểu đồ độ lệch cho một mã JIG, hệ thống tự hiểu JIG và chỉ số, trả về cùng ảnh biểu đồ như cách chọn bằng ô chọn, kèm lời giải thích ngắn gọn.

**Vì sao ưu tiên này**: Giữ đúng triết lý một khung chat duy nhất, tăng tùy biến cho người đã quen, không cần thêm màn hình mới.

**Kiểm thử độc lập**: Chỉ với câu chat và cùng bộ tệp mẫu đã nhập, người dùng gõ câu yêu cầu vẽ biểu đồ, nhận được ảnh và lời giải thích đúng JIG, đúng chỉ số.

**Tình huống nghiệm thu**:

1. **Cho** đã có gói dữ liệu hợp lệ trong phiên, **khi** người dùng gõ câu yêu cầu vẽ biểu đồ cho một mã JIG và một chỉ số bằng tiếng Việt, **thì** hệ thống trả về ảnh biểu đồ đúng JIG và đúng chỉ số kèm câu giải thích tiếng Việt.
2. **Cho** câu chat thiếu tên JIG hoặc tên chỉ số, **khi** người dùng gửi câu, **thì** hệ thống hỏi lại đúng phần còn thiếu bằng tiếng Việt, không tự đoán mò.

---

### Câu chuyện 3 — Xem trước, tải về và dùng lại cho báo cáo (Ưu tiên: P3)

Người dùng xem ảnh rõ nét, phóng to được, tải về một tệp ảnh duy nhất để đính kèm email hoặc trình chiếu, biết rõ ảnh này vẽ từ gói dữ liệu nào và thời điểm nào.

**Vì sao ưu tiên này**: Phục vụ demo tại công ty và báo cáo sau demo, nhưng chỉ có giá trị sau khi hai câu chuyện trên chạy đúng.

**Kiểm thử độc lập**: Từ ảnh đang xem trước, người dùng tải về được một tệp ảnh mở được trên máy văn phòng thông thường.

**Tình huống nghiệm thu**:

1. **Cho** đang xem ảnh biểu đồ, **khi** người dùng bấm tải về, **thì** nhận được một tệp ảnh mở được, có tem thông tin gồm mã JIG, tên chỉ số, ngày giờ và gói dữ liệu nguồn.
2. **Cho** gói dữ liệu chưa hợp lệ hoặc chưa chọn tệp, **khi** người dùng mở khu vực biểu đồ, **thì** hệ thống báo rõ chưa có dữ liệu và hướng dẫn quay lại bước tải tệp.

---

### Trường hợp biên

- Tệp tổng hợp rộng tới khoảng 1100 cột và nặng tới khoảng 26 MB: hệ thống chỉ liệt kê chỉ số đo được, không liệt kê cột thời gian nhịp hay mã nội bộ làm chỉ số vẽ.
- Tệp đo sâu chỉ có 3 cột không có dòng tiêu đề: hệ thống tự nhận diện theo vị trí cột thường gặp (ngày giờ, mã sản phẩm, chuỗi giá trị đo); chỉ khi mơ hồ mới hỏi bổ sung, không bắt xuất lại từ đầu.
- Tệp vị trí camera rỗng 0 KB: hệ thống báo tệp trống và hướng dẫn kiểm tra lại xuất log.
- Tên chỉ số trong tệp là mã kỹ thuật (ví dụ mã độ lệch, độ nghiêng theo màu và vị trí): hệ thống hiện tên tiếng Việt dễ hiểu bên cạnh mã gốc.
- Người dùng nhập sai mã JIG hoặc chỉ số không có trong gói dữ liệu: hệ thống báo không tìm thấy và gợi ý danh sách gần đúng.
- Tệp vượt giới hạn máy đã công bố (CSV 100 MB, 200.000 dòng mỗi bảng, lô 10.000 dòng): hệ thống từ chối nhẹ nhàng bằng tiếng Việt và nêu cách tách nhỏ tệp.
- Mọi chữ hiện ra phải là tiếng Việt dễ hiểu; lỗi từ thư viện, hệ điều hành hoặc tệp phải được đổi thành nguyên nhân đơn giản và bước xử lý, không hiện nguyên văn tiếng Anh hay chi tiết kỹ thuật thô.

## Yêu cầu

### Yêu cầu chức năng

- **FR-001**: Hệ thống PHẢI cho phép người dùng chọn mã JIG và tên chỉ số từ danh sách gợi ý ngay trong màn hình đã nhập tệp CSV hoặc Excel, sau khi dữ liệu được báo hợp lệ.
- **FR-002**: Hệ thống PHẢI vẽ ảnh biểu đồ đúng JIG, đúng chỉ số và đúng 1 trong 3 loại đã chọn gồm xu hướng theo thời gian, phân bố giá trị, so sánh theo màu; ảnh có đường giới hạn trên, đường trung tâm, đường giới hạn dưới và tem thông tin quản lý (mã JIG, tên chỉ số, ngày giờ, gói dữ liệu nguồn).
- **FR-003**: Hệ thống PHẢI cho phép đổi JIG, đổi chỉ số và đổi loại ảnh mà không bắt tải lại tệp.
- **FR-004**: Hệ thống PHẢI hiểu câu chat tiếng Việt yêu cầu vẽ biểu đồ và trả về cùng ảnh như cách chọn bằng ô chọn; khi thiếu thông tin PHẢI hỏi lại bằng tiếng Việt thay vì tự đoán.
- **FR-005**: Hệ thống PHẢI cho phép xem trước ảnh trong giao diện và tải về một tệp ảnh duy nhất mở được trên máy văn phòng; cùng ảnh này PHẢI dùng được luôn cho email cảnh báo mà không phải vẽ lại.
- **FR-006**: Hệ thống PHẢI chỉ liệt kê các chỉ số đo được làm lựa chọn vẽ, ưu tiên hiện trước nhóm độ lệch và độ nghiêng theo 4 màu (đen, hồng, xanh, vàng); cột ngày giờ, mã sản phẩm, kết quả đạt/lỗi, thời gian nhịp và mã nội bộ KHÔNG được hiện làm chỉ số vẽ.
- **FR-007**: Hệ thống PHẢI hiện tên tiếng Việt dễ hiểu bên cạnh mọi mã kỹ thuật (mã JIG, tên chỉ số, đơn vị đo).
- **FR-008**: Hệ thống PHẢI kiểm tra tệp trước khi vẽ: tệp trống, thiếu cột bắt buộc, sai cấu trúc hoặc vượt giới hạn máy đều phải báo bằng tiếng Việt kèm bước xử lý; riêng tệp đo sâu không có dòng tiêu đề PHẢI được tự nhận diện theo vị trí cột thường gặp, chỉ khi mơ hồ mới hỏi bổ sung, không bắt xuất lại từ đầu.
- **FR-009**: Hệ thống PHẢI giữ dữ liệu thật ở lại máy cục bộ; không đưa dòng dữ liệu, mã sản phẩm, giá trị đo hoặc đường dẫn tuyệt đối vào nhật ký công khai, báo cáo kiểm thử hoặc câu lệnh gửi ra ngoài.
- **FR-010**: Khi dữ liệu chỉ đủ ở mức mẫu làm sạch, hệ thống PHẢI ghi rõ đây là kết quả kỹ thuật trên dữ liệu mẫu, không dùng để tuyên bố đạt vận hành thật.

### Thực thể chính

- **Gói dữ liệu đã nhập**: tập hợp các tệp CSV người dùng vừa tải trong phiên, kèm trạng thái hợp lệ, mã gói và thời điểm nhập.
- **Chỉ số đo**: một đại lượng đo từ JIG có thể vẽ được (tên mã gốc, tên tiếng Việt, đơn vị, mã JIG sở hữu).
- **Lựa chọn biểu đồ**: bộ gồm mã JIG, tên chỉ số và loại ảnh người dùng đã chọn bằng ô chọn hoặc bằng câu chat.
- **Ảnh biểu đồ xem trước**: ảnh kết quả đúng lựa chọn, kèm tem thông tin truy vết về gói dữ liệu nguồn.

## Tiêu chí thành công

### Kết quả đo được

- **SC-001**: Người không chuyên hoàn thành việc tải tệp mẫu, chọn biểu đồ và xem được ảnh đúng trong dưới 2 phút.
- **SC-002**: 9 trên 10 lần thử đầu tiên với tệp mẫu hợp lệ cho ra ảnh đúng JIG và đúng chỉ số đã chọn.
- **SC-003**: Với tệp tổng hợp rộng khoảng 500–1100 cột, danh sách chỉ số mở ra trong dưới 5 giây và chỉ chứa chỉ số đo được.
- **SC-004**: 100% trường hợp tệp trống, sai cấu trúc hoặc vượt giới hạn đều nhận được thông báo tiếng Việt có bước xử lý, không có câu tiếng Anh hay chi tiết kỹ thuật thô.
- **SC-005**: Ảnh tải về mở được trên máy văn phòng thông thường và đọc được tem thông tin gồm mã JIG, tên chỉ số, ngày giờ và mã gói dữ liệu.

## Giả định

- Người dùng là kỹ thuật viên hoặc quản lý chất lượng, dùng tiếng Việt, không cần biết cấu trúc tệp log.
- Tệp đầu vào là CSV hoặc Excel (XLSX, XLSM) xuất từ JIG LSU, đúng giới hạn máy đã công bố; tệp ngoài mẫu phải được xuất lại trước khi dùng.
- Đích đầu tiên là BOWSKEW 4 BEAM; các JIG và chỉ số khác mở dần sau khi đường chính chạy ổn định.
- Dữ liệu thật chỉ dùng cục bộ để kiểm chứng, gắn nhãn `local_only`, không đưa vào Git hay câu lệnh gửi ra ngoài; kiểm thử tự động chỉ dùng dữ liệu mẫu đã làm sạch.
- Mốc demo 23/09/2026 dùng đường ô chọn; câu chat tự nhiên hoàn thiện cùng đợt bù 15/10/2026 nếu nguồn lực cho phép, nếu không sẽ bàn giao phần chat ở nhịp tiếp theo mà không chặn phần ô chọn.
