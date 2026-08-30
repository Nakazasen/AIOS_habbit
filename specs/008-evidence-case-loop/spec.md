# Đặc tả tính năng: Vòng khép kín từ Hồ sơ sự vụ – Thẩm định chuyên gia – Bài học thực tế (Có bằng chứng)

**Mã nhánh tính năng**: `008-evidence-case-loop`  
**Ngày lập**: 30/08/2026  
**Trạng thái**: Bản dự thảo xin ý kiến phê duyệt trước khi lập trình  
**Mục tiêu tổng quát**: Xây dựng một quy trình hoàn chỉnh và chặt chẽ: *Phát sinh sự vụ $\rightarrow$ Thu thập bằng chứng $\rightarrow$ Đề xuất hướng xử lý $\rightarrow$ Chuyên gia con người phê duyệt $\rightarrow$ Đúc kết bài học kinh nghiệm*. Tuyệt đối không để AI tự ý chẩn đoán, không tự ý điều khiển máy móc và không coi các kết quả suy đoán là sự thật khi chưa có bằng chứng thực tế.

---

## 1. Phạm vi và ranh giới áp dụng (Dành cho người quản lý & vận hành)

### 🎯 Hệ thống sẽ làm gì?
Hệ thống kết nối các mảnh ghép đang rời rạc thành một quy trình làm việc minh bạch, có thể kiểm tra lại bất cứ lúc nào:
1. **Lập hồ sơ sự vụ**: Khi người dùng hỏi đáp trên giao diện chat và nhận được câu trả lời kèm tài liệu trích dẫn, hệ thống cho phép bấm lưu thành một "Hồ sơ sự vụ" lưu trữ cục bộ trên máy tính.
2. **Mời chuyên gia thẩm định**: Chuyên gia kỹ thuật của nhà máy mở hồ sơ, kiểm tra lại các trích dẫn và bấm nút "Xác nhận đúng" hoặc "Bác bỏ" kèm lý do rõ ràng.
3. **Đúc kết bài học**: Chỉ những kết luận đã được chuyên gia ký duyệt mới được chuyển thành "Bài học kinh nghiệm" để tra cứu sau này.
4. **Kiểm tra độ sẵn sàng cho dự đoán lỗi**: Đưa ra bảng kiểm tra nghiêm ngặt trước khi thử nghiệm dự đoán lỗi cho cụm máy LSU, đảm bảo không bao giờ đưa mô hình chưa kiểm chứng vào dây chuyền sản xuất.

### 🚫 Những điều hệ thống TUYỆT ĐỐI KHÔNG LÀM (Ranh giới an toàn)
- Không để AI tự động kết luận nguyên nhân gốc rễ hay tự chẩn đoán hỏng hóc thiết bị.
- Không tự động gửi lệnh điều khiển tới máy móc, dây chuyền, PLC hay hệ thống điều khiển nhà máy.
- Không tự động ghi đè, sửa đổi hay xóa bất kỳ tệp dữ liệu gốc nào của nhà máy.
- Không gửi hình ảnh, bản vẽ kỹ thuật mật lên các dịch vụ đám mây công cộng (Gemini Web, Router ngoài).
- Không tự động nạp các tệp bảng tính CSV thô vào thư viện tri thức chung khi chưa được xử lý.

---

## 2. Các tình huống sử dụng thực tế (User Stories)

### Câu chuyện 1: Lưu hồ sơ sự vụ từ câu trả lời có trích dẫn tài liệu (Ưu tiên: P1)
* **Bối cảnh**: Kỹ sư đang tra cứu cách xử lý một hiện tượng lỗi trên giao diện Workspace Chat và nhận được câu trả lời kèm các đoạn trích dẫn từ tài liệu hướng dẫn (SOP).
* **Hành động**: Kỹ sư bấm nút "Lưu hồ sơ sự vụ". Hệ thống sẽ gom câu hỏi, câu trả lời, danh sách nguồn trích dẫn và thời điểm tạo thành một bộ hồ sơ lưu trên máy tính.
* **Ý nghĩa thực tế**: Thay thế nút bấm mang tính "mô phỏng" trước đây bằng tính năng lưu trữ thật, giúp lưu lại bằng chứng để gửi cho chuyên gia hoặc ca sau xem xét.
* **Tiêu chí nghiệm thu**:
  1. Khi câu trả lời có đầy đủ nguồn trích dẫn, việc lưu hồ sơ phải thành công, sinh mã hồ sơ duy nhất và ghi nhận thời gian rõ ràng.
  2. Nếu thiếu nguồn trích dẫn hoặc xảy ra lỗi lưu tệp, hệ thống phải báo lỗi bằng tiếng Việt dễ hiểu, không được tạo ra hồ sơ lỗi dở dang.
  3. Hồ sơ này được lưu riêng tại máy cục bộ, không tự tiện sao chép nội dung chat riêng tư lên kho dữ liệu dùng chung.

---

### Câu chuyện 2: Chuyên gia thẩm định và xác nhận kết luận (Ưu tiên: P1)
* **Bối cảnh**: Chuyên gia kỹ thuật phụ trách công đoạn mở hồ sơ sự vụ vừa được tạo để đánh giá.
* **Hành động**: Chuyên gia đọc lại các trích dẫn tài liệu và log, sau đó nhập ý kiến nhận xét, bấm "Xác nhận đúng", "Từ chối" hoặc "Yêu cầu thêm bằng chứng" trong phạm vi trách nhiệm của mình.
* **Ý nghĩa thực tế**: Ngăn chặn tình trạng câu trả lời do AI sinh ra bị nhầm lẫn thành quy trình chuẩn của nhà máy. Chỉ con người có chuyên môn mới có quyền xác nhận sự thật.
* **Tiêu chí nghiệm thu**:
  1. Khi chưa có chuyên gia phê duyệt, mọi nhận định chỉ ở trạng thái "Ứng viên / Chờ duyệt (`candidate`)".
  2. Khi chuyên gia bấm xác nhận, hệ thống bắt buộc phải ghi lại: Tên chuyên gia, vai trò/phòng ban, lý do phê duyệt và thời điểm duyệt.
  3. Nếu thiếu thông tin người duyệt hoặc thiếu căn cứ bằng chứng, hệ thống sẽ tự động khóa lại (fail-closed) và không cho phép duyệt.

---

### Câu chuyện 3: Đưa bài học đã xác nhận vào sổ tay kinh nghiệm (Ưu tiên: P1)
* **Bối cảnh**: Quản lý chất lượng muốn lưu lại một ca xử lý lỗi xuất sắc để đào tạo kỹ sư mới hoặc tra cứu sau này.
* **Hành động**: Người có thẩm quyền chọn nhận định đã được chuyên gia xác nhận và bấm "Duyệt thành bài học kinh nghiệm".
* **Ý nghĩa thực tế**: Giúp nhà máy giữ lại tri thức vận hành quý báu nhưng chỉ học từ những gì đã được kiểm chứng thực tế 100%, tránh "học vẹt" từ những suy đoán sai lệch.
* **Tiêu chí nghiệm thu**:
  1. Chỉ những nội dung đã được chuyên gia xác nhận mới được nâng cấp thành bài học chính thức.
  2. Bài học luôn lưu kèm nguồn gốc: Thuộc hồ sơ sự vụ nào, do chuyên gia nào duyệt, dựa trên tài liệu nào.
  3. Bài học này dùng để người đọc tra cứu, không tự động can thiệp vào mô hình AI hay làm thay đổi tài liệu gốc.

---

### Câu chuyện 4: Thử nghiệm điều tra dữ liệu log máy ở mức nghi vấn (Ưu tiên: P2)
* **Bối cảnh**: Kỹ sư nạp bảng dữ liệu log lỗi (dạng Jam máy, gọi hỗ trợ C-call) vào hồ sơ sự vụ để đối chiếu với tài liệu quy trình.
* **Hành động**: Hệ thống hiển thị các sự kiện log dưới nhãn "Nghi vấn (`suspected`)" để chuyên gia xem xét, không khẳng định là nguyên nhân gây hỏng hóc.
* **Ý nghĩa thực tế**: Tránh việc nhìn thấy mã lỗi trong log là vội vàng kết luận hỏng cảm biến hay linh kiện khi chưa có kỹ sư hiện trường kiểm tra.
* **Tiêu chí nghiệm thu**:
  1. Mọi sự kiện trích xuất từ bảng log máy luôn mang trạng thái "Nghi vấn".
  2. Tệp bảng tính CSV chỉ dùng để tra cứu log, không nạp vào thư viện tri thức đọc hiểu RAG.
  3. Khi chưa có bản đồ vị trí cảm biến được chuyên gia đóng dấu, hệ thống không được tự ý vẽ sơ đồ phán đoán vị trí lỗi.

---

### Câu chuyện 5: Kiểm tra độ sẵn sàng trước khi dự đoán lỗi cụm LSU (Ưu tiên: P3)
* **Bối cảnh**: Nhóm kỹ sư muốn thử nghiệm giải pháp AI dự đoán lỗi cho cụm máy quét laser LSU.
* **Hành động**: Hệ thống chạy bảng kiểm tra xem đã đủ 6 điều kiện bắt buộc chưa: *Dữ liệu lịch sử có đủ không? Nhãn lỗi có chính xác không? Có người chịu trách nhiệm chất lượng không? Có phương án kiểm thử lại không? Có người giám sát thử nghiệm bóng (shadow) không?*
* **Ý nghĩa thực tế**: Đảm bảo không bao giờ đưa một mô hình AI "chưa đủ lông đủ cánh" vào dây chuyền sản xuất thực tế.
* **Tiêu chí nghiệm thu**:
  1. Nếu thiếu bất kỳ điều kiện nào trong 6 tiêu chí trên, hệ thống báo trạng thái "Bị chặn (`blocked`)" và chỉ rõ mục còn thiếu.
  2. Khi đủ điều kiện, hệ thống chỉ cho phép chuyển sang trạng thái "Sẵn sàng chạy thử nghiệm bóng song song (`ready_for_shadow`)" để người vận hành quan sát, không phát cảnh báo hay can thiệp dây chuyền.

---

### Câu chuyện 6: Trợ lý AI chỉ soạn nháp tài liệu, con người bấm duyệt (Ưu tiên: P2)
* **Bối cảnh**: Sau khi đã có hồ sơ và ý kiến chuyên gia, trợ lý AI hỗ trợ kỹ sư soạn nhanh một bản dự thảo quy trình (SOP) hoặc báo cáo kỹ thuật.
* **Hành động**: AI tạo bản nháp Markdown. Kỹ sư đọc lại, chỉnh sửa và bấm nút duyệt trên màn hình tiếng Việt thì tệp mới được xuất ra thư mục cho phép.
* **Ý nghĩa thực tế**: AI đóng vai trò "tay phải" hỗ trợ soạn thảo văn bản, giảm thời gian gõ báo cáo cho kỹ sư, nhưng quyền quyết định cuối cùng 100% thuộc về con người.
* **Tiêu chí nghiệm thu**:
  1. AI chỉ được tạo tệp mới tại thư mục được chỉ định, tuyệt đối không được ghi đè hay xóa tệp có sẵn.
  2. Khi người dùng chưa bấm nút duyệt trên màn hình, tệp nháp không thể xuất ra thành văn bản chính thức.
  3. Mọi yêu cầu tự động chỉnh sửa máy móc, can thiệp PLC hay tự phát hành văn bản đều bị hệ thống từ chối ngay lập tức.

---

## 3. Bảng thuật ngữ dễ hiểu cho nhà máy (Glossary)

| Thuật ngữ kỹ thuật | Tên gọi dễ hiểu trong nhà máy | Giải thích ý nghĩa thực tế |
|---|---|---|
| **`CaseRecord`** | **Hồ sơ sự vụ** | Bản ghi chép lại toàn bộ một ca xử lý lỗi: Kỹ sư hỏi gì, tài liệu nói gì, chuyên gia nhận xét ra sao. |
| **`EvidenceReference`** | **Căn cứ trích dẫn** | Đoạn văn bản trong tiêu chuẩn SOP hoặc dòng log máy được dùng làm bằng chứng đối chiếu. |
| **`ExpertReview`** | **Ý kiến thẩm định chuyên gia** | Nhận xét, đánh giá chính thức của kỹ sư trưởng hoặc chuyên gia phụ trách công đoạn. |
| **`LearningRecord`** | **Bài học kinh nghiệm** | Tri thức xử lý lỗi đã được chứng minh hiệu quả thực tế, dùng để lưu truyền trong nhà máy. |
| **`Candidate`** | **Ứng viên / Chờ duyệt** | Trạng thái dự thảo do máy hoặc người tạo ra, chưa có giá trị pháp lý cho đến khi chuyên gia ký duyệt. |
| **`Confirmed`** | **Đã xác nhận** | Chuyên gia đã kiểm tra và đóng dấu đồng ý với kết luận. |
| **`Suspected`** | **Nghi vấn / Cần đối chứng** | Dữ liệu log máy ghi nhận hiện tượng bất thường nhưng chưa thể khẳng định là lỗi hỏng thật. |
| **`Fail-Closed`** | **Tự động khóa an toàn** | Nguyên tắc bảo vệ: Cứ thiếu thông tin, thiếu người duyệt hoặc có nghi ngờ là hệ thống tự động dừng lại, không cho đi tiếp. |
| **`Shadow Mode`** | **Thử nghiệm bóng song song** | Mô hình AI chạy ngầm để người vận hành quan sát đánh giá độ chính xác, không phát loa cảnh báo hay dừng máy của xưởng. |

---

## 4. Tiêu chí thành công đánh giá bằng mắt và số liệu

1. **Minh bạch 100%**: Mở bất kỳ một bài học hay quy trình nháp nào, người quản lý đều thấy rõ: *Dựa vào tài liệu nào, đoạn trích dẫn ở đâu, ai là người bấm duyệt*.
2. **Không có cảnh báo giả**: Không bao giờ xảy ra việc AI tự ý báo lỗi hay tự nhận định nguyên nhân hỏng hóc khi chưa có chuyên gia đối chứng.
3. **An toàn tuyệt đối**: Thử bấm các thao tác xóa tệp nhà máy, ghi đè tài liệu gốc hay gửi ảnh mật ra ngoài đều bị chặn đứng 100%.
4. **Giao diện thuần Việt**: Toàn bộ nút bấm, thông báo trạng thái, bảng biểu đều hiển thị bằng tiếng Việt rõ ràng, mạch lạc, không có các đoạn lỗi mã nguồn khó hiểu.
