# Vé: UX-AGENT-UI-FIX1-VERIFY — verify lại sau khi Muse vá lỗi gốc doc root

Lane: [NHÀ] OMP verify trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

- Verify lần 1 **CHƯA ĐẠT** (mục 1): app 8515 trả "Chưa làm được: Đường dẫn nằm
  ngoài thư mục làm việc, từ chối." khi gõ "tạo báo cáo tuan.docx: ...".
- Nguyên nhân (OMP chẩn đoán, Muse xác nhận độc lập trên code): khi không có
  `AIOS_DOC_ROOT` (file `.bat` không đặt biến này),
  `chat_action_agent_report._default_doc_root()` tính ra `~/AIOS_bao_cao`
  nhưng `agent_doc_edit._safe_path()` chỉ cho phép `cwd` → `edit_document`
  từ chối đúng đường dẫn mà lớp action vừa tạo.
- Muse đã vá (commit `f1dc433`): thêm hàm dùng chung `default_doc_root()`
  trong `agent_doc_edit.py`; cả hai lớp dùng cùng một gốc `~/AIOS_bao_cao`;
  cổng `_safe_path()` vẫn chặn `..` / thoát khỏi gốc như cũ. Kiểm chứng VM:
  **51 passed** (3 file test liên quan, gồm 1 regression test mới với
  `AIOS_DOC_ROOT` không đặt), `compileall` OK, `cli audit` PASS,
  `import aios_habit.workspace_chat_app` được, tương thích Python 3.11.

## Việc OMP verify [NHÀ]

Điều kiện mở: `f1dc433` là tổ tiên của HEAD
(`git merge-base --is-ancestor f1dc433 HEAD`). App thử **8515**, đúng biến môi
trường của `RUN_AIOS_WORKSPACE_CHAT.bat` (kể cả `AIOS_FEATURE_CHAT_ACTION=1`,
**không** đặt `AIOS_DOC_ROOT` — giữ nguyên để test đúng kịch bản đã lỗi).
Không đụng app 8501 và cầu nối 8585.

1. Trong chat, gõ "tạo báo cáo tuan.docx: ..." (nội dung tùy ý): thẻ đính kèm
   hiện 3 nút; bấm **Tải về** → file `.docx` tải về **mở được ngay bằng Word**,
   nội dung đúng. (Đây là mục đã FAIL lần 1.)
2. Gõ "sửa báo cáo tuan.docx: thêm ..." (file đã có): sau khi sửa, bấm
   **Hoàn tác** → file trở về đúng nội dung trước khi sửa (so bằng mắt hoặc SHA).
3. Tạo báo cáo `.md`: nút **Xem toàn văn** vẫn mở/thu gọn được trong thẻ;
   với `.docx`, nút Xem toàn văn **bị mờ** (không bấm được).
4. Ghi SHA index production trước/sau (phải không đổi).
5. Kiểm cổng: `compileall` + `pytest` các test liên quan
   (`test_agent_doc_edit.py`, `test_chat_action_agent_report.py`,
   `test_agent_report_artifact.py`) + `cli audit` PASS + import
   `workspace_chat_app` được, trên Python 3.11.

## Tiêu chí ĐẠT

- Đủ 5 mục trên đều đúng như mô tả; không vỡ thẻ đính kèm loại khác.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
- Báo cáo kết quả: bổ sung **mục verify lần 2** vào
  `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` rồi `xong-cho-duyet`.
