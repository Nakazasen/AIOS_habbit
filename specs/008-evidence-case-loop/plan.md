# Kế hoạch triển khai kỹ thuật: Vòng khép kín từ Hồ sơ sự vụ – Thẩm định chuyên gia – Bài học thực tế

**Mã nhánh**: `008-evidence-case-loop` | **Ngày lập**: 30/08/2026 | **Tài liệu đặc tả**: [spec.md](spec.md)

---

## 1. Tóm tắt kế hoạch (Dành cho Quản lý dự án & Trưởng bộ phận)

### 📌 Hiện trạng hệ thống đã có gì?
- Hệ thống đã có bộ máy tìm kiếm đọc hiểu tài liệu (RAG) kèm trích dẫn nguồn.
- Đã có bộ lọc tách riêng dữ liệu log máy (mã lỗi Jam/C-call) và đánh dấu là "dữ liệu nghi vấn".
- Đã khóa chặt các cổng bảo mật: Cấm nạp CSV thô vào thư viện tri thức đọc hiểu, cấm gửi ảnh sơ đồ mật lên AI đám mây (Gemini Web, Router ngoài), cấm AI tự ý can thiệp file nhà máy.

### ❓ Điểm còn thiếu cần hoàn thiện trong đợt này
1. **Lưu trữ hồ sơ thật**: Trước đây nút "Lưu hồ sơ" chỉ là mô phỏng trên màn hình, nay cần lưu thành tệp cơ sở dữ liệu thật trên máy tính.
2. **Quy trình chuyên gia thẩm định**: Chưa có màn hình để kỹ sư trưởng/chuyên gia vào đọc bằng chứng và bấm nút "Xác nhận đúng / Bác bỏ".
3. **Sổ tay bài học kinh nghiệm**: Chưa có cơ chế đúc kết các ca xử lý thành công thành bài học tra cứu lâu dài.
4. **Cổng kiểm tra an toàn cho dự đoán LSU**: Cần một bảng kiểm tra 6 tiêu chí bắt buộc trước khi cho phép chạy thử nghiệm dự đoán lỗi.

### 🚦 Thứ tự thực hiện tuần tự bắt buộc (Không nhảy cóc)
Quy trình thực hiện chia thành 7 Cổng kiểm soát (Gate 0 $\rightarrow$ Gate 6). Mỗi cổng hoàn thành phải có bài kiểm tra thực tế, được nghiệm thu xong mới chuyển sang cổng tiếp theo:

```text
 [Cổng 0: Nhận dữ liệu bàn giao từ Quản lý]
                   ↓
 [Cổng 1: Lưu trữ Hồ sơ sự vụ thật trên máy tính]
                   ↓
 [Cổng 2: Màn hình Chuyên gia thẩm định & Đóng dấu xác nhận]
                   ↓
 [Cổng 3: Đúc kết Bài học kinh nghiệm vào Sổ tay]
                   ↓
 [Cổng 4: Ghép dữ liệu Log máy vào Hồ sơ điều tra (Mức nghi vấn)]
                   ↓
 [Cổng 5: Bảng kiểm tra 6 điều kiện Sẵn sàng cho Dự đoán LSU]
                   ↓
 [Cổng 6: Trợ lý AI Soạn nháp Báo cáo / SOP — Con người bấm duyệt]
```

---

## 2. Bối cảnh kỹ thuật & Ràng buộc an toàn

- **Ngôn ngữ & Môi trường**: Python 3.11, chạy trên môi trường máy tính cục bộ của nhà máy (`.venv`).
- **Công nghệ lưu trữ**: Sử dụng SQLite cục bộ, chia tách rành mạch thành 3 ngăn kéo độc lập:
  1. `library.sqlite`: Ngăn kéo chỉ chứa **Sách quy chuẩn, tài liệu SOP, tiêu chuẩn kỹ thuật** đã được duyệt.
  2. `line_events.sqlite`: Ngăn kéo chỉ chứa **Dữ liệu log máy, sự kiện cảnh báo Jam/C-call** (ở mức nghi vấn).
  3. `local_cases/workspace_cases.sqlite`: Ngăn kéo mới, chuyên lưu trữ **Hồ sơ sự vụ, biên bản thẩm định của chuyên gia, bài học kinh nghiệm và các bản dự thảo báo cáo**.
- **Nguyên tắc an toàn bất di bất dịch**:
  - *Không nạp CSV thô vào thư viện tri thức đọc hiểu.*
  - *Không gửi hình ảnh/sơ đồ mật ra ngoài mạng nội bộ.*
  - *Không để AI tự động kết luận nguyên nhân hỏng hóc hay tự động điều khiển máy móc.*
  - *Không xóa, không ghi đè bất kỳ tệp dữ liệu gốc nào của nhà máy.*
  - *Toàn bộ giao diện hiển thị 100% bằng tiếng Việt rõ ràng, dễ hiểu.*

---

## 3. Bảng tự đánh giá tuân thủ Hiến chương dự án (Constitution Gate Audit)

| Tiêu chuẩn an toàn | Trạng thái trước khi làm | Đánh giá sau thiết kế | Giải pháp kiểm soát thực tế |
|---|---|---|---|
| **1. An toàn dữ liệu nhà máy** | Nút lưu hồ sơ còn là mô phỏng, dễ nhầm lẫn. | **ĐẠT (PASS)** | Tạo cơ sở dữ liệu riêng cục bộ `workspace_cases.sqlite`, làm sạch dữ liệu trước khi lưu, không sao chép dữ liệu chat riêng tư vào kho chung. |
| **2. Trung thực, có bằng chứng (Chống PASS ảo)** | Chưa có chỗ cho chuyên gia xác nhận. | **ĐẠT (PASS)** | Mọi nhận định bắt buộc gắn kèm nguồn trích dẫn. Thiếu bằng chứng thì hệ thống tự động khóa lại (`blocked`), không cho duyệt. |
| **3. Phân định ranh giới hệ thống** | Cần tránh import các module cũ không còn dùng. | **ĐẠT (PASS)** | Viết module mới gọn gàng, độc lập, có bài kiểm tra import tự động để chặn code rác. |
| **4. Bảo mật hình ảnh và quyền riêng tư** | Nguy cơ lọt ảnh sơ đồ mạch ra ngoài. | **ĐẠT (PASS)** | Giữ vững chốt chặn Gate C: Gemini Web và Router ngoài tuyệt đối bị chặn gửi ảnh; chỉ đường truyền riêng C-AGENT của công ty mới được phép. |
| **5. Giới hạn quyền hạn của Trợ lý AI** | AI có thể tự ý sửa file bừa bãi. | **ĐẠT (PASS)** | Tước bỏ hoàn toàn quyền chạy lệnh tự động của AI. AI chỉ được soạn nháp, con người bấm duyệt trên màn hình thì tệp mới được xuất ra. |
| **6. Ngôn ngữ giao diện** | Chưa có màn hình cho quy trình mới. | **ĐẠT (PASS)** | Toàn bộ nhãn, nút bấm, thông báo lỗi viết bằng tiếng Việt tự nhiên, không lộ lỗi kỹ thuật phức tạp. |

---

## 4. Chi tiết thực hiện theo 7 Cổng kiểm soát

### 🚪 Cổng 0: Tiếp nhận đầu vào thực tế từ Chủ sở hữu (Không thể code thay)
* **Việc cần làm**: Chủ sở hữu hệ thống cung cấp danh sách vai trò chuyên gia (ai là Kỹ sư trưởng, ai là Quản lý chất lượng có quyền duyệt), mẫu log thực tế của dây chuyền và bộ dữ liệu mẫu LSU.
* **Quy tắc an toàn**: Lập trình viên không được tự bịa ra chức danh, không tự bịa ra dữ liệu mẫu. Nếu chưa có dữ liệu thật thì hệ thống dừng lại ở trạng thái "Chờ bàn giao (`blocked`)", không được báo hoàn thành giả tạo.

---

### 🚪 Cổng 1: Xây dựng tính năng Lưu trữ Hồ sơ sự vụ cục bộ thật
* **Việc cần làm**: Lập trình hàm lưu hồ sơ thật (`create_case_from_trace_id`). Chỉ lưu mã phiên, mã câu trả lời, mã trace, mã băm và các tham chiếu nguồn đã có vào `local_cases/workspace_cases.sqlite`; không sao chép câu hỏi, câu trả lời hoặc đoạn trích nguồn.
* **Kết quả kiểm tra**: Bấm lưu trên giao diện chat $\rightarrow$ Hồ sơ được ghi nhận ngay lập tức $\rightarrow$ Tắt ứng dụng bật lại vẫn đọc được đầy đủ dữ liệu.

---

### 🚪 Cổng 2: Màn hình Chuyên gia thẩm định & Ký duyệt kết luận
* **Việc cần làm**: Xây dựng giao diện cho phép chuyên gia mở từng hồ sơ sự vụ, đọc lại căn cứ trích dẫn và chọn:
  - *Xác nhận đúng*: Nhập tên, phòng ban và lý do xác nhận.
  - *Bác bỏ*: Nhập lý do từ chối.
  - *Yêu cầu thêm bằng chứng*: Ghi rõ cần bổ sung tài liệu hay dữ liệu log nào.
* **Kết quả kiểm tra**: Nếu một người không có thẩm quyền hoặc không nhập lý do bấm duyệt, hệ thống từ chối ngay lập tức.

---

### 🚪 Cổng 3: Cơ chế Đúc kết Bài học kinh nghiệm vào Sổ tay
* **Việc cần làm**: Cho phép Quản lý chất lượng bấm chọn các nhận định đã được chuyên gia xác nhận để chuyển thành "Bài học kinh nghiệm chính thức".
* **Kết quả kiểm tra**: Bài học luôn hiển thị rõ nguồn gốc: Thuộc hồ sơ nào, trích dẫn tài liệu nào, chuyên gia nào đã ký duyệt. Bài học này độc lập, không làm thay đổi hay sửa chữa các tài liệu tiêu chuẩn SOP gốc.

---

### 🚪 Cổng 4: Ghép nối Dữ liệu Log máy vào Hồ sơ điều tra (Mức nghi vấn)
* **Việc cần làm**: Cho phép đính kèm các dòng log lỗi Jam/C-call từ `line_events.sqlite` vào hồ sơ sự vụ.
* **Quy tắc an toàn**: Toàn bộ sự kiện log hiển thị dưới nhãn "Nghi vấn / Cần đối chứng". Không tự ý vẽ sơ đồ cảm biến hỏng hay phán đoán nguyên nhân khi chưa có kỹ sư hiện trường kiểm tra.

---

### 🚪 Cổng 5: Bảng kiểm tra 6 tiêu chí Sẵn sàng cho Dự đoán lỗi LSU
* **Việc cần làm**: Xây dựng bảng kiểm tra tự động 6 điều kiện bắt buộc trước khi thử nghiệm dự đoán lỗi:
  1. *Dữ liệu lịch sử đo đạc có đầy đủ không?*
  2. *Nhãn phân loại lỗi có chính xác không?*
  3. *Có chuyên gia chịu trách nhiệm về chất lượng không?*
  4. *Có quy trình kiểm tra lại kết quả (replay) không?*
  5. *Có người giám sát thử nghiệm bóng song song không?*
  6. *Chủ sở hữu hệ thống đã ký duyệt văn bản chưa?*
* **Kết quả kiểm tra**: Thiếu bất kỳ điều kiện nào $\rightarrow$ Trạng thái là "Bị chặn (`blocked`)". Đủ điều kiện $\rightarrow$ Chỉ cho phép chạy thử nghiệm ngầm (`ready_for_shadow`), tuyệt đối không được tự động phát loa cảnh báo hay can thiệp máy móc.

---

### 🚪 Cổng 6: Trợ lý AI Soạn nháp Quy trình & Báo cáo (Con người bấm duyệt)
* **Việc cần làm**: AI đọc bằng chứng trong hồ sơ đã được chuyên gia duyệt để soạn thảo bản nháp báo cáo hoặc quy trình SOP dưới định dạng Markdown.
* **Quy tắc an toàn**:
  - Bản nháp mang trạng thái "Chưa phê duyệt".
  - Người dùng bấm "Duyệt bản nháp" trên giao diện tiếng Việt thì tệp mới được lưu ra ổ cứng.
  - Cấm hoàn toàn AI ghi đè tệp cũ hoặc xóa tệp của nhà máy.

---

## 5. Kế hoạch kiểm thử và bàn giao

1. **Kiểm thử tự động từng bước**: Mỗi cổng đều có các bài kiểm tra tự động (Unit Test) chạy độc lập, xanh 100% mới được làm tiếp.
2. **Kiểm tra biên dịch và không xung đột**: Chạy `compileall` sạch lỗi và `git diff --check` không có khoảng trắng thừa.
3. **Cập nhật tài liệu chính thức**: Cập nhật tài liệu kiến trúc và bàn giao kỹ thuật, nêu rõ những gì đã làm được và những gì còn đang chờ dữ liệu thực tế từ nhà máy.
