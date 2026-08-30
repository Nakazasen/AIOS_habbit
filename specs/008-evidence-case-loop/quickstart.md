# Kiểm chứng cổng theo thứ tự

Không làm các cổng đồng thời. Mỗi cổng chỉ bắt đầu khi cổng trước có commit, kiểm thử focused và audit độc lập.

## 0. Điều kiện do chủ repo xác nhận trước code

1. Chạy ingest tài liệu thật đã được phép trên máy chủ sở hữu và lưu evidence kết quả; không dùng raw CSV.
2. Thử một writer/nhiều reader ở đường dẫn thư viện chung thật; nếu không có thì Gate A vẫn `PARTIAL`.
3. Chỉ định reviewer chuyên gia, scope quyết định, người có quyền promotion và người có quyền phát hành SOP.
4. Cấp sample log/pilot được phép dùng, định nghĩa header/múi giờ/mã lỗi; bảng mapping/sơ đồ chỉ cấp khi muốn mở gate overlay sau này.
5. Với LSU, cấp dataset history, nhãn, data owner, quality owner, replay protocol và shadow reviewer. Thiếu là `blocked`.

## 1. Cổng hồ sơ

Chạy tests mới cho case store/UI cùng `tests/test_workspace_chat_source_selection_owner_flow.py` và `tests/test_workspace_chat_ui_copy.py`. Kiểm một ca có evidence, một ca evidence thiếu, một lỗi I/O; mở lại process để readback. Không có raw excerpt/secret/CSV trong case storage.

## 2. Cổng chuyên gia và bài học

Chạy tests state transition/restart/readback. Xác minh candidate không promotion; confirmed thiếu role/scope/rationale không qua; lesson provenance truy ngược đúng case/review/evidence.

## 3. Cổng pilot line

Chạy `tests/test_line_log_parser.py`, tests evidence case mới và Gate B/C focused. Kiểm event không match không tự gắn 5 event mới nhất thành evidence case; toàn bộ output vẫn nói nghi vấn/chưa chẩn đoán.

## 4. Cổng LSU readiness

Chạy test manifest. Dataset/label/owner/replay thiếu phải `blocked`; đủ trường chỉ tạo `ready_for_shadow`. Không gọi model prediction, không alert/control.

## 5. Cổng đề xuất agent

Chạy tests draft/policy/action proposal. No-evidence, unapproved, overwrite, protected path, command/bridge/PLC/delete đều bị từ chối. Chỉ kiểm export mới sau approval đã bind proposal/case digest.

## Lệnh kỹ thuật cuối mỗi cổng

```powershell
D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe -m compileall -q src tests
D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe -m pytest -q <danh-sách-tests-focused-của-cổng>
$env:PYTHONPATH="src"; D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe -c "import aios_habit.workspace_chat_app"
git diff --check
```

Chỉ chạy `pytest -q` toàn repo và `cli audit` khi cổng đã đủ focused tests và phạm vi cho phép. Timeout hay dependency thiếu là chưa xác minh, không phải PASS.
