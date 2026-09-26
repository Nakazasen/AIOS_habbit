"""Optional ONNX Runtime fp32 path for BGE-M3 dense and learned-sparse vectors.

The ONNX fp32 runtime is the default. Set ``BGE_BACKEND=pytorch`` explicitly
to use the PyTorch FlagEmbedding path. This module does not import
onnxruntime or torch until a session is actually constructed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Any, Sequence

from .retrieval_backends import BGE_M3_DIMENSION, BGE_M3_MODEL_ID, verify_model_tree
from .semantic import (
    MultiVector,
    MultiVectorDescriptor,
    SemanticBackendError,
    SemanticBackendUnavailable,
    SemanticCapability,
    SemanticModelDescriptor,
    SparseVector,
    normalize_sparse_vector,
    normalize_vector,
)

LOGGER = logging.getLogger(__name__)

BGE_BACKEND_FLAG = "BGE_BACKEND"
ONNX_MODEL_PATH_FLAG = "AIOS_BGE_ONNX_MODEL_PATH"
ONNX_CHECKSUM_FLAG = "AIOS_BGE_ONNX_MODEL_CHECKSUM"
ONNX_MAX_LENGTH_FLAG = "AIOS_BGE_ONNX_MAX_LENGTH"
DEFAULT_ONNX_MAX_LENGTH = 512
ONNX_DIR_NAME = "bge-m3-onnx-fp32"
DEFAULT_BGE_BACKEND = "onnx_int8"
_BACKEND_ALIASES = {
    "pytorch": "pytorch",
    "flagembedding": "pytorch",
    "onnx_int8": "onnx_int8",
    "onnx": "onnx_int8",
    "auto": "onnx_int8",
}


def _onnx_override_hint() -> str:
    return f"Set {BGE_BACKEND_FLAG}=pytorch to use the PyTorch path explicitly."


def resolve_bge_backend_name(configured: str = "onnx_int8") -> str:
    """Return the active BGE runtime. An unset or auto flag selects ONNX fp32."""
    raw = os.environ.get(BGE_BACKEND_FLAG, "").strip().lower()
    if not raw:
        raw = (configured or "onnx_int8").strip().lower()
    try:
        return _BACKEND_ALIASES[raw]
    except KeyError as exc:
        raise SemanticBackendUnavailable(
            "BGE_BACKEND must be pytorch, onnx, onnx_int8 or auto"
        ) from exc


def default_onnx_model_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "models" / ONNX_DIR_NAME


def resolve_onnx_model_path() -> Path:
    raw = os.environ.get(ONNX_MODEL_PATH_FLAG, "").strip()
    return Path(raw) if raw else default_onnx_model_dir()


def onnx_max_length() -> int:
    raw = os.environ.get(ONNX_MAX_LENGTH_FLAG, "").strip()
    if not raw:
        return DEFAULT_ONNX_MAX_LENGTH
    try:
        value = int(raw)
    except ValueError as exc:
        raise SemanticBackendUnavailable(
            "AIOS_BGE_ONNX_MAX_LENGTH must be a positive integer"
        ) from exc
    if value < 1:
        raise SemanticBackendUnavailable(
            "AIOS_BGE_ONNX_MAX_LENGTH must be a positive integer"
        )
    return value


def onnx_checksum_sidecar(model_dir: Path) -> Path:
    return model_dir.resolve().parent / f"{model_dir.name}.sha256"


def resolve_onnx_checksum(model_dir: Path) -> str:
    raw = os.environ.get(ONNX_CHECKSUM_FLAG, "").strip()
    if not raw:
        sidecar = onnx_checksum_sidecar(model_dir)
        if not sidecar.is_file():
            raise SemanticBackendUnavailable("onnx_int8_checksum_missing")
        raw = sidecar.read_text(encoding="utf-8").strip().split()[0]
    if not raw.startswith("sha256:"):
        raw = f"sha256:{raw}"
    return raw


def _model_file(model_dir: Path) -> Path:
    for name in ("model_quantized.onnx", "model.onnx"):
        candidate = model_dir / name
        if candidate.is_file():
            return candidate
    raise SemanticBackendUnavailable("onnx_int8_model_file_missing")


def require_onnx_model_dir(model_dir: Path | None = None) -> Path:
    """Fail closed when the default ONNX fp32 model tree is unusable."""
    resolved = Path(model_dir) if model_dir is not None else resolve_onnx_model_path()
    problems: list[str] = []
    if not resolved.is_dir():
        problems.append(f"model directory is missing: {resolved}")
    else:
        try:
            _model_file(resolved)
        except SemanticBackendUnavailable:
            problems.append(
                f"model file is missing in {resolved} "
                "(expected model.onnx or model_quantized.onnx)"
            )
        try:
            resolve_onnx_checksum(resolved)
        except SemanticBackendUnavailable as exc:
            problems.append(f"checksum is unavailable for {resolved}: {exc}")
    if problems:
        detail = "; ".join(problems)
        raise SemanticBackendUnavailable(
            f"default ONNX fp32 model is unavailable: {detail}. {_onnx_override_hint()}"
        )
    return resolved


def lexical_weights_from_hidden(
    hidden: Any,
    input_ids: Sequence[int],
    weight: Any,
    bias: float,
    special_ids: set[int],
) -> dict[str, float]:
    """Match FlagEmbedding's inference lexical-weight loop on one sequence."""
    import numpy as np

    hidden_array = np.asarray(hidden, dtype=np.float32)
    weight_vector = np.asarray(weight, dtype=np.float32).reshape(-1)
    if hidden_array.ndim != 2 or hidden_array.shape[1] != weight_vector.shape[0]:
        raise SemanticBackendError("sparse head does not match the hidden width")
    if len(input_ids) != hidden_array.shape[0]:
        raise SemanticBackendError("sparse token weights and input ids differ in length")
    scores = np.maximum(hidden_array @ weight_vector + np.float32(bias), 0.0)
    result: dict[str, float] = {}
    for score, token_id in zip(scores.tolist(), input_ids):
        token = int(token_id)
        if token in special_ids or score <= 0.0:
            continue
        key = str(token)
        if score > result.get(key, 0.0):
            result[key] = float(score)
    return result


def _load_sparse_head(model_dir: Path) -> tuple[Any, float] | None:
    path = model_dir / "sparse_linear.npy"
    if not path.is_file():
        return None
    import numpy as np

    weight = np.load(path)
    bias_path = model_dir / "sparse_linear_bias.npy"
    bias = float(np.load(bias_path).reshape(-1)[0]) if bias_path.is_file() else 0.0
    return weight, bias


class OnnxInt8BgeM3Backend:
    """BGE-M3 dense+sparse adapter over one local ONNX Runtime session."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        revision: str,
        artifact_checksum: str = "",
        model_id: str = BGE_M3_MODEL_ID,
        dimension: int = BGE_M3_DIMENSION,
        batch_size: int = 8,
        max_length: int | None = None,
        intra_op_num_threads: int | None = None,
        enable_multivector: bool = False,
        session: Any = None,
        tokenizer: Any = None,
    ) -> None:
        del enable_multivector
        if not revision.strip():
            raise SemanticBackendUnavailable("a pinned BGE-M3 model revision is required")
        if dimension < 1:
            raise SemanticBackendUnavailable("BGE-M3 dimension must be positive")
        if batch_size < 1:
            raise ValueError("BGE-M3 batch_size must be positive")
        self._model_path = Path(model_path).resolve() if model_path is not None else resolve_onnx_model_path()
        self._max_length = onnx_max_length() if max_length is None else max_length
        if self._max_length < 1:
            raise ValueError("BGE-M3 max_length must be positive")
        checksum = artifact_checksum.strip() or resolve_onnx_checksum(self._model_path)
        if session is None:
            verified = verify_model_tree(self._model_path, checksum)
            self._session = self._open_session(intra_op_num_threads)
            self._tokenizer = self._open_tokenizer()
        else:
            verified = checksum
            self._session = session
            self._tokenizer = tokenizer
        self._batch_size = batch_size
        self._dimension = dimension
        self._sparse_head = _load_sparse_head(self._model_path)
        self._special_ids = self._special_token_ids()
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id,
            revision=revision,
            runtime="onnxruntime-int8",
            runtime_version=_onnxruntime_version(),
            dimension=dimension,
            normalized=True,
            artifact_checksum=verified,
            device="cpu",
        )
        self._capability = SemanticCapability(
            capability="embedding",
            available=True,
            backend="bge-m3-onnxruntime-int8",
            model=self._descriptor,
        )
        sparse_available = self._sparse_head is not None
        self._sparse_capability = SemanticCapability(
            capability="sparse_embedding",
            available=sparse_available,
            backend="bge-m3-onnxruntime-int8" if sparse_available else "disabled",
            reason="" if sparse_available else "onnx_int8_sparse_head_missing",
            model=self._descriptor if sparse_available else None,
        )
        self._multivector_descriptor = MultiVectorDescriptor(
            model_fingerprint=self._descriptor.fingerprint,
            dimension=dimension,
            max_tokens=self._max_length,
        )
        self._pending_sparse: dict[tuple[str, ...], tuple[SparseVector, ...]] = {}
        self._pending_queries: dict[str, tuple[tuple[float, ...], SparseVector]] = {}
        LOGGER.info(
            "bge_onnx_loaded threads=%s max_length=%s sparse=%s",
            intra_op_num_threads or os.cpu_count() or 1,
            self._max_length,
            sparse_available,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    @property
    def sparse_capability(self) -> SemanticCapability:
        return self._sparse_capability

    @property
    def multivector_capability(self) -> SemanticCapability:
        return SemanticCapability(
            capability="multivector_embedding",
            available=False,
            backend="disabled",
            reason="onnx_int8_colbert_not_exported",
            model=None,
        )

    @property
    def multivector_descriptor(self) -> MultiVectorDescriptor:
        self.multivector_capability.require()
        return self._multivector_descriptor

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        key = tuple(str(text) for text in texts)
        dense, sparse = self._encode(key)
        self._pending_sparse[key] = sparse
        return dense

    def embed_query(self, text: str) -> tuple[float, ...]:
        return self._query_representations(text)[0]

    def sparse_documents(self, texts: Sequence[str]) -> tuple[SparseVector, ...]:
        self.sparse_capability.require()
        key = tuple(str(text) for text in texts)
        cached = self._pending_sparse.pop(key, None)
        if cached is not None:
            return cached
        _dense, sparse = self._encode(key)
        return sparse

    def sparse_query(self, text: str) -> SparseVector:
        self.sparse_capability.require()
        return self._query_representations(text)[1]

    def _query_representations(self, text: str) -> tuple[tuple[float, ...], SparseVector]:
        key = str(text)
        cached = self._pending_queries.get(key)
        if cached is not None:
            return cached
        dense, sparse = self._encode((key,))
        representation = (dense[0], sparse[0])
        if len(self._pending_queries) >= 16:
            self._pending_queries.pop(next(iter(self._pending_queries)))
        self._pending_queries[key] = representation
        return representation

    def _encode(
        self,
        texts: Sequence[str],
    ) -> tuple[tuple[tuple[float, ...], ...], tuple[SparseVector, ...]]:
        prepared = tuple(str(text) for text in texts)
        if not prepared:
            return (), ()
        started = time.perf_counter()
        dense_rows: list[tuple[float, ...]] = []
        sparse_rows: list[SparseVector] = []
        try:
            for start in range(0, len(prepared), self._batch_size):
                batch = prepared[start:start + self._batch_size]
                hidden, input_ids = self._run_batch(batch)
                for row_index, ids in enumerate(input_ids):
                    dense_rows.append(
                        normalize_vector(hidden[row_index, 0], dimension=self._dimension)
                    )
                    sparse_rows.append(self._sparse_row(hidden[row_index], ids))
        except SemanticBackendError:
            raise
        except Exception as exc:
            raise SemanticBackendError("BGE-M3 ONNX embedding inference failed") from exc
        LOGGER.info(
            "bge_onnx_embed count=%s elapsed_ms=%.3f max_length=%s",
            len(prepared),
            (time.perf_counter() - started) * 1000.0,
            self._max_length,
        )
        return tuple(dense_rows), tuple(sparse_rows)

    def _sparse_row(self, hidden: Any, input_ids: Sequence[int]) -> SparseVector:
        if self._sparse_head is None:
            return {}
        weight, bias = self._sparse_head
        return normalize_sparse_vector(
            lexical_weights_from_hidden(
                hidden,
                input_ids,
                weight,
                bias,
                self._special_ids,
            )
        )

    def _run_batch(self, texts: Sequence[str]) -> tuple[Any, list[list[int]]]:
        import numpy as np

        if self._tokenizer is None:
            raise SemanticBackendError("BGE-M3 ONNX tokenizer is unavailable")
        encodings = self._tokenizer.encode_batch(list(texts))
        input_ids = [list(item.ids) for item in encodings]
        attention = [list(item.attention_mask) for item in encodings]
        feeds = {
            "input_ids": np.asarray(input_ids, dtype=np.int64),
            "attention_mask": np.asarray(attention, dtype=np.int64),
        }
        input_names = {item.name for item in self._session.get_inputs()}
        if "token_type_ids" in input_names:
            feeds["token_type_ids"] = np.zeros_like(feeds["input_ids"])
        outputs = self._session.run(None, {name: value for name, value in feeds.items() if name in input_names})
        hidden = _hidden_state(self._session, outputs)
        if hidden.ndim != 3:
            raise SemanticBackendError("BGE-M3 ONNX did not return token hidden states")
        return hidden, input_ids

    def _open_session(self, intra_op_num_threads: int | None) -> Any:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise SemanticBackendUnavailable(
                "onnxruntime is unavailable; install the retrieval-lab extra"
            ) from exc
        threads = intra_op_num_threads or os.cpu_count() or 1
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(threads)
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        try:
            return ort.InferenceSession(
                str(_model_file(self._model_path)),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
        except Exception as exc:
            raise SemanticBackendUnavailable("the pinned local BGE-M3 ONNX model failed to load") from exc

    def _open_tokenizer(self) -> Any:
        tokenizer_path = self._model_path / "tokenizer.json"
        if not tokenizer_path.is_file():
            raise SemanticBackendUnavailable("onnx_int8_tokenizer_missing")
        try:
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise SemanticBackendUnavailable("tokenizers is unavailable") from exc
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        pad_id = _pad_id(self._model_path)
        tokenizer.enable_truncation(max_length=self._max_length)
        tokenizer.enable_padding(
            direction="right",
            pad_id=pad_id,
            pad_token=_pad_token(self._model_path),
        )
        return tokenizer

    def _special_token_ids(self) -> set[int]:
        ids = {0, 1, 2, 3}
        tokenizer = self._tokenizer
        token_to_id = getattr(tokenizer, "token_to_id", None)
        if token_to_id is None:
            return ids
        for token in ("<s>", "</s>", "<pad>", "<unk>", "[CLS]", "[SEP]", "[PAD]", "[UNK]"):
            value = token_to_id(token)
            if value is not None:
                ids.add(int(value))
        return ids


def _hidden_state(session: Any, outputs: Sequence[Any]) -> Any:
    named = list(zip(session.get_outputs(), outputs))
    for output, value in named:
        if "last_hidden_state" in output.name or "token_embeddings" in output.name:
            return value
    if len(named) == 1:
        return named[0][1]
    raise SemanticBackendError("BGE-M3 ONNX did not return token hidden states")


def _pad_id(model_dir: Path) -> int:
    config = model_dir / "config.json"
    if not config.is_file():
        return 1
    import json

    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 1
    value = payload.get("pad_token_id", 1)
    return int(value) if isinstance(value, int) else 1


def _pad_token(model_dir: Path) -> str:
    path = model_dir / "special_tokens_map.json"
    if not path.is_file():
        return "<pad>"
    import json

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "<pad>"
    token = payload.get("pad_token", "<pad>")
    if isinstance(token, dict):
        token = token.get("content", "<pad>")
    return str(token or "<pad>")


def _onnxruntime_version() -> str:
    try:
        from importlib.metadata import version
        return version("onnxruntime")
    except Exception:
        return ""
