<!--
Báo cáo tác động đồng bộ
- Đổi phiên bản: 1.0.0 → 1.1.0
- Nguyên tắc sửa đổi: IV — chỉ dùng tiếng Việt trên bề mặt người dùng
- Quy trình sửa đổi: khóa Python 3.11 qua uv và runtime thử nghiệm tách dữ liệu thật
- Tài liệu đã đồng bộ: AGENTS.md, AGENT_RULES.md, đặc tả/kế hoạch 008
- Nội dung bị xóa: không có
- Việc còn chờ: không có
-->
# AIOS WorkLens Constitution

## Core Principles

### I. Evidence Before Assertion
Every durable memory, user-facing answer, PASS result, and project decision MUST
cite an evidence record or a reviewable artifact. A claim without sufficient
evidence MUST remain `candidate`, `PARTIAL`, `FAIL`, or `BLOCKED`; it MUST NOT be
presented as verified. Raw AI output is not evidence unless its original source
is retained and traceable. This protects the platform from invented knowledge
and false completion signals.

### II. Local-First Privacy and Consent
User data, local evidence, raw transcripts, spreadsheets, logs, screenshots,
and private configuration MUST remain local by default. `local_only` content and
unconfirmed learning material MUST NOT enter an external-cloud prompt, export,
or handover. Cloud use requires an explicit policy and the user's affirmative
consent; local AI use requires the explicit `include_local_only=True` choice
when applicable. Private runtime data, credentials, `.env`, and local case data
MUST NOT be committed to version control.

### III. Portable, Pattern-Based Knowledge
The product MUST preserve validated operational patterns rather than archival
chat wording. Durable knowledge MUST use documented open formats such as
Markdown, JSON, or YAML with a clear schema and provenance. No core knowledge
workflow may depend exclusively on one AI provider, opaque proprietary memory,
or non-exportable conversation history. This keeps the user's knowledge usable
across models and over time.

### IV. Workspace Chat dành cho người dùng không chuyên
Workspace Chat là giao diện được hỗ trợ. Tiếng Việt dễ hiểu là ngôn ngữ duy nhất
trên giao diện, hướng dẫn, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo.
Lỗi từ thư viện hoặc dịch vụ bên ngoài phải được chặn và đổi thành lời giải thích
cùng bước xử lý bằng tiếng Việt; không được hiện câu tiếng Anh hoặc traceback.
Tài liệu nguồn ngoại ngữ có thể giữ nguyên để bảo toàn bằng chứng. Công việc mới
không được khôi phục đường dẫn, import, launcher hoặc kỳ vọng kiểm thử của Case
Cockpit hay Habit Studio nếu chưa có quyết định kiến trúc được phê duyệt rõ ràng.

### V. Change Discipline and Verifiable Quality
Every non-trivial change MUST be audited and designed before implementation,
executed against an approved plan, covered by proportionate tests, and validated
with reproducible commands. Architecture, roadmap, and behavioral changes MUST
update their respective canonical records: `ARCHITECTURE.md`, `ROADMAP.md`, and
`PROJECT_HANDOVER.md`. A phase MUST be closed with recorded evidence before a
subsequent phase opens.

## Operational Constraints

- Python support MUST remain compatible with the declared project requirement
  (`>=3.11`), and dependencies MUST be managed through `pyproject.toml` and
  `uv.lock`.
- Supported modules MUST NOT import retired `studio` or `case_cockpit` code.
  Removing a legacy slice MUST remove its supported launch path and stale tests.
- New durable memory MUST follow this provenance path: `Raw Source → Evidence
  Record → Extracted Pattern → Validated Memory → Export Profile`.
- The priority order for conflicts is: user-data safety; evidence and
  correctness; long-term portability; extensibility; delivery speed.
- Complexity, external integrations, and data egress MUST have a documented
  rationale and a safe rollback or remediation path.

## Quy trình phát triển và cổng chất lượng

1. Công việc tính năng phải bắt đầu bằng `/speckit-specify`; thay đổi kiến trúc
   hoặc nhiều bước phải tiếp tục qua `/speckit-plan` và `/speckit-tasks` trước
   `/speckit-implement`.
2. Trước khi hợp nhất hoặc phát hành, thay đổi liên quan phải chạy bằng Python
   3.11 và đạt: `uv run --no-sync --group dev python -m compileall src tests`,
   `uv run --no-sync --group dev pytest -q`,
   `uv run --no-sync --group dev python -m aios_habit.cli audit`, và
   `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`.
3. CLI audit phải trả `"status": "PASS"`; nếu không, thay đổi phải ghi `FAIL`,
   `BLOCKED` hoặc `PARTIAL` cùng hành động khắc phục tiếp theo.
4. Người kiểm toán phải xem file đã sửa, bằng chứng test, ranh giới riêng tư và
   ảnh hưởng migration/rollback. Tác tử chỉ kiểm toán không được viết code tính
   năng trừ khi người dùng cho phép một sửa chữa nhỏ.
5. Khi có `graphify-out/graph.json`, điều tra implementation và kiến trúc phải
   hỏi graph trước khi đọc rộng; thay đổi code phải chạy `graphify update .`.

## Governance

This constitution supersedes conflicting development habits and informal agent
instructions within AIOS WorkLens. `CONSTITUTION.md`, `AGENT_RULES.md`,
`ARCHITECTURE.md`, `ROADMAP.md`, and `PROJECT_HANDOVER.md` remain canonical
project records; their material governance requirements are incorporated here
for Spec Kit workflows, not replaced.

Amendments MUST be documented in this file, include a Sync Impact Report,
identify affected templates or workflows, and use semantic versioning: MAJOR for
incompatible principle redefinitions/removals, MINOR for new principles or
materially expanded obligations, and PATCH for clarifications only. Every plan,
task list, implementation review, and release assessment MUST verify compliance
with these principles; exceptions require explicit user approval, a bounded
scope, and recorded remediation or rollback.

**Version**: 1.1.0 | **Ratified**: 2026-08-04 | **Last Amended**: 2026-09-05
