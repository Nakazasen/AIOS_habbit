# Vé B2 — Vòng phản hồi (feedback loop)

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Sau mỗi lần gợi ý, người dùng bấm đánh giá: đúng / sai / một phần. Khi lỗi được đóng,
bắt buộc nhập nguyên nhân thật + đối sách thật → cập nhật ngược vào kho dữ liệu.
Mục tiêu: ≥80% lượt gợi ý có đánh giá; tỉ lệ "đúng/một phần" tăng dần theo quý (có số đo).

## Việc cần làm
1. Schema: bảng `feedback` (gợi ý nào, đánh giá nào, khi nào, ai) + cập nhật record ca lỗi
   khi đóng (nguyên nhân thật, đối sách thật).
2. Luật cứng: không đóng được phiếu lỗi nếu chưa nhập nguyên nhân thật & đối sách thật.
3. UI: 3 nút đánh giá (đúng / sai / một phần) nằm trong câu trả lời chứa gợi ý
   (đúng luật 1 ô chat, không toolbar riêng).
4. Báo cáo tỉ lệ: % lượt gợi ý có đánh giá, tỉ lệ đúng/một phần theo quý.
5. Code + test trên VM.

## Tiêu chí ĐẠT
- Test: đóng phiếu thiếu nguyên nhân → bị chặn; bấm đánh giá → ghi log; báo cáo tỉ lệ chạy ra số.
- OMP verify trên máy nhà với DB thật.
