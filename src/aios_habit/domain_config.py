"""Domain-specific declarative configuration for factory entities and lane definitions.

This module isolates plant-specific, manufacturing-specific, and machine-line specific
declarations from the core RAG library (rag_v2), fulfilling ticket DESKTOP-QD-S1-HARDCODE-CLEANUP-HOME
(addressing QD-02, QD-11 and structured lane exception).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

# =============================================================================
# QD-02 EXCEPTION: STRUCTURED LANE DOCUMENT IDS (NGOẠI LỆ ĐÃ QUYẾT TỪ TRƯỚC)
# =============================================================================
# Căn cứ quyết định dự án: DESKTOP-SPEED-LSU-COVERAGE-EXEMPTION-FIX-HOME & CSV-STRUCTURED-LANE-HOME
# Quyết định điều phối & người dùng: 4 tệp CSV dạng wsc-* của làn có cấu trúc (structured query lane)
# được miễn trừ tính toán dense semantic embeddings, vận hành trên bộ máy phân tích bảng SQL riêng biệt.
# Hành vi giữ nguyên 100%.
STRUCTURED_LANE_DOCUMENT_IDS: frozenset[str] = frozenset({
    "wsc-8eb2a5d21b75fa88307223b1",  # 2026_08_Error_BowOverAdjust.csv
    "wsc-03bf475fc208c02f741d4013",  # 2026_08_Error.csv
    "wsc-4bd2e353e19864fe786358c5",  # 2026_08_UnitTest.csv
    "wsc-d4df39c14101e40ebad88a91",  # 2026_08_Spec.csv
})


def get_structured_lane_document_ids() -> frozenset[str]:
    """Return the set of document IDs exempt from dense semantic embeddings."""
    return STRUCTURED_LANE_DOCUMENT_IDS


# =============================================================================
# QD-11: 16 FACTORY BUSINESS ENTITY KEYWORDS & COMPILED PATTERNS
# =============================================================================
# 16 factory entity keywords and mechanical patterns previously hardcoded into rag_v2/index.py:
# (1) Sirius, (2) Sirius 2, (3) OKNGUNIT, (4) Camera 140 / Camera, (5) MOUNT LD BLOCK / MOUNT BLOCK,
# (6) NanoScan, (7) Bow_Skew, (8) SIM tape / SIM, (9) LSU Line / LSU, (10) COVER GLASS,
# (11) g1, (12) g2, (13) OHP, (14) 1035, (15) 1004, (16) JIG/LINE JIG Cxx.
FACTORY_ENTITY_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"(?<![A-Za-z0-9])(?:JIG\s*|LINE\s*)?C\d{2,3}(?:[/\-–]\d{2,3}|[/\-–]C\d{2,3})", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]\s*距離", re.IGNORECASE),
    re.compile(r"\b(?:Sirius(?:\s*2)?|OKNGUNIT|Camera(?:\s*140)?|MOUNT(?:\s*LD)?\s*BLOCK|NanoScan|Bow_Skew)\b", re.IGNORECASE),
    re.compile(r"\b(?:SIM(?:\s*tape)?|LSU(?:\s*Line)?|COVER\s*GLASS)\b", re.IGNORECASE),
    re.compile(r"\b(?:g1|g2|OHP)\b", re.IGNORECASE),
    re.compile(r"\b(?:1035|1004)\b"),
)


def get_factory_entity_patterns() -> Tuple[re.Pattern, ...]:
    """Return compiled regex patterns for domain factory entities."""
    return FACTORY_ENTITY_PATTERNS


# =============================================================================
# QD-11: MAINTENANCE CONTEXT KEYWORDS & COMPILED PATTERN
# =============================================================================
# Factory maintenance context keywords (khuôn, housing, 金型, màu):
MAINTENANCE_CONTEXT_PATTERN: re.Pattern = re.compile(
    r"(?:bảo\s*dưỡng|bao\s*duong|khuôn|khuon|maintenance|金型|housing|màu|mau)",
    re.IGNORECASE,
)


def get_maintenance_context_pattern() -> re.Pattern:
    """Return regex pattern matching maintenance context in factory questions."""
    return MAINTENANCE_CONTEXT_PATTERN


# =============================================================================
# QD-02: MACHINE SERIES KEYWORD & TYPO PATTERNS
# =============================================================================
# Decouples factory machine line matching (Sirius typo 'siriud', Iris camera file 'y_beamh')
# from the core pipeline logic in rag_v2/pipeline.py.
MACHINE_SERIES_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "sirius": ("sirius", "siriud"),
    "iris": ("iris", "y_beamh"),
}


def get_machine_series_patterns() -> Dict[str, Tuple[str, ...]]:
    """Return keyword/substring mappings for machine series classification."""
    return MACHINE_SERIES_PATTERNS
