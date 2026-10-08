# Báo cáo audit độc lập — kết quả đo vé `SYNTH-MODEL-AB-HOME`

- **Người thực hiện:** OMP (thợ phụ) — máy nhà `h410asrock`, phiên 2026-10-08 ~09:07–09:20 +07.
- **Phạm vi:** việc phụ #2 do điều phối Muse giao sau verdict ĐẠT `SYNTH-MODEL-AB-HOME` (`9fc7e0e` ~09:04 + mốc CỔNG ĐÃ MỞ ~09:10).
  **Chỉ đọc + tính lại** — không sửa code, không ghi index, không merge `main`.
- **Nguồn đối chiếu:** báo cáo `docs/phieu-viec/ket-qua/synth-model-ab-home.md` (thợ agy)
  với dữ liệu thô tại máy nhà (ngoài Git): `C:/tmp/lsu-quality-rag-home/rows-synth-ab-a.jsonl`,
  `rows-synth-ab-b.jsonl`, `rows-synth-ab-c.jsonl`, `ket-qua-synth-ab-a/b/c.json`,
  `tien-trinh-synth-ab-a/b/c.log`, runner `do_rag_50_synth_ab.py`.
- **Cách làm:** đọc trực tiếp 3 × 50 hàng rows bằng Python, tính lại tổng/GPA từ trường `tong`,
  đếm chế độ theo trường `che_do` (nguồn chuẩn: `provider_validated` + `provider_validated_after_repair`
  = validated; hai fallback = fallback; hai not_called = not_called), rà từng lượt gọi trong
  `luot_goi_provider`, từng cảnh báo trong `nhat_ky_provider`, đối chiếu từng dòng bảng §2 của báo cáo.

## 1. Số tự tính lại từ dữ liệu thô (nguồn chuẩn = rows)

- Mỗi file đủ **50/50 hàng**; `ok=True` cả **150/150**; trình tự `stt` 1–50 đầy đủ cả 3 lượt.
- **Lượt A** (`ling-3.1-flash:free`): tổng **61,67/150, GPA 1,23**; chế độ **2 validated + 46 fallback
  + 2 not_called** (`Q0824, Q0668`); validated là `Q0689` (3,0) và `Q0677` (2,0), cả hai đều
  `provider_validated`, 1 lượt gọi, đúng model lượt A; câu =3,0: **4** (`Q0689, Q0695, Q1777, Q0680`);
  câu ≥2,0: **7** (thêm `Q0636, Q0674` cùng 2,33 và `Q0677` 2,0); trễ TB toàn câu **22,28s**,
  TB tổng hợp **11,54s** (tính lại từ `giay_cau`/`giay_tong` khớp tới 2 chữ số thập phân).
- **Lượt B** (`ling-3.0-flash-sante:free`): tổng **60,67/150, GPA 1,21**; chế độ **0 validated
  + 48 fallback + 2 not_called** (`Q0824, Q0668`); câu =3,0: **4** (cùng 4 mã như lượt A);
  câu ≥2,0: **6** (thiếu `Q0677` so với lượt A); trễ TB toàn câu **13,01s**, TB tổng hợp **2,96s**.
- **Lượt C** (`laguna-s-2.1-free`): tổng **60,67/150, GPA 1,21**; chế độ **2 validated + 46 fallback
  + 2 not_called** (`Q0824, Q0668`); validated là `Q0708` (`provider_validated_after_repair`, 1,0,
  2 lượt gọi — đúng là ca sửa thành công duy nhất) và `Q0652` (`provider_validated`, 1,67, 1 lượt gọi);
  câu =3,0: **4** (cùng 4 mã); câu ≥2,0: **6**; trễ TB toàn câu **15,74s**, TB tổng hợp **4,22s**.
- Ép tuyến đúng cả 3 lượt: cột `model_tra_loi` **50/50 cùng một model** đúng tên từng lượt,
  không lẫn model khác — tắt luân chuyển có hiệu lực thật.
- Ba file tổng `ket-qua-synth-ab-a/b/c.json` ghi đúng toàn bộ số trên (tổng, GPA, validated/fallback/
  not_called, =3/≥2, trễ hai loại, 0 lỗi kỹ thuật, credits 0,0, băm index khớp) — **không còn lỗi bộ đếm
  kiểu vé ROUTER** (vé này runner đã đếm đúng theo `che_do`).
- Index chỉ-đọc: cả 3 file tổng đều ghi SHA-256 trước = sau = `45eb0e07…b7c0`, md5 `23900967…`,
  size **2.942.201.856 byte**; kiểm lại file thật lúc audit vẫn đúng **2.942.201.856 byte**.

## 2. Đối chiếu tuyên bố của báo cáo (từng dòng bảng §2)

| Tuyên bố | Kết quả audit |
|---|---|
| Tổng/GPA ba lượt 61,67–1,23 / 60,67–1,21 / 60,67–1,21 | **KHỚP** (tính lại từ `tong`) |
| Validated 2 / 0 / 2 + mã câu (`Q0689, Q0677` / không có / `Q0708 repaired, Q0652`) | **KHỚP rows** (đúng `che_do`; Q0708 đúng `after_repair` 2 lượt gọi) |
| Fallback 46 / 48 / 46 + not_called 2 (`Q0824, Q0668`) cả 3 lượt | **KHỚP** |
| Câu =3,0: 4 cả ba lượt; câu ≥2,0: 7 / 6 / 6 | **KHỚP** (danh sách mã trùng: 4 câu 3,0 giống nhau cả 3 lượt) |
| Trễ TB toàn câu 22,28 / 13,01 / 15,74 + trễ tổng hợp 11,54 / 2,96 / 4,22 | **KHỚP** (tính lại từ `giay_cau`/`giay_tong`) |
| 0 lỗi kỹ thuật, $0 credits cả 3 lượt | **KHỚP cục bộ** (`ok` 150/150; model toàn hậu tố `:free`; hoá đơn thật ngoài dữ liệu máy) |
| Index chỉ-đọc SHA/md5/size khớp trước–sau | **KHỚP** (file tổng + file thật lúc audit) |
| Kết luận “validated thấp do CẢ nhóm free, sante kéo mạnh nhất (0/50)” | **KHỚP dữ liệu**: cả 3 con đứng một mình đều ≤2/50; sante 0/50 là thấp nhất |
| Thứ tự đề xuất 3.1 → laguna → sante (validated trước, GPA sau, trễ cuối) | **HỢP LÝ theo số**: 3.1 dẫn validated+GPA+≥2; laguna ngang validated, trễ tốt hơn; sante chót validated nhưng nhanh nhất |
| Quan sát “sante viết dài, 100% bản nháp dính `budget` hoặc `uncited`” | **KHỚP**: 15/15 bản nháp lượt B (lượt gọi 1) dính `budget` hoặc `uncited` |

## 3. Kiểm riêng tuyên bố “sante dính 429 sau câu 16”

- **ĐÚNG ở mức đọc thô, cần nói chính xác hơn một chút**: lượt B có **33/50 hàng** mang cảnh báo
  `rate_limited` trong `nhat_ky_provider` (so với 12 ở lượt A và 41 ở lượt C — 429 là hiện tượng
  chung của ngày đo, không riêng sante), nhưng riêng lượt B chúng **đóng khối liên tục từ `stt=17`
  tới hết `stt=50`** (33/34 câu cuối, chỉ trừ `stt=40` not_called) — trùng với mô tả “sau câu 16”.
- 15 bản nháp lượt B nằm gọn ở `stt=1–16` (trừ `stt=12` not_called); từ `stt=17` trở đi **0 bản nháp nào**,
  toàn bộ rơi về trích cục bộ với 0 lượt gọi provider — đúng kịch bản “gọi nhanh → bị giới hạn tốc độ →
  fallback an toàn giữ GPA”.
- Ghi nhận trung thực: với mật độ 429 dày cả 3 lượt (đặc biệt lượt C dính từ câu 1), so sánh GPA tuyệt đối
  giữa các lượt trong ngày này nên đọc kèm chú thích nhiễu mạng — nhưng thứ hạng validated (2/0/2)
  vẫn đứng vững vì validated chỉ đến từ các câu gọi thành công.

## 4. Lưu ý vận hành (trung thực, không chặn ĐẠT)

- Bốn câu 3,0 điểm (`Q0689, Q0695, Q1777, Q0680`) **giống hệt nhau ở cả 3 lượt** — điểm cao đến từ phần
  trích cục bộ/fallback ổn định, không phải từ model tổng hợp; validated mới là thước phân biệt model.
- Hai câu not_called (`Q0824, Q0668`) giống hệt cả 3 lượt — thiếu dữ liệu đầu vào, không liên quan model.
- Tốc độ đo bằng `giay_tong` TB (11,54 / 2,96 / 4,22s) là thời gian tổng hợp provider, không phải toàn câu;
  đọc nhanh dễ nhầm với `giay_cau` (22,28 / 13,01 / 15,74s) — báo cáo ghi đúng cả hai cột, audit xác nhận.
- File tổng + log chốt của vé này **đã đếm đúng**, khác hẳn lỗi bộ đếm ở vé ROUTER — cảnh báo bộ đếm
  của điều phối đã được agy thực hiện (`che_do` trực tiếp + reset health mỗi câu).

## 5. Kết luận audit

- Mọi số cốt lõi của báo cáo **khớp dữ liệu thô**: tổng/GPA, phân bố chế độ, mã câu validated/
  not_called, câu =3/≥2, trễ hai loại, ép tuyến một model, 0 lỗi kỹ thuật, index chỉ-đọc.
- Tuyên bố 429 của sante **có bằng chứng** (khối 33 câu từ `stt=17` tới hết, 0 bản nháp sau đó);
  tinh chỉnh diễn đạt: 429 là nhiễu chung cả ngày đo, ở lượt B nó tới dồn dập sau câu 16.
- Khuyến nghị pool (3.1 chính → laguna dự phòng 1 → sante đệm tốc độ) **suy ra đúng từ số đo**
  theo tiêu chí validated–GPA–trễ của vé.
- Audit chỉ-đọc: **không sửa code, không ghi index, không merge `main`**.
