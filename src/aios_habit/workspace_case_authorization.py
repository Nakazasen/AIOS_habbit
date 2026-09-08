"""Explicit local actor and role/scope authorization for Workspace cases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Optional, Sequence, Set, Union

from aios_habit.expert_identity import (
    ACTION_ARTIFACT_APPROVE,
    ACTION_ARTIFACT_CANDIDATE_CREATE,
    ACTION_CLAIM_REVIEW,
    ACTION_COVERAGE_MANAGE,
    ACTION_INTERVIEW_ANSWER,
    ACTION_PUBLICATION_PUBLISH,
    ALL_EXPERT_ACTIONS,
    ExpertProfile,
    ScopeGrant,
    VerifiedPrincipal,
)
from aios_habit.feature_flags import (
    FEATURE_EXPERT_MULTI_USER,
    is_feature_enabled,
)


LOCAL_ADMIN_ACTOR_ID: Final[str] = "local_admin"


class AuthorizationError(PermissionError):
    """Safe authorization failure for service and UI boundaries."""


@dataclass(frozen=True)
class ActorContext:
    actor_id: str


@dataclass(frozen=True)
class RoleGrant:
    grant_id: str
    actor_id: str
    role: str
    scope: str
    valid_from: str
    valid_until: str
    revoked_at: str | None = None


ROLE_CAPABILITIES: Final[dict[str, frozenset[str]]] = {
    "investigator": frozenset(
        {
            "case.view",
            "case.receive",
            "case.transition",
            "case.assign",
            "case.checklist",
            "case.attach_evidence",
            "expert.request",
            "expert.resolve_conflict",
            "learning.propose",
            "artifact.draft",
            "alert.view",
            "coverage.manage",
        }
    ),
    "expert": frozenset(
        {
            "case.view",
            "case.attach_evidence",
            "expert.review",
            "expert.request",
            "learning.propose",
            "alert.view",
            "interview.answer",
            "claim.review",
            "artifact.candidate_create",
        }
    ),
    # Admin is deliberately not a wildcard; capabilities remain explicit.
    "admin": frozenset(
        {
            "case.view",
            "case.configure_roles",
            "learning.view",
            "alert.view",
            "alert.manage_policy",
            "alert.kill_switch",
            "coverage.manage",
            "publication.publish",
        }
    ),
    "local_admin": frozenset(
        {
            "case.view",
            "case.configure_roles",
            "learning.view",
            "alert.view",
            "alert.manage_policy",
            "alert.kill_switch",
            "coverage.manage",
            "publication.publish",
        }
    ),
    "quality_manager": frozenset(
        {
            "case.view",
            "learning.propose",
            "learning.approve",
            "learning.revoke",
            "expert.resolve_conflict",
            "artifact.draft",
            "artifact.approve",
            "alert.view",
            "alert.manage_policy",
            "alert.kill_switch",
            "interview.answer",
            "claim.review",
            "artifact.candidate_create",
            "publication.publish",
            "coverage.manage",
        }
    ),
    "artifact_approver": frozenset(
        {
            "case.view",
            "artifact.draft",
            "artifact.approve",
        }
    ),
    "shadow_reviewer": frozenset({"case.view", "shadow.review", "alert.view"}),
    "system_owner": frozenset(
        {
            "case.view",
            "shadow.approve",
            "alert.view",
            "alert.manage_policy",
            "alert.kill_switch",
            "publication.publish",
            "coverage.manage",
        }
    ),
    "qc_operator": frozenset({"case.view", "alert.view"}),
    "operator": frozenset({"case.view", "alert.view"}),
}


def trusted_local_actor() -> ActorContext:
    """Return the app-controlled actor for the current single-user local runtime."""
    return ActorContext(LOCAL_ADMIN_ACTOR_ID)


class WorkspaceCaseAuthorization:
    def __init__(self, store) -> None:
        self.store = store

    def require(self, actor: ActorContext, capability: str, scope: str) -> None:
        actor_id = actor.actor_id.strip()
        if not actor_id:
            raise AuthorizationError("CASE_ACTOR_REQUIRED")
        if not scope or scope == "*":
            raise AuthorizationError("CASE_SCOPE_REQUIRED")
        now = datetime.now(timezone.utc)
        for grant in self.store.list_role_grants(actor_id):
            if (grant.scope != scope and grant.scope != "general") or grant.scope == "*" or grant.revoked_at:
                continue
            try:
                valid_from = datetime.fromisoformat(grant.valid_from)
                valid_until = datetime.fromisoformat(grant.valid_until)
            except (TypeError, ValueError):
                continue
            if (
                valid_from.tzinfo is None
                or valid_until.tzinfo is None
                or valid_from.utcoffset() is None
                or valid_until.utcoffset() is None
            ):
                continue
            valid_from = valid_from.astimezone(timezone.utc)
            valid_until = valid_until.astimezone(timezone.utc)
            if valid_from <= now <= valid_until and capability in ROLE_CAPABILITIES.get(grant.role, frozenset()):
                return
        raise AuthorizationError("CASE_AUTH_DENIED")

    def has_capability(self, actor: ActorContext, capability: str, scope: str) -> bool:
        """Check if actor holds capability in given scope without raising exception."""
        try:
            self.require(actor, capability, scope)
            return True
        except (AuthorizationError, PermissionError):
            return False

    def get_active_roles(self, actor: ActorContext, scope: str) -> set[str]:
        """Return set of unrevoked, active roles for actor in scope (or general)."""
        actor_id = actor.actor_id.strip()
        if not actor_id or not scope or scope == "*":
            return set()
        now = datetime.now(timezone.utc)
        active_roles: set[str] = set()
        for grant in self.store.list_role_grants(actor_id):
            if (grant.scope != scope and grant.scope != "general") or grant.scope == "*" or grant.revoked_at:
                continue
            try:
                valid_from = datetime.fromisoformat(grant.valid_from)
                valid_until = datetime.fromisoformat(grant.valid_until)
            except (TypeError, ValueError):
                continue
            if (
                valid_from.tzinfo is None
                or valid_until.tzinfo is None
                or valid_from.utcoffset() is None
                or valid_until.utcoffset() is None
            ):
                continue
            valid_from = valid_from.astimezone(timezone.utc)
            valid_until = valid_until.astimezone(timezone.utc)
            if valid_from <= now <= valid_until:
                active_roles.add(grant.role)
        return active_roles

    def require_expert_action(
        self,
        principal: Union[VerifiedPrincipal, ActorContext],
        action: str,
        scope: str,
        current_time_iso: Optional[str] = None,
    ) -> None:
        """Evaluate expert action authorization with fail-closed invariants.

        Under multi-user mode:
          - Prohibits silent fallback to local_admin.
          - VerifiedPrincipal must be valid.
          - Checks active ExpertProfile mapping for the subject.
          - Checks valid ScopeGrant matching action, scope, and time bounds.
        """
        if isinstance(principal, VerifiedPrincipal):
            subject = principal.subject.strip()
        elif isinstance(principal, ActorContext):
            subject = principal.actor_id.strip()
        else:
            raise AuthorizationError("EXPERT_PRINCIPAL_INVALID")

        if not subject:
            raise AuthorizationError("EXPERT_PRINCIPAL_REQUIRED")
        if not action or not action.strip():
            raise AuthorizationError("EXPERT_ACTION_REQUIRED")
        if not scope or not scope.strip():
            raise AuthorizationError("EXPERT_SCOPE_REQUIRED")

        multi_user_enabled = is_feature_enabled(FEATURE_EXPERT_MULTI_USER)

        if multi_user_enabled:
            # Strict fail-closed: No fallback to local_admin when multi-user is active
            if subject == LOCAL_ADMIN_ACTOR_ID and not hasattr(self.store, "get_expert_profile"):
                raise AuthorizationError("MULTI_USER_LOCAL_ADMIN_FALLBACK_PROHIBITED")

            # Check ExpertProfile if repository supports it
            if hasattr(self.store, "get_expert_profile_by_subject"):
                profile = self.store.get_expert_profile_by_subject(subject)
                if profile is None or not profile.is_active:
                    raise AuthorizationError("EXPERT_PROFILE_INACTIVE_OR_MISSING")
                if not profile.has_scope(scope) and scope != "general":
                    raise AuthorizationError("EXPERT_SCOPE_NOT_IN_PROFILE")

            # Check ScopeGrants if repository supports it
            if hasattr(self.store, "list_scope_grants_for_subject"):
                grants = self.store.list_scope_grants_for_subject(subject)
                matching = [g for g in grants if g.matches(action, scope, current_time_iso)]
                if not matching:
                    raise AuthorizationError("EXPERT_ACTION_GRANT_MISSING")
                return

        # Canonical role-based fallback for single-user or when using canonical RoleGrants
        try:
            self.require(ActorContext(subject), action, scope)
            return
        except AuthorizationError:
            # If not found in standard roles and multi-user is enabled, strictly deny
            if multi_user_enabled:
                raise AuthorizationError("EXPERT_AUTH_DENIED")

        # Single user mode: if actor is local_admin and multi_user is disabled, allow admin actions
        if not multi_user_enabled and subject == LOCAL_ADMIN_ACTOR_ID:
            if action in (ACTION_COVERAGE_MANAGE, ACTION_PUBLICATION_PUBLISH):
                return

        raise AuthorizationError("EXPERT_AUTH_DENIED")

    def has_expert_action(
        self,
        principal: Union[VerifiedPrincipal, ActorContext],
        action: str,
        scope: str,
        current_time_iso: Optional[str] = None,
    ) -> bool:
        """Check if principal is authorized for expert action without raising exception."""
        try:
            self.require_expert_action(principal, action, scope, current_time_iso)
            return True
        except (AuthorizationError, PermissionError):
            return False
