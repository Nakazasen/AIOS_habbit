# Danh sách kiểm đặc tả

## Chất lượng nội dung

- [x] Mọi user story có thể kiểm thử độc lập.
- [x] Có ranh giới rõ với Gate A/B/C và các hạng mục cấm.
- [x] Tách phần đọc-only có thể tự chấm khỏi các quyền tác động dữ liệu, người dùng hoặc máy phải do chủ hệ thống cấp.
- [x] Không dùng tuyên bố dự đoán, chẩn đoán hay production khi chưa có evidence.
- [x] Các yêu cầu có mã duy nhất và tiêu chí thành công đo được.
- [x] US1–US11 vẫn được giữ đầy đủ; việc tinh gọn chỉ thay đổi thứ tự thực thi.
- [x] Mỗi đợt có điều kiện vào, kết quả dùng được và điều kiện hoàn tất.
- [x] `tasks.md` chỉ chứa lát cắt đang đủ điều kiện; backlog tương lai không giả làm việc đang triển khai.
- [x] Thiết kế phù hợp máy i5, RAM 16 GB, không GPU và không bắt buộc model nặng.
- [x] Chuỗi lot linh kiện → Unit → JIG → outcome, phát lại lịch sử và shadow khớp `AI cảnh báo lỗi LSU.pptx`.
- [x] BOWSKEW 4 BEAM là target đầu tiên; các target còn lại không triển khai đồng thời.
- [x] MVP có đường hoàn thành không cần model học máy khi dữ liệu chưa đủ.
- [x] Không đưa scheduler, PLC, AutoML, Knowledge Graph prediction hoặc tích hợp ERP/JIG vào MVP.
- [x] RAG, case, chuyên gia, bài học, C-call/Jam, Agent, NAS và Drum/DLP vẫn có vị trí rõ trong kế hoạch.
- [x] Tiếng Việt là ngôn ngữ giao diện duy nhất trong đặc tả, kế hoạch, task, hợp đồng và hướng dẫn kiểm chứng.
- [x] Phạm vi ngôn ngữ bao gồm nút, hướng dẫn, tiến độ, trạng thái, cảnh báo, lỗi, nhật ký vận hành và báo cáo.
- [x] Có tiêu chí giả lập lỗi tiếng Anh từ bên ngoài và chặn không cho lọt ra giao diện.
- [x] Tài liệu nguồn ngoại ngữ được giữ nguyên làm bằng chứng nhưng phần điều khiển và giải thích vẫn bằng tiếng Việt.
- [x] Locale giao diện tiếng Việt được tách khỏi ngôn ngữ nguồn và locale lịch sử để không phá dữ liệu cũ.
- [x] Gemini/tác tử cloud bị cấm đọc dữ liệu nhà máy thật; cổng kỹ thuật có fixture và manifest làm sạch thay thế.
- [x] Giao thức phát lại khóa metric, khoảng dự báo, cách ghép outcome và cách tính đúng/nhầm/bỏ sót/lead time.
- [x] Nhánh model không thêm dependency khi Data Gate thật và công thức cỡ mẫu trong rubric chưa đạt.
- [x] Phục hồi hai SQLite có trạng thái tối thiểu và khóa chống trùng không dựa vào đồng hồ lúc chạy.
- [x] Lệnh kiểm chứng dùng Python 3.11 và smoke chạy trong runtime thử nghiệm tách khỏi dữ liệu thật.
- [x] Gemini thực hiện T001–T029 trong một goal; T029 do tác tử kiểm toán độc lập với tác tử thực thi và tự kết luận bằng rubric/lệnh thật.
- [x] Có prompt `/goal` đầy đủ, checklist, biên nhận, checkpoint và bàn giao phục hồi được nhưng không dựng hệ điều phối vào code sản phẩm.
- [x] Có mẫu từ điển dữ liệu T011, ngưỡng EWMA mặc định, công thức cỡ mẫu và rubric T022 để người dùng không phải tự nghĩ thông số thống kê.
- [x] Rubric cho phép tự mở `AUTO_SHADOW` hoặc `LEARNING_SHADOW` đọc-only nhưng không mở đường điều khiển máy.
- [x] Nguồn LSU và gói Kyocera chỉ được đăng ký bằng bí danh; đường dẫn và nội dung thật không vào Git hoặc ngữ cảnh tác tử cloud.

## Trước khi code và trước khi chạy dữ liệu thật

- [x] Chủ repo duyệt thứ tự cổng và định nghĩa quyền chuyên gia/phát hành SOP.
- [ ] Có bằng chứng Gói 1 và Gói 2 ngoài phạm vi code; mục này không chặn T001–T029.
- [x] Có sample log đã được phép và owner cho pilot line.
- [x] Chủ sở hữu xác nhận các trường dữ liệu/nhãn và người chịu trách nhiệm cho LSU có sẵn.
- [ ] Tiến trình cục bộ đã kiểm tra file thật có nối ổn định `component_lot_id → unit_serial → jig_id/run_id`; nếu chưa, goal vẫn chạy hết bằng fixture.
- [ ] Dữ liệu thật BOWSKEW 4 BEAM tự đạt công thức cỡ mẫu OK/NG; nếu chưa, dùng `LEARNING_SHADOW` thay vì chặn ship.
- [x] Chủ sở hữu duyệt phương án giao theo đợt nhỏ ngày 04/09/2026.

Ghi chú: thư mục nguồn, mẫu log, SOP, mã lỗi, mapping và các trường dữ liệu LSU đã được chủ sở hữu xác nhận có sẵn cục bộ. Việc ingest thật, kiểm tra NAS nhiều máy và backup/restore vẫn chưa chạy nên Gói 1/Gói 2 chưa được đánh dấu hoàn tất.
