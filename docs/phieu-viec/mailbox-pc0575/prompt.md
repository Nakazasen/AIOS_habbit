# Vé RAG-REMEASURE-PC0575 — Đo lại hợp nhất 2 lane sau khi các fix đã về (hồi quy §6.5)

**Máy thực hiện:** CÔNG TY KDTVN-PC0575 (thợ OMP), CPU-only.
**Role gợi ý:** DEFAULT (chạy đo + phân tích).
**Nguồn:** `lsu-quality-pc0575.md` §6 mục 5 — hồi quy bằng chính bộ 50 câu sau các fix.

## Cổng chờ (BẮT BUỘC)

Vé này chỉ bắt đầu khi vé `RETRIEVAL-ENTITY-PC0575` (mailbox-pc0575-agy) đã có verdict ĐẠT trong mailbox của nó. Chưa đạt → đặt `dang-lam` + ghi mốc chờ cổng, KHÔNG chạy lane, KHÔNG thoát vé.

## Bối cảnh — các fix đã/đang về kể từ lượt đo gốc

- MATCHER-FIX: C-Agent 2,16 → 2,92 (đo lại sau vá), thước chuẩn hoá → 2,95.
- RUBRIC-NORMALIZE: thước đo đã chuẩn hoá; lane RAG chấm lại offline 0,93 → 1,21 (đáp án cũ).
- RETRIEVAL-ENTITY (đang làm ở agy): boost thực thể + cap 3 mảnh/tệp — thay đổi retrieval thật, cần đo lane mới để thấy tác động.
- SRC-SYNC (đang chạy ở opencode): bổ sung file nguồn về máy — nếu đã xong pha ingest thì ghi rõ trạng thái nguồn trong báo cáo; vé này KHÔNG tự ingest.

## Việc phải làm

1. Kéo code mới nhất của nhánh `phieu-viec/rag-fix1`, ghi commit HEAD vào báo cáo. Index chỉ-đọc, md5 trước/sau.
2. Chạy lại **trọn 2 lane × 50 câu** (bộ đề + thước đã chuẩn hoá, đúng bản đã đóng dấu trong repo ở vé RETRIEVAL-ENTITY bước 0):
   - Lane C-Agent: qua endpoint trên mạng `vn-kdwireless` (lưu ý: nếu vé SRC-SYNC vừa chuyển mạng, chờ máy về `vn-kdwireless` rồi mới chạy lane này).
   - Lane RAG: CPU-only như các lượt trước.
   - Checkpoint từng câu, heartbeat tối thiểu 15 phút (lane RAG ~2 phút/câu — vé dài).
3. So sánh 3 cột cho mỗi lane: đo gốc (C-Agent 2,16 / RAG 0,93) → sau từng fix (2,95 / 1,21) → **lượt này**. Mục tiêu theo báo cáo gốc: C-Agent ≥2,5 (kỳ vọng ~2,9), RAG ≥1,5.
4. Phân tích riêng các câu còn dưới chuẩn sau lượt này: thuộc nhóm nào (A retrieval / B bảng / D thiếu nguồn / khác), đếm số lượng — làm đầu vào cho vòng fix tiếp theo.

## Rào cứng

- Không merge `main`. Không ghi index. Không tự ingest file nguồn. Python 3.11.
- Không sửa code ở vé này (đo thuần); phát hiện lỗi code thì ghi vào báo cáo, không tự vá.
- Không nới thước đo; dùng đúng bộ đề/thước đã đóng dấu.

## Báo cáo

`docs/phieu-viec/ket-qua/rag-remeasure-pc0575.md` — commit code đã đo, trạng thái nguồn (SRC-SYNC tới đâu), bảng 3 cột 2 lane, phân loại câu còn dưới chuẩn.
