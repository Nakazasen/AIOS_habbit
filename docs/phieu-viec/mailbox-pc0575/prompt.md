# Vé P3 — Chẩn đoán app Streamlit báo "0/171 tài liệu sẵn sàng" (KDTVN-PC0575)

## Hiện tượng (user báo 2026-09-29 ~16:46 +07, kèm screenshot localhost:8501)

App chat hiển thị:

> 📚 Đã chuẩn bị xong 0/171 tài liệu (0%) · Tài liệu sẵn sàng để tìm kiếm: 0/171
> · Có 68 tài liệu cần xử lý. Tìm kiếm đầy đủ chưa sẵn sàng.

Trong khi P2 (vừa nghiệm thu ĐẠT, commit `07061b70d21b`) đã chứng minh production
index trên chính máy này hoạt động: 107.331 chunk có embedding ONNX, smoke B7b
exit 0, B1/B2/B3/B5 pass.

## Nhận định sơ bộ của Muse

Engine retrieval OK, vấn đề nằm ở tầng app UI: hoặc app đang đọc sai file sqlite
(không phải production index đã verify), hoặc bảng trạng thái document của app
lệch với số chunk thực tế trong index.

## Nhiệm vụ OMP — CHỈ ĐỌC, CẤM GHI INDEX, CẤM EMBED trong vé này

1. Xác định app Streamlit (localhost:8501) đang đọc file sqlite nào: kiểm tra
   config, biến môi trường, hoặc code khởi tạo đường dẫn DB.
2. So sánh với đường dẫn production index đã verify P2:
   `local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
   (SHA-256: `062EC090644FB4EC09D2FB6388F3175E988E48D63061B04E6C27BBED334EF8CA`).
3. Trong DB app đang đọc, kiểm tra bảng documents/manifest: tại sao readiness =
   0/171? Đếm số chunk thực tế có embedding ONNX trong DB đó.
4. Làm rõ "68 tài liệu cần xử lý": là thật sự chưa có embedding, hay chỉ là
   status tracking sai? (Đối chiếu với 25.813 chunk `retrievable=0` đã biết ở P2 —
   chunk không retrieve được không tính là "cần xử lý".)
5. Nếu app đọc sai DB: sửa config trỏ đúng production index, restart app,
   chụp màn hình dòng readiness sau khi sửa.
6. Ghi báo cáo vào `docs/phieu-viec/ket-qua/p3-bao-cao.md`, gồm: nguyên nhân gốc,
   đã sửa gì (file nào, dòng nào), screenshot trước/sau, số tài liệu sẵn sàng mới.

## Tiêu chí ĐẠT

- App báo số tài liệu sẵn sàng > 0 và khớp với production index đã verify,
  HOẶC báo cáo chứng minh 68 tài liệu thật sự chưa được embed (khi đó việc embed
  là ticket tiếp theo, thuộc OMP, không làm trong vé này).

## Ràng buộc

- Không ghi bất kỳ byte nào lên production index trong vé này.
- Không chạy embed.
- Không merge `main`.
- Nếu screenshot của user thực ra chụp trên máy nhà (không phải KDTVN-PC0575),
  ghi rõ trong báo cáo và dừng vé.

## Xong việc

OMP cập nhật `docs/phieu-viec/mailbox-pc0575/trang-thai.md`:
`Trạng thái: \`xong-cho-duyet\``, `Ticket hiện tại: p3-app-readiness`,
đường dẫn báo cáo, commit SHA. Cron Muse sẽ review.
