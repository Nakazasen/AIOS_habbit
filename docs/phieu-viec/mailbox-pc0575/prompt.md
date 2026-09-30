# Ticket dieutra-banner-0494 — Điều tra: banner "0/494 tài liệu" vẫn hiện sau khi xóa/tắt hết nguồn

## Hiện tượng (user báo 2026-09-30 ~12:10 +07, có ảnh chụp màn hình)
- User đã xóa 494 nguồn tạm trong cuộc trò chuyện (mục "Nguồn tạm" hiện "Chưa có nguồn nào").
- Trong sổ còn "494 tài liệu · 0 đang bật" (tất cả đã tắt).
- Banner vẫn hiện: "Đã chuẩn bị xong 0/494 tài liệu (0%) · Tài liệu sẵn sàng để tìm kiếm: 0/494 · Việc chuẩn bị đang tạm dừng. Bấm 'Tiếp tục chuẩn bị' để chạy lại."

## Đầu mối từ code (Muse đã tra cứu trên VM, cần kiểm chứng trên máy thật)
- `src/aios_habit/workspace_chat_app.py` dòng ~4657:
  `tracked_prep_sources = enabled_ctx_sources if enabled_ctx_sources else ctx_all_sources`
  → khi không còn nguồn nào đang bật, banner chuyển sang theo dõi TẤT CẢ nguồn, nên hiện 0/494 thay vì ẩn đi.
- Nút "Tiếp tục chuẩn bị" gọi `on_resume_preparation` → `resume_workspace_chat_source_preparation(tracked_prep_sources)` → có nguy cơ enqueue cả 494 nguồn đã tắt để embed trên máy CPU-only.

## Việc cần làm (CHỈ điều tra, KHÔNG sửa)
1. Refresh trang (F5), rồi restart app: banner còn hiện không? (loại trừ session Streamlit cũ)
2. Chụp màn hình banner + mục "Quản lý tài liệu" sau refresh/restart.
3. Tìm file ledger `workspace_chat.sqlite` trong thư mục runtime của app, mở bảng ledger chuẩn bị nguồn: đếm có bao nhiêu row ở trạng thái pending/processing thuộc 494 nguồn này.
4. **TUYỆT ĐỐI KHÔNG bấm "Tiếp tục chuẩn bị" / "Thử chuẩn bị lại"** trong lúc điều tra (tránh enqueue 494 tài liệu lên máy CPU).
5. Báo cáo: `docs/phieu-viec/ket-qua/dieutra-banner-0494.md` — từng bước đã làm, kết quả quan sát, ảnh chụp màn hình, kết luận banner có tái hiện sau restart không.

## Cấm
- Không sửa code, không bấm nút chuẩn bị lại dưới mọi hình thức.
- Không merge `main`. Không đụng ổ D máy nhà.
