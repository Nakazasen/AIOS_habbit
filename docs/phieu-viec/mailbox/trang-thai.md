# Trạng thái mailbox

- Trạng thái: `xong`
- Ticket hiện tại: `INDEX-SWITCH-APP` — [NHÀ] chuyển app sang 3 khối lĩnh vực + bật định tuyến (junction sang ổ D, không tốn chỗ ổ C). Prompt: `docs/phieu-viec/mailbox/prompt.md` (copy nguyên văn `prompt-queue-index-switch-app.md`).
- `hang-cho`: hết.
- `commit`: `717ffdc`
- `bao_cao`: `docs/phieu-viec/ket-qua/index-switch-app.md`
- `ghi_chu`: 2026-10-04 00:54:19 xong. 4 junction, đếm khớp manifest, badge LSU/MOM/Điều tra lỗi đã hiện, câu mơ hồ ghi khối đã chọn, không vào tong_hop. Rollback tắt cờ trả lời kho cũ, trạng thái cuối cờ BẬT. SHA kho cũ không đổi. Câu mẫu C6770 trên app thường bị action tra cứu ca lỗi bắt trước badge — ghi trong báo cáo.

- `ghi_chu` (verdict Muse 2026-10-04 ~00:58 +07): **ĐẠT** (commit `717ffdc`). 5/5 tiêu chí vé: 4 junction đọc được, đếm khớp manifest (92/71.945, 681/74.439, 44/1.014, 72/2.402); badge đúng 3 khối LSU/MOM/Điều tra lỗi, câu mơ hồ ghi rõ khối đã chọn; không câu nào vào tong_hop; rollback đã thử (tắt cờ → về kho tri_thuc cũ bình thường), trạng thái cuối cờ BẬT; SHA/size/mtime tri_thuc `45eb0e07…65b7c0` không đổi. Lưu ý: câu mẫu C6770 trên app thường do action tra cứu ca lỗi (AIOS_FEATURE_CHAT_ACTION=1) trả lời đúng mã nên không hiện badge; định tuyến đã chứng minh chạy đúng khi tắt action — ưu tiên action/router để user chốt. hang-cho đã hết → mailbox `xong`. Merge vào main CHƯA làm: duyệt 2026-09-29 chỉ cover chuỗi E cũ, chờ user duyệt mới cho trạng thái branch hiện tại.
