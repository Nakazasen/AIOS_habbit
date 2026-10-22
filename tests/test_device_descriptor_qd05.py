"""Tests for QD-05: Dynamic Execution Provider Detection & Safety Gate (DESKTOP-QD-S2-GLOSSARY-WORKER-LIFECYCLE-HOME)."""
from __future__ import annotations

import pytest

from aios_habit.rag_v2.bge_onnx_backend import detect_onnx_execution_provider
from aios_habit.rag_v2.chunk_evaluation import load_bge_eval_identity
from aios_habit.rag_v2.semantic import SemanticModelDescriptor


def test_detect_onnx_execution_provider_returns_string() -> None:
    provider = detect_onnx_execution_provider()
    assert isinstance(provider, str)
    assert len(provider) > 0
    # On typical Windows machine with CPU ONNX, returns CPUExecutionProvider
    assert "ExecutionProvider" in provider


def test_semantic_model_descriptor_exposes_actual_device() -> None:
    desc = SemanticModelDescriptor(
        model_id="BAAI/bge-m3",
        dimension=1024,
        revision="5617a9f61b028005a4858fdac845db406aefb181",
        artifact_checksum="sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
        device="cpu",
        actual_device="CPUExecutionProvider",
        execution_provider="CPUExecutionProvider",
    )
    assert desc.device == "cpu"
    assert desc.actual_device == "CPUExecutionProvider"
    assert desc.execution_provider == "CPUExecutionProvider"

    safe_dict = desc.to_safe_dict()
    assert safe_dict["device"] == "cpu"
    assert safe_dict["actual_device"] == "CPUExecutionProvider"
    assert safe_dict["execution_provider"] == "CPUExecutionProvider"


def test_safety_gate_qd05_fingerprint_strictly_preserved() -> None:
    """SAFETY GATE (CONG AN TOAN QD-05):

    The SHA-256 fingerprint must remain strictly unchanged regardless of
    actual_device / execution_provider reporting to preserve 100% compatibility
    with existing production vector databases (avoiding invalidation).
    """
    desc_legacy = SemanticModelDescriptor(
        model_id="BAAI/bge-m3",
        dimension=1024,
        revision="5617a9f61b028005a4858fdac845db406aefb181",
        artifact_checksum="sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
        device="cpu",
    )
    desc_with_actual = SemanticModelDescriptor(
        model_id="BAAI/bge-m3",
        dimension=1024,
        revision="5617a9f61b028005a4858fdac845db406aefb181",
        artifact_checksum="sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
        device="cpu",
        actual_device="CPUExecutionProvider",
        execution_provider="CPUExecutionProvider",
    )
    desc_with_gpu = SemanticModelDescriptor(
        model_id="BAAI/bge-m3",
        dimension=1024,
        revision="5617a9f61b028005a4858fdac845db406aefb181",
        artifact_checksum="sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
        device="cpu",
        actual_device="CUDAExecutionProvider",
        execution_provider="CUDAExecutionProvider",
    )

    # All three must share the exact same fingerprint!
    assert desc_legacy.fingerprint == desc_with_actual.fingerprint
    assert desc_legacy.fingerprint == desc_with_gpu.fingerprint


def test_chunk_evaluation_load_bge_eval_identity(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    model_dir = tmp_path / "fake_model"
    model_dir.mkdir()
    manifest.write_text(
        '{"model": {"path": "' + str(model_dir).replace('\\', '\\\\') + '", "revision": "rev1234567890", "checksum": "sha256:abcdef1234567890", "device": "cpu"}}',
        encoding="utf-8"
    )
    meta = load_bge_eval_identity(manifest)
    assert meta["device"] == "cpu"
    assert "actual_device" in meta
    assert "execution_provider" in meta
    assert isinstance(meta["actual_device"], str)


def test_safety_gate_qd05_on_production_index_copy(tmp_path) -> None:
    """SAFETY GATE (CONG AN TOAN QD-05):
    Verify on a temporary copy of the real production SQLite index that:
    1. Changing the hashed `device` field inside fingerprint invalidates all stored vectors (0 matching rows).
    2. Preserving `device='cpu'` in fingerprint while decoupling `actual_device`/`execution_provider`
       matches 100% of stored production vectors without requiring index rebuild.
    """
    from pathlib import Path
    import shutil
    import sqlite3
    from aios_habit.workspace_chat_rag_v2_adapter import (
        WorkspaceChatRagV2CanaryConfig,
        _expected_backend_fingerprint,
    )

    prod_db = Path("D:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/mom/library.sqlite")
    if not prod_db.is_file():
        pytest.skip("Production SQLite index not present on this host")

    copy_db = tmp_path / "mom_copy.sqlite"
    shutil.copy2(prod_db, copy_db)

    cfg = WorkspaceChatRagV2CanaryConfig.from_env()
    expected_fp = _expected_backend_fingerprint(cfg)
    assert len(expected_fp) == 64

    from aios_habit.rag_v2.bge_onnx_backend import (
        BGE_M3_DIMENSION,
        BGE_M3_MODEL_ID,
        DEFAULT_BGE_BACKEND,
        _onnxruntime_version,
        require_onnx_model_dir,
        resolve_bge_backend_name,
        resolve_onnx_checksum,
    )

    backend_name = resolve_bge_backend_name(DEFAULT_BGE_BACKEND)
    model_dir = require_onnx_model_dir(backend_name=backend_name)
    checksum = resolve_onnx_checksum(model_dir)
    ort_version = _onnxruntime_version()
    detected_ep = detect_onnx_execution_provider()

    desc_current = SemanticModelDescriptor(
        model_id=BGE_M3_MODEL_ID,
        revision=cfg.bge_m3_model_revision,
        runtime="onnxruntime-int8",
        runtime_version=ort_version,
        dimension=BGE_M3_DIMENSION,
        normalized=True,
        artifact_checksum=checksum,
        device="cpu",
        actual_device=detected_ep,
        execution_provider=detected_ep,
    )
    # Hypothetical descriptor if device in fingerprint were mutated
    desc_mutated = SemanticModelDescriptor(
        model_id=BGE_M3_MODEL_ID,
        revision=cfg.bge_m3_model_revision,
        runtime="onnxruntime-int8",
        runtime_version=ort_version,
        dimension=BGE_M3_DIMENSION,
        normalized=True,
        artifact_checksum=checksum,
        device=f"onnxruntime:{detected_ep}",
        actual_device=detected_ep,
        execution_provider=detected_ep,
    )

    conn = sqlite3.connect(copy_db)
    try:
        total_rows = conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
        matched_preserved = conn.execute(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE model_fingerprint = ?",
            (desc_current.fingerprint,),
        ).fetchone()[0]
        matched_mutated = conn.execute(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE model_fingerprint = ?",
            (desc_mutated.fingerprint,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert total_rows > 0
    # Mutating hashed device breaks production index readability (0 matches)
    assert matched_mutated == 0
    # Preserving hashed device while exposing actual_device matches 100% of production vectors
    assert matched_preserved == total_rows
    assert desc_current.fingerprint == expected_fp


