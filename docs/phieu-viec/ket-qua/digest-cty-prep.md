# Vé `DIGEST-CTY-PREP-HOME` — kiểm kê thành phẩm sổ tay cho máy công ty tái dùng

- Trạng thái: `xong-cho-duyet`; đủ 3 bảng theo tiêu chí vé, số liệu SHA khớp báo cáo R2.
- Máy làm: nhà `h410asrock` (Windows), 2026-10-06 04:28–04:45 +07 (giờ máy).
- Vé: `docs/phieu-viec/mailbox-opencode/prompt-queue-digest-cty-prep-home.md`. Nhánh `phieu-viec/rag-fix1`, không merge `main`.
- Nền: vé `KNOWLEDGE-DIGEST-HOME-R2` đã ĐẠT (báo cáo `docs/phieu-viec/ket-qua/knowledge-digest-home-r2.md`); vé `UPLOAD-SPLIT-DRIVE-HOME` đã xong (báo cáo `docs/phieu-viec/ket-qua/upload-split-drive-home.md`).

## 0. Nhận vé + cổng kiểm tra

- `git pull` nhận vé mới (trạng thái `moi`, prompt đúng vé `DIGEST-CTY-PREP-HOME`). 0 tập tin watcher tự mở trong `mailbox-opencode`, chưa chạm ngưỡng 4 lần nên không đặt `cho-muse`.
- Đặt `trang-thai.md` thành `dang-lam` ngay + đẩy lên, rồi đẩy mốc tiến độ sau kiểm kê.
- Toàn vé chỉ đọc: không sửa, không xóa thành phẩm; không nhúng lại; không ghi index hay cơ sở dữ liệu.

## 1. Bảng kê thành phẩm tái sử dụng được

| Tên thành phẩm | Vị trí máy nhà | Vị trí Drive / mã | Dung lượng | SHA-256 |
|---|---|---|---|---|
| Sổ tay tri thức (889 mục) | `C:\tmp\knowledge-digest-home\so_tay_tri_thuc.md` | chưa đưa lên Drive (nằm trong git? không — chỉ máy nhà; vé tiếp theo quyết có đưa hay không) | 1.374.070 B | `fd2b10e10f618e0f861fdd5db9ce8c30667c265d3a9c0f0ddbf70f55002cf1cd` |
| Manifest sổ tay | `C:\tmp\knowledge-digest-home\so_tay_tri_thuc.md.manifest.json` | — (đi kèm sổ tay) | 290 B | (nội dung ghi sẵn SHA trên; `doc_total=889`, `entry_count=889`, `draft=true`) |
| Checkpoint R2 (889/889) | `C:\tmp\knowledge-digest-home\digest_checkpoint.json` (`done=889`, `saved_local=2026-10-05 06:39:49`) | — | 1.438.726 B | — (tái tạo được từ index, không cần khớp SHA) |
| Cặp hỏi-đáp đã duyệt | `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (trong git) | — (trong git) | 1.267.666 B | `e242585724ba864c4b2131d1d0a3c072bf58508ded952f46c4c56189a3b3632a` |
| Khối `lsu` | `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` | `AIOS_Data/index-split-r5-backup/lsu/library.sqlite` (thư mục backup `1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`) | 1.155.637.248 B | `5982a4f1b99a455e89d30bb87095a3ab6f4617b50325a2da10c6d8f4b3c4eabb` |
| Khối `dieu_tra_loi` | `D:\Sandbox\AIOS_index_split_new\dieu_tra_loi\library.sqlite` | `AIOS_Data/index-split-r5-backup/dieu_tra_loi/library.sqlite` (cùng thư mục backup trên) | 1.643.761.664 B | `3bb7b10b5bb2d9345e6ba2baf95d6d6f25575639805504bda66284c36e569651` |
| Khối `mom` | `D:\Sandbox\AIOS_index_split_new\mom\library.sqlite` | `AIOS_Data/index-split-r5-backup/mom/library.sqlite` — link `https://drive.google.com/file/d/1Ew6pZTXL41hr-mn5x_Sm3qXU4X2oPBtf/view?usp=sharing` | 21.598.208 B | `9e796f79e20ee152cb48a56815149243fddfe165e0917f0303c2bf076840d14c` |
| Khối `tong_hop` | `D:\Sandbox\AIOS_index_split_new\tong_hop\library.sqlite` | `AIOS_Data/index-split-r5-backup/tong_hop/library.sqlite` — link `https://drive.google.com/file/d/1fcmGxVZ6zwWc_04JITDZPWikO7py27PK/view?usp=sharing` | 36.081.664 B | `4ad4bb35a2367eda4c0a78c0459ed6cf0b0d2d8f2b22f0c36685ba95dd76e73b` |
| Manifest khối tách | `D:\Sandbox\AIOS_index_split_new\domain_manifest.json` | `AIOS_Data/index-split-r5-backup/domain_manifest.json` — link `https://drive.google.com/file/d/1iAWjsdQHOgJzLJlZHOe_u14L0w4neTHB/view?usp=sharing` | 491.253 B | `54f916944c4f2a720300ae0845399d196b3053fe537558f68e2f9f7915531e88` |

Ghi chú về link: 2 khối lớn (`lsu`, `dieu_tra_loi`) Drive còn báo "không thể chia sẻ vào thời điểm này" nên chưa lấy được link riêng — vào bằng link thư mục backup `https://drive.google.com/drive/folders/1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`. Số liệu này chép từ báo cáo `upload-split-drive-home.md`, thợ không bịa.

## 2. Đối chiếu với báo cáo R2 (khớp hay lệch)

| Mục đối chiếu | Báo cáo R2 ghi | Kiểm lại máy nhà | Kết quả |
|---|---|---|---|
| Sổ tay: số mục | 889 mục `## ` = 889 tài liệu | đếm lại 889 mục | **Khớp** |
| Sổ tay: dung lượng | 1.374.070 B | 1.374.070 B | **Khớp** |
| Sổ tay: dòng đầu | `Bản thảo — chưa qua chuyên gia duyệt` | đúng dòng đầu | **Khớp** |
| Sổ tay: SHA manifest | `fd2b10e1…02cf1cd` | băm lại file khớp từng ký tự | **Khớp** |
| Checkpoint | 889/889 | `done=889` | **Khớp** |
| Cặp hỏi-đáp | (vé này ghi 3.392 cặp) | 3.392 dòng, mã `Q0001`–`Q3406` (thiếu đúng 14 mã có chủ đích: `Q639`–`Q648`, `Q3206`–`Q3208`, loại `Q3214`) | **Khớp** |
| Khối tách: tài liệu | 92 + 681 + 44 + 72 = 889 | manifest tách ghi đúng 4 số này | **Khớp** |
| Khối tách: chunk | 71.945 + 74.439 + 1.014 + 2.402 = 149.800 | manifest tách ghi đúng 4 số này | **Khớp** |
| Khối tách: byte + SHA | 5 số SHA trong báo cáo upload | băm lại 5/5 khớp 100% | **Khớp** |
| Index nguồn R2 (tham chiếu) | SHA `45eb0e07…b7c0`, 2.942.201.856 B | không đo lại (ngoài vé; máy công ty dùng index khác) | giữ nguyên để tham chiếu |

Kết luận: không có thành phẩm nào lệch hay thiếu. Không tự sửa gì.

## 3. Việc máy công ty CẦN làm tiếp

1. Tải 5 tập tin từ thư mục backup `index-split-r5-backup` về máy công ty (4 khối + manifest), rồi băm SHA-256 đối chiếu với bảng mục 1 — lệch byte nào thì báo, không dùng cố.
2. Đếm lại tài liệu/chunk trên index TẠM của máy công ty (số 889/149.800 là của máy nhà; index khác thì số khác — phải đo lại, không chép số).
3. Chạy lại vòng hỏi-đáp lane RAG trên index máy công ty (lane R2 đợt này bị giới hạn lượt từ câu 4 nên đáp án chỉ là trích cục bộ — chưa so được khi mạng khỏe; máy công ty phải đo lại khi quota hồi).
4. Quyết nơi đặt sổ tay + cặp hỏi-đáp trên máy công ty (hiện 2 món này chưa lên Drive; hoặc chép tay từ máy nhà, hoặc vé `DIGEST-CTY-RESUME` đưa lên Drive rồi tải về — Muse quyết).
5. Bổ sung 2 link chia sẻ còn thiếu (`lsu`, `dieu_tra_loi`) khi Drive mở lại — hiện vào bằng link thư mục backup vẫn được.

## 4. Việc máy công ty KHÔNG CẦN làm lại

1. Không cần tóm tắt lại 889 tài liệu — sổ tay đã bao phủ 100%, manifest SHA khớp.
2. Không cần kiểm lại 3.392 cặp hỏi-đáp — đã duyệt, đủ 6 trường, không trùng.
3. Không cần tách lại 4 khối index từ đầu — bản tách đã xong, đã sao lưu đủ 5 tập tin, SHA khớp.
4. Không cần chạy lại vòng hỏi-đáp lane sổ tay (548,4 giây/12 câu) — kết quả và đáp án từng câu nằm trong `probe-R2.json` máy nhà.
5. Không cần dựng lại checkpoint R2 — `digest_checkpoint.json` 889/889 còn nguyên.

## 5. Ghi chú trung thực

- 5 mục sổ tay rỗng phần chủ đề + ý chính được giữ nguyên có chủ đích (4 tài liệu gốc quá ngắn 11–39 ký tự + 1 PDF quét nhiễu) — máy công ty không cần sửa lén.
- 5/12 câu lane sổ tay báo "chưa đủ dữ kiện" là lỗ hổng phạm vi đã ghi trong R2 (sổ tay hiện là tóm tắt ca lỗi, thiếu mảng quy trình/định nghĩa) — để Muse quyết vòng cải thiện, vé này không tự thêm.
- Vé này không đụng ổ D, không ghi index/cơ sở dữ liệu, không chạm mã nguồn (`git diff --stat` chỉ có báo cáo + trạng thái).

## 6. Đã KHÔNG làm (đúng rào vé)

- Không sửa, xóa, di chuyển thành phẩm; không nhúng lại; không ghi index production.
- Không nhập sổ tay vào kho; không gắn nhãn kiến thức đã duyệt; không nối sổ tay vào luồng trả lời chính.
- Không merge `main`; chỉ commit báo cáo + `trang-thai.md` lên `phieu-viec/rag-fix1`.
