import json
from types import SimpleNamespace

import pytest

from aios_habit.rag_v2.bge_onnx_backend import (
    BGE_BACKEND_FLAG,
    ONNX_CHECKSUM_FLAG,
    ONNX_DIR_NAME,
    ONNX_MODEL_PATH_FLAG,
    default_onnx_model_dir,
    lexical_weights_from_hidden,
    onnx_checksum_sidecar,
    require_onnx_model_dir,
    resolve_bge_backend_name,
    resolve_onnx_checksum,
    resolve_onnx_model_path,
)
from aios_habit.rag_v2.pipeline import RagV2DevConfig, _resolve_embedding_backend
from aios_habit.rag_v2.retrieval_backends import sha256_model_tree, verify_model_tree
from aios_habit.rag_v2.semantic import SemanticBackendUnavailable


def test_bge_backend_flag_defaults_to_onnx(monkeypatch):
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    assert resolve_bge_backend_name() == "onnx_int8"
    assert resolve_bge_backend_name("onnx_int8") == "onnx_int8"
    assert resolve_bge_backend_name("auto") == "onnx_int8"


def test_bge_backend_flag_explicit_pytorch_override(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "pytorch")
    assert resolve_bge_backend_name() == "pytorch"
    assert resolve_bge_backend_name("onnx_int8") == "pytorch"
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    assert resolve_bge_backend_name("pytorch") == "pytorch"


def test_bge_backend_flag_auto_selects_onnx(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "auto")
    assert resolve_bge_backend_name() == "onnx_int8"
    assert resolve_bge_backend_name("pytorch") == "onnx_int8"


def test_bge_backend_flag_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "tensorrt")
    try:
        resolve_bge_backend_name()
    except SemanticBackendUnavailable:
        pass
    else:
        raise AssertionError("unknown BGE_BACKEND value must raise")


def test_require_onnx_model_dir_fails_closed_on_missing_model(tmp_path, monkeypatch):
    missing = tmp_path / "no-such-model"
    monkeypatch.setenv(ONNX_MODEL_PATH_FLAG, str(missing))
    try:
        require_onnx_model_dir()
    except SemanticBackendUnavailable as exc:
        message = str(exc)
        assert "BGE_BACKEND" in message or "pytorch" in message
        assert str(missing) in message
    else:
        raise AssertionError("missing ONNX model must raise fail-closed")
    finally:
        monkeypatch.delenv(ONNX_MODEL_PATH_FLAG, raising=False)


def test_require_onnx_model_dir_fails_closed_on_missing_file(tmp_path, monkeypatch):
    model_dir = tmp_path / "empty-model"
    model_dir.mkdir()
    checksum = "sha256:" + "ab" * 32
    monkeypatch.setenv(ONNX_MODEL_PATH_FLAG, str(model_dir))
    monkeypatch.setenv(ONNX_CHECKSUM_FLAG, checksum)
    try:
        require_onnx_model_dir()
    except SemanticBackendUnavailable as exc:
        assert "model file is missing" in str(exc)
    else:
        raise AssertionError("missing model.onnx must raise fail-closed")
    finally:
        monkeypatch.delenv(ONNX_MODEL_PATH_FLAG, raising=False)
        monkeypatch.delenv(ONNX_CHECKSUM_FLAG, raising=False)


def test_bge_backend_flag_selects_onnx_aliases(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "onnx")
    assert resolve_bge_backend_name() == "onnx_int8"
    monkeypatch.setenv(BGE_BACKEND_FLAG, "onnx_int8")
    assert resolve_bge_backend_name() == "onnx_int8"


def test_onnx_defaults_to_fp32_model_and_checksum_sidecar(tmp_path, monkeypatch):
    monkeypatch.delenv(ONNX_MODEL_PATH_FLAG, raising=False)
    monkeypatch.delenv(ONNX_CHECKSUM_FLAG, raising=False)
    default_path = default_onnx_model_dir()
    assert ONNX_DIR_NAME == "bge-m3-onnx-fp32"
    assert default_path.name == "bge-m3-onnx-fp32"
    assert resolve_onnx_model_path() == default_path
    assert onnx_checksum_sidecar(default_path).name == "bge-m3-onnx-fp32.sha256"

    model_dir = tmp_path / ONNX_DIR_NAME
    model_dir.mkdir()
    checksum = "sha256:" + "9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093"
    sidecar = onnx_checksum_sidecar(model_dir)
    sidecar.write_text(checksum + "\n", encoding="utf-8")
    assert resolve_onnx_checksum(model_dir) == checksum


def test_verify_model_tree_cache_skips_second_hash(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "weights.bin").write_bytes(b"abc")
    checksum = sha256_model_tree(model_dir)
    calls = {"count": 0}
    original = sha256_model_tree

    def counting(path):
        calls["count"] += 1
        return original(path)

    monkeypatch.setattr(
        "aios_habit.rag_v2.retrieval_backends.sha256_model_tree",
        counting,
    )
    assert verify_model_tree(model_dir, checksum) == checksum
    assert verify_model_tree(model_dir, checksum) == checksum
    assert calls["count"] == 1
    (model_dir / "weights.bin").write_bytes(b"abcd")
    with pytest.raises(SemanticBackendUnavailable):
        verify_model_tree(model_dir, checksum)
    assert calls["count"] == 2


def test_lexical_weights_keep_the_strongest_non_special_token():
    pytest.importorskip("numpy")
    import numpy as np

    hidden = np.asarray(
        [
            [1.0, 0.0],
            [0.0, 2.0],
            [0.0, 3.0],
            [4.0, 0.0],
        ],
        dtype=np.float32,
    )
    weights = lexical_weights_from_hidden(
        hidden,
        [0, 7, 7, 1],
        np.asarray([1.0, 1.0], dtype=np.float32),
        0.0,
        {0, 1},
    )
    assert weights == {"7": 3.0}


def test_onnx_backend_matches_cls_and_sparse_contract(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    import numpy as np

    from aios_habit.rag_v2.bge_onnx_backend import OnnxInt8BgeM3Backend

    model_dir = tmp_path / "onnx-model"
    model_dir.mkdir()
    np.save(model_dir / "sparse_linear.npy", np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32))

    class FakeTokenizer:
        def encode_batch(self, texts):
            return [
                SimpleNamespace(ids=[0, 7, 1], attention_mask=[1, 1, 0])
                for _text in texts
            ]

        def token_to_id(self, _token):
            return None

    class FakeSession:
        def get_inputs(self):
            return [SimpleNamespace(name="input_ids"), SimpleNamespace(name="attention_mask")]

        def get_outputs(self):
            return [SimpleNamespace(name="last_hidden_state")]

        def run(self, _names, feeds):
            batch, seq = feeds["input_ids"].shape
            hidden = np.zeros((batch, seq, 4), dtype=np.float32)
            hidden[:, 0, 0] = 3.0
            hidden[:, 1, 0] = 2.0
            return [hidden]

    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    backend = OnnxInt8BgeM3Backend(
        model_dir,
        revision="rev",
        artifact_checksum="sha256:" + "ab" * 32,
        dimension=4,
        max_length=512,
        session=FakeSession(),
        tokenizer=FakeTokenizer(),
    )
    dense = backend.embed_documents(["alpha"])
    sparse = backend.sparse_documents(["alpha"])
    assert dense[0] == tuple(value / 3.0 for value in (3.0, 0.0, 0.0, 0.0))
    assert sparse == ({"7": 2.0},)
    assert backend.embed_query("alpha") == dense[0]
    assert backend.sparse_query("alpha") == {"7": 2.0}
    assert backend.descriptor.runtime == "onnxruntime-int8"
    assert backend.multivector_capability.available is False


def test_resolver_defaults_to_onnx_and_keeps_pytorch_override(tmp_path, monkeypatch):
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    monkeypatch.delenv("AIOS_BGE_ONNX_MODEL_PATH", raising=False)
    monkeypatch.delenv("AIOS_BGE_ONNX_MODEL_CHECKSUM", raising=False)
    created = {}

    class Marker:
        def __init__(self, kind):
            self.kind = kind
            self.capability = SimpleNamespace(require=lambda: None)
            self.sparse_capability = SimpleNamespace(available=True)
            self.multivector_capability = SimpleNamespace(available=False)

    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.OnnxInt8BgeM3Backend",
        lambda *args, **kwargs: created.setdefault("backend", Marker("onnx")),
    )
    config = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_path=tmp_path,
        bge_m3_model_revision="rev",
        bge_m3_model_checksum="sha256:" + "cd" * 32,
    )
    resolved = _resolve_embedding_backend(config, None)
    assert resolved.kind == "onnx"
    compatibility = config.index_build_compatibility()["embedding_model"]
    assert compatibility["runtime_backend"] == "onnx_int8"
    assert compatibility["max_length"] == 512
    assert json.dumps(compatibility)

    monkeypatch.setenv(BGE_BACKEND_FLAG, "pytorch")
    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.BgeM3Backend",
        lambda *args, **kwargs: created.setdefault("pytorch", Marker("pytorch")),
    )
    pytorch_config = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_path=tmp_path,
        bge_m3_model_revision="rev",
        bge_m3_model_checksum="sha256:" + "cd" * 32,
        bge_backend="pytorch",
    )
    resolved = _resolve_embedding_backend(pytorch_config, None)
    assert resolved.kind == "pytorch"
    assert "runtime_backend" not in pytorch_config.index_build_compatibility()["embedding_model"]
