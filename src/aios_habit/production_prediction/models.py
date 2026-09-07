"""Domain models for LSU Iris production prediction data gate and trace joining."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DataGateStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNING = "PASS_WITH_WARNING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    BLOCKED_DATA = "BLOCKED_DATA"
    FAIL_TECHNICAL = "FAIL_TECHNICAL"


@dataclass
class ComponentLotMeasurement:
    lot_measurement_id: str
    component_lot_id: str
    component_code: str
    metric_name: str
    value: Optional[float] = None
    unit: str = ""
    event_time: Optional[datetime] = None
    ingested_at: Optional[datetime] = None
    source_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_time"] = self.event_time.isoformat() if self.event_time else None
        d["ingested_at"] = self.ingested_at.isoformat() if self.ingested_at else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComponentLotMeasurement:
        d = dict(data)
        if isinstance(d.get("event_time"), str):
            d["event_time"] = datetime.fromisoformat(d["event_time"])
        if isinstance(d.get("ingested_at"), str):
            d["ingested_at"] = datetime.fromisoformat(d["ingested_at"])
        return cls(**d)


@dataclass
class UnitLotLink:
    link_id: str
    unit_serial: str
    component_lot_id: str
    component_code: str
    assembly_time: Optional[datetime] = None
    line_id: Optional[str] = None
    station_id: Optional[str] = None
    ingested_at: Optional[datetime] = None
    source_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["assembly_time"] = self.assembly_time.isoformat() if self.assembly_time else None
        d["ingested_at"] = self.ingested_at.isoformat() if self.ingested_at else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UnitLotLink:
        d = dict(data)
        if isinstance(d.get("assembly_time"), str):
            d["assembly_time"] = datetime.fromisoformat(d["assembly_time"])
        if isinstance(d.get("ingested_at"), str):
            d["ingested_at"] = datetime.fromisoformat(d["ingested_at"])
        return cls(**d)


@dataclass
class JigOutcomeResult:
    jig_result_id: str
    unit_serial: str
    jig_id: str
    run_id: str
    event_time: Optional[datetime] = None
    metric_name: str = ""
    value: Optional[float] = None
    unit: Optional[str] = None
    jig_version: str = ""
    process_version: str = ""
    target_label: str = "UNKNOWN"
    failure_code: Optional[str] = None
    retest_outcome: Optional[str] = None
    ingested_at: Optional[datetime] = None
    source_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_time"] = self.event_time.isoformat() if self.event_time else None
        d["ingested_at"] = self.ingested_at.isoformat() if self.ingested_at else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JigOutcomeResult:
        d = dict(data)
        if isinstance(d.get("event_time"), str):
            d["event_time"] = datetime.fromisoformat(d["event_time"])
        if isinstance(d.get("ingested_at"), str):
            d["ingested_at"] = datetime.fromisoformat(d["ingested_at"])
        return cls(**d)


@dataclass
class JoinedUnitTrace:
    unit_serial: str
    assembly_time: Optional[datetime] = None
    jig_event_time: Optional[datetime] = None
    target_label: str = "UNKNOWN"
    failure_code: Optional[str] = None
    lot_measurements: List[ComponentLotMeasurement] = field(default_factory=list)
    jig_measurements: List[JigOutcomeResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_serial": self.unit_serial,
            "assembly_time": self.assembly_time.isoformat() if self.assembly_time else None,
            "jig_event_time": self.jig_event_time.isoformat() if self.jig_event_time else None,
            "target_label": self.target_label,
            "failure_code": self.failure_code,
            "lot_measurements": [m.to_dict() for m in self.lot_measurements],
            "jig_measurements": [j.to_dict() for j in self.jig_measurements],
        }


@dataclass
class LsuDatasetSnapshot:
    snapshot_id: str
    created_at: datetime
    source_files: Dict[str, str] = field(default_factory=dict)
    component_measurements: List[ComponentLotMeasurement] = field(default_factory=list)
    unit_links: List[UnitLotLink] = field(default_factory=list)
    jig_outcomes: List[JigOutcomeResult] = field(default_factory=list)
    content_digest: str = ""
    parse_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at.isoformat(),
            "source_files": self.source_files,
            "component_measurements": [m.to_dict() for m in self.component_measurements],
            "unit_links": [u.to_dict() for u in self.unit_links],
            "jig_outcomes": [j.to_dict() for j in self.jig_outcomes],
            "content_digest": self.content_digest,
            "parse_errors": self.parse_errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LsuDatasetSnapshot:
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at=created_at,
            source_files=dict(data.get("source_files", {})),
            component_measurements=[
                ComponentLotMeasurement.from_dict(m) for m in data.get("component_measurements", [])
            ],
            unit_links=[UnitLotLink.from_dict(u) for u in data.get("unit_links", [])],
            jig_outcomes=[JigOutcomeResult.from_dict(j) for j in data.get("jig_outcomes", [])],
            content_digest=data.get("content_digest", ""),
            parse_errors=list(data.get("parse_errors", [])),
        )


@dataclass
class DataGateReport:
    status: DataGateStatus
    rubric_version: str
    source_digest: str
    total_rows: int
    join_coverage_percent: float
    conflicting_primary_keys_count: int
    future_leak_count: int
    time_parse_valid_percent: float
    unit_recognition_percent: float
    ok_count: int
    ng_count: int
    unknown_count: int
    action_items: List[str] = field(default_factory=list)
    guidance: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "rubric_version": self.rubric_version,
            "source_digest": self.source_digest,
            "total_rows": self.total_rows,
            "join_coverage_percent": self.join_coverage_percent,
            "conflicting_primary_keys_count": self.conflicting_primary_keys_count,
            "future_leak_count": self.future_leak_count,
            "time_parse_valid_percent": self.time_parse_valid_percent,
            "unit_recognition_percent": self.unit_recognition_percent,
            "ok_count": self.ok_count,
            "ng_count": self.ng_count,
            "unknown_count": self.unknown_count,
            "action_items": self.action_items,
            "guidance": self.guidance,
            "created_at": self.created_at.isoformat(),
        }