# Hướng dẫn kiểm chứng: Vòng trí nhớ công việc thích nghi

## 1. Điều kiện vào

1. Dùng Python 3.11.
2. Bảo toàn `local_cases/`, `.env`, dữ liệu thật và file chưa được theo dõi của người dùng.
3. Không yêu cầu Goal 010 hoàn tất. Nếu thư viện Goal 010 không tồn tại hoặc chưa có artifact đủ điều kiện, xác nhận adapter trả candidate rỗng và các nguồn khác vẫn hoạt động.

```powershell
uv run --no-sync --group dev python -c "import sys; print(sys.version); raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
git status --short
```

## 2. Kịch bản A — MVP gọi lại chỉ đọc

Fixture phải có đúng 30 tình huống gắn nhãn: 20 câu có bài học liên quan và 10 câu không liên quan. Nhóm này phải bao phủ verified/draft MemoryUnit, confirmed SeniorLearningCard, approved/revoked CaseLesson, published/revoked Goal 010 artifact, no-match và conflict. US1 không chứa `MemoryDecision` của người dùng.

```powershell
uv run --no-sync --group dev pytest -q tests/test_workspace_memory_recall.py tests/test_workspace_chat_ai_answer.py
```

Kết quả mong đợi:

- Chỉ item đủ điều kiện được trả về.
- Ít nhất 18/20 câu liên quan gọi lại đúng ít nhất một mục và 10/10 câu không liên quan không bị chèn trí nhớ.
- No-match giữ baseline và không có block “Sổ việc”.
- Conflict không chọn bên thắng.
- Feature flag tắt tạo baseline prompt.
- Direct provider và bridge cùng dùng một memory result.

## 3. Kịch bản B — Riêng tư và consent

```powershell
uv run --no-sync --group dev pytest -q tests/test_workspace_memory_recall.py -k "privacy or consent or local_only or prompt_injection"
```

Kết quả mong đợi:

- Cloud không nhận `local_only`/không export.
- Local chỉ nhận `local_only` khi chọn rõ.
- Thay đổi item làm fingerprint cũ hết hiệu lực.
- Delimiter/role marker trong memory không đổi system instruction.

## 4. Kịch bản C — Nhớ và quên

```powershell
uv run --no-sync --group dev pytest -q tests/test_workspace_memory_commands.py
```

Kết quả mong đợi:

- Chưa xác nhận thì không có durable record.
- Confirm idempotent qua restart.
- Hai tiến trình cùng ghi phải đi qua `LibraryWriterLease`; tiến trình không lấy được lease fail-closed và không tạo dòng JSONL dở dang.
- Forget/revoke ngừng recall ngay và vẫn giữ audit history.

## 5. Kịch bản D — Sửa sai thành bài học

```powershell
uv run --no-sync --group dev pytest -q tests/test_workspace_memory_corrections.py
```

Kết quả mong đợi:

- Candidate không ảnh hưởng câu hỏi khác.
- Confirmed correction được gọi lại ở phiên mới.
- Duplicate/conflict bắt buộc quyết định rõ.
- Không persist raw assistant answer/transcript.

## 6. Benchmark máy không GPU

```powershell
uv run --no-sync --group dev python scripts/benchmark_workspace_memory_recall.py --items 10000 --runs 100 --json-out local_runs/workspace_memory_benchmark.json
```

PASS khi p95 dưới 500 ms, tăng working set không quá 200 MB và output xác nhận không tải model/GPU.

## 7. Kiểm tra giao diện thủ công

1. Bật feature flag trong runtime thử nghiệm, không dùng dữ liệu thật.
2. Hỏi một câu có bài học liên quan và mở “Vì sao AIOS nhớ điều này?”.
3. Hỏi câu không liên quan và xác nhận không có mục nhớ rỗng.
4. Thử “Hãy nhớ:”, “Hãy quên:” và “Sửa để AIOS học”; hủy trước xác nhận rồi kiểm tra không persist.
5. Restart ứng dụng và xác nhận bài đã nhớ còn dùng được, bài đã quên không quay lại.
6. Xác nhận mọi nhãn/lỗi tiếng Việt, không lộ engine/path/traceback.

## 8. Cổng đầy đủ

```powershell
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py
git diff --check
```

Sau thay đổi code:

```powershell
graphify update .
```

## 9. Bàn giao kiểm toán

Execution Specialist phải cung cấp: task IDs đã làm, file đã sửa, test/lệnh/mã thoát, artifact benchmark, thay đổi dữ liệu/migration, rollback, rủi ro và `git diff --stat`. Không tự đánh dấu task kiểm toán độc lập hoặc tuyên bố Goal hoàn thành.
