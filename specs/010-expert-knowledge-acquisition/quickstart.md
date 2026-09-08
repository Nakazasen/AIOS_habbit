# Kịch bản triển khai và xác minh

## 1. Nguyên tắc chạy

- Gemini Flash 3.8 chạy vai trò `Execution Specialist`; một agent/phiên tách biệt chạy audit sau từng cổng và tự trả finding để sửa.
- Mỗi lần chỉ có một cổng `IN_PROGRESS`; không code cổng sau khi cổng trước chưa có receipt.
- Toàn Goal kỹ thuật dùng fixture giả lập; dữ liệu/chuyên gia thật chỉ vào vận hành sau `TECHNICAL_READY` và không chặn chuỗi triển khai.
- Không commit/push tự động. Chỉ thực hiện khi chủ sở hữu yêu cầu rõ và sau khi quét dữ liệu riêng tư.

## 2. Khởi động một lượt Goal

```powershell
Set-Location D:\Sandbox\AIOS_habbit
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
git status --short --branch
Get-Content .\AGENTS.md -Encoding UTF8
Get-Content .\CONSTITUTION.md -Encoding UTF8
Get-Content .\AGENT_RULES.md -Encoding UTF8
Get-Content .\specs\010-expert-knowledge-acquisition\GEMINI_FLASH_3_8_GOAL.md -Encoding UTF8
```

Không xóa, stage hoặc sửa file không thuộc allowlist của cổng hiện tại. Đặc biệt không chạm dữ liệu trong `local_cases/`, `local_runs/`, `.env` hoặc file khóa ứng dụng.

## 3. Chu kỳ cho từng cổng

1. Đọc task của cổng, contract và code liên quan.
2. Ghi baseline `git status`, test trọng điểm và blocker hiện có.
3. Implement tối thiểu theo task; không mở feature ngoài scope.
4. Chạy test trọng điểm và negative test của cổng.
5. Ghi evidence vào Gate Card: command, exit code, phạm vi, digest/fixture, giới hạn.
6. Agent audit độc lập kết luận `PASS` hoặc `NEEDS_FIX`.
7. Khi `NEEDS_FIX`, agent thực thi tự sửa rồi audit lại; khi `PASS`, tự chuyển cổng kế tiếp.

## 4. Kịch bản demo bắt buộc

### Demo A — Từ khoảng trống tới chat thích nghi

1. Nạp corpus fixture có một quy tắc thiếu ngưỡng, một nguồn mâu thuẫn và một nguồn lỗi thời.
2. Chạy coverage; reviewer accept gap thiếu ngưỡng.
3. Identity fixture ánh xạ đúng expert/scope; thử một intruder bị deny.
4. Tạo InterviewPlan và bắt đầu chat.
5. Chuyên gia trả lời “khi thấy cao thì dừng”; C-AGENT qua Brain Gateway phải hỏi ngưỡng, đơn vị và ngoại lệ.
6. Chuyên gia trả lời `uncertain`; phiên phải ghi uncertainty, không tự điền số.
7. Pause, restart app, resume đúng checkpoint và không lặp câu hỏi.

### Demo B — Audio và xác nhận thuật ngữ

1. Từ chối consent: record bị deny nhưng chat text vẫn dùng được.
2. Đồng ý consent: chỉ báo ghi xuất hiện và audio lưu ở local-only root.
3. Chép audio fixture có mã máy, số đo và tiếng ồn.
4. Sửa critical tokens, xác nhận từng mã/số/đơn vị.
5. Rút consent; capture dừng và receipt phản ánh policy retention.
6. Quét Git/DB/provider payload: không có raw audio/transcript.

### Demo C — SOP, duyệt và xuất bản

1. Trích claim từ turn/segment; tạo một claim confirmed và một conflict.
2. Sinh SOP candidate; conflict chỉ ở mục cần quyết định.
3. Thử publish trước duyệt: bị deny.
4. Duyệt đúng actor/scope/digest; sửa artifact sau duyệt rồi publish: bị stale deny.
5. Duyệt version mới; backup, lease, ingest và `quick_check` đạt.
6. Hỏi acceptance questions; câu trả lời có citation tới artifact mới.
7. Revoke; retrieval thường không dùng phiên bản đã thu hồi.

### Demo D — Báo cáo fine-tune

1. Đo retrieval/prompt baseline trên tập holdout.
2. Chạy eligibility rubric.
3. Khi thiếu dữ liệu hoặc không có lợi ích rõ, kết quả phải là `NOT_APPLICABLE` và không có training job.
4. Nếu đủ toàn bộ điều kiện, chỉ tạo đề xuất/Gate Card mới; vẫn không train trong feature 010.

## 5. Test trọng điểm dự kiến

```powershell
uv run --no-sync --group dev pytest tests/test_expert_identity.py -q
uv run --no-sync --group dev pytest tests/test_knowledge_coverage.py -q
uv run --no-sync --group dev pytest tests/test_adaptive_expert_interview.py -q
uv run --no-sync --group dev pytest tests/test_local_transcription.py -q
uv run --no-sync --group dev pytest tests/test_knowledge_claims.py -q
uv run --no-sync --group dev pytest tests/test_knowledge_publication.py -q
uv run --no-sync --group dev pytest tests/test_expert_knowledge_e2e.py -q
```

File test chưa tồn tại ở G0; task tương ứng phải tạo trước khi chạy. Không đổi tên/xóa assertion để lấy PASS.

## 6. Quality gate trước khi đóng feature

Xác nhận Python 3.11 rồi chạy:

```powershell
uv run --no-sync --group dev python -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version"
uv run --no-sync --group dev python scripts/check_docs.py
uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

Sau đó chạy privacy scan được mô tả trong Gate Card, E2E Windows trên đường dẫn có dấu/khoảng trắng và diễn tập fixture trọn vòng. Full suite bỏ bớt có chủ ý phải được ghi là phạm vi chưa kiểm chứng, không được đổi thành PASS toàn bộ.

## 7. Quy tắc tiếp tục không chờ quyết định

- Thiếu tài khoản OS thật: giữ multi-user runtime tắt, hoàn tất contract bằng fixture và tiếp tục.
- Thiếu microphone/engine thật: giữ audio runtime tắt, hoàn tất adapter/fixture và tiếp tục chat chữ.
- Fine-tune: luôn `NOT_APPLICABLE` trong feature 010, không mở câu hỏi quyết định.
- Finding audit trong phạm vi: tự sửa và chạy lại.
- Lỗi baseline ngoài phạm vi: ghi tách biệt, không nhận là PASS nhưng tiếp tục test trọng điểm feature.
- Worktree có thay đổi người dùng trùng file mục tiêu hoặc có nguy cơ mất dữ liệu: không ghi đè; chuyển phần việc sang worktree/patch tách biệt và tiếp tục phần an toàn.

Không có checkpoint chờ con người giữa G0–G10. Chỉ sự cố hạ tầng thực sự không thể khắc phục an toàn mới được báo giới hạn cuối; không hạ chuẩn privacy/quyền để tránh dừng.
