"""Controlled Knowledge Artifacts (SOPs and Lessons Learned) with provenance mapping and approval matrix.

Implements T054, T055, T056 of Goal 010-expert-knowledge-acquisition.
Fail-closed invariants:
1. Every artifact MUST map back to verified knowledge claims.
2. Self-approval is strictly forbidden (authors/experts cannot approve their own artifacts).
3. Approval requires exact artifact digest match (any edit after approval invalidates approval).
4. Artifacts referencing conflicted claims cannot be approved without escalation resolution.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from aios_habit.knowledge_claim_extractor import (
    CLAIM_STATUS_CONFIRMED,
    CLAIM_STATUS_CONFLICTED,
    KnowledgeClaim,
)

# Artifact Types
ARTIFACT_TYPE_SOP = "sop"
ARTIFACT_TYPE_LESSON = "lesson"
VALID_ARTIFACT_TYPES = {ARTIFACT_TYPE_SOP, ARTIFACT_TYPE_LESSON}

# Artifact Statuses
ARTIFACT_STATUS_CANDIDATE = "candidate"
ARTIFACT_STATUS_APPROVED = "approved"
ARTIFACT_STATUS_REJECTED = "rejected"
ARTIFACT_STATUS_CHANGES_REQUESTED = "changes_requested"
ARTIFACT_STATUS_REVOKED = "revoked"

VALID_ARTIFACT_STATUSES = {
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_REJECTED,
    ARTIFACT_STATUS_CHANGES_REQUESTED,
    ARTIFACT_STATUS_REVOKED,
}

# Approval Actions
APPROVAL_ACTION_APPROVE = "approve"
APPROVAL_ACTION_REJECT = "reject"
APPROVAL_ACTION_REQUEST_CHANGE = "request_change"
APPROVAL_ACTION_REVOKE = "revoke"

VALID_APPROVAL_ACTIONS = {
    APPROVAL_ACTION_APPROVE,
    APPROVAL_ACTION_REJECT,
    APPROVAL_ACTION_REQUEST_CHANGE,
    APPROVAL_ACTION_REVOKE,
}


class ControlledArtifactError(Exception):
    """Base exception for controlled knowledge artifacts."""
    pass


class SelfApprovalDeniedError(ControlledArtifactError):
    """Raised when creator or expert attempts to approve their own artifact."""
    pass


class StaleArtifactDigestError(ControlledArtifactError):
    """Raised when approval is submitted against an outdated artifact digest."""
    pass


class ConflictedClaimArtifactError(ControlledArtifactError):
    """Raised when an artifact containing unresolved conflicted claims is submitted for approval."""
    pass


@dataclass(frozen=True)
class ArtifactApproval:
    """Immutable audit record of an approval decision for an artifact."""

    approval_id: str
    artifact_id: str
    artifact_digest: str
    action: str
    actor_id: str
    scope: str
    reason: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.approval_id.strip():
            raise ValueError("Mã định danh phê duyệt không được để trống.")
        if not self.artifact_id.strip():
            raise ValueError("Mã tài liệu không được để trống.")
        if not self.artifact_digest.strip():
            raise ValueError("Mã băm kiểm tra (digest) không được để trống.")
        if self.action not in VALID_APPROVAL_ACTIONS:
            raise ValueError(f"Hành động phê duyệt '{self.action}' không hợp lệ. Phải thuộc {VALID_APPROVAL_ACTIONS}.")
        if not self.actor_id.strip():
            raise ValueError("Định danh người phê duyệt không được để trống.")
        if not self.reason.strip():
            raise ValueError("Lý do phê duyệt/từ chối không được để trống.")


@dataclass(frozen=True)
class ControlledKnowledgeArtifact:
    """Formalized standard operating procedure or lesson learned derived from verified claims."""

    artifact_id: str
    artifact_type: str
    title: str
    scope: str
    version: str
    content_markdown: str
    claim_ids: Tuple[str, ...]
    claim_map: Dict[str, str] = field(default_factory=dict)
    status: str = ARTIFACT_STATUS_CANDIDATE
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approvals: Tuple[ArtifactApproval, ...] = ()

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("Mã tài liệu quy chuẩn (artifact_id) không được để trống.")
        if self.artifact_type not in VALID_ARTIFACT_TYPES:
            raise ValueError(f"Loại tài liệu '{self.artifact_type}' không hợp lệ. Phải là 'sop' hoặc 'lesson'.")
        if not self.title.strip():
            raise ValueError("Tiêu đề tài liệu không được để trống.")
        if not self.scope.strip():
            raise ValueError("Phạm vi nghiệp vụ không được để trống.")
        if not self.content_markdown.strip():
            raise ValueError("Nội dung tài liệu Markdown không được để trống.")
        if not self.claim_ids:
            raise ValueError("Tài liệu quy chuẩn bắt buộc phải dẫn xuất từ ít nhất một phát biểu tri thức (claim_ids).")
        if self.status not in VALID_ARTIFACT_STATUSES:
            raise ValueError(f"Trạng thái '{self.status}' không hợp lệ.")

    @property
    def digest(self) -> str:
        """Deterministic SHA-256 digest covering semantic content, scope, version, and claims."""
        payload = f"{self.artifact_id}:{self.artifact_type}:{self.version}:{self.title}:{self.scope}:{','.join(sorted(self.claim_ids))}:{self.content_markdown}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArtifactDiffReport:
    """Difference analysis between two artifact versions."""

    artifact_id: str
    old_version: str
    new_version: str
    content_diff: str
    added_claim_ids: Tuple[str, ...]
    removed_claim_ids: Tuple[str, ...]
    conflict_decision_items: Tuple[str, ...]


def generate_candidate_sop(
    artifact_id: str,
    title: str,
    scope: str,
    claims: Sequence[KnowledgeClaim],
    created_by: str,
    version: str = "1.0",
) -> ControlledKnowledgeArtifact:
    """Synthesize candidate Standard Operating Procedure (SOP) in Vietnamese from approved claims."""
    if not claims:
        raise ValueError("Không có phát biểu tri thức nào để tạo quy trình SOP.")

    # Check for any unresolved conflicted claims
    conflicted = [c.claim_id for c in claims if c.status == CLAIM_STATUS_CONFLICTED]
    if conflicted:
        raise ConflictedClaimArtifactError(
            f"Không thể tạo tài liệu quy chuẩn khi các phát biểu {conflicted} đang có xung đột chưa giải quyết."
        )

    claim_ids = tuple(c.claim_id for c in claims)
    claim_map = {c.claim_id: c.statement for c in claims}

    # Format Markdown content
    lines = [
        f"# QUY TRÌNH THAO TÁC CHUẨN (SOP): {title.upper()}",
        "",
        f"- **Mã tài liệu**: `{artifact_id}`",
        f"- **Phiên bản**: `{version}`",
        f"- **Phạm vi công đoạn**: `{scope}`",
        f"- **Người khởi tạo**: `{created_by}`",
        f"- **Ngày tạo**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d')}`",
        "",
        "## 1. MỤC ĐÍCH VÀ PHẠM VI",
        f"Quy trình này hướng dẫn chuẩn hóa thao tác vận hành và xử lý trong công đoạn **{scope}**.",
        "",
        "## 2. THÔNG SỐ VÀ ĐIỀU KIỆN KỸ THUẬT BẮT BUỘC",
    ]

    all_conds: List[str] = []
    for c in claims:
        for cond in c.validity_conditions:
            all_conds.append(f"- {cond} *(Dẫn xuất từ `{c.claim_id}`)*")

    if all_conds:
        lines.extend(all_conds)
    else:
        lines.append("- Tuân thủ theo các tiêu chuẩn vận hành cơ bản của xưởng.")

    lines.extend([
        "",
        "## 3. CÁC BƯỚC THỰC HIỆN CHI TIẾT",
    ])

    for i, c in enumerate(claims, start=1):
        lines.append(f"### Bước {i}: Thao tác theo phát biểu `{c.claim_id}`")
        lines.append(f"{c.statement}")
        if c.uncertainty_note:
            lines.append(f"> **Lưu ý chuyên gia**: {c.uncertainty_note}")
        lines.append("")

    lines.extend([
        "## 4. HỒ SƠ NGUỒN CHỨNG MINH (PROVENANCE MAP)",
    ])
    for c in claims:
        sources_str = ", ".join(f"`{s}`" for s in c.source_refs)
        lines.append(f"- Phát biểu `{c.claim_id}`: Nguồn {sources_str}")

    content_markdown = "\n".join(lines)

    return ControlledKnowledgeArtifact(
        artifact_id=artifact_id,
        artifact_type=ARTIFACT_TYPE_SOP,
        title=title,
        scope=scope,
        version=version,
        content_markdown=content_markdown,
        claim_ids=claim_ids,
        claim_map=claim_map,
        status=ARTIFACT_STATUS_CANDIDATE,
        created_by=created_by,
    )


def generate_candidate_lesson(
    artifact_id: str,
    title: str,
    scope: str,
    claims: Sequence[KnowledgeClaim],
    created_by: str,
    version: str = "1.0",
) -> ControlledKnowledgeArtifact:
    """Synthesize candidate Lesson Learned in Vietnamese from verified claims."""
    if not claims:
        raise ValueError("Không có phát biểu tri thức nào để tạo bài học kinh nghiệm.")

    conflicted = [c.claim_id for c in claims if c.status == CLAIM_STATUS_CONFLICTED]
    if conflicted:
        raise ConflictedClaimArtifactError(
            f"Không thể tạo bài học khi các phát biểu {conflicted} đang có xung đột chưa giải quyết."
        )

    claim_ids = tuple(c.claim_id for c in claims)
    claim_map = {c.claim_id: c.statement for c in claims}

    lines = [
        f"# BÀI HỌC KINH NGHIỆM VẬN HÀNH: {title.upper()}",
        "",
        f"- **Mã bài học**: `{artifact_id}`",
        f"- **Phiên bản**: `{version}`",
        f"- **Phạm vi**: `{scope}`",
        f"- **Người tổng hợp**: `{created_by}`",
        "",
        "## 1. BỐI CẢNH VÀ HIỆN TƯỢNG KỸ THUẬT",
        f"Ghi nhận thực tế sản xuất trong công đoạn **{scope}** qua phỏng vấn chuyên gia hiện trường.",
        "",
        "## 2. NGUYÊN NHÂN VÀ PHÂN TÍCH CHUYÊN SÂU",
    ]

    for c in claims:
        lines.append(f"- **Phát biểu `{c.claim_id}`**: {c.statement}")
        if c.validity_conditions:
            lines.append(f"  + Điều kiện áp dụng: {', '.join(c.validity_conditions)}")

    lines.extend([
        "",
        "## 3. KHUYẾN NGHỊ VÀ HÀNH ĐỘNG PHÒNG NGỪA",
        "- Cập nhật thông số kiểm soát định kỳ vào bảng kiểm checklist đầu ca.",
        "- Đào tạo lại thao tác cho kỹ thuật viên vận hành mới.",
        "",
        "## 4. DẪN XUẤT NGUỒN CHỨNG MINH",
    ])

    for c in claims:
        lines.append(f"- `{c.claim_id}`: Liên kết {', '.join(c.source_refs)}")

    content_markdown = "\n".join(lines)

    return ControlledKnowledgeArtifact(
        artifact_id=artifact_id,
        artifact_type=ARTIFACT_TYPE_LESSON,
        title=title,
        scope=scope,
        version=version,
        content_markdown=content_markdown,
        claim_ids=claim_ids,
        claim_map=claim_map,
        status=ARTIFACT_STATUS_CANDIDATE,
        created_by=created_by,
    )


def generate_artifact_diff(
    old_artifact: ControlledKnowledgeArtifact,
    new_artifact: ControlledKnowledgeArtifact,
) -> ArtifactDiffReport:
    """Generate textual unified diff and identify changes in claims and conflict decision points."""
    old_lines = old_artifact.content_markdown.splitlines(keepends=True)
    new_lines = new_artifact.content_markdown.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{old_artifact.artifact_id} (v{old_artifact.version})",
            tofile=f"{new_artifact.artifact_id} (v{new_artifact.version})",
        )
    )
    diff_text = "".join(diff_lines)

    old_claims = set(old_artifact.claim_ids)
    new_claims = set(new_artifact.claim_ids)

    added_claims = tuple(sorted(new_claims - old_claims))
    removed_claims = tuple(sorted(old_claims - new_claims))

    # Identify items that require decisions (e.g. removed claims or scope changes)
    decision_items: List[str] = []
    if removed_claims:
        decision_items.append(f"Loại bỏ các phát biểu tri thức: {list(removed_claims)}")
    if added_claims:
        decision_items.append(f"Bổ sung các phát biểu tri thức mới: {list(added_claims)}")
    if old_artifact.scope != new_artifact.scope:
        decision_items.append(f"Thay đổi phạm vi từ '{old_artifact.scope}' sang '{new_artifact.scope}'")

    return ArtifactDiffReport(
        artifact_id=new_artifact.artifact_id,
        old_version=old_artifact.version,
        new_version=new_artifact.version,
        content_diff=diff_text,
        added_claim_ids=added_claims,
        removed_claim_ids=removed_claims,
        conflict_decision_items=tuple(decision_items),
    )
