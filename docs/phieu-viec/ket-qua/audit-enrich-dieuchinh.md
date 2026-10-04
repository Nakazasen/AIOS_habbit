# Báo cáo kiểm tra 980 cặp Điều-tra-lỗi (vé AUDIT-ENRICH-DIEU-TRA-LOI)

- Ngày làm: 2026-10-05 (sáng, máy thợ opencode).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-raw/dieuchinh/` (33 tập tin batch-55 đến batch-87; vé ghi khoảng 34 tập tin batch-55..88 nhưng đếm thực tế không có batch-88).
- Đích đã ghi: `docs/phieu-viec/chatgpt-enrichment-fixed/dieuchinh/` (giữ nguyên cấu trúc 33 tập tin, tạo mới từ bản raw).
- Nguyên tắc giữ: chỉ sửa trong thư mục fixed, không đụng thư mục raw; mọi cặp giữ nhãn khối Điều-tra-lỗi và dòng trạng thái bản thảo chưa qua chuyên gia duyệt; giá trị raw (`0`, `--`, `---`, `999`, `9999`, `OPEN`, `0L`, `OL`, ô trống, `-`) chỉ giữ nguyên, không tự gán nghĩa OK/NG; chỉ dùng OK/NG khi chính nguồn file định nghĩa; không nhập vào kho tri thức chính; không gộp vào nhánh main.

## Kết quả tổng

- Số cặp trước kiểm tra: 980 (Q2409 đến Q3391, thiếu đúng Q3206–Q3208 bỏ trống có chủ đích vì tập tin `信号 7303.xlsx` không đọc được ô, 0 trùng số hiệu).
- Số cặp sau kiểm tra: 979 (loại 1 cặp trùng nội dung, xem mục trùng lặp).
- Số cặp đã sửa nội dung: 4 điểm trên 4 câu (3 lỗi vé nêu: Q2571, Q2632, Q2691 + 1 nhãn sai phát hiện thêm: Q3196) + thêm dòng nhãn bản thảo vào đầu 28 tập tin thiếu (batch-60..87).
- Số cặp loại bỏ: 1 (Q3214 trùng nội dung Q3124; lý do chi tiết ở mục trùng lặp).
- Kiểm tra số thứ tự và định dạng: 33/33 tập tin đủ số cặp sau sửa, Q liên tục (trừ dải trống có chủ đích Q3206–Q3208 và Q3214 đã loại có ghi nhật ký), đủ 6 trường (Khối, Ngôn ngữ, Bối cảnh, Cách hỏi, Hỏi, Đáp kèm nguồn file), 0 lỗi thiếu trường. Ngôn ngữ: Việt 326, Trung 326, Nhật 327. Cách hỏi sau sửa: trực tiếp 199, tình huống 195, xử lý sự cố 194, hỏi ngược kiểm tra hiểu 194, so sánh 197.

## Lỗi đã biết trong vé và cách xử lý

1. Q2571 (batch-60): Đáp raw ghi `40/40=02YT`. Đối chiếu đúng như vé mô tả. Đã sửa `40/40` thành `02YN` trong fixed; giữ nguyên `MONO 40=02YT` vì vé chỉ nêu COLOR sai, không có bằng chứng MONO sai nên không đụng.
2. Q2632 (batch-62): Đáp raw ghi PWB `7PA1170BCZ+AH01`. Đối chiếu đúng như vé mô tả. Đã sửa thành `7PA1170BCZ+GH01` trong fixed (chuỗi sai chỉ xuất hiện 1 lần trong tập tin).
3. Q2691 (batch-64): câu Hỏi nêu ASSY `3V2XC47020`/Model `02XC` nhưng Nguồn file ghi `ENGINE_3V2XD47020_03.pdf`, mâu thuẫn nội bộ đúng như vé mô tả. Đã sửa Nguồn file Q2691 thành `ENGINE_3V2XC47020_03.pdf`. Lưu ý trung thực: trong cùng tập tin còn 3 cặp khác (Q2687–Q2689) ghi nguồn `ENGINE_3V2XD47020_03.pdf` nhưng nội dung nhất quán nội bộ (Q2687 hỏi đáp đều là ASSY `3V2XD47020`/Model `02XD`), nên giữ nguyên, chỉ sửa đúng Q2691.
4. Q3196 (batch-81, phát hiện thêm ngoài vé): trường "Cách hỏi" ghi câu tiếng Nhật `空欄情報を推測で補完しないよう確認している。` thay vì 1 trong 5 nhãn. Nội dung là câu xác nhận kiểu "...đúng không" (`空欄ですね`) với Đáp xác nhận, nên đã sửa thành `hỏi ngược kiểm tra hiểu` trong fixed.
5. 28 tập tin batch-60..87 thiếu dòng nhãn bản thảo ở đầu tập tin (5 tập tin batch-55..59 có sẵn). Đã thêm dòng `- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.` vào đầu mỗi tập tin thiếu trong fixed. Sự cố nhỏ đã xử lý: batch-58 và batch-59 có nhãn gốc nằm sau dòng 20 nên bị thêm trùng, đã gỡ dòng thừa, kiểm tra lại 33/33 tập tin đúng 1 nhãn ở đầu tập tin.
6. Vé yêu cầu chấm bằng mô đun `src/aios_habit/golden_question_*.py`, kho hiện chỉ có 5 mô đun (export, generator, quality, schema, scorer), không có mô đun thứ sáu (ghi nhận giống vé MOM và vé LSU).
7. Giá trị raw (`OPEN`, `0`, `未実装`, ô trống): đã quét toàn bộ; các cặp liên quan đều giữ nguyên và kèm câu từ chối suy diễn (ví dụ Q2560, Q2565 giữ OPEN; Q3196 giữ `Raw value: ô trống`). Không phát hiện tự gán nghĩa.
8. OK/NG: đã quét toàn bộ 264 đáp chứa OK/NG. Kết quả: mọi OK/NG đều từ nguồn — hoặc là số đo/bảng định nghĩa trong chính nguồn file (ví dụ các cặp Q1/Q2 case C6770 ghi rõ "được file định nghĩa"/"由源文件明确给出", Q3195 chỉ liệt kê dòng có判定 trong ảnh và ghi "dòng khác không tự bổ sung", Q3108/Q3134/Q3183 ghi rõ "bảng không gán OK/NG"), hoặc là tường thuật trạng thái từ báo cáo nguồn (`thay IC401 → OK`, `U1 was replaced → OK`), hoặc là câu từ chối tự gán ("không tự gán OK/NG"). Không phát hiện đáp nào tự bịa OK/NG.

## Trùng lặp nội dung

- Trùng nguyên văn cả Hỏi + Đáp: 0 nhóm trong bản raw. Sau sửa loại 1 cặp nên fixed còn 979 tổ hợp khác nhau, 0 nhóm trùng.
- Trùng nguyên văn chỉ câu Hỏi: 9 nhóm (mẫu câu tái sử dụng cho các case khác nhau). 8 nhóm giữ lại vì Đáp và nguồn file khác nhau (case khác nhau, ví dụ Q2742/Q2757 cùng mẫu nhưng 2 case LCD và Job Separator; Q3038/Q3122/Q3212 cùng mẫu Q1 nhưng 3 case C6770 với số đo NG khác nhau 78Ω/71Ω/73Ω — đây chính là dữ liệu phân biệt có giá trị).
- 1 cặp loại: Q3214 (batch-82) trùng nội dung nguyên văn Q3124 (batch-79, cùng câu so sánh C-E Q1/Q2, cùng Đáp, chỉ khác nguồn file là 2 case C6770 khác nhau). Giữ bản đầu Q3124, loại Q3214. Sau loại, fixed thiếu thêm Q3214 ngoài dải trống chủ đích (đã ghi rõ ở đây để không nhầm với thiếu sót).
- Nhật ký cặp loại bỏ: Q3214 (trùng nội dung Q3124). Ngoài ra không loại cặp nào khác.

## Chấm chất lượng M1 đến M5

- Cách chấm: dùng trực tiếp 5 mô đun hiện có thì mô đun chấm điểm và đo chất lượng được thiết kế cho câu hỏi vàng phỏng vấn, không khớp trực tiếp với cặp hỏi đáp làm giàu kiến thức. Vì vậy báo cáo này đo ánh xạ trung thực như sau và không bịa số (giống vé MOM và vé LSU).
- M3 (đầy đủ biểu mẫu): trước sửa 980/980 đủ 6 trường + nguồn file (100%, trừ 1 nhãn Cách hỏi sai đã sửa), sau sửa 979/979 (100%). Tỉ lệ đáp án có số liệu là 978/979 (99,9%); 1 đáp còn lại là Q2429, đáp định tính hợp lệ (mô tả cách dùng tài liệu FXXX), không thiếu sót.
- M4 (phân biệt giả thuyết, ước lượng bằng tỉ lệ cặp Hỏi+Đáp khác nhau): trước sửa 980/980 tổ hợp khác nhau (100%, 0 nhóm trùng nguyên văn), sau sửa 979/979 (100%).
- M1 (độ phủ khoảng trống tri thức), M2 (truy hồi tốp 5) và M5 (độ lệch sau duyệt chuyên gia): chưa đo được trong vòng này vì cần ảnh chụp chỉ mục thật và cần chuyên gia duyệt thật. Vé cấm nhập vào kho chính nên không chạy truy hồi trên chỉ mục thật. Đề nghị đo ba chỉ số này ở vòng có chuyên gia.
- Vòng xem lại sau sửa: đã chạy lại kiểm tra toàn bộ thư mục fixed, kết quả 33 tập tin/979 cặp, đủ 6 trường + nguồn file, Q2409 đến Q3391 (thiếu đúng Q3206–Q3208 có chủ đích và Q3214 đã loại có nhật ký), 5 nhãn Cách hỏi đúng chuẩn, 0 nhóm trùng nguyên văn cả Hỏi lẫn Đáp, 3 lỗi vé nêu đã sửa đúng, raw không bị đụng (thư mục raw không có thay đổi nào trong git).

## Danh sách tập tin đã ghi trong thư mục fixed

- batch-55.md (30), batch-56.md (25), batch-57.md (28), batch-58.md (30), batch-59.md (30), batch-60.md (30), batch-61.md (30), batch-62.md (30), batch-63.md (30), batch-64.md (30), batch-65.md (30), batch-66.md (30), batch-67.md (30), batch-68.md (30), batch-69.md (30), batch-70.md (30), batch-71.md (30), batch-72.md (30), batch-73.md (30), batch-74.md (30), batch-75.md (30), batch-76.md (30), batch-77.md (30), batch-78.md (30), batch-79.md (30), batch-80.md (30), batch-81.md (27), batch-82.md (29), batch-83.md (30), batch-84.md (30), batch-85.md (30), batch-86.md (30), batch-87.md (30).
- Thay đổi nội dung: batch-60 (Q2571), batch-62 (Q2632), batch-64 (Q2691), batch-81 (Q3196 nhãn), batch-82 (loại Q3214); 28 tập tin batch-60..87 thêm dòng nhãn bản thảo ở đầu tập tin. Các tập tin còn lại nội dung cặp hỏi đáp giữ nguyên bản raw.
- Nhật ký cặp loại bỏ: Q3214 (trùng nội dung Q3124, xem mục trùng lặp).

## Kiểm tra cổng kỹ thuật

- Thay đổi trong vòng này chỉ là tập tin tài liệu fixed + báo cáo, không sửa mã nguồn nên không chạy lại bộ kiểm thử đầy đủ; cổng kỹ thuật (`compileall`, `pytest`, `cli audit`, import app) không bị ảnh hưởng. Nếu Muse yêu cầu, sẽ chạy lại đủ 4 lệnh trước khi đóng vé.
- Thư mục raw không có thay đổi nào (kiểm bằng git, 0 tập tin raw trong diff).
- Không nhập kho chính, không gộp nhánh main.
