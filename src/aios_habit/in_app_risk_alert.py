"""In-app risk alert gate and notification service for LSU Iris shadow predictions.

Adheres to specs/008-evidence-case-loop/spec.md (US10, FR-014, FR-015),
specs/008-evidence-case-loop/contracts/workspace-evidence-loop.md (Section 12), and
specs/008-evidence-case-loop/tasks.md (T049, T050, T051).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from aios_habit.prediction_shadow_ui import explain_technical_code
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    RoleGrant,
    WorkspaceCaseAuthorization,
    trusted_local_actor,
)
from aios_habit.workspace_case_repository import (
    WorkspaceCaseRepository,
    default_workspace_cases_db_path,
)



AUTHORIZED_POLICY_OWNER_ROLES = frozenset(
    {"system_owner", "quality_manager", "admin", "local_admin"}
)

ALLOWED_GATE_STATUSES = frozenset({"PASS", "PASS_WITH_WARNING"})


@dataclass
class AlertPolicy:
    """Bounded policy controlling whether in-app risk alerts may be displayed."""

    policy_id: str = "GLOBAL_ALERT_POLICY"
    is_enabled: bool = True
    approved_by: str = "local_admin"
    approved_at: str = ""
    allowed_roles: List[str] = field(
        default_factory=lambda: [
            "system_owner",
            "quality_manager",
            "admin",
            "local_admin",
            "operator",
            "qc_operator",
            "investigator",
        ]
    )
    max_alert_age_days: int = 7
    scope: str = "workspace_chat"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InAppRiskAlert:
    """In-app notification banner presented to authorized roles in Workspace Chat."""

    alert_id: str
    idempotency_key: str
    unit_serial: str
    title: str
    reason: str
    priority: str  # "Khẩn", "Cao", "Bình thường"
    as_of_time: str
    case_id: Optional[str] = None
    status: str = "active"  # "active", "acknowledged", "dismissed", "snoozed"
    responded_by: Optional[str] = None
    responded_at: Optional[str] = None
    response_note: str = ""
    snooze_until: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_alert_tables(db_path: Path) -> None:
    """Ensure in-app alert responses, policy, and kill switch tables exist with append-only schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(_get_connection(db_path)) as conn:
        with conn:
            # 1. Policy table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS in_app_alert_policy (
                    policy_id TEXT PRIMARY KEY,
                    is_enabled INTEGER NOT NULL,
                    approved_by TEXT NOT NULL,
                    approved_at TEXT NOT NULL,
                    allowed_roles TEXT NOT NULL,
                    max_alert_age_days INTEGER NOT NULL,
                    scope TEXT NOT NULL
                )
                """
            )

            # 2. Check if in_app_alert_responses needs migration to append-only (response_id as PK)
            table_info = conn.execute(
                "PRAGMA table_info(in_app_alert_responses)"
            ).fetchall()
            if table_info:
                col_names = {col["name"] for col in table_info}
                if "response_id" not in col_names:
                    conn.execute(
                        "ALTER TABLE in_app_alert_responses RENAME TO in_app_alert_responses_legacy"
                    )
                    conn.execute(
                        """
                        CREATE TABLE in_app_alert_responses (
                            response_id TEXT PRIMARY KEY,
                            alert_id TEXT NOT NULL,
                            idempotency_key TEXT NOT NULL,
                            unit_serial TEXT NOT NULL,
                            action TEXT NOT NULL,
                            responded_by TEXT NOT NULL,
                            responded_at TEXT NOT NULL,
                            notes TEXT NOT NULL,
                            snooze_until TEXT
                        )
                        """
                    )
                    legacy_rows = conn.execute(
                        "SELECT alert_id, idempotency_key, unit_serial, action, responded_by, responded_at, notes, snooze_until FROM in_app_alert_responses_legacy"
                    ).fetchall()
                    for idx, lr in enumerate(legacy_rows):
                        conn.execute(
                            """
                            INSERT INTO in_app_alert_responses (
                                response_id, alert_id, idempotency_key, unit_serial, action,
                                responded_by, responded_at, notes, snooze_until
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                f"MIG-{idx}-{lr[0]}",
                                lr[0],
                                lr[1],
                                lr[2],
                                lr[3],
                                lr[4],
                                lr[5],
                                lr[6],
                                lr[7],
                            ),
                        )
                    conn.execute("DROP TABLE in_app_alert_responses_legacy")
            else:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS in_app_alert_responses (
                        response_id TEXT PRIMARY KEY,
                        alert_id TEXT NOT NULL,
                        idempotency_key TEXT NOT NULL,
                        unit_serial TEXT NOT NULL,
                        action TEXT NOT NULL,
                        responded_by TEXT NOT NULL,
                        responded_at TEXT NOT NULL,
                        notes TEXT NOT NULL,
                        snooze_until TEXT
                    )
                    """
                )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_resp_key ON in_app_alert_responses(idempotency_key, responded_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_resp_alert_id ON in_app_alert_responses(alert_id, responded_at DESC)"
            )

            # 3. Kill switch table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS in_app_alert_kill_switch (
                    switch_id TEXT PRIMARY KEY,
                    is_active INTEGER NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reason TEXT NOT NULL
                )
                """
            )


def _resolve_case_repo(
    db_path: Optional[Path] = None,
    case_repo: Optional[WorkspaceCaseRepository] = None,
    case_db_path: Optional[Path] = None,
) -> WorkspaceCaseRepository:
    """Resolve the canonical WorkspaceCaseRepository."""
    if case_repo is not None:
        case_repo.initialize()
        return case_repo
    if case_db_path is not None:
        repo = WorkspaceCaseRepository(case_db_path)
        repo.initialize()
        return repo
    if db_path is not None:
        candidate = db_path.parent / "workspace_cases.sqlite"
        repo = WorkspaceCaseRepository(candidate)
        repo.initialize()
        return repo
    repo = WorkspaceCaseRepository()
    repo.initialize()
    return repo


def _ensure_default_local_admin_grants(repo: WorkspaceCaseRepository) -> None:
    """Ensure trusted local admin holds base administrative role grants in canonical store."""
    admin_id = "local_admin"
    existing = {g.role for g in repo.list_role_grants(admin_id) if not g.revoked_at}
    needed = [
        ("DEFAULT-LOCAL-ADMIN-LOCAL-ADMIN", "local_admin", "general"),
        ("DEFAULT-LOCAL-ADMIN-SYSTEM-OWNER", "system_owner", "general"),
        ("DEFAULT-LOCAL-ADMIN-QC-OPERATOR", "qc_operator", "general"),
        ("DEFAULT-LOCAL-ADMIN-QM", "quality_manager", "general"),
        ("DEFAULT-LOCAL-ADMIN-ADMIN", "admin", "general"),
    ]
    to_add: List[RoleGrant] = []
    for gid, role, scope in needed:
        if role not in existing:
            to_add.append(
                RoleGrant(
                    grant_id=gid,
                    actor_id=admin_id,
                    role=role,
                    scope=scope,
                    valid_from="2000-01-01T00:00:00+00:00",
                    valid_until="9999-12-31T23:59:59+00:00",
                    revoked_at=None,
                )
            )
    if to_add:
        all_grants = repo.list_role_grants(admin_id) + to_add
        repo.replace_role_grants(admin_id, all_grants)


def _resolve_authorizer(
    db_path: Optional[Path] = None,
    auth: Optional[WorkspaceCaseAuthorization] = None,
    case_repo: Optional[WorkspaceCaseRepository] = None,
    case_db_path: Optional[Path] = None,
) -> WorkspaceCaseAuthorization:
    """Resolve WorkspaceCaseAuthorization wrapping the canonical repository."""
    if auth is not None:
        return auth
    repo = _resolve_case_repo(db_path=db_path, case_repo=case_repo, case_db_path=case_db_path)
    _ensure_default_local_admin_grants(repo)
    return WorkspaceCaseAuthorization(repo)


def get_in_app_alert_policy(db_path: Path) -> Optional[AlertPolicy]:
    """Load active in-app alert policy from local storage."""
    ensure_alert_tables(db_path)
    with closing(_get_connection(db_path)) as conn:
        row = conn.execute(
            "SELECT policy_id, is_enabled, approved_by, approved_at, allowed_roles, max_alert_age_days, scope "
            "FROM in_app_alert_policy WHERE policy_id = 'GLOBAL_ALERT_POLICY'"
        ).fetchone()
        if row is None:
            return None
        allowed_roles = json.loads(row["allowed_roles"]) if row["allowed_roles"] else []
        return AlertPolicy(
            policy_id=row["policy_id"],
            is_enabled=bool(row["is_enabled"]),
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            allowed_roles=allowed_roles,
            max_alert_age_days=int(row["max_alert_age_days"]),
            scope=row["scope"],
        )


def grant_role_permission(
    db_or_repo: Path | WorkspaceCaseRepository,
    *,
    actor_id: str,
    role: str,
    scope: str = "workspace_chat",
    valid_from: str = "2000-01-01T00:00:00+00:00",
    valid_until: str = "9999-12-31T23:59:59+00:00",
    grant_id: Optional[str] = None,
) -> RoleGrant:
    """Explicitly grant a role to an actor in the canonical WorkspaceCaseRepository storage."""
    repo = _resolve_case_repo(
        db_path=db_or_repo if isinstance(db_or_repo, Path) else None,
        case_repo=db_or_repo if isinstance(db_or_repo, WorkspaceCaseRepository) else None,
    )
    gid = grant_id or f"GRANT-{actor_id.upper()}-{role.upper()}-{uuid.uuid4().hex[:8]}"
    grant = RoleGrant(
        grant_id=gid,
        actor_id=actor_id,
        role=role,
        scope=scope,
        valid_from=valid_from,
        valid_until=valid_until,
        revoked_at=None,
    )
    existing = [g for g in repo.list_role_grants(actor_id) if g.grant_id != gid]
    existing.append(grant)
    repo.replace_role_grants(actor_id, existing)
    return grant


def revoke_role_permission(
    db_or_repo: Path | WorkspaceCaseRepository,
    grant_id: str,
) -> None:
    """Revoke a role grant immediately in the canonical WorkspaceCaseRepository storage."""
    repo = _resolve_case_repo(
        db_path=db_or_repo if isinstance(db_or_repo, Path) else None,
        case_repo=db_or_repo if isinstance(db_or_repo, WorkspaceCaseRepository) else None,
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    with repo._connection() as conn:
        with conn:
            conn.execute("UPDATE role_grants SET revoked_at = ? WHERE grant_id = ?", (now_iso, grant_id))


def list_active_role_grants(
    db_or_repo: Path | WorkspaceCaseRepository,
    actor_id: str,
    scope: str = "workspace_chat",
) -> List[RoleGrant]:
    """List unrevoked, active role grants for an actor from the canonical WorkspaceCaseRepository."""
    repo = _resolve_case_repo(
        db_path=db_or_repo if isinstance(db_or_repo, Path) else None,
        case_repo=db_or_repo if isinstance(db_or_repo, WorkspaceCaseRepository) else None,
    )
    now = datetime.now(timezone.utc)
    grants = repo.list_role_grants(actor_id)
    valid_grants: List[RoleGrant] = []
    for r in grants:
        if r.scope != scope and r.scope != "general":
            continue
        if r.revoked_at:
            continue
        try:
            vf = datetime.fromisoformat(r.valid_from.replace("Z", "+00:00"))
            vu = datetime.fromisoformat(r.valid_until.replace("Z", "+00:00"))
            if vf.tzinfo is None:
                vf = vf.replace(tzinfo=timezone.utc)
            if vu.tzinfo is None:
                vu = vu.replace(tzinfo=timezone.utc)
            if vf <= now <= vu:
                valid_grants.append(r)
        except Exception:
            continue
    return valid_grants


def verify_actor_role_authorization(
    db_path: Path,
    actor: str | ActorContext,
    required_role: Optional[str] = None,
    scope: str = "workspace_chat",
    auth: Optional[WorkspaceCaseAuthorization] = None,
    case_repo: Optional[WorkspaceCaseRepository] = None,
    case_db_path: Optional[Path] = None,
) -> str:
    """
    Fail-closed verification: check ActorContext + RoleGrant in canonical storage.
    Prevents self-claiming of roles (e.g. actor='intruder' passing actor_role='system_owner').
    """
    actor_id = actor.actor_id if isinstance(actor, ActorContext) else str(actor).strip()
    if not actor_id:
        raise PermissionError("Yêu cầu định danh người dùng (actor) hợp lệ.")

    authorizer = _resolve_authorizer(
        db_path=db_path,
        auth=auth,
        case_repo=case_repo,
        case_db_path=case_db_path,
    )
    active_roles = authorizer.get_active_roles(ActorContext(actor_id), scope=scope)

    if required_role:
        if required_role not in active_roles:
            raise PermissionError(
                f"Người dùng '{actor_id}' không có cấp quyền (RoleGrant) hợp lệ cho vai trò '{required_role}' trong phạm vi '{scope}'."
            )
        if required_role not in AUTHORIZED_POLICY_OWNER_ROLES:
            raise PermissionError(
                f"Vai trò '{required_role}' không có thẩm quyền quản lý hoặc phê duyệt chính sách cảnh báo nguy cơ."
            )
        return required_role
    else:
        for role_candidate in ["system_owner", "quality_manager", "admin", "local_admin"]:
            if role_candidate in active_roles:
                return role_candidate
        raise PermissionError(
            f"Người dùng '{actor_id}' không có bất kỳ cấp quyền (RoleGrant) nào thuộc danh mục vai trò quản lý có thẩm quyền trong phạm vi '{scope}'."
        )


def enable_in_app_alert_policy(
    db_path: Path,
    policy: AlertPolicy,
    actor: str | ActorContext,
    actor_role: Optional[str] = None,
    scope: Optional[str] = None,
    auth: Optional[WorkspaceCaseAuthorization] = None,
    case_repo: Optional[WorkspaceCaseRepository] = None,
    case_db_path: Optional[Path] = None,
) -> AlertPolicy:
    """
    Contract Section 12: enable_in_app_alert_policy(policy, actor) -> AlertPolicy.
    Fail-closed authorization: requires explicit owner or quality manager authorization
    via verified ActorContext + RoleGrant in scope. Does NOT allow self-claimed roles.
    """
    ensure_alert_tables(db_path)
    actor_id = actor.actor_id if isinstance(actor, ActorContext) else str(actor).strip()
    if not actor_id:
        raise PermissionError(
            "Yêu cầu định danh người dùng (actor) hợp lệ để phê duyệt chính sách cảnh báo nguy cơ."
        )

    effective_scope = scope or policy.scope or "workspace_chat"
    verified_role = verify_actor_role_authorization(
        db_path,
        actor=actor,
        required_role=actor_role,
        scope=effective_scope,
        auth=auth,
        case_repo=case_repo,
        case_db_path=case_db_path,
    )

    authorizer = _resolve_authorizer(
        db_path=db_path,
        auth=auth,
        case_repo=case_repo,
        case_db_path=case_db_path,
    )
    try:
        authorizer.require(ActorContext(actor_id), "alert.manage_policy", scope=effective_scope)
    except Exception as err:
        raise PermissionError(
            f"Người dùng '{actor_id}' không có quyền quản lý chính sách cảnh báo nguy cơ trong phạm vi '{effective_scope}'."
        ) from err

    now_iso = datetime.now(timezone.utc).isoformat()
    approved_policy = AlertPolicy(
        policy_id=policy.policy_id or "GLOBAL_ALERT_POLICY",
        is_enabled=policy.is_enabled,
        approved_by=actor_id,
        approved_at=now_iso,
        allowed_roles=list(policy.allowed_roles),
        max_alert_age_days=max(1, policy.max_alert_age_days),
        scope=effective_scope,
    )

    with closing(_get_connection(db_path)) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO in_app_alert_policy (
                    policy_id, is_enabled, approved_by, approved_at, allowed_roles, max_alert_age_days, scope
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(policy_id) DO UPDATE SET
                    is_enabled = excluded.is_enabled,
                    approved_by = excluded.approved_by,
                    approved_at = excluded.approved_at,
                    allowed_roles = excluded.allowed_roles,
                    max_alert_age_days = excluded.max_alert_age_days,
                    scope = excluded.scope
                """,
                (
                    approved_policy.policy_id,
                    1 if approved_policy.is_enabled else 0,
                    approved_policy.approved_by,
                    approved_policy.approved_at,
                    json.dumps(approved_policy.allowed_roles, ensure_ascii=False),
                    approved_policy.max_alert_age_days,
                    approved_policy.scope,
                ),
            )
    return approved_policy


def is_kill_switch_active(db_path: Path) -> bool:
    """Check whether in-app alert kill switch is currently active."""
    ensure_alert_tables(db_path)
    with closing(_get_connection(db_path)) as conn:
        row = conn.execute(
            "SELECT is_active FROM in_app_alert_kill_switch WHERE switch_id = 'GLOBAL_KILL_SWITCH'"
        ).fetchone()
        if row is None:
            return False
        return bool(row[0])


def set_kill_switch(
    db_path: Path,
    active: bool,
    *,
    actor: str | ActorContext,
    actor_role: Optional[str] = None,
    reason: str = "",
    scope: str = "workspace_chat",
    auth: Optional[WorkspaceCaseAuthorization] = None,
    case_repo: Optional[WorkspaceCaseRepository] = None,
    case_db_path: Optional[Path] = None,
) -> None:
    """
    Activate or deactivate the global alert emergency cutoff switch immediately.
    Fail-closed authorization: requires verified ActorContext + RoleGrant in scope.
    """
    ensure_alert_tables(db_path)
    actor_id = actor.actor_id if isinstance(actor, ActorContext) else str(actor).strip()
    if not actor_id:
        raise PermissionError("Yêu cầu định danh người dùng (actor) để thao tác công tắc ngắt khẩn cấp.")

    verified_role = verify_actor_role_authorization(
        db_path,
        actor=actor,
        required_role=actor_role,
        scope=scope,
        auth=auth,
        case_repo=case_repo,
        case_db_path=case_db_path,
    )

    authorizer = _resolve_authorizer(
        db_path=db_path,
        auth=auth,
        case_repo=case_repo,
        case_db_path=case_db_path,
    )
    try:
        authorizer.require(ActorContext(actor_id), "alert.kill_switch", scope=scope)
    except Exception as err:
        raise PermissionError(
            f"Người dùng '{actor_id}' không có quyền thao tác công tắc ngắt khẩn cấp trong phạm vi '{scope}'."
        ) from err

    now_iso = datetime.now(timezone.utc).isoformat()
    with closing(_get_connection(db_path)) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO in_app_alert_kill_switch (switch_id, is_active, updated_by, updated_at, reason)
                VALUES ('GLOBAL_KILL_SWITCH', ?, ?, ?, ?)
                ON CONFLICT(switch_id) DO UPDATE SET
                    is_active = excluded.is_active,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at,
                    reason = excluded.reason
                """,
                (1 if active else 0, actor_id, now_iso, reason.strip() or ("Người vận hành thao tác" if active else "Khôi phục cảnh báo")),
            )



def acknowledge_alert(
    db_path: Path,
    *,
    alert_id: str,
    idempotency_key: str,
    unit_serial: str,
    actor: str,
    notes: str = "",
) -> str:
    """User action 1: Acknowledge risk alert receipt with append-only history."""
    ensure_alert_tables(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    response_id = f"RESP-ACK-{uuid.uuid4().hex[:12].upper()}"
    with closing(_get_connection(db_path)) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO in_app_alert_responses (
                    response_id, alert_id, idempotency_key, unit_serial, action,
                    responded_by, responded_at, notes, snooze_until
                ) VALUES (?, ?, ?, ?, 'acknowledged', ?, ?, ?, NULL)
                """,
                (
                    response_id,
                    alert_id,
                    idempotency_key,
                    unit_serial,
                    actor,
                    now_iso,
                    notes.strip(),
                ),
            )
    return response_id


def dismiss_alert(
    db_path: Path,
    *,
    alert_id: str,
    idempotency_key: str,
    unit_serial: str,
    actor: str,
    notes: str,
) -> str:
    """User action 2: Dismiss risk alert with mandatory justification into append-only history."""
    clean_notes = notes.strip()
    if not clean_notes:
        raise ValueError("Vui lòng cung cấp lý do khi bác bỏ cảnh báo nguy cơ.")
    ensure_alert_tables(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    response_id = f"RESP-DIS-{uuid.uuid4().hex[:12].upper()}"
    with closing(_get_connection(db_path)) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO in_app_alert_responses (
                    response_id, alert_id, idempotency_key, unit_serial, action,
                    responded_by, responded_at, notes, snooze_until
                ) VALUES (?, ?, ?, ?, 'dismissed', ?, ?, ?, NULL)
                """,
                (
                    response_id,
                    alert_id,
                    idempotency_key,
                    unit_serial,
                    actor,
                    now_iso,
                    clean_notes,
                ),
            )
    return response_id


def snooze_alert(
    db_path: Path,
    *,
    alert_id: str,
    idempotency_key: str,
    unit_serial: str,
    actor: str,
    duration_minutes: int = 60,
    notes: str = "",
) -> str:
    """User action 3: Temporarily snooze alert for specified minutes into append-only history."""
    ensure_alert_tables(db_path)
    now = datetime.now(timezone.utc)
    snooze_until = (now + timedelta(minutes=duration_minutes)).isoformat()
    response_id = f"RESP-SNZ-{uuid.uuid4().hex[:12].upper()}"
    with closing(_get_connection(db_path)) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO in_app_alert_responses (
                    response_id, alert_id, idempotency_key, unit_serial, action,
                    responded_by, responded_at, notes, snooze_until
                ) VALUES (?, ?, ?, ?, 'snoozed', ?, ?, ?, ?)
                """,
                (
                    response_id,
                    alert_id,
                    idempotency_key,
                    unit_serial,
                    actor,
                    now.isoformat(),
                    notes.strip(),
                    snooze_until,
                ),
            )
    return snooze_until


def get_alert_response_history(
    db_path: Path,
    *,
    idempotency_key: Optional[str] = None,
    alert_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve full append-only response audit trail."""
    ensure_alert_tables(db_path)
    with closing(_get_connection(db_path)) as conn:
        query = (
            "SELECT response_id, alert_id, idempotency_key, unit_serial, action, "
            "responded_by, responded_at, notes, snooze_until FROM in_app_alert_responses"
        )
        params: List[Any] = []
        conditions: List[str] = []
        if idempotency_key:
            conditions.append("idempotency_key = ?")
            params.append(idempotency_key)
        if alert_id:
            conditions.append("alert_id = ?")
            params.append(alert_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY responded_at ASC, rowid ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def evaluate_alerts_for_display(
    db_path: Path,
    *,
    snapshot_id: Optional[str] = None,
    current_time_iso: Optional[str] = None,
    actor_role: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_context: Optional[ActorContext] = None,
    scope: str = "workspace_chat",
    auth: Optional[WorkspaceCaseAuthorization] = None,
    case_repo: Optional[WorkspaceCaseRepository] = None,
    case_db_path: Optional[Path] = None,
) -> Tuple[List[InAppRiskAlert], bool, str]:
    """
    Evaluates persisted shadow risk assessments against the in-app alert gate.
    Returns (active_alerts, is_kill_switched, status_message).
    Fail-closed: requires active approved policy, authorized role, passing data gate,
    no future leakage on gate or assessment, within TTL window, no kill switch, and deduplication.
    """
    ensure_alert_tables(db_path)

    # 1. Kill switch check (fail-closed)
    if is_kill_switch_active(db_path):
        return (
            [],
            True,
            "Hệ thống cảnh báo rủi ro đang bị tạm dừng bởi công tắc ngắt khẩn cấp.",
        )

    # 2. Owner Policy approval check (fail-closed)
    policy = get_in_app_alert_policy(db_path)
    if policy is None or not policy.is_enabled:
        return (
            [],
            False,
            "Chính sách cảnh báo nguy cơ trong ứng dụng chưa được phê duyệt hoặc đang tắt.",
        )

    # 3. Role and Actor authorization check (FAIL-CLOSED)
    if actor_role is not None and not str(actor_role).strip():
        return (
            [],
            False,
            "Yêu cầu vai trò người dùng (actor_role) hợp lệ để truy xuất cảnh báo nguy cơ.",
        )

    effective_actor_id = (
        actor_context.actor_id if actor_context else (str(actor_id).strip() if actor_id else None)
    )

    if not effective_actor_id and not actor_role:
        return (
            [],
            False,
            "Yêu cầu vai trò người dùng (actor_role) hợp lệ để truy xuất cảnh báo nguy cơ.",
        )

    act = actor_context or (ActorContext(effective_actor_id) if effective_actor_id else trusted_local_actor())

    authorizer = _resolve_authorizer(
        db_path=db_path,
        auth=auth,
        case_repo=case_repo,
        case_db_path=case_db_path,
    )

    # Capability verification: require "alert.view"
    try:
        authorizer.require(act, "alert.view", scope=scope)
    except Exception:
        return (
            [],
            False,
            f"Người dùng '{act.actor_id}' không có quyền nhận cảnh báo nguy cơ trong ứng dụng.",
        )

    # Role verification: verify actor actually holds the role in scope
    active_roles = authorizer.get_active_roles(act, scope=scope)
    resolved_role = actor_role.strip() if actor_role and str(actor_role).strip() else None

    if resolved_role:
        if resolved_role not in policy.allowed_roles:
            return (
                [],
                False,
                f"Vai trò '{resolved_role}' không có quyền nhận cảnh báo nguy cơ trong ứng dụng.",
            )
        if resolved_role not in active_roles:
            return (
                [],
                False,
                f"Người dùng '{act.actor_id}' không sở hữu vai trò '{resolved_role}' trong phạm vi '{scope}'.",
            )
    else:
        matching = [r for r in active_roles if r in policy.allowed_roles]
        if not matching:
            return (
                [],
                False,
                f"Người dùng '{act.actor_id}' không có vai trò nào được phép nhận cảnh báo theo chính sách.",
            )
        resolved_role = matching[0]

    now_dt = (
        datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
        if current_time_iso
        else datetime.now(timezone.utc)
    )

    with closing(_get_connection(db_path)) as conn:
        # 4. Resolve append-only responses chronologically
        resp_rows = conn.execute(
            "SELECT idempotency_key, action, snooze_until, responded_at "
            "FROM in_app_alert_responses "
            "ORDER BY responded_at ASC, rowid ASC"
        ).fetchall()

        # Map each key to its latest action
        latest_response_by_key: Dict[str, Tuple[str, Optional[str]]] = {}
        for r in resp_rows:
            key, act, snooze_str = r["idempotency_key"], r["action"], r["snooze_until"]
            latest_response_by_key[key] = (act, snooze_str)

        suppressed_keys: Set[str] = set()
        for key, (act, snooze_str) in latest_response_by_key.items():
            if act in ("acknowledged", "dismissed"):
                suppressed_keys.add(key)
            elif act == "snoozed" and snooze_str:
                try:
                    snooze_dt = datetime.fromisoformat(
                        snooze_str.replace("Z", "+00:00")
                    )
                    if now_dt < snooze_dt:
                        suppressed_keys.add(key)
                except Exception:
                    pass

        # 5. Load shadow risk assessments joined with snapshot and data gate report
        query = """
            SELECT sra.idempotency_key, sra.snapshot_id, sra.unit_serial,
                   sra.as_of_time, sra.risk_level, sra.reason, sra.case_id,
                   sra.future_leakage_detected,
                   snap.content_digest,
                   dgr.status AS gate_status,
                   dgr.future_leak_count
            FROM shadow_risk_assessments sra
            LEFT JOIN lsu_snapshots snap ON sra.snapshot_id = snap.snapshot_id
            LEFT JOIN data_gate_reports dgr ON sra.snapshot_id = dgr.snapshot_id
        """
        params: List[Any] = []
        if snapshot_id:
            query += " WHERE sra.snapshot_id = ?"
            params.append(snapshot_id)
        query += " ORDER BY sra.rowid DESC"

        try:
            rows = conn.execute(query, params).fetchall()
        except sqlite3.OperationalError:
            return ([], False, "Chưa có dữ liệu đánh giá nguy cơ từ thử nghiệm bóng.")

        alerts: List[InAppRiskAlert] = []
        for r in rows:
            idem_key = r["idempotency_key"]
            snap_id = r["snapshot_id"]
            unit_serial = r["unit_serial"]
            as_of_time = r["as_of_time"]
            risk_level = r["risk_level"]
            reason = r["reason"]
            case_id = r["case_id"]
            snap_digest = r["content_digest"]
            gate_status = r["gate_status"]
            future_leak_count = r["future_leak_count"]
            future_leakage_detected = r["future_leakage_detected"]

            # Provenance gate: snapshot must exist and have content digest
            if not snap_digest:
                continue

            # DataGateStatus check: fail-closed if status is missing or not passing
            if not gate_status or gate_status not in ALLOWED_GATE_STATUSES:
                continue

            # Future leakage gate on data gate report: strictly zero future leaks permitted
            if future_leak_count is not None and future_leak_count > 0:
                continue

            # Future leakage gate on assessment itself: fail-closed if future leakage detected
            if bool(future_leakage_detected):
                continue

            # Expiration / TTL gate: filter out alerts older than policy max_alert_age_days
            if as_of_time:
                try:
                    as_of_dt = datetime.fromisoformat(as_of_time.replace("Z", "+00:00"))
                    if now_dt - as_of_dt > timedelta(days=policy.max_alert_age_days):
                        continue
                except Exception:
                    continue

            # Deduplication gate: skip acknowledged, dismissed, or currently snoozed
            if idem_key in suppressed_keys:
                continue

            # Risk threshold gate: only elevated risk levels trigger alert banner
            if risk_level not in ("HIGH", "ELEVATED", "WARNING"):
                continue

            alert_id = (
                f"ALT-{hashlib.sha256(idem_key.encode('utf-8')).hexdigest()[:10].upper()}"
            )
            explained_reason = explain_technical_code(reason)
            clean_reason = f"Phát hiện nguy cơ lệch chuẩn dung sai kiểm soát ({explained_reason}). Cần kiểm tra trước khi lắp ráp."

            priority_label = "Khẩn" if risk_level == "HIGH" else "Cao"

            alerts.append(
                InAppRiskAlert(
                    alert_id=alert_id,
                    idempotency_key=idem_key,
                    unit_serial=unit_serial,
                    title=f"Cảnh báo nguy cơ linh kiện: {unit_serial}",
                    reason=clean_reason,
                    priority=priority_label,
                    as_of_time=as_of_time or now_dt.isoformat(),
                    case_id=case_id,
                    status="active",
                )
            )

        msg = (
            f"Có {len(alerts)} cảnh báo nguy cơ cần chú ý."
            if alerts
            else "Không có cảnh báo nguy cơ nào đang hoạt động."
        )
        return (alerts, False, msg)


def render_in_app_risk_alerts(
    db_path: Path,
    *,
    on_open_case: Callable[[str], None],
    actor: str = "local_admin",
    actor_role: str = "local_admin",
    locale: str = "vi",
) -> None:
    """Render approved in-app alerts, bounded user actions, and operator kill switch controls."""
    del locale  # Giao diện sản phẩm chỉ hỗ trợ tiếng Việt.

    try:
        import streamlit as st
    except ImportError:
        return

    # Operator and Admin controls expander for Kill Switch & Policy management
    actor_ctx = ActorContext(actor) if isinstance(actor, str) else actor
    authorizer = _resolve_authorizer(db_path=Path(db_path))
    active_roles = authorizer.get_active_roles(actor_ctx, scope="workspace_chat")
    is_owner_or_admin = (actor_role in AUTHORIZED_POLICY_OWNER_ROLES and actor_role in active_roles) or bool(active_roles.intersection(AUTHORIZED_POLICY_OWNER_ROLES))
    kill_sw_active = is_kill_switch_active(Path(db_path))
    current_policy = get_in_app_alert_policy(Path(db_path))

    with st.expander("⚙️ Quản lý công tắc ngắt khẩn cấp và Chính sách cảnh báo", expanded=False):
        st.markdown("#### Trạng thái công tắc ngắt khẩn cấp")
        if kill_sw_active:
            st.markdown("🚨 **Trạng thái:** Công tắc ngắt khẩn cấp ĐANG KÍCH HOẠT (Toàn bộ cảnh báo bị tạm dừng).")
            if is_owner_or_admin:
                if st.button("Khôi phục cảnh báo nguy cơ (Tắt công tắc ngắt khẩn cấp)", key="wsc_btn_deactivate_kill_switch"):
                    set_kill_switch(Path(db_path), active=False, actor=actor, actor_role=actor_role, reason="Người vận hành khôi phục trên giao diện")
                    st.rerun()
            else:
                st.caption("Chỉ người quản trị hoặc chủ sở hữu mới có quyền tắt công tắc ngắt khẩn cấp.")
        else:
            st.markdown("✅ **Trạng thái:** Công tắc ngắt khẩn cấp ĐANG TẮT (Hệ thống cảnh báo hoạt động bình thường).")
            if is_owner_or_admin:
                reason_input = st.text_input("Lý do kích hoạt công tắc ngắt khẩn cấp", key="wsc_kill_switch_reason", placeholder="Nhập lý do tạm dừng khẩn cấp...")
                if st.button("Kích hoạt công tắc ngắt khẩn cấp (Tạm dừng mọi cảnh báo)", key="wsc_btn_activate_kill_switch"):
                    set_kill_switch(Path(db_path), active=True, actor=actor, actor_role=actor_role, reason=reason_input or "Kích hoạt từ giao diện người dùng")
                    st.rerun()
            else:
                st.caption("Chỉ người quản trị hoặc chủ sở hữu mới có quyền kích hoạt công tắc ngắt khẩn cấp.")

        if is_owner_or_admin:
            st.markdown("---")
            st.markdown("#### Phê duyệt chính sách cảnh báo (Dành cho Người phê duyệt)")
            if current_policy and current_policy.is_enabled:
                st.markdown(f"📋 **Chính sách hiện tại:** ĐANG BẬT · Người phê duyệt: {current_policy.approved_by} · Hạn lưu: {current_policy.max_alert_age_days} ngày.")
                if st.button("Tạm dừng chính sách cảnh báo", key="wsc_btn_disable_policy"):
                    new_policy = AlertPolicy(is_enabled=False, approved_by=actor)
                    enable_in_app_alert_policy(Path(db_path), new_policy, actor=actor, actor_role=actor_role)
                    st.rerun()
            else:
                st.markdown("⚠️ **Chính sách hiện tại:** ĐANG TẮT hoặc CHƯA ĐƯỢC PHÊ DUYỆT.")
                if st.button("Phê duyệt & Kích hoạt chính sách cảnh báo", key="wsc_btn_enable_policy"):
                    new_policy = AlertPolicy(is_enabled=True, approved_by=actor)
                    enable_in_app_alert_policy(Path(db_path), new_policy, actor=actor, actor_role=actor_role)
                    st.rerun()

    try:
        alerts, kill_switched, status_message = evaluate_alerts_for_display(
            Path(db_path),
            actor_role=actor_role,
            actor_id=actor,
        )
    except Exception:
        st.warning("Chưa thể đọc dữ liệu cảnh báo. Vui lòng kiểm tra lại kho dự đoán cục bộ.")
        return

    if kill_switched:
        st.warning(
            "Cảnh báo nguy cơ đang được tạm dừng bằng công tắc ngắt khẩn cấp. "
            "Vui lòng liên hệ người quản trị trước khi tiếp tục."
        )
        return

    if not alerts:
        st.info(
            f"{status_message} Chưa đủ dữ liệu đã vượt cổng để bật cảnh báo; "
            "hãy hoàn tất chạy bóng và xác nhận gói dữ liệu trước."
        )
        return

    st.markdown("### Cảnh báo nguy cơ cần kiểm tra")
    st.caption(
        "Đây là đề xuất kiểm tra dựa trên dữ liệu đã qua cổng; "
        "người có thẩm quyền vẫn quyết định hành động thực tế."
    )

    for alert in alerts:
        with st.container(border=True):
            st.markdown(f"#### {alert.title}")
            st.write(alert.reason)
            st.caption(
                f"Mức ưu tiên: {alert.priority} · Thời điểm: {alert.as_of_time}"
            )
            notes_key = f"wsc_alert_notes_{alert.alert_id}"
            notes = st.text_input(
                "Ghi chú phản hồi",
                key=notes_key,
                placeholder="Nhập lý do nếu bác bỏ hoặc ghi chú khi tiếp nhận.",
            )
            acknowledge_col, dismiss_col, snooze_col, open_case_col = st.columns(4)

            with acknowledge_col:
                if st.button(
                    "Tiếp nhận",
                    key=f"wsc_alert_ack_{alert.alert_id}",
                    use_container_width=True,
                ):
                    try:
                        acknowledge_alert(
                            Path(db_path),
                            alert_id=alert.alert_id,
                            idempotency_key=alert.idempotency_key,
                            unit_serial=alert.unit_serial,
                            actor=actor,
                            notes=notes,
                        )
                        st.success("Đã ghi nhận việc tiếp nhận cảnh báo.")
                        st.rerun()
                    except Exception:
                        st.error(
                            "Không thể ghi nhận phản hồi lúc này. Vui lòng thử lại."
                        )

            with dismiss_col:
                if st.button(
                    "Bác bỏ",
                    key=f"wsc_alert_dismiss_{alert.alert_id}",
                    use_container_width=True,
                ):
                    try:
                        dismiss_alert(
                            Path(db_path),
                            alert_id=alert.alert_id,
                            idempotency_key=alert.idempotency_key,
                            unit_serial=alert.unit_serial,
                            actor=actor,
                            notes=notes,
                        )
                        st.success("Đã ghi nhận việc bác bỏ cảnh báo.")
                        st.rerun()
                    except ValueError as error:
                        st.warning(str(error))
                    except Exception:
                        st.error(
                            "Không thể ghi nhận phản hồi lúc này. Vui lòng thử lại."
                        )

            with snooze_col:
                if st.button(
                    "Tạm ẩn 60p",
                    key=f"wsc_alert_snooze_{alert.alert_id}",
                    use_container_width=True,
                ):
                    try:
                        snooze_alert(
                            Path(db_path),
                            alert_id=alert.alert_id,
                            idempotency_key=alert.idempotency_key,
                            unit_serial=alert.unit_serial,
                            actor=actor,
                            duration_minutes=60,
                            notes=notes,
                        )
                        st.success("Đã tạm ẩn cảnh báo trong 60 phút.")
                        st.rerun()
                    except Exception:
                        st.error(
                            "Không thể tạm ẩn cảnh báo lúc này. Vui lòng thử lại."
                        )

            with open_case_col:
                open_disabled = not bool(alert.case_id)
                if st.button(
                    "Mở hồ sơ",
                    key=f"wsc_alert_case_{alert.alert_id}",
                    disabled=open_disabled,
                    use_container_width=True,
                ):
                    if alert.case_id:
                        on_open_case(alert.case_id)
