# Hướng dẫn xác minh theo cổng

Tài liệu này chỉ mô tả cách chứng minh Goal 009. Lệnh chưa tồn tại không được dùng làm bằng chứng đã triển khai.

## 1. Điều kiện chung

- Dùng Python 3.11 qua môi trường `uv` đã khóa.
- Chỉ dùng fixture trong `tests/fixtures/agent_harness/`; không dùng dữ liệu công ty hoặc `local_only` thật.
- OpenCode phải đúng phiên bản/checksum ghi trong Gate Card.
- `antigravity_bridge.py` và các test Workspace Chat liên quan phải còn hoạt động.
- Không chạy runtime với toàn bộ `os.environ` của tiến trình cha.

## 2. G0 — Kiểm tra tài liệu và phạm vi

```powershell
git diff --check -- specs/009-agent-harness-adoption ARCHITECTURE.md ROADMAP.md
rg -n "chỉ đọc|duyệt toàn bộ|partial hunk|extension Code-OSS" specs/009-agent-harness-adoption
rg -n "antigravity_bridge|workspace_agent_bridge_client" specs/009-agent-harness-adoption ARCHITECTURE.md ROADMAP.md
```

Kỳ vọng:

- Không còn probe chỉ đọc hoặc bắt người dùng duyệt toàn bộ `diff` như MVP.
- Cầu nối Antigravity được giữ; chỉ cầu nối lập trình NVIDIA cũ nằm trong đường thay thế.
- Scope có báo cáo lỗi, biểu đồ, rà soát thiết kế công đoạn, sửa mã và hàng đợi nhỏ.

## 3. G1 — Probe OpenCode đọc–sửa–test–hoàn tác

Sau khi T001–T004 tồn tại:

```powershell
uv run --no-sync --group dev python scripts/probe_opencode_runtime.py --fixture tests/fixtures/agent_harness --bind 127.0.0.1 --json
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_capabilities.py
```

Probe phải chứng minh bằng receipt:

1. health/version và checksum đúng bản pin;
2. create/get/abort/resume session;
3. read/search file;
4. create/edit file trong task root;
5. chạy một test thất bại và một test đạt, lấy exit code thật;
6. đọc trạng thái sau sửa và hoàn tác về checkpoint;
7. từ chối path traversal, symlink thoát root, `.env`, command ngoài allowlist, commit và push;
8. auto-approval không hỏi lại với action hợp lệ trong task root.

Thiếu bất kỳ mục nào thì G1 là `BLOCKED`; đánh giá Cline theo cùng fixture, không fork OpenCode ngay.

## 4. G2 — Báo cáo lỗi có biểu đồ

Sau khi US1 được triển khai:

```powershell
uv run --no-sync --group dev pytest -q tests/test_agent_error_report_artifact.py
```

Chạy hai fixture:

- Fixture đủ log/số liệu: tạo Markdown báo cáo, bảng và ít nhất một biểu đồ/sơ đồ có `source_refs`, cột, đơn vị, phép lọc/tổng hợp và data digest.
- Fixture thiếu số liệu: vẫn tạo báo cáo và cảnh báo rõ, nhưng không tạo biểu đồ giả.

Xác minh bản nháp được tự lưu, mở được và hoàn tác không làm mất file có trước.

## 5. G3 — Rà soát thiết kế công đoạn

```powershell
uv run --no-sync --group dev pytest -q tests/test_agent_process_design_review.py
```

Fixture phải có:

- hai tài liệu mâu thuẫn giới hạn;
- một bước thiếu điểm kiểm tra;
- một nhận định không đủ bằng chứng;
- một tài liệu phiên bản cũ.

Kỳ vọng đầu ra tách rõ hiện trạng, phát hiện, ảnh hưởng, đề xuất và câu hỏi cần xác nhận; mỗi phát hiện có source location hoặc nhãn `insufficient`/`proposal`. Sơ đồ hiện tại và đề xuất không được ghi thành tài liệu chính thức.

## 6. G4 — Sửa mã nguồn

```powershell
uv run --no-sync --group dev pytest -q tests/test_agent_code_worktree.py
```

Kịch bản tối thiểu:

1. Agent sửa bug fixture trong worktree.
2. Test đầu tiên lỗi; Agent sửa tiếp trong budget; test sau đạt.
3. UI tóm tắt bằng tiếng Việt, không bắt mở `diff`.
4. “Dùng kết quả” chỉ đổi đúng file trong checkpoint khi workspace không xung đột.
5. “Hoàn tác” khôi phục trạng thái trước task.
6. Workspace bẩn hoặc file đổi giữa chừng không bị ghi đè.

## 7. G5 — Hàng đợi và UX không chuyên

```powershell
uv run --no-sync --group dev pytest -q tests/test_agent_work_queue.py
```

Tạo ba việc: báo cáo lỗi, rà soát công đoạn và sửa mã. Đóng/mở lại ứng dụng giữa chừng.

Kỳ vọng:

- nhận thêm việc khi một việc đang chạy;
- một writer trên mỗi workspace;
- trạng thái “Đang chờ”, “Đang làm”, “Cần bạn bổ sung”, “Đã xong”, “Chưa đạt kiểm thử”, “Đã hoàn tác” đúng;
- không sửa JSON hoặc chọn từng quyền;
- `diff`, terminal, digest và mã lỗi nằm trong chi tiết đóng mặc định.

## 8. G6 — An toàn, tương thích và cổng đầy đủ

```powershell
uv run --no-sync --group dev python -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version"
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
```

Ngoài ra phải kiểm tra:

- test của `antigravity_bridge.py` và Workspace Chat vẫn đạt;
- không secret, traceback, đường dẫn tuyệt đối hoặc transcript thô trên UI/Case;
- đường dẫn Windows có khoảng trắng/tiếng Việt không lỗi;
- restart không lặp thao tác ghi;
- reviewer độc lập đối chiếu SC-001–SC-007 trước khi đổi Goal thành `DONE`.

## 9. Ma trận kết quả tối thiểu

| Tình huống | File thật | Trạng thái | Người dùng thấy |
|---|---|---|---|
| Báo cáo đủ số liệu | Bản nháp mới | `completed` | Báo cáo, biểu đồ, nguồn, hoàn tác |
| Báo cáo thiếu số liệu | Bản nháp mới | `completed_with_warning` | Nói rõ thiếu gì, không có biểu đồ giả |
| Công đoạn có mâu thuẫn | Bản nháp mới | `needs_input` hoặc `completed` | Hai nguồn mâu thuẫn và câu hỏi cần xác nhận |
| Sửa mã, test đạt | Chỉ worktree trước khi dùng | `completed` | Tóm tắt, kết quả test, dùng/hoàn tác |
| Sửa mã, test lỗi | Main workspace không đổi | `verification_failed` | Lỗi dễ hiểu và việc nên làm tiếp |
| Action ngoài scope | Không đổi | `blocked` | Giải thích tiếng Việt, không lộ chi tiết nhạy cảm |
| Runtime mất kết nối khi ghi | Không tự lặp | `interrupted_unknown` | Đang đối chiếu hoặc cần người dùng quyết định |

Không dòng nào được ghi PASS chỉ dựa trên lời model, report tự khai hoặc checkbox giao diện.
