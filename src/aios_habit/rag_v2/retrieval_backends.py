"""Gate H retrieval-lab adapters built on the official FlagEmbedding APIs.

The optional dependency is imported lazily. Benchmark profiles must pass a local
model directory plus a verified SHA-256 tree checksum; adapters never download a
model or silently substitute a weaker backend.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
import math
import os
from pathlib import Path
from typing import Any, Iterator, Sequence

from .semantic import (
    EmbeddingBackend,
    FastEmbedRerankerBackend,
    MultiVector,
    MultiVectorDescriptor,
    RerankerBackend,
    SemanticBackendError,
    SemanticBackendUnavailable,
    SemanticCapability,
    SemanticModelDescriptor,
    SparseVector,
    normalize_multivector,
    normalize_sparse_vector,
    normalize_vector,
)

BGE_M3_MODEL_ID = "BAAI/bge-m3"
BGE_M3_DIMENSION = 1024
BGE_M3_RERANKER_MODEL_ID = "BAAI/bge-reranker-v2-m3"


def sha256_model_tree(model_path: str | Path) -> str:
    """Hash all regular files in a local model tree with stable relative names."""
    root = Path(model_path).resolve()
    if not root.is_dir():
        raise SemanticBackendUnavailable(f"local model directory does not exist: {root.name}")
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise SemanticBackendUnavailable(f"local model directory is empty: {root.name}")
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def verify_model_tree(model_path: str | Path, expected_checksum: str) -> str:
    """Fail closed unless a model tree exactly matches its pinned checksum."""
    digest_text = expected_checksum.removeprefix("sha256:")
    if (
        not expected_checksum.startswith("sha256:")
        or len(digest_text) != 64
        or any(character not in "0123456789abcdefABCDEF" for character in digest_text)
    ):
        raise SemanticBackendUnavailable(
            "a pinned model checksum in sha256:<64 hex characters> form is required"
        )
    actual = sha256_model_tree(model_path)
    if actual.casefold() != expected_checksum.casefold():
        raise SemanticBackendUnavailable(
            f"local model checksum mismatch: expected {expected_checksum}, received {actual}"
        )
    return actual


@contextmanager
def _offline_huggingface() -> Iterator[None]:
    """Prevent accidental Hub access while constructing local benchmark models."""
    keys = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    previous = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ[key] = "1"
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _flag_embedding_version() -> str:
    try:
        from importlib.metadata import version
        return version("FlagEmbedding")
    except Exception:
        return ""


class BgeM3Backend(EmbeddingBackend):
    """Official BGE-M3 dense+sparse+ColBERT adapter over one resident model."""

    def __init__(
        self, model_path: str | Path, *, revision: str, artifact_checksum: str,
        model_id: str = BGE_M3_MODEL_ID, dimension: int = BGE_M3_DIMENSION,
        device: str = "cpu", use_fp16: bool = False,
        batch_size: int = 12, max_length: int = 8192,
        enable_multivector: bool = False,
    ) -> None:
        if not revision.strip():
            raise SemanticBackendUnavailable("a pinned BGE-M3 model revision is required")
        if dimension < 1:
            raise SemanticBackendUnavailable("BGE-M3 dimension must be positive")
        if batch_size < 1 or max_length < 1:
            raise ValueError("BGE-M3 batch_size and max_length must be positive")
        self._model_path = Path(model_path).resolve()
        verified_checksum = verify_model_tree(self._model_path, artifact_checksum)
        try:
            module = importlib.import_module("FlagEmbedding")
            model_class = module.BGEM3FlagModel
        except (ImportError, AttributeError) as exc:
            raise SemanticBackendUnavailable(
                "FlagEmbedding with BGEM3FlagModel is unavailable; install the retrieval-lab extra"
            ) from exc
        try:
            with _offline_huggingface():
                self._model = model_class(
                    str(self._model_path), use_fp16=use_fp16, devices=device,
                    trust_remote_code=False,
                )
        except Exception as exc:
            raise SemanticBackendUnavailable("the pinned local BGE-M3 model failed to load") from exc
        self._batch_size = batch_size
        self._max_length = max_length
        self._enable_multivector = bool(enable_multivector)
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id, revision=revision, runtime="flagembedding-pytorch",
            runtime_version=_flag_embedding_version(), dimension=dimension,
            normalized=True, artifact_checksum=verified_checksum, device=device,
        )
        self._capability = SemanticCapability(
            capability="embedding", available=True, backend="bge-m3-flagembedding",
            model=self._descriptor,
        )
        self._sparse_capability = SemanticCapability(
            capability="sparse_embedding", available=True, backend="bge-m3-flagembedding",
            model=self._descriptor,
        )
        self._multivector_descriptor = MultiVectorDescriptor(
            model_fingerprint=self._descriptor.fingerprint,
            dimension=dimension,
            max_tokens=max_length,
        )
        self._pending_sparse: dict[tuple[str, ...], tuple[SparseVector, ...]] = {}
        self._pending_multivector: dict[tuple[str, ...], tuple[MultiVector, ...]] = {}
        self._pending_queries: dict[
            str, tuple[tuple[float, ...], SparseVector, MultiVector | None]
        ] = {}

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
        enabled = bool(getattr(self, "_enable_multivector", False))
        return SemanticCapability(
            capability="multivector_embedding",
            available=enabled,
            backend="bge-m3-colbert-flagembedding" if enabled else "disabled",
            reason="" if enabled else "multivector_not_enabled",
            model=self._descriptor if enabled else None,
        )

    @property
    def multivector_descriptor(self) -> MultiVectorDescriptor:
        self.multivector_capability.require()
        return self._multivector_descriptor

    def _encode(
        self,
        texts: Sequence[str],
    ) -> tuple[tuple[tuple[float, ...], ...], tuple[SparseVector, ...], tuple[MultiVector, ...]]:
        prepared = tuple(str(text) for text in texts)
        if not prepared:
            return (), (), ()
        multivector_enabled = bool(getattr(self, "_enable_multivector", False))
        try:
            output = self._model.encode(
                list(prepared), batch_size=self._batch_size, max_length=self._max_length,
                return_dense=True, return_sparse=True,
                return_colbert_vecs=multivector_enabled,
            )
        except Exception as exc:
            raise SemanticBackendError("BGE-M3 embedding inference failed") from exc
        if not isinstance(output, dict):
            raise SemanticBackendError("BGE-M3 returned an invalid embedding payload")
        dense_values = output.get("dense_vecs")
        sparse_values = output.get("lexical_weights")
        if dense_values is None or sparse_values is None:
            raise SemanticBackendError("BGE-M3 did not return dense and learned sparse outputs")
        dense = tuple(
            normalize_vector(vector, dimension=self._descriptor.dimension)
            for vector in dense_values
        )
        sparse = tuple(normalize_sparse_vector(vector) for vector in sparse_values)
        if len(dense) != len(prepared) or len(sparse) != len(prepared):
            raise SemanticBackendError("BGE-M3 returned an unexpected representation count")

        multivectors: tuple[MultiVector, ...] = ()
        if multivector_enabled:
            colbert_values = output.get("colbert_vecs")
            if colbert_values is None:
                raise SemanticBackendError("BGE-M3 did not return ColBERT vectors")
            descriptor = self._multivector_descriptor
            multivectors = tuple(
                normalize_multivector(
                    vectors,
                    dimension=descriptor.dimension,
                    max_tokens=descriptor.max_tokens,
                )
                for vectors in colbert_values
            )
            if len(multivectors) != len(prepared):
                raise SemanticBackendError("BGE-M3 returned an unexpected ColBERT count")
        return dense, sparse, multivectors

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        key = tuple(str(text) for text in texts)
        dense, sparse, multivectors = self._encode(key)
        self._pending_sparse[key] = sparse
        if bool(getattr(self, "_enable_multivector", False)):
            self._pending_multivector[key] = multivectors
        return dense

    def sparse_documents(self, texts: Sequence[str]) -> tuple[SparseVector, ...]:
        key = tuple(str(text) for text in texts)
        cached = self._pending_sparse.pop(key, None)
        if cached is not None:
            return cached
        _dense, sparse, multivectors = self._encode(key)
        if bool(getattr(self, "_enable_multivector", False)):
            self._pending_multivector[key] = multivectors
        return sparse

    def multivector_documents(self, texts: Sequence[str]) -> tuple[MultiVector, ...]:
        self.multivector_capability.require()
        key = tuple(str(text) for text in texts)
        cached = self._pending_multivector.pop(key, None)
        if cached is not None:
            return cached
        _dense, sparse, multivectors = self._encode(key)
        self._pending_sparse[key] = sparse
        return multivectors

    def _query_representations(
        self,
        text: str,
    ) -> tuple[tuple[float, ...], SparseVector, MultiVector | None]:
        key = str(text)
        pending = getattr(self, "_pending_queries", None)
        if pending is None:
            pending = {}
            self._pending_queries = pending
        cached = pending.get(key)
        if cached is not None:
            return cached
        dense, sparse, multivectors = self._encode((key,))
        representation = (dense[0], sparse[0], multivectors[0] if multivectors else None)
        if len(pending) >= 16:
            pending.pop(next(iter(pending)))
        pending[key] = representation
        return representation

    def embed_query(self, text: str) -> tuple[float, ...]:
        return self._query_representations(text)[0]

    def sparse_query(self, text: str) -> SparseVector:
        return self._query_representations(text)[1]

    def multivector_query(self, text: str) -> MultiVector:
        self.multivector_capability.require()
        multivector = self._query_representations(text)[2]
        if multivector is None:
            raise SemanticBackendError("BGE-M3 query ColBERT vectors are unavailable")
        return multivector


class CrossEncoderRerankBackend(RerankerBackend):
    """Official multilingual BGE cross-encoder over a pinned local model tree."""

    def __init__(
        self, model_path: str | Path, *, revision: str, artifact_checksum: str,
        model_id: str = BGE_M3_RERANKER_MODEL_ID, device: str = "cpu",
        use_fp16: bool = False, batch_size: int = 16, max_length: int = 1024,
    ) -> None:
        if not revision.strip():
            raise SemanticBackendUnavailable("a pinned reranker model revision is required")
        self._model_path = Path(model_path).resolve()
        verified_checksum = verify_model_tree(self._model_path, artifact_checksum)
        try:
            module = importlib.import_module("FlagEmbedding")
            model_class = module.FlagReranker
        except (ImportError, AttributeError) as exc:
            raise SemanticBackendUnavailable(
                "FlagEmbedding with FlagReranker is unavailable; install the retrieval-lab extra"
            ) from exc
        try:
            with _offline_huggingface():
                self._model = model_class(
                    str(self._model_path), use_fp16=use_fp16, devices=device,
                    trust_remote_code=False,
                )
        except Exception as exc:
            raise SemanticBackendUnavailable("the pinned local BGE reranker failed to load") from exc
        self._batch_size = batch_size
        self._max_length = max_length
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id, revision=revision,
            runtime="flagembedding-pytorch-cross-encoder",
            runtime_version=_flag_embedding_version(), dimension=1, normalized=False,
            artifact_checksum=verified_checksum, device=device,
        )
        self._capability = SemanticCapability(
            capability="reranker", available=True,
            backend="bge-reranker-v2-m3-flagembedding", model=self._descriptor,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        if not pairs:
            return ()
        try:
            values = self._model.compute_score(
                [list(pair) for pair in pairs], batch_size=self._batch_size,
                max_length=self._max_length, normalize=False,
            )
            if isinstance(values, (float, int)):
                values = [values]
            scores = tuple(float(value) for value in values)
        except Exception as exc:
            raise SemanticBackendError("BGE multilingual reranker inference failed") from exc
        if len(scores) != len(pairs) or any(not math.isfinite(score) for score in scores):
            raise SemanticBackendError("BGE multilingual reranker returned invalid scores")
        return scores
