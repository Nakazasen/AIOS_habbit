# Vé B1-FEAT — Bước 1 thành tính năng hoàn chỉnh

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Lõi RAG chạy được (chuỗi E/TOOL xong ở tầng code+test). Còn thiếu để thành tính năng
Bước 1: nhập error code / hiện tượng → Top 3–5 lỗi tương tự kèm nguyên nhân & đối sách
đã áp dụng, có link báo cáo gốc; thời gian <1 phút; AI không hỏi ngược lại.

## Việc cần làm
1. Nối RAG với DB ca lỗi Bước 0 (15.707 ca thật + 262 nguồn LSU sau vé GPU-262).
2. Render trong vùng trả lời: top 3–5 thẻ, mỗi thẻ gồm hiện tượng, nguyên nhân, đối sách,
   link báo cáo gốc (mở được). Có error code → trả lời ngay, không hỏi ngược.
3. Đo latency đầu-cuối <1 phút trên máy nhà (sau fix coverage gate đã ở mức ms).
4. Code + test trên VM: 5 error code thật → đủ top 3–5 + link gốc mở được.

## Tiêu chí ĐẠT
- OMP verify trên máy nhà: nhập 5 error code thật → mỗi cái ra top 3–5, link gốc đúng,
  thời gian <1 phút, không bị hỏi ngược.
