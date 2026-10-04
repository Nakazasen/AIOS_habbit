# Vé: ROUTER-FIX — sửa lỗi khóa cloud Router (unknown_error từ tối 2/10)

Lane: [NHÀ] OMP chạy trên máy nhà h410asrock.
Không merge `main`; code tương thích Python 3.11; không force-push.
Role OMP gợi ý: PLAN (chẩn đoán) rồi DEFAULT (sửa + verify).

## Bối cảnh

- `Nakazasen Router` (lane 3, đường gọi model cloud) chết từ tối 2/10 với lỗi `unknown_error` ở bước khóa cloud (OMP đã ghi nhận trong vé `LLM-ENABLE-DO-NHA-R1`).
- Hệ quả: vé `SPEED-COLDSTART-HOME-R1` chỉ đo được lane 1 (cầu nối Gemini, 26s/6 câu ĐẠT), lane 3 bỏ trống; máy công ty đang làm SPEED-COLDSTART-PC0575 cũng cần Router khỏe để so sánh.
- User chỉ đạo 2026-10-04 ~19:05 +07: **ưu tiên số 1, làm ngay sau ROUND5**.

## Công việc

1. **Chẩn đoán (role PLAN):** mở log/config, xác định lỗi `unknown_error` tối 2/10 nằm ở đâu — env/key/account cloud; phân biệt: key hết hạn, sai biến môi trường, account bị khóa, hay mạng. Ghi nguyên nhân gốc vào báo cáo.
2. **Sửa:** refresh/nhập lại key đúng cách (qua Secure Vault hoặc file config máy nhà, không nhúng key vào repo/commit); sửa config/env cho đúng.
3. **Verify:**
   - Probe 1 câu hỏi qua `RouterSynthesisProvider` trả lời được.
   - Chạy lại 6 câu L1–E3 **lạnh** qua lane 3 (restart app trước), ghi thời gian từng câu, parity với đáp án lane 1.
4. **Regression nhẹ:** restart app 2 lần, xác nhận lane 1 không bị ảnh hưởng bởi thay đổi config.

## Tiêu chí ĐẠT

- Router trả lời được câu hỏi qua `RouterSynthesisProvider`, không còn `unknown_error`.
- 6 câu lạnh lane 3 có số đo thời gian cụ thể từng câu; kết quả parity đúng với lane 1.
- Không ghi key/secret nào vào repo hoặc commit; SHA index production không đổi.

## Báo cáo

Ghi rõ: nguyên nhân gốc (key/env/account/mạng) — key sửa bằng cách nào — số đo 6 câu lane 3 — commit SHA — máy đã khởi động lại app bao nhiêu lần.
