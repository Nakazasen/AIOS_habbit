Model thực hiện: Gemini 3.1 Pro (Thinking Level: High)

# BÁO CÁO NGHIỆM THU VÉ: DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX

## 1. THÔNG TIN CHUNG
- **Mã vé:** `DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX`
- **Mục tiêu:** Xóa bỏ triệt để hiện tượng nhiễm ngôn ngữ tiếng Nhật trên tất cả các luồng soạn thảo và trả lời câu hỏi của Workspace Chat (luồng DB/bậc thang, luồng tổng hợp có căn cứ, luồng bản thảo). Khi người dùng hỏi bằng tiếng Việt, thân đáp án phải là 100% tiếng Việt tự nhiên, rõ nghĩa, không sót trường thô (`不要`), cụm từ tiếng Nhật chưa dịch hay câu nguyên văn tiếng Nhật rò rỉ.
- **Trạng thái:** HOÀN THÀNH (100% test pass, kiểm thử Playwright UI thực tế đạt chuẩn, 0 lỗi Han/Kana rò rỉ trong thân văn bản, bảo toàn toàn vẹn định danh tài liệu và mã lỗi).
- **Môi trường thực thi:** Host `H410ASROCK`, Python 3.11.14 (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`).

---

## 2. TRUY NGUYÊN GỐC RỄ & CƠ CHẾ RÒ RỈ TIẾNG NHẬT (MỤC 2.1)

Sau khi tái hiện trên giao diện thực tế và phân tích toàn bộ chuỗi sinh đáp án, chúng tôi đã xác định được 4 cơ chế chính khiến tiếng Nhật lọt vào thân câu trả lời tiếng Việt:

1. **Rò rỉ trực tiếp từ trường thô trong CSDL (`chat_action_error_lookup.py`)**:
   - Dữ liệu 30.075 ca lịch sử (`error_cases_reconciled.db`) lưu các cột nguyên bản từ tệp Excel gốc Nhật Bản: cột `AA` (nguyên nhân), cột `AB` (đối sách), cột `I` (hiện tượng), và danh mục thuật ngữ (`name_ja`).
   - Có tới **8.313 ca** trong CSDL có giá trị `AA == '不要'`. Trước đây, hàm `_case_dict` sao chép thẳng chuỗi này vào Markdown, dẫn tới dòng:
     ```markdown
     - Nguyên nhân 2: 不要
     ```
   - Tương tự, các giá trị như `原因不明（メカ）`, `部品要因(電気)`, `LCD画面にWaste Tonner Box Cover is Open 表示` bị nhúng trực tiếp vào các thẻ ca lịch sử mà không qua bước chuẩn hóa/dịch thuật ngữ cảnh.

2. **Cụm từ kỹ thuật chưa dịch trong Bảng tra cứu thuật ngữ (`glossary_table`)**:
   - Tên mã lỗi gốc và cơ chế phát sinh từ tài liệu tự chẩn đoán (như `JAM4212: 定着センサー滞留(カセット2給紙)` hay `F000: Welcome画面のまま一定時間※注経過するとCF000が表示される`) được lưu bằng tiếng Nhật.
   - Khi hiển thị mục *1. Định nghĩa kỹ thuật & Mô tả mã lỗi*, hệ thống xuất thẳng chuỗi tiếng Nhật nếu trường tiếng Việt chưa được biên tập.

3. **Hiện tượng giả lập ký tự Nhật do dấu chấm tròn Katakana (`\u30fb` - `・`)**:
   - Nhiều tài liệu hướng dẫn kỹ thuật tiếng Việt sử dụng dấu chấm giữa Katakana `・` để liệt kê đầu dòng (ví dụ: `・UNIT IH - Bản mạch IH`).
   - Các bộ lọc ký tự hoặc người dùng nhìn thấy ký tự này ngỡ là lỗi hiển thị tiếng Nhật, đồng thời gây nhiễu cho các thuật toán phát hiện ngôn ngữ.

4. **Prompt tổng hợp chưa siết chặt luật cấm rò rỉ (`i18n.py`)**:
   - Chỉ thị hệ thống trước đây cho phép LLM "trích dẫn nguyên văn" dẫn tới việc LLM giữ lại các đoạn tiếng Nhật trong tài liệu tham chiếu thay vì dịch sang tiếng Việt.

---

## 3. CHÍNH SÁCH NGÔN NGỮ ĐÃ TRIỂN KHAI (MỤC 2.2 & 2.3)

Chúng tôi đã thiết kế và triển khai module chính sách ngôn ngữ tập trung tại [`src/aios_habit/answer_language_policy.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/answer_language_policy.py) với 5 nguyên tắc bất di bất dịch:

1. **Quy tắc (a) - Khóa ngôn ngữ câu hỏi**:
   - Phát hiện ngôn ngữ câu hỏi qua `is_vietnamese_question(q)`. Nếu câu hỏi viết bằng tiếng Việt (hoặc không chứa ký tự tiếng Nhật), toàn bộ thân đáp án BẮT BUỘC phải là tiếng Việt.
   - Ngoại lệ hợp lệ: Nếu người dùng hỏi bằng tiếng Nhật hoặc yêu cầu rõ "trích nguyên văn tiếng Nhật", hệ thống tôn trọng yêu cầu của người dùng.

2. **Quy tắc (b) - Xử lý trường thô tiếng Nhật (`不要`, mảnh từ chuyên ngành)**:
   - Dịch theo ngữ cảnh kỹ thuật ngành in/máy photocopy KDTPS:
     - `不要` ở cột nguyên nhân $\rightarrow$ `"Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)"`
     - `不要` ở cột đối sách $\rightarrow$ `"Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức"`
     - `原因不明（メカ）` $\rightarrow$ `"Không rõ nguyên nhân (Cơ khí)"`
     - `部品要因(電気)` $\rightarrow$ `"Yếu tố linh kiện (Phần điện)"`
     - `LCD画面に...表示` $\rightarrow$ `"Màn hình LCD hiển thị: ..."`
     - `Iris2024 上位` $\rightarrow$ `"Iris2024 Thượng vị (Bản nâng cao)"`
     - `Iris2024 下位` $\rightarrow$ `"Iris2024 Hạ vị (Bản tiêu chuẩn)"`

3. **Quy tắc (c) - Trích nguồn tiếng Nhật có nhãn**:
   - Mọi trích dẫn tiếng Nhật thực sự cần thiết đều phải nằm trong block riêng biệt có nhãn rõ ràng: `> **Nguyên văn nguồn (tiếng Nhật):** ...` kèm bản dịch/giải thích tiếng Việt đặt ngay bên cạnh.

4. **Quy tắc (d) - Bảo toàn định danh được phép (Anti-Blind-Deletion)**:
   - Tuyệt đối không xóa mù quáng ký tự Han/Kana.
   - Định danh tài liệu (`02XC_自己診断表示一覧表-Iris2020 VN.xls`, `02XC_機能定義書_JAM一覧 (1).xls`, `UWCAシステムエラー(FXXX)概要.xls`, `FY2027上期機器製造 品質状況...xlsx`) và mã kỹ thuật/mã lỗi (`C6770`, `JAM4212`, `F000`, `302ND4637_`) được BẢO TOÀN NGUYÊN VẸN để các nút mở nguồn trích dẫn ([`Source Viewer`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_app.py)) hoạt động chính xác 100%.

5. **Quy tắc (e) - Chuẩn hóa dấu chấm giữa Katakana**:
   - Thay thế toàn bộ ký tự `・` (`\u30fb`) bằng dấu bullet chuẩn `• ` trong các danh sách liệt kê kỹ thuật.

6. **Vòng lặp cải thiện liên tục (Mục 2.4 - Luật 2026-10-03)**:
   - Mọi lần phát hiện hoặc xử lý đoạn tiếng Nhật đều tự động ghi sự kiện vào [`local_cases/answer_language_events.jsonl`](file:///D:/Sandbox/AIOS_habbit/local_cases/answer_language_events.jsonl) ghi nhận: route, detected_count, actions (`dich`, `giu-dinh-danh`), line_no, và conversation_id. Không ghi đè hay làm rò rỉ dữ liệu nhạy cảm.

---

## 4. BẢNG PHÂN LOẠI TỪNG ĐOẠN TIẾNG NHẬT ĐÃ XỬ LÝ

| STT | Chuỗi / Mảnh tiếng Nhật gốc | Vị trí xuất hiện | Phân loại | Hành động áp dụng | Kết quả hiển thị tiếng Việt sau sửa |
|---|---|---|---|---|---|
| 1 | `不要` (trong cột AA - Nguyên nhân) | Nguyên nhân ca lịch sử C6770, JAM4212, F000 | Giá trị trường thô | Dịch theo ngữ cảnh | "Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)" |
| 2 | `不要` (trong cột AB - Đối sách) | Đối sách ca lịch sử C6770, JAM4212, F000 | Giá trị trường thô | Dịch theo ngữ cảnh | "Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức" |
| 3 | `定着センサー滞留(カセット2給紙)` | Tên mã lỗi JAM4212 | Định nghĩa thuật ngữ | Dịch chuyên ngành | "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)" |
| 4 | `中間巻き付き検知センサーOFFから規定時間経過しても定着センサーをOFFしない` | Cơ chế JAM4212 | Cơ chế kỹ thuật | Dịch thuật ngữ | "Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt (OFF) nhưng cảm biến sấy vẫn chưa ngắt (OFF)" |
| 5 | `原因不明（メカ）` | Nguyên nhân JAM4212 | Giá trị trường thô | Dịch thuật ngữ | "Không rõ nguyên nhân (Cơ khí)" |
| 6 | `Welcome画面のまま一定時間※注経過するとCF000が表示される` | Mô tả mã lỗi F000 | Mô tả kỹ thuật | Dịch thuật ngữ | "Màn hình dừng ở màn hình Welcome quá thời gian quy định sẽ hiển thị mã CF000." |
| 7 | `Panel-Main基板間の通信異常` | Chi tiết hiện tượng F000 | Mô tả kỹ thuật | Dịch thuật ngữ | "Bất thường truyền thông giữa bản mạch Panel và bản mạch Main" |
| 8 | `Panel Core-Main Core間の通信異常 注2` | Chi tiết hiện tượng F000 | Mô tả kỹ thuật | Dịch thuật ngữ | "Bất thường truyền thông giữa Panel Core và Main Core (chú thích 2)" |
| 9 | `部品要因(電気)` | Nguyên nhân ca lỗi F000 | Giá trị trường thô | Dịch thuật ngữ | "Yếu tố linh kiện (Phần điện)" |
| 10 | `要因不明(電気)` | Nguyên nhân ca lỗi F000 | Giá trị trường thô | Dịch thuật ngữ | "Không rõ nguyên nhân (Phần điện)" |
| 11 | `1Panel⇔Main基板間、※(Main基板⇔HDD間)のハーネス、コネクタの接続状態を確認し、動作確認を行う。` | Biện pháp xử lý 1 của F000 | Biện pháp chuẩn đoán | Dịch hoàn chỉnh | "1. Kiểm tra trạng thái kết nối của dây cáp (harness), connector giữa bản mạch Panel ⇔ Main, (giữa Main ⇔ HDD) và chạy thử kiểm tra hoạt động." |
| 12 | `2DDRメモリの接触を確認(抜き出し)し、動作確認を行う。交換可能であれば、交換し、動作確認を行う。` | Biện pháp xử lý 2 của F000 | Biện pháp chuẩn đoán | Dịch hoàn chỉnh | "2. Kiểm tra tiếp xúc của bộ nhớ DDR (rút ra cắm lại) và kiểm tra hoạt động. Nếu có linh kiện thay thế, hãy thay và chạy thử." |
| 13 | `3HDDの初期化をし、動作確認を行う。(U024のFULL)` | Biện pháp xử lý 3 của F000 | Biện pháp chuẩn đoán | Dịch hoàn chỉnh | "3. Khởi tạo (format) ổ cứng HDD và kiểm tra hoạt động (chạy U024 FULL)." |
| 14 | `4U021 コントローラバックアップ初期化をし、動作確認を行う。` | Biện pháp xử lý 4 của F000 | Biện pháp chuẩn đoán | Dịch hoàn chỉnh | "4. Khởi tạo sao lưu bộ điều khiển U021 và kiểm tra hoạt động." |
| 15 | `5Main基板を交換し、動作確認を行う。` | Biện pháp xử lý 5 của F000 | Biện pháp chuẩn đoán | Dịch hoàn chỉnh | "5. Thay thế bản mạch Main và kiểm tra hoạt động." |
| 16 | `6PanelMain基板を交換し、動作確認を行う。` | Biện pháp xử lý 6 của F000 | Biện pháp chuẩn đoán | Dịch hoàn chỉnh | "6. Thay thế bản mạch Panel Main và kiểm tra hoạt động." |
| 17 | `LCD画面にWaste Tonner Box Cover is Open 表示` | Hiện tượng ca lỗi C6770 | Giá trị trường thô | Dịch nhãn | "Màn hình LCD hiển thị: Waste Tonner Box Cover is Open" |
| 18 | `PC画面 100000. DINQ 0133. c3v表示` | Hiện tượng ca lỗi C6770 | Giá trị trường thô | Dịch nhãn | "Màn hình PC hiển thị 100000. DINQ 0133. c3v" |
| 19 | `Check Black , Check Color 画像 異常` | Hiện tượng ca lỗi C6770 | Giá trị trường thô | Dịch nhãn | "Check Black , Check Color bất thường hình ảnh" |
| 20 | `COVER MAGのボス 折れ` | Hiện tượng ca lỗi C6770 | Giá trị trường thô | Dịch nhãn | "COVER MAG gãy vấu (boss)" |
| 21 | `LCD画面が暗く表示し、30秒にフリーズになった後、F000表示` | Hiện tượng ca lỗi F000 | Giá trị trường thô | Dịch nhãn | "Màn hình LCD hiển thị tối, sau khi bị đóng băng (treo) 30 giây thì hiển thị F000" |
| 22 | `LCD画面が白く表示し、ロックされた` | Hiện tượng ca lỗi F000 | Giá trị trường thô | Dịch nhãn | "Màn hình LCD hiển thị trắng xóa và bị khóa" |
| 23 | `LCD画面がF000表示` / `LCD画面にF000表示` | Hiện tượng ca lỗi F000 | Giá trị trường thô | Dịch nhãn | "Màn hình LCD hiển thị F000" |
| 24 | `Iris2024 上位` / `Iris2024 下位` | Dòng máy KDTPS | Phân loại máy | Dịch chuẩn hóa | "Iris2024 Thượng vị (Bản nâng cao)" / "Iris2024 Hạ vị (Bản tiêu chuẩn)" |
| 25 | `・` (Katakana middle dot `\u30fb`) | Dấu gạch đầu dòng kỹ thuật | Ký tự điều khiển | Chuẩn hóa | `• ` (bullet point) |
| 26 | `02XC_自己診断表示一覧表-Iris2020 VN.xls` | Tài liệu tham chiếu | Tên tệp tài liệu | Giữ định danh | Giữ nguyên vẹn để liên kết mở file |
| 27 | `02XC_機能定義書_JAM一覧 (1).xls` | Tài liệu tham chiếu | Tên tệp tài liệu | Giữ định danh | Giữ nguyên vẹn để liên kết mở file |
| 28 | `UWCAシステムエラー(FXXX)概要.xls` | Tài liệu tham chiếu | Tên tệp tài liệu | Giữ định danh | Giữ nguyên vẹn để liên kết mở file |
| 29 | `FY2027上期機器製造 品質状況...xlsx` | Báo cáo gốc | Tên tệp tài liệu | Giữ định danh | Giữ nguyên vẹn để liên kết mở file |
| 30 | `old/2022年機器製造 品質状況...xlsx` | Báo cáo gốc | Tên tệp tài liệu | Giữ định danh | Giữ nguyên vẹn để liên kết mở file |

---

## 5. ĐỐI CHIẾU NGUYÊN VĂN ĐÁP ÁN TRƯỚC VÀ SAU SỬA (VERBATIM EVIDENCE)

### 5.1. Câu hỏi 1: C6770 ("Mã lỗi C6770 nguyên nhân là gì?")

#### TRƯỚC SỬA (Lỗi rò rỉ: dòng "Nguyên nhân 2: 不要", tên máy Iris2024 上位/下位, hiện tượng tiếng Nhật):
````markdown
Dựa trên cơ sở dữ liệu **30.075 ca điều tra lịch sử KDTPS** và danh mục mã lỗi chuẩn. dưới đây là thông tin điều tra và xử lý cho mã lỗi **C6770**:

### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `C6770`
- **Tên mã lỗi / Hiện tượng:** Lỗi  nguồn điện thấp Fuser IH
- **Phân loại hệ thống:** C_CALL
- **Cơ chế phát sinh:** Sau khi bắt đầu gia nhiệt Fuser, giá trị đọc của công suất ở trạng thái dưới 0.3x giá trị công suất thiết lập liên tục 4 lần, dù thực hiện lại 3 lần vẫn dưới  giá trị công suất thiết lập ×0.3
- **Tài liệu tham chiếu:** 02XC_自己診断表示一覧表-Iris2020 VN.xls

### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế
- **Nguyên nhân 1:** Sau khi bắt đầu gia nhiệt Fuser, giá trị đọc của công suất ở trạng thái dưới 0.3x giá trị công suất thiết lập liên tục 4 lần, dù thực hiện lại 3 lần vẫn dưới  giá trị công suất thiết lập ×0.3
- **Nguyên nhân 2:** 不要

### 3. Đối sách và biện pháp xử lý theo báo cáo điều tra
- **Biện pháp 1:** VI 1. Xác nhận kết nối — NN: Connector không được kết nối chính xác... <br>・UNIT IH - Bản mạch IH <br>・Bản mạch IH - Bản mạch Engine...
...
### 4. Danh sách các ca điều tra thực tế đối chiếu (DB 30.075 ca)
**1. Phiếu 2026/1143** (Iris2024 上位 / C33)
- **Nguyên nhân:** 不要
- **Đối sách:** 不要
**2. Phiếu 2025/3179** (Iris2024 下位 / C35)
- **Hiện tượng:** LCD画面にWaste Tonner Box Cover is Open 表示
- **Nguyên nhân:** 不要
````

#### SAU SỬA (100% tiếng Việt thuần túy, 0 chữ `不要`, chỉ giữ định danh tệp tham chiếu hợp lệ):
````markdown
Dựa trên cơ sở dữ liệu **30.075 ca điều tra lịch sử KDTPS** và danh mục mã lỗi chuẩn. dưới đây là thông tin điều tra và xử lý cho mã lỗi **C6770**:

### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `C6770`
- **Tên mã lỗi / Hiện tượng:** Lỗi  nguồn điện thấp Fuser IH
- **Phân loại hệ thống:** C_CALL
- **Cơ chế phát sinh:** Sau khi bắt đầu gia nhiệt Fuser, giá trị đọc của công suất ở trạng thái dưới 0.3x giá trị công suất thiết lập liên tục 4 lần, dù thực hiện lại 3 lần vẫn dưới  giá trị công suất thiết lập ×0.3
- **Tài liệu tham chiếu:** 02XC_自己診断表示一覧表-Iris2020 VN.xls

### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế
- **Nguyên nhân 1:** Sau khi bắt đầu gia nhiệt Fuser, giá trị đọc của công suất ở trạng thái dưới 0.3x giá trị công suất thiết lập liên tục 4 lần, dù thực hiện lại 3 lần vẫn dưới  giá trị công suất thiết lập ×0.3
- **Nguyên nhân 2:** Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)

### 3. Đối sách và biện pháp xử lý theo báo cáo điều tra
- **Biện pháp 1:** VI 1. Xác nhận kết nối — NN: Connector không được kết nối chính xác. Hoặc có bất thường ở dây điện. → XL: Vệ sinh đầu kết nối connector rồi cắm lại. Trường hợp không thông mạch yêu cầu thay thế dây điện. <br>• UNIT IH - Bản mạch IH <br>• Bản mạch IH - Bản mạch Engine <br>• Bản mạch IMAGE DRIVE - Bản mạch Engine
...
### 4. Danh sách các ca điều tra thực tế đối chiếu (DB 30.075 ca)
Tìm thấy **5** ca điều tra thực tế liên quan trực tiếp đến mã lỗi **C6770**:

**1. Phiếu 2026/1143** (Iris2024 Thượng vị (Bản nâng cao) / C33)
- **Máy:** Iris2024 Thượng vị (Bản nâng cao) | **Serial:** 110C2K3NLV 1Y86605676 | **Ngày phát sinh:** 2026-06-22
- **Hiện tượng:** C6770
- **Nguyên nhân:** Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)
- **Đối sách:** Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 14432`

**2. Phiếu 2025/3179** (Iris2024 Hạ vị (Bản tiêu chuẩn) / C35)
- **Máy:** Iris2024 Hạ vị (Bản tiêu chuẩn) | **Serial:** 1102YP3NLV H565Y61327 | **Ngày phát sinh:** 2025-11-28
- **Hiện tượng:** Màn hình LCD hiển thị: Waste Tonner Box Cover is Open
- **Nguyên nhân:** Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)
- **Đối sách:** Đánh giá: Không lưu hànhLeader cho NTT xem hiện trạng lỗi. Hướng dẫn lại NTT khi lắp ráp linh kiện phải lắp ráp hoàn chỉnh.Bổ sung thêm thao tác kiểm tra công đoạn lắp cụm assy case Weight sensor WTB trước khi lắp vào hộp mực thải.
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 11633`
````

---

### 5.2. Câu hỏi 2: JAM4212 ("Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?")

#### TRƯỚC SỬA (Lỗi rò rỉ: Tên tiếng Nhật `定着センサー滞留`, cơ chế tiếng Nhật, `原因不明（メカ）`):
````markdown
### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `JAM4212`
- **Tên mã lỗi / Hiện tượng:** 定着センサー滞留(カセット2給紙)
- **Phân loại hệ thống:** JAM
- **Cơ chế phát sinh:** 中間巻き付き検知センサーOFFから規定時間経過しても定着センサーをOFFしない
- **Tài liệu tham chiếu:** 02XC_機能定義書_JAM一覧 (1).xls

### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế
- **Nguyên nhân 1:** 中間巻き付き検知センサーOFFから規定時間経過しても定着センサーをOFFしない
- **Nguyên nhân 2:** 不要
- **Nguyên nhân 3:** 原因不明（メカ）
````

#### SAU SỬA (100% tiếng Việt, giải thích tường minh cơ chế kỹ thuật):
````markdown
### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `JAM4212`
- **Tên mã lỗi / Hiện tượng:** Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)
- **Phân loại hệ thống:** JAM
- **Cơ chế phát sinh:** Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt (OFF) nhưng cảm biến sấy vẫn chưa ngắt (OFF)
- **Tài liệu tham chiếu:** 02XC_機能定義書_JAM一覧 (1).xls

### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế
- **Nguyên nhân 1:** Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt (OFF) nhưng cảm biến sấy vẫn chưa ngắt (OFF)
- **Nguyên nhân 2:** Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)
- **Nguyên nhân 3:** Không rõ nguyên nhân (Cơ khí)

### 3. Đối sách và biện pháp xử lý theo báo cáo điều tra
- **Biện pháp 1:** => Xử lý lỗi trong gia công.
- **Biện pháp 2:** Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức
- **Biện pháp 3:** => Máy lỗi sẽ xử lý không tái hiện, cho máy đi. Thông tin cho chế tạo và QC giảm thời gian tái sử dụng giấy từ 2h xuống 1h và tiếp tục theo dõi sản xuất trên line.
````

---

### 5.3. Câu hỏi 3: F000 ("Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?")

#### TRƯỚC SỬA (Lỗi rò rỉ: 6 biện pháp kỹ thuật bằng tiếng Nhật JA, hiện tượng Welcome màn hình):
````markdown
### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `F000`
- **Tên mã lỗi / Hiện tượng:** Welcome画面のまま一定時間※注経過するとCF000が表示される。

Panel-Main基板間の通信異常
Panel Core-Main Core間の通信異常 注2
- **Phân loại hệ thống:** F_SYSTEM
- **Tài liệu tham chiếu:** UWCAシステムエラー(FXXX)概要.xls

### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế
- **Nguyên nhân 1:** 電気技術に連携 đang điều tra...
- **Nguyên nhân 2:** 部品要因(電気)
- **Nguyên nhân 3:** 要因不明(電気)

### 3. Đối sách và biện pháp xử lý theo báo cáo điều tra
- **Biện pháp 1:** JA: 1Panel⇔Main基板間、※(Main基板⇔HDD間)のハーネス、コネクタの接続状態を確認し、動作確認を行う。
- **Biện pháp 2:** 2DDRメモリの接触を確認(抜き出し)し、動作確認を行う。交換可能であれば、交換し、動作確認を行う。
- **Biện pháp 3:** 3HDDの初期化をし、動作確認を行う。(U024のFULL)  ※
- **Biện pháp 4:** 4U021 コントローラバックアップ初期化をし、動作確認を行う。
- **Biện pháp 5:** 5Main基板を交換し、動作確認を行う。
- **Biện pháp 6:** 6PanelMain基板を交換し、動作確認を行う。
````

#### SAU SỬA (Toàn bộ 6 biện pháp kỹ thuật được dịch sang tiếng Việt chuẩn xác):
````markdown
### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `F000`
- **Tên mã lỗi / Hiện tượng:** Màn hình dừng ở màn hình Welcome quá thời gian quy định sẽ hiển thị mã CF000.

Bất thường truyền thông giữa bản mạch Panel và bản mạch Main
Bất thường truyền thông giữa Panel Core và Main Core (chú thích 2)
- **Phân loại hệ thống:** F_SYSTEM
- **Tài liệu tham chiếu:** UWCAシステムエラー(FXXX)概要.xls

### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế
- **Nguyên nhân 1:** Phối hợp với bộ phận kỹ thuật điện đang điều trakiểm tra cổng network không bất thường. Gửi bản mạch sang EMS check lại I/F OK-> phán đoán lỗi linh kiện U1 (hayabusha) ->yêu cầu thay linh kiện U1 sau đó check lại bằng máy thực nghiệm OK-> xử lý lỗi phát sinh đơn phát. Xác nhận cổ…
- **Nguyên nhân 2:** Yếu tố linh kiện (Phần điện)
- **Nguyên nhân 3:** Không rõ nguyên nhân (Phần điện)

### 3. Đối sách và biện pháp xử lý theo báo cáo điều tra
- **Biện pháp 1:** 1. Kiểm tra trạng thái kết nối của dây cáp (harness), connector giữa bản mạch Panel ⇔ Main, (giữa Main ⇔ HDD) và chạy thử kiểm tra hoạt động.
- **Biện pháp 2:** 2. Kiểm tra tiếp xúc của bộ nhớ DDR (rút ra cắm lại) và kiểm tra hoạt động. Nếu có linh kiện thay thế, hãy thay và chạy thử.
- **Biện pháp 3:** 3. Khởi tạo (format) ổ cứng HDD và kiểm tra hoạt động (chạy U024 FULL).
- **Biện pháp 4:** 4. Khởi tạo sao lưu bộ điều khiển U021 và kiểm tra hoạt động.
- **Biện pháp 5:** 5. Thay thế bản mạch Main và kiểm tra hoạt động.
- **Biện pháp 6:** 6. Thay thế bản mạch Panel Main và kiểm tra hoạt động.
````

---

## 6. DANH MỤC ẢNH MINH CHỨNG GIAO DIỆN THỰC TẾ & BẢNG CHECKSUM

Toàn bộ ảnh chụp giao diện được tự động thu thập thông qua Playwright headless browser chạy trên ứng dụng Streamlit thực tế (cổng tạm thời), căn chỉnh khung trọn vẹn toàn bộ thẻ đáp án (từ tiêu đề, định nghĩa, nguyên nhân, đối sách đến danh sách ca thực tế đối chiếu).

| STT | Tên tệp ảnh | Dung lượng | SHA-256 Checksum | Mô tả cảnh chụp nghiệm thu |
|---|---|---|---|---|
| 1 | `anh-language-purity-01-c6770.png` | 191.723 bytes | `9C2D2B1845708A7E371C82B654EBDB44E0F178FC0AC7A409D82A8DE33595B943` | C6770: Thân đáp án thuần Việt, `不要` đã được chuyển thành đối sách xử lý tại chỗ, bảo toàn nút trích dẫn `02XC_自己診断表示一覧表-Iris2020 VN.xls`. |
| 2 | `anh-language-purity-02-jam4212.png` | 184.551 bytes | `B252323625BF50BE9DF89FB74AB681C5AC74E073E8186D7B1B55A9F36F2A5C95` | JAM4212: Định nghĩa "Kẹt giấy tại cảm biến sấy", cơ chế cuốn giấy trung gian, nguyên nhân thuần Việt, nút mở tài liệu `02XC_機能定義書_JAM一覧 (1).xls` hoạt động. |
| 3 | `anh-language-purity-03-f000.png` | 181.508 bytes | `B5544091389D5A95A4093C5200F00F4597969A974A59C50F8463B450F8EE4609` | F000: Bất thường truyền thông Panel-Main, 6 biện pháp kỹ thuật thuần Việt, bảo toàn định danh tài liệu `UWCAシステムエラー(FXXX)概要.xls`. |

Tất cả các tệp trên đã được đồng bộ song song tại 2 thư mục:
- `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\`
- `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`

---

## 7. BẢO TOÀN NỘI DUNG VÀ KHÔNG HỒI QUY (REGRESSION CHECKS)

1. **Bảo toàn số lượng ý/nội dung (Mục 4)**:
   - Số ý nguyên nhân trước sửa: C6770 (2 ý), JAM4212 (3 ý), F000 (3 ý).
   - Số ý nguyên nhân sau sửa: C6770 (2 ý), JAM4212 (3 ý), F000 (3 ý). **Không giảm bất kỳ ý nào.**
   - Số biện pháp xử lý sau sửa: C6770 (6 biện pháp), JAM4212 (3 biện pháp), F000 (6 biện pháp). **Đầy đủ 100%.**
2. **Nút mở nguồn trích dẫn (`Source Viewer`)**:
   - Vẫn giữ nguyên vẹn tên tài liệu gốc trong mã Markdown (`02XC_自己診断表示一覧表-Iris2020 VN.xls`, `02XC_機能定義書_JAM一覧 (1).xls`, `UWCAシステムエラー(FXXX)概要.xls`), nút mở nguồn hoạt động hoàn hảo và liên kết chính xác sang tài liệu gốc.
3. **Hiệu ứng chữ chạy dần (`Streaming`)**:
   - Vòng lặp streaming trong `workspace_chat_app.py` hoạt động bình thường, các marker truyền thông tin liên tục.
4. **Bộ kiểm thử tự động**:
   - `tests/test_answer_language_purity.py`: 8/8 tests PASSED (100%).
   - `tests/test_chat_action_error_lookup.py`: 9 passed, 9 skipped (không có lỗi hồi quy).

---

## 8. KẾT LUẬN & NGHIỆM THU

Hệ thống đáp ứng đầy đủ và vượt mức tất cả các tiêu chí nghiệm thu của vé `DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX`. Người dùng khi hỏi bằng tiếng Việt trên giao diện desktop sẽ nhận được câu trả lời 100% tiếng Việt tự nhiên, mạch lạc, chính xác về mặt kỹ thuật, không còn bất kỳ mảnh tiếng Nhật thô hay chuỗi `不要` nào rò rỉ.

```json
{
  "ma_ve": "DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-22T06:05:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
