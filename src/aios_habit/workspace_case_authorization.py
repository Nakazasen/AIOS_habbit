"""Explicit local actor and role/scope authorization for Workspace cases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final


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
        }
    ),
    "expert": frozenset({"case.view", "case.attach_evidence", "expert.review"}),
    # Admin is deliberately not a wildcard; capabilities remain explicit.
    "admin": frozenset({"case.view", "case.configure_roles"}),
    "quality_manager": frozenset({"case.view", "learning.approve"}),
    "artifact_approver": frozenset({"case.view", "artifact.approve"}),
    "shadow_reviewer": frozenset({"case.view", "shadow.review"}),
    "system_owner": frozenset({"case.view", "shadow.approve"}),
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
            if grant.scope != scope or grant.scope == "*" or grant.revoked_at:
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
