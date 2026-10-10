# Báo cáo nghiệm thu giao diện Mục 0.2 (SYNTH-Q0668-FILTER-FIX-HOME)

- **Mã vé / Mục**: `Mục 0.2 - Chẩn đoán gốc rễ, sửa hẹp nhất và nghiệm thu giao diện Streamlit dùng thật`
- **Máy thực hiện**: Nhà `h410asrock` (thợ `agy`).
- **Thời điểm hoàn thành**: 2026-10-10 11:35 +07.
- **Commit mã nguồn bản vá**: `51bd6d2` (`fix(retrieval): route mechanical spec queries to LSU and enable block param in UI (Muc 0.2)`).
- **Trạng thái**: **ĐẠT 100% (PASS)**.

---

## 1. Tóm tắt chẩn đoán gốc rễ Q0668 trên giao diện

1. **Hiện tượng ban đầu**:
   - Khi chạy kiểm thử tự động trên harness RAG v2 (`do_rag_50_synth_q0668_filter_fix.py`), Q0668 đạt trọn vẹn điểm (2.0 chính xác + 1.0 đầy đủ + 1.0 trích dẫn = 4.0 điểm) nhờ nạp đúng bản vẽ cơ khí `3V2ND19040` (chứa nominal và giới hạn của g1/g2).
   - Tuy nhiên, trên giao diện tương tác Streamlit (`workspace_chat_app.py`), khi người dùng mở sổ MOM (`mom_opcenter`) mà không chỉ định khối tri thức, hệ thống tìm kiếm trên toàn bộ 889 tài liệu của thư viện hợp nhất.
   - Do từ khóa `g1` / `g2` quá ngắn, bộ định tuyến từ vựng vô tình khớp nhãn chân pin của các sơ đồ mạch điện tử MOM (`DP IF ASSY_7PA1153CJF.pdf`, `MAIN_3V2XC47010_04.pdf`), dẫn đến việc mô hình kết luận g1/g2 là pin label và không tìm thấy dung sai/nominal cơ khí.

2. **Bản vá hẹp nhất đã áp dụng (Commit `51bd6d2`)**:
   - `src/aios_habit/index_domain.py`: Bổ sung từ khóa đo lường kỹ thuật LSU (`skew`, `beam`, `beam径`, `DMT/PMT`, `điểm đo G`, `thông số đo lường`, `khối LD`), đồng thời chuẩn hóa regex nhận diện điểm đo `\b[gG]\d{1,2}\b` để tránh nhầm với mã buồng máy `C33`.
   - `src/aios_habit/workspace_chat_app.py`: Bổ sung tham số `&block=lsu` trên URL để khởi tạo chính xác khối tri thức LSU cho phiên hội thoại mới.
   - `src/aios_habit/workspace_chat_rag_v2_adapter.py`: Bổ sung cơ chế `_select_domain_route` để khi tự động chọn khối trên `library.sqlite` hợp nhất, bộ lọc `document_id` của khối LSU vẫn được kích hoạt chặt chẽ (`applied=True`).

---

## 2. Kết quả kiểm thử giao diện thực tế (Playwright E2E)

- **Môi trường chạy**: Runtime **CPU-only**, cổng `8516`, lane `nakazasen_router` (ghim tay).
- **Mã phiên hội thoại mới hoàn toàn**: `CONV-Q0668-6AC9BA1F` (khối tri thức LSU: 92 tài liệu).
- **Chỉ số toàn vẹn cơ sở dữ liệu (`library.sqlite`)**:
  - Kích thước trước và sau phiên: **2.942.201.856 byte** (khớp tuyệt đối).
  - Mã băm SHA-256 trước và sau: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` (bất biến 100%).

### Bảng số liệu đo lường 3 câu hỏi

| STT | Mã câu | Loại câu hỏi / Nội dung | Thời gian trả lời (s) | Độ dài đáp án | Trích dẫn hợp lệ | Trạng thái |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| 1 | **Q0668** | Ca gỡ oan: Nominal và giới hạn g1/g2 | **300.42 s** | 1.813 ký tự | **Có** (`[1]`, `[2]`, `[3]`, `[4]`) | **ĐẠT** |
| 2 | **Q0718** | Đối chứng 1: Phân tích nguyên nhân chênh lệch DMT–PMT | **170.97 s** | 2.396 ký tự | **Có** (`[1]`..`[12]`) | **ĐẠT** |
| 3 | **Q0709** | Đối chứng 2: Bảng quy đổi Skew (µm và dot theo 4 màu) | **378.12 s** | 1.930 ký tự | **Có** (`[1]`, `[2]`, `[3]`, `[4]`) | **ĐẠT** |

---

## 3. Danh mục tệp minh chứng đính kèm

1. File dữ liệu nghiệm thu JSON:
   - `docs/phieu-viec/ket-qua/nghiem-thu-ui-synth-q0668-filter-fix-home.json`
2. Bộ 4 ảnh chụp giao diện Playwright (chụp trọn thân viewport):
   - `docs/phieu-viec/ket-qua/ui-synth-q0668-filter-fix-01-app-ready.png` (102.199 bytes): Giao diện ứng dụng khởi động sẵn sàng tại cổng 8516.
   - `docs/phieu-viec/ket-qua/ui-synth-q0668-filter-fix-02-cau1-q0668.png` (94.999 bytes): Kết quả câu Q0668 tra cứu trọn vẹn trong khối LSU, hiển thị phân tích nguồn Slide 6 C7620 và Capture.PNG.
   - `docs/phieu-viec/ket-qua/ui-synth-q0668-filter-fix-03-cau2-q0718.png` (94.324 bytes): Kết quả câu Q0718 phân tích sâu 12 nguồn về DMT-PMT.
   - `docs/phieu-viec/ket-qua/ui-synth-q0668-filter-fix-04-cau3-q0709.png` (87.570 bytes): Kết quả câu Q0709 hiển thị bảng quy đổi Skew chi tiết cho 4 màu Black, Cyan, Magenta, Yellow.

---

## 4. Kết luận Mục 0

- **Mục 0.1**: Đã chốt đường chấm qua `lsu_quality_50_questions.json` và `quality_harness.py`, khớp 100% kết quả chấm lại của Muse (Lượt 1 = 67.50, Lượt 2 = 68.50, Lượt Q0668 = 74.50), đính chính bản chất câu Q0824 là điểm giả.
- **Mục 0.2**: Đã tìm ra nguyên nhân gốc rễ, áp dụng bản vá hẹp nhất (commit `51bd6d2`), bảo đảm 4 cổng repo PASS và nghiệm thu giao diện Playwright thành công tuyệt đối trên cả 3 câu.
- **Chính thức khép lại Mục 0**, đủ điều kiện an toàn chuyển sang Mục 2 (Sao lưu chỉ mục sản xuất) và Mục 3 (Chạy thử dry-run 5 tệp nguồn).
