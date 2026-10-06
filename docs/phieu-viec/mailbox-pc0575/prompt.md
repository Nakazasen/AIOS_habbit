# Vé APP-RESTORE-DEFAULT-PC0575 — Đưa app Workspace Chat về env mặc định sau demo WIRE-QA

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Role gợi ý:** SMOL/TINY (việc nhanh ~5–10 phút, chỉ thao tác process + smoke).

## Bối cảnh

- Vé `WIRE-QA-CAGENT-PC0575` (verdict Muse ĐẠT 2026-10-06 ~15:29) chạy demo 3 câu bằng app tách tiến trình (WMI detached, **pid 26880**) với env demo:
  `AIOS_FEATURE_WIRE_QA_CAGENT=1` + ghim lane `AIOS_AI_BACKEND=cagent_api`; worker BGE sống tới 6 h idle.
- Về dùng thật vẫn phải ở env **mặc định** (flag TẮT theo quy ước) cho tới khi có quyết định bật của user — báo cáo §7.5 ghi rõ: muốn về mặc định thì tắt pid này rồi mở lại bằng `RUN_AIOS_WORKSPACE_CHAT.bat`.

## Việc cần làm

1. **Tắt app demo:** kill process app demo (pid 26880, WMI detached). Sau kill, kiểm tra không còn process Streamlit/app nào trên port 8501.
2. **Mở lại app mặc định:** chạy `RUN_AIOS_WORKSPACE_CHAT.bat` như dùng thật hằng ngày (env mặc định, flag `AIOS_FEATURE_WIRE_QA_CAGENT` TẮT — không set tay).
3. **Smoke 1 câu lạnh đơn giản** qua UI (vd "ORICON STATUS là gì?"): xác nhận app trả lời bình thường, có trích dẫn; ghi thời gian gửi→đáp vào mốc.
4. Checkpoint theo quy ước; ghi mốc tắt + mở lại + smoke vào `trang-thai.md`, rồi chốt `xong-cho-duyet`.

## Không làm

- Không đổi code, không bật/tắt flag cho vé khác, không merge `main`. Mọi commit trên `phieu-viec/rag-fix1`.
- App mở lại bằng đúng file bat — không mở tay bằng lệnh streamlit khác env.
