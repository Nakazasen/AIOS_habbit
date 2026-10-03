# Vé: UX-INTERVIEW-UI-FIX1-VERIFY — verify fix chữ "Đã lưu nháp chờ duyệt" trên app thật

Lane: [NHÀ] OMP verify trên app thật. Không merge `main`; không sửa code (fix đã có); không force-push.

## Bối cảnh

Vé `UX-INTERVIEW-UI` verify [NHÀ]: mục 1, 2, 4, 5, 6 PASS; mục 3 CHƯA ĐẠT — trả lời hết câu thì sqlite ghi đúng nhưng màn không hiện "Đã lưu nháp chờ duyệt" (OMP đặt `cho-muse` 2026-10-03 16:50 +07, báo cáo `docs/phieu-viec/ket-qua/ux-interview-ui.md` mục 6).

Muse vá Phase A [VM], commit `f521566` (xác nhận độc lập: chỉ sửa UI `src/aios_habit/chat_interview_ui.py` +48 và `tests/test_chat_interview_ui.py` +68): khi phiên hoàn thành, chữ "Đã lưu nháp chờ duyệt" được lưu vào `st.session_state` trước `st.rerun`, nên widget vẫn hiện đúng dù phiên đã `drop_session`. Test 111 passed, audit PASS, tương thích Python 3.11.

## Việc OMP verify [NHÀ]

1. Điều kiện mở: commit fix `f521566` là tổ tiên của HEAD nhánh `phieu-viec/rag-fix1`; mở app thử cổng 8515 (không đụng app user 8501), sổ `E2EUxApp`; ghi SHA index production trước.
2. Gõ "mở phiên phỏng vấn F000": phiên mở ra, câu 1 + ô trả lời ngay dưới, không đổi màn.
3. Trả lời ĐẦY ĐỦ hết các câu (KHÔNG F5 giữa chừng): app báo **"Đã lưu nháp chờ duyệt" ổn định trên màn** (chữ không biến mất sau rerun); kiểm tra `local_cases/staging_enrichment.sqlite` có đáp án mới, `reviewer_status` = `cho_chuyen_gia_phan_hoi`.
4. Chấm regression nhanh các mục 1, 2, 4, 5, 6 (không vỡ luồng chat cũ). Sau khi hoàn thành rồi reload trang: chấp nhận widget báo hết hạn (chữ chỉ sống trong cùng browser session — giới hạn đã ghi, hành vi Streamlit bình thường).
5. `compileall src tests` OK + pytest các test liên quan đỗ; SHA index production trước/sau không đổi.
6. Viết báo cáo `docs/phieu-viec/ket-qua/ux-interview-ui-fix1.md`, commit lên nhánh, rồi đặt `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Mục 3 đúng: chữ "Đã lưu nháp chờ duyệt" hiện ổn định sau khi trả lời hết + sqlite đúng; các mục khác không vỡ.
- Commit fix `f521566` là tổ tiên của HEAD; test đỗ; index production không đổi.
- Mục nào FAIL → dừng vé, đặt `cho-muse` theo luật.
