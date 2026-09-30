# Vé B0-FORM — Form nhập liệu chuẩn Bước 0

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Bước 0 yêu cầu: không còn file rời theo FY; mọi báo cáo mới nhập trực tiếp theo form
chuẩn với 12 trường: Model / Line / Công đoạn / Tên lỗi / Error code / Hiện tượng /
Nội dung điều tra / Nguyên nhân / Đối sách / Bộ phận PT / Ngày phát sinh – ngày đóng /
Link báo cáo.

## Việc cần làm
1. Xây form nhập liệu ghi thẳng vào DB Bước 0 (không qua file trung gian).
   UI nằm trong vùng trả lời của chat (đúng luật: 1 ô nhập + 1 vùng trả lời), không thêm toolbar/nút riêng.
2. Validate: 5 trường bắt buộc (error code, hiện tượng, nguyên nhân, đối sách, công đoạn)
   không được trống; ngày đóng ≥ ngày phát sinh; error code đối chiếu từ điển (vé B0-DICT).
3. Chống trùng: cùng (model, line, error code, ngày phát sinh) → cảnh báo trùng, không cho nhập đúp.
4. Code + test trên VM; test dùng fixture trích từ dữ liệu thật, gắn mác SIMULATED_* nếu mô phỏng.

## Tiêu chí ĐẠT
- Nhập 1 báo cáo mới qua form → đủ 12 trường trong DB, không sinh file rời.
- Test: thiếu trường bắt buộc → bị chặn; trùng → cảnh báo; error code lạ → cảnh báo (không chặn).
- OMP verify trên máy nhà: form chạy được với DB thật, nhập thử 3 ca thật không lỗi.
