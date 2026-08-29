# Chỉ mục Dự án Tổng thể (Master Project Index)

> Không phải luật sản phẩm. Lối vào: `AGENTS.md`. Bản đồ tài liệu: `docs/PROFESSIONALIZATION_INDEX.md`.

## Mục đích

Lưu danh mục dự án đã biết, trạng thái, vai trò trong hệ tri thức và quan hệ giữa các dự án.

## Quy tắc Cốt lõi (Critical Rule)

Danh sách dưới đây là seed list ban đầu, **không được coi là đầy đủ**. Giai đoạn 1 (Phase 1) phải tự khám phá dự án mới.

## Các Dự án Hạt giống Đã biết (Known Seed Projects)

| Dự án | Đường dẫn | Trạng thái | Vai trò | Trạng thái Bằng chứng | Ghi chú |
|---|---|---|---|---|---|
| AIOS_habbit | `[LOCAL_WORKSPACE]\AIOS_habbit` | active | Dự án chính | candidate | Repository mục tiêu của nền tảng memory |
| MP2027 | `<LOCAL_PROJECT_PATH>` | unknown | Dự án liên quan | candidate | Cần Phase 1 inventory |
| Master Knowledge Manager System (MKMS) | `<LOCAL_PROJECT_PATH>` | unknown | Hệ thống tri thức liên quan | candidate | Có thể liên quan trực tiếp đến AIOS Habit |
| ABW_NVIDIA_FUSION_CONTROL | `<LOCAL_PROJECT_PATH>` | unknown | Dự án liên quan | candidate | Cần inventory |
| Nvidia | `<LOCAL_PROJECT_PATH>` | unknown | Dự án liên quan | candidate | Cần inventory |
| skill-Anti-brain-wiki_note | `[LOCAL_WORKSPACE]\skill-Anti-brain-wiki_note` | unknown | Kỹ năng/dự án liên quan | candidate | Cần inventory |

## Yêu cầu Thẻ Dự án (Project Card Requirements)

Mỗi dự án sau Phase 1 phải có:

- Tên dự án (Project name).
- Đường dẫn cục bộ (Local path).
- Mục đích (Purpose).
- Trạng thái (Status).
- Chủ sở hữu / vai trò (Owner/role).
- Các tệp quan trọng (Key files).
- Mức độ liên quan bộ nhớ (Memory relevance).
- Hồ sơ bằng chứng (Evidence records).
- Rủi ro chưa xử lý (Open risks).
- Liên kết bàn giao (Handover link).

## Chiến lược Khám phá (Discovery Strategy)

Phase 1 phải quét các root được người dùng cho phép, tìm các dấu hiệu nhận diện:

- `.git/`
- `README.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `ARCHITECTURE.md`
- `AGENT_RULES.md`
- `docs/`
- `prompts/`
- `specs/`
- `pyproject.toml`
- `package.json`

## Các Loại Quan hệ Dự án (Project Relationship Types)

- `parent` (cha)
- `child` (con)
- `dependency` (phụ thuộc)
- `knowledge-source` (nguồn tri thức)
- `execution-target` (mục tiêu thực thi)
- `archive` (lưu trữ)
- `unknown` (chưa xác định)

## Nhiệm vụ Mở cho Phase 1

- Xác thực tất cả các đường dẫn dự án hạt giống.
- Khám phá các dự án bổ sung trong các thư mục gốc được cho phép.
- Tạo các thẻ dự án (project cards).
- Phân tách rõ ràng các dự án đang hoạt động, đã lưu trữ, thử nghiệm và chưa xác định.



