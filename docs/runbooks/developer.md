# Sổ Tay Dành Cho Nhà Phát Triển (Developer Runbook)

Status: `ACTIVE`
Owner role: Maintainer / release reviewer
Last reviewed: 2026-08-16
Review cadence: Every Gate Card closure and release candidate

## Thiết Lập (Setup)

```powershell
uv sync --group dev
```

`uv run --group dev pytest -q` là lệnh kiểm thử được hỗ trợ. Lệnh này cài đặt test runner từ biểu đồ phụ thuộc đã khóa thay vì dựa vào bản cài đặt Python toàn cục.

## Xác Thực Bắt Buộc (Required validation)

```powershell
uv run --no-sync --group dev python scripts/check_docs.py
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
git status --short --ignored
```

## Quy Trình Làm Việc (Workflow)

1. Đọc `ROADMAP.md`, Thẻ Cổng (Gate Card) đang hoạt động và các ADR/yêu cầu/hợp đồng liên quan trước khi triển khai.
2. Giữ các thay đổi mã/tài liệu trong danh sách cho phép của Cổng; không ngầm mở các công việc RAG/A18/P1.0 đã được lên kế hoạch.
3. Chỉ sử dụng các fixture giả lập (synthetic). Không stage dữ liệu riêng tư/runtime, khóa, tài liệu thô, ảnh chụp màn hình, header provider hoặc `local_cases/`/`local_runs/`.
4. Thêm các bài kiểm thử hồi quy tập trung, sau đó chạy tất cả các bước xác thực bắt buộc.
5. Chỉ ghi lại bằng chứng hiện tại trong lộ trình/bàn giao/nhật ký thay đổi chuẩn tắc sau khi đã vượt qua kiểm thử. Một Cổng không được coi là `DONE` nếu thiếu bằng chứng hoàn tác và đánh giá.

## Phát Hành Và Bảo Trì (Release and maintenance)

Sử dụng [cổng chất lượng (quality gates)](../quality/QUALITY_GATES.md), [danh mục kiểm tra phát hành (release checklist)](../release/RELEASE_CHECKLIST.md), [chính sách phụ thuộc (dependency policy)](../security/DEPENDENCY_POLICY.md) và [hướng dẫn đóng góp (contributing guide)](../../CONTRIBUTING.md). Đối với thay đổi tuyến quyền riêng tư/provider, hãy đọc các bản ghi mối đe dọa/quyền riêng tư và Thẻ Cổng hợp nhất chính sách P0 trước.

