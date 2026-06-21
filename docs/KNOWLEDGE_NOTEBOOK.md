# Hướng dẫn sử dụng Sổ tri thức (Knowledge Notebook) trong AIOS Case Cockpit

Tài liệu này giải thích các khái niệm cốt lõi, cách sử dụng và các nguyên tắc bảo mật của **Không gian làm việc (Workspace)**, **Sổ tri thức (Knowledge Notebook)** và **Tài liệu nguồn (Source Document)** trong AIOS Case Cockpit kể từ Gate M1.7 và nâng cấp NotebookLM Bridge ở M1.8.

---

## 1. Các khái niệm cốt lõi

### 📁 Không gian làm việc (Workspace)
* **Khái niệm:** Workspace là phân vùng cao nhất dùng để phân chia công việc theo ngành hoặc domain cụ thể (ví dụ: *IT Support*, *Kế toán*, *MOM nhà máy máy in*, *QA*).
* **Mục đích:** Đảm bảo hồ sơ sự việc (Case) và sổ tri thức (Notebook) của các bộ phận khác nhau không bị trộn lẫn hay làm loãng ngữ cảnh.

### 📚 Sổ tri thức (Knowledge Notebook)
* **Khái niệm:** Sổ tri thức là một tuyển tập chứa các tài liệu tham chiếu, quy trình hoặc hướng dẫn nghiệp vụ nền của hệ thống.
* **Quy tắc:** Sổ tri thức thuộc về một Workspace cụ thể. Nó không đại diện cho một sự cố hay sự việc nào cả, mà đóng vai trò là "tri thức tham chiếu nền".

### 📄 Tài liệu nguồn (Source Document)
* **Khái niệm:** Là các tệp tin tài liệu nền tải lên Sổ tri thức (ví dụ: file PDF hướng dẫn sử dụng thiết bị, sơ đồ kiến trúc hệ thống, danh sách bảng cơ sở dữ liệu, file excel đặc tả thông số kỹ thuật).

---

## 2. Điểm khác biệt quan trọng giữa Tài liệu nguồn (Source Document) và Bằng chứng sự việc (Evidence)

Để tránh nhầm lẫn luồng xử lý và đảm bảo chất lượng suy luận, AIOS phân định rất rõ:

| Tiêu chí | Tài liệu nguồn (Source Document) | Bằng chứng sự việc (Evidence) |
| :--- | :--- | :--- |
| **Bản chất** | Tri thức nền, cẩm nang, tài liệu tham khảo chung. | Dữ liệu phát sinh thực tế liên quan đến sự cố cụ thể. |
| **Nơi lưu trữ** | Thuộc **Sổ tri thức (Notebook)**. | Thuộc **Hồ sơ sự việc (Case)**. |
| **Ví dụ** | PDF manual thiết bị, Excel đặc tả cơ sở dữ liệu hệ thống. | Log lỗi cụ thể tại thời điểm chết, ảnh chụp màn hình thông báo lỗi. |
| **Quy mô ảnh hưởng** | Dùng chung cho nhiều Case khác nhau nếu chung nghiệp vụ. | Chỉ gắn liền và có giá trị chứng minh cho riêng một Case đó. |

---

## 3. Liên kết Case với Notebook

* **Quy tắc liên kết:** Một sự việc (Case) phát sinh có thể tham chiếu đến một hoặc nhiều **Sổ tri thức (Notebook)** liên quan.
* **Tác dụng:** Khi biên dịch gói Prompt Pack hoặc tài liệu Bàn giao (Handover) cho AI, hệ thống sẽ tự động đính kèm liên kết nghiệp vụ và tóm tắt danh sách tài liệu tham khảo nền từ Sổ tri thức liên quan, giúp AI có ngữ cảnh nghiệp vụ rộng hơn để chẩn đoán nguyên nhân.

---

## 4. Các giới hạn kỹ thuật ở M1.7

> [!IMPORTANT]
> **Giới hạn phạm vi (Scope Limits) ở Gate M1.7:**
> * **Không sử dụng RAG:** Hệ thống chưa thực hiện chia nhỏ tài liệu, nhúng vector (embedding) hay tìm kiếm ngữ nghĩa qua cơ sở dữ liệu Vector.
> * **Không làm OCR:** Không tự động nhận diện chữ từ ảnh tài liệu nguồn.
> * **Không xây dựng Đồ thị tri thức (Knowledge Graph):** Chưa phân tích tự động thực thể và mối quan hệ từ tài liệu.
> * **Chế độ xem trước tinh gọn:** Tài liệu nguồn tải lên chỉ hiển thị một bản xem trước tĩnh (Preview) ngắn (TXT/MD đọc tối đa 1000 ký tự đầu; CSV/Excel đọc danh sách cột và vài dòng dữ liệu đầu để kiểm chứng).

---

## 5. Chính sách Bảo mật dữ liệu cục bộ (Local-First Privacy)

* **Không theo dõi qua Git:** Toàn bộ dữ liệu Workspace, Notebook, metadata và tệp tin tải lên đều nằm trong thư mục `local_cases/` (đã cấu hình bỏ qua trong `.gitignore`), đảm bảo không bao giờ bị đẩy lên kho chứa Git công khai.
* **Chống rò rỉ lên Cloud:** Các tài liệu nguồn được đánh dấu là `local_only` (Chỉ lưu cục bộ) sẽ tự động bị che giấu hoặc loại bỏ hoàn toàn phần preview thô trong Prompt Pack khi biên dịch cho các AI đám mây (Gemini, GPT, Copilot, NotebookLM Safe).
* **Định vị đường dẫn an toàn:** Mọi tệp tin tải lên đều được kiểm tra tính hợp lệ của thư mục đích qua cơ chế so khớp Path Containment của Python (`Path.is_relative_to()`), ngăn ngừa hoàn toàn các cuộc tấn công Directory Traversal.

---

## 6. NotebookLM Bridge & Persistence (Nâng cấp M1.8)

Kể từ Gate M1.8A - M1.8D, AIOS Case Cockpit bổ sung các khả năng nâng cao để tích hợp và lưu trữ dữ liệu từ NotebookLM:
* **Q&A Truth Modes (Chế độ Chân lý Hỏi đáp):**
  1. *AIOS Local Context:* Truy vấn bằng dữ liệu cục bộ hoàn toàn qua công cụ tìm kiếm keyword/phrase matching cục bộ và gọi LLM thông qua adapter tương thích OpenAI (urllib). Chế độ này bị chặn cứng nếu dùng Cloud AI để chống rò rỉ dữ liệu `local_only`.
  2. *Cloud-safe Context:* Tự động ẩn các bằng chứng `local_only` (để lại placeholder redacted) trước khi gửi cho Cloud AI.
  3. *NotebookLM Bridge:* Tạo prompt tối ưu để dán thủ công sang NotebookLM (không gửi dữ liệu tự động).
* **NotebookLM Bridge Prompt Schemas:**
  Hệ thống cung cấp các prompt có khuôn mẫu chặt chẽ để NotebookLM trả về dữ liệu chuẩn cấu trúc JSON/Mermaid cho 4 loại:
  - `knowledge_graph_json`: Đồ thị tri thức dạng JSON.
  - `study_pack_json`: Bộ học tập ôn bài dạng JSON.
  - `case_investigation_json`: Phân tích điều tra hồ sơ dạng JSON.
  - `mermaid_graph`: Sơ đồ Mermaid thô.
* **Paste & Persistence Store:**
  - Hỗ trợ dán trực tiếp kết quả trả về từ NotebookLM, tự động parse sạch codeblock fences và hiển thị preview trực quan.
  - Nút **Lưu kết quả vào AIOS** ghi nhận dữ liệu vào `local_cases/notebook_bridge_imports.jsonl` với trạng thái mặc định là `draft` và quyền bảo mật `local_only`.
  - Hiển thị danh sách kết quả đã lưu kèm tính năng xóa bản ghi.
  - Tích hợp kết quả đồ thị Mermaid đã lưu vào tab **Bản đồ** để trực quan hóa quan hệ thực thể.
