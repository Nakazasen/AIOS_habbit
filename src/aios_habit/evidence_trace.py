# -*- coding: utf-8 -*-
"""Evidence Trace Module.

Re-exports core classes, dataclasses, and contracts from evidence_trace_schema
for standard and convenient imports across AIOS WorkLens.
"""
from __future__ import annotations

from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_1_0_0,
    SCHEMA_VERSION_V1,
    SUPPORTED_SCHEMA_VERSIONS,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)

__all__ = [
    "EvidenceNode",
    "EvidenceEdge",
    "EvidenceTrace",
    "EvidenceTraceContract",
    "SCHEMA_VERSION_1_0_0",
    "SCHEMA_VERSION_V1",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ALLOWED_NODE_TYPES",
    "ALLOWED_EDGE_TYPES",
]
