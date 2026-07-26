"""Local semantic backend contracts and FastEmbed ONNX adapters.

The module has no mandatory third-party imports. FastEmbed is loaded lazily so the
base lexical installation remains usable and testable without the ``rag-semantic``
extra. Corpus text and queries are processed only by the local backend instance.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import importlib.metadata
import json
import math
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence, runtime_checkable


class SemanticBackendError(RuntimeError):
    """Base error for local semantic backend failures."""


class SemanticBackendUnavailable(SemanticBackendError):
    """Raised when a requested local semantic capability is unavailable."""


@dataclass(frozen=True)
class SemanticModelDescriptor:
    """Immutable identity and vector contract for one local semantic model."""

    model_id: str
    dimension: int
    revision: str = ""
    runtime: str = "onnxruntime"
    runtime_version: str = ""
    distance: str = "cosine"
    normalized: bool = True
    cache_identity: str = ""

    def __post_init__(self) -> None:
        model_id = self.model_id.strip()
        if not model_id:
            raise ValueError("model_id is required")
        if self.dimension < 1:
            raise ValueError("dimension must be positive")
        if self.distance != "cosine":
            raise ValueError("only cosine distance is supported")
        object.__setattr__(self, "model_id", model_id)
        if not self.cache_identity:
            object.__setattr__(self, "cache_identity", self.fingerprint)

    @property
    def fingerprint(self) -> str:
        payload = {
            "dimension": self.dimension,
            "distance": self.distance,
            "model_id": self.model_id,
            "normalized": self.normalized,
            "revision": self.revision,
            "runtime": self.runtime,
            "runtime_version": self.runtime_version,
        }
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_safe_dict(self) -> dict[str, Any]:
        """Return model provenance without exposing cache paths or source text."""
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "runtime": self.runtime,
            "runtime_version": self.runtime_version,
            "dimension": self.dimension,
            "distance": self.distance,
            "normalized": self.normalized,
            "fingerprint": self.fingerprint,
            "cache_identity": self.cache_identity,
        }


@dataclass(frozen=True)
class SemanticCapability:
    """Inspectable availability state; unavailable never implies lexical fallback."""

    capability: str
    available: bool
    backend: str
    reason: str = ""
    model: SemanticModelDescriptor | None = None

    def require(self) -> None:
        if not self.available:
            reason = self.reason or f"{self.capability} backend is unavailable"
            raise SemanticBackendUnavailable(reason)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "available": self.available,
            "backend": self.backend,
            "reason": self.reason,
            "model": self.model.to_safe_dict() if self.model is not None else None,
        }


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Small mockable contract for local document and query embeddings."""

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        ...

    @property
    def capability(self) -> SemanticCapability:
        ...

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        ...

    def embed_query(self, text: str) -> tuple[float, ...]:
        ...


@runtime_checkable
class RerankerBackend(Protocol):
    """Small mockable contract for local query/document pair scoring."""

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        ...

    @property
    def capability(self) -> SemanticCapability:
        ...

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        ...


def normalize_vector(values: Iterable[float], *, dimension: int | None = None) -> tuple[float, ...]:
    """Validate and L2-normalize a vector for deterministic cosine storage."""
    vector = tuple(float(value) for value in values)
    if dimension is not None and len(vector) != dimension:
        raise SemanticBackendError(
            f"embedding dimension mismatch: expected {dimension}, received {len(vector)}"
        )
    if not vector or any(not math.isfinite(value) for value in vector):
        raise SemanticBackendError("embedding vector must contain finite values")
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude <= 0.0:
        raise SemanticBackendError("embedding vector magnitude must be positive")
    return tuple(value / magnitude for value in vector)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Return cosine similarity for normalized vectors with strict dimensions."""
    if len(left) != len(right) or not left:
        raise SemanticBackendError("cosine vectors must have equal positive dimensions")
    return float(sum(float(a) * float(b) for a, b in zip(left, right)))


class UnavailableEmbeddingBackend:
    """Explicit unavailable backend used for degraded lexical-only capability state."""

    def __init__(self, reason: str, descriptor: SemanticModelDescriptor) -> None:
        self._descriptor = descriptor
        self._capability = SemanticCapability(
            capability="embedding",
            available=False,
            backend="unavailable",
            reason=reason,
            model=descriptor,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        del texts
        self._capability.require()
        raise AssertionError("unreachable")

    def embed_query(self, text: str) -> tuple[float, ...]:
        del text
        self._capability.require()
        raise AssertionError("unreachable")


class UnavailableRerankerBackend:
    """Explicit unavailable backend for a requested local reranker."""

    def __init__(self, reason: str, descriptor: SemanticModelDescriptor) -> None:
        self._descriptor = descriptor
        self._capability = SemanticCapability(
            capability="reranker",
            available=False,
            backend="unavailable",
            reason=reason,
            model=descriptor,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        del pairs
        self._capability.require()
        raise AssertionError("unreachable")


class DeterministicEmbeddingBackend:
    """Dependency-free deterministic fake backend for persistence/retrieval tests."""

    def __init__(self, dimension: int = 16, *, model_id: str = "test/deterministic") -> None:
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id,
            revision="v1",
            runtime="deterministic-test",
            runtime_version="1",
            dimension=dimension,
            normalized=True,
        )
        self._capability = SemanticCapability(
            capability="embedding",
            available=True,
            backend="deterministic-test",
            model=self._descriptor,
        )
        self.document_call_count = 0
        self.query_call_count = 0
        self.embedded_document_count = 0

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def _embed(self, text: str) -> tuple[float, ...]:
        buckets = [0.0] * self._descriptor.dimension
        tokens = text.casefold().split()
        for token in tokens or [text.casefold()]:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset, byte in enumerate(digest):
                bucket = offset % self._descriptor.dimension
                buckets[bucket] += (float(byte) - 127.5) / 127.5
        if not any(buckets):
            buckets[0] = 1.0
        return normalize_vector(buckets, dimension=self._descriptor.dimension)

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        self.document_call_count += 1
        self.embedded_document_count += len(texts)
        return tuple(self._embed(text) for text in texts)

    def embed_query(self, text: str) -> tuple[float, ...]:
        self.query_call_count += 1
        return self._embed(text)


class DeterministicRerankerBackend:
    """Dependency-free deterministic fake pair scorer for Gate D tests."""

    def __init__(self, *, model_id: str = "test/deterministic-reranker") -> None:
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id,
            revision="v1",
            runtime="deterministic-test",
            runtime_version="1",
            dimension=1,
            normalized=False,
        )
        self._capability = SemanticCapability(
            capability="reranker",
            available=True,
            backend="deterministic-test",
            model=self._descriptor,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        scores = []
        for query, document in pairs:
            query_terms = set(query.casefold().split())
            document_terms = set(document.casefold().split())
            scores.append(len(query_terms & document_terms) / max(1, len(query_terms)))
        return tuple(scores)


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _supported_dimension(model_class: Any, model_id: str) -> int | None:
    for record in model_class.list_supported_models():
        if str(record.get("model", "")) == model_id:
            dimension = record.get("dim")
            return int(dimension) if dimension is not None else None
    return None


class FastEmbedEmbeddingBackend:
    """Lazy local ONNX embedding adapter backed by the optional FastEmbed extra."""

    def __init__(
        self,
        model_id: str = "BAAI/bge-small-en-v1.5",
        *,
        revision: str = "",
        dimension: int | None = None,
        cache_dir: str | Path | None = None,
        local_files_only: bool = True,
        threads: int | None = None,
    ) -> None:
        try:
            module = importlib.import_module("fastembed")
            model_class = module.TextEmbedding
        except (ImportError, AttributeError) as exc:
            raise SemanticBackendUnavailable(
                "FastEmbed is unavailable; install the 'rag-semantic' extra"
            ) from exc
        resolved_dimension = dimension or _supported_dimension(model_class, model_id)
        if resolved_dimension is None:
            raise SemanticBackendUnavailable(
                f"FastEmbed model dimension is unknown for {model_id!r}; provide dimension explicitly"
            )
        kwargs: dict[str, Any] = {
            "model_name": model_id,
            "local_files_only": local_files_only,
        }
        if cache_dir is not None:
            kwargs["cache_dir"] = str(Path(cache_dir))
        if threads is not None:
            kwargs["threads"] = threads
        try:
            self._model = model_class(**kwargs)
        except Exception as exc:
            raise SemanticBackendUnavailable(
                f"FastEmbed model {model_id!r} is not available in the local cache"
            ) from exc
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id,
            revision=revision,
            runtime="fastembed-onnx",
            runtime_version=_package_version("fastembed"),
            dimension=resolved_dimension,
            normalized=True,
        )
        self._capability = SemanticCapability(
            capability="embedding",
            available=True,
            backend="fastembed-onnx",
            model=self._descriptor,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        try:
            vectors = tuple(
                normalize_vector(vector, dimension=self._descriptor.dimension)
                for vector in self._model.embed(list(texts))
            )
        except SemanticBackendError:
            raise
        except Exception as exc:
            raise SemanticBackendError("FastEmbed embedding inference failed") from exc
        if len(vectors) != len(texts):
            raise SemanticBackendError("FastEmbed returned an unexpected document count")
        return vectors

    def embed_query(self, text: str) -> tuple[float, ...]:
        vectors = self.embed_documents([text])
        if len(vectors) != 1:
            raise SemanticBackendError("FastEmbed returned an unexpected query count")
        return vectors[0]


class FastEmbedRerankerBackend:
    """Lazy local ONNX cross-encoder adapter backed by FastEmbed."""

    def __init__(
        self,
        model_id: str = "Xenova/ms-marco-MiniLM-L-6-v2",
        *,
        revision: str = "",
        cache_dir: str | Path | None = None,
        local_files_only: bool = True,
        threads: int | None = None,
    ) -> None:
        try:
            module = importlib.import_module("fastembed.rerank.cross_encoder")
            model_class = module.TextCrossEncoder
        except (ImportError, AttributeError) as exc:
            raise SemanticBackendUnavailable(
                "FastEmbed reranker is unavailable; install the 'rag-semantic' extra"
            ) from exc
        kwargs: dict[str, Any] = {
            "model_name": model_id,
            "local_files_only": local_files_only,
        }
        if cache_dir is not None:
            kwargs["cache_dir"] = str(Path(cache_dir))
        if threads is not None:
            kwargs["threads"] = threads
        try:
            self._model = model_class(**kwargs)
        except Exception as exc:
            raise SemanticBackendUnavailable(
                f"FastEmbed reranker {model_id!r} is not available in the local cache"
            ) from exc
        self._descriptor = SemanticModelDescriptor(
            model_id=model_id,
            revision=revision,
            runtime="fastembed-onnx-cross-encoder",
            runtime_version=_package_version("fastembed"),
            dimension=1,
            normalized=False,
        )
        self._capability = SemanticCapability(
            capability="reranker",
            available=True,
            backend="fastembed-onnx-cross-encoder",
            model=self._descriptor,
        )

    @property
    def descriptor(self) -> SemanticModelDescriptor:
        return self._descriptor

    @property
    def capability(self) -> SemanticCapability:
        return self._capability

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        scores = []
        try:
            for query, document in pairs:
                values = tuple(float(value) for value in self._model.rerank(query, [document]))
                if len(values) != 1 or not math.isfinite(values[0]):
                    raise SemanticBackendError("FastEmbed reranker returned an invalid score")
                scores.append(values[0])
        except SemanticBackendError:
            raise
        except Exception as exc:
            raise SemanticBackendError("FastEmbed reranker inference failed") from exc
        return tuple(scores)


def unavailable_embedding_backend(
    model_id: str,
    *,
    revision: str = "",
    dimension: int = 384,
    reason: str,
) -> UnavailableEmbeddingBackend:
    """Create a descriptor-preserving unavailable backend for safe inspection."""
    descriptor = SemanticModelDescriptor(
        model_id=model_id,
        revision=revision,
        runtime="fastembed-onnx",
        runtime_version=_package_version("fastembed"),
        dimension=dimension,
        normalized=True,
    )
    return UnavailableEmbeddingBackend(reason, descriptor)