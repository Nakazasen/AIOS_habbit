# Vé: UX-AGENT-UI-FIX2-VERIFY — verify lại sau khi Muse vá fallback thẻ đính kèm

Lane: [NHÀ] OMP verify trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

- Verify lần 3 **CHƯA ĐẠT** (19:19 +07, `cho-muse`): tạo file đã được
  (SHA `35b2d708…ea50`, Word mở được trên đĩa), mục 2 Hoàn tác **PASS**
  (SHA về đúng `0e3ffa4b…bd48`), nhưng **mục 1 FAIL** (nút Tải về vẫn mờ)
  và **mục 3 FAIL** (Xem toàn văn `.docx` không mờ; cả `.md` và `.docx`
  báo "không còn trên máy" dù file còn trên đĩa).
- Nguyên nhân (OMP chẩn đoán, Muse xác nhận độc lập trên code): luồng tạo
  báo cáo trong chat (`ARE-*`) **không ghi dòng `agent_work_items`**; thẻ
  đính kèm trong `render_chat_bubble` chỉ bật nút khi
  `get_agent_work(work_id)` có dòng → `verified_result_path` luôn trống
  với thẻ ARE-* → nút Tải về tắt, Xem toàn văn báo sai. Vá `ab70e69`
  đúng với hàm cổng nhưng thẻ không đi tới chỗ đó.
- Muse đã vá (commit `0a0716f`): trích helper mới `verify_card_result_path`
  trong `agent_report_artifact.py` — thẻ ưu tiên `result_ref` của dòng việc
  (luồng orchestrator), **fallback sang kiểm đúng `result_path` ghi trong
  comment metadata** (luồng ARE-*) bằng cổng an toàn với
  `allowed_roots=(default_doc_root(),)` — **vẫn chặn `..` và file ngoài
  gốc** như cũ. Kiểm chứng VM: **63 passed** (5 file test liên quan, gồm
  4 regression test mới cho helper: ưu tiên dòng việc / fallback comment /
  chặn traversal + file ngoài gốc / không gì hợp lệ → None), `compileall`
  OK, `cli audit` PASS, `import aios_habit.workspace_chat_app` được,
  tương thích Python 3.11.

## Việc OMP verify [NHÀ]

Điều kiện mở: `0a0716f` là tổ tiên của HEAD
(`git merge-base --is-ancestor 0a0716f HEAD`). App thử **8515**, đúng biến môi
trường của `RUN_AIOS_WORKSPACE_CHAT.bat` (kể cả `AIOS_FEATURE_CHAT_ACTION=1`,
**không** đặt `AIOS_DOC_ROOT` — giữ nguyên để test đúng kịch bản đã lỗi).
Không đụng app 8501 và cầu nối 8585.

1. Trong chat, gõ "tạo báo cáo tuan.docx: ..." (nội dung tùy ý): thẻ đính kèm
   hiện 3 nút; bấm **Tải về** → nút **bấm được**, file `.docx` tải về **mở
   được ngay bằng Word**, nội dung đúng. (Đây là mục FAIL lần 3.)
2. Gõ "sửa báo cáo tuan.docx: thêm ..." (file đã có): sau khi sửa, bấm
   **Hoàn tác** → file trở về đúng nội dung trước khi sửa (so bằng mắt hoặc SHA).
   (Đã PASS lần 3 — verify nhanh lại để chắc fix không vỡ.)
3. Tạo báo cáo `.md`: nút **Xem toàn văn** mở/thu gọn được, nội dung đúng;
   với `.docx`, nút Xem toàn văn **bị mờ** (không bấm được). (Đây là mục FAIL lần 3.)
4. Ghi SHA index production trước/sau (phải không đổi).
5. Kiểm cổng: `compileall` + `pytest` các test liên quan
   (`test_agent_report_artifact.py`, `test_chat_action_agent_report.py`,
   `test_workspace_chat_ui_copy.py`, `test_workspace_agent_policy.py`)
   + `cli audit` PASS + import `workspace_chat_app` được, trên Python 3.11.

## Tiêu chí ĐẠT

- Đủ 5 mục trên đều đúng như mô tả; không vỡ thẻ đính kèm loại khác
  (thẻ interview, thẻ workflow... nếu có trên app 8515).
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
- Báo cáo kết quả: bổ sung **mục verify lần 4** vào
  `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` rồi `xong-cho-duyet`.
  Nếu còn FAIL → ghi đúng mục + bằng chứng, đặt lại `cho-muse`, không sửa code.
