# -*- coding: utf-8 -*-
"""Unit & Reproduction tests for ticket DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX.

Verifies:
1. Full send-draft trap reproduction sequence (draft exists + send callback sets ack + rerun executes draft restore & ack gate):
   - Fails before fix (draft restored into input, ask_submitted remains False).
   - Passes after fix (draft cleared, input stays empty, ask_submitted is True).
2. Each of the 3 interlocking points independently:
   - Point (1): _handle_composer_send_callback removes draft_backup_key and sets clear_input_key.
   - Point (2): Draft restore branch refuses to restore draft when wsc_submitting_ack_{conv_id} is active,
                but restores draft normally when no submitting ack is present.
   - Point (3): Ack activation gate dispatches ask_submitted=True whenever valid wsc_submitting_ack has q_text,
                even if user_input is non-empty, and all send paths clear draft_backup_key.
3. Safe default environment variables via os.environ.setdefault at top of workspace_chat_app.py.
4. Honest initial wait steps in build_answer_wait_steps (step_timings=None never marks step 3 "Tổng hợp trả lời" as running,
   while harmonizing with LIVENESS step_timings when provided).
"""
from __future__ import annotations

import ast
import os
import types
from pathlib import Path
from typing import Any, Dict, List

import pytest

from aios_habit.workspace_chat_ui import build_answer_wait_steps

APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


class _SessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _load_app_ast() -> Tuple[str, ast.Module]:
    source = APP_PATH.read_text(encoding="utf-8")
    return source, ast.parse(source, filename=str(APP_PATH))


def _extract_send_callback_fn(tree: ast.Module, st_mock: Any):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_handle_composer_send_callback":
            mod = ast.Module(body=[node], type_ignores=[])
            ast.fix_missing_locations(mod)
            ns: Dict[str, Any] = {
                "st": st_mock,
                "time": __import__("time"),
                "uuid": __import__("uuid"),
                "json": __import__("json"),
                "Path": Path,
                "datetime": __import__("datetime").datetime,
            }
            exec(compile(mod, filename=str(APP_PATH), mode="exec"), ns)
            return ns["_handle_composer_send_callback"]
    raise AssertionError("_handle_composer_send_callback not found in workspace_chat_app.py")


def _extract_composer_draft_restore_stmts(tree: ast.Module) -> List[ast.stmt]:
    """Find the with st.container(border=True, key=f'wsc-composer-...') block and extract statements up to user_input = st.text_area."""
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call):
                    for kw in ctx.keywords:
                        if kw.arg == "key" and isinstance(kw.value, ast.JoinedStr):
                            s_repr = ast.unparse(kw.value)
                            if "wsc-composer-" in s_repr:
                                stmts: List[ast.stmt] = []
                                for stmt in node.body:
                                    stmts.append(stmt)
                                    if (
                                        isinstance(stmt, ast.Assign)
                                        and any(isinstance(t, ast.Name) and t.id == "uploaded_image" for t in stmt.targets)
                                    ):
                                        return stmts
    raise AssertionError("Composer draft restore block not found in workspace_chat_app.py")


def _extract_ack_gate_stmts(tree: ast.Module) -> List[ast.stmt]:
    """Extract the _current_submitting_ack check and ask_submitted activation gate right before 'if ask_submitted:'."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_render_chat_main_column":
            body = node.body
            for idx, stmt in enumerate(body):
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "_current_submitting_ack"
                ):
                    # Collect until `if ask_submitted:`
                    collected: List[ast.stmt] = []
                    for sub in body[idx:]:
                        if (
                            isinstance(sub, ast.If)
                            and isinstance(sub.test, ast.Name)
                            and sub.test.id == "ask_submitted"
                        ):
                            return collected
                        collected.append(sub)
    raise AssertionError("Ack activation gate not found in _render_chat_main_column")


def _make_st_mock() -> Any:
    st_mock = types.SimpleNamespace()
    st_mock.session_state = _SessionState()
    return st_mock


def test_reproduce_full_send_draft_trap_chain() -> None:
    """Requirement 4a: Simulate exact trap sequence (draft exists -> send callback -> rerun draft restore -> ack gate).
    Must FAIL before fix and PASS after fix.
    """
    _, tree = _load_app_ast()
    st_mock = _make_st_mock()
    conv_id = "CONV-3A496585"
    question = "Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"

    # Step 1: User typed question and a rerun occurred (e.g. changing collection dropdown or input blur),
    # saving both widget state and draft_backup_key.
    st_mock.session_state[f"wsc_question_input_{conv_id}"] = question
    st_mock.session_state[f"wsc_draft_input_backup_{conv_id}"] = question

    # Step 2: User clicks Send -> Streamlit runs on_click=_handle_composer_send_callback(conv_id)
    send_cb = _extract_send_callback_fn(tree, st_mock)
    send_cb(conv_id)

    assert f"wsc_submitting_ack_{conv_id}" in st_mock.session_state
    assert st_mock.session_state[f"wsc_submitting_ack_{conv_id}"]["q_text"] == question

    # Step 3: Script body reruns -> composer draft restore block executes before st.text_area
    draft_stmts = _extract_composer_draft_restore_stmts(tree)
    mod_draft = ast.Module(body=draft_stmts, type_ignores=[])
    ast.fix_missing_locations(mod_draft)
    active_conv = types.SimpleNamespace(id=conv_id)
    ns_draft: Dict[str, Any] = {"st": st_mock, "active_conversation": active_conv}
    exec(compile(mod_draft, filename=str(APP_PATH), mode="exec"), ns_draft)

    # Simulate st.text_area reading its key from session_state
    user_input = st_mock.session_state.get(f"wsc_question_input_{conv_id}", "")
    assert user_input == "", "Input box must remain cleared after clicking Send, not overwritten by draft backup"
    assert f"wsc_draft_input_backup_{conv_id}" not in st_mock.session_state, "draft_backup_key must be cleared on Send"

    # Step 4: Because is_answering is True during _submitting_ack, the Stop button branch sets ask_submitted = False.
    # Then the ack activation gate runs.
    ack_stmts = _extract_ack_gate_stmts(tree)
    mod_ack = ast.Module(body=ack_stmts, type_ignores=[])
    ast.fix_missing_locations(mod_ack)
    ns_ack: Dict[str, Any] = {
        "st": st_mock,
        "active_conversation": active_conv,
        "time": __import__("time"),
        "user_input": user_input,
        "ask_submitted": False,
    }
    exec(compile(mod_ack, filename=str(APP_PATH), mode="exec"), ns_ack)

    assert ns_ack["ask_submitted"] is True, "Ack gate must set ask_submitted=True"
    assert ns_ack["user_input"] == question, "Ack gate must populate user_input from submitting ack q_text"


def test_draft_restore_guarded_when_submitting_ack_present_and_works_normally_without_ack() -> None:
    """Requirement 2(2) & 4a: Draft restore must not overwrite input when wsc_submitting_ack is present,
    but must still restore draft normally when no wsc_submitting_ack exists.
    """
    _, tree = _load_app_ast()
    draft_stmts = _extract_composer_draft_restore_stmts(tree)
    mod_draft = ast.Module(body=draft_stmts, type_ignores=[])
    ast.fix_missing_locations(mod_draft)

    conv_id = "CONV-TEST-RESTORE"
    active_conv = types.SimpleNamespace(id=conv_id)

    # Case A: wsc_submitting_ack IS present and input is empty -> must NOT restore draft
    st_mock_a = _make_st_mock()
    st_mock_a.session_state[f"wsc_draft_input_backup_{conv_id}"] = "Bản nháp cũ"
    st_mock_a.session_state[f"wsc_question_input_{conv_id}"] = ""
    st_mock_a.session_state[f"wsc_submitting_ack_{conv_id}"] = {
        "q_text": "Bản nháp cũ",
        "user_msg_id": "MSG-U-12345678",
        "timestamp": 1000.0,
    }
    exec(compile(mod_draft, filename=str(APP_PATH), mode="exec"), {"st": st_mock_a, "active_conversation": active_conv})
    assert st_mock_a.session_state.get(f"wsc_question_input_{conv_id}", "") == ""

    # Case B: NO wsc_submitting_ack present and input is empty -> MUST restore draft as before
    st_mock_b = _make_st_mock()
    st_mock_b.session_state[f"wsc_draft_input_backup_{conv_id}"] = "Câu hỏi đang gõ dở"
    st_mock_b.session_state[f"wsc_question_input_{conv_id}"] = ""
    exec(compile(mod_draft, filename=str(APP_PATH), mode="exec"), {"st": st_mock_b, "active_conversation": active_conv})
    assert st_mock_b.session_state.get(f"wsc_question_input_{conv_id}") == "Câu hỏi đang gõ dở"


def test_ack_gate_dispatches_even_if_user_input_not_empty() -> None:
    """Requirement 2(3): Ack activation gate must not depend on `not user_input.strip()`."""
    _, tree = _load_app_ast()
    ack_stmts = _extract_ack_gate_stmts(tree)
    mod_ack = ast.Module(body=ack_stmts, type_ignores=[])
    ast.fix_missing_locations(mod_ack)

    conv_id = "CONV-TEST-ACK"
    active_conv = types.SimpleNamespace(id=conv_id)
    st_mock = _make_st_mock()
    now = __import__("time").time()
    st_mock.session_state[f"wsc_submitting_ack_{conv_id}"] = {
        "q_text": "Câu hỏi từ ack",
        "user_msg_id": "MSG-U-ABCDEF01",
        "timestamp": now,
    }

    ns_ack: Dict[str, Any] = {
        "st": st_mock,
        "active_conversation": active_conv,
        "time": __import__("time"),
        "user_input": "Chữ còn sót trong ô nhập",
        "ask_submitted": False,
    }
    exec(compile(mod_ack, filename=str(APP_PATH), mode="exec"), ns_ack)
    assert ns_ack["ask_submitted"] is True
    assert ns_ack["user_input"] == "Câu hỏi từ ack"


def test_env_vars_setdefault_at_top_of_workspace_chat_app() -> None:
    """Requirement 2(4): Top of workspace_chat_app.py sets os.environ.setdefault for the 5 required env vars."""
    source, _ = _load_app_ast()
    # Must appear before adapter imports
    first_adapter_idx = source.find("workspace_chat_rag_v2_adapter")
    assert first_adapter_idx != -1
    header_slice = source[:first_adapter_idx]

    expected_defaults = {
        "AIOS_RAGV2_WORKER_PERSIST": "1",
        "AIOS_DOMAIN_ROUTING_ENABLED": "1",
        "AIOS_RAG_V2_NUMPY_DENSE": "1",
        "AIOS_BGE_INIT_TIMEOUT": "420",
        "AIOS_BGE_QUERY_TIMEOUT": "1200",
    }
    for env_key, env_val in expected_defaults.items():
        assert (
            f'os.environ.setdefault("{env_key}", "{env_val}")' in header_slice
            or f"os.environ.setdefault('{env_key}', '{env_val}')" in header_slice
        ), f"Missing os.environ.setdefault for {env_key}={env_val} near top of workspace_chat_app.py"


def test_build_answer_wait_steps_honest_initial_state_and_liveness_harmony() -> None:
    """Requirement 2(5): Initial waiting state (without step_timings) never marks step 3 'Tổng hợp trả lời' as running,
    while preserving LIVENESS step_timings behavior when provided.
    """
    steps_initial = build_answer_wait_steps("dang_xu_ly", step_timings=None)
    assert len(steps_initial) == 3
    assert [s["dang_chay"] for s in steps_initial] == [True, False, False]
    assert steps_initial[0]["status"] == "running"
    assert steps_initial[0]["icon"] == "●"
    assert steps_initial[1]["status"] == "pending"
    assert steps_initial[1]["icon"] == "○"
    assert steps_initial[2]["status"] == "pending"
    assert steps_initial[2]["icon"] == "○"

    # Harmonized with LIVENESS step_timings when real progress exists
    steps_synth = build_answer_wait_steps(
        "dang_xu_ly",
        step_timings={
            "find": {"status": "done", "duration": 0.2},
            "read": {"status": "done", "duration": 0.3},
            "synth": {"status": "running", "elapsed": 1.4},
        },
    )
    assert [s["status"] for s in steps_synth] == ["done", "done", "running"]
    assert [s["icon"] for s in steps_synth] == ["✓", "✓", "●"]
    assert steps_synth[0]["timing_str"] == "(0.2s)"
    assert steps_synth[1]["timing_str"] == "(0.3s)"
    assert steps_synth[2]["timing_str"] == "(1.4s)"
