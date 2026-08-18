# Kim chỉ nam & Học thuyết Sản phẩm AIOS WorkLens (North Star & Product Doctrine)

## 1. AIOS WorkLens là gì
AIOS WorkLens là một **Hệ thống Trí tuệ Công việc Chuyên gia Cá nhân** (Personal Senior Work Intelligence System).
Hệ thống được thiết kế để hỗ trợ người dùng học hỏi, làm việc, điều tra xử lý sự vụ (case), tích lũy kinh nghiệm và trưởng thành như một chuyên gia cao cấp. Thay vì chỉ lưu trữ ghi chú thụ động hay quản lý danh sách việc cần làm thông thường, WorkLens chuyển hóa tài liệu, bảng tính Excel/CSV, ảnh chụp màn hình, log hệ thống, tin nhắn trao đổi, email và kết quả đầu ra của AI thành các hồ sơ sự vụ có bằng chứng xác thực cùng các thẻ ghi nhớ công việc có thể tái sử dụng lâu dài.

---

## 2. AIOS WorkLens KHÔNG PHẢI là gì (Những điều chúng ta tránh)
- **KHÔNG PHẢI là bản sao của NotebookLM:** NotebookLM chỉ tập trung vào đọc hiểu tài liệu dựa trên nguồn. WorkLens kết nối trực tiếp tri thức với các sự vụ công việc thực tế, hành động cụ thể và quy trình bàn giao.
- **KHÔNG PHẢI là bản sao của Cursor / VS Code:** Cursor tập trung vào viết mã lập trình. WorkLens tập trung vào điều tra sự vụ, lập luận logic và đưa ra quyết định vận hành.
- **KHÔNG PHẢI là Second Brain chung chung:** Second Brain thông thường chỉ thu thập tri thức trừu tượng. WorkLens thúc đẩy hành động thực thi, bằng chứng xác thực và bài học kinh nghiệm có cấu trúc từ sự kiện công việc hàng ngày.
- **KHÔNG CHỈ là biểu mẫu sự vụ Streamlit đơn thuần:** Streamlit chỉ là tầng giao diện hiển thị MVP ban đầu. Cốt lõi của hệ thống là mô hình trí tuệ công việc và kho lưu trữ kinh nghiệm bên dưới.
- **KHÔNG CHỈ là công cụ RAG/OCR/ingest thông thường:** WorkLens không chỉ ném tài liệu vào cơ sở dữ liệu vector. Hệ thống tổ chức thông tin thành các hồ sơ sự vụ (case), các nút bằng chứng (evidence node), bản đồ lập luận suy luận (reasoning map) và các thẻ học việc đã được kiểm chứng (verified learning card).
- **KHÔNG BỊA ĐẶT NGUYÊN NHÂN:** Hệ thống tuyệt đối không đoán mò hay tự tiện kết luận "nguyên nhân gốc rễ" khi chưa có đủ bằng chứng. Giả thuyết luôn chỉ là giả thuyết cho đến khi được kiểm chứng.
- **KHÔNG TỰ HỌC THIẾU KIỂM SOÁT:** Hệ thống tích lũy các mẫu học việc, nhưng người dùng bắt buộc phải kiểm tra và xác nhận chuyển trạng thái thẻ sang `confirmed` trước khi được tin cậy đưa vào vận hành.
- **KHÔNG RÒ RỈ DỮ LIỆU:** Dữ liệu thô gắn nhãn `local_only` bị nghiêm cấm gửi hoặc trích xuất ra các dịch vụ AI đám mây theo mặc định.

---

## 3. Vòng lặp Sản phẩm (Product Loop)
```
Knowledge → Case → Evidence → Reasoning Map → Action / Communication → Outcome → Learning Memory → Better Work
```

### Diễn giải chi tiết:
```
Tài liệu nền (Knowledge)
→ Sự việc hằng ngày (Case)
→ Phân tích có bằng chứng (Evidence)
→ Bản đồ tư duy / suy luận (Reasoning Map)
→ Hành động / giao tiếp (Action / Communication)
→ Kết quả thật (Outcome)
→ Bài học rút ra (Learning Memory)
→ Trí nhớ công việc / Lần sau làm tốt hơn (Better Work)
```

---

## 4. Năm Tầng Cốt Lõi + Hai Tầng Nâng Cao của Sản Phẩm

### Tầng 1: Không gian làm việc (Workspace)
- Phân chia các không gian làm việc chuyên biệt theo từng miền nghiệp vụ/ngành nghề.
- Ví dụ: Biên bản sản xuất (Manufacturing MOM), Hỗ trợ CNTT (IT Support), Kế toán, QA/Kiểm thử, Quản lý dự án, Dịch thuật.
- Giữ các hồ sơ sự vụ và cấu hình được cô lập hoàn toàn, tránh lây nhiễm chéo dữ liệu giữa các dự án.

### Tầng 2: Sổ Tri thức (Knowledge Notebook)
- Sổ tri thức dùng để nạp và xử lý các tài liệu nền tảng, hướng dẫn quy trình và cẩm nang vận hành.
- Hỗ trợ cô lập sổ nguồn để các miền hoặc khách hàng khác nhau không bị lẫn lộn dữ liệu.
- Tập trung vào việc đối chiếu tri thức sẵn có để giải quyết các sự vụ đang diễn ra, không chỉ dừng lại ở hỏi đáp thông thường.

### Tầng 3: Trung tâm Sự vụ (Case Cockpit)
- Trung tâm theo dõi và điều tra sự việc phát sinh hàng ngày.
- Tổng hợp log hệ thống, ảnh chụp màn hình, bảng tính Excel, tin nhắn chat, email và ghi chú thủ công.
- Tự động tạo bản đồ sự vụ, gợi ý hành động tiếp theo theo quy tắc, gói prompt định hình và nội dung bàn giao an toàn.

### Tầng 4: Bộ nhớ Học nghề (Learning Memory)
- Đúc kết và lưu giữ các bài học kinh nghiệm từ công việc thực tế.
- Tạo ra **Thẻ Học Nghề Cao Cấp** (Senior Learning Card) chi tiết gồm: triệu chứng, hệ thống liên quan, giả thuyết ban đầu/bị bác bỏ, nguyên nhân đã kiểm chứng, hành động xử lý, bài học tái sử dụng, quy tắc áp dụng, từ khóa nhận diện và mẫu câu phản hồi song ngữ (VI/JA) hữu ích.
- Yêu cầu người dùng kiểm tra và xác nhận thủ công trước khi chuyển trạng thái sang `confirmed`.

### Tầng 5: Huấn luyện viên Chuyên gia / Trí tuệ Công việc (Senior Coach / Work Intelligence)
- Hướng dẫn người dùng như một đồng nghiệp chuyên gia cao cấp tận tâm và dày dặn kinh nghiệm.
- Đưa ra lời khuyên: cần kiểm tra điều gì trước, nên hỏi ai, cách soạn phản hồi tin nhắn/email, chỉ ra các lỗ hổng thiếu bằng chứng và tham chiếu đến các sự vụ tương tự trong quá khứ.
- Từng bước tích hợp sâu với sổ tri thức, lịch sử sự vụ, phong cách giao tiếp và các mẫu kinh nghiệm đã tích lũy.

---

### Tầng 6: Bản đồ Tri thức Trực quan (Visual Knowledge Graph - Tầng Nâng cao)
- Trực quan hóa tri thức đã nạp, hệ thống, cơ sở dữ liệu, quy trình, nhân sự, hồ sơ sự vụ và kết quả lịch sử.
- Chỉ triển khai sau khi nền tảng dữ liệu cục bộ đã hoàn thiện vững chắc. Tuyệt đối không xây dựng đồ thị khi chưa có nền tảng.

### Tầng 7: Trí tuệ Hiện trường & Cảnh báo (Field Intelligence / Alert - Tầng Nâng cao)
- Nhận diện và làm nổi bật các lỗi vận hành trực tiếp từ dữ liệu đo lường từ xa, log và ngữ cảnh chuỗi quy trình.
- Chỉ triển khai khi lược đồ dữ liệu, hồ sơ sự vụ lịch sử và các quy tắc kiểm thực đã hoàn toàn trưởng thành.

---

## 5. Các Nguyên Tắc & Giá Trị Cốt Lõi
- **Bảo mật Ưu tiên Cục bộ (Local-first Security):** Toàn bộ dữ liệu sự vụ và bằng chứng nhạy cảm mặc định luôn lưu trữ ngoại tuyến.
- **Kỷ luật Dựa trên Bằng chứng (Evidence-first Discipline):** Không một giả thuyết nào được coi là nguyên nhân xác thực nếu không có bằng chứng kiểm chứng kèm theo.
- **Trọng tâm Song ngữ (Bilingual Focus):** Hỗ trợ chuẩn xác, độ trung thực cao cho Tiếng Việt và Tiếng Nhật phục vụ các đội ngũ công nghiệp và vận hành.

