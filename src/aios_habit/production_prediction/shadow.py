"""Manual shadow experiment runner and resilient case linkage for LSU Iris.

Adheres strictly to specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md and
specs/008-evidence-case-loop/plan.md section 5.1 & Milestone 4.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aios_habit.production_prediction.evaluation import ReplayProtocol
from aios_habit.production_prediction.models import (
    ComponentLotMeasurement,
    JoinedUnitTrace,
    LsuDatasetSnapshot,
)
from aios_habit.production_prediction.repository import ProductionPredictionRepository
from aios_habit.workspace_case_models import CaseRecord
from aios_habit.workspace_case_service import WorkspaceCaseService


@dataclass
class ShadowRunProgress:
    total_units: int
    processed_units: int
    alerted_units: int
    current_unit: str = ""
    status: str = "running"  # "running", "completed", "stopped", "failed"


@dataclass
class ShadowRiskAssessment:
    idempotency_key: str
    snapshot_id: str
    unit_serial: str
    as_of_time: str
    risk_level: str
    factors: List[Dict[str, Any]]
    reason: str
    link_status: str = "pending_case_link"  # "pending_case_link", "linked", "retryable_error", "failed"
    case_id: Optional[str] = None
    future_leakage_detected: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def save_shadow_risk_assessment(
    repository: ProductionPredictionRepository,
    assessment: ShadowRiskAssessment,
) -> None:
    """Persist shadow risk assessment record into SQLite database."""
    with repository._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO shadow_risk_assessments (
                idempotency_key, snapshot_id, unit_serial, as_of_time,
                risk_level, factors_json, reason, link_status, case_id,
                future_leakage_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO UPDATE SET
                link_status = excluded.link_status,
                case_id = excluded.case_id
            """,
            (
                assessment.idempotency_key,
                assessment.snapshot_id,
                assessment.unit_serial,
                assessment.as_of_time,
                assessment.risk_level,
                json.dumps(assessment.factors),
                assessment.reason,
                assessment.link_status,
                assessment.case_id,
                1 if assessment.future_leakage_detected else 0,
                assessment.created_at,
            ),
        )


def load_shadow_risk_assessments(
    repository: ProductionPredictionRepository,
    snapshot_id: Optional[str] = None,
) -> List[ShadowRiskAssessment]:
    """Load persisted shadow risk assessments from SQLite database."""
    with repository._get_connection() as conn:
        if snapshot_id:
            cursor = conn.execute(
                """
                SELECT idempotency_key, snapshot_id, unit_serial, as_of_time,
                       risk_level, factors_json, reason, link_status, case_id,
                       future_leakage_detected, created_at
                FROM shadow_risk_assessments WHERE snapshot_id = ? ORDER BY rowid ASC
                """,
                (snapshot_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT idempotency_key, snapshot_id, unit_serial, as_of_time,
                       risk_level, factors_json, reason, link_status, case_id,
                       future_leakage_detected, created_at
                FROM shadow_risk_assessments ORDER BY rowid ASC
                """
            )

        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append(
                ShadowRiskAssessment(
                    idempotency_key=r[0],
                    snapshot_id=r[1],
                    unit_serial=r[2],
                    as_of_time=r[3],
                    risk_level=r[4],
                    factors=json.loads(r[5]),
                    reason=r[6],
                    link_status=r[7],
                    case_id=r[8],
                    future_leakage_detected=bool(r[9]),
                    created_at=r[10],
                )
            )
        return result


@dataclass
class ShadowOutcomeRecord:
    outcome_id: str
    unit_serial: str
    target_label: str  # "OK", "NG", "UNKNOWN"
    failure_code: Optional[str]
    confirmed_by: str
    rationale: str
    is_missed_alert: bool = False
    assessment_idempotency_key: Optional[str] = None
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShadowRunResult:
    status: str  # "completed", "stopped", "failed"
    total_units: int
    processed_units: int
    alerted_units: int
    risk_assessments: List[ShadowRiskAssessment] = field(default_factory=list)
    future_leakage_detected: bool = False


class ManualShadowRunner:
    """Manual batch runner for shopfloor shadow analysis adhering to laptop CPU limits."""

    def __init__(self, protocol: ReplayProtocol, batch_size: int = 10) -> None:
        self.protocol = protocol
        self.batch_size = max(1, batch_size)

    def run(
        self,
        snapshot: LsuDatasetSnapshot,
        traces: Dict[str, JoinedUnitTrace],
        on_progress: Optional[Callable[[ShadowRunProgress], None]] = None,
        stop_after_units: Optional[int] = None,
        repository: Optional[ProductionPredictionRepository] = None,
    ) -> ShadowRunResult:
        all_units = sorted(traces.keys())
        total_units = len(all_units)
        measurements = [m for m in snapshot.component_measurements if m.value is not None and m.event_time is not None]

        # Group measurements by metric
        by_metric: Dict[str, List[ComponentLotMeasurement]] = {}
        for m in measurements:
            by_metric.setdefault(m.metric_name, []).append(m)

        for k in by_metric:
            by_metric[k].sort(key=lambda x: x.event_time)

        # Filter and rank metrics if exceeding maximum_ewma_metrics (specs/008-evidence-case-loop/contracts/lsu-iris-input.md dòng 72)
        if len(by_metric) > self.protocol.maximum_ewma_metrics:
            def _metric_sort_key(item: Tuple[str, List[ComponentLotMeasurement]]) -> Tuple[float, str]:
                m_name, m_items = item
                valid_pts = sum(1 for x in m_items if x.value is not None and not math.isnan(x.value))
                ratio = valid_pts / len(m_items) if m_items else 0.0
                return (-ratio, m_name)

            sorted_metrics = sorted(by_metric.items(), key=_metric_sort_key)
            by_metric = dict(sorted_metrics[: self.protocol.maximum_ewma_metrics])

        # Compute metric statistics using synchronized EWMA formula with Strict Causality
        measurement_z_scores: Dict[str, float] = {}
        baseline_established_times: Dict[str, datetime] = {}
        alpha = self.protocol.ewma_alpha
        k_min = self.protocol.baseline_minimum_points
        w_size = self.protocol.baseline_window
        for metric_name, m_list in by_metric.items():
            # Strict Causality: NEVER use future points or fewer than baseline_minimum_points to calibrate baseline!
            if len(m_list) < k_min:
                continue

            baseline_established_times[metric_name] = m_list[k_min - 1].event_time

            init_vals = [m.value for m in m_list[:k_min] if m.value is not None and not math.isnan(m.value)]
            if len(init_vals) < k_min:
                continue
            init_mean = statistics.mean(init_vals)

            z_current = init_mean
            for t_idx, m in enumerate(m_list, start=1):
                if m.value is None or math.isnan(m.value):
                    continue
                y_t = m.value
                z_current = alpha * y_t + (1.0 - alpha) * z_current

                # In calibration window (t_idx <= k_min), points serve as initial baseline reference, not alerting
                if t_idx <= k_min:
                    z_score = 0.0
                else:
                    # Point-in-time causal baseline window: up to baseline_window prior points strictly before t_idx
                    prior_pts = [
                        x.value for x in m_list[max(0, t_idx - 1 - w_size) : t_idx - 1]
                        if x.value is not None and not math.isnan(x.value)
                    ]
                    if len(prior_pts) < k_min:
                        z_score = 0.0
                    else:
                        mu_0 = statistics.mean(prior_pts)
                        sigma_0 = statistics.stdev(prior_pts) if len(prior_pts) > 1 else 0.0
                        if sigma_0 <= 0.0:
                            sigma_0 = 1e-6

                        step = len(prior_pts)
                        denom = max(1e-9, 2.0 - alpha)
                        factor = (alpha / denom) * (1.0 - ((1.0 - alpha) ** (2 * step)))
                        sigma_zt = sigma_0 * math.sqrt(max(1e-12, factor))
                        if sigma_zt <= 0.0:
                            sigma_zt = 1e-6

                        if self.protocol.risk_direction == "upper":
                            dev_ewma = (z_current - mu_0) / sigma_zt
                            dev_inst = (y_t - mu_0) / sigma_0
                        elif self.protocol.risk_direction == "lower":
                            dev_ewma = (mu_0 - z_current) / sigma_zt
                            dev_inst = (mu_0 - y_t) / sigma_0
                        else:  # "two_sided"
                            dev_ewma = abs(z_current - mu_0) / sigma_zt
                            dev_inst = abs(y_t - mu_0) / sigma_0

                        z_ewma = max(0.0, dev_ewma)
                        z_inst = max(0.0, dev_inst)
                        z_score = round(max(z_ewma, z_inst), 6)

                if m.lot_measurement_id:
                    measurement_z_scores[m.lot_measurement_id] = z_score
                fallback_k = f"{m.component_lot_id}:{m.metric_name}:{m.event_time.isoformat() if m.event_time else ''}"
                measurement_z_scores[fallback_k] = z_score

        assessments: List[ShadowRiskAssessment] = []
        alerted = 0
        processed = 0
        status = "completed"
        any_leakage = False
        protocol_digest = self.protocol.compute_digest()

        for idx, u_serial in enumerate(all_units, start=1):
            if stop_after_units is not None and processed >= stop_after_units:
                status = "stopped"
                break

            trace = traces[u_serial]
            as_of = trace.assembly_time
            if as_of is None and trace.lot_measurements:
                valid_times = [m.event_time for m in trace.lot_measurements if m.event_time is not None]
                if valid_times:
                    as_of = min(valid_times)
            as_of_str = as_of.isoformat() if as_of else ""

            # Check future leakage
            leakage = False
            factors: List[Tuple[str, str, float]] = []
            for m in trace.lot_measurements:
                if as_of and m.event_time and m.event_time > as_of:
                    leakage = True
                    any_leakage = True
                    # STRICT CAUSALITY: Never use future measurements to alert this unit!
                    continue

                # Strict Causality: Check if baseline was established by as_of time
                est_time = baseline_established_times.get(m.metric_name)
                if est_time is None or (as_of and est_time > as_of):
                    # At as_of time, factory had not yet accumulated sufficient baseline points for this metric
                    # STRICT CAUSALITY: Do not use future baseline calibration parameters!
                    continue

                z = measurement_z_scores.get(m.lot_measurement_id)
                if z is None:
                    fallback_k = f"{m.component_lot_id}:{m.metric_name}:{m.event_time.isoformat() if m.event_time else ''}"
                    z = measurement_z_scores.get(fallback_k, 0.0)

                if z >= self.protocol.control_limit_std:
                    factors.append((m.component_lot_id, m.metric_name, z))

            if trace.jig_event_time and as_of and trace.jig_event_time < as_of:
                leakage = True
                any_leakage = True

            factors.sort(key=lambda x: x[2], reverse=True)
            top_factors = factors[:3]

            if top_factors:
                alerted += 1
                # Deterministic idempotency key from immutable attributes
                key_raw = f"{snapshot.content_digest}:{protocol_digest}:{u_serial}:{as_of_str}"
                idemp_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

                factors_payload = [
                    {"component_lot_id": f[0], "metric_name": f[1], "z_score": round(f[2], 2)}
                    for f in top_factors
                ]
                reason = (
                    f"Phát hiện {len(top_factors)} thông số linh kiện lệch chuẩn "
                    f"vượt ngưỡng dung sai {self.protocol.control_limit_std} std."
                )

                assess_item = ShadowRiskAssessment(
                    idempotency_key=idemp_key,
                    snapshot_id=snapshot.snapshot_id,
                    unit_serial=u_serial,
                    as_of_time=as_of_str,
                    risk_level="HIGH",
                    factors=factors_payload,
                    reason=reason,
                    future_leakage_detected=leakage,
                )
                assessments.append(assess_item)
                if repository is not None:
                    save_shadow_risk_assessment(repository, assess_item)

            processed += 1
            if on_progress is not None and (processed % self.batch_size == 0 or processed == total_units):
                on_progress(
                    ShadowRunProgress(
                        total_units=total_units,
                        processed_units=processed,
                        alerted_units=alerted,
                        current_unit=u_serial,
                        status="running",
                    )
                )

        if on_progress is not None:
            on_progress(
                ShadowRunProgress(
                    total_units=total_units,
                    processed_units=processed,
                    alerted_units=alerted,
                    current_unit="",
                    status=status,
                )
            )

        return ShadowRunResult(
            status=status,
            total_units=total_units,
            processed_units=processed,
            alerted_units=alerted,
            risk_assessments=assessments,
            future_leakage_detected=any_leakage,
        )


def link_shadow_risk_to_workspace_case(
    assessment: ShadowRiskAssessment,
    case_service: WorkspaceCaseService,
    repository: Optional[ProductionPredictionRepository] = None,
) -> CaseRecord:
    """Link a shadow risk assessment to a local Workspace Case idempotently."""
    # Check if a case already exists strictly by immutable idempotency key matching evidence_digest
    existing_cases = case_service.store.list_cases()
    for c in existing_cases:
        if assessment.idempotency_key == c.evidence_digest:
            assessment.case_id = c.case_id
            assessment.link_status = "linked"
            if repository is not None:
                save_shadow_risk_assessment(repository, assessment)
            return c

    # Create new case with clean Vietnamese title and immutable key in evidence_digest
    title = f"Nguy cơ bất thường LSU: {assessment.unit_serial}"
    case_id = f"case_{assessment.idempotency_key[:12]}"
    trace_id = f"trace_{assessment.unit_serial}"
    case_record = CaseRecord(
        case_id=case_id,
        conversation_id=f"conv_{assessment.snapshot_id[:8]}",
        assistant_message_id=f"msg_{assessment.idempotency_key[:16]}",
        trace_id=trace_id,
        evidence_digest=assessment.idempotency_key,
        title=title,
        status="in_progress",
        case_type="investigation",
        priority="high" if assessment.risk_level == "HIGH" else "normal",
        scope="lsu_bowskew",
    )

    from aios_habit.workspace_case_models import CaseEvidenceReference
    ref = CaseEvidenceReference(
        reference_id=f"ref_{assessment.idempotency_key[:12]}",
        case_id=case_id,
        trace_id=trace_id,
        evidence_node_id=f"node_{assessment.idempotency_key[:8]}",
        citation_id=f"cite_{assessment.idempotency_key[:8]}",
        source_locator=f"snapshot://{assessment.snapshot_id}",
        source_title="Đánh giá bóng LSU Iris",
        reference_digest=assessment.idempotency_key,
        privacy_label="local_only",
    )

    try:
        result = case_service.store.create_case_with_evidence(case_record, references=[ref])
        created = case_service.store.load_case(result.case_id)
        assessment.case_id = result.case_id
        assessment.link_status = "linked"
        if repository is not None:
            save_shadow_risk_assessment(repository, assessment)
        return created
    except Exception:
        assessment.link_status = "retryable_error"
        if repository is not None:
            save_shadow_risk_assessment(repository, assessment)
        raise


def record_shadow_outcome(
    repository: ProductionPredictionRepository,
    unit_serial: str,
    target_label: str,
    failure_code: Optional[str],
    confirmed_by: str,
    rationale: str,
    is_missed_alert: bool = False,
    assessment_idempotency_key: Optional[str] = None,
) -> ShadowOutcomeRecord:
    """Record verified ground truth outcome into production prediction store.

    Allows recording missed NG outcomes for units without previous alerts.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    outcome_raw = f"{unit_serial}:{target_label}:{confirmed_by}:{now_iso}"
    outcome_id = f"out_{hashlib.sha256(outcome_raw.encode('utf-8')).hexdigest()[:16]}"

    record = ShadowOutcomeRecord(
        outcome_id=outcome_id,
        unit_serial=unit_serial,
        target_label=target_label.upper(),
        failure_code=failure_code,
        confirmed_by=confirmed_by,
        rationale=rationale,
        is_missed_alert=is_missed_alert,
        assessment_idempotency_key=assessment_idempotency_key,
        recorded_at=now_iso,
    )

    # Persist in repository database
    with repository._get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO shadow_outcomes (
                outcome_id, unit_serial, target_label, failure_code,
                confirmed_by, rationale, is_missed_alert, assessment_idempotency_key, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.outcome_id,
                record.unit_serial,
                record.target_label,
                record.failure_code,
                record.confirmed_by,
                record.rationale,
                1 if record.is_missed_alert else 0,
                record.assessment_idempotency_key,
                record.recorded_at,
            ),
        )

    return record