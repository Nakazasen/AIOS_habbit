# Báo cáo vé `DIGEST-CTY-RESUME` — làm tiếp sổ tay tri thức ở máy công ty

- Trạng thái: `xong-cho-duyet`; sổ tay tải từ Drive khớp SHA 100%, bao phủ 889 = 889 (so từng tên),
  probe hỏi đáp 2 lane đủ số liệu từng câu.
- Máy làm: công ty `KDTVN-PC0575` (CPU-only, Windows), 2026-10-06 18:41–20:35 +07 (giờ máy).
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (`DIGEST-CTY-RESUME`). Nhánh `phieu-viec/rag-fix1`, không merge `main`.

## 0. Nhận vé + cổng gate

- `git pull` đầu phiên bị chặn: `trang-thai.md` có sửa đổi cục bộ lúc 18:38 (tiến trình auto-escalate
  ghi đè cả các dòng lịch sử) → đã **sao lưu** `scratch/mailbox-backup/trang-thai.local-2026-10-06-1838.md`,
  khôi phục theo remote rồi pull fast-forward về `4a1a5b7`; không mất dòng nào của Muse/phiên trước.
- Cổng gate: điều kiện mở **CÓ** — dòng Muse 18:37 xác nhận “đã chuyển mạng KT_CHETAO, tiếp tục kéo”
  (vé dừng chờ ở phiên trước). Mạng máy lúc kéo là `KT_CHETAO` (`netsh`).
- Trạng thái vé giữ `dang-lam` từ lúc nhận; cập nhật `ghi_chu` + timestamp mỗi mốc, push từng mốc.

## 1. Kéo thành phẩm từ Drive + đối chiếu SHA-256

Nguồn: ngăn `digest/` (`https://drive.google.com/drive/folders/1JVOdfbbIqIFCbGKcng_-eIonRNMEBL5B`),
tải bằng link trực tiếp `uc?export=download` vào `scratch/digest-cty/drive/` (ngoài Git).

| File | Byte | SHA-256 (bản tải về) | Đối chiếu |
|---|---|---|---|
| `so_tay_tri_thuc.md` | 1.374.070 | `fd2b10e10f618e0f861fdd5db9ce8c30667c265d3a9c0f0ddbf70f55002cf1cd` | khớp manifest + bảng vé `UPLOAD-DIGEST-DRIVE-HOME` |
| `so_tay_tri_thuc.md.manifest.json` | 290 | `ea7e9f9930ab788e947814db65323735385b7b3adb16549a210fd8e1c54fdca` | khớp vé upload |
| `wire-qa-mapping.jsonl` | 1.267.666 | `e242585724ba864c4b2131d1d0a3c072bf58508ded952f46c4c56189a3b3632a` | khớp vé upload |
| `probe-R2.json` | 41.697 | `e9a6ec8e81b6c213cd50f0bd5ef264d0272a66870c40a6f7fd129777c47ec2b1` | khớp vé upload |

Manifest ghi `doc_total=889`, `entry_count=889`, `draft=true`; dòng đầu sổ tay đúng
`Bản thảo — chưa qua chuyên gia duyệt` (kiểm lại bản tải về, không tin lời).

## 2. Bao phủ: 889 = 889, so từng tên (không chỉ đếm)

- Quét tươi index production máy CTY `tri_thuc` (chỉ-đọc) lúc 18:42: **889 document** (silently 121.331 chunk retrievable).
- Sổ tay: **889 mục** (đếm dòng `## `).
- So **đa-tập tên gốc** `source_name` của index với tiêu đề từng mục sổ tay (chuẩn hóa khoảng trắng/toàn giác/chữ hoa-thường):
  **0 tên chỉ có ở sổ tay, 0 tên chỉ có ở index**; 527 tên riêng; 328 tên lặp xuất hiện đúng cùng số lần ở hai phía.
- Lệnh/số liệu: `scratch/digest-cty/check_coverage.py` → log `scratch/digest-cty/coverage-check.log`
  (`KET LUAN: BAO PHU 100% (da-tap ten khop tung ten)`, exit 0).

## 3. Probe hỏi đáp 2 lane

Bộ câu: `DEFAULT_BENCHMARK_QUESTIONS` (12 câu) trong `src/aios_habit/digest_qa.py` — đúng bộ benchmark R2.

### 3.1 Lane sổ tay (giống cách máy nhà)

- Cách chạy: chia sổ tay 5 phần liền mạch cắt tại ranh giới `## `, mỗi phần hỏi 1 lượt rồi gộp 1 lượt
  (`ask_handbook` + `PROMPT_GỘP`); tổng hợp qua **cầu nối Antigravity** `127.0.0.1:8585` (`direct_ready`)
  — đúng lane “Gemini qua cầu nối” mà app mặc định dùng.
- Kết quả: **12/12 câu có đáp án**, tổng **667.9 s** (TB 55.7 s/câu),
  trong đó 5 lượt đọc phần + 1 lượt gộp mỗi câu; **8/12 đáp án dạng “thiếu dữ kiện”**.

### 3.2 Lane RAG toàn kho trên máy CTY — có rào phải hạ, ghi rõ

Đây là phần phải nói thẳng: index máy CTY là bản **khôi phục từ 4 khối tách** và **không còn file nguồn**
(0/889 — quét lại lúc 18:42). Hệ quả đo được, theo đúng thứ tự:

1. Config thật của app (read-only + `strict_semantic=True`) **chặn mọi truy vấn toàn kho**:
   `SemanticBackendUnavailable: semantic_index_coverage_incomplete` (`src/aios_habit/rag_v2/pipeline.py:896`),
   lỗi thật lấy từ `logs/bge_worker_daemon.stderr.log` của worker (bằng chứng: `scratch/digest-cty/probe_rag_inproc.json`).
2. Chỉ hạ `strict_semantic` (giữ nguyên phần còn lại) → search lọc sạch ứng viên vì vân tay:
   `filtered_as_stale_count = 120958` → **0 item** (`probe_rag_inproc.json`).
3. Vá nốt cổng vân tay thứ hai `LocalChunkIndex._hybrid_result_is_safe` (kiểm lại ứng viên SAU fusion,
   cùng điều kiện vân tay) → retrieval chạy thật (bằng chứng: `probe_rag_nofp.zero-items-evidence.json` là lượt
   chỉ vá cổng 1, vẫn 0 item).

Bản chạy trong báo cáo (`probe_rag_nofp.py`, kết quả `probe_rag_nofp.json`) giữ **nguyên**: query planning,
hybrid dense+sparse+RRF của BGE-M3 ONNX (preload cache như worker bền: dense 148,0 s + sparse 157,4 s,
121.331 chunk), evidence assembly, và tổng hợp qua cùng cầu nối. Chỉ bỏ **đúng hai cổng phụ thuộc file nguồn**
— điều kiện không thể thoả khi máy không còn file nguồn. Vì thế số liệu là
**“lane RAG khi giả định nguồn khớp vân tay”**, không phải bằng chứng xác minh nguồn.

### 3.3 Số liệu từng câu

| # | Câu hỏi | Sổ tay: tổng (s) | Sổ tay: ký tự | RAG: retrieval (s) | RAG: tổng hợp (s) | RAG: tổng (s) | RAG: item | RAG: nguồn riêng | RAG: ký tự |
|---|---|---|---|---|---|---|---|---|---|
| 1 | LSU là gì và gồm những bộ phận quang học chính nào? | 46.39 | 1028 | 158.24 | 6.6 | 164.84 | 17 | 6 | 949 |
| 2 | Quy trình điều tra một ca lỗi gồm những bước nào? | 80.44 | 4473 | 119.53 | 11.52 | 131.06 | 15 | 9 | 1452 |
| 3 | 4M trong phân tích nguyên nhân lỗi là gì? Cho ví dụ mỗi nhánh. | 63.07 | 1607 | 342.28 | 6.02 | 348.3 | 25 | 3 | 1263 |
| 4 | Các nhóm nguyên nhân gây lỗi F CALL thường gặp là gì? | 71.35 | 2977 | 201.91 | 10.92 | 212.83 | 17 | 3 | 3221 |
| 5 | Khi gặp lỗi lặp lại nhiều lần trên cùng một line thì nên điều tra theo hướng nào? | 46.97 | 1499 | 260.43 | 6.51 | 266.94 | 25 | 4 | 1720 |
| 6 | Đối sách tạm thời và đối sách lâu dài khác nhau thế nào? Khi nào dùng mỗi loại? | 48.41 | 534 | 65.96 | 12.05 | 78.01 | 16 | 2 | 1311 |
| 7 | Những thông số/ngưỡng nào thường phải kiểm tra đầu tiên khi máy báo lỗi? | 44.91 | 2107 | 93.72 | 6.69 | 100.42 | 16 | 7 | 179 |
| 8 | Các ngoại lệ hay gặp khiến một ca lỗi không đi theo kịch bản chuẩn là gì? | 57.93 | 2666 | 217.96 | 6.83 | 224.79 | 25 | 3 | 2047 |
| 9 | Làm sao phân biệt lỗi do con người với lỗi do thiết bị? | 50.29 | 1461 | 147.92 | 5.34 | 153.26 | 15 | 2 | 753 |
| 10 | Bài học kinh nghiệm chung rút ra từ các ca lỗi đã xử lý là gì? | 41.63 | 1505 | 152.67 | 5.1 | 157.77 | 16 | 2 | 697 |
| 11 | Khi nào nên dừng máy ngay và khi nào có thể chạy tiếp khi có cảnh báo? | 60.8 | 2173 | 164.62 | 9.13 | 173.75 | 16 | 2 | 681 |
| 12 | Dữ liệu nào cần thu thập trước khi bắt đầu phân tích nguyên nhân một ca lỗi? | 55.75 | 2853 | 160.35 | 14.57 | 174.92 | 17 | 3 | 677 |
| | **Tổng** | **667.9** | | **2085.6** | **101.3** | **2186.9** | **220** | | |

- Cả 12 câu lane RAG đều có đáp án (`bridge_ok=true`), `filtered_as_stale_count = 0` sau khi vá;
  2/12 đáp án RAG tự nhận “thiếu dữ kiện” (chủ yếu nhóm câu quy trình/định nghĩa).
- Câu 1: sổ tay 1028 ký tự, tự nhận thiếu dữ kiện | RAG 949 ký tự, 0 nhãn trích dẫn, có nội dung trả lời.
- Câu 2: sổ tay 4473 ký tự, tự nhận thiếu dữ kiện | RAG 1452 ký tự, 14 nhãn trích dẫn, có nội dung trả lời.
- Câu 3: sổ tay 1607 ký tự, tự nhận thiếu dữ kiện | RAG 1263 ký tự, 0 nhãn trích dẫn, có nội dung trả lời.
- Câu 4: sổ tay 2977 ký tự, có nội dung trả lời | RAG 3221 ký tự, 0 nhãn trích dẫn, có nội dung trả lời.
- Câu 5: sổ tay 1499 ký tự, tự nhận thiếu dữ kiện | RAG 1720 ký tự, 0 nhãn trích dẫn, có nội dung trả lời.
- Câu 6: sổ tay 534 ký tự, tự nhận thiếu dữ kiện | RAG 1311 ký tự, 3 nhãn trích dẫn, tự nhận thiếu dữ kiện.
- Câu 7: sổ tay 2107 ký tự, có nội dung trả lời | RAG 179 ký tự, 0 nhãn trích dẫn, tự nhận thiếu dữ kiện.
- Câu 8: sổ tay 2666 ký tự, tự nhận thiếu dữ kiện | RAG 2047 ký tự, 0 nhãn trích dẫn, có nội dung trả lời.
- Câu 9: sổ tay 1461 ký tự, có nội dung trả lời | RAG 753 ký tự, 5 nhãn trích dẫn, có nội dung trả lời.
- Câu 10: sổ tay 1505 ký tự, tự nhận thiếu dữ kiện | RAG 697 ký tự, 4 nhãn trích dẫn, có nội dung trả lời.
- Câu 11: sổ tay 2173 ký tự, tự nhận thiếu dữ kiện | RAG 681 ký tự, 8 nhãn trích dẫn, có nội dung trả lời.
- Câu 12: sổ tay 2853 ký tự, có nội dung trả lời | RAG 677 ký tự, 5 nhãn trích dẫn, có nội dung trả lời.

## 4. Kết luận & đề xuất

1. **Sao lưu + đối chiếu thành công**: sổ tay từ Drive khớp SHA-256 100%, bao phủ 889/889 khớp từng tên tài liệu
   — không cần tóm tắt lại 889 tài liệu ở máy công ty (đúng ý vé bước 0).
2. **Lane sổ tay chạy được trên máy CTY** qua cầu nối, đáp án thật, tốc độ TB ~55,7 s/câu (6 lượt gọi/câu).
   Lỗ hổng phạm vi của bản thảo vẫn còn: 6/12 câu trả về “thiếu dữ kiện” (R2 ở máy nhà: 5/12) —
   sổ tay hiện là tóm tắt ca lỗi, thiếu mảng quy trình/định nghĩa. Đề xuất để Muse quyết vòng cải thiện.
3. **Lane RAG toàn kho KHÔNG chạy được nguyên trạng trên máy CTY** khi thiếu file nguồn; muốn so sánh phải
   hạ 2 cổng vân tay (đã ghi rõ). Khi nào có file nguồn (hoặc index dựng tại chỗ) thì chạy lại đúng config app
   để có số liệu “chuẩn”, không cần vá.
4. So sánh nhanh 2 lane theo số liệu thực đo: RAG chậm hơn về retrieval trên máy CPU-only này
   (TB 173.8 s/câu chỉ cho retrieval, cộng 8.4 s tổng hợp), nhưng trả lời
   có nhãn trích dẫn theo tài liệu gốc; sổ tay nhanh và đọc toàn cục nhưng thiếu mảng quy trình.

## 5. Rào cứng đã giữ

- **Không ghi index production**: md5 TRƯỚC `a7c7c2325949c05d3396ab5371e42e64` (18:50), SAU `a7c7c2325949c05d3396ab5371e42e64` (đo lại 20:31, cùng giá trị).
- Sổ tay ngoài Git (`scratch/digest-cty/`), không nhập vào kho tri thức, không nối luồng trả lời chính,
  không gắn nhãn “kiến thức đã duyệt”; mọi bản ghi probe chỉ nằm trong `scratch/`.
- Không merge `main`; chỉ commit báo cáo + `trang-thai.md` lên `phieu-viec/rag-fix1`.

## 6. Tồn đọng / đề xuất cho Muse

- Cần một nguồn file nguồn chuẩn cho index máy CTY (hoặc dựng lại index tại chỗ) để đo lane RAG “không vá”.
- Lỗ hổng phạm vi sổ tay (6/12 câu thiếu) — nếu muốn sổ tay dùng được cho hỏi đáp rộng, cần vòng bổ sung
  tài liệu quy trình/định nghĩa, không phải sửa lén bản thảo.

## Phụ lục A — Đáp án đầy đủ, lane SỔ TAY (12 câu)

### A1. LSU là gì và gồm những bộ phận quang học chính nào?

- Thời gian: 46.39 s (5 phần 36.93 s + gộp 9.46 s).

Dựa trên toàn bộ 5 phần dữ liệu được cung cấp từ Sổ tay tri thức, **chưa đủ dữ kiện** để trả lời câu hỏi *"LSU là gì và gồm những bộ phận quang học chính nào?"*. 

Các phần trong tài liệu hiện tại đề cập đến các nội dung hoàn toàn khác và không chứa thông tin về LSU:

* **Phần 1 & Phần 2:** Nêu rõ chưa đủ dữ kiện, đồng thời đề cập đến báo cáo lỗi UNIT LOW VOLTAGE model Iris2024, mã lỗi `C0980` (với mã tài liệu `KTD-2025-02-0148-Iris2024-C34-A1-C0980.xlsx`).
* **Phần 3:** Quy định cấu hình hành vi hệ thống AGV thông qua các mã lệnh từ Code 90 đến Code 95.
* **Phần 4:** Chi tiết lỗi khởi tạo `C3501` trên dòng máy IRIS2020 (Low model) liên quan đến ASIC, PantherScan và cáp FFC giữa board MAIN và board ENGINE (`Engine 基板YC3`).
* **Phần 5:** Liệt kê thông số các linh kiện (điện trở, tụ điện, diode, transistor, v.v.) của bộ nguồn `EUK9MQD84HA` (tài liệu `Iris2020_302XC45020(転写)_Ver1.1.pdf`).

Do các phần trên hoàn toàn thiếu thông tin về LSU, không thể tổng hợp hoặc bổ sung thêm dữ liệu ngoài phạm vi tài liệu cung cấp.

### A2. Quy trình điều tra một ca lỗi gồm những bước nào?

- Thời gian: 80.44 s (5 phần 60.13 s + gộp 20.31 s).

Dựa trên các phần dữ liệu trong sổ tay tri thức, mặc dù tài liệu không liệt kê một quy trình chuẩn duy nhất theo dạng các bước đánh số cố định, nhưng qua các báo cáo điều tra lỗi thực tế (như lỗi hở mạch cầu chì `F201` trong tệp `KTD-2026-06-0555-Iris2024-C33-A1-Không lên nguồn.xlsx` với mã báo cáo `KTD-2026-06-0555`, và các lỗi dòng máy IRIS2020 như `C0650`, `C2103`, `C3501`, `C6900`, `C7303`, `Cover R Open`), quy trình điều tra và xử lý một ca lỗi gồm các bước tổng hợp sau:

---

### 1. Kiểm tra ngoại quan và truy xuất thông tin sản xuất (Traceability)
* **Kiểm tra ngoại quan:** Kiểm tra trực quan các vấn đề về mối hàn, dị vật hoặc vị trí lắp đặt linh kiện (ví dụ: kiểm tra lắp đặt PI sensor và tấm chắn sáng).
* **Kiểm tra thông tin lịch sử:** 
  * Xác định ngày sản xuất và địa điểm (ví dụ: bo mạch sản xuất ngày 2026-04-09 tại JQH, hàng đi thẳng không có lịch sử sửa chữa).
  * Kiểm tra lịch sử lô linh kiện (ví dụ: lô nhập cầu chì `F201` mã `1T5M16P0015-AA` với số lượng 1000 PCS, thống kê từ tháng 1/2025 đến tháng 5/2026 có tổng nhập 63.880 PCS không ghi nhận lỗi).

### 2. Kiểm tra chức năng và chạy chẩn đoán hệ thống
* **Kiểm tra tự động:** Chạy các bài kiểm tra ICT, FCT, kiểm tra tồn kho nội bộ hoặc nhà cung cấp.
* **Sử dụng lệnh chẩn đoán chuyên dụng:** 
  * Chạy lệnh `U037 FAN ALL` (chạy trên 20 giây để kiểm tra quạt 3Pin đối với lỗi `C6900`).
  * Chạy lệnh `U950` và lấy log phân tích khi gặp lỗi động cơ `HOP_MOT_M_OUT2` (`C7303`).
  * Sử dụng lệnh `U201` (bấm `79248313`) để kiểm tra vị trí Touch Panel (như khi điều tra lỗi `Cover R Open`).
  * Thực hiện cài đặt ban đầu (initial setting) hoặc chạy Upsoft OK.

### 3. Phân tích chi tiết phần cứng và đối chiếu Jig
* **Phân tích hình ảnh / X-ray:** Chụp X-ray (ví dụ: kiểm tra cầu chì `F201` không thấy vị trí đứt, từ đó đánh giá khả năng lỗi tiếp xúc đầu kết nối bên trong).
* **Kiểm tra linh kiện và kết nối:** 
  * Kiểm tra các linh kiện như `302XC45031` (UNIT LOW VOLTAGE) hoặc chân pin của `PIN TERMINAL` (mã `302XC15020 JURARON`) bị tụt vào trong nhựa dẫn đến rò rỉ cao áp (`C2103`).
  * Kiểm tra cáp kết nối (ví dụ: cáp FFC giữa board MAIN và board ENGINE `Engine 基板YC3` gây lỗi `C3501` do đọc/ghi rời rạc 离散write時).
* **Đối chiếu và so sánh tương quan Jig:** Thực hiện xác nhận tương quan giữa các loại jig trên cả UNIT OK và UNIT NG (tất cả không có LID):
  * **Jig Nano Scan** (NanoScan / JIG Nano SCAN): Không có chênh lệch PIN.
  * **Jig Beam** (JIG BEAM): Chênh lệch PIN lớn.
  * **Jig Bow** (JIG BOW / JIG BOW SKEW): Mức độ chênh lệch PIN trung bình; phân tích tỷ lệ NG trên các jig Bow Skew theo từng JIG BEAM để tìm ra JIG BEAM có tỷ lệ NG thấp nhằm khớp tương quan phù hợp.

### 4. Thu thập Log và Đánh giá nguyên nhân / An toàn
* **Thu thập Log:** Thu thập file log (ví dụ: lỗi `C0650` khi lắp tùy chọn FAX System) để phân tích dạng sóng tín hiệu.
* **Làm rõ điều kiện phát sinh:** Ví dụ đối với lỗi `C6900`, làm rõ nguyên nhân phần mềm yêu cầu 20 giây liên tục không phát hiện khóa mới báo lỗi `Cコール`, trong khi quy trình kiểm tra quạt chỉ diễn ra trong 5 giây nên không phát hiện kịp thời.
* **Đánh giá an toàn và xu hướng:** Đánh giá mức độ ảnh hưởng an toàn (ví dụ: mất nguồn 5V0 làm máy không khởi động nhưng không gây vấn đề an toàn; xác nhận không có xu hướng lỗi bất thường).

### 5. Đưa ra đối sách, xử lý và xác nhận kết quả
* **Biện pháp xử lý tạm thời / kiểm soát:** Tạm giữ hàng tồn kho thành phẩm chờ PQM xem xét phương pháp phân loại, liên hệ bộ phận SM lọc hàng tồn kho, thêm thao tác xác nhận linh kiện trước khi lắp ráp trong vòng 2 tuần để kiểm tra tính khuynh hướng.
* **Thay thế và xác nhận (Line out / Verification):** Thay thế linh kiện hỏng (ví dụ: thay cầu chì `F201` mới, thay Toner Hopper Assy), thực hiện chạy lại quy trình (Line out, cài đặt ban đầu lại) và kiểm tra lặp lại để xác nhận kết quả (ví dụ: bật/tắt nguồn 10 lần đạt 10/10 tốt, hoặc thao tác kiểm tra lỗi `Cover R Open` 15 lần không tái hiện).

---
*Ghi chú bổ sung từ tài liệu:* Trong sổ tay tri thức cũng có các dữ liệu tham chiếu về bố cục tuyến đường và bản đồ trong các tệp Excel như `CTUマップ再検討20251215.xlsx`, `CTUマップ再検討20260318.xlsx`, `CTUマップ再検討20260317.xlsx`, và `CTUマップ修正20260406.xlsx` (trang tính `CourseLayout_CTU` cho mã sản phẩm `C3B_YB2200C300**` chứa các điểm RFID, băng từ, khay オリコン, cửa lấy hàng 引き取り口, và vị trí sạc 充電位置). Phần 5 trong dữ liệu gốc ghi nhận chưa đủ dữ kiện nếu thiếu câu hỏi, tuy nhiên các nội dung trên đã được tổng hợp hoàn toàn từ các phần cung cấp.

### A3. 4M trong phân tích nguyên nhân lỗi là gì? Cho ví dụ mỗi nhánh.

- Thời gian: 63.07 s (5 phần 50.84 s + gộp 12.23 s).

Dựa trên các phần thông tin được cung cấp từ Sổ tay tri thức, dưới đây là tổng hợp câu trả lời cho yêu cầu của bạn:

* **Về định nghĩa 4M và ví dụ các nhánh trong phân tích nguyên nhân lỗi:** Sổ tay tri thức hiện **thiếu dữ kiện** để trả lời câu hỏi này. Cụ thể, theo nội dung tại **Phần 1**, sổ tay không chứa đủ dữ kiện để trả lời (do đoạn văn bản bị cắt cụt ở phần cuối) nên chưa đủ dữ kiện để kết luận.
* **Dữ liệu hiện có trong tài liệu (không phân loại theo 4M):** Các phần còn lại của sổ tay chủ yếu tập trung cung cấp các báo cáo điều tra lỗi kỹ thuật cụ thể cho model **Iris2024** và các thông tin khác, chứ không định nghĩa khái niệm 4M:
  * **Báo cáo lỗi kỹ thuật (Phần 2):** Bao gồm chi tiết các lỗi Fax, nguồn điện, RFID, Scan và bo mạch PWB với các mã báo cáo như `KTD-2026-06-0540-Iris2024-C35-A2-NG Fax.xlsx`, `KTD-2025-09-0953-Iris2024-C2B-NG Fax.xlsx`, `KTD-2026-06-0555-Iris2024-C33-A1-Không lên nguồn.xlsx`, `KTD-2025-05-0447-Iris2024-C33-A2-C6770.xlsx`, `KTD-2026-02-0152-Iris2024-C33-A2-TLBĐ NG RFID.xlsx`, `KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx`...
  * **Bố cục khóa học CTU (Phần 3):** Các tệp Excel liên quan đến bản đồ và bố cục khóa học như `CTUマップ再検討20251215.xlsx`, `CTUマップ再検討20260318.xlsx`, `CTUマップ再検討20260317.xlsx`, `CTUマップ修正20260406.xlsx`.
  * **Thông số điện áp (Phần 5):** Các giá trị tối thiểu, tiêu chuẩn (Typ), tối đa của các thông số **VGH**, **Vcom**, **VGL**, và **AVDD**.

**Kết luận:** Do tài liệu không chứa định nghĩa hoặc ví dụ về 4M và bị cắt cụt ở phần cuối theo **Phần 1**, hệ thống ghi nhận thiếu dữ kiện và không tự ý bịa thêm thông tin ngoài tài liệu.

### A4. Các nhóm nguyên nhân gây lỗi F CALL thường gặp là gì?

- Thời gian: 71.35 s (5 phần 61.33 s + gộp 10.02 s).

Dựa trên các phần thông tin trong Sổ tay tri thức được cung cấp, dưới đây là tổng hợp chi tiết và đầy đủ nhất về các nhóm nguyên nhân gây lỗi liên quan đến **F CALL** (cụ thể là các lỗi **Beam径 NG** / lỗi đường kính Beam ở Iris LSU và các nguyên nhân liên quan được thảo luận qua các cuộc họp chất lượng bất thường):

---

### 1. Nhóm nguyên nhân về Cài đặt, Đồ gá (Jig) và Thiết lập đo lường
* **Vấn đề về cài đặt và năng lực của jig:**
  * Có sự khác biệt và phân tán giữa các JIG BEAM khác nhau (ví dụ: JIG BEAM 1 có xu hướng cho đường kính Beam nhỏ nhất quá mức ở tất cả các màu và mọi chiều cao ảnh - image height; trong khi JIG BEAM 1 có năng lực điều chỉnh tương đương JIG BEAM 6, các JIG còn lại có năng lực điều chỉnh khác nhau giữa các màu K, M, C, Y).
  * Phát sinh hiện tượng tỷ lệ NG đường kính Beam có xu hướng tăng mặc dù KDC đã phát hành thay đổi 4M cho 6 JIG BEAM.
  * Bản thân JIG có thể gặp vấn đề về setting hoặc cần dịch độ sâu phán định của JIG BEAM thêm 1 mm nếu có sai lệch. 
  * Sự chênh lệch PIN giữa các thiết bị đo: JIG BEAM lớn, JIG BOW SKEW trung bình, và JIG Nano SCAN không có.
* **Vấn đề về điều kiện và phương pháp đo:**
  * Độ lệch theo chiều ngang xuất phát từ vị trí độ sâu của camera, trong khi độ lệch theo chiều dọc xuất phát từ điều kiện đo đường kính Beam.
  * Từng ghi nhận trường hợp đo thất bại tại image height -140 của máy `#7018` (tất cả các màu), trong khi máy `#7022` đo được, điều này cho thấy cần điều tra ảnh hưởng từ phía Unit.

### 2. Nhóm nguyên nhân về Linh kiện, Cấu trúc và Vị trí lắp ráp (Lens, LD Block, Bracket)
* **Biến động vị trí tiêu cự và linh kiện Lens A:**
  * Hiện tượng thay đổi vị trí tiêu cự ở LENS A xuất hiện ngay cả khi cùng LOT và cùng CAV.
  * Đối tượng kiểm tra tập trung vào Lens A Cav 2 (Lot 6116) và Lens A Cav 3 (Lot 6116) do có tỷ lệ NG cao nhất (ví dụ Lens A Cav 3 có vị trí lấy nét ở chiều cao ảnh trung gian và +140 lệch về phía +).
  * Có các ASSY lấy nét được và không lấy nét được, chứng tỏ có yếu tố khác ngoài setting; UNIT có vị trí lấy nét khác nhau theo từng chiều cao ảnh và có UNIT biến động vị trí lấy nét ngay cả khi cùng LENS Cav./Lot.
* **Yếu tố LD Block, Bracket và Lens Co:**
  * Có khả năng vị trí Co của LD block thay đổi theo thời gian.
  * Dữ liệu đo 3D Co và BRACKET (thực hiện bởi Hung - 製造技術1課) cho LSU OK và LSU NG liên quan đến đánh giá lệch beam của LD1 và LD4, cũng như so sánh kích thước liên quan giữa BRACKET LD và LENS CO giữa UNIT OK và NG, **không thấy khác biệt rõ ràng**.
  * Dữ liệu lượng sáng cho thấy **không có tương quan** giữa lượng sáng và giá trị đường kính BEAM.

---

### Điểm mâu thuẫn / Khác biệt ghi nhận giữa các phần:
* **Về tương quan dữ liệu đo:** Tại cuộc họp lần 3, dữ liệu cho thấy *không có tương quan* giữa lượng sáng và giá trị đường kính BEAM. Trong khi đó, tại cuộc họp lần 5, dữ liệu đồ thị biểu diễn mối tương quan giữa đường kính beam và độ sâu do Kurihara (製造技術13課) tạo ra cho thấy *tương quan tốt nhưng vẫn còn khá phân tán*.

### A5. Khi gặp lỗi lặp lại nhiều lần trên cùng một line thì nên điều tra theo hướng nào?

- Thời gian: 46.97 s (5 phần 41.37 s + gộp 5.6 s).

Dựa trên nội dung các phần của sổ tay tri thức đã cung cấp, **chưa đủ dữ kiện** để trả lời câu hỏi cụ thể về hướng điều tra khi gặp lỗi lặp lại nhiều lần trên cùng một line (Phần 3 và Phần 5 ghi rõ là thiếu dữ kiện). 

Tuy nhiên, tổng hợp toàn bộ các phần dữ liệu, sổ tay tri thức **không có hướng dẫn chung** cho việc điều tra lỗi lặp lại trên line, mà chỉ ghi nhận các hướng xử lý, nguyên nhân và đối sách cụ thể cho từng mã lỗi hoặc hiện tượng phát sinh riêng biệt trên các dòng máy **Iris2024** và **Iris2020**. Dưới đây là tóm tắt thông tin liên quan từ các phần:

* **Về lỗi đường kính Beam của Iris LSU (Cuộc họp chất lượng bất thường lần 3 và lần 5):** 
  * *Hiện tượng/Nguyên nhân:* Có ASSY lấy nét được, có ASSY không; vị trí tiêu cự LENS A thay đổi dù cùng LOT/CAV; vị trí Co của LD block có thể thay đổi theo thời gian; không tương quan giữa lượng sáng và đường kính BEAM.
  * *Đối sách điều tra:* Thay đổi 4M cho 6 JIG BEAM (tỷ lệ lỗi tăng); so sánh tương quan giữa JIG Nano Scan, JIG BEAM, JIG BOW trên UNIT OK và UNIT NG; so sánh kích thước BRACKET LD và LENS CO; đo 3D Co và BRACKET.
* **Các lỗi phần cứng, linh kiện hoặc bo mạch cụ thể (ví dụ C0350, C0980, C1950, C2103, C3200, C3501, C6900, C7303, v.v.):** 
  * Thường được điều tra dựa trên việc kiểm tra linh kiện hỏng/chập/hở mạch (như cầu chì F401, F201, linh kiện Q, C, U), kiểm tra tiếp xúc cáp FFC, kiểm tra điện áp tín hiệu, đo chân pin terminal, hoặc chạy các lệnh chẩn đoán chuyên dụng (như `U037 FAN ALL`, `U950`, v.v.).

### A6. Đối sách tạm thời và đối sách lâu dài khác nhau thế nào? Khi nào dùng mỗi loại?

- Thời gian: 48.41 s (5 phần 43.8 s + gộp 4.61 s).

Dựa trên các phần của sổ tay tri thức được cung cấp, **không có thông tin nào** đề cập đến khái niệm, định nghĩa hoặc sự khác nhau giữa "đối sách tạm thời" và "đối sách lâu dài", cũng như thời điểm dùng mỗi loại. 

Các phần tài liệu được cung cấp chỉ tập trung mô tả hiện tượng, nguyên nhân lỗi kỹ thuật (như lỗi `C0350`, `C6900`, kẹt giấy, đứt cầu chì F201, lỗi linh kiện trên các dòng máy *Iris2020*, *Iris2024*), thông số kỹ thuật bản vẽ mạch in và cấu trúc bo mạch, hoàn toàn thiếu dữ kiện về câu hỏi đối sách tạm thời và lâu dài.

### A7. Những thông số/ngưỡng nào thường phải kiểm tra đầu tiên khi máy báo lỗi?

- Thời gian: 44.91 s (5 phần 39.14 s + gộp 5.77 s).

Dưới đây là tổng hợp thông tin từ các phần của Sổ tay tri thức để trả lời cho câu hỏi: *"Những thông số/ngưỡng nào thường phải kiểm tra đầu tiên khi máy báo lỗi?"*

* **Về tình trạng thiếu dữ kiện:** 
  * Phần 1 và Phần 4 ghi nhận rằng sổ tay không chứa đủ dữ kiện để trả lời cụ thể cho câu hỏi hoặc chưa có câu hỏi chi tiết về một số trường hợp cụ thể. 
  * Phần 5 lưu ý rằng nếu câu hỏi cụ thể chưa được đề cập trong phạm vi dữ liệu, cần cung cấp thêm chi tiết.

* **Thông số/ngưỡng cụ thể được đề cập khi máy báo lỗi (đặc biệt là lỗi không lên nguồn hoặc các lỗi quang học, cảm biến, phần cứng):**
  * **Cầu chì và Điện áp nguồn (như mô tả lỗi không lên nguồn trên model Iris2024):**
    * Kiểm tra cầu chì **F201** (trạng thái hở mạch/OPEN, có thể do lỗi tiếp xúc đầu kết nối bên trong mặc dù kiểm tra X-ray không thấy vị trí đứt). Sau khi thay cầu chì F201 mới, máy bật/tắt nguồn 10 lần hoạt động bình thường.
    * Mất điện áp **5V** (hoặc **5V0** không có đầu ra), đứt cầu chì F201 (item code `302XD45010-8`, mã `C33-A1`, `C35-A1`, các tệp tài liệu liên quan: `KTD-2026-06-0555-Iris2024-C33-A1-Không lên nguồn.xlsx`, `KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx`).
  * **Điện áp và Dòng điện tổng quát:**
    * Điện áp nguồn (ví dụ: +12V, +5.1V, +3.3V, +1.8V, +24V...) và các mức điện áp ngõ ra (như nguồn LED DRIVE IF, LDO).
    * Dòng điện tối đa (max current) và trạng thái dòng điện kiểm tra (ví dụ phát hiện bất thường khi dòng ở mức 5µA hoặc thấp hơn).
  * **Thông số Điện áp tối (Dark voltage) và Cảm biến:**
    * Điện áp tối nhỏ hơn 0.15V hoặc lớn hơn 0.80V.
    * Trạng thái giá trị cảm biến (từ 60 trở xuống hoặc từ 944 trở lên kéo dài từ 3 giây trở lên).
  * **Thông số Quang học và Dầm (Beam / Bow / Skew / Light Path):**
    * Đường kính Beam, giá trị Bow [um], Skew [um], Light Path [mm] và BD Timing [mm].
    * Trở kháng kiểm soát đường tín hiệu (ví dụ 100Ω cho LVDS/DSI).
  * **Thông số Áp suất và Cơ khí:**
    * Áp suất khí nén (Air Pressure Up / Air Pressure Dw).
    * Kiểm tra kết nối connector, độ rơ/khe hở (ví dụ khe hở lắp bộ sấy 1.0mm) và vị trí Home của cơ cấu.

### A8. Các ngoại lệ hay gặp khiến một ca lỗi không đi theo kịch bản chuẩn là gì?

- Thời gian: 57.93 s (5 phần 44.33 s + gộp 13.6 s).

Dựa trên nội dung tổng hợp từ các phần của sổ tay tri thức, các ngoại lệ hay gặp khiến một ca lỗi không đi theo kịch bản chuẩn được phân loại theo từng trường hợp thiết bị và mã lỗi cụ thể như sau:

---

### 1. Lỗi đường kính Beam của Iris LSU (Ngoại lệ trong các ca đo đạc và lắp ráp)
Các ca lỗi không theo kịch bản chuẩn liên quan đến đường kính Beam ghi nhận các điểm bất thường sau:
* **Sự bất đồng giữa các thiết bị đo (Jig và NanoScan):** 
  * Có sự khác biệt đáng kể giữa xu hướng dữ liệu đo bằng **Beam治具** và **BowSkew治具**. 
  * **NanoScan** cho kết quả UNIT hội tụ tốt (OK), trong khi **Beam jig** lại báo không hội tụ (NG). Tài liệu ghi nhận: *Nếu NanoScan báo OK mà jig báo NG thì cơ bản vấn đề nằm ở phần Setting của jig.*
* **Biến động phần cứng ngoài dự kiến:** 
  * Tồn tại đồng thời các ASSY lấy nét được và không lấy nét được dù cùng setting, cho thấy có yếu tố khác ngoài cài đặt.
  * Hiện tượng UNIT biến động vị trí lấy nét ngay cả khi sử dụng cùng LENS Cav./Lot (đặc biệt ghi nhận trên Lens A Cav 2 và Lens A Cav 3 thuộc Lot 6116).
  * Vị trí Co của LD block có khả năng thay đổi theo thời gian; không có tương quan giữa lượng sáng và giá trị đường kính Beam.
* **Ảnh hưởng sau thay đổi kỹ thuật (4M):** Tỷ lệ NG đường kính Beam có xu hướng tăng sau khi thay đổi 4M trên 6 JIG BEAM. Phát sinh hiện tượng đo thất bại tại image height -140 của #7018 trong khi #7022 đo được, đòi hỏi phải phân biệt độ lệch vị trí độ sâu camera (chiều ngang) và điều kiện đo (chiều dọc).

---

### 2. Lỗi khởi tạo ban đầu dòng máy IRIS2020 (Low model) - Mã lỗi C3501
Khi thực hiện initial setting sau khi chạy Upsoft OK, màn hình LCD có thể hiển thị mã lỗi **C3501** với các ngoại lệ kỹ thuật:
* **Nguyên nhân cốt lõi:** ASIC phát hiện lỗi khi đọc/ghi rời rạc (離散write時) dẫn đến lỗi checksum hoặc lỗi kích thước dữ liệu (ghi vào PantherScan lần đầu).
* **Điểm tiếp xúc ngoại lệ:** Nghi ngờ do lỗi tiếp xúc kém của cáp FFC kết nối giữa board MAIN và board ENGINE (Engine 基板YC3), kèm theo yêu cầu kiểm tra dạng sóng trong khung màu đỏ và dị vật.
* **Tính tái hiện:** Lỗi này đặc trưng bởi việc **thường không tái hiện lại** sau khi thực hiện line out và chạy lại quá trình cài đặt ban đầu.

---

### 3. Dữ liệu thiếu và không đề cập ca lỗi
* **Mã lỗi C0980:** Dữ liệu bị cắt ngang ở phần cuối tài liệu nên **chưa đủ dữ kiện** để kết luận các ngoại lệ liên quan.
* *Lưu ý:* Các thông tin kỹ thuật khác về bộ nguồn **OPEN FRAME Ver. B (ETX9KC995ME)** hay bo mạch **PWB IH 200 ASSY (302ND47260)** trong tài liệu tập trung vào thông số linh kiện, sơ đồ mạch và ngưỡng bảo vệ (như quá dòng từ 120A, nhiệt độ IGBT từ 120°C trở lên), không mô tả các ngoại lệ ca lỗi cụ thể.

### A9. Làm sao phân biệt lỗi do con người với lỗi do thiết bị?

- Thời gian: 50.29 s (5 phần 40.07 s + gộp 10.22 s).

Dựa trên các phần dữ liệu được cung cấp từ sổ tay tri thức, hiện tại **dữ liệu chưa đề cập hoặc thiếu dữ kiện** để trả lời câu hỏi *"Làm sao phân biệt lỗi do con người với lỗi do thiết bị?"* (đúng như nội dung đã ghi nhận tại Phần 2). 

Các phần thông tin còn lại trong sổ tay đề cập đến các chủ đề kỹ thuật khác không liên quan trực tiếp đến việc phân biệt lỗi, cụ thể gồm:

* **Thông tin kho/sổ tay (Phần 1):** Ghi nhận 889 document và mục trong sổ tay, thời điểm tạo `2026-10-05T06:43:51+07:00`.
* **Thông số nguồn bo mạch PWB (Phần 3):** Bảng nguồn (**POWER TABLE**) của bản vẽ mạch in **CCD ASSY 302XD01070** (phiên bản 04) bao gồm các mức điện áp (+12V, +12V2, +5.1V, +10VL, +3.3VL, +1.8VL, GND) và các thông số LDO then chốt.
* **Chi tiết lỗi C2103 trên máy IRIS2020 A-6 (Phần 4):**
  * **Hiện tượng:** Lỗi phát hiện bất thường motor hiện hình (Color) (*C2103检知条件：現像モータ異常(Color)*) khi in ảnh RCG (ghi nhận 3 trường hợp trên 2 máy).
  * **Nguyên nhân cốt lõi:** Linh kiện **PIN TERMINAL (302XC15020 JURARON)** bị lỗi (chân pin bên trong bị tụt vào trong nhựa), gây tiếp xúc kém, rò rỉ và nhiễu điện.
  * **Biện pháp đối ứng:** Tạm giữ hàng tồn kho thành phẩm, liên hệ bộ phận **SM** lọc hàng, yêu cầu kiểm tra linh kiện trước khi lắp ráp trong **2 tuần**, kiểm tra kỹ linh kiện tại VN và tạm thời không cần phân tích **USBLOG**.
* **Giá trị điện áp bo mạch điều khiển (Phần 5):** Các thông số điện áp then chốt gồm **VGH**, **Vcom**, **VGL**, và **AVDD**.

### A10. Bài học kinh nghiệm chung rút ra từ các ca lỗi đã xử lý là gì?

- Thời gian: 41.63 s (5 phần 36.54 s + gộp 5.09 s).

Dưới đây là phần tổng hợp thông tin từ 5 phần của sổ tay tri thức liên quan đến câu hỏi **"Bài học kinh nghiệm chung rút ra từ các ca lỗi đã xử lý là gì?"**:

* **Thiếu dữ kiện:** Phần lớn các phần trong sổ tay tri thức (gồm thông tin về cuộc họp chất lượng bất thường của Iris LSU, dữ liệu Timing tháng 7, nguyên nhân lỗi C6900 dòng máy Iris2020, và tổng quan các bo mạch chủ/tài liệu kỹ thuật) **chưa cung cấp đủ dữ kiện** hoặc không đề cập trực tiếp đến một "bài học kinh nghiệm chung" tổng quát nào cho tất cả các ca lỗi.
* Riêng tại **Phần 2**, nội dung bị ngắt quãng ở phần cuối mô tả thông số của `KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx` nên không thể hoàn thiện ý. 

Các phần thông tin đã hiển thị chỉ tập trung vào các nội dung chi tiết cụ thể của từng sự vụ:
* **Lỗi đường kính Beam của Iris LSU (Phần 1):** Rút ra các điểm bất thường (như JIG số 1 quá nhỏ, nghi vấn vị trí Co của LD block thay đổi theo thời gian, hiện tượng tiêu cự LENS A thay đổi dù cùng LOT/CAV) và các hướng đối ứng (kiểm tra setting của jig, dịch độ sâu phán định của JIG BEAM thêm 1 mm, xem xét lại điều kiện phủ và chiếu UV).
* **Lỗi C6900 dòng máy Iris2020 (Phần 4):** Nguyên nhân là do phần mềm quy định cần liên tục 20 giây không phát hiện khóa (lock) thì mới báo lỗi Cコール, dẫn đến quy trình kiểm tra 5 giây của quạt định vị (FAN) không phát hiện được lỗi kết nối.

Bạn vui lòng cung cấp thêm phần nội dung còn thiếu hoặc đặt câu hỏi cụ thể hơn dựa trên các phần thông tin đã hiển thị trong sổ tay nhé!

### A11. Khi nào nên dừng máy ngay và khi nào có thể chạy tiếp khi có cảnh báo?

- Thời gian: 60.8 s (5 phần 43.18 s + gộp 17.62 s).

Dựa trên nội dung của 5 phần trong Sổ tay tri thức, **dữ kiện trực tiếp trả lời câu hỏi "Khi nào nên dừng máy ngay và khi nào có thể chạy tiếp khi có cảnh báo" hiện đang bị thiếu**. 

Tuy nhiên, Sổ tay tri thức có cung cấp một số thông tin liên quan đến thời gian khóa hệ thống, mã lỗi tự chẩn đoán (C-call) và các điều kiện phát sinh lỗi trên dòng máy **Iris2020** từ Phần 3 và Phần 4 như sau:

---

### 1. Thông tin về thời gian khóa hệ thống và chờ xử lý (Phần 3)
* **Các mốc thời gian chờ:** Thời gian chờ reset nguồn hoặc khóa hệ thống bao gồm: `5s`, `100ms`, `1s`, `20s`, `6 giây`.
* **Đối tượng áp dụng mã lỗi C-call:** Seat inserter, máy màu, ペーパーフィーダー, đại容量フィーダー, hoặc サイドフィーダー.
* **Quy trình xử lý lỗi tổng quát:** Kiểm tra kết nối và các cổng cắm (connector), làm sạch linh kiện, reset nguồn hoặc cài đặt lại firmware, thay thế các linh kiện hoặc bản mạch tương ứng (bản mạch FAX, bản mạch Engine, bản mạch Main, bản mạch Image Driver, bản mạch nguồn, v.v.).

### 2. Điều kiện phát sinh và quy định lỗi liên quan (Phần 4)
* **Lỗi `C6900` (Iris2020 hạ tầng):** Phát sinh kèm theo hiện tượng kẹt giấy (JAM) ở trang thứ 3 khi in liên tục 3 tờ giấy dày trong quá trình kiểm tra PQC xuất xưởng. Nguyên nhân do phần mềm quy định cần liên tục `20 giây` không phát hiện khóa thì mới báo lỗi `Cコール`, khiến quy trình kiểm tra `5 giây` của quạt định vị (FAN) không phát hiện được lỗi kết nối.
* **Các mã lỗi phần cứng và firmware liên quan đến C-call (Phần 3 & Phần 4):** 
  * `C0030`, `C0060`, `C0980`, `C1800`, `C1820`, `C5134`, `C6130`, `C6900`, `C6930`, `C7880`, `C8B00`, `C8B40`
  * `C0650`, `C2103`, `C3501`, `C7303`

---

### 3. Tình trạng dữ liệu các phần khác
* **Phần 1:** Tập trung vào lỗi đường kính Beam của Iris LSU (jig số 1, mã #7018, mã #7022). Không chứa thông tin về việc dừng máy hay chạy tiếp.
* **Phần 2:** Tập trung vào các báo cáo điều tra lỗi model **Iris2024** (FAX, Nguồn, Panel/LCD như `C6770`, `C7902`, `C1950`, `C4001`, RFID, Scan SITC NG). Không chứa tiêu chí dừng/chạy máy khi cảnh báo.
* **Phần 5:** Chỉ liệt kê các tài liệu, sơ đồ mạch nguồn (Power Supply) của model EUK9MQD84HA và Iris2020. Không chứa hướng dẫn vận hành khi có cảnh báo.

### A12. Dữ liệu nào cần thu thập trước khi bắt đầu phân tích nguyên nhân một ca lỗi?

- Thời gian: 55.75 s (5 phần 41.38 s + gộp 14.37 s).

Dưới đây là câu trả lời tổng hợp và đầy đủ nhất dựa trên nội dung được cung cấp từ các phần của sổ tay tri thức đối với câu hỏi về dữ liệu cần thu thập khi phân tích nguyên nhân ca lỗi:

---

### 1. Dữ liệu cần thu thập và ghi nhận theo các tài liệu/báo cáo lỗi
Dựa trên các phần tài liệu, khi xảy ra lỗi trong quá trình sản xuất hoặc kiểm tra, các dữ liệu thực tế được thu thập và ghi nhận bao gồm:

* **File log hệ thống:** Cụ thể đối với **Lỗi C0650 (Dòng máy IRIS2020 High Model)** phát sinh tại khâu kiểm tra xuất xưởng PQC, tài liệu ghi nhận: **"Đã thu thập file log để phân tích nguyên nhân"** [Phần 4].
* **Mã báo cáo và tên tệp chi tiết:** Các báo cáo phân tích lỗi được lưu trữ dưới dạng tệp dữ liệu, ví dụ:
  * `KTD-2026-06-0555-Iris2024-C33-A1-Không lên nguồn.xlsx` [Phần 2]
  * `KTD-2025-12-1314-Iris2024-C33-A1-C6760.xlsx` [Phần 2]
  * `KTD-2025-07-0733-Iris2024-C33-A11-C6950.xlsx` [Phần 2]
  * `KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx` [Phần 2]
* **Hiện tượng lỗi và mã lỗi:** Ghi nhận hiện tượng thực tế trên màn hình panel/LCD (ví dụ: lỗi `C0350`, `C6760`, `C6950`, `C0650`, `C2103`, `C3501`, `C6900`, `C7303`, `Cover R Open`, hoặc hiện tượng không lên nguồn, mất điện áp 5V, kẹt giấy JAM) [Phần 1, Phần 2, Phần 4].
* **Thông tin linh kiện liên quan và nhà cung cấp:** 
  * Tên linh kiện, mã bản mạch (ví dụ: bản mạch `PWB PANEL ASSY WITH SOFTWARE` với mã item `3V2XD01380-1`, nhà cung cấp `TAISHODO VIETNAM CO., LTD.`; bản mạch `UNIT LOW VOLTAGE` chứa cầu chì `F201`; linh kiện `U16`; cầu chì `YF1`, `F002`; bản mạch CCD ASSY mã PWB `302XD01070` chứa các IC `U5 AK8446BVN`, `U4 TCD2724DG-1(Z,C)`, `U6 BD00IA5WEFJ-E2`, `U7 BD00IC0WEFJ-E2`, `U8 BDJ0GA3WEFJ-E2`) [Phần 1, Phần 2, Phần 3].
* **Thông số đo kiểm điện trở chuẩn (OK/NG):**
  * Tại line C33-A2 (Model Iris2024) cho lỗi `C0350`: Chuẩn OK là **7.5 Ohm**, NG bằng `OL` [Phần 1].
  * Các lỗi liên quan đến cầu chì (`YF1`, `F002`, `F201`): Chuẩn OK dao động từ `0.1Ω` đến `0.2Ω`, chuẩn NG là `OL` hoặc `Open` [Phần 2].
* **Kết quả kiểm tra ngoại quan và ảnh chụp:** Kiểm tra ngoại quan mối hàn, ảnh chụp X-ray (ví dụ kiểm tra cầu chì `F201`) [Phần 2].

---

### 2. Điểm mâu thuẫn và mức độ thiếu dữ kiện
* **Điểm mâu thuẫn:** Không có mâu thuẫn trực tiếp giữa các phần; các phần đề cập đến các model máy khác nhau (`Iris2024`, `IRIS2020`) và các dòng lỗi/linh kiện khác nhau trong quá trình sản xuất.
* **Dữ liệu còn thiếu:** Các phần tài liệu được cung cấp **chưa có một danh mục hoặc quy chuẩn tổng quát đầy đủ** liệt kê toàn bộ các hạng mục dữ liệu bắt buộc cần thu thập *trước khi* bắt đầu phân tích nguyên nhân cho mọi ca lỗi. Tài liệu chỉ liệt kê các dữ liệu thực tế đã được thu thập rải rác trong các báo cáo sự cố cụ thể (trong đó chỉ có trường hợp lỗi `C0650` đề cập trực tiếp đến việc thu thập file log cho mục đích phân tích nguyên nhân) [Phần 4, Phần 5].

## Phụ lục B — Đáp án đầy đủ, lane RAG (12 câu)

Nguồn: `probe_rag_nofp.json` — lane `rag_cty_no_source_fingerprint_gate` (đọc kèm mục 3.2 về hai cổng đã hạ).

### B1. LSU là gì và gồm những bộ phận quang học chính nào?

- Thời gian: retrieval 158.24 s + tổng hợp 6.6 s = 164.84 s; item 17, nguồn riêng 6; `filtered_as_stale_count=0`.

Dựa trên tài liệu đính kèm, dưới đây là thông tin về LSU và các bộ phận quang học chính:

* **LSU** là viết tắt của **Laser Scanner Unit** (Cụm máy quét laser). Trong quá trình in ảnh điện tử, dữ liệu được xử lý thông qua LSU để chiếu tia LASER lên bề mặt trống cảm quang DRUM (đã được tĩnh điện), tạo thành ảnh ẩn tĩnh điện dựa vào sự khác nhau về điện thế (được gọi là quá trình phơi sáng).
* **Các bộ phận/linh kiện quan trọng trong LSU** được đề cập trong tài liệu bao gồm:
  * **Laser Diode** (Điốt laser), cấu tạo gồm các phần chính như: Seal (シール), Kính (窓ガラス - cửa sổ kính), Cover (キャップ - nắp), Laser Chip (レーザチップ), The sub-mount (サブマウント - mạch điện tử), Điốt quang (Photodiode), Khung đỡ kim loại, và LID.
  * **Motor Polygon** (mô-tơ đa giác / mô-tơ gương đa giác).
  * **Gương phản xạ** (Mirror).
  * **Lens F** (thấu kính F) hoặc các cấu cơ điều chỉnh gương, thấu kính để chỉnh sửa đường sáng, độ lệch (Skew) và độ cong đường sáng (Bow).

### B2. Quy trình điều tra một ca lỗi gồm những bước nào?

- Thời gian: retrieval 119.53 s + tổng hợp 11.52 s = 131.06 s; item 15, nguồn riêng 9; `filtered_as_stale_count=0`.

Dựa trên các tài liệu đính kèm, quy trình điều tra một ca lỗi (hoặc các nội dung liên quan đến việc điều tra lỗi) bao gồm các bước và hướng dẫn sau đây:

* **Đối với việc điều tra lỗi cần dùng bản mạch (MAIN, ENGINE,...):** Sau khi điều tra lỗi, sẽ xử lý theo 2 cách: (1) Chuyển cho KTĐ để gửi bản mạch về Partner để xóa dữ liệu Serial thân máy lưu trong bản mạch; hoặc (2) CT sẽ chịu chi phí và giữ lại bản mạch để làm bản mạch dummy dùng cho điều tra lỗi về sau [1].
* **Đối với quy trình khắc phục và xử lý khi xảy ra lỗi AGV:** 
  * Các quy trình khắc phục lỗi chỉ nên được thực hiện sau khi người vận hành đã xác định được vị trí khắc phục an toàn [6].
  * Vui lòng điều tra nguyên nhân dựa trên thông tin lỗi (mã lỗi và thông báo lỗi hiển thị trên màn hình) [6].
* **Ví dụ về nội dung và trình tự các bước kiểm tra/điều tra thực tế trong một số ca lỗi cụ thể:**
  * Thực hiện lại thao tác [7], [12].
  * Liên lạc KTCT [7].
  * Kiểm tra kết nối đã vào hết, không bất thường [7], [12].
  * Crosscheck (chéo kiểm tra) dây WIRE PF INTERFACE hoặc các linh kiện liên quan, thực hiện lại thao tác [7].
  * Xác nhận ngoại quan không có gì bất thường, kiểm tra thông mạch bằng đồng hồ điện [7].
  * Phán đoán nguyên nhân (ví dụ: có dị vật khi kết nối và rơi ra khi Crosscheck [7], hoặc do Jig/phần mềm máy tính [12]).
  * Tổng hợp thông tin, liên lạc Partner để điều tra thêm [10].
  * Gửi Log phân tích để so sánh với các log lỗi phát sinh trước đó [12].

### B3. 4M trong phân tích nguyên nhân lỗi là gì? Cho ví dụ mỗi nhánh.

- Thời gian: retrieval 342.28 s + tổng hợp 6.02 s = 348.3 s; item 25, nguồn riêng 3; `filtered_as_stale_count=0`.

Dựa vào các tài liệu đính kèm, khái niệm "4M" trong phân tích nguyên nhân lỗi (thường liên quan đến việc kiểm tra các yếu tố 4M như trong các báo cáo xác nhận không có thay đổi hoặc điều tra nguyên nhân) bao gồm 4 yếu tố chính: **Man** (Con người), **Machine** (Máy móc/Thiết bị), **Material** (Nguyên vật liệu), và **Method** (Phương pháp). 

Dưới đây là ví dụ cho từng nhánh dựa trên các ngữ cảnh lỗi trong tài liệu:

* **Man (Con người):** 
  * *Ví dụ:* Do người thao tác không lắp ráp hoàn chỉnh hoặc làm gián đoạn thao tác (như rời khỏi vị trí để lấy sổ File) dẫn đến việc quên kiểm tra lại thành phẩm và chuyển sang công đoạn sau gây phát sinh lỗi.
* **Machine (Máy móc / Thiết bị):** 
  * *Ví dụ:* Lỗi phát sinh do trang thiết bị, máy móc hoặc các bộ phận bên trong như chân pin bị gãy, cảm biến, hoặc đứt dây FFC do va chạm/kẹp.
* **Material (Nguyên vật liệu / Linh kiện):** 
  * *Ví dụ:* Lỗi do bản thân linh kiện đầu vào (như linh kiện điện SENSOR A4 CIS bị lỗi, linh kiện nhựa bị nứt do đường hàn kém, hoặc lỗi biến dạng mặt phẳng linh kiện).
* **Method (Phương pháp):** 
  * *Ví dụ:* Quy định thao tác, phương pháp đóng gói, hoặc quy trình lọc hàng chưa tối ưu dẫn đến việc thao tác nhầm lẫn hoặc va chạm linh kiện trong quá trình gia công/đóng thùng.

### B4. Các nhóm nguyên nhân gây lỗi F CALL thường gặp là gì?

- Thời gian: retrieval 201.91 s + tổng hợp 10.92 s = 212.83 s; item 17, nguồn riêng 3; `filtered_as_stale_count=0`.

Dựa trên tài liệu hệ thống, các nhóm nguyên nhân hoặc danh mục lỗi F CALL (lỗi hệ thống / Fコード) thường gặp bao gồm các mã và nội dung lỗi sau:

* **F000**: 本体CPU間通信異常 (Lỗi giao tiếp giữa CPU chính) hoặc Lỗi giao tiếp giữa các CPU trong thân máy (giao tiếp giữa bộ điều khiển và bảng điều khiển).
* **F010**: プログラムRead異常（SSD） (Lỗi đọc chương trình - SSD).
* **F020 / F021 / F022**: システムメモリー異常 (Lỗi bộ nhớ hệ thống: lỗi đọc/ghi RAM hoặc lỗi bộ nhớ CPU / lỗi bộ nhớ ASIC).
* **F040**: 本体CPU間通信異常（コントローラー - プリントエンジン間通信異常） (Lỗi giao tiếp giữa các CPU trong thân máy - lỗi giao tiếp giữa bộ điều khiển và engine in).
* **F050**: エンジンメインプログラム異常 (Lỗi chương trình chính engine).
* **F052**: パネルエンジンプログラム異常 (Lỗi chương trình engine bảng điều khiển).
* **F053**: メインプログラム署名検証失敗 (Lỗi xác thực chữ ký chương trình chính).
* **F12x**: スキャン制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển quét).
* **F14x**: FAX制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển FAX).
* **F15x**: 認証デバイス制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển thiết bị xác thực).
* **F17x**: プリントデータ制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển dữ liệu in).
* **F18x**: Video制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển Video).
* **F1Dx**: 画像メモリー管理部の異常検知 (Phát hiện bất thường tại bộ phận quản lý bộ nhớ hình ảnh).
* **F21x / F22x / F23x**: 画像処理部での異常検知 (Phát hiện bất thường tại bộ phận xử lý hình ảnh).
* **F24x / F26x / F27x / F28x / F29x / F2Ax**: システム管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý hệ thống).
* **F25x**: ネットワーク管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý mạng).
* **F2Bx / F2Cx / F2Dx / F2Ex / F2Fx / F30x / F31x / F32x**: ネットワーク制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển mạng).
* **F33x**: スキャン管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý quét).
* **F34x**: パネル管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý bảng điều khiển).
* **F35x**: 印刷制御管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý điều khiển in ấn).
* **F37x**: FAX管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý FAX).
* **F38x**: 認証認可管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý xác thực và phân quyền).
* **F3Ax / F3Bx / F3Cx / F3Dx / F3Ex / F3Fx / F40x / F41x / F42x / F43x / F44x / F45x / F4Dx**: 内部設定値管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý giá trị thiết lập nội bộ).
* **F46x / F4Ax / F4Cx**: プリント描画処理部での異常検知 (Phát hiện bất thường tại bộ phận xử lý vẽ bản in).
* **F47x / F48x / F49x**: 画像編集処理部での異常検知 (Phát hiện bất thường tại bộ phận xử lý chỉnh sửa hình ảnh).
* **F50x**: FAX管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý FAX).
* **F52x / F53x / F55x / F56x / F57x**: JOB実行部での異常検知 (Phát hiện bất thường tại bộ phận thực thi công việc/JOB).
* **F61x**: レポート作成部での異常検知 (Phát hiện bất thường tại bộ phận tạo báo cáo).
* **F63x**: デバイス制御部での異常検知 (Phát hiện bất thường tại bộ phận điều khiển thiết bị).
* **F90x**: 拡張アプリケーション統合部での異常検知 (Phát hiện bất thường tại bộ phận tích hợp ứng dụng mở rộng do lỗi giao tiếp trong bo mạch chính).
* **F93x**: 拡張アプリケーション管理部での異常検知 (Phát hiện bất thường tại bộ phận quản lý ứng dụng mở rộng do lỗi giao tiếp trong bo mạch chính).
* **FC0x**: システムアプリケーションでの異常検知 (Phát hiện bất thường ở ứng dụng hệ thống do lỗi giao tiếp trong bo mạch chính).

### B5. Khi gặp lỗi lặp lại nhiều lần trên cùng một line thì nên điều tra theo hướng nào?

- Thời gian: retrieval 260.43 s + tổng hợp 6.51 s = 266.94 s; item 25, nguồn riêng 4; `filtered_as_stale_count=0`.

Dựa trên các tài liệu được cung cấp, khi gặp lỗi lặp lại nhiều lần trên cùng một line (hoặc thực hiện lại thao tác nhiều lần để kiểm tra/điều tra lỗi), các hướng điều tra và xử lý thường được áp dụng bao gồm:

* **Kiểm tra và xác nhận lại thao tác, quy trình:** Thực hiện lại các thao tác nhiều lần (ví dụ: 5 lần, 15 lần, hoặc thực hiện các thao tác điều chỉnh/scan/chuyển giấy) để kiểm tra tính tái hiện của lỗi.
* **Kiểm tra kết nối và phần cứng liên quan:** 
  * Kiểm tra ngoại quan, vị trí các sensor, đường chuyển giấy, roller giấy đi qua.
  * Kiểm tra các kết nối dây, connector (ví dụ: connector main và engine) xem có bị lỏng, cắm chưa vào hết hoặc có dị vật hay không.
  * Thực hiện cross-check (chéo) các dây cáp/giao diện (như dây `WIRE PF INTERFACE`, `WIRE EXIT`, `WIRE SENSOR`) để loại trừ hoặc xác định nguyên nhân.
  * Kiểm tra thông mạch bằng đồng hồ điện hoặc kiểm tra các vị trí tiếp xúc của frame.
* **Thay thế thử nghiệm các linh kiện, cụm chi tiết hoặc bản mạch:**
  * Thay thế các cụm linh kiện nghi ngờ (như Housing Assy, GUIDE LIFT, dây WIRE FRONT, cụm DRIVE, v.v.).
  * Thay thế các bản mạch như Main, Engine, ISU Unit, hoặc bản mạch CTL.
* **Kiểm tra đường truyền, kết nối mạng hoặc thiết bị ngoại vi:**
  * Kiểm tra kết nối hoặc đường truyền giữa PC và máy in (truyền tín hiệu qua dây Lan hoặc cáp USB), kiểm tra xem PC tại vị trí line đó có bị đơ hoặc bất thường không.
* **Lấy và phân tích Log:** Lấy log hệ thống để gửi bộ phận kỹ thuật điện (`KTĐ`) phân tích.
* **Xử lý khi không tái hiện được lỗi:** Nếu lỗi không tái hiện sau khi đưa máy ra ngoài line (`lineout`) hoặc kiểm tra lại, tiến hành lập biểu không tái hiện, cho máy quay lại line tiếp tục theo dõi, hoặc xử lý như lỗi đơn phát.

### B6. Đối sách tạm thời và đối sách lâu dài khác nhau thế nào? Khi nào dùng mỗi loại?

- Thời gian: retrieval 65.96 s + tổng hợp 12.05 s = 78.01 s; item 16, nguồn riêng 2; `filtered_as_stale_count=0`.

Dựa trên tài liệu đính kèm, không đủ dữ kiện trong tài liệu để định nghĩa chi tiết sự khác biệt lý thuyết tổng quát cũng như thời điểm sử dụng cụ thể của đối sách tạm thời và đối sách lâu dài. 

Tuy nhiên, tài liệu có ghi nhận một số nguyên tắc và ví dụ thực tế liên quan đến các đối sách này như sau:

* **Nguyên tắc chung đối với đối sách tạm thời:** Nếu là đối ứng tạm thời, cần ghi rõ “tạm thời” và nêu rõ điều kiện để bỏ đối ứng đó trong tương lai [8].
* **Ví dụ thực tế về đối sách tạm thời và lâu dài trong tài liệu:**
  * Sự cố kẹt khí/sáng bạc: Đối sách tạm thời là tinh chỉnh tốc độ phun theo từng giai đoạn, giảm tốc khu vực hợp dòng/cuối dòng; đối sách lâu dài là cải tiến bổ sung insert thoát khí [2].
  * Sự cố dừng chuyền do lỗi định danh: Đối sách tạm thời là làm lại dây, cố định vị trí kết nối, tra keo nến; đối sách lâu dài là thay thế dây định kỳ và ghi lại lỗi vào sổ tay đồ gá [3].
  * Sự cố phần cứng/máy tính: Đối sách tạm thời là thay máy tính mới/dự phòng hoặc đổi port hỏng sang port khác; đối sách lâu dài có thể là thay ổ cứng mới, đặt bảng mạch mới thay thế và dự phòng [5, 6, 9], hoặc trong một số trường hợp liên quan đến lỗi hệ điều hành hoặc thiết bị điện tử không tái hiện lại được, tài liệu ghi nhận là "chưa có đối sách lâu dài" hoặc "không có đối sách lâu dài" [5, 12, 13].

### B7. Những thông số/ngưỡng nào thường phải kiểm tra đầu tiên khi máy báo lỗi?

- Thời gian: retrieval 93.72 s + tổng hợp 6.69 s = 100.42 s; item 16, nguồn riêng 7; `filtered_as_stale_count=0`.

Dựa trên tài liệu đính kèm, dữ liệu không đủ để xác định các thông số hoặc ngưỡng cụ thể nào thường phải kiểm tra đầu tiên khi máy báo lỗi. Do đó, không đủ dữ kiện trong tài liệu.

### B8. Các ngoại lệ hay gặp khiến một ca lỗi không đi theo kịch bản chuẩn là gì?

- Thời gian: retrieval 217.96 s + tổng hợp 6.83 s = 224.79 s; item 25, nguồn riêng 3; `filtered_as_stale_count=0`.

Dựa trên tài liệu đính kèm, các ngoại lệ hay trường hợp phát sinh khiến một ca lỗi không đi theo kịch bản chuẩn bao gồm:

* **Quá trình thao tác và điều chỉnh máy không theo chuẩn:**
  * Người thao tác (NTT) đặt bản thảo vào máy bị lệch khoảng 2mm so với trạng thái ban đầu, hoặc thay đổi bản thảo mới chất liệu là giấy nên nhanh hỏng hơn.
  * Kỹ thuật viên (KTV) khi điều chỉnh máy đã nhớ sai tiêu chuẩn kích thước (mặc dù có xác nhận tài liệu setup nhưng khi chỉnh lại nhớ nhầm).
  * KTV đang xác nhận hàng điều chỉnh máy thì phát sinh sự cố ở máy khác nên để hàng điều chỉnh ngay trên bàn máy, khiến IPQC tưởng nhầm là hàng OK và để lẫn vào thùng linh kiện OK.
  * Người thao tác không tuân thủ quy định đóng gói, gộp 4-5 linh kiện vào với nhau khi đóng gói hoặc do hàng ùn sau ăn ca nên tự ý thay đổi thao tác đóng gói để đẩy nhanh tiến độ.
* **Vấn đề về quy trình xử lý lỗi và dòng chảy sản phẩm trên chuyền:**
  * Máy lỗi ATL chưa được sửa chữa đã chíp MSI, do công nhân không kịp tact time nên vội chuyển máy sang công đoạn sau mà quên đặt giấy lỗi lên.
  * Hiện tượng nhầm lẫn linh kiện/thùng hàng: Lẫn mẫu lỗi vào linh kiện OK do test năng lực ở khu vực bàn thao tác nhưng không thu hồi thùng hàng test; hoặc nhân viên kho xuất nhầm mã sản phẩm do các mã tương tự nhau nằm cạnh nhau mà không kiểm tra kỹ phần đuôi số.
  * Lỗi do công nhân không tập trung kiểm tra kỹ vị trí PL liên quan do ba via phát sinh tập trung đột ngột, hoặc do vị trí lay-out hàng chưa kiểm và đã kiểm bằng băng dính bị đẩy tịnh tiến quá vạch dẫn đến LQC chỉ kiểm tra thành phẩm trong vạch chưa kiểm, làm lọt lỗi lưu hành.
* **Yếu tố từ linh kiện và thiết bị:**
  * Linh kiện phát sinh dị tật/biến dạng do dính khuôn tại phần core (khuôn quá tuổi, mòn chi tiết nhỏ ở vị trí khuất), hoặc linh kiện bị xô lệch và kẹt vào vách ngăn khi vận chuyển do đóng gói không cẩn thận.
  * Sự cố kỹ thuật phần cứng/khoảng cách giữa các bộ phận không đồng đều (ví dụ: khoảng cách giữa DP và ISU phía Rear và Front không bằng nhau khiến bản thảo bị lệch khi đi qua, gây lỗi U411).

### B9. Làm sao phân biệt lỗi do con người với lỗi do thiết bị?

- Thời gian: retrieval 147.92 s + tổng hợp 5.34 s = 153.26 s; item 15, nguồn riêng 2; `filtered_as_stale_count=0`.

Dựa vào tài liệu đính kèm, không có đủ dữ kiện để nêu cách phân biệt tổng quát giữa lỗi do con người với lỗi do thiết bị. 

Tuy nhiên, tài liệu có ghi nhận các trường hợp lỗi cụ thể do từng nguyên nhân gây ra như sau:
* **Lỗi do con người:** Ví dụ như người thao tác (NTT) bị mất tập trung do say xe nên không kiểm soát được linh kiện cũ và mới [2], dùng ngón tay đặt lệch/dùng 1 ngón tay kết nối dây do giữ máy không vuông góc [9], hay người thao tác vô tình va chạm thùng khi bê máy làm rách thùng CASE OUTER [11].
* **Lỗi do thiết bị/linh kiện:** Ví dụ như block trong khối dao tạo vòng bị mòn do sử dụng thời gian dài làm dao bị rơ và lệch vị trí [1], hoặc nhựa bị chảy ngược trong quá trình phun do check ring bị mòn không đóng kín (back flow) [5].

### B10. Bài học kinh nghiệm chung rút ra từ các ca lỗi đã xử lý là gì?

- Thời gian: retrieval 152.67 s + tổng hợp 5.1 s = 157.77 s; item 16, nguồn riêng 2; `filtered_as_stale_count=0`.

Dựa trên các tài liệu đính kèm, các bài học kinh nghiệm và biện pháp rút ra từ các ca lỗi bao gồm:

* Leader lấy các lỗi phát sinh làm kinh nghiệm và tiến hành xác nhận những vấn đề tương tự ở các vị trí khác để đào tạo cho những lần sau [5].
* Bổ sung lỗi vào lý lịch lỗi để đào tạo cho QC và công nhân thao tác [13].
* Bổ sung thêm vào tài liệu đào tạo lỗi phát sinh của phòng, thực hiện đào tạo định kỳ và đào tạo cho người mới để tránh tái diễn [12].
* Đối với các vấn đề kỹ thuật, cần phân biệt rõ giữa "lỗi APS không đổi được thứ tự" và "lý do cần đổi thứ tự", đồng thời nhận định rằng gốc rễ cần cải thiện lâu dài là hệ thống đăng ký lịch sử sản xuất phải phân biệt được nhiều Phantom [14].

### B11. Khi nào nên dừng máy ngay và khi nào có thể chạy tiếp khi có cảnh báo?

- Thời gian: retrieval 164.62 s + tổng hợp 9.13 s = 173.75 s; item 16, nguồn riêng 2; `filtered_as_stale_count=0`.

Dựa trên tài liệu đính kèm, hướng dẫn cụ thể về việc xử lý khi có bất thường/cảnh báo như sau:

* **Khi nào nên dừng máy ngay:** Nếu bạn nhận thấy bất kỳ tiếng động, mùi lạ hoặc hành vi bất thường nào, hãy **dừng ngay** xe tự hành AGV và điều tra nguyên nhân [7]. Ngoài ra, khi gặp bất thường, yêu cầu dừng chuyền (Stop Line) để xác nhận [9], [14].
* **Khi nào có thể chạy tiếp:** Sau khi đã kiểm tra, xử lý nguyên nhân, xác nhận không có vấn đề (hoặc được các bộ phận kỹ thuật/chất lượng đánh giá và cho phép như QA xác nhận đánh giá OK), máy có thể được cho quay trở lại line/chạy tiếp [4], [8], [10], [12], [16].

Bạn có cần tôi hỗ trợ thêm thông tin nào khác từ tài liệu không?

### B12. Dữ liệu nào cần thu thập trước khi bắt đầu phân tích nguyên nhân một ca lỗi?

- Thời gian: retrieval 160.35 s + tổng hợp 14.57 s = 174.92 s; item 17, nguồn riêng 3; `filtered_as_stale_count=0`.

Dựa trên tài liệu đính kèm, trước hoặc khi bắt đầu phân tích nguyên nhân một ca lỗi, các dữ liệu và bước cần thực hiện bao gồm:

* **Thu thập log tại đúng thời điểm phát sinh lỗi:** Việc này rất quan trọng vì nếu không lấy log đúng thời điểm, sẽ rất khó để phân tích và khẳng định nguyên nhân [11], [13].
* **Xác định hệ thống xảy ra lỗi:** Không được chỉnh sửa hoặc chạy tiếp theo cảm tính mà phải xác định rõ lỗi đang xảy ra ở hệ thống nào [17], đồng thời làm rõ lỗi thuộc dạng map sai hay false detection [11].
* **Phân chia lỗi theo chuỗi hệ thống chuẩn:** Luôn chia lỗi theo chuỗi: `BOP → MOM → APS → T_PARTS_OUT → Matecon/CTU → Opcenter → T_IF_PROD_RESULT → MES/R3` [17].

