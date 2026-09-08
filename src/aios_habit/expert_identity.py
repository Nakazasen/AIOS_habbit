"""Expert Identity and Scope Grant models and protocols for AIOS Habit.

Implements T008 and T009 of 010-expert-knowledge-acquisition.
Provides fail-closed principal verification, expert profiles, and scope grants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol, Sequence, Tuple


# Action constants for Expert Knowledge Acquisition
ACTION_INTERVIEW_ANSWER = "interview.answer"
ACTION_CLAIM_REVIEW = "claim.review"
ACTION_ARTIFACT_CANDIDATE_CREATE = "artifact.candidate_create"
ACTION_ARTIFACT_APPROVE = "artifact.approve"
ACTION_PUBLICATION_PUBLISH = "publication.publish"
ACTION_COVERAGE_MANAGE = "coverage.manage"
ACTION_KILL_SWITCH = "expert.kill_switch"

ALL_EXPERT_ACTIONS: Tuple[str, ...] = (
    ACTION_INTERVIEW_ANSWER,
    ACTION_CLAIM_REVIEW,
    ACTION_ARTIFACT_CANDIDATE_CREATE,
    ACTION_ARTIFACT_APPROVE,
    ACTION_PUBLICATION_PUBLISH,
    ACTION_COVERAGE_MANAGE,
    ACTION_KILL_SWITCH,
)


def _utc_now_iso() -> str:
    """Return current UTC timestamp formatted in ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


class IdentityProviderError(RuntimeError):
    """Raised when an IdentityProvider encounters an operational error."""
    pass


@dataclass(frozen=True)
class VerifiedPrincipal:
    """Represents an authenticated principal from an underlying identity provider."""

    subject: str
    provider_name: str
    display_name: str
    authenticated_at: str = field(default_factory=_utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.subject or not self.subject.strip():
            raise ValueError("Định danh người dùng (subject) không được để trống.")
        if not self.provider_name or not self.provider_name.strip():
            raise ValueError("Tên nhà cung cấp danh tính không được để trống.")


@dataclass(frozen=True)
class ExpertProfile:
    """Domain profile mapping a verified principal subject to expert capabilities."""

    expert_id: str
    subject: str
    full_name: str
    scopes: Tuple[str, ...] = field(default_factory=tuple)
    status: str = "active"  # "active", "suspended", "revoked"
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not self.expert_id or not self.expert_id.strip():
            raise ValueError("Mã chuyên gia không được để trống.")
        if not self.subject or not self.subject.strip():
            raise ValueError("Định danh người dùng liên kết không được để trống.")

    @property
    def is_active(self) -> bool:
        """Check if expert profile is in active status."""
        return self.status == "active"

    def has_scope(self, scope: str) -> bool:
        """Check if expert is registered for a given scope."""
        if not self.is_active:
            return False
        if "*" in self.scopes or "all" in self.scopes:
            return True
        return scope in self.scopes


@dataclass(frozen=True)
class ScopeGrant:
    """Granular, scoped authorization grant assigned to a subject or expert."""

    grant_id: str
    subject: str
    action: str
    scope: str
    granted_by: str
    granted_at: str = field(default_factory=_utc_now_iso)
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    status: str = "active"  # "active", "expired", "revoked"

    def __post_init__(self) -> None:
        if not self.grant_id or not self.grant_id.strip():
            raise ValueError("Mã cấp quyền (grant_id) không được để trống.")
        if not self.subject or not self.subject.strip():
            raise ValueError("Đối tượng nhận quyền không được để trống.")
        if not self.action or not self.action.strip():
            raise ValueError("Hành động được cấp quyền không được để trống.")

    def is_revoked(self) -> bool:
        """Check if grant has been revoked."""
        return self.status == "revoked" or self.revoked_at is not None

    def is_expired(self, current_time_iso: Optional[str] = None) -> bool:
        """Check if grant has expired compared to reference timestamp."""
        if self.status == "expired":
            return True
        if self.expires_at is None:
            return False
        ref_time = current_time_iso or _utc_now_iso()
        return ref_time > self.expires_at

    def is_valid(self, current_time_iso: Optional[str] = None) -> bool:
        """Check if grant is active, not revoked, and not expired."""
        if self.status != "active":
            return False
        if self.is_revoked():
            return False
        if self.is_expired(current_time_iso):
            return False
        return True

    def matches(self, action: str, scope: str, current_time_iso: Optional[str] = None) -> bool:
        """Evaluate if grant satisfies requested action and scope."""
        if not self.is_valid(current_time_iso):
            return False
        if self.action != action and self.action != "*":
            return False
        if self.scope != scope and self.scope != "*" and self.scope != "all":
            return False
        return True


class IdentityProvider(Protocol):
    """Protocol for resolving the authenticated caller principal."""

    def resolve_current_principal(self) -> Optional[VerifiedPrincipal]:
        """Resolve current principal from ambient environment or session."""
        ...

    def get_provider_name(self) -> str:
        """Return canonical name of identity provider."""
        ...


class FixtureIdentityProvider:
    """Test fixture adapter for simulating authenticated principals."""

    def __init__(
        self,
        current_principal: Optional[VerifiedPrincipal] = None,
        provider_name: str = "fixture_simulated",
    ) -> None:
        self._current_principal = current_principal
        self._provider_name = provider_name
        self._simulate_failure = False
        self._failure_message = "Lỗi nhà cung cấp danh tính mô phỏng."

    def set_current_principal(self, principal: Optional[VerifiedPrincipal]) -> None:
        """Set the active simulated principal."""
        self._current_principal = principal

    def simulate_failure(
        self,
        should_fail: bool = True,
        error_message: str = "Lỗi nhà cung cấp danh tính mô phỏng.",
    ) -> None:
        """Configure the adapter to simulate an operational failure."""
        self._simulate_failure = should_fail
        self._failure_message = error_message

    def resolve_current_principal(self) -> Optional[VerifiedPrincipal]:
        """Resolve current simulated principal or raise if failure is simulated."""
        if self._simulate_failure:
            raise IdentityProviderError(self._failure_message)
        return self._current_principal

    def get_provider_name(self) -> str:
        """Return provider name."""
        return self._provider_name
