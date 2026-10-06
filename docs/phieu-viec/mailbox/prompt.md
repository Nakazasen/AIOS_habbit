# Vé RAG-LANE-INVESTIGATE-HOME — Điều tra lane RAG: 0/50 tổng hợp cloud + 21 câu bằng chứng rỗng

**Máy thực hiện:** NHÀ h410asrock (thợ OMP).
**Role gợi ý:** DEFAULT (điều tra + sửa mức cấu hình + đo lại).
**Nguồn:** báo cáo `docs/phieu-viec/ket-qua/lsu-quality-rag-home.md` §6–§7 (vé `LSU-QUALITY-RAG-HOME`, verdict ĐẠT phần đo).

## Hai lỗi cần tìm gốc

**Lỗi A — 21/50 câu gói bằng chứng rỗng** (`provider_not_called`, 0 điểm):
- Cùng index, cùng câu Q0699: pilot PC0575 lấy được 26 item (retrieval 198,4s), lượt máy nhà lấy 0 mảnh (3,97s).
- So runner 2 bên (scratch PC0575 vs runner máy nhà): đường retrieval, ngưỡng, cách dựng gói
  bằng chứng khác nhau ở đâu? Vì sao 21 câu rỗng trong khi kho có cặp hỏi–đáp y hệt (theo ID)?
- Phân biệt rõ: rỗng do matcher staging loại (phát hiện §6, 12 câu) vs rỗng do retrieval
  toàn kho không trả mảnh nào — hai cơ chế khác nhau, đừng gộp.

**Lỗi B — 29/29 lượt tổng hợp cloud lỗi** (`provider_fallback`):
- `RouterSynthesisProvider` (gemini-2.5-flash, max_attempts=1, timeout 120s): gọi thử cầu
  `127.0.0.1:8585` đạt 2,7s trước khi đo, nhưng mọi lượt gọi thật trong lane đều lỗi.
- Bắt lỗi thật (exception/status/body) của 1 lượt gọi đại diện: lỗi ở đâu — Router (khóa/model),
  cầu 8585, timeout, hay payload? Không đoán, phải có log.

## Phạm vi sửa

- Sửa được ở mức **cấu hình/env/runner** (chọn model còn sống, thông số gọi, đường dựng gói
  bằng chứng cho khớp điều kiện pilot) → sửa luôn, ghi rõ trước/sau.
- Phải đụng logic lõi (`quality_harness.py`, provider tổng hợp trong `src/`) → DỪNG ở báo cáo
  + đề xuất, chờ Muse verdict. Không tự redesign.
- Không ghi index. Không merge `main`. Python 3.11.

## Đo lại (sau khi sửa)

- Chạy lại trọn lane RAG 50 câu, **CPU-only** như vé trước (bằng chứng device = CPU, index
  chỉ-đọc + SHA trước/sau), checkpoint từng câu, cùng rubric.
- Mục tiêu: tổng hợp cloud thành công >0 câu (kỳ vọng đa số), gói bằng chứng không còn rỗng
  bất thường. Báo cáo đối chiếu 3 cột: lượt này / lượt fallback trước (GPA 0,75) / C-Agent (2,16).

## Nhịp heartbeat (BẮT BUỘC)

Mỗi **15 phút** append mốc `` `ghi_chu` `` vào `trang-thai.md` mailbox này. Cấm im lặng quá 15 phút.

## Báo cáo

`docs/phieu-viec/ket-qua/rag-lane-investigate-home.md` — gốc lỗi A + gốc lỗi B (kèm log),
điểm đã sửa, bảng đo lại 50 câu, tách staging khớp/không khớp như cũ.
