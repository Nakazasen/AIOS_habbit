# VÉ: SYNTH-CLAIMBUDGET-APPLY-HOME (áp chính thức nới ngân sách luận điểm cho câu hỏi chẩn đoán/tra cứu + đo xác nhận)

- Mã vé: `SYNTH-CLAIMBUDGET-APPLY-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-claimbudget-apply-home.md`
- Căn cứ: vé chẩn đoán `SYNTH-CLAIMBUDGET-DIAG-HOME` (đã verdict ĐẠT): đo biến thể ngân sách ×2 (tối đa 10 luận điểm) trên 50 câu cho thấy số lượt vi phạm vượt ngân sách giảm 62 → 3, số câu qua kiểm định tăng gấp đôi 2 → 4, điểm tổng 62,65 → 63,51, và đọc tay 5 đáp án thay đổi xác nhận không phát sinh luận điểm bịa. Trong mã nguồn đã có tiền lệ nới ngân sách lên 10 cho dạng câu hỏi kiến trúc/tích hợp; vé này mở rộng tiền lệ đó cho dạng chẩn đoán và tra cứu kỹ thuật — là dạng câu hỏi chính của sổ LSU.

## Việc phải làm

1. **Áp thay đổi vào mã nguồn:** trong khâu lập kế hoạch tổng hợp, nâng ngân sách luận điểm hiệu dụng lên 10 cho dạng câu hỏi `diagnosis` và `lookup` (theo đúng cơ chế tiền lệ hiện có cho `architecture`/`integration`). Không đổi ngân sách mặc định cho các dạng khác. Kèm test khẳng định: dạng chẩn đoán/tra cứu nhận ngân sách 10; dạng khác giữ nguyên.
2. **Đo xác nhận 50 câu** bằng runner hiện hành, model chính Ling 3.1 Flash free, CPU-only: nộp file kết quả thô + bảng so sánh với hai mốc đã có (ngân sách 5: 2 validated / 62,65 điểm; lượt chẩn đoán ngân sách 10: 4 validated / 63,51 điểm). Nếu kết quả xác nhận lệch hẳn khỏi mốc chẩn đoán (validated < 4 hoặc điểm giảm), khai rõ và đề xuất hoàn lui — không giấu.
3. **Nghiệm thu dùng thật trên giao diện** (CPU-only, commit HEAD ghi rõ): 3 câu chuẩn trong sổ LSU phải ra đáp án trọn vẹn trên giao diện; nếu vé mở cổng `UI-LOCALONLY-SYNTH-OPEN-HOME` đã xong trước vé này, ít nhất 1 câu phải là đáp án do model tổng hợp phục vụ (ghi rõ tên model ở phần nguồn gốc đáp án); chụp ảnh chứa đáp án trong khung hình.

## Rào cứng

- Chỉ đụng đúng điểm lập kế hoạch ngân sách + test; không nới các cổng kiểm định khác (trích dẫn, số liệu nguyên văn, độ phủ vẫn giữ nguyên độ nghiêm). Không ghi chỉ mục (băm trước/sau phải khớp). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần; kích thước tệp trong báo cáo lấy bằng lệnh liệt kê tệp thật.
