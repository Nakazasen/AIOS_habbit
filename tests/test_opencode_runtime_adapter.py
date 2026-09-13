"""Unit and contract tests for OpenCodeRuntimeAdapter."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aios_habit.opencode_runtime_adapter import (
    OpenCodeRuntimeAdapter,
    RuntimeAdapterError,
    RuntimeRequest,
)
from aios_habit.workspace_agent_policy import (
    AgentPolicyError,
    TASK_TYPE_CODE_CHANGE,
    TASK_TYPE_ERROR_REPORT,
    create_scope_grant,
)


def test_adapter_initialization_and_health(tmp_path: Path):
    grant = create_scope_grant(
        work_id="WORK-TEST-001",
        task_root=tmp_path,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    req = RuntimeRequest(work_id="WORK-TEST-001", action="health")
    receipt = adapter.execute_request(req)
    assert receipt.status == "passed"
    assert receipt.payload.get("status") == "ok"
    assert receipt.sequence == 1


def test_adapter_file_operations_and_containment(tmp_path: Path):
    grant = create_scope_grant(
        work_id="WORK-TEST-002",
        task_root=tmp_path,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    # 1. Create file
    create_req = RuntimeRequest(
        work_id="WORK-TEST-002",
        action="create_file",
        payload={"path": "src/calc.py", "content": "def add(a, b):\n    return a + b\n"},
    )
    r1 = adapter.execute_request(create_req)
    assert r1.status == "passed"
    assert (tmp_path / "src" / "calc.py").is_file()

    # 2. Read file
    read_req = RuntimeRequest(
        work_id="WORK-TEST-002",
        action="read_file",
        payload={"path": "src/calc.py"},
    )
    r2 = adapter.execute_request(read_req)
    assert r2.status == "passed"
    assert "def add" in r2.payload["content"]

    # 3. Search files
    search_req = RuntimeRequest(
        work_id="WORK-TEST-002",
        action="search_files",
        payload={"query": "add"},
    )
    r3 = adapter.execute_request(search_req)
    assert r3.status == "passed"
    assert "src/calc.py" in r3.payload["matches"]

    # 4. Edit file
    edit_req = RuntimeRequest(
        work_id="WORK-TEST-002",
        action="edit_file",
        payload={"path": "src/calc.py", "content": "def add(a, b):\n    return a + b + 0\n"},
    )
    r4 = adapter.execute_request(edit_req)
    assert r4.status == "passed"
    assert (tmp_path / "src" / "calc.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b + 0\n"

    # 5. Path traversal denial
    with pytest.raises(AgentPolicyError, match="path traversal"):
        adapter.execute_request(
            RuntimeRequest(
                work_id="WORK-TEST-002",
                action="read_file",
                payload={"path": "../secret.txt"},
            )
        )

    # 6. Secret denial
    with pytest.raises(AgentPolicyError, match="chứa bí mật"):
        adapter.execute_request(
            RuntimeRequest(
                work_id="WORK-TEST-002",
                action="create_file",
                payload={"path": ".env", "content": "API_KEY=123"},
            )
        )


def test_adapter_test_command_execution(tmp_path: Path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8")

    grant = create_scope_grant(
        work_id="WORK-TEST-003",
        task_root=tmp_path,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    cmd_req = RuntimeRequest(
        work_id="WORK-TEST-003",
        action="run_test",
        payload={"command": f"python -m unittest {test_file.name}"},
    )
    receipt = adapter.execute_request(cmd_req)
    assert receipt.status in ("passed", "failed")
    assert "returncode" in receipt.payload
    assert "command" in receipt.payload


def test_adapter_idempotency_and_scope_validation(tmp_path: Path):
    grant = create_scope_grant(
        work_id="WORK-TEST-004",
        task_root=tmp_path,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    req1 = RuntimeRequest(
        work_id="WORK-TEST-004",
        action="create_file",
        payload={"path": "note.txt", "content": "hello"},
        idempotency_key="KEY-001",
        scope_digest=grant.scope_digest,
    )
    res1 = adapter.execute_request(req1)
    assert res1.sequence == 1

    # Exact same request with same idempotency key returns exact same receipt
    res2 = adapter.execute_request(req1)
    assert res2.event_id == res1.event_id
    assert res2.sequence == 1

    # Same key with different payload raises error
    req_conflict = RuntimeRequest(
        work_id="WORK-TEST-004",
        action="create_file",
        payload={"path": "note.txt", "content": "different"},
        idempotency_key="KEY-001",
        scope_digest=grant.scope_digest,
    )
    with pytest.raises(RuntimeAdapterError, match="trùng lặp với nội dung khác"):
        adapter.execute_request(req_conflict)

    # Invalid scope digest raises error
    req_bad_scope = RuntimeRequest(
        work_id="WORK-TEST-004",
        action="create_file",
        payload={"path": "note2.txt", "content": "test"},
        scope_digest="sha256:invalid",
    )
    with pytest.raises(RuntimeAdapterError, match="không khớp với nhiệm vụ"):
        adapter.execute_request(req_bad_scope)


def test_adapter_workspace_state_and_events(tmp_path: Path):
    grant = create_scope_grant(
        work_id="WORK-TEST-005",
        task_root=tmp_path,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    # State before file
    s1 = adapter.execute_request(RuntimeRequest(work_id="WORK-TEST-005", action="get_workspace_state"))
    assert s1.payload["total_files"] == 0

    # Add file
    (tmp_path / "data.txt").write_text("123", encoding="utf-8")
    s2 = adapter.execute_request(RuntimeRequest(work_id="WORK-TEST-005", action="get_workspace_state"))
    assert s2.payload["total_files"] == 1
    assert "data.txt" in s2.payload["manifest"]

    # List events
    evts = adapter.execute_request(RuntimeRequest(work_id="WORK-TEST-005", action="list_events"))
    assert len(evts.payload["events"]) >= 2
