"""Regression fixture: the 372 opaque/low-confidence filenames from the
production dry-run (2026-10-03).

Guards the Phase A2 keyword taxonomy: names whose domain is obvious from the
filename must keep classifying into the right block with usable confidence.
Names with genuinely no signal (wsc-*.txt, tổng hợp, ...) are expected to stay
at confidence 0 -- they are handled by the content / centroid path, not by
name rules.
"""

from pathlib import Path

from aios_habit.index_domain import (
    CONFIDENCE_LOW_THRESHOLD,
    DOMAIN_DIEU_TRA_LOI,
    DOMAIN_LSU,
    classify_document,
)

NAMES_FILE = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "phieu-viec"
    / "ket-qua"
    / "index-split-lowconf-453-names.txt"
)


def _expected_domain(name: str):
    low = name.lower()
    if low.startswith("ktd-"):
        return DOMAIN_DIEU_TRA_LOI
    if "tape" in low:
        return DOMAIN_LSU
    if "回路図" in name:
        return DOMAIN_DIEU_TRA_LOI
    if "治具" in name:
        return DOMAIN_LSU
    if "drbfm" in low:
        return DOMAIN_DIEU_TRA_LOI
    if "自己診断" in name:
        return DOMAIN_DIEU_TRA_LOI
    if "mirror" in low:
        return DOMAIN_LSU
    return None


def _names():
    return [
        line.strip()
        for line in NAMES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_fixture_file_present():
    names = _names()
    assert len(names) >= 300, "fixture shrank unexpectedly"


def test_obvious_names_classify_correctly():
    names = _names()
    labeled = [(n, d) for n in names if (d := _expected_domain(n)) is not None]
    assert len(labeled) >= 150
    wrong = []
    for name, expected in labeled:
        result = classify_document(name, "", "")
        if not (result.domain == expected and result.confidence >= CONFIDENCE_LOW_THRESHOLD):
            wrong.append((name, result.domain, result.confidence))
    assert not wrong, "misclassified obvious names: %s" % wrong[:10]
    assert len(wrong) == 0


def test_overall_name_coverage():
    # At least 70% of the formerly-zero-confidence names now get a usable
    # name-based signal; the rest go through content / centroid.
    names = _names()
    hits = sum(
        1 for n in names if classify_document(n, "", "").confidence >= CONFIDENCE_LOW_THRESHOLD
    )
    assert hits / len(names) >= 0.70
