# Vé: UX-AGENT-UI — verify nút Tải về / Hoàn tác thẻ đính kèm trên app thật

Lane: [NHÀ] OMP verify trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

User đã chọn **phương án A** (2026-10-03 ~16:10): sửa nút "Tải về" nhận biết
định dạng, không thêm nút mới. Muse code xong Phase A [VM] (commit `98a2a65`,
báo cáo `docs/phieu-viec/ket-qua/ux-agent-ui-a.md`, 11/11 test mới pass,
audit PASS).

## Việc OMP verify [NHÀ] (theo mục 4 của báo cáo)

1. Trong chat, gõ "tạo báo cáo tuan.docx: ..." (nội dung tùy ý): thẻ đính kèm
   hiện 3 nút; bấm **Tải về** → file `.docx` tải về **mở được ngay bằng Word**,
   nội dung đúng.
2. Gõ "sửa báo cáo tuan.docx: thêm ..." (file đã có): sau khi sửa, bấm
   **Hoàn tác** → file trở về đúng nội dung trước khi sửa (so bằng mắt hoặc SHA).
3. Tạo báo cáo `.md`: nút **Xem toàn văn** vẫn mở/thu gọn được trong thẻ;
   với `.docx`, nút Xem toàn văn **bị mờ** (không bấm được).
4. Ghi SHA index production trước/sau (phải không đổi).

## Tiêu chí ĐẠT

- Đủ 4 mục trên đều đúng như mô tả; không vỡ thẻ đính kèm loại khác.
- `compileall` + `pytest` các test liên quan + `cli audit` PASS trên Python 3.11.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
- Báo cáo kết quả vào `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (bổ sung mục
  verify [NHÀ]) rồi `xong-cho-duyet`.
