# AIOS WorkLens

[English](README.md)

AIOS WorkLens là Workspace Chat theo hướng local-first: người dùng nạp tài liệu
công việc, hỏi bằng ngôn ngữ tự nhiên và kiểm tra lại bằng chứng đã dùng trong
câu trả lời.

## Chức năng hiện có

- Workspace Chat quản lý nguồn theo sổ tài liệu và từng cuộc trò chuyện.
- Tìm kiếm hybrid BGE-M3 cục bộ khi máy có model pack đã được xác thực.
- Giao diện và ngôn ngữ trả lời: Tiếng Việt, 日本語, 简体中文.
- Lưu vết bằng chứng `rag-trace/v1` gắn với tin nhắn trả lời.
- Nút xem Đồ thị bằng chứng theo yêu cầu, chỉ dùng được khi câu trả lời có
  trích dẫn hợp lệ.
- Mã đóng gói Desktop/VPS với Graphify và ExcaliFlow được ghim phiên bản.

Đồ thị bằng chứng giúp xem AI đã dựa vào những đoạn nào. Nó không biến một câu
trả lời không có trích dẫn thành câu trả lời đã được kiểm chứng.

## Trạng thái và giới hạn cần biết

- `Workspace Chat` là giao diện dành cho người dùng. Case Cockpit và Habit
  Studio cũ không còn thuộc luồng sử dụng thông thường.
- Bộ wheel offline Windows/Linux được lưu qua Git LFS. Cần tải LFS xong trước
  khi cài hoặc build ở chế độ offline.
- Model BGE-M3 không nằm trong Git repository. Khi build Desktop, chương trình
  kiểm tra revision và checksum; thiếu hoặc hỏng model thì build sẽ dừng rõ
  ràng, không giả vờ tìm kiếm tài liệu.
- Mã và test đóng gói Desktop/VPS đã có trong repository. Trước khi dùng cho
  production, vẫn phải kiểm tra gói cuối cùng trên đúng máy/VPS đích.

## Bắt đầu nhanh trên Windows

Cần có Git, Git LFS, Python **3.11** và `uv`.

```powershell
git clone https://github.com/Nakazasen/AIOS_habbit.git
cd AIOS_habbit
git lfs install
git lfs pull
uv sync --group dev
```

Mở Workspace Chat:

```powershell
.\RUN_AIOS_WORKSPACE_CHAT.bat
```

Hoặc:

```powershell
.\scripts\run_workspace_chat.ps1
```

Nếu BGE-M3 chưa sẵn sàng, hãy làm theo runbook về model pack và retrieval trước
khi kỳ vọng hệ thống tìm được câu trả lời từ tài liệu. AIOS phải báo tình trạng
này rõ ràng thay vì âm thầm trả lời như thể đã tìm kiếm.

## Kiểm tra dành cho developer

```powershell
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
git diff --check
git status --short
```

## Tài liệu

- [README tiếng Anh](README.md)
- [Roadmap và trạng thái chuẩn](ROADMAP.md)
- [Bàn giao dự án](PROJECT_HANDOVER.md)
- [Kiến trúc Workspace](WORKLENS_ARCHITECTURE.md)
- [Đóng gói Desktop](packaging/desktop/README.md)
- [Triển khai VPS](packaging/vps/README.md)
- [Runbook vận hành](docs/runbooks/operator.md)
- [Runbook developer](docs/runbooks/developer.md)

## An toàn dữ liệu cục bộ

Không commit dữ liệu runtime hoặc nguồn riêng tư: `local_cases/`, `local_runs/`,
JSONL evidence/memory, tài liệu đã tải lên, ảnh chụp, `.env`, credentials,
tokens hoặc cache. Trước khi gửi tài liệu nội bộ ra ngoài máy, phải kiểm tra cấu
hình provider và cầu nối AI đang được chọn.
