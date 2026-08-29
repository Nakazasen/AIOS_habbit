# AIOS WorkLens

AIOS WorkLens là Workspace Chat ưu tiên cục bộ: người dùng nạp tài liệu công việc,
hỏi bằng ngôn ngữ tự nhiên và kiểm tra bằng chứng đã dùng trong câu trả lời.

Tài liệu sản phẩm viết **tiếng Việt**. Tên file, lệnh và hằng kỹ thuật giữ nguyên
tiếng Anh. Lối vào cho agent: [`AGENTS.md`](AGENTS.md).

## Chức năng hiện có

- Workspace Chat quản lý nguồn theo sổ tài liệu và từng cuộc trò chuyện.
- Tìm kiếm hybrid BGE-M3 cục bộ khi máy có gói model đã được xác thực.
- Giao diện và ngôn ngữ trả lời: Tiếng Việt, 日本語, 简体中文.
- Lưu vết bằng chứng `rag-trace/v1` gắn với tin nhắn trả lời.
- Nút xem đồ thị bằng chứng khi câu trả lời có trích dẫn hợp lệ.
- Mã đóng gói Desktop/VPS với Graphify và ExcaliFlow được ghim phiên bản.

Đồ thị bằng chứng giúp xem AI đã dựa vào những đoạn nào. Nó không biến một câu
trả lời không có trích dẫn thành câu đã được kiểm chứng.

## Trạng thái và giới hạn

- `Workspace Chat` là giao diện dành cho người dùng. Case Cockpit và Habit Studio
  cũ không còn thuộc luồng thông thường.
- Bộ wheel offline Windows/Linux lưu qua Git LFS. Cần `git lfs pull` trước khi
  cài hoặc build offline.
- Model BGE-M3 không nằm trong Git. Khi build Desktop, chương trình kiểm tra
  revision và checksum; thiếu hoặc hỏng thì dừng rõ, không giả vờ đã tìm được tài liệu.
- Mã và test đóng gói đã có trong repo. Trước khi dùng production, kiểm tra gói
  cuối trên đúng máy/VPS đích.

## Bắt đầu nhanh trên Windows

Cần Git, Git LFS, Python **3.11** và `uv`.

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

Nếu BGE-M3 chưa sẵn sàng, làm theo runbook model pack trước khi kỳ vọng tìm được
câu trả lời từ tài liệu. Ứng dụng phải báo tình trạng này, không âm thầm giả vờ đã tìm.

## Kiểm tra dành cho developer

```powershell
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
git diff --check
git status --short
```

## Tài liệu

- [Hiến chương](CONSTITUTION.md)
- [Lối vào agent](AGENTS.md)
- [Roadmap](ROADMAP.md)
- [Bàn giao](PROJECT_HANDOVER.md)
- [Kiến trúc](ARCHITECTURE.md)
- [Bản đồ tài liệu](docs/PROFESSIONALIZATION_INDEX.md)
- [Đóng gói Desktop](packaging/desktop/README.md)
- [Triển khai VPS](packaging/vps/README.md)
- [Runbook vận hành](docs/runbooks/operator.md)
- [Runbook developer](docs/runbooks/developer.md)

## An toàn dữ liệu cục bộ

Không commit dữ liệu runtime hoặc nguồn riêng tư: `local_cases/`, `local_runs/`,
JSONL bằng chứng/bộ nhớ, tài liệu đã tải lên, ảnh chụp, `.env`, credentials,
tokens hoặc cache. Trước khi gửi tài liệu nội bộ ra ngoài máy, phải kiểm tra cấu
hình nhà cung cấp AI và cầu nối đang chọn.
