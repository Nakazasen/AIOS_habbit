# Hợp đồng giao tiếp runtime Agent

## 1. Phạm vi

Hợp đồng này là ranh giới giữa AIOS và runtime OpenCode trong Goal 009.

- AIOS quyết định nhiệm vụ, nguồn, vùng file, privacy route, quyền tự động, checkpoint, verifier và kết quả trình bày.
- Runtime thực hiện session, vòng model–tool, event, thao tác file và command trong vùng đã cấp.
- Workspace Chat không gọi runtime trực tiếp.
- `antigravity_bridge.py` tiếp tục là tuyến nguồn AI của Workspace Chat và không bị thay bởi hợp đồng này.
- Bridge NVIDIA cũ không đáp ứng hợp đồng và không được nối tắt vào đường mới.

## 2. Capability bắt buộc ở G1

Adapter chỉ được tạo sau khi bản OpenCode đã pin chứng minh được:

- health và version;
- tạo, đọc, tiếp tục và hủy session;
- event stream hoặc cơ chế theo dõi trạng thái tương đương;
- read/search trong task root;
- create/edit file trong task root;
- chạy lệnh test được phép với timeout và exit code;
- đọc trạng thái thay đổi để checkpoint/undo;
- từ chối path ngoài root, secret và command bị cấm trước thực thi.

Probe chỉ đọc không đủ điều kiện G1.

## 3. Request chung

```json
{
  "schema_version": "aios_agent_runtime_v1",
  "request_id": "REQ-...",
  "work_id": "WORK-...",
  "session_id": "RUNTIME-...",
  "action": "edit_file",
  "scope_digest": "sha256:...",
  "idempotency_key": "...",
  "payload": {}
}
```

Action tối thiểu:

```text
health
create_session
get_session
list_events
read_file
search_files
create_file
edit_file
run_test
get_workspace_state
abort_session
```

## 4. Event và receipt

Mỗi event AIOS lưu phải có:

- `work_id`, `session_id`, `event_id`, `sequence`;
- `event_type`, `action`, `status`;
- `observed_at`, `payload_digest`, `previous_event_digest`;
- payload đã làm sạch hoặc locator cục bộ khi nội dung không được đưa vào Case.

Cùng `idempotency_key` và cùng payload trả receipt cũ. Cùng key nhưng payload khác bị từ chối.

## 5. Quyền tự động theo vùng

Runtime có thể tự động thực hiện action khi tất cả điều kiện đều đúng:

1. `scope_digest` còn hiệu lực và khớp nhiệm vụ.
2. Đường dẫn sau chuẩn hóa nằm trong task root.
3. Action có trong `allowed_actions`.
4. Command khớp `allowed_commands` nếu là `run_test`.
5. Privacy route cho phép dữ liệu đi tới provider đang dùng.
6. Checkpoint trước thao tác ghi đã tồn tại.

Không yêu cầu prompt xác nhận từng action hợp lệ. Các action sau luôn bị từ chối ở MVP:

- đọc `.env`, secret store hoặc vùng dữ liệu ngoài phạm vi;
- quyền quản trị hoặc sửa hệ thống;
- commit, push, merge, deploy;
- gửi dữ liệu qua provider route không hợp lệ;
- xóa/đổi tên hàng loạt hoặc sửa tài liệu công đoạn chính thức.

## 6. Thao tác file và command

- Path luôn là đường dẫn tương đối đã chuẩn hóa; path traversal và symlink thoát root bị từ chối.
- Mã nguồn chỉ được ghi trong worktree của nhiệm vụ.
- Báo cáo và tài liệu chỉ được ghi vào vùng bản nháp đã cấp.
- Command được biểu diễn bằng executable và danh sách argument chuẩn hóa; không truyền raw shell string từ lời model.
- Timeout phải dừng cây tiến trình và ghi trạng thái còn sót nếu không xác minh được đã dừng sạch.

## 7. Resume và trạng thái chưa rõ

- Mất kết nối khi đang read/search có thể retry bằng cùng idempotency key.
- Mất kết nối khi đang write/command chuyển `interrupted_unknown`.
- Resume phải đối chiếu session, process, workspace digest và receipt trước khi tiếp tục.
- Không tự lặp write/command chưa rõ kết quả.

## 8. Xác minh theo loại đầu ra

Runtime có thể cung cấp summary, nhưng AIOS tự quan sát:

- task mã: filesystem/Git, file digest, command, exit code và timeout;
- task báo cáo: section, citation, dữ liệu bảng/biểu đồ và phép tổng hợp;
- task thiết kế công đoạn: source location, nhãn evidence và trạng thái bản nháp.

Checkbox UI và lời model không tạo bằng chứng đạt.

## 9. Dùng kết quả và hoàn tác

- Báo cáo và rà soát công đoạn được tự lưu dưới dạng bản nháp sau verification.
- Kết quả mã chỉ được đưa từ worktree sang workspace chính khi checkpoint, manifest và trạng thái hiện tại không xung đột.
- Xung đột giữ nguyên kết quả trong worktree và trả hướng dẫn tiếng Việt; không ghi đè.
- Hoàn tác dùng checkpoint của nhiệm vụ, không gọi `git reset --hard`, không viết lại lịch sử và không xóa thay đổi có trước.

## 10. Ranh giới dữ liệu và transport

- Server chỉ bind loopback và dùng xác thực cục bộ nếu runtime hỗ trợ.
- Không truyền toàn bộ `os.environ`; adapter chỉ cấp biến cần thiết theo allowlist.
- Runtime không nhận `local_cases/`, `local_runs/`, `.env`, secret hoặc dữ liệu `local_only` ngoài phạm vi/provider route được phép.
- Transcript, raw `diff` và stdout/stderr không đi vào hồ sơ Case.

## 11. Hợp đồng lỗi

Mọi lỗi được ánh xạ theo [hợp đồng báo cáo lỗi](agent-error-report-v1.md). UI chỉ nhận bản tiếng Việt đã làm sạch, trạng thái resume/rollback và hành động tiếp theo; không nhận traceback hoặc đường dẫn tuyệt đối.

## 12. Tương thích

- Reader `aios_agent_task_pack_v1` và `aios_agent_report_v1` tiếp tục đọc artifact lịch sử theo nghĩa cũ.
- Session/proposal trong RAM từ bridge NVIDIA hết hiệu lực khi restart và không được chuyển thành grant OpenCode.
- Thêm runtime khác chỉ sau khi OpenCode không đạt G1 hoặc có giới hạn được đo bằng cùng fixture.
