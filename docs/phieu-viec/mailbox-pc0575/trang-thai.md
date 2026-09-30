# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: hodap-lsu-loi
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `6e05dc8` (báo cáo tạm + mốc 4)
`bao_cao`: `docs/phieu-viec/ket-qua/hodap-lsu-loi.md` (đã có **báo cáo TẠM**: chẩn đoán + việc đã làm + lệnh dừng nhúng + thông tin index; sẽ bỏ chữ "TẠM" sau bước verify 6 câu hỏi)
`collection_id`: **`tri_thuc`** (sổ "Điều tra lỗi LSU" = `NB-E35A7BEE` không có trường `collection_id` trong bản ghi → dùng mặc định `DEFAULT_COLLECTION_ID = "tri_thuc"`; index production: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`, profile `bge_m3_hybrid`)
`ghi_chu`: 2026-09-30 14:47 +07 — Theo bổ sung khẩn 14:40: ĐÃ DỪNG nhúng CPU (kill worker `bge_subprocess_worker` PID 2764/17368); 25 nguồn chưa chuẩn bị được park `failed` với lý do `paused_shared_index_from_home_machine` → không tự nhúng lại (đã F5 kiểm chứng 40 giây: ledger đứng yên, không sinh worker mới); 9 nguồn đã ready giữ nguyên; app vẫn phục vụ LAN (HTTP 200, `/_stcore/health` ok). Chờ index dùng chung từ máy nhà để tiếp tục bước verify 6 câu hỏi.

Mốc:
- ghi chú: 2026-09-30 14:52 +07 — ⚠️ PHIÊN OMP SAU (khi watcher tự mở lại): KHÔNG có việc nào chạy được cho tới khi index dùng chung từ máy nhà được copy sang. KHÔNG bấm "Thử chuẩn bị lại" / "Tiếp tục chuẩn bị" (sẽ nhúng lại bằng CPU — trái lệnh user). Chỉ đọc, xác nhận, rồi dừng. Hiện trạng: 9 ready / 25 parked, 0 processing; app LAN HTTP 200.
- 2026-09-30 14:40–14:47 +07 — Nhận bổ sung khẩn, thực hiện đúng 3 điểm: (1) dừng worker nhúng CPU (`Stop-Process` PID 2764 + 17368; xác nhận 0 tiến trình `bge_subprocess_worker`); park 24 nguồn `pending` + 1 nguồn `processing` (biên bản lỗi kỳ 3) thành `failed`/`paused_shared_index_from_home_machine` bằng `scratch/hodap_pause_prep.py` (dry-run + apply) để reconcile không tự xếp lại hàng đợi; (2) `collection_id` = `tri_thuc`; (3) giữ vé `dang-lam`, chờ index dùng chung. Trạng thái cuối: 9 ready / 25 parked, 0 processing; LAN: `localhost:8501` → HTTP 200, `/_stcore/health` → ok. [commit `06118e3`]
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
