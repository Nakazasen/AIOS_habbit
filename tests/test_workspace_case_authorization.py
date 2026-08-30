from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    RoleGrant,
    WorkspaceCaseAuthorization,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


def _iso(delta_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat()


def test_same_actor_can_hold_investigator_and_expert_grants_for_same_scope(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    auth = WorkspaceCaseAuthorization(store)
    store.replace_role_grants(
        "worker-1",
        [
            RoleGrant("GRANT-1", "worker-1", "investigator", "line-a", _iso(-1), _iso(1)),
            RoleGrant("GRANT-2", "worker-1", "expert", "line-a", _iso(-1), _iso(1)),
        ],
    )

    auth.require(ActorContext("worker-1"), "case.transition", "line-a")
    auth.require(ActorContext("worker-1"), "expert.review", "line-a")


@pytest.mark.parametrize("scope", ["line-b", "*"])
def test_authorization_fails_closed_for_wrong_or_wildcard_scope(tmp_path, scope):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    auth = WorkspaceCaseAuthorization(store)
    store.replace_role_grants(
        "worker-1",
        [RoleGrant("GRANT-1", "worker-1", "investigator", scope, _iso(-1), _iso(1))],
    )

    with pytest.raises(AuthorizationError, match="CASE_AUTH_DENIED"):
        auth.require(ActorContext("worker-1"), "case.transition", "line-a")


def test_authorization_rejects_expired_revoked_and_admin_wildcard_assumptions(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    auth = WorkspaceCaseAuthorization(store)
    store.replace_role_grants(
        "actor-1",
        [
            RoleGrant("EXPIRED", "actor-1", "investigator", "line-a", _iso(-2), _iso(-1)),
            RoleGrant("REVOKED", "actor-1", "expert", "line-a", _iso(-1), _iso(1), revoked_at=_iso(0)),
            RoleGrant("ADMIN", "actor-1", "admin", "line-a", _iso(-1), _iso(1)),
        ],
    )

    with pytest.raises(AuthorizationError, match="CASE_AUTH_DENIED"):
        auth.require(ActorContext("actor-1"), "shadow.approve", "line-a")


def test_missing_actor_fails_closed(tmp_path):
    auth = WorkspaceCaseAuthorization(WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite"))
    with pytest.raises(AuthorizationError, match="CASE_ACTOR_REQUIRED"):
        auth.require(ActorContext(""), "case.view", "general")


def test_authorization_rejects_timestamps_without_timezone(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    auth = WorkspaceCaseAuthorization(store)
    store.replace_role_grants(
        "worker-1",
        [RoleGrant("GRANT-NAIVE", "worker-1", "investigator", "line-a", "2026-01-01T00:00:00", "2027-01-01T00:00:00")],
    )

    with pytest.raises(AuthorizationError, match="CASE_AUTH_DENIED"):
        auth.require(ActorContext("worker-1"), "case.transition", "line-a")
