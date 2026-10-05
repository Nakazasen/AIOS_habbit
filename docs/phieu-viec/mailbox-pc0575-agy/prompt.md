# Vé PROBE-CAGENT-PC0575 — Kiểm tra lane C-Agent còn sống từ PC0575

**Thợ:** agy (Antigravity CLI)
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
**Thư mục làm việc DUY NHẤT:** `D:\Sandbox\AIOS_habbit`
Role gợi ý: SMOL/TINY (việc kiểm tra nhanh).

## Bối cảnh

Hai vé sắp tới (WIRE-QA-CAGENT, DIGEST-CTY-RESUME) đều phụ thuộc lane C-Agent.
Ngày 02/10 C-Agent đã chạy được 6/6 câu từ PC0575 (16,5–45,8 s/câu phần viết).
Cần xác minh lại TRƯỚC để biết đường còn sống hay đã chết.

## Việc cần làm

1. Dùng ĐÚNG code có sẵn trong repo (`src/aios_habit/cagent_api.py`,
   `src/aios_habit/ai_lane.py`) để gọi C-Agent. **Không tự chế cách gọi riêng.**
2. Endpoint mặc định trong code:
   `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f`
3. Gửi ĐÚNG 1 câu hỏi ngắn kiểm tra (không spam nhiều câu, tiết kiệm quota).
   Ghi lại: sống/chết, thời gian phản hồi, lỗi nguyên văn nếu chết.
4. **Không đi qua app UI** — thợ omp đang làm vé SPEED-COLDSTART có restart app;
   probe trực tiếp lane C-Agent để tránh xung đột.

## Tiêu chí ĐẠT

- Báo cáo `docs/phieu-viec/ket-qua/probe-cagent-pc0575.md`: kết luận SỐNG/CHẾT
  + bằng chứng (thời gian/lỗi nguyên văn) + câu hỏi đã dùng.
- Xong thì `trang-thai.md` → `xong-cho-duyet`.

## Cấm

- Không merge `main`. Không force-push. Không sửa code lane.
- Không gửi quá 2 câu hỏi tới C-Agent trong vé này.
- Không đụng file của thợ khác (mailbox-pc0575, mailbox-pc0575-opencode).
