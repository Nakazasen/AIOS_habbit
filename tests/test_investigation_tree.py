"""Tests for the Step-3 investigation tree generator (4M + Why-Why).

DỮ LIỆU MÔ PHỎNG — SIMULATED DATA ONLY.
Every error code, phenomenon, cause and remedy in this file is invented
for testing (fixtures are prefixed SIMULATED_*). Nothing here is real
factory data and nothing here may be treated as a real investigation
record. Nội dung fixture dựa trên từ vựng domain thật (Iris LSU, JIG
BOWSKEW 4/2 BEAM, phân tích 4M từ file AI_LSU_du_doan_loi.xlsx) để đúng
chất ngành, nhưng mọi bản ghi đều bịa cho kiểm thử.
"""
import sqlite3

import pytest

from aios_habit.error_cases.glossary import init_glossary
from aios_habit.error_cases.investigation_tree import (
    BRANCH_LABELS_VI,
    BRANCHES,
    build_tree,
    build_why_chain,
    export_markdown,
    render_markdown,
)

# ---------------------------------------------------------------------------
# SIMULATED fixtures (invented data, not real records; domain vocabulary
# mirrors the real LSU files: Iris LSU, BOWSKEW jig names, 4M analysis)
# ---------------------------------------------------------------------------

SIMULATED_PHENOMENON = ("JIG BOWSKEW 4 BEAM báo tỷ lệ NG cao bất thường ở "
                        "Iris LSU, nghi linh kiện nhựa lot lệch kích thước")
SIMULATED_CODE = "C0030"
SIMULATED_FAMILY = "C_CALL"
SIMULATED_NAME_VI = "SIMULATED: lỗi JIG điều chỉnh Ranks S tại Iris LSU"
SIMULATED_CAUSE = ("SIMULATED: hiệu suất JIG giảm sút, chưa có cảnh báo tự động "
                   "khi dữ liệu có xu hướng xấu (mô phỏng)")
SIMULATED_REMEDY = ("SIMULATED: hiệu chỉnh lại JIG theo Ranks S + đo lại kích "
                    "thước linh kiện 5 unit/lot (mô phỏng)")


@pytest.fixture()
def sim_conn():
    """In-memory glossary holding one SIMULATED entry."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_glossary(c)
    c.execute(
        """INSERT INTO error_glossary
           (code_family, code, code_sub, name_vi, cause, remedy, source_file)
           VALUES (?, ?, '', ?, ?, ?, 'SIMULATED-test-fixture')""",
        (SIMULATED_FAMILY, SIMULATED_CODE, SIMULATED_NAME_VI,
         SIMULATED_CAUSE, SIMULATED_REMEDY),
    )
    c.commit()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Tree structure
# ---------------------------------------------------------------------------

def test_build_tree_has_all_four_branches():
    tree = build_tree(SIMULATED_PHENOMENON)
    assert tree.branch_order == list(BRANCHES)
    for branch in BRANCHES:
        assert branch in BRANCH_LABELS_VI
        assert len(tree.branches[branch]) >= 4  # generic templates
    assert tree.phenomenon == SIMULATED_PHENOMENON


def test_build_tree_rejects_empty_phenomenon():
    with pytest.raises(ValueError):
        build_tree("   ")


def test_build_tree_with_simulated_glossary_entry(sim_conn):
    tree = build_tree(SIMULATED_PHENOMENON, code=SIMULATED_CODE,
                      code_family=SIMULATED_FAMILY, conn=sim_conn)
    assert tree.code_name == SIMULATED_NAME_VI
    assert tree.code_cause == SIMULATED_CAUSE
    # C_CALL emphasizes Machine first.
    assert tree.branch_order[0] == "Machine"
    assert any(it.priority for it in tree.branches["Machine"])
    # Glossary cause hint seeds the first Why node.
    assert SIMULATED_CAUSE in tree.why_chain[0].hint


def test_unknown_code_falls_back_to_templates(sim_conn):
    tree = build_tree(SIMULATED_PHENOMENON, code="C0000",
                      code_family=SIMULATED_FAMILY, conn=sim_conn)
    assert tree.code_name == ""
    assert tree.branch_order[0] == "Machine"  # family hint still applies
    assert all(len(tree.branches[b]) >= 4 for b in BRANCHES)


def test_keyword_items_are_prioritized():
    tree = build_tree("JIG BOWSKEW 2 BEAM bị kẹt cứng khi điều chỉnh Ranks S, "
                      "máy báo mã lỗi")
    machine_qs = [it.question for it in tree.branches["Machine"]]
    assert any("Vị trí kẹt" in q for q in machine_qs)
    assert any("Mã lỗi hiển thị đầy đủ" in q for q in machine_qs)


# ---------------------------------------------------------------------------
# Why-Why chain
# ---------------------------------------------------------------------------

def test_why_chain_has_five_levels():
    chain = build_why_chain(SIMULATED_PHENOMENON)
    assert len(chain) == 5
    assert [n.level for n in chain] == [1, 2, 3, 4, 5]
    assert SIMULATED_PHENOMENON in chain[0].question
    assert all(n.answer == "" for n in chain)  # left blank for investigator
    assert all(n.hint for n in chain)


# ---------------------------------------------------------------------------
# Markdown rendering + export
# ---------------------------------------------------------------------------

def test_render_markdown_structure(sim_conn):
    tree = build_tree(SIMULATED_PHENOMENON, code=SIMULATED_CODE,
                      code_family=SIMULATED_FAMILY, conn=sim_conn)
    md = render_markdown(tree)
    assert md.startswith("# Cây điều tra —")
    assert "## 1. Cây điều tra 4M" in md
    assert "## 2. Chuỗi Why-Why (5 lần hỏi vì sao)" in md
    assert "## 3. Tổng hợp dữ liệu/hiện vật cần thu thập" in md
    assert "- [ ]" in md  # checkboxes
    assert SIMULATED_NAME_VI in md
    assert SIMULATED_CODE in md
    for branch in BRANCHES:
        assert BRANCH_LABELS_VI[branch] in md


def test_export_markdown_writes_file(tmp_path, sim_conn):
    tree = build_tree(SIMULATED_PHENOMENON)
    out = export_markdown(tree, tmp_path / "SIMULATED-ke-hoach-dieu-tra.md")
    assert out.is_file()
    assert out.read_text(encoding="utf-8") == render_markdown(tree)


def test_export_adds_md_suffix(tmp_path):
    tree = build_tree(SIMULATED_PHENOMENON)
    out = export_markdown(tree, tmp_path / "SIMULATED-plan")
    assert out.suffix == ".md"
    assert out.is_file()
