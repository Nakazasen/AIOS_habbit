# Vé: KNOWLEDGE-DIGEST-HOME-R2 — resume sổ tay tri thức từ checkpoint 180/889

Lane: [NHÀ] OMP chạy trên máy nhà h410asrock, qua cầu nối Gemini Web (`127.0.0.1:8585`).
Role OMP gợi ý: DEFAULT (batch chạy dài).

## Bối cảnh

- R1 (2026-10-03 01:47–02:26 +07) đếm được **889 document / 149.800 chunk** trong collection `tri_thuc`, chạy batch tóm tắt tới checkpoint **180/889** thì cầu nối Gemini Web trả 405/502 từ 02:03 → watcher escalate `cho-muse` lúc ~05:35 (`docs/phieu-viec/mailbox/cho-muse-knowledge-digest-home.md`).
- Escalation **ĐÃ được gỡ**: vé ROUTER-FIX (2026-10-04 21:42–23:0x) kiểm tra cầu nối = `direct_ready`, gọi trực tiếp `openai_compatible_local/gemini-web` OK ("Kết nối thành công"), 6 câu kiểm tra đạt.
- Đây là mục tiêu user chốt cho 2 ngày cuối tuần (2026-10-03): nén toàn bộ kho thành sổ tay Markdown để hỏi đáp qua context dài, chạy song song với RAG. R1 chưa xong → R2 resume, không làm lại từ đầu.
- Báo cáo R1: `docs/phieu-viec/ket-qua/knowledge-digest-home.md`. Checkpoint: `C:/tmp/knowledge-digest-home/`.

## Việc OMP làm [NHÀ]

0. Kiểm tra checkpoint `C:/tmp/knowledge-digest-home/` còn nguyên vẹn (số doc đã xong phải = 180). Nếu checkpoint hỏng/mất: báo trung thực, đếm lại từ đầu là phương án cuối cùng.
1. Resume batch tóm tắt từ doc 181 → 889 qua cầu nối Gemini Web (đặt `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` trong tiến trình gọi). Checkpoint mỗi 25 doc; **cấm quá 45 phút không ghi log tiến độ**.
2. Nếu cầu nối lại trả 405/502: backoff 5/15/30/60 phút theo cổng R1; sau 2 giờ vẫn lỗi → DỪNG trung thực, báo số doc đã xong + đặt `cho-muse` (không fake số, không tự đổi provider — đổi provider là quyết định của user).
3. Gom thành sổ tay Markdown duy nhất + manifest SHA-256. Dòng đầu file sổ tay: "Bản thảo — chưa qua chuyên gia duyệt".
4. Kiểm tra bao phủ: số mục trong sổ tay phải = số document đếm ở bước 0 (cấm hardcode 889 — đếm lại thực tế).
5. Chạy probe hỏi đáp trên bộ benchmark của R1 (10–15 câu): ghi đáp án + thời gian từng câu; chạy cùng bộ câu qua lane RAG hiện tại để so sánh (thời gian + độ bao quát theo rubric).
6. Index production **chỉ đọc**: đo SHA-256 trước/sau, phải khớp `45eb0e07…b7c0`.

## Rào cứng (giữ nguyên từ R1)

- Sổ tay là **bản thảo do LLM soạn** — không gắn nhãn `kiến thức đã được đào tạo bổ sung`; không nhập sổ tay vào kho tri thức; không nhập vào luồng trả lời chính của app; không lưu vết LLM nào vào DB.
- Không merge `main`; không force-push; code tương thích Python 3.11.
- Không ghi index production; không đụng ổ D.

## Tiêu chí ĐẠT

- Sổ tay bao phủ 100% document đã đếm; manifest SHA-256 hợp lệ.
- Probe: số liệu từng câu đầy đủ (đáp án + thời gian), so sánh được với lane RAG.
- SHA index production không đổi.
- Báo cáo `docs/phieu-viec/ket-qua/knowledge-digest-home-r2.md`; commit riêng trên nhánh `phieu-viec/rag-fix1`; `trang-thai.md` → `xong-cho-duyet`.

## Tiêu chí CHƯA ĐẠT

- Số bao phủ báo cáo không khớp đếm thực tế; hoặc thiếu log tiến độ quá 45 phút; hoặc có thao tác ghi vào index/DB.
