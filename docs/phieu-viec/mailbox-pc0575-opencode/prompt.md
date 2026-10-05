# Vé AUDIT-BATCH88-PC0575 — Audit 15 cặp mẻ 88 (Q3392–Q3406) raw → fixed

**Thợ:** opencode
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
**Thư mục làm việc DUY NHẤT:** `D:\Sandbox\AIOS_habbit`
Role gợi ý: DEFAULT.

## Bối cảnh

Khâu sinh hỏi đáp ChatGPT đã xong toàn bộ 88 mẻ (3.393 cặp raw). Mẻ 88 là mẻ vét cuối
(15 cặp Q3392–Q3406, Điều-tra-lỗi, vi 5 / zh 5 / ja 5) — **chưa qua audit/fixed**.
Các mẻ trước đã fixed: MOM 608, LSU 1.790, Điều-tra-lỗi batch 55–87 được 979
(loại Q3214 trùng Q3124).

## Việc cần làm

1. Đọc `docs/phieu-viec/chatgpt-enrichment-raw/dieuchinh/batch-88.md` (15 cặp).
2. Audit từng cặp theo đúng chuẩn các mẻ trước: đủ 6 trường (Khối/Ngôn ngữ/Bối cảnh/
   Cách hỏi/Hỏi/Đáp), đáp án có nguồn, không bịa, văn phong đúng ngôn ngữ.
3. Kiểm tra trùng lặp với toàn bộ cặp đã fixed (đặc biệt các cặp Q31xx–Q33xx);
   cặp nào trùng thì loại và ghi rõ.
4. Ghi kết quả vào `docs/phieu-viec/chatgpt-enrichment-fixed/dieuchinh/batch-88.md`
   (giữ nguyên format các file fixed batch 55–87).

## Tiêu chí ĐẠT

- File fixed đủ 15 cặp (hoặc ít hơn nếu loại trùng — ghi rõ số loại + mã cặp).
- Báo cáo `docs/phieu-viec/ket-qua/audit-batch88-pc0575.md`: số cặp đạt/loại,
  lỗi tìm thấy (nếu có), đối chiếu chuẩn format.
- Xong thì `trang-thai.md` → `xong-cho-duyet`.

## Cấm

- Không merge `main`. Không force-push. Không sửa file raw.
- Không đụng file của thợ khác (mailbox-pc0575, mailbox-pc0575-agy).
- Code mới (nếu có) tương thích Python 3.11.
