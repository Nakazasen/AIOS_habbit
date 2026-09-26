import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_habit.rag_v2.bge_onnx_backend import (
    BGE_BACKEND_FLAG,
    DEFAULT_BGE_BACKEND,
    INT8_ONNX_DIR_NAME,
    ONNX_CHECKSUM_FLAG,
    ONNX_DIR_NAME,
    ONNX_MODEL_PATH_FLAG,
    default_onnx_int8_model_dir,
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


def test_bge_backend_flag_defaults_to_fp32_onnx_and_keeps_int8_distinct(monkeypatch):
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    assert DEFAULT_BGE_BACKEND == "onnx"
    assert resolve_bge_backend_name() == "onnx"
    assert resolve_bge_backend_name("onnx_int8") == "onnx_int8"
    assert resolve_bge_backend_name("auto") == "onnx"


def test_bge_backend_flag_explicit_pytorch_override(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "pytorch")
    assert resolve_bge_backend_name() == "pytorch"
    assert resolve_bge_backend_name("onnx_int8") == "pytorch"
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    assert resolve_bge_backend_name("pytorch") == "pytorch"


def test_bge_backend_flag_auto_selects_fp32_onnx(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "auto")
    assert resolve_bge_backend_name() == "onnx"
    assert resolve_bge_backend_name("pytorch") == "onnx"


def test_bge_backend_flag_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "tensorrt")
    with pytest.raises(SemanticBackendUnavailable, match="BGE_BACKEND must be"):
        resolve_bge_backend_name()


def test_require_onnx_model_dir_fails_closed_on_missing_model(tmp_path, monkeypatch):
    missing = tmp_path / "no-such-model"
    monkeypatch.setenv(ONNX_MODEL_PATH_FLAG, str(missing))
    with pytest.raises(SemanticBackendUnavailable) as exc_info:
        require_onnx_model_dir()
    message = str(exc_info.value)
    assert str(missing) in message
    assert "BGE_BACKEND=pytorch" in message


def test_require_onnx_model_dir_requires_fp32_model_file(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "model_quantized.onnx").touch()
    monkeypatch.setenv(ONNX_MODEL_PATH_FLAG, str(model_dir))
    monkeypatch.setenv(ONNX_CHECKSUM_FLAG, "ab" * 32)
    with pytest.raises(SemanticBackendUnavailable) as exc_info:
        require_onnx_model_dir()
    assert "model.onnx" in str(exc_info.value)
    assert str(model_dir) in str(exc_info.value)


def test_require_onnx_model_dir_requires_quantized_model_for_int8(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "model.onnx").touch()
    monkeypatch.setenv(ONNX_MODEL_PATH_FLAG, str(model_dir))
    monkeypatch.setenv(ONNX_CHECKSUM_FLAG, "ab" * 32)
    with pytest.raises(SemanticBackendUnavailable) as exc_info:
        require_onnx_model_dir(backend_name="onnx_int8")
    assert "model_quantized.onnx" in str(exc_info.value)
    assert str(model_dir) in str(exc_info.value)


def test_require_onnx_model_dir_reports_unreadable_checksum(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "model.onnx").touch()
    onnx_checksum_sidecar(model_dir).write_text("", encoding="utf-8")
    monkeypatch.setenv(ONNX_MODEL_PATH_FLAG, str(model_dir))
    monkeypatch.delenv(ONNX_CHECKSUM_FLAG, raising=False)
    with pytest.raises(SemanticBackendUnavailable) as exc_info:
        require_onnx_model_dir()
    assert str(model_dir) in str(exc_info.value)
    assert "BGE_BACKEND=pytorch" in str(exc_info.value)


def test_bge_backend_flag_selects_separate_onnx_backends(monkeypatch):
    monkeypatch.setenv(BGE_BACKEND_FLAG, "onnx")
    assert resolve_bge_backend_name() == "onnx"
    monkeypatch.setenv(BGE_BACKEND_FLAG, "onnx_int8")
    assert resolve_bge_backend_name() == "onnx_int8"


def test_onnx_defaults_to_fp32_model_and_int8_has_own_model_dir(tmp_path, monkeypatch):
    monkeypatch.delenv(ONNX_MODEL_PATH_FLAG, raising=False)
    monkeypatch.delenv(ONNX_CHECKSUM_FLAG, raising=False)
    default_path = default_onnx_model_dir()
    int8_path = default_onnx_int8_model_dir()
    assert ONNX_DIR_NAME == "bge-m3-onnx-fp32"
    assert INT8_ONNX_DIR_NAME == "bge-m3-onnx-int8"
    assert default_path.name == ONNX_DIR_NAME
    assert int8_path.name == INT8_ONNX_DIR_NAME
    assert default_path != int8_path
    assert resolve_onnx_model_path() == default_path
    assert resolve_onnx_model_path("onnx_int8") == int8_path
    assert onnx_checksum_sidecar(default_path).name == "bge-m3-onnx-fp32.sha256"
    assert onnx_checksum_sidecar(int8_path).name == "bge-m3-onnx-int8.sha256"

    model_dir = tmp_path / ONNX_DIR_NAME
    model_dir.mkdir()
    checksum = "sha256:" + "9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093"
    sidecar = onnx_checksum_sidecar(model_dir)
    sidecar.write_text(checksum + "\n", encoding="utf-8")
    assert resolve_onnx_checksum(model_dir) == checksum


def test_backend_selects_model_file_for_each_onnx_runtime(tmp_path):
    from aios_habit.rag_v2.bge_onnx_backend import _model_file

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    fp32_model = model_dir / "model.onnx"
    int8_model = model_dir / "model_quantized.onnx"
    fp32_model.touch()
    int8_model.touch()
    assert _model_file(model_dir, "onnx") == fp32_model
    assert _model_file(model_dir, "onnx_int8") == int8_model


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



def test_onnx_artifact_checksum_keeps_fp32_and_int8_fingerprints_distinct(tmp_path):
    from aios_habit.rag_v2.bge_onnx_backend import OnnxInt8BgeM3Backend

    fp32_dir = tmp_path / "bge-m3-onnx-fp32"
    int8_dir = tmp_path / "bge-m3-onnx-int8"
    fp32_dir.mkdir()
    int8_dir.mkdir()
    tokenizer = SimpleNamespace(token_to_id=lambda _token: None)

    def fingerprint(model_dir, checksum, backend_name):
        backend = OnnxInt8BgeM3Backend(
            model_dir,
            backend_name=backend_name,
            revision="rev",
            artifact_checksum=checksum,
            dimension=4,
            session=object(),
            tokenizer=tokenizer,
        )
        return backend.descriptor.fingerprint

    fp32_fingerprint = fingerprint(fp32_dir, "sha256:" + "ab" * 32, "onnx")
    int8_fingerprint = fingerprint(int8_dir, "sha256:" + "cd" * 32, "onnx_int8")
    assert fp32_fingerprint != int8_fingerprint

def test_resolver_uses_distinct_onnx_models_and_keeps_pytorch_override(
    tmp_path, monkeypatch
):
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    monkeypatch.delenv(ONNX_MODEL_PATH_FLAG, raising=False)
    monkeypatch.delenv(ONNX_CHECKSUM_FLAG, raising=False)
    created = {}
    model_paths = {
        "onnx": tmp_path / "bge-m3-onnx-fp32",
        "onnx_int8": tmp_path / "bge-m3-onnx-int8",
    }
    checksums = {
        model_paths["onnx"]: "sha256:" + "ab" * 32,
        model_paths["onnx_int8"]: "sha256:" + "cd" * 32,
    }

    class Marker:
        def __init__(self, kind):
            self.kind = kind
            self.capability = SimpleNamespace(require=lambda: None)
            self.sparse_capability = SimpleNamespace(available=True)
            self.multivector_capability = SimpleNamespace(available=False)

    def create_onnx_backend(*, model_path, artifact_checksum, backend_name, **_kwargs):
        created[Path(model_path).name] = (artifact_checksum, backend_name)
        return Marker("onnx")

    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.require_onnx_model_dir",
        lambda *, backend_name: model_paths[backend_name],
    )
    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.resolve_onnx_checksum",
        lambda model_path: checksums[Path(model_path)],
    )
    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.OnnxInt8BgeM3Backend",
        create_onnx_backend,
    )
    default_config = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_revision="rev",
    )
    resolved = _resolve_embedding_backend(default_config, None)
    assert resolved.kind == "onnx"
    assert created["bge-m3-onnx-fp32"] == (checksums[model_paths["onnx"]], "onnx")
    compatibility = default_config.index_build_compatibility()["embedding_model"]
    assert compatibility["runtime_backend"] == "onnx"
    assert compatibility["max_length"] == 512
    assert json.dumps(compatibility)

    monkeypatch.setenv(BGE_BACKEND_FLAG, "onnx_int8")
    int8_config = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_revision="rev",
        bge_backend="onnx_int8",
    )
    resolved = _resolve_embedding_backend(int8_config, None)
    assert resolved.kind == "onnx"
    assert created["bge-m3-onnx-int8"] == (
        checksums[model_paths["onnx_int8"]],
        "onnx_int8",
    )
    int8_compatibility = int8_config.index_build_compatibility()["embedding_model"]
    assert int8_compatibility["runtime_backend"] == "onnx_int8"
    assert checksums[model_paths["onnx"]] != checksums[model_paths["onnx_int8"]]

    monkeypatch.setenv(BGE_BACKEND_FLAG, "pytorch")
    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.BgeM3Backend",
        lambda *args, **kwargs: Marker("pytorch"),
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


def test_default_onnx_checksum_failure_reports_path_and_override(tmp_path, monkeypatch):
    monkeypatch.delenv(BGE_BACKEND_FLAG, raising=False)
    model_path = tmp_path / "bge-m3-onnx-fp32"
    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.require_onnx_model_dir",
        lambda *, backend_name: model_path,
    )
    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.resolve_onnx_checksum",
        lambda _model_path: "sha256:" + "ab" * 32,
    )

    def fail_checksum_verification(**_kwargs):
        raise SemanticBackendUnavailable("local model checksum mismatch")

    monkeypatch.setattr(
        "aios_habit.rag_v2.pipeline.OnnxInt8BgeM3Backend",
        fail_checksum_verification,
    )
    config = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_revision="rev",
    )
    with pytest.raises(SemanticBackendUnavailable) as exc_info:
        _resolve_embedding_backend(config, None)
    assert str(model_path) in str(exc_info.value)
    assert "BGE_BACKEND=pytorch" in str(exc_info.value)
