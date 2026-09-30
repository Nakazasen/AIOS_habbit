# Kế hoạch làm hết dich-den-du-an.md (lập 2026-09-30)

File đích: `docs/dich-den-du-an.md` (branch `phieu-viec/rag-fix1`).
Mỗi Bước = 1+ vé có tiêu chí ĐẠT đo được. Vé kỹ thuật xong ở tầng code+test chưa phải
vé ĐẠT — ĐẠT cần verify độc lập (Muse) trên bằng chứng thật.

## Quy ước lane
- **[VM]** = Muse code+test trên VM; OMP KHÔNG làm, chỉ verify trên máy nhà với dữ liệu
  thật khi Muse báo code xong (ghi rõ commit). Khi vé [VM] thành vé hiện tại, OMP chờ.
- **[NHÀ]** = OMP làm toàn bộ trên máy nhà (GPU/nhúng/giữ index/đo trên dữ liệu thật).
- **[NGƯỜI DÙNG]** = cần người dùng công ty tham gia (dùng thử, vận hành); vé là chuẩn bị + ghi nhận.

## Thứ tự hàng chờ (đã cập nhật vào mailbox máy nhà)

| # | Vé | Lane | Làm gì | Xong khi |
|---|---|---|---|---|
| 0 | GPU-262 (đang chạy) | NHÀ | Nhúng GPU 52.979 chunk 262 nguồn LSU + đóng gói delta cho PC0575 | Đủ 262 ID, fingerprint 016c5255…, delta có manifest |
| 1 | LSU-1 | NHÀ | Pipeline Bước 0–5 trên list LSU thật | Exit 0, đủ Bước 0→5, số liệu thật |
| 2 | don-canary | NHÀ | Xóa kho canary 2,4GB sau verify SHA production | SHA production nguyên vẹn, đã xóa |
| 3 | f3b-backfill | NHÀ | Backfill trường fix (gate đang mở 56,7%) | Gate đóng hoặc có số đo mới |
| 4 | date-map | NHÀ | Map cột ngày thật X/Y | Xu hướng/tái phát tính được theo ngày phát sinh |
| 5 | B0-FORM | VM | Form nhập liệu chuẩn 12 trường, ghi thẳng DB | Nhập mới không qua file rời; validate + chống trùng |
| 6 | B0-DICT | VM | Từ điển thuật ngữ + số hóa bảng mã lỗi còn thiếu | % mã lỗi tra được có số đo |
| 7 | B0-MEASURE | NHÀ | Đo ≥90% đủ 5 trường bắt buộc | Có % thật; <90% → danh sách backfill |
| 8 | B1-FEAT | VM | Bước 1 thành tính năng: nhập error code → top 3–5 + nguyên nhân/đối sách/link gốc, <1 phút, không hỏi ngược | Verify 5 error code thật đạt |
| 9 | B2 | VM | Vòng phản hồi: đánh giá đúng/sai/một phần; chặn đóng phiếu thiếu nguyên nhân thật | Luật chặn chạy đúng; báo cáo tỉ lệ có số |
| 10 | B3 | VM | Cây điều tra 4M + Why-Why, checklist, xuất file đúng format báo cáo công ty | 3 hiện tượng thật ra cây + file đúng format |
| 11 | B4 | VM | Xu hướng theo model/line/công đoạn/loại giấy/máy cấp thấp/jig + cảnh báo ngưỡng + báo cáo định kỳ (tái dùng engine JIG) | Biểu đồ + cảnh báo + báo cáo chạy trên DB thật |
| 12 | B5 | VM | Phân loại tự động (accuracy ≥80%) + cảnh báo tái phát "N lần, đối sách X" | Số đo accuracy thật; demo 3 lỗi mới đúng |
| 13 | J1-CSV | VM | JIG: nhập cả file CSV + chọn biểu đồ + tự gửi mail kèm biểu đồ đã setup | Verify trên log jig thật |
| 14 | J1-RT | VM+cty | JIG realtime: spec API + prototype phát lại dữ liệu thật + danh sách yêu cầu hạ tầng | Spec + prototype chạy; hạ tầng chờ công ty |
| 15 | J2 | NHÀ+người dùng | JIG: checklist xác nhận chức năng trước khi đưa thử | Biên bản PASS/FAIL trên dữ liệu thật |
| 16 | J3 | NGƯỜI DÙNG | JIG: dùng thử, thu thập cải tiến | Biên bản + backlog được xác nhận |
| 17 | J4 | NHÀ+người dùng | JIG: chạy thử nghiệm, đo đúng/sai/nhầm/sót cảnh báo | Báo cáo có số đo thật |
| 18 | J5 | NGƯỜI DÙNG | JIG: chạy thật, vận hành chính thức | Checklist vận hành được xác nhận |

## Đối chiếu vào file đích
- Bước 0: vé 1 (LSU-1) + 5, 6, 7 → điều kiện ≥90% đủ 5 trường; form chuẩn; từ điển.
- Bước 1: vé 0 (dữ liệu vector) + 8 → top 3–5 + link gốc, <1 phút, không hỏi ngược.
- Bước 2: vé 9 → log đánh giá + luật chặn đóng phiếu; ≥80% lượt có đánh giá.
- Bước 3: vé 10 → cây 4M + Why-Why + checklist + file đúng format báo cáo.
- Bước 4: vé 4 + 11 → biểu đồ xu hướng + cảnh báo ngưỡng + báo cáo định kỳ tự động.
- Bước 5: vé 3 + 12 → phân loại ≥80% + cảnh báo tái phát ngay khi nhập.
- JIG Bước 1: vé 13 (phần tay còn thiếu) + 14 (realtime/API/server).
- JIG Bước 2–5: vé 15–18 (các pha validation, cần người dùng công ty).

## Lưu ý trung thực
- Vé [VM] Muse làm song song, có thể xong code trước khi tới lượt trong hàng chờ;
  khi tới lượt, OMP chỉ verify trên dữ liệu thật.
- Vé J2–J5 không thể xong bằng kỹ thuật đơn thuần — cần người dùng công ty tham gia
  (dùng thử, chạy thử, chạy thật). Vé ở đây là chuẩn bị + ghi nhận trung thực.
- Không merge `main` khi chưa có đèn xanh của user; không ghi đè production khi chưa
  backup + verify.
