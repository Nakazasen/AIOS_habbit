"""Historical replay evaluation engine for LSU Iris prediction baselines.

Implements fixed, versioned baseline protocols:
1. No-alert baseline (calculates pure baseline loss, all NGs count as missed)
2. EWMA statistical baseline (exponentially weighted moving average with fixed control limits)
3. Guarded supervised model branch (returns not_applicable when data requirements are unmet)

Adheres strictly to specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md and
specs/008-evidence-case-loop/plan.md section 5.1.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from aios_habit.production_prediction.models import (
    ComponentLotMeasurement,
    JoinedUnitTrace,
    LsuDatasetSnapshot,
)


@dataclass(frozen=True)
class ReplayProtocol:
    rubric_version: str = "lsu_iris_replay_v1"
    ewma_alpha: float = 0.2
    baseline_window: int = 50
    baseline_minimum_points: int = 20
    control_limit_std: float = 3.0
    prediction_horizon: str = "next_final_outcome"
    risk_direction: str = "two_sided"
    maximum_ewma_metrics: int = 20
    random_seed: int = 42

    def compute_digest(self) -> str:
        s = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    @classmethod
    def default_lsu_iris(
        cls,
        baseline_minimum_points: Optional[int] = None,
        control_limit_std: Optional[float] = None,
    ) -> ReplayProtocol:
        kwargs: Dict[str, Any] = {}
        if baseline_minimum_points is not None:
            kwargs["baseline_minimum_points"] = baseline_minimum_points
        if control_limit_std is not None:
            kwargs["control_limit_std"] = control_limit_std
        return cls(**kwargs)


@dataclass
class ReplayMetrics:
    method_name: str
    status: str = "evaluated"  # "evaluated" or "not_applicable"
    reason: str = ""
    evaluated_units_count: int = 0
    alerted_units_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    maximum_alerts_per_unit: int = 0
    median_lead_time_seconds: float = 0.0
    recall_ng_percent: float = 0.0
    false_alert_rate_per_100: float = 0.0
    protocol_digest: str = ""
    digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayReport:
    protocol_version: str
    protocol_digest: str
    snapshot_id: str
    snapshot_digest: str
    created_at: str
    future_leakage_detected: bool
    metrics_by_method: Dict[str, ReplayMetrics] = field(default_factory=dict)
    unit_alerts: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "protocol_digest": self.protocol_digest,
            "snapshot_id": self.snapshot_id,
            "snapshot_digest": self.snapshot_digest,
            "created_at": self.created_at,
            "future_leakage_detected": self.future_leakage_detected,
            "metrics_by_method": {k: v.to_dict() for k, v in self.metrics_by_method.items()},
            "unit_alerts": self.unit_alerts,
        }


def evaluate_replay_baseline(
    snapshot: LsuDatasetSnapshot,
    traces: Dict[str, JoinedUnitTrace],
    protocol: ReplayProtocol,
) -> ReplayMetrics:
    """Evaluate standard no-alert baseline. All NG units are classified as missed (false negatives)."""
    evaluated_units = list(traces.values())
    ng_count = sum(1 for t in evaluated_units if t.target_label == "NG")
    ok_count = sum(1 for t in evaluated_units if t.target_label == "OK")
    proto_digest = protocol.compute_digest()

    m = ReplayMetrics(
        method_name="no_alert",
        status="evaluated",
        reason="Phương án nền chuẩn: Không phát cảnh báo",
        evaluated_units_count=len(evaluated_units),
        alerted_units_count=0,
        true_positives=0,
        false_positives=0,
        false_negatives=ng_count,
        true_negatives=ok_count,
        maximum_alerts_per_unit=0,
        median_lead_time_seconds=0.0,
        recall_ng_percent=0.0,
        false_alert_rate_per_100=0.0,
        protocol_digest=proto_digest,
    )
    s = json.dumps(m.to_dict(), sort_keys=True)
    m.digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return m


def evaluate_ewma_baseline(
    snapshot: LsuDatasetSnapshot,
    traces: Dict[str, JoinedUnitTrace],
    protocol: ReplayProtocol,
    return_report: bool = False,
) -> Union[ReplayMetrics, ReplayReport]:
    """Evaluate EWMA statistical baseline adhering to temporal anti-leakage invariants."""
    proto_digest = protocol.compute_digest()
    # Check baseline minimum points requirement across valid measurements
    measurements = [m for m in snapshot.component_measurements if m.value is not None and m.event_time is not None]
    if len(measurements) < protocol.baseline_minimum_points:
        m = ReplayMetrics(
            method_name="ewma",
            status="not_applicable",
            reason=(
                f"Chưa đủ dữ liệu nền để áp dụng EWMA an toàn. "
                f"Hiện có {len(measurements)} điểm đo, yêu cầu tối thiểu {protocol.baseline_minimum_points} điểm."
            ),
            evaluated_units_count=len(traces),
            protocol_digest=proto_digest,
        )
        s = json.dumps(m.to_dict(), sort_keys=True)
        m.digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
        if return_report:
            return ReplayReport(
                protocol_version=protocol.rubric_version,
                protocol_digest=proto_digest,
                snapshot_id=snapshot.snapshot_id,
                snapshot_digest=snapshot.content_digest,
                created_at=datetime.now(timezone.utc).isoformat(),
                future_leakage_detected=False,
                metrics_by_method={"ewma": m},
            )
        return m

    # Group measurements by metric_name and sort by event_time
    by_metric: Dict[str, List[ComponentLotMeasurement]] = {}
    for meas in measurements:
        by_metric.setdefault(meas.metric_name, []).append(meas)

    for k in by_metric:
        by_metric[k].sort(key=lambda m: m.event_time)

    # Filter and rank metrics if exceeding maximum_ewma_metrics (specs/008-evidence-case-loop/contracts/lsu-iris-input.md dòng 72)
    if len(by_metric) > protocol.maximum_ewma_metrics:
        def _metric_sort_key(item: Tuple[str, List[ComponentLotMeasurement]]) -> Tuple[float, str]:
            m_name, m_items = item
            valid_pts = sum(1 for x in m_items if x.value is not None and not math.isnan(x.value))
            ratio = valid_pts / len(m_items) if m_items else 0.0
            return (-ratio, m_name)

        sorted_metrics = sorted(by_metric.items(), key=_metric_sort_key)
        by_metric = dict(sorted_metrics[: protocol.maximum_ewma_metrics])

    # For each metric, compute baseline mean and std, then run EWMA recursion
    measurement_z_scores: Dict[str, float] = {}  # lot_measurement_id -> z-score
    baseline_established_times: Dict[str, datetime] = {}  # metric_name -> earliest timestamp when baseline was established
    future_leakage_detected = False
    alpha = protocol.ewma_alpha
    k_min = protocol.baseline_minimum_points
    w_size = protocol.baseline_window

    for metric_name, m_list in by_metric.items():
        # Invariant: Fixed causal baseline calibration window anchored at baseline_minimum_points.
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

                    if protocol.risk_direction == "upper":
                        dev_ewma = (z_current - mu_0) / sigma_zt
                        dev_inst = (y_t - mu_0) / sigma_0
                    elif protocol.risk_direction == "lower":
                        dev_ewma = (mu_0 - z_current) / sigma_zt
                        dev_inst = (mu_0 - y_t) / sigma_0
                    else:  # "two_sided"
                        dev_ewma = abs(z_current - mu_0) / sigma_zt
                        dev_inst = abs(y_t - mu_0) / sigma_0

                    z_ewma = max(0.0, dev_ewma)
                    z_inst = max(0.0, dev_inst)
                    z_score = round(max(z_ewma, z_inst), 6)

            # Store point-in-time score per measurement (both by ID and tuple key for resilience)
            if m.lot_measurement_id:
                measurement_z_scores[m.lot_measurement_id] = z_score
            fallback_k = f"{m.component_lot_id}:{m.metric_name}:{m.event_time.isoformat() if m.event_time else ''}"
            measurement_z_scores[fallback_k] = z_score

    # If no metric had sufficient points to establish a baseline, safely return not_applicable
    if not baseline_established_times:
        m = ReplayMetrics(
            method_name="ewma",
            status="not_applicable",
            reason=(
                f"Chưa đủ dữ liệu nền để áp dụng EWMA an toàn. "
                f"Không có thông số nào đạt tối thiểu {protocol.baseline_minimum_points} điểm đo."
            ),
            evaluated_units_count=len(traces),
            protocol_digest=proto_digest,
        )
        s = json.dumps(m.to_dict(), sort_keys=True)
        m.digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
        if return_report:
            return ReplayReport(
                protocol_version=protocol.rubric_version,
                protocol_digest=proto_digest,
                snapshot_id=snapshot.snapshot_id,
                snapshot_digest=snapshot.content_digest,
                created_at=datetime.now(timezone.utc).isoformat(),
                future_leakage_detected=False,
                metrics_by_method={"ewma": m},
            )
        return m

    # Evaluate against unit traces
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    alerted_units = 0
    max_alerts_per_unit = 0
    lead_times: List[float] = []
    unit_alerts_dict: Dict[str, Dict[str, Any]] = {}

    for u_serial, trace in traces.items():
        # Check future leakage: measurement event_time > as_of_time
        as_of = trace.assembly_time
        if as_of is None and trace.lot_measurements:
            valid_times = [m.event_time for m in trace.lot_measurements if m.event_time is not None]
            if valid_times:
                as_of = min(valid_times)

        # Detect any abnormal factors for lots used in this unit strictly <= as_of
        factors: List[Tuple[str, str, float]] = []
        for m in trace.lot_measurements:
            if as_of and m.event_time and m.event_time > as_of:
                future_leakage_detected = True
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

            if z >= protocol.control_limit_std:
                factors.append((m.component_lot_id, m.metric_name, z))

        # Also check if jig event time is anomalously earlier than assembly time
        if trace.jig_event_time and as_of and trace.jig_event_time < as_of:
            future_leakage_detected = True

        # Sort factors by z-score descending and keep at most 3
        factors.sort(key=lambda x: x[2], reverse=True)
        top_factors = factors[:3]

        has_alert = len(top_factors) > 0
        alerts_for_this_unit = 1 if has_alert else 0
        if alerts_for_this_unit > max_alerts_per_unit:
            max_alerts_per_unit = alerts_for_this_unit

        if has_alert:
            alerted_units += 1
            lt = 0.0
            if trace.jig_event_time and as_of:
                lt = max(0.0, (trace.jig_event_time - as_of).total_seconds())
            lead_times.append(lt)

            unit_alerts_dict[u_serial] = {
                "unit_serial": u_serial,
                "as_of_time": as_of.isoformat() if as_of else None,
                "top_factors": [
                    {"component_lot_id": f[0], "metric_name": f[1], "z_score": round(f[2], 2)}
                    for f in top_factors
                ],
                "lead_time_seconds": lt,
            }

            if trace.target_label == "NG":
                true_positives += 1
            else:
                false_positives += 1
        else:
            if trace.target_label == "NG":
                false_negatives += 1
            else:
                true_negatives += 1

    total_eval = len(traces)
    total_ng = true_positives + false_negatives
    recall = (true_positives / total_ng * 100.0) if total_ng > 0 else 0.0
    false_alert_rate = (false_positives / total_eval * 100.0) if total_eval > 0 else 0.0
    median_lt = statistics.median(lead_times) if lead_times else 0.0

    m = ReplayMetrics(
        method_name="ewma",
        status="evaluated",
        reason="Phương án EWMA với ngưỡng dung sai kiểm soát chuẩn hóa",
        evaluated_units_count=total_eval,
        alerted_units_count=alerted_units,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        maximum_alerts_per_unit=max_alerts_per_unit,
        median_lead_time_seconds=round(median_lt, 2),
        recall_ng_percent=round(recall, 2),
        false_alert_rate_per_100=round(false_alert_rate, 2),
        protocol_digest=proto_digest,
    )
    s = json.dumps(m.to_dict(), sort_keys=True)
    m.digest = hashlib.sha256(s.encode("utf-8")).hexdigest()

    if return_report:
        return ReplayReport(
            protocol_version=protocol.rubric_version,
            protocol_digest=proto_digest,
            snapshot_id=snapshot.snapshot_id,
            snapshot_digest=snapshot.content_digest,
            created_at=datetime.now(timezone.utc).isoformat(),
            future_leakage_detected=future_leakage_detected,
            metrics_by_method={"ewma": m},
            unit_alerts=unit_alerts_dict,
        )
    return m


def evaluate_supervised_model(
    snapshot: LsuDatasetSnapshot,
    traces: Dict[str, JoinedUnitTrace],
    protocol: ReplayProtocol,
) -> ReplayMetrics:
    """Supervised model branch guarded by sample size rubric invariants."""
    total_units = len(traces)
    ng_count = sum(1 for t in traces.values() if t.target_label == "NG")
    proto_digest = protocol.compute_digest()

    # Strict rubric requirements: min 200 units, min 30 NG
    if total_units < 200 or ng_count < 30:
        m = ReplayMetrics(
            method_name="logistic_regression",
            status="not_applicable",
            reason=(
                f"Chưa đủ cỡ mẫu tối thiểu theo rubric để kích hoạt mô hình học máy "
                f"(hiện có {total_units}/200 Unit, {ng_count}/30 NG). Nhánh model trả not_applicable."
            ),
            evaluated_units_count=total_units,
            protocol_digest=proto_digest,
        )
        s = json.dumps(m.to_dict(), sort_keys=True)
        m.digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
        return m

    # Stub for future optional model branch when real dataset satisfies criteria
    m = ReplayMetrics(
        method_name="logistic_regression",
        status="not_applicable",
        reason="Mô hình tùy chọn chưa kích hoạt.",
        evaluated_units_count=total_units,
        protocol_digest=proto_digest,
    )
    s = json.dumps(m.to_dict(), sort_keys=True)
    m.digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return m