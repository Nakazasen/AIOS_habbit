# Vé: UX-INTERVIEW-UI — verify UI phiên phỏng vấn trong chat trên app thật

Lane: [NHÀ] OMP verify trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

User đã gật phương án UI (2026-10-03 ~16:10). Muse code xong Phase A [VM]:
backend giữ nguyên, chỉ nối UI vào (commit `4b6b4c2`, báo cáo
`docs/phieu-viec/ket-qua/ux-interview-ui.md`, 24/24 test mới pass, audit PASS).

## Việc OMP verify [NHÀ] (theo mục 4 của báo cáo)

1. Mở app, gõ "mở phiên phỏng vấn F000" (mã lỗi thật trong kho): phiên mở ra,
   **câu hỏi 1 hiện kèm các ô trả lời ngay dưới**, không chuyển màn hình.
2. Gửi đáp án thiếu (bỏ trống cơ chế gây lỗi): app **nhắc "Còn thiếu phần
   nguyên nhân / bằng chứng"** và không qua câu mới.
3. Điền đủ → qua câu tiếp theo; trả lời hết → app báo **"Đã lưu nháp chờ duyệt"**;
   kiểm tra `local_cases/staging_enrichment.sqlite` có đáp án mới,
   `reviewer_status` = `cho_chuyen_gia_phan_hoi`.
4. Gõ "tiếp theo nên làm gì?" (mở sổ tri thức trước): mỗi gợi ý có **3 nút**
   👍/😐/👎; bấm 👎 → hiện 3 ô ngay dưới gợi ý; bỏ trống 1 ô rồi lưu → bị chặn;
   điền đủ → ghi nhận.
5. Chê 1 gợi ý "sai", rồi hỏi lại việc tương tự: thấy dòng
   **"💡 Lưu ý: tình huống này từng bị chê vì …"** đứng trước gợi ý.
6. Gõ "báo cáo cải thiện gợi ý": thấy dòng **"📉 Tỉ lệ lặp lại lỗi"**.
7. Ghi SHA index production trước/sau (phải không đổi).

## Tiêu chí ĐẠT

- Đủ 6 mục trên đều đúng như mô tả; không vỡ luồng chat cũ.
- `compileall` + `pytest` các test liên quan + `cli audit` PASS trên Python 3.11.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
- Báo cáo kết quả vào `docs/phieu-viec/ket-qua/ux-interview-ui.md` (bổ sung mục
  verify [NHÀ]) rồi `xong-cho-duyet`.
