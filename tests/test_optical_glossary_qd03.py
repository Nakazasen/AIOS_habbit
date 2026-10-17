"""Tests for QD-03: External Optical LSU Equivalences Glossary (Ticket DESKTOP-QD-S2-GLOSSARY-WORKER-LIFECYCLE-HOME)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from aios_habit.rag_v2.query_planning import (
    _load_optical_lsu_glossary,
    _resolve_glossary_lsu_path,
    build_query_plan,
    get_optical_lsu_ja_to_vi_equivalences,
    get_optical_lsu_vi_to_ja_equivalences,
)


def test_glossary_json_file_exists_and_valid() -> None:
    glossary_path = _resolve_glossary_lsu_path()
    assert glossary_path is not None, "config/glossary_lsu.json should be discoverable"
    assert glossary_path.is_file(), f"{glossary_path} must be an existing file"

    with open(glossary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "ja_to_vi" in data
    assert "vi_to_ja" in data
    assert len(data["ja_to_vi"]) == 16
    assert len(data["vi_to_ja"]) == 12


def test_optical_glossary_loads_28_rules_dynamically() -> None:
    ja_to_vi = get_optical_lsu_ja_to_vi_equivalences()
    vi_to_ja = get_optical_lsu_vi_to_ja_equivalences()

    assert len(ja_to_vi) == 16, f"Expected 16 JA->VI rules, got {len(ja_to_vi)}"
    assert len(vi_to_ja) == 12, f"Expected 12 VI->JA rules, got {len(vi_to_ja)}"


def test_optical_variant_generation_q0707_sim_tape() -> None:
    query = "SIM tape được dán ở đâu, dày bao nhiêu và trình tự thao tác thế nào?"
    plan = build_query_plan(query)
    variant_texts = [v.text for v in plan.variants]
    # Expect optics crosslingual variant containing Japanese equivalents
    assert any("SIM 貼付" in vt or "補正順番" in vt or "手順" in vt for vt in variant_texts)


def test_optical_variant_generation_q0693_correlation() -> None:
    query = "NanoScan比较后，需要重新Correlation的是哪台Jig？"
    plan = build_query_plan(query)
    variant_texts = [v.text for v in plan.variants]
    # Expect optics crosslingual variant containing Vietnamese equivalents
    assert any("tương quan" in vt for vt in variant_texts)


def test_optical_glossary_fallback_on_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    non_existent = tmp_path / "missing_glossary.json"
    monkeypatch.setenv("AIOS_GLOSSARY_LSU_PATH", str(non_existent))

    ja_to_vi, vi_to_ja = _load_optical_lsu_glossary()
    assert len(ja_to_vi) == 16
    assert len(vi_to_ja) == 12
