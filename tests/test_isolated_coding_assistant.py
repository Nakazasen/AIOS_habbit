from __future__ import annotations

import pytest
from pathlib import Path

from aios_habit.coding_assistant import (
    CodingProposal,
    ProposalStateError,
    ScopeViolationError,
    approve_coding_proposal,
    build_observed_evidence,
    create_coding_proposal,
    create_coding_task_pack,
    parse_diff_touched_files,
    reject_coding_proposal,
    verify_coding_execution,
)
from aios_habit.agent_result_import import (
    FAIL,
    REVIEW_REQUIRED,
    VERIFIED_PASS,
    attach_report_sha256,
)
from aios_habit.agent_task_pack import ValidationError


SAMPLE_DIFF = """--- a/src/aios_habit/calculator.py
+++ b/src/aios_habit/calculator.py
@@ -1,3 +1,4 @@
 def add(a, b):
-    return a - b
+    return a + b
"""

SAMPLE_DIFF_FORBIDDEN = """--- a/local_cases/secrets.txt
+++ b/local_cases/secrets.txt
@@ -1 +1 @@
-old
+new
"""

SAMPLE_DIFF_OUT_OF_SCOPE = """--- a/other/module.py
+++ b/other/module.py
@@ -1 +1 @@
-old
+new
"""


def _sample_task_pack(tmp_path: Path) -> tuple[dict, str, str]:
    return create_coding_task_pack(
        task_id="TASK_FIX_CALC_001",
        case_id="CASE_CALC_100",
        objective="Sửa lỗi hàm add trong module calculator",
        allowed_files=["src/aios_habit/calculator.py"],
        allowed_commands=["uv run pytest tests/test_calc.py -v"],
        required_tests=["tests/test_calc.py"],
        export_root=str(tmp_path / "outbox"),
    )


def test_task_pack_scoping_and_forbidden_paths(tmp_path: Path):
    # 1. Valid task pack export
    pack, pack_sha256, exp_path = _sample_task_pack(tmp_path)
    assert pack_sha256 is not None
    assert len(pack_sha256) == 64
    assert Path(exp_path).exists()
    assert pack["scope"]["allowed_files"] == ["src/aios_habit/calculator.py"]
    assert "local_cases/**" in pack["scope"]["forbidden_files"]
    assert "local_runs/**" in pack["scope"]["forbidden_files"]

    # 2. Reject empty objective
    with pytest.raises(ValidationError):
        create_coding_task_pack(
            task_id="TASK_ERR_001",
            case_id="CASE_1",
            objective="",
            allowed_files=["src/test.py"],
            allowed_commands=["pytest"],
            required_tests=["test.py"],
            export_root=str(tmp_path / "outbox"),
        )

    # 3. Reject forbidden files in allowed_files
    with pytest.raises(ValidationError):
        create_coding_task_pack(
            task_id="TASK_ERR_002",
            case_id="CASE_2",
            objective="Thử truy cập file cấm",
            allowed_files=["local_cases/db.sqlite"],
            allowed_commands=["pytest"],
            required_tests=["test.py"],
            export_root=str(tmp_path / "outbox"),
        )


def test_coding_proposal_creation_and_scoping(tmp_path: Path):
    pack, pack_sha256, _ = _sample_task_pack(tmp_path)
    pack["pack_sha256"] = pack_sha256

    # 1. Valid proposal creation
    prop = create_coding_proposal(
        task_pack=pack,
        case_id="CASE_CALC_100",
        diff_content=SAMPLE_DIFF,
        commands_to_run=["uv run pytest tests/test_calc.py -v"],
        risk_assessment="Rủi ro thấp, chỉ đổi phép trừ thành cộng.",
    )
    assert prop.status == "pending"
    assert prop.version == 1
    assert len(prop.proposal_digest) == 64
    assert prop.task_id == pack["task_id"]

    # 2. Reject diff with empty content
    with pytest.raises(ScopeViolationError, match="trống"):
        create_coding_proposal(
            task_pack=pack,
            case_id="CASE_CALC_100",
            diff_content="   ",
            commands_to_run=["uv run pytest tests/test_calc.py -v"],
            risk_assessment="test",
        )

    # 3. Reject diff touching forbidden files
    with pytest.raises(ScopeViolationError, match="cấm tuyệt đối"):
        create_coding_proposal(
            task_pack=pack,
            case_id="CASE_CALC_100",
            diff_content=SAMPLE_DIFF_FORBIDDEN,
            commands_to_run=["uv run pytest tests/test_calc.py -v"],
            risk_assessment="Sửa file hệ thống",
        )

    # 4. Reject diff touching out of scope files
    with pytest.raises(ScopeViolationError, match="ngoài phạm vi"):
        create_coding_proposal(
            task_pack=pack,
            case_id="CASE_CALC_100",
            diff_content=SAMPLE_DIFF_OUT_OF_SCOPE,
            commands_to_run=["uv run pytest tests/test_calc.py -v"],
            risk_assessment="Sửa file ngoài",
        )

    # 5. Reject unallowed or forbidden commands
    with pytest.raises(ScopeViolationError, match="không nằm trong danh sách lệnh"):
        create_coding_proposal(
            task_pack=pack,
            case_id="CASE_CALC_100",
            diff_content=SAMPLE_DIFF,
            commands_to_run=["npm test"],
            risk_assessment="Test",
        )


def test_coding_proposal_approval_and_rejection(tmp_path: Path):
    pack, pack_sha256, _ = _sample_task_pack(tmp_path)
    prop = create_coding_proposal(
        task_pack=pack,
        case_id="CASE_CALC_100",
        diff_content=SAMPLE_DIFF,
        commands_to_run=["uv run pytest tests/test_calc.py -v"],
        risk_assessment="Sửa đúng",
    )

    # 1. Approval with wrong digest fails
    with pytest.raises(ProposalStateError, match="không khớp"):
        approve_coding_proposal(prop, expected_digest="0" * 64, approver="lead_engineer")

    # 2. Approval with matching digest succeeds
    approved = approve_coding_proposal(
        prop,
        expected_digest=prop.proposal_digest,
        approver="lead_engineer",
        notes="Đã kiểm tra diff và chấp thuận.",
    )
    assert approved.status == "approved"
    assert approved.version == 2
    assert approved.approved_by == "lead_engineer"
    assert "chấp thuận" in approved.approval_notes

    # 3. Cannot approve already approved proposal
    with pytest.raises(ProposalStateError, match="Chỉ có thể phê duyệt"):
        approve_coding_proposal(approved, expected_digest=approved.proposal_digest, approver="lead_engineer")

    # 4. Rejection flow
    prop2 = create_coding_proposal(
        task_pack=pack,
        case_id="CASE_CALC_100",
        diff_content=SAMPLE_DIFF,
        commands_to_run=["uv run pytest tests/test_calc.py -v"],
        risk_assessment="Sửa đúng",
    )
    rejected = reject_coding_proposal(prop2, reviewer="lead_engineer", reason="Chưa viết unit test bổ sung.")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Chưa viết unit test bổ sung."


def test_observed_evidence_verification(tmp_path: Path):
    pack, pack_sha256, _ = _sample_task_pack(tmp_path)
    pack["pack_sha256"] = pack_sha256

    prop = create_coding_proposal(
        task_pack=pack,
        case_id="CASE_CALC_100",
        diff_content=SAMPLE_DIFF,
        commands_to_run=["uv run pytest tests/test_calc.py -v"],
        risk_assessment="Sửa đúng",
    )

    # Base report payload
    base_report = {
        "schema_version": "aios_agent_report_v1",
        "task_id": pack["task_id"],
        "task_pack_sha256": pack_sha256,
        "agent_class": "implementation",
        "model_tool_name": "aios_coding_agent",
        "declared_status": "PASS",
        "baseline": {
            "branch": "main",
            "head": "0" * 40,
        },
        "final_state": {
            "branch": "main",
            "head": "0" * 40,
            "worktree_clean": True,
            "staged_files": [],
            "untracked_files": [],
            "commit_hash": "a" * 40,
            "push_status": "NOT_PUSHED",
        },
        "declared_files": {
            "changed_files": ["src/aios_habit/calculator.py"],
            "committed_files": ["src/aios_habit/calculator.py"],
            "staged_files": [],
            "untracked_files": [],
        },
        "declared_commands": [
            {"command": "uv run pytest tests/test_calc.py -v", "exit_code": 0, "result": "PASS"}
        ],
        "declared_tests": [
            {"command": "tests/test_calc.py", "result": "PASS", "exit_code": 0}
        ],
        "risks": ["Rui ro thap"],
        "blockers": [],
        "rollback": {
            "performed": False,
            "strategy_details": "N/A",
        },
        "reason_codes": [],
    }
    signed_report = attach_report_sha256(base_report)

    # 1. Unapproved proposal cannot be verified as PASS
    dec1 = verify_coding_execution(
        task_pack=pack,
        proposal=prop,  # status is pending
        report_dict=signed_report,
    )
    assert dec1.verdict == FAIL
    assert "PROPOSAL_NOT_APPROVED" in dec1.reason_codes

    # 2. Approved proposal without observed evidence rejects self-reported PASS
    approved_prop = approve_coding_proposal(
        prop, expected_digest=prop.proposal_digest, approver="lead_engineer"
    )
    dec2 = verify_coding_execution(
        task_pack=pack,
        proposal=approved_prop,
        report_dict=signed_report,
        observed_evidence=None,
    )
    assert dec2.verdict == REVIEW_REQUIRED
    assert "DECLARED_PASS_WITHOUT_OBSERVED_EVIDENCE" in dec2.reason_codes

    # 3. Approved proposal with valid observed evidence yields VERIFIED_PASS
    observed = build_observed_evidence(
        tests_passed=True,
        changed_files=["src/aios_habit/calculator.py"],
        worktree_clean=True,
    )
    dec3 = verify_coding_execution(
        task_pack=pack,
        proposal=approved_prop,
        report_dict=signed_report,
        observed_evidence=observed,
    )
    assert dec3.verdict == VERIFIED_PASS
    assert "VERIFIED_PASS" in dec3.safe_summary
    assert "100%" in dec3.evidence_summary


def test_coding_assistant_ui_components_wired():
    ui_source = Path("src/aios_habit/workspace_case_ui.py").read_text(encoding="utf-8")

    assert "Trợ lý lập trình trong không gian cách ly" in ui_source
    assert "Tạo gói công việc lập trình (Task Pack)" in ui_source
    assert "Đề xuất thay đổi mã nguồn (Coding Proposal & Diff)" in ui_source
    assert "Thẩm định và cấp phép đề xuất lập trình" in ui_source
    assert "Nghiệm thu kết quả lập trình và bằng chứng thực thi" in ui_source
    assert "create_coding_task_pack" in ui_source
    assert "create_coding_proposal" in ui_source
    assert "approve_coding_proposal" in ui_source
    assert "reject_coding_proposal" in ui_source
    assert "verify_coding_execution" in ui_source
