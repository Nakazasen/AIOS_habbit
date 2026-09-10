"""Unit, integration, and security negative tests for Expert Identity and Scoped Authorization.

Implements T013 and T014 of 010-expert-knowledge-acquisition.
Verifies fail-closed invariants:
1. Impersonation denial.
2. Duplicate subject prevention.
3. Disabled/suspended profile denial.
4. Scope mismatch denial.
5. Grant expiry and revocation denial.
6. Identity provider operational failure handling.
7. Absolute prohibition of silent fallback to local_admin when multi-user is active (T014).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from aios_habit.expert_identity import (
    ACTION_ARTIFACT_APPROVE,
    ACTION_ARTIFACT_CANDIDATE_CREATE,
    ACTION_CLAIM_REVIEW,
    ACTION_COVERAGE_MANAGE,
    ACTION_INTERVIEW_ANSWER,
    ACTION_PUBLICATION_PUBLISH,
    ExpertProfile,
    FixtureIdentityProvider,
    IdentityProviderError,
    ScopeGrant,
    VerifiedPrincipal,
)
from aios_habit.expert_identity_windows import WindowsOSIdentityProvider
from aios_habit.feature_flags import override_feature_flags
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    LOCAL_ADMIN_ACTOR_ID,
    WorkspaceCaseAuthorization,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


@pytest.fixture
def repo(tmp_path: Path) -> WorkspaceCaseRepository:
    """Fixture providing an initialized SQLite repository."""
    db_path = tmp_path / "workspace_cases.sqlite"
    r = WorkspaceCaseRepository(db_path)
    r.initialize()
    return r


@pytest.fixture
def auth(repo: WorkspaceCaseRepository) -> WorkspaceCaseAuthorization:
    """Fixture providing authorization engine bound to repository."""
    return WorkspaceCaseAuthorization(repo)


def test_verified_principal_validation():
    """VerifiedPrincipal must enforce non-empty subject and provider name."""
    with pytest.raises(ValueError, match="subject"):
        VerifiedPrincipal(subject="", provider_name="test", display_name="User")
    with pytest.raises(ValueError, match="nhà cung cấp"):
        VerifiedPrincipal(subject="sub-1", provider_name="", display_name="User")

    principal = VerifiedPrincipal(
        subject="sub-1",
        provider_name="test_provider",
        display_name="Nguyen Van A",
    )
    assert principal.subject == "sub-1"
    assert principal.display_name == "Nguyen Van A"


def test_fixture_identity_provider_and_failure_simulation():
    """FixtureIdentityProvider must support failure simulation."""
    provider = FixtureIdentityProvider()
    assert provider.resolve_current_principal() is None

    test_principal = VerifiedPrincipal(
        subject="sim_user_1",
        provider_name="fixture_simulated",
        display_name="Simulated Expert",
    )
    provider.set_current_principal(test_principal)
    assert provider.resolve_current_principal() == test_principal

    # Simulate operational outage
    provider.simulate_failure(True, "Mất kết nối Active Directory.")
    with pytest.raises(IdentityProviderError, match="Mất kết nối Active Directory."):
        provider.resolve_current_principal()

    provider.simulate_failure(False)
    assert provider.resolve_current_principal() == test_principal


def test_windows_os_identity_provider_smoke():
    """WindowsOSIdentityProvider must return current OS user or None without password."""
    provider = WindowsOSIdentityProvider()
    assert provider.get_provider_name() == "windows_os"
    principal = provider.resolve_current_principal()
    assert principal is not None
    assert len(principal.subject) > 0
    # Strictly zero password or secret in metadata
    assert "password" not in principal.metadata
    assert "secret" not in principal.metadata


def test_expert_profile_persistence_and_duplicate_subject_prevention(repo: WorkspaceCaseRepository):
    """Database schema must enforce UNIQUE constraint on subject."""
    profile1 = ExpertProfile(
        expert_id="EXPERT-001",
        subject="win_user_alpha",
        full_name="Alpha Expert",
        scopes=("lsu_optical_assembly",),
        status="active",
    )
    repo.save_expert_profile(profile1)

    fetched = repo.get_expert_profile("EXPERT-001")
    assert fetched is not None
    assert fetched.subject == "win_user_alpha"
    assert "lsu_optical_assembly" in fetched.scopes

    # Another expert cannot claim the same subject
    profile2 = ExpertProfile(
        expert_id="EXPERT-002",
        subject="win_user_alpha",  # Duplicate subject!
        full_name="Duplicate Expert",
        scopes=("lsu_lens_calibration",),
        status="active",
    )
    with pytest.raises(sqlite3.IntegrityError):
        with repo._connect() as conn:
            conn.execute(
                "INSERT INTO expert_profiles (expert_id, subject, full_name, scopes_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("EXPERT-002", "win_user_alpha", "Duplicate Expert", '["lsu_lens_calibration"]', "active", "now", "now"),
            )


def test_impersonation_denial(repo: WorkspaceCaseRepository, auth: WorkspaceCaseAuthorization):
    """An intruder claiming an unverified subject is denied fail-closed."""
    # Profile exists for legitimate expert
    repo.save_expert_profile(
        ExpertProfile(
            expert_id="EXPERT-LEGIT",
            subject="expert_legit_subject",
            full_name="Legit Expert",
            scopes=("lsu_optical_assembly",),
            status="active",
        )
    )
    repo.save_scope_grant(
        ScopeGrant(
            grant_id="GRANT-LEGIT-1",
            subject="expert_legit_subject",
            action=ACTION_INTERVIEW_ANSWER,
            scope="lsu_optical_assembly",
            granted_by="admin",
        )
    )

    intruder = VerifiedPrincipal(
        subject="intruder_subject",
        provider_name="fixture_simulated",
        display_name="Malicious Actor",
    )

    with override_feature_flags(expert_multi_user=True):
        with pytest.raises(AuthorizationError, match="EXPERT_PROFILE_INACTIVE_OR_MISSING"):
            auth.require_expert_action(
                intruder,
                action=ACTION_INTERVIEW_ANSWER,
                scope="lsu_optical_assembly",
            )


def test_suspended_or_revoked_profile_denial(repo: WorkspaceCaseRepository, auth: WorkspaceCaseAuthorization):
    """Suspended or revoked expert profile cannot perform actions."""
    repo.save_expert_profile(
        ExpertProfile(
            expert_id="EXPERT-SUSPENDED",
            subject="subject_suspended",
            full_name="Suspended Expert",
            scopes=("lsu_optical_assembly",),
            status="suspended",
        )
    )
    repo.save_scope_grant(
        ScopeGrant(
            grant_id="GRANT-SUSPENDED-1",
            subject="subject_suspended",
            action=ACTION_INTERVIEW_ANSWER,
            scope="lsu_optical_assembly",
            granted_by="admin",
        )
    )

    principal = VerifiedPrincipal(
        subject="subject_suspended",
        provider_name="fixture_simulated",
        display_name="Suspended",
    )

    with override_feature_flags(expert_multi_user=True):
        with pytest.raises(AuthorizationError, match="EXPERT_PROFILE_INACTIVE_OR_MISSING"):
            auth.require_expert_action(
                principal,
                action=ACTION_INTERVIEW_ANSWER,
                scope="lsu_optical_assembly",
            )


def test_scope_mismatch_denial(repo: WorkspaceCaseRepository, auth: WorkspaceCaseAuthorization):
    """An expert granted scope A cannot perform action in scope B."""
    repo.save_expert_profile(
        ExpertProfile(
            expert_id="EXPERT-ALPHA",
            subject="subject_alpha",
            full_name="Alpha",
            scopes=("lsu_optical_assembly",),
            status="active",
        )
    )
    repo.save_scope_grant(
        ScopeGrant(
            grant_id="GRANT-ALPHA-1",
            subject="subject_alpha",
            action=ACTION_INTERVIEW_ANSWER,
            scope="lsu_optical_assembly",
            granted_by="admin",
        )
    )

    principal = VerifiedPrincipal(
        subject="subject_alpha",
        provider_name="fixture_simulated",
        display_name="Alpha",
    )

    with override_feature_flags(expert_multi_user=True):
        # Scope A succeeds
        auth.require_expert_action(principal, ACTION_INTERVIEW_ANSWER, "lsu_optical_assembly")

        # Scope B fails
        with pytest.raises(AuthorizationError, match="EXPERT_SCOPE_NOT_IN_PROFILE"):
            auth.require_expert_action(principal, ACTION_INTERVIEW_ANSWER, "lsu_lens_calibration")


def test_grant_expiry_denial(repo: WorkspaceCaseRepository, auth: WorkspaceCaseAuthorization):
    """Expired grant is strictly rejected."""
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(hours=2)).isoformat()

    repo.save_expert_profile(
        ExpertProfile(
            expert_id="EXPERT-EXPIRED",
            subject="subject_expired",
            full_name="Expired Expert",
            scopes=("lsu_optical_assembly",),
            status="active",
        )
    )
    repo.save_scope_grant(
        ScopeGrant(
            grant_id="GRANT-EXPIRED-1",
            subject="subject_expired",
            action=ACTION_INTERVIEW_ANSWER,
            scope="lsu_optical_assembly",
            granted_by="admin",
            expires_at=expired_time,
        )
    )

    principal = VerifiedPrincipal(
        subject="subject_expired",
        provider_name="fixture_simulated",
        display_name="Expired",
    )

    with override_feature_flags(expert_multi_user=True):
        with pytest.raises(AuthorizationError, match="EXPERT_ACTION_GRANT_MISSING"):
            auth.require_expert_action(principal, ACTION_INTERVIEW_ANSWER, "lsu_optical_assembly")


def test_grant_revocation_denial(repo: WorkspaceCaseRepository, auth: WorkspaceCaseAuthorization):
    """Revoking an active grant immediately denies future operations."""
    repo.save_expert_profile(
        ExpertProfile(
            expert_id="EXPERT-REVOKED",
            subject="subject_revoked",
            full_name="Revoked Expert",
            scopes=("lsu_optical_assembly",),
            status="active",
        )
    )
    repo.save_scope_grant(
        ScopeGrant(
            grant_id="GRANT-REVOKE-ME",
            subject="subject_revoked",
            action=ACTION_INTERVIEW_ANSWER,
            scope="lsu_optical_assembly",
            granted_by="admin",
        )
    )

    principal = VerifiedPrincipal(
        subject="subject_revoked",
        provider_name="fixture_simulated",
        display_name="To Revoke",
    )

    with override_feature_flags(expert_multi_user=True):
        # Authorized before revocation
        auth.require_expert_action(principal, ACTION_INTERVIEW_ANSWER, "lsu_optical_assembly")

        # Explicit revocation
        repo.revoke_scope_grant("GRANT-REVOKE-ME", revoked_by="security_admin")

        # Must be denied immediately
        with pytest.raises(AuthorizationError, match="EXPERT_ACTION_GRANT_MISSING"):
            auth.require_expert_action(principal, ACTION_INTERVIEW_ANSWER, "lsu_optical_assembly")


def test_t014_no_fallback_to_local_admin_when_multi_user_enabled(
    repo: WorkspaceCaseRepository, auth: WorkspaceCaseAuthorization
):
    """T014: Under multi-user mode, unauthorized users CANNOT fallback to local_admin."""
    intruder = VerifiedPrincipal(
        subject="unknown_external_caller",
        provider_name="fixture_simulated",
        display_name="Intruder",
    )

    with override_feature_flags(expert_multi_user=True):
        # Attempting to call as arbitrary ungranted subject
        with pytest.raises(AuthorizationError):
            auth.require_expert_action(
                intruder,
                action=ACTION_INTERVIEW_ANSWER,
                scope="lsu_optical_assembly",
            )

        # Attempting to spoof local_admin directly when multi-user is active
        local_admin_actor = ActorContext(LOCAL_ADMIN_ACTOR_ID)
        with pytest.raises(AuthorizationError):
            auth.require_expert_action(
                local_admin_actor,
                action=ACTION_INTERVIEW_ANSWER,
                scope="lsu_optical_assembly",
            )


def test_os_name_is_only_an_editable_non_authoritative_suggestion(monkeypatch):
    from aios_habit.expert_identity_windows import suggest_recorded_person

    monkeypatch.setattr("getpass.getuser", lambda: "ten_goi_y")
    monkeypatch.setattr("platform.node", lambda: "MAY-01")
    suggestion = suggest_recorded_person()

    assert suggestion.suggested_name == "ten_goi_y"
    assert suggestion.machine_ref == "MAY-01"
    assert suggestion.is_verified is False
    edited_name = "Tên người dùng tự sửa"
    assert edited_name != suggestion.suggested_name


def test_recorded_person_suggestion_confers_no_authorization_or_grants(auth: WorkspaceCaseAuthorization):
    """T089: RecordedPersonSuggestion is responsibility attribution only; it does NOT grant authority."""
    from aios_habit.expert_identity_windows import suggest_recorded_person

    suggestion = suggest_recorded_person()
    assert suggestion.is_verified is False

    # RecordedPersonSuggestion cannot be used as VerifiedPrincipal to bypass authorization
    with pytest.raises(AuthorizationError, match="EXPERT_PRINCIPAL_INVALID"):
        auth.require_expert_action(
            suggestion,  # type: ignore[arg-type]
            action=ACTION_INTERVIEW_ANSWER,
            scope="lsu_optical_assembly",
        )
