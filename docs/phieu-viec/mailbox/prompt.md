# Vé: UX-AGENT-UI-FIX2-VERIFY — verify lại sau khi Muse vá cổng an toàn thẻ đính kèm

Lane: [NHÀ] OMP verify trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

- Verify lần 2 **CHƯA ĐẠT** (18:59 +07, `cho-muse`): tạo file đã được
  (hết lỗi đường dẫn lần 1), mục 2 Hoàn tác **PASS** (SHA về đúng
  `0e3ffa4b…bd48`), nhưng **mục 1 FAIL** (nút Tải về bị mờ) và **mục 3 FAIL**
  (Xem toàn văn `.md` báo "không còn trên máy" dù file còn; `.docx` nút
  Xem toàn văn không bị mờ).
- Nguyên nhân (OMP chẩn đoán, Muse xác nhận độc lập trên code): thẻ đính kèm
  trong chat gọi `is_safe_artifact_path(cand)` mà **không truyền**
  `allowed_roots` → file dưới `~/AIOS_bao_cao` (gốc mặc định của
  `default_doc_root()`) bị coi là không an toàn → `verified_result_path`
  là None → nút Tải về tắt, Xem toàn văn báo sai, nhận diện file nhị phân
  cũng sai theo.
- Muse đã vá (commit `ab70e69`): tại điểm gọi duy nhất trong
  `workspace_chat_ui.py`, truyền `allowed_roots=(default_doc_root(),)` —
  cổng an toàn của thẻ đính kèm giờ tin đúng gốc báo cáo của agent, **vẫn
  chặn `..` và file ngoài gốc** như cũ. Kiểm chứng VM: **59 passed**
  (4 file test liên quan, gồm regression test mới
  `test_is_safe_artifact_path_allows_agent_doc_root`), `compileall` OK,
  `cli audit` PASS, `import aios_habit.workspace_chat_app` được,
  tương thích Python 3.11.

## Việc OMP verify [NHÀ]

Điều kiện mở: `ab70e69` là tổ tiên của HEAD
(`git merge-base --is-ancestor ab70e69 HEAD`). App thử **8515**, đúng biến môi
trường của `RUN_AIOS_WORKSPACE_CHAT.bat` (kể cả `AIOS_FEATURE_CHAT_ACTION=1`,
**không** đặt `AIOS_DOC_ROOT` — giữ nguyên để test đúng kịch bản đã lỗi).
Không đụng app 8501 và cầu nối 8585.

1. Trong chat, gõ "tạo báo cáo tuan.docx: ..." (nội dung tùy ý): thẻ đính kèm
   hiện 3 nút; bấm **Tải về** → nút **bấm được**, file `.docx` tải về **mở
   được ngay bằng Word**, nội dung đúng. (Đây là mục FAIL lần 2.)
2. Gõ "sửa báo cáo tuan.docx: thêm ..." (file đã có): sau khi sửa, bấm
   **Hoàn tác** → file trở về đúng nội dung trước khi sửa (so bằng mắt hoặc SHA).
   (Đã PASS lần 2 — verify nhanh lại để chắc fix không vỡ.)
3. Tạo báo cáo `.md`: nút **Xem toàn văn** mở/thu gọn được, nội dung đúng;
   với `.docx`, nút Xem toàn văn **bị mờ** (không bấm được). (Đây là mục FAIL lần 2.)
4. Ghi SHA index production trước/sau (phải không đổi).
5. Kiểm cổng: `compileall` + `pytest` các test liên quan
   (`test_agent_report_artifact.py`, `test_chat_action_agent_report.py`,
   `test_workspace_chat_ui_copy.py`, `test_workspace_agent_policy.py`)
   + `cli audit` PASS + import `workspace_chat_app` được, trên Python 3.11.

## Tiêu chí ĐẠT

- Đủ 5 mục trên đều đúng như mô tả; không vỡ thẻ đính kèm loại khác
  (thẻ interview, thẻ workflow... nếu có trên app 8515).
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
- Báo cáo kết quả: bổ sung **mục verify lần 3** vào
  `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` rồi `xong-cho-duyet`.
  Nếu còn FAIL → ghi đúng mục + bằng chứng, đặt lại `cho-muse`, không sửa code.
