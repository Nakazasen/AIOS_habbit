# Hợp đồng an toàn: Quy chuẩn vận hành Vòng khép kín có bằng chứng

Tài liệu này định nghĩa các **Hợp đồng an toàn (Safety Contracts)** và quy tắc kỹ thuật bắt buộc giữa các thành phần trong hệ thống. Mọi hàm lập trình đều phải tuân thủ nghiêm ngặt các điều kiện tiên quyết dưới đây để đảm bảo an toàn tuyệt đối cho dữ liệu và dây chuyền sản xuất của nhà máy.

---

## 1. Hợp đồng Lưu hồ sơ sự vụ
**Tên hàm nghiệp vụ**: `create_case_from_trace_id(trace_id) -> CaseRecord`

### 📋 Điều kiện đầu vào:
- Mã phiên, mã câu trả lời của hệ thống, mã trace và danh sách các tham chiếu căn cứ trích dẫn đã có (`EvidenceReference[]`).

### 🛡 Rào chắn an toàn (Tự động từ chối nếu vi phạm):
- Từ chối lưu nếu căn cứ trích dẫn không có vị trí tài liệu rõ ràng hoặc không có mã băm kiểm chứng nội dung.
- Từ chối lưu nếu trace hoặc nguồn trích dẫn không mang nhãn `local_only`, hoặc nếu đầu vào thiếu mã phiên hay mã câu trả lời của hệ thống.

### ✅ Kết quả thực thi:
- Ghi nhận trọn vẹn trong một lần thực thi: Tạo hồ sơ sự vụ + lưu danh sách tham chiếu căn cứ trích dẫn + ghi nhật ký kiểm toán. Không sao chép câu hỏi, câu trả lời hay đoạn trích nguồn vào kho này.
- Nếu xảy ra lỗi giữa chừng, toàn bộ thao tác bị hủy bỏ ngay lập tức, không bao giờ để lại hồ sơ lỗi dở dang.

---

## 2. Hợp đồng Thẩm định của Chuyên gia
**Tên hàm nghiệp vụ**: `record_expert_review(case_id, review) -> ExpertReview`

### 📋 Điều kiện thẩm định:
- Khi ý kiến thẩm định mới ở mức **Dự thảo (`candidate`)** (do người dùng hoặc AI tạo ra), nó không được phép kích hoạt bất kỳ hành động xuất văn bản hay nâng cấp thành bài học nào.
- Khi chuyên gia bấm **Xác nhận đúng (`confirmed`)** hoặc **Bác bỏ (`rejected`)**:
  - Bắt buộc phải có: Mã chuyên gia, chức danh/vai trò, phạm vi phụ trách, mức độ tin cậy và lý do phê duyệt chi tiết.
  - Mã băm của tập tài liệu trích dẫn phải trùng khớp tuyệt đối với hồ sơ sự vụ gốc.

### 🛡 Rào chắn an toàn:
- Mọi ý kiến đánh giá được ghi nối tiếp vào cơ sở dữ liệu (append-only), không cho phép chỉnh sửa đè lên ý kiến cũ. Muốn sửa đổi thì chuyên gia phải tạo một lượt đánh giá mới kèm lý do giải thích.

---

## 3. Hợp đồng Đúc kết Bài học kinh nghiệm
**Tên hàm nghiệp vụ**: `promote_learning(review_id, actor, rationale) -> LearningRecord`

### 📋 Điều kiện phê duyệt:
- Chỉ tiếp nhận các lượt thẩm định đã được chuyên gia bấm **Xác nhận đúng (`confirmed`)** và mã băm bằng chứng vẫn còn nguyên vẹn.
- Bắt buộc phải ghi nhận: Tên Quản lý chất lượng phê duyệt, thời điểm phê duyệt và lý do đưa vào sổ tay bài học.

### 🛡 Rào chắn an toàn:
- Quá trình này **hoàn toàn không can thiệp** vào thư viện tài liệu quy chuẩn (`library.sqlite`), không tự động huấn luyện lại mô hình AI và không làm thay đổi các tài liệu hướng dẫn gốc.

---

## 4. Hợp đồng Đính kèm Dữ liệu Log máy (Thử nghiệm điều tra)
**Tên hàm nghiệp vụ**: `attach_line_events(case_id, events) -> EvidenceReference[]`

### 📋 Điều kiện đính kèm:
- Chỉ tiếp nhận các sự kiện được trích xuất từ ngăn kéo log máy `line_events.sqlite`, mang nhãn xuất xứ rõ ràng là **"Nghi vấn (`suspected`)"**.
- Nếu sự kiện log không khớp với hiện tượng đang điều tra hoặc chưa được chuyên gia đối chứng xác nhận: Tuyệt đối không đưa ra kết luận lỗi, không tạo bài học và không vẽ sơ đồ cảm biến hỏng.

### 🛡 Rào chắn an toàn:
- Tệp bảng tính CSV thô của log máy chỉ dùng để tra cứu sự kiện, tuyệt đối không nạp vào thư viện tri thức đọc hiểu RAG.

---

## 5. Hợp đồng Đánh giá độ sẵn sàng cho Dự đoán lỗi LSU
**Tên hàm nghiệp vụ**: `evaluate_lsu_readiness(manifest) -> LsuReadinessManifest`

### 📋 Bảng kiểm tra 6 tiêu chí bắt buộc:
1. *Dữ liệu lịch sử đo đạc của cụm LSU có đầy đủ không?*
2. *Định nghĩa các nhãn lỗi có rõ ràng, chính xác không?*
3. *Có Trưởng nhóm kỹ thuật dữ liệu và Quản lý chất lượng ký tên chịu trách nhiệm không?*
4. *Có tiêu chí đánh giá chất lượng và kịch bản thử nghiệm lại (replay) không?*
5. *Có kỹ sư giám sát thử nghiệm bóng song song (shadow) không?*

### 🛡 Kết luận an toàn:
- Nếu thiếu bất kỳ tiêu chí nào trong 5 mục trên $\rightarrow$ Kết luận là **"Bị chặn (`blocked`)"** và liệt kê cụ thể các mục còn thiếu.
- Nếu đáp ứng đủ 5 tiêu chí $\rightarrow$ Kết luận là **"Sẵn sàng chạy thử nghiệm bóng song song (`ready_for_shadow`)"**.
- **Điều khoản khóa cứng**: Hợp đồng này tuyệt đối không có trạng thái đưa vào sản xuất thực tế (`production`), không tự động gọi AI dự đoán và không can thiệp vào máy móc của nhà máy.

---

## 6. Hợp đồng Soạn nháp và Phê duyệt văn bản do AI đề xuất
**Tên hàm nghiệp vụ**: `create_action_proposal(case_id, kind, evidence_digest) -> ActionProposal`

### 📋 Điều kiện tạo bản nháp:
- AI chỉ được phép soạn thảo bản nháp Quy trình thao tác chuẩn (SOP) hoặc Báo cáo điều tra kỹ thuật từ các hồ sơ sự vụ đã có bằng chứng xác thực.
- Nếu hồ sơ chưa được chuyên gia thẩm định hoặc bằng chứng bị rỗng: Hệ thống tự động từ chối tạo nháp.

### 🛡 Rào chắn an toàn khi xuất văn bản:
- Tuyệt đối không cung cấp các lệnh chạy mã độc hại, lệnh can thiệp hệ điều hành, lệnh sửa PLC/bộ điều khiển máy, hoặc lệnh xóa tệp.
- Chữ ký phê duyệt được gắn chặt với mã bản nháp, chức danh người duyệt và mã băm tài liệu gốc.
- Khi người dùng bấm duyệt trên màn hình tiếng Việt, hệ thống chỉ xuất ra một **tệp mới** trong thư mục được cấp phép, tuyệt đối không ghi đè lên tệp cũ.

---

## 7. Các chốt chặn bảo mật không thương lượng (Fail-Closed Invariants)

1. **Bảo mật hình ảnh**: Các cổng kết nối Gemini Web và Nakazasen Router ngoài tuyệt đối từ chối tiếp nhận hình ảnh và bản vẽ kỹ thuật mật trước khi gửi đi.
2. **Đường truyền C-AGENT của công ty**: Chỉ được tiếp nhận dữ liệu kỹ thuật theo đúng chính sách bảo mật nội bộ đã cam kết, không dùng để chứng minh kết quả dự đoán khi chưa đủ điều kiện.
3. **Phân định ranh giới dữ liệu**: Dữ liệu CSV thô bị từ chối khỏi thư viện tri thức đọc hiểu `library.sqlite`; dữ liệu log máy chỉ nằm trong ngăn kéo tra cứu riêng với nhãn "Nghi vấn".
