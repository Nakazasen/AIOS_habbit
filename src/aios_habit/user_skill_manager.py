"""User Skill Manager & Chat Creation Engine (DESKTOP-HOME-USER-SKILL-CREATE).

Enables users to create, list, inspect, and archive personal skills directly
from the chat interface using ported Hermes Agent standards:
- Adheres 100% to Hermes authoring standards:
  - YAML Frontmatter: `name` <= 64 chars, `description` <= 60 chars ending with a period.
  - Body procedures under `local_cases/skills/<name>/SKILL.md`.
  - Supporting files under `references/`, `templates/`, `scripts/`, `assets/` if needed.
- Saved in PINNED state (`hermes_curator.set_pinned(name, True)`), protecting user-created
  skills from ever being archived or pruned automatically by the curator.
- Tracks user skill metrics and lifecycle events in `local_cases/user_skill_metrics.json`.
- Integrates continuous improvement feedback: Approve (Duyệt), Edit (Sửa), Cancel (Hủy).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.hermes_curator import (
    archive_skill,
    is_pinned,
    load_usage,
    record_skill_usage,
    set_pinned,
)
from aios_habit.hermes_memory import atomic_write_text, file_lock, get_default_local_cases_dir
from aios_habit.hermes_skill_manager import (
    MAX_NAME_LENGTH,
    SKILL_PROMPT_DESC_LIMIT,
    VALID_NAME_RE,
    create_skill,
    find_skill,
    get_skills_dir,
    parse_frontmatter,
    read_skill,
)

logger = logging.getLogger("aios_habit.user_skill_manager")

METRICS_FILE_NAME = "user_skill_metrics.json"

# In-memory registry of conversational interview sessions keyed by conversation_id
_ACTIVE_INTERVIEW_SESSIONS: Dict[str, "SkillInterviewSession"] = {}


@dataclass
class SkillInterviewSession:
    """State of an ongoing skill creation interview."""

    conversation_id: str
    step: str = "awaiting_name"  # "awaiting_name" | "awaiting_description" | "awaiting_when" | "awaiting_steps" | "awaiting_approval"
    skill_name: str = ""
    description: str = ""
    when_to_use: str = ""
    procedure_steps: str = ""
    references_content: str = ""
    composed_draft: str = ""
    created_at: str = field(default_factory=lambda: datetime.datetime.now().astimezone().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().astimezone().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_local_cases_dir() -> Path:
    """Return local_cases directory respecting AIOS_LOCAL_CASES_DIR."""
    return get_default_local_cases_dir()


def get_user_skill_metrics_path() -> Path:
    """Path to user skill metrics JSON file in local_cases."""
    return get_local_cases_dir() / METRICS_FILE_NAME


def load_user_skill_metrics() -> Dict[str, Any]:
    """Load user skill metrics from local_cases."""
    path = get_user_skill_metrics_path()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug("Failed reading %s: %s", path, e)
    return {
        "total_user_skills_created": 0,
        "total_user_skills_used": 0,
        "total_user_skills_archived": 0,
        "actions_breakdown": {
            "approved": 0,
            "revised": 0,
            "cancelled": 0,
        },
        "by_skill": {},
        "last_event_at": None,
    }


def record_user_skill_event(
    event_type: str,
    skill_name: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Record user skill lifecycle events into local_cases metrics."""
    try:
        path = get_user_skill_metrics_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(path):
            metrics = load_user_skill_metrics()
            now_iso = datetime.datetime.now().astimezone().isoformat()
            metrics["last_event_at"] = now_iso

            evt = (event_type or "").strip().lower()
            if evt == "created":
                metrics["total_user_skills_created"] = metrics.get("total_user_skills_created", 0) + 1
                metrics.setdefault("actions_breakdown", {})["approved"] = (
                    metrics.get("actions_breakdown", {}).get("approved", 0) + 1
                )
                if skill_name:
                    by_s = metrics.setdefault("by_skill", {})
                    s_rec = by_s.setdefault(skill_name, {})
                    s_rec["created_at"] = now_iso
                    s_rec["pinned"] = True
                    s_rec["created_by"] = "user"
                    s_rec["use_count"] = 0
            elif evt == "used":
                metrics["total_user_skills_used"] = metrics.get("total_user_skills_used", 0) + 1
                if skill_name:
                    by_s = metrics.setdefault("by_skill", {})
                    s_rec = by_s.setdefault(skill_name, {})
                    s_rec["use_count"] = s_rec.get("use_count", 0) + 1
                    s_rec["last_used_at"] = now_iso
            elif evt == "archived":
                metrics["total_user_skills_archived"] = metrics.get("total_user_skills_archived", 0) + 1
                if skill_name and skill_name in metrics.get("by_skill", {}):
                    metrics["by_skill"][skill_name]["archived_at"] = now_iso
            elif evt == "revised":
                metrics.setdefault("actions_breakdown", {})["revised"] = (
                    metrics.get("actions_breakdown", {}).get("revised", 0) + 1
                )
            elif evt == "cancelled":
                metrics.setdefault("actions_breakdown", {})["cancelled"] = (
                    metrics.get("actions_breakdown", {}).get("cancelled", 0) + 1
                )

            atomic_write_text(path, json.dumps(metrics, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.warning("Failed recording user skill event: %s", e)


def normalize_skill_name(name: str) -> str:
    """Convert arbitrary text into valid Hermes skill name (lowercase alphanumeric with hyphens)."""
    clean = (name or "").strip().lower()
    # Replace whitespace and underscores with hyphen
    clean = re.sub(r"[\s_]+", "-", clean)
    # Remove unsupported characters
    clean = re.sub(r"[^a-z0-9.-]", "", clean)
    clean = clean.strip(".-")
    if len(clean) > MAX_NAME_LENGTH:
        clean = clean[:MAX_NAME_LENGTH].rstrip(".-")
    return clean


def normalize_hermes_description(text: str) -> str:
    """Format description strictly for Hermes standard (1 sentence, ends with '.', <= 60 chars)."""
    raw = (text or "").strip()
    if not raw:
        return "Huong dan quy trinh thao tac."
    # Take first sentence if multi-sentence
    sentences = re.split(r"(?<=[.!?])\s+", raw)
    first_sent = sentences[0].strip() if sentences else raw
    if not first_sent.endswith("."):
        first_sent = first_sent + "."
    if len(first_sent) > SKILL_PROMPT_DESC_LIMIT:
        first_sent = first_sent[: SKILL_PROMPT_DESC_LIMIT - 1].rstrip() + "."
    return first_sent


def build_hermes_skill_markdown(
    name: str,
    description: str,
    when_to_use: str,
    procedure_steps: str,
    references_note: str = "",
) -> str:
    """Build compliant SKILL.md markdown content conforming 100% to Hermes authoring standard."""
    desc_clean = normalize_hermes_description(description)
    when_clean = (when_to_use or "Khi thao tác công việc liên quan.").strip()
    steps_clean = (procedure_steps or "1. Thực hiện theo trình tự thao tác tiêu chuẩn.").strip()

    title_display = name.replace("-", " ").title()

    lines = [
        "---",
        f"name: {name}",
        f"description: {desc_clean}",
        "---",
        f"# {title_display}",
        "",
        "## Khi nào sử dụng (When to Use)",
        f"- {when_clean}",
        "",
        "## Quy trình thực hiện (Procedure)",
        steps_clean,
    ]

    if references_note.strip():
        lines.extend([
            "",
            "## Tài liệu tham khảo (References)",
            f"- {references_note.strip()}",
        ])

    return "\n".join(lines).strip() + "\n"


def has_active_interview(conversation_id: str) -> bool:
    """Check if conversation currently has an active interview in progress."""
    return conversation_id in _ACTIVE_INTERVIEW_SESSIONS


def get_active_interview(conversation_id: str) -> Optional[SkillInterviewSession]:
    """Retrieve active interview session if any."""
    return _ACTIVE_INTERVIEW_SESSIONS.get(conversation_id)


def cancel_interview(conversation_id: str) -> str:
    """Cancel and clear current interview session."""
    session = _ACTIVE_INTERVIEW_SESSIONS.pop(conversation_id, None)
    if session:
        record_user_skill_event("cancelled", session.skill_name)
    return "### 🛑 Đã hủy phiên tạo kỹ năng.\n\nBản nháp đã được hủy bỏ an toàn. Khi cần tạo mới, bạn có thể gõ lại `/kynang tao`."


def parse_inline_skill_args(text: str) -> Dict[str, str]:
    """Extract inline key-value pairs if user provided everything in one command."""
    result: Dict[str, str] = {}
    clean = (text or "").strip()
    # Strip leading slash commands like /kynang tao, /kynang-tao, /kynang, etc.
    clean = re.sub(
        r"^/(?:kynang|ky-nang)(?:-|\s+)?(?:tao|xem|luu-tru|luutru|sua|duyet)?\s*",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    # Pattern: ten: ... | viec: ... | khi_nao: ... | buoc: ...
    # Also support commas or newlines as delimiters
    tokens = re.split(r"[|\n]", clean)
    for tok in tokens:
        part = tok.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            k_norm = k.strip().lower()
            v_val = v.strip()
            if k_norm in ("ten", "tên", "name", "skill_name"):
                result["name"] = v_val
            elif k_norm in ("viec", "việc", "mo_ta", "mô tả", "desc", "description"):
                result["description"] = v_val
            elif k_norm in ("khi_nao", "khi nào", "dieu_kien", "điều kiện", "when", "trigger"):
                result["when"] = v_val
            elif k_norm in ("buoc", "bước", "cac_buoc", "các bước", "procedure", "steps"):
                result["steps"] = v_val
            elif k_norm in ("tham_khao", "references", "ref"):
                result["references"] = v_val

    return result


def start_or_reset_interview(conversation_id: str, raw_text: str = "") -> str:
    """Start a new skill creation interview session or initialize with inline arguments."""
    inline_args = parse_inline_skill_args(raw_text)

    session = SkillInterviewSession(conversation_id=conversation_id)

    # Check if all 4 required parts were provided inline
    if inline_args.get("name") and inline_args.get("description") and inline_args.get("when") and inline_args.get("steps"):
        session.skill_name = normalize_skill_name(inline_args["name"])
        session.description = normalize_hermes_description(inline_args["description"])
        session.when_to_use = inline_args["when"]
        session.procedure_steps = inline_args["steps"]
        session.references_content = inline_args.get("references", "")
        session.step = "awaiting_approval"
        session.composed_draft = build_hermes_skill_markdown(
            name=session.skill_name,
            description=session.description,
            when_to_use=session.when_to_use,
            procedure_steps=session.procedure_steps,
            references_note=session.references_content,
        )
        _ACTIVE_INTERVIEW_SESSIONS[conversation_id] = session
        return _render_draft_preview(session)

    # If partial inline name provided
    if inline_args.get("name"):
        norm_n = normalize_skill_name(inline_args["name"])
        if norm_n and VALID_NAME_RE.match(norm_n):
            session.skill_name = norm_n
            session.step = "awaiting_description"
            _ACTIVE_INTERVIEW_SESSIONS[conversation_id] = session
            return (
                f"### 🛠️ Phỏng vấn tạo kỹ năng mới (Chuẩn Hermes)\n\n"
                f"Đã ghi nhận tên kỹ năng: `{norm_n}`\n\n"
                f"**Bước 2/4: Việc gì (Mô tả kích hoạt)**\n"
                f"Kỹ năng này giải quyết việc gì ngắn gọn? *(1 câu kết thúc bằng dấu chấm, dưới 60 ký tự theo chuẩn Hermes, ví dụ: `Kiểm tra và xử lý sự cố cảm biến quang trên JIG.`)*"
            )

    _ACTIVE_INTERVIEW_SESSIONS[conversation_id] = session
    return (
        "### 🛠️ Phỏng vấn tạo kỹ năng mới (Chuẩn Hermes)\n\n"
        "Chào bạn! Tôi sẽ phỏng vấn ngắn 4 câu để cùng bạn đóng gói quy trình thành kỹ năng chuẩn Hermes "
        "(lưu tại máy cục bộ `local_cases/skills/`, trạng thái **PINNED** bảo vệ vĩnh viễn không bị curator dọn dẹp).\n\n"
        "**Bước 1/4: Tên kỹ năng**\n"
        "Bạn muốn đặt tên kỹ năng là gì? *(Dùng chữ thường không dấu, số, gạch nối, ví dụ: `kiem-tra-cam-bien-jig`)*\n\n"
        "*Gợi ý: Bạn có thể gõ `hủy` bất kỳ lúc nào để dừng phỏng vấn.*"
    )


def handle_interview_turn(conversation_id: str, user_text: str) -> str:
    """Process a user response in the active interview session."""
    session = _ACTIVE_INTERVIEW_SESSIONS.get(conversation_id)
    if not session:
        return start_or_reset_interview(conversation_id, user_text)

    clean_text = (user_text or "").strip()
    norm_lower = clean_text.lower()

    # Universal cancellation
    if norm_lower in ("huy", "hủy", "/kynang huy", "/kynang-huy", "cancel", "dung", "dừng"):
        return cancel_interview(conversation_id)

    # Approval step
    if session.step == "awaiting_approval":
        if any(w in norm_lower for w in ("duyet", "duyệt", "xac nhan", "xác nhận", "dong y", "đồng ý", "luu", "lưu", "/kynang duyet")):
            return save_and_finalize_skill(conversation_id)
        elif norm_lower.startswith(("sua", "sửa", "chinh sua", "chỉnh sửa", "/kynang sua")):
            record_user_skill_event("revised", session.skill_name)
            # Check if user specified what to edit
            edit_part = re.sub(r"^(?:sua|sửa|chinh sua|chỉnh sửa|/kynang sua)[:\s]*", "", clean_text, flags=re.IGNORECASE).strip()
            if edit_part:
                # Re-parse inline edit
                inline_edit = parse_inline_skill_args(edit_part)
                if inline_edit.get("name"):
                    session.skill_name = normalize_skill_name(inline_edit["name"])
                if inline_edit.get("description"):
                    session.description = normalize_hermes_description(inline_edit["description"])
                if inline_edit.get("when"):
                    session.when_to_use = inline_edit["when"]
                if inline_edit.get("steps"):
                    session.procedure_steps = inline_edit["steps"]
                session.composed_draft = build_hermes_skill_markdown(
                    name=session.skill_name,
                    description=session.description,
                    when_to_use=session.when_to_use,
                    procedure_steps=session.procedure_steps,
                    references_note=session.references_content,
                )
                return "### ✏️ Đã cập nhật bản nháp theo yêu cầu:\n\n" + _render_draft_preview(session)
            else:
                session.step = "awaiting_name"
                return (
                    "### ✏️ Bắt đầu chỉnh sửa lại bản nháp kỹ năng:\n\n"
                    f"**Bước 1/4: Tên kỹ năng hiện tại:** `{session.skill_name}`\n"
                    "Nhập tên mới hoặc gõ `giữ nguyên` để sang bước mô tả:"
                )
        else:
            return (
                "Bản nháp kỹ năng đang chờ bạn duyệt. Vui lòng chọn một trong các thao tác:\n"
                "- Gõ **`duyệt`** (hoặc `/kynang duyet`) để hoàn tất lưu kỹ năng.\n"
                "- Gõ **`sửa: <thông tin>`** (hoặc `/kynang sua`) để điều chỉnh nội dung.\n"
                "- Gõ **`hủy`** (hoặc `/kynang huy`) để hủy bỏ bản nháp.\n\n"
                + _render_draft_preview(session)
            )

    # Step 1: awaiting name
    if session.step == "awaiting_name":
        candidate = clean_text.strip()
        if candidate.lower() == "giữ nguyên" and session.skill_name:
            norm_name = session.skill_name
        else:
            if not VALID_NAME_RE.match(candidate):
                suggested = normalize_skill_name(candidate)
                return (
                    f"⚠️ Tên kỹ năng `{clean_text}` chưa hợp lệ. Tên chỉ dùng chữ thường không dấu, số và dấu gạch nối (tối đa 64 ký tự).\n\n"
                    f"Gợi ý: bạn có thể dùng `{suggested}`. Vui lòng nhập lại tên hợp lệ:"
                )
            norm_name = candidate

        # Check if already exists in local_cases
        if find_skill(norm_name):
            return (
                f"⚠️ Kỹ năng mang tên `{norm_name}` đã tồn tại trong `local_cases/skills/`.\n\n"
                "Vui lòng chọn một tên khác để tránh ghi đè (ví dụ: `{norm_name}-v2`):"
            )

        session.skill_name = norm_name
        session.step = "awaiting_description"
        session.updated_at = datetime.datetime.now().astimezone().isoformat()
        return (
            f"✅ **Đã ghi nhận tên kỹ năng:** `{norm_name}`\n\n"
            "**Bước 2/4: Việc gì (Mô tả kích hoạt)**\n"
            "Kỹ năng này giải quyết việc gì ngắn gọn? *(1 câu kết thúc bằng dấu chấm, tối đa 60 ký tự theo ngân sách prompt Hermes, ví dụ: `Kiểm tra và khắc phục lỗi cảm biến quang JIG.`)*"
        )

    # Step 2: awaiting description
    if session.step == "awaiting_description":
        desc_norm = normalize_hermes_description(clean_text)
        session.description = desc_norm
        session.step = "awaiting_when"
        session.updated_at = datetime.datetime.now().astimezone().isoformat()
        return (
            f"✅ **Mô tả kích hoạt:** `{desc_norm}` ({len(desc_norm)}/60 ký tự)\n\n"
            "**Bước 3/4: Điều kiện kích hoạt (Khi nào sử dụng)**\n"
            "Kỹ năng này được kích hoạt khi nào? *(Ngữ cảnh hoặc hiện tượng lỗi, ví dụ: `Đèn LED vàng trên cảm biến JIG nhấp nháy hoặc cảm biến không phản hồi tín hiệu.`)*"
        )

    # Step 3: awaiting when
    if session.step == "awaiting_when":
        session.when_to_use = clean_text
        session.step = "awaiting_steps"
        session.updated_at = datetime.datetime.now().astimezone().isoformat()
        return (
            "✅ **Đã ghi nhận điều kiện kích hoạt.**\n\n"
            "**Bước 4/4: Các bước thực hiện (Quy trình thao tác)**\n"
            "Nhập các bước thực hiện cụ thể theo thứ tự:\n"
            "*(Ví dụ:\n"
            "1. Đo nguồn cấp 24V tại chân cảm biến.\n"
            "2. Vệ sinh thấu kính quang bằng cồn IPA.\n"
            "3. Hiệu chỉnh biến trở độ nhạy đến khi đèn xanh sáng ổn định.)*"
        )

    # Step 4: awaiting steps
    if session.step == "awaiting_steps":
        session.procedure_steps = clean_text
        session.step = "awaiting_approval"
        session.updated_at = datetime.datetime.now().astimezone().isoformat()
        session.composed_draft = build_hermes_skill_markdown(
            name=session.skill_name,
            description=session.description,
            when_to_use=session.when_to_use,
            procedure_steps=session.procedure_steps,
            references_note=session.references_content,
        )
        return _render_draft_preview(session)

    return "Trạng thái phỏng vấn không xác định. Gõ `/kynang tao` để bắt đầu lại."


def _render_draft_preview(session: SkillInterviewSession) -> str:
    """Render the draft preview card with interactive approval callouts."""
    return (
        "### 📋 BẢN NHÁP KỸ NĂNG NGƯỜI DÙNG (CHUẨN HERMES)\n\n"
        f"- **Tên kỹ năng:** `{session.skill_name}`\n"
        f"- **Mô tả Frontmatter (Trigger):** `{session.description}`\n"
        f"- **Ngữ cảnh kích hoạt:** {session.when_to_use}\n"
        f"- **Trạng thái lưu dự kiến:** **`PINNED`** *(Được ghim vĩnh viễn tại `local_cases/skills/`, curator không tự động lưu trữ)*\n\n"
        "#### Nội dung tệp `SKILL.md` sẽ được tạo:\n"
        "```markdown\n"
        f"{session.composed_draft}"
        "```\n\n"
        "---\n"
        "#### 🎯 XÁC NHẬN & PHẢN HỒI BẢN NHÁP:\n"
        "- Gõ **`duyệt`** (hoặc bấm **[Duyệt lưu]**): Lưu kỹ năng vào kho cục bộ và kích hoạt ngay.\n"
        "- Gõ **`sửa: <thay đổi>`** (hoặc bấm **[Sửa]**): Hiệu chỉnh lại nội dung phỏng vấn.\n"
        "- Gõ **`hủy`** (hoặc bấm **[Hủy]**): Hủy bỏ toàn bộ bản nháp này.\n\n"
        f"<!-- aios_user_skill_draft: {{\"name\": \"{session.skill_name}\", \"status\": \"pending_approval\"}} -->"
    )


def save_and_finalize_skill(conversation_id: str) -> str:
    """Save approved skill to local_cases/skills/<name>/SKILL.md and pin it."""
    session = _ACTIVE_INTERVIEW_SESSIONS.pop(conversation_id, None)
    if not session:
        return "⚠️ Không tìm thấy bản nháp kỹ năng cần duyệt. Vui lòng gõ `/kynang tao` để tạo mới."

    name = session.skill_name
    content = session.composed_draft

    # Ensure compliant Hermes skill creation
    res = create_skill(name=name, content=content)
    if not res.get("success"):
        # Re-attach session so user can fix
        _ACTIVE_INTERVIEW_SESSIONS[conversation_id] = session
        return f"### ❌ Không thể lưu kỹ năng: {res.get('error')}\nVui lòng gõ `sửa` để hiệu chỉnh lại."

    # Mark as PINNED immediately so curator never purges or moves to archive
    set_pinned(name, True)

    # Mutate usage record to mark created_by="user"
    def _mark_user_created(rec: Dict[str, Any]) -> None:
        rec["created_by"] = "user"
        rec["pinned"] = True

    try:
        from aios_habit.hermes_curator import _mutate_usage

        _mutate_usage(name, _mark_user_created)
    except Exception as e:
        logger.debug("Failed setting created_by: %s", e)

    # Record event in metrics
    record_user_skill_event("created", name)

    skill_path = Path(res.get("path", "")) / "SKILL.md"

    return (
        f"### 🎉 ĐÃ TẠO VÀ LƯU KỸ NĂNG THÀNH CÔNG!\n\n"
        f"- **Tên kỹ năng:** `{name}`\n"
        f"- **Đường dẫn tệp:** `{skill_path}`\n"
        f"- **Định dạng:** Chuẩn Hermes Agent (YAML Frontmatter + Quy trình thao tác)\n"
        f"- **Trạng thái:** 📌 **`PINNED`** *(Bảo vệ vĩnh viễn trên máy nhà, curator không tự động lưu trữ)*\n"
        f"- **Phạm vi lưu trữ:** `local_cases/skills/{name}/` (chỉ ở máy cá nhân, không đưa vào bộ cài)\n\n"
        f"💡 **Sẵn sàng áp dụng:** Kỹ năng đã được nạp tức thì vào kho tri thức của AIOS. "
        f"Khi bạn đặt câu hỏi liên quan đến *\"{session.when_to_use}\"*, AIOS sẽ nhận diện ngữ cảnh và tự động áp dụng quy trình này!"
    )


def list_user_skills_markdown() -> str:
    """Return formatted markdown listing all skills in local_cases/skills/."""
    skills_root = get_skills_dir()
    if not skills_root.exists():
        return (
            "### 📚 Kho kỹ năng cá nhân (`local_cases/skills/`)\n\n"
            "Hiện tại bạn chưa lưu kỹ năng cá nhân nào.\n\n"
            "👉 Gõ **`/kynang tao`** để tạo kỹ năng chuẩn Hermes đầu tiên!"
        )

    usage = load_usage()
    items: List[Dict[str, Any]] = []

    for item in sorted(skills_root.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        skill_md = item / "SKILL.md"
        if not skill_md.is_file():
            continue

        try:
            fm, body = parse_frontmatter(skill_md.read_text(encoding="utf-8-sig")[:4000])
            name = fm.get("name") or item.name
            desc = fm.get("description") or ""
        except Exception:
            name = item.name
            desc = "Không đọc được frontmatter."

        u_rec = usage.get(name, {})
        pinned_val = bool(u_rec.get("pinned", False))
        created_by = str(u_rec.get("created_by", "agent"))
        state = str(u_rec.get("state", "active"))
        use_count = int(u_rec.get("use_count", 0))

        items.append({
            "name": name,
            "description": desc,
            "pinned": pinned_val,
            "created_by": created_by,
            "state": state,
            "use_count": use_count,
            "path": item,
        })

    if not items:
        return (
            "### 📚 Kho kỹ năng cá nhân (`local_cases/skills/`)\n\n"
            "Hiện tại bạn chưa lưu kỹ năng cá nhân nào.\n\n"
            "👉 Gõ **`/kynang tao`** để bắt đầu tạo kỹ năng mới!"
        )

    lines = [
        f"### 📚 DANH SÁCH KỸ NĂNG CÁ NHÂN CỦA BẠN ({len(items)} kỹ năng)",
        "",
        "Lưu trữ tại: `local_cases/skills/` (chỉ trên máy này, độc lập với bộ cài hệ thống).",
        "",
        "| Tên kỹ năng | Mô tả kích hoạt (Trigger) | Trạng thái | Lượt dùng | Nguồn tạo |",
        "| :--- | :--- | :--- | :---: | :--- |",
    ]

    for it in items:
        status_badge = "📌 **PINNED**" if it["pinned"] else f"`{it['state']}`"
        creator_badge = "👤 Người dùng" if it["created_by"] == "user" else "🤖 Hệ thống"
        lines.append(
            f"| **`{it['name']}`** | {it['description']} | {status_badge} | {it['use_count']} | {creator_badge} |"
        )

    lines.extend([
        "",
        "*Lệnh hữu ích:*",
        "- Xem chi tiết: `/kynang xem <ten>`",
        "- Lưu trữ đóng băng: `/kynang luu-tru <ten>`",
        "- Tạo kỹ năng mới: `/kynang tao`",
    ])

    return "\n".join(lines)


def view_skill_markdown(skill_name: str) -> str:
    """Read and format a specific skill's SKILL.md and files."""
    clean_name = (skill_name or "").strip()
    if not clean_name:
        return "⚠️ Vui lòng cung cấp tên kỹ năng cần xem. Ví dụ: `/kynang xem kiem-tra-cam-bien-jig`"

    # Remove leading slash commands if passed verbatim
    clean_name = re.sub(r"^/kynang\s+xem\s*", "", clean_name, flags=re.IGNORECASE).strip()
    clean_name = normalize_skill_name(clean_name)

    res = read_skill(clean_name)
    if not res.get("success"):
        return f"⚠️ Không tìm thấy kỹ năng `{clean_name}` trong kho `local_cases/skills/`."

    content = res.get("content", "")
    usage = load_usage().get(clean_name, {})
    pinned = bool(usage.get("pinned", False))
    use_count = int(usage.get("use_count", 0))

    # Bump usage count as viewing
    try:
        from aios_habit.hermes_curator import _mutate_usage

        def _bump_view(rec: Dict[str, Any]) -> None:
            rec["view_count"] = int(rec.get("view_count", 0)) + 1
            rec["last_viewed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        _mutate_usage(clean_name, _bump_view)
    except Exception:
        pass

    pinned_badge = "📌 **PINNED** (Bảo vệ vĩnh viễn)" if pinned else "Bình thường"

    return (
        f"### 📖 CHI TIẾT KỸ NĂNG: `{clean_name}`\n\n"
        f"- **Đường dẫn:** `local_cases/skills/{clean_name}/SKILL.md`\n"
        f"- **Trạng thái:** {pinned_badge}\n"
        f"- **Số lượt dùng:** `{use_count}` lượt\n\n"
        "```markdown\n"
        f"{content}\n"
        "```"
    )


def archive_skill_markdown(skill_name: str) -> str:
    """Move a skill to .archive/ folder."""
    clean_name = (skill_name or "").strip()
    clean_name = re.sub(r"^/kynang\s+luu-tru\s*", "", clean_name, flags=re.IGNORECASE).strip()
    clean_name = normalize_skill_name(clean_name)

    if not clean_name:
        return "⚠️ Vui lòng chỉ định tên kỹ năng cần lưu trữ. Ví dụ: `/kynang luu-tru kiem-tra-cam-bien-jig`"

    ok, msg = archive_skill(clean_name)
    if not ok:
        return f"⚠️ Không thể lưu trữ kỹ năng `{clean_name}`: {msg}"

    record_user_skill_event("archived", clean_name)

    return (
        f"### 📦 ĐÃ LƯU TRỮ KỸ NĂNG: `{clean_name}`\n\n"
        f"- Kỹ năng đã được di chuyển an toàn vào thư mục `local_cases/skills/.archive/{clean_name}/`.\n"
        "- Trạng thái chuyển sang `archived` và không còn tham gia kích hoạt tự động.\n"
        "- Bạn có thể khôi phục bất cứ lúc nào khi cần."
    )
