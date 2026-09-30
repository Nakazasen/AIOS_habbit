# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: hodap-lsu-loi
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `e9e5d48` (mốc 2 — ghi tiến độ Pha 2)
`bao_cao`: `docs/phieu-viec/ket-qua/hodap-lsu-loi.md` (chưa tạo)
`ghi_chu`: 2026-09-30 14:41 +07 — Pha 2 tiến triển thật: 9/34 nguồn đã ready (gồm `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` và biên bản họp lỗi Beam径NG kỳ 2); nguồn từng "failed" đã được app tự chữa qua nút "Thử chuẩn bị lại". Worker ONNX vẫn chạy nền, ETA phần còn lại ~15:45. Chưa hỏi mẫu vì còn 2/3 biên bản lỗi đang chuẩn bị.

Mốc:
- ghi chú: 2026-09-30 14:41 +07 — 9/34 nguồn ready (LSU pptx + biên bản lỗi kỳ 2 + 7 tài liệu dữ liệu); nguồn "failed" đầu tiên đã tự chữa thành ready; đang chờ 2 biên bản lỗi còn lại rồi chạy bộ 6 câu hỏi mẫu.
- 2026-09-30 14:16–14:41 +07 — Pha 2 (nối tiếp): xác minh worker `bge_subprocess_worker` (ONNX fp32, PID 2764) nhúng thật; đo tốc độ sống 0,31–0,35 chunk/s (khớp 0,32 chunk/s của Pha 1); xếp 5 nguồn trọng tâm (trai LSU pptx + 3 biên bản họp lỗi `.msg`) lên ưu tiên `interactive` bằng `scratch/hodap_promote_priority.py` (dry-run + apply) để kiểm chứng sớm; kết quả: `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` + `DATA_Matome.xlsx` + biên bản lỗi kỳ 2 đã ready; nguồn `SRC-8A0501D5` từng `failed` (`bge_worker_staged_commit_invalid_response` — lỗi tạm thời lúc worker khởi động lại) đã tự chữa thành `ready` sau khi bấm nút "🔄 Thử chuẩn bị lại" của app. [commit `e9e5d48`]
- 2026-09-30 14:06–14:16 +07 — Đo lại hiện trạng trước khi làm tiếp: worker `bge_subprocess_worker` (PID 2764) khởi động 14:03:55 đang nhúng tài liệu `wsc-a1a89391` (tổng_hợp_dữ_liệu_dán_tape.xlsx); 35 nguồn đang bật cho hội thoại `CONV-9C730D76` (24 xlsx + 8 pptx + 3 msg), 15 lựa chọn cũ trỏ nguồn tạm đã xóa vẫn nằm trong file chọn (vô hại); ledger 1 failed (`SRC-8A0501D5` — lỗi `bge_worker_staged_commit_invalid_res...`, sẽ điều tra) + 1 processing + 33 pending; ước tính 19 tài liệu duy nhất ≈ 1.993 chunk theo `content_text` → ETA ~2h ở 0,32 chunk/s. [commit `adbb0e9`]
- 2026-09-30 13:35 +07 — Nhận vé (watcher mở 1/4 lúc 13:34:15), `git pull` HEAD = `53b900d` → nhánh cập nhật. [commit `45c992e`]
- 2026-09-30 13:36–14:0x +07 — Pha 1 (chỉ đọc): xác định luồng trả lời (chỉ dùng nguồn **đang bật** → retrieval lọc `document_id` đã ready → LLM); đo index production (496 doc/133k chunk, có tri thức LSU và `Loi KDTPS.xlsx` nhưng không khớp `document_id` của 494 nguồn sổ); đo tốc độ nhúng thật ONNX fp32 CPU = **0,32 chunk/s** (3,1 s/chunk) → nhúng cả 494 nguồn (~79k chunk) ≈ **68 giờ**, bất khả thi. Tái hiện lỗi trên app đang chạy (phiên Chromium mới): "LSU là gì?" → "⚠️ Tìm kiếm tài liệu chưa sẵn sàng. Vui lòng thử lại sau khi các nguồn hoàn tất chuẩn bị." + "⚠️ Thiếu ngữ cảnh / Chưa có nguồn nào." (ảnh `scratch/hodap-00-hien-trang.png`).
- 2026-09-30 14:0x +07 — Pha 2 bước 1: bật 35/494 nguồn (8 pptx + 3 msg + 24 xlsx; bỏ 459 CSV log vì ~66 giờ nhúng) cho hội thoại `CONV-9C730D76` bằng API store của app; UI xác nhận "Nguồn đang bật: 35". Chuẩn bị nền đã chạy: ledger 1 `processing` + 34 `pending`.

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`).
- Vé dieutra-banner-0494: **ĐẠT** 2026-09-30 ~12:31 +07 (commit `329524c`).
- Vé deploy-fix-banner-0494: **ĐẠT** 2026-09-30 ~12:58 +07 (commit `1b40e400`) — banner 0/494 đã ẩn, app LAN bình thường.
- Vé này: thông luồng hỏi đáp LSU + lỗi trên chat.
