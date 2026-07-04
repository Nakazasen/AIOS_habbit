# Master Project Index

## Purpose

Lưu danh mục project đã biết, trạng thái, vai trò trong hệ tri thức và quan hệ giữa các project.

## Critical Rule

Danh sách dưới đây là seed list ban đầu, **không được coi là đầy đủ**. Phase 1 phải tự khám phá project mới.

## Known Seed Projects

| Project | Path | Status | Role | Evidence Status | Notes |
|---|---|---|---|---|---|
| AIOS_habbit | `[LOCAL_WORKSPACE]\AIOS_habbit` | active | Main project | candidate | Repository mục tiêu của nền tảng memory |
| MP2027 | `<LOCAL_PROJECT_PATH>` | unknown | Related project | candidate | Cần Phase 1 inventory |
| Master Knowledge Manager System (MKMS) | `<LOCAL_PROJECT_PATH>` | unknown | Related knowledge system | candidate | Có thể liên quan trực tiếp đến AIOS Habit |
| ABW_NVIDIA_FUSION_CONTROL | `<LOCAL_PROJECT_PATH>` | unknown | Related project | candidate | Cần inventory |
| Nvidia | `<LOCAL_PROJECT_PATH>` | unknown | Related project | candidate | Cần inventory |
| skill-Anti-brain-wiki_note | `[LOCAL_WORKSPACE]\skill-Anti-brain-wiki_note` | unknown | Related skill/project | candidate | Cần inventory |

## Project Card Requirements

Mỗi project sau Phase 1 phải có:

- Project name.
- Local path.
- Purpose.
- Status.
- Owner/role.
- Key files.
- Memory relevance.
- Evidence records.
- Open risks.
- Handover link.

## Discovery Strategy

Phase 1 phải scan các root được người dùng cho phép, tìm marker:

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

## Project Relationship Types

- `parent`
- `child`
- `dependency`
- `knowledge-source`
- `execution-target`
- `archive`
- `unknown`

## Open Tasks for Phase 1

- Validate all seed project paths.
- Discover additional projects under allowed roots.
- Create project cards.
- Separate active, archived, experimental and unknown projects.


