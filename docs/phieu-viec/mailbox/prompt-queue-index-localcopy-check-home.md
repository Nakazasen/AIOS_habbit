# VÉ XẾP HÀNG: INDEX-LOCALCOPY-CHECK-HOME (kiểm tra bản sao chỉ mục thiếu mảnh trong local_runs ở máy nhà)

- Mã vé: `INDEX-LOCALCOPY-CHECK-HOME`
- Role gợi ý: SMOL/TINY (kiểm tra chỉ-đọc + khuyến nghị)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/index-localcopy-check-home.md`
- Căn cứ: phát hiện §3 báo cáo `test-health-home.md` — bản sao `local_runs/workspace_chat_rag_v2_production/.../library.sqlite` ở máy nhà chỉ có **133.144 mảnh**, thiếu ~16.656 so với production đã kiểm chứng (149.800 mảnh, tệp ở `C:\AIOS_workspace_chat_rag_v2_production\...`).

## Việc phải làm (CHỈ ĐỌC với dữ liệu; không xoá, không ghi đè gì ở vé này)

1. Xác nhận số đếm của bản sao local (tài liệu/mảnh/vân tay) và thời điểm/đường nào đã tạo ra nó (dấu vết trong log/manifest nếu có).
2. Rà trong code + script + test: có đường nào (mặc định hay fallback) đọc bản sao `local_runs/` này thay vì production không — nếu có, liệt kê chính xác file/dòng và điều kiện kích hoạt. Đây là phần quan trọng nhất: bản sao thiếu chỉ nguy hiểm nếu có ai/có gì đo hay chạy trên nó.
3. Khuyến nghị chốt một trong hai hướng và ghi lý do: (a) làm tươi bản sao từ production (kèm cách làm an toàn + chi phí dung lượng/thời gian), hoặc (b) đánh dấu/loại khỏi mọi đường đọc mặc định. KHÔNG tự thực hiện ở vé này — điều phối duyệt hướng mới làm.

## Rào cứng

- Chỉ đọc; không đụng tệp production; không đụng index nào khác; không merge `main`.
