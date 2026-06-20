# Chính Sách Ngôn Ngữ Giao Diện (UI Language Policy)

Tài liệu này quy định quy tắc dịch thuật tiếng Việt và kiểm soát việc sử dụng tiếng Anh trên giao diện người dùng (UI) và tài liệu của dự án AIOS WorkLens / Case Cockpit.

---

## 1. Nguyên Tắc Chung
1. **Ưu tiên Tiếng Việt**: Toàn bộ giao diện người dùng hiển thị (tiêu đề, nhãn nút, menu, metric hiển thị, thông báo lỗi, thông báo thành công, tài liệu hướng dẫn người dùng...) phải sử dụng tiếng Việt 100%.
2. **Không lạm dụng tiếng Anh**: Tránh giữ nguyên các từ tiếng Anh trong giao diện nếu có thể diễn đạt rõ ràng và tự nhiên bằng tiếng Việt.

---

## 2. Các Trường Hợp Ngoại Lệ Được Giữ Tiếng Anh
Các thuật ngữ tiếng Anh chỉ được giữ lại trên UI nếu thuộc một trong các nhóm sau đây:

### Nhóm A: Tên sản phẩm, thương hiệu hoặc dịch vụ công nghệ
* *Ví dụ*: Streamlit, GitHub, NotebookLM, Gemini, Copilot.

### Nhóm B: Tên lệnh hoặc tên tệp tin cụ thể
* *Ví dụ*: `pytest`, `compileall`, `RUN_AIOS_CASE_COCKPIT.bat`, `src/aios_habit/case_cockpit.py`.

### Nhóm C: Thuật ngữ kỹ thuật nội bộ bắt buộc và định dạng tệp
* *Ví dụ*: `local_only`, `PYTHONPATH`, `CSV`, `Excel`, `Mermaid`.

---

## 3. Quy Định Chú Giải Tiếng Việt Gần Thuật Ngữ Ngoại Lệ
Nếu bắt buộc phải giữ thuật ngữ tiếng Anh theo ngoại lệ nêu trên trên UI, phải có phần chú giải hoặc giải thích nghĩa tiếng Việt ngay gần đó (trong nhãn, ngoặc đơn hoặc văn bản giải thích phụ).

* *Ví dụ*:
  * **NotebookLM-safe** $\rightarrow$ Bản tóm tắt an toàn cho NotebookLM (loại bỏ dữ liệu `local_only`).
  * **local_only** $\rightarrow$ Chỉ lưu cục bộ, tuyệt đối không đưa vào prompt cho AI đám mây.
  * **Prompt Pack** $\rightarrow$ Gói câu lệnh cho AI.
  * **Excel/CSV** $\rightarrow$ Tệp bảng tính Excel hoặc CSV (dữ liệu dòng/cột).

---

## 4. Phân Biệt Code & UI/Tài Liệu
* **Code nội bộ**: Lập trình viên có thể dùng tiếng Anh cho tên biến, tên hàm, comment kỹ thuật, và các hằng số logic.
* **Giao diện người dùng (UI)**: Bắt buộc tuân thủ 100% tiếng Việt hoặc tiếng Anh có chú giải.
* **Tài liệu hướng dẫn (User Docs)**: Phải dễ hiểu cho đối tượng người dùng không chuyên về kỹ thuật (non-tech).
* **Tài liệu lập trình (Developer Docs)**: Có thể giữ tiếng Anh kỹ thuật nếu cần thiết cho sự chính xác.
