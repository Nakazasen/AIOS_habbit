# Chẩn đoán escalate cho-muse — vé KNOWLEDGE-DIGEST-HOME-R1 (máy nhà h410asrock)

Ngày: 2026-10-03 ~05:35 +07 (phát hiện ở poll mailbox-omp-poll, head 57d544e5).

## Kết luận: escalation HỢP LỆ, không vội
- Compare API 605a464b → 57d544e5: chỉ có đúng 1 commit (commit escalate của watcher lúc 05:32), không có commit mới nào của OMP.
- Watcher escalate sau 4 lần tự mở OMP (~10 phút/lần) không thấy mailbox tiến triển — đúng gate đã chốt (N=4 no-op → cho-muse).

## Blocker
- Cầu nối Gemini Web (127.0.0.1:8585) trả HTTP 405/502 từ 02:03 — đã ~3,5 giờ.
- Batch tóm tắt kẹt ở checkpoint 180/889 (R1 resume từ 92, tiến được tới 180 khi cầu nối còn thở).
- Vé R1 đã có sẵn cổng health + backoff (5/15/30/60 phút) + quy định "sau 2 giờ vẫn 405/502 thì dừng, watcher mở lại khi cầu nối khỏe" — escalate lần này chính là hệ quả của nhánh đó.

## Vì sao chưa viết R2 ngay
- R1 đã bao đúng cách xử lý 405; viết R2 lặp lại nội dung không thêm gì mới.
- Lane 3 (Nakazasen Router) cũng đang lỗi khóa cloud (ghi nhận ở verdict vé LLM-ENABLE-DO-NHA-R1) → không có lane dự phòng khả dụng.
- Đổi provider sang Grok/ChatGPT cho batch digest là quyết định của user (user dặn Grok để dành đối chứng sau) → không tự ý đổi.

## Quyết định
- Giữ mailbox ở `cho-muse`. Watcher KHÔNG tự mở lại OMP cho vé này cho tới khi có chỉ đạo mới từ Muse/user.
- Cần: user kiểm tra/khởi động lại cầu nối ở máy nhà, HOẶC user chốt đổi lane/provider cho batch digest.

## Bug watcher (ghi nhận, không sửa trong lượt này)
- Commit escalate 57d544e5 ghi trùng dòng `ghi_chu` ~20 lần vào trang-thai.md — watcher cần dedupe khi append ghi_chu.
