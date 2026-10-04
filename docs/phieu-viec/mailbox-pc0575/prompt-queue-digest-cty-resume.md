# Vé DIGEST-CTY-RESUME — Làm tiếp sổ tay tri thức ở máy công ty bằng lane C-Agent

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** sau `WIRE-QA-CAGENT-PC0575`.
**Role gợi ý:** DEFAULT (batch chạy dài).

## Bối cảnh

- Vé `KNOWLEDGE-DIGEST-HOME-R2` đang chạy dở ở máy nhà (checkpoint 180/889 doc, qua cầu Gemini Web). Máy nhà sắp tắt → thợ nhà dừng.
- User chốt: làm tiếp phần sổ tay tri thức ở máy công ty, dùng lane C-Agent (đã đo 6/6 câu thành công ngày 2/10 trên chính máy này) thay cầu Gemini Web.
- Mục tiêu gốc (user chốt 3/10): nén toàn bộ kho thành sổ tay Markdown để hỏi đáp qua context dài, chạy song song với RAG.

## Yêu cầu (làm theo đúng thứ tự)

0. **Kiểm tra trước, không làm trùng:** đọc `docs/phieu-viec/mailbox/trang-thai.md` (máy nhà) xem OMP đã xong chưa. Nếu OMP đã `xong-cho-duyet`/`xong` và sổ tay đã push → chỉ `git pull` sổ tay về, KHÔNG làm lại, báo rõ rồi kết thúc vé ở mức ĐẠT.
1. Nếu OMP chưa xong: kiểm tra checkpoint `C:/tmp/knowledge-digest-home/` có được OMP push lên GitHub/Drive không. Có → pull về, resume từ checkpoint. Không → DỪNG, báo trung thực (không tự làm lại 889 doc từ đầu khi chưa có lệnh — tốn hàng giờ).
2. Resume batch tóm tắt qua lane C-Agent (đặt `AIOS_CAGENT_API_URL` nếu cần; không hardcode URL vào code). Checkpoint mỗi 25 doc; cấm quá 45 phút không ghi log tiến độ.
3. Gom thành sổ tay Markdown duy nhất + manifest SHA-256. Dòng đầu file: `Bản thảo — chưa qua chuyên gia duyệt`.
4. Kiểm tra bao phủ: số mục trong sổ tay = số document đếm thực tế (cấm hardcode 889).
5. Chạy probe hỏi đáp `src/aios_habit/digest_qa.py` trên 10–15 câu benchmark, so sánh với lane RAG.

## Rào cứng

- Sổ tay là bản thảo do LLM soạn — không gắn nhãn tri thức đã duyệt; không nhập vào kho tri thức; không nhập luồng trả lời chính; không lưu vết LLM vào DB.
- Không ghi index production (đo SHA trước/sau). Không merge `main`. Code tương thích Python 3.11.

## Điều kiện nghiệm thu

- Sổ tay bao phủ 100% document đã đếm; manifest SHA-256 hợp lệ.
- Probe có đủ số liệu từng câu (đáp án + thời gian), so sánh được với lane RAG.
- Báo cáo `docs/phieu-viec/ket-qua/knowledge-digest-cty.md`; commit riêng nhánh `phieu-viec/rag-fix1`.

**Verdict:** Muse review trên bằng chứng độc lập.
