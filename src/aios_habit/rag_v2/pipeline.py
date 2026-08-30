"""Dev-only orchestration for the independent, local-first RAG v2 pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Tuple

from .adapters import ConversionContext
from .chunking import StructureAwareChunker
from .evidence import EvidencePack, EvidencePackConfig, build_evidence_pack
from .index import (
    HybridRankingConfig,
    LocalChunkIndex,
    SearchOptions,
    SearchResponse,
    fuse_ranked_channels,
)
from .query_planning import RetrievalQueryPlan, build_query_plan, coerce_query_plan
from .registry import ConverterRegistry
from .schema import ExtractionStatus
from .semantic import (
    EmbeddingBackend,
    FastEmbedEmbeddingBackend,
    FastEmbedRerankerBackend,
    RerankerBackend,
    SemanticBackendError,
    SemanticBackendUnavailable,
    unavailable_embedding_backend,
)
from .retrieval_backends import BgeM3Backend, CrossEncoderRerankBackend
from .adaptive_retrieval import CircuitBreaker
from .synthesis import (

    LocalSynthesisResult,
    ProviderSynthesisProvider,
    synthesize_evidence,
    synthesize_with_provider,
)

_CANONICAL_PRIVACY_LABELS = frozenset({
    "local_only", "confidential", "cloud_safe", "public",
})
INDEX_BUILD_SCHEMA_VERSION = 1
_INDEX_BUILD_IMPLEMENTATION_FILES = (
    "adapters.py",
    "chunking.py",
    "converters.py",
    "registry.py",
    "schema.py",
)
_BGE_SPARSE_PROFILES = frozenset({
    "bge_m3_hybrid",
    "bge_m3_multivector",
    "bge_m3_hybrid_rerank",
    "bge_m3_hybrid_rerank_expand",
})


def _index_build_implementation_fingerprint() -> str:
    """Fingerprint only code that can change extracted chunks or their identity."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in _INDEX_BUILD_IMPLEMENTATION_FILES:
        path = root / name
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _stable_document_id(path: Path) -> str:
    normalized = str(path.resolve()).replace("\\", "/").casefold()
    return f"doc-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class RagV2DevConfig:
    """Local runtime configuration. Network and provider use are unsupported here."""

    runtime_root: Path | str = Path("local_runs/rag_v2_dev")
    index_filename: str = "rag_v2_dev.sqlite"
    max_chunk_chars: int = 1200
    retrieval_limit: int = 15
    candidate_limit: int = 100
    dense_candidate_limit: int = 100
    per_document_limit: int = 5
    retrieval_profile: str = "lexical"
    embedding_model_id: str = "BAAI/bge-small-en-v1.5"
    embedding_model_revision: str = ""
    embedding_dimension: int = 384
    embedding_cache_dir: Path | str | None = None
    reranker_model_id: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    reranker_model_revision: str = ""
    rrf_k: int = 60
    lexical_channel_weight: float = 1.0
    dense_channel_weight: float = 1.0
    sparse_channel_weight: float = 1.0
    rerank_limit: int = 30
    context_neighbor_window: int = 2
    context_parent_limit: int = 1
    strict_semantic: bool = False
    bge_m3_model_path: Path | str | None = None
    bge_m3_model_revision: str = ""
    bge_m3_model_checksum: str = ""
    bge_m3_dimension: int = 1024
    bge_m3_batch_size: int = 8
    bge_m3_max_length: int = 2048
    bge_m3_use_fp16: bool = False
    bge_reranker_model_path: Path | str | None = None
    bge_reranker_model_revision: str = ""
    bge_reranker_model_checksum: str = ""
    retrieval_device: str = "cpu"
    allowed_privacy_labels: Tuple[str, ...] = (
        "local_only", "confidential", "cloud_safe", "public",
    )
    enable_network: bool = False
    enable_provider_synthesis: bool = False
    sqlite_check_same_thread: bool = True
    ensure_embeddings_on_open: bool = True
    index_read_only: bool = False

    def __post_init__(self) -> None:
        root = Path(self.runtime_root)
        object.__setattr__(self, "runtime_root", root)
        if root == Path("."):
            raise ValueError("runtime_root must be a dedicated directory")
        if Path(self.index_filename).name != self.index_filename:
            raise ValueError("index_filename must be a file name")
        if self.max_chunk_chars < 80:
            raise ValueError("max_chunk_chars must be at least 80")
        if (
            self.retrieval_limit < 1
            or self.candidate_limit < 1
            or self.dense_candidate_limit < 1
            or self.per_document_limit < 1
            or self.rerank_limit < 1
        ):
            raise ValueError("retrieval limits must be positive")
        valid_profiles = {
            "lexical", "hybrid", "hybrid_rerank", "lexical_baseline",
            "bge_m3_dense", "bge_m3_hybrid", "bge_m3_multivector",
            "bge_m3_hybrid_rerank", "bge_m3_hybrid_rerank_expand",
        }
        if self.retrieval_profile not in valid_profiles:
            raise ValueError(f"retrieval_profile must be one of {sorted(valid_profiles)}")
        if not self.embedding_model_id.strip():
            raise ValueError("embedding_model_id is required")
        if not self.reranker_model_id.strip():
            raise ValueError("reranker_model_id is required")
        if self.embedding_dimension < 1 or self.bge_m3_dimension < 1:
            raise ValueError("embedding dimensions must be positive")
        if self.bge_m3_batch_size < 1:
            raise ValueError("bge_m3_batch_size must be positive")
        if self.bge_m3_max_length < 1:
            raise ValueError("bge_m3_max_length must be positive")
        if self.rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        if self.context_neighbor_window < 0 or self.context_parent_limit < 0:
            raise ValueError("context expansion limits must be non-negative")
        if (
            self.lexical_channel_weight <= 0.0
            or self.dense_channel_weight <= 0.0
            or self.sparse_channel_weight <= 0.0
        ):
            raise ValueError("retrieval channel weights must be positive")
        cache_dir = self.embedding_cache_dir
        if cache_dir is not None:
            object.__setattr__(self, "embedding_cache_dir", Path(cache_dir))
        for attribute in ("bge_m3_model_path", "bge_reranker_model_path"):
            value = getattr(self, attribute)
            if value is not None:
                object.__setattr__(self, attribute, Path(value))
        labels = tuple(dict.fromkeys(self.allowed_privacy_labels))
        if not labels or any(label not in _CANONICAL_PRIVACY_LABELS for label in labels):
            raise ValueError("allowed_privacy_labels must use canonical labels")
        object.__setattr__(self, "allowed_privacy_labels", labels)
        if self.enable_network or self.enable_provider_synthesis:
            raise ValueError("Dev pipeline is local-only; provider synthesis is a separate gate")
        if self.index_read_only and self.ensure_embeddings_on_open:
            raise ValueError("index_read_only requires ensure_embeddings_on_open=False")

    @property
    def index_path(self) -> Path:
        return Path(self.runtime_root) / self.index_filename

    def index_build_compatibility(self) -> dict[str, Any]:
        """Return settings that can change persisted chunks or embeddings.

        Retrieval limits, fusion weights, reranking, context expansion, synthesis,
        and scoring are intentionally excluded so those algorithms can evolve while
        reusing a compatible expensive index.
        """
        semantic_required = self.retrieval_profile not in {"lexical", "lexical_baseline"}
        sparse_required = self.retrieval_profile in _BGE_SPARSE_PROFILES
        multivector_required = self.retrieval_profile == "bge_m3_multivector"
        payload: dict[str, Any] = {
            "schema_version": INDEX_BUILD_SCHEMA_VERSION,
            "implementation_fingerprint": _index_build_implementation_fingerprint(),
            "max_chunk_chars": self.max_chunk_chars,
            "allowed_privacy_labels": list(self.allowed_privacy_labels),
            "semantic_required": semantic_required,
            "sparse_required": sparse_required,
            "multivector_required": multivector_required,
        }
        if semantic_required:
            if _is_retrieval_lab_profile(self.retrieval_profile):
                payload["embedding_model"] = {
                    "kind": "bge_m3",
                    "model_path": str(Path(self.bge_m3_model_path).resolve()) if self.bge_m3_model_path else "",
                    "revision": self.bge_m3_model_revision,
                    "artifact_checksum": self.bge_m3_model_checksum,
                    "dimension": self.bge_m3_dimension,
                    "device": self.retrieval_device,
                    "multivector_schema_version": 1 if multivector_required else 0,
                }
            else:
                payload["embedding_model"] = {
                    "kind": "fastembed",
                    "model_id": self.embedding_model_id,
                    "revision": self.embedding_model_revision,
                    "dimension": self.embedding_dimension,
                }
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return {**payload, "compatibility_hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest()}


@dataclass(frozen=True)
class SourceSpec:
    """Explicit source selection and privacy policy for one local document."""

    path: Path | str
    source_id: str = ""
    document_id: str = ""
    privacy_labels: Tuple[str, ...] = ("local_only",)
    enabled: bool = True
    owner_consent: bool = False
    language_hints: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        path = Path(self.path).resolve()
        labels = tuple(dict.fromkeys(self.privacy_labels))
        if not labels or any(label not in _CANONICAL_PRIVACY_LABELS for label in labels):
            raise ValueError("source privacy_labels must use canonical labels")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "privacy_labels", labels)
        object.__setattr__(self, "language_hints", tuple(self.language_hints))
        if not self.document_id:
            object.__setattr__(self, "document_id", _stable_document_id(path))


@dataclass(frozen=True)
class IngestionItemReport:
    document_id: str
    source_name: str
    status: str
    source_fingerprint: str = ""
    element_count: int = 0
    chunk_count: int = 0
    warning_codes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RagV2IngestionReport:
    items: Tuple[IngestionItemReport, ...]
    converted_count: int
    skipped_count: int
    failed_count: int
    disabled_count: int
    indexed_chunk_count: int
    created_at: str
    unsupported_count: int = 0
    empty_count: int = 0

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RagV2QueryResult:
    query_plan: RetrievalQueryPlan
    search_response: SearchResponse
    evidence_pack: EvidencePack
    synthesis_result: LocalSynthesisResult
    route: str = "local_retrieval_evidence"
    provider_used: bool = False
    reranker_requested: bool = False
    reranker_applied: bool = False
    effective_path: str = "hybrid"
    degraded: bool = False
    degraded_reason: str = ""
    policy_version: str = "adaptive-reranking-v1"


def _is_retrieval_lab_profile(profile: str) -> bool:
    return profile.startswith("bge_m3_")


def _resolve_embedding_backend(
    config: RagV2DevConfig,
    backend: Optional[EmbeddingBackend],
) -> Optional[EmbeddingBackend]:
    """Resolve a semantic backend without network acquisition or silent fake scores."""
    if backend is not None:
        resolved = backend
    elif config.retrieval_profile in {"lexical", "lexical_baseline"}:
        return None
    elif _is_retrieval_lab_profile(config.retrieval_profile):
        if config.bge_m3_model_path is None:
            raise SemanticBackendUnavailable("BGE-M3 profile requires bge_m3_model_path")
        if not config.bge_m3_model_revision.strip():
            raise SemanticBackendUnavailable("BGE-M3 profile requires a pinned model revision")
        if not config.bge_m3_model_checksum.strip():
            raise SemanticBackendUnavailable("BGE-M3 profile requires bge_m3_model_checksum")
        resolved = BgeM3Backend(
            model_path=config.bge_m3_model_path,
            revision=config.bge_m3_model_revision,
            artifact_checksum=config.bge_m3_model_checksum,
            dimension=config.bge_m3_dimension,
            device=config.retrieval_device,
            batch_size=config.bge_m3_batch_size,
            max_length=config.bge_m3_max_length,
            use_fp16=config.bge_m3_use_fp16,
            enable_multivector=config.retrieval_profile == "bge_m3_multivector",
        )
    else:
        try:
            resolved = FastEmbedEmbeddingBackend(
                model_id=config.embedding_model_id,
                revision=config.embedding_model_revision,
                dimension=config.embedding_dimension,
                cache_dir=config.embedding_cache_dir,
                local_files_only=True,
            )
        except SemanticBackendUnavailable as exc:
            resolved = unavailable_embedding_backend(
                config.embedding_model_id,
                revision=config.embedding_model_revision,
                dimension=config.embedding_dimension,
                reason=str(exc),
            )
    if config.strict_semantic or _is_retrieval_lab_profile(config.retrieval_profile):
        resolved.capability.require()
    return resolved


def _resolve_reranker_backend(
    config: RagV2DevConfig,
    backend: Optional[RerankerBackend],
) -> tuple[Optional[RerankerBackend], str]:
    """Resolve reranking only for its requested profile and preserve failure reason."""
    rerank_profiles = {
        "hybrid_rerank",
        "bge_m3_hybrid_rerank",
        "bge_m3_hybrid_rerank_expand",
    }
    if backend is not None:
        resolved = backend
    elif config.retrieval_profile in {
        "bge_m3_hybrid_rerank",
        "bge_m3_hybrid_rerank_expand",
    } or (config.retrieval_profile == "bge_m3_hybrid" and config.bge_reranker_model_path is not None):
        if config.bge_reranker_model_path is None:
            if config.retrieval_profile == "bge_m3_hybrid":
                return None, ""
            raise SemanticBackendUnavailable(
                "BGE reranker profile requires bge_reranker_model_path"
            )
        if not config.bge_reranker_model_revision.strip():
            raise SemanticBackendUnavailable(
                "BGE reranker profile requires a pinned model revision"
            )
        if not config.bge_reranker_model_checksum.strip():
            raise SemanticBackendUnavailable(
                "BGE reranker profile requires bge_reranker_model_checksum"
            )
        resolved = CrossEncoderRerankBackend(
            model_path=config.bge_reranker_model_path,
            revision=config.bge_reranker_model_revision,
            artifact_checksum=config.bge_reranker_model_checksum,
            device=config.retrieval_device,
        )
    elif config.retrieval_profile in rerank_profiles:
        try:
            resolved = FastEmbedRerankerBackend(
                model_id=config.reranker_model_id,
                revision=config.reranker_model_revision,
                cache_dir=config.embedding_cache_dir,
                local_files_only=True,
            )
        except SemanticBackendUnavailable as exc:
            if config.strict_semantic:
                raise
            return None, str(exc)
    else:
        return None, ""
    if not resolved.capability.available:
        if config.strict_semantic or _is_retrieval_lab_profile(config.retrieval_profile):
            resolved.capability.require()
        return resolved, resolved.capability.reason or "reranker_backend_unavailable"
    return resolved, ""



class RagV2DevPipeline:
    """Compose existing RAG v2 primitives without touching Workspace Chat."""

    def __init__(
        self,
        config: Optional[RagV2DevConfig] = None,
        *,
        registry: Optional[ConverterRegistry] = None,
        chunker: Optional[StructureAwareChunker] = None,
        index: Optional[LocalChunkIndex] = None,
        embedding_backend: Optional[EmbeddingBackend] = None,
        reranker_backend: Optional[RerankerBackend] = None,
        synthesis_provider: Optional[ProviderSynthesisProvider] = None,
    ) -> None:
        self.config = config or RagV2DevConfig()
        self.synthesis_provider = synthesis_provider
        if self.config.index_read_only:
            if not self.config.index_path.is_file():
                raise FileNotFoundError(f"read-only index does not exist: {self.config.index_path}")
        else:
            Path(self.config.runtime_root).mkdir(parents=True, exist_ok=True)
        self.registry = registry or ConverterRegistry()
        self.chunker = chunker or StructureAwareChunker(self.config.max_chunk_chars)
        self.embedding_backend = _resolve_embedding_backend(self.config, embedding_backend)
        self.reranker_backend, reranker_reason = _resolve_reranker_backend(
            self.config, reranker_backend
        )
        self.index = index or LocalChunkIndex(
            self.config.index_path,
            embedding_backend=self.embedding_backend,
            sparse_backend=(
                self.embedding_backend
                if self.config.retrieval_profile in _BGE_SPARSE_PROFILES
                else None
            ),
            sqlite_check_same_thread=self.config.sqlite_check_same_thread,
            ensure_embeddings_on_open=self.config.ensure_embeddings_on_open,
            read_only=self.config.index_read_only,
        )
        self._owns_index = index is None
        capability = self.index.semantic_capability
        retrieval_lab = _is_retrieval_lab_profile(self.config.retrieval_profile)
        if (self.config.strict_semantic or retrieval_lab) and self.config.retrieval_profile not in {
            "lexical", "lexical_baseline",
        }:
            if capability is None:
                raise SemanticBackendUnavailable(
                    "strict semantic profile requires an embedding-enabled LocalChunkIndex"
                )
            capability.require()
        profile_aliases = {
            "lexical_baseline": "lexical",
            "bge_m3_dense": "dense",
            "bge_m3_hybrid": "hybrid",
            "bge_m3_multivector": "hybrid_multivector",
            "bge_m3_hybrid_rerank": "hybrid_rerank",
            "bge_m3_hybrid_rerank_expand": "hybrid_rerank_expand",
        }
        self._effective_retrieval_profile = profile_aliases.get(
            self.config.retrieval_profile, self.config.retrieval_profile
        )
        self._degraded_reason = ""
        if retrieval_lab and (capability is None or not capability.available):
            raise SemanticBackendUnavailable(
                capability.reason if capability is not None
                else "embedding_backend_not_configured"
            )
        if not retrieval_lab and self.config.retrieval_profile not in {"lexical", "lexical_baseline"} and (
            capability is None or not capability.available
        ):
            self._effective_retrieval_profile = "lexical"
            self._degraded_reason = (
                capability.reason if capability is not None
                else "embedding_backend_not_configured"
            )
        elif not retrieval_lab and self.config.retrieval_profile == "hybrid_rerank" and reranker_reason:
            self._effective_retrieval_profile = "hybrid"
            self._degraded_reason = reranker_reason
        self.circuit_breaker = CircuitBreaker()

    def ingest(self, sources: Iterable[SourceSpec]) -> RagV2IngestionReport:

        items = []
        for source in sources:
            if not source.enabled:
                items.append(IngestionItemReport(
                    document_id=source.document_id,
                    source_name=source.path.name,
                    status="disabled",
                ))
                continue
            if not source.path.is_file():
                items.append(IngestionItemReport(
                    document_id=source.document_id,
                    source_name=source.path.name,
                    status="failed",
                    warning_codes=("source_unavailable",),
                ))
                continue

            fingerprint = _file_fingerprint(source.path)
            current = self.index.document_state(source.document_id)
            if current["chunk_count"] and current["source_fingerprint"] == fingerprint:
                items.append(IngestionItemReport(
                    document_id=source.document_id,
                    source_name=source.path.name,
                    status="unchanged",
                    source_fingerprint=fingerprint,
                    chunk_count=int(current["chunk_count"]),
                ))
                continue

            context = ConversionContext(
                source_id=source.source_id,
                document_id=source.document_id,
                privacy_labels=source.privacy_labels,
                owner_consent=source.owner_consent,
                cloud_allowed=source.owner_consent and all(
                    label in {"cloud_safe", "public"} for label in source.privacy_labels
                ),
                source_fingerprint=fingerprint,
                language_hints=list(source.language_hints),
                fail_soft=True,
            )
            elements = self.registry.convert_document(str(source.path), context)
            failed = [item for item in elements if item.extraction_status in {
                ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED,
            }]
            usable = [item for item in elements if item.extraction_status not in {
                ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED,
            }]
            if not usable:
                unsupported = bool(elements) and all(
                    item.extraction_status == ExtractionStatus.UNSUPPORTED
                    for item in elements
                )
                items.append(IngestionItemReport(
                    document_id=source.document_id,
                    source_name=source.path.name,
                    status="unsupported" if unsupported else "failed",
                    source_fingerprint=fingerprint,
                    element_count=len(elements),
                    warning_codes=(
                        "unsupported_file_type" if unsupported else "conversion_failed",
                    ),
                ))
                continue

            chunks = self.chunker.chunk_elements(usable)
            self.index.replace_document_chunks(source.document_id, chunks)
            if not chunks:
                items.append(IngestionItemReport(
                    document_id=source.document_id,
                    source_name=source.path.name,
                    status="empty",
                    source_fingerprint=fingerprint,
                    element_count=len(elements),
                    warning_codes=("empty_extracted_content",),
                ))
                continue
            warning_codes = ("partial_conversion",) if failed else ()
            items.append(IngestionItemReport(
                document_id=source.document_id,
                source_name=source.path.name,
                status="partial" if failed else "converted",
                source_fingerprint=fingerprint,
                element_count=len(elements),
                chunk_count=len(chunks),
                warning_codes=warning_codes,
            ))

        return RagV2IngestionReport(
            items=tuple(items),
            converted_count=sum(item.status in {"converted", "partial"} for item in items),
            skipped_count=sum(item.status == "unchanged" for item in items),
            failed_count=sum(item.status == "failed" for item in items),
            disabled_count=sum(item.status == "disabled" for item in items),
            indexed_chunk_count=self.index.count(),
            created_at=datetime.now(timezone.utc).isoformat(),
            unsupported_count=sum(item.status == "unsupported" for item in items),
            empty_count=sum(item.status == "empty" for item in items),
        )

    def query(
        self,
        question: str | RetrievalQueryPlan,
        sources: Iterable[SourceSpec],
        *,
        expansion: Optional[Mapping[str, Any]] = None,
        evidence_config: Optional[EvidencePackConfig] = None,
        rerank_requested: bool = False,
        routing_reason_codes: Tuple[str, ...] = (),
        policy_version: str = "adaptive-reranking-v1",
    ) -> RagV2QueryResult:
        selected = tuple(source for source in sources if source.enabled)
        plan = question if isinstance(question, RetrievalQueryPlan) else (
            build_query_plan(question, expansion) if expansion is not None else coerce_query_plan(question)
        )
        expected = {}
        allowed_paths = []
        allowed_documents = []
        for source in selected:
            allowed_paths.append(str(source.path))
            allowed_documents.append(source.document_id)
            expected[source.document_id] = (
                _file_fingerprint(source.path) if source.path.is_file() else "__source_unavailable__"
            )
        # Diversity limits are meaningful only across distinct source documents.
        # For a user-selected single manual, a cap of three can suppress the
        # procedure, prerequisite, and safety chunks needed to answer one
        # operational question.  Preserve the configured cap for multi-source
        # searches, but permit the normal retrieval window for one document.
        effective_per_document_limit = (
            self.config.retrieval_limit
            if (
                len(set(allowed_documents)) == 1
                and plan.intent_category in {"procedure", "actionable_output", "diagnosis"}
            )
            else self.config.per_document_limit
        )
        options = SearchOptions(
            allowed_privacy_labels=self.config.allowed_privacy_labels,
            allowed_document_ids=tuple(allowed_documents),
            allowed_source_paths=tuple(allowed_paths),
            expected_source_fingerprints=expected,
            candidate_limit=self.config.candidate_limit,
            per_document_limit=effective_per_document_limit,
        )
        ranking_config = HybridRankingConfig(
            rrf_k=self.config.rrf_k,
            lexical_weight=self.config.lexical_channel_weight,
            dense_weight=self.config.dense_channel_weight,
            sparse_weight=self.config.sparse_channel_weight,
            rerank_limit=self.config.rerank_limit,
        )
        if self.config.strict_semantic and self.config.index_read_only:
            coverage = self.index.verify_selected_document_coverage(
                allowed_documents,
                expected_document_fingerprints=expected,
                sparse_required=self.config.retrieval_profile in _BGE_SPARSE_PROFILES,
                multivector_required=self.config.retrieval_profile == "bge_m3_multivector",
            )
            if not coverage["valid"]:
                raise SemanticBackendUnavailable("semantic_index_coverage_incomplete")

        def _safe_reranker_error_code(exc: BaseException) -> str:
            """Map any exception to an allowlisted safe string without leaking paths or text."""
            exc_type = type(exc).__name__.lower()
            exc_msg = str(exc).lower()
            if "timeout" in exc_type or "timeout" in exc_msg or "timed out" in exc_msg:
                return "reranker_backend_timeout"
            if "memoryerror" in exc_type or "oom" in exc_msg or "out of memory" in exc_msg:
                return "reranker_oom"
            if "unavailable" in exc_msg or "missing" in exc_msg or "not found" in exc_msg:
                return "reranker_backend_unavailable"
            return "reranker_backend_failed"



        effective_profile = self._effective_retrieval_profile
        reranker_applied = False
        degraded = False
        degraded_reason = ""
        effective_path = "hybrid"

        if effective_profile == "lexical":
            response = self.index.search_with_summary(
                plan,
                limit=self.config.retrieval_limit,
                options=options,
            )
            effective_path = "lexical"
            if rerank_requested:
                reranker = self.reranker_backend
                if self.circuit_breaker.is_open():
                    degraded = True
                    degraded_reason = "circuit_breaker_open"
                elif (
                    reranker is None
                    or not getattr(reranker, "capability", None)
                    or not reranker.capability.available
                ):
                    degraded = True
                    degraded_reason = "reranker_backend_unavailable"
                else:
                    try:
                        if response.results:
                            from .index import _rerank_hybrid_window, _select_hybrid_results
                            reranked_candidates = _rerank_hybrid_window(
                                plan.original_query,
                                response.results,
                                reranker,
                                ranking_config.rerank_limit,
                            )
                            final_results, _rejected = _select_hybrid_results(
                                reranked_candidates,
                                plan,
                                limit=self.config.retrieval_limit,
                                per_document_limit=options.per_document_limit,
                                near_duplicate_threshold=ranking_config.near_duplicate_threshold,
                            )
                            new_summary = replace(
                                response.summary,
                                candidate_backend="lexical_rerank",
                                returned_count=len(final_results),
                            )
                            response = SearchResponse(results=tuple(final_results), summary=new_summary)
                            reranker_applied = True
                            effective_path = "lexical_rerank"
                            self.circuit_breaker.record_success()
                    except Exception as rerank_exc:
                        self.circuit_breaker.record_failure()
                        degraded = True
                        degraded_reason = _safe_reranker_error_code(rerank_exc)
                        reranker_applied = False
                        effective_path = "lexical"
        elif effective_profile == "dense":

            response = self.index.dense_search_with_summary(
                plan,
                limit=self.config.retrieval_limit,
                options=options,
                dense_limit=self.config.dense_candidate_limit,
                ranking_config=ranking_config,
            )
            effective_path = "dense"
        else:
            # Base hybrid retrieval first (without reranker)
            # This strictly preserves fail-closed for base BGE semantic errors if strict_semantic=True
            # A reranker can only improve ranking when it sees a wider candidate
            # window than the final evidence pack.  Previously Deep reranked the
            # already-truncated top-N result, which made it effectively the same
            # retrieval as Fast whenever N equalled rerank_limit.
            should_rerank = rerank_requested or (
                effective_profile in {"hybrid_rerank", "hybrid_rerank_expand"}
            )
            pre_rerank_limit = self.config.retrieval_limit
            if should_rerank:
                pre_rerank_limit = min(
                    self.config.candidate_limit,
                    max(self.config.retrieval_limit, ranking_config.rerank_limit),
                )
            response = self.index.hybrid_search_with_summary(
                plan,
                limit=pre_rerank_limit,
                options=options,
                dense_limit=self.config.dense_candidate_limit,
                ranking_config=ranking_config,
                reranker=None,
                use_multivector=effective_profile == "hybrid_multivector",
                precomputed_only=effective_profile == "hybrid_multivector",
            )
            effective_path = "hybrid"

            if should_rerank:
                reranker = self.reranker_backend
                if self.circuit_breaker.is_open():
                    degraded = True
                    degraded_reason = "circuit_breaker_open"
                elif (
                    reranker is None
                    or not getattr(reranker, "capability", None)
                    or not reranker.capability.available
                ):
                    degraded = True
                    degraded_reason = "reranker_backend_unavailable"
                else:
                    try:
                        if response.results:
                            from .index import _rerank_hybrid_window, _select_hybrid_results
                            reranked_candidates = _rerank_hybrid_window(
                                plan.original_query,
                                response.results,
                                reranker,
                                ranking_config.rerank_limit,
                            )
                            final_results, _rejected = _select_hybrid_results(
                                reranked_candidates,
                                plan,
                                limit=self.config.retrieval_limit,
                                per_document_limit=options.per_document_limit,
                                near_duplicate_threshold=ranking_config.near_duplicate_threshold,
                            )
                            new_summary = replace(
                                response.summary,
                                candidate_backend="hybrid_rrf_rerank",
                                returned_count=len(final_results),
                            )
                            response = SearchResponse(results=tuple(final_results), summary=new_summary)
                            reranker_applied = True
                            effective_path = "hybrid_rerank"
                            self.circuit_breaker.record_success()
                    except Exception as rerank_exc:
                        self.circuit_breaker.record_failure()
                        degraded = True
                        degraded_reason = _safe_reranker_error_code(rerank_exc)
                        reranker_applied = False
                        effective_path = "hybrid"
                        if self.config.retrieval_profile in {"hybrid_rerank", "hybrid_rerank_expand"}:
                            self._effective_retrieval_profile = "hybrid"
                            self._degraded_reason = degraded_reason


            if effective_profile in {
                "hybrid_rerank_expand",
                "bge_m3_hybrid",
                "bge_m3_hybrid_rerank",
                "bge_m3_hybrid_rerank_expand",
            }:
                response = self.index.expand_context(
                    response,
                    options=options,
                    neighbor_window=self.config.context_neighbor_window,
                    parent_limit=self.config.context_parent_limit,
                )
                if effective_profile == "hybrid_rerank_expand":
                    effective_path = "hybrid_rerank_expand"



        if evidence_config is None:
            evidence_config = EvidencePackConfig()

        if plan.intent_category in {"procedure", "actionable_output", "excel_native", "citation_provenance", "diagnosis", "compare_change", "precise_lookup"}:
            evidence_config = replace(
                evidence_config,
                min_final_evidence_term_coverage=min(0.05, evidence_config.min_final_evidence_term_coverage),
                min_semantic_support_score=min(0.1, evidence_config.min_semantic_support_score)
            )
        if (
            plan.intent_category in {"procedure", "actionable_output", "diagnosis"}
            and len(set(allowed_documents)) == 1
        ):
            # A complete operational answer commonly spans definition,
            # prerequisites, execution, and safety within one manual.  The
            # normal cross-document diversity cap of three would keep only the
            # opening section and make the provider claim the later steps are
            # absent.  The retrieval window remains bounded by the configured
            # limit and still uses only the caller-selected document.
            evidence_config = replace(
                evidence_config,
                max_items=max(evidence_config.max_items, self.config.retrieval_limit),
                per_document_limit=max(
                    evidence_config.per_document_limit,
                    self.config.retrieval_limit,
                ),
            )

        pack = build_evidence_pack(plan, response, config=evidence_config)
        synthesis = (
            synthesize_with_provider(
                pack,
                self.synthesis_provider,
                answer_shape=plan.intent_category,
            )
            if self.synthesis_provider is not None
            else synthesize_evidence(pack, answer_shape=plan.intent_category)
        )
        return RagV2QueryResult(
            query_plan=plan,
            search_response=response,
            evidence_pack=pack,
            synthesis_result=synthesis,
            route=(
                synthesis.mode
                if self.synthesis_provider is not None
                else "local_retrieval_evidence"
            ),
            provider_used=synthesis.provider_used,
            reranker_requested=bool(rerank_requested),
            reranker_applied=bool(reranker_applied),
            effective_path=effective_path,
            degraded=bool(degraded),
            degraded_reason=degraded_reason,
            policy_version=policy_version,
        )


    def inspect(self, sources: Iterable[SourceSpec] = ()) -> dict[str, Any]:
        states = []
        for source in sources:
            state = self.index.document_state(source.document_id)
            states.append({
                "document_id": source.document_id,
                "source_name": source.path.name,
                "enabled": source.enabled,
                "chunk_count": state["chunk_count"],
                "source_fingerprint": state["source_fingerprint"],
            })
        semantic = self.index.embedding_status()
        requested_profile = self.config.retrieval_profile
        runtime_profile = self._effective_retrieval_profile
        requested_runtime_profile = {
            "lexical_baseline": "lexical",
            "bge_m3_dense": "dense",
            "bge_m3_hybrid": "hybrid",
            "bge_m3_multivector": "hybrid_multivector",
            "bge_m3_hybrid_rerank": "hybrid_rerank",
            "bge_m3_hybrid_rerank_expand": "hybrid_rerank_expand",
        }.get(requested_profile, requested_profile)
        degraded = requested_runtime_profile != runtime_profile
        effective_profile = requested_profile if not degraded else runtime_profile
        reranker_capability = (
            self.reranker_backend.capability.to_safe_dict()
            if self.reranker_backend is not None
            else {
                "capability": "reranker",
                "available": False,
                "backend": "not_configured",
                "reason": self._degraded_reason if requested_profile == "hybrid_rerank" else "",
                "model": None,
            }
        )
        return {
            "mode": "provider_capable" if self.synthesis_provider is not None else "local_only",
            "provider_used": False,
            "provider_configured": self.synthesis_provider is not None,
            "index_path": self.config.index_filename,
            "indexed_chunk_count": self.index.count(),
            "retrieval": {
                "requested_profile": requested_profile,
                "effective_profile": effective_profile,
                "runtime_profile": runtime_profile,
                "degraded": degraded,
                "degraded_reason": self._degraded_reason if degraded else "",
                "lexical_backend": self.index.retrieval_backend,
                "semantic": semantic,
                "reranker": reranker_capability,
                "ranking": {
                    "rrf_k": self.config.rrf_k,
                    "lexical_channel_weight": self.config.lexical_channel_weight,
                    "dense_channel_weight": self.config.dense_channel_weight,
                    "sparse_channel_weight": self.config.sparse_channel_weight,
                    "dense_candidate_limit": self.config.dense_candidate_limit,
                    "rerank_limit": self.config.rerank_limit,
                },
            },
            "sources": states,
        }

    def close(self) -> None:
        if self._owns_index:
            self.index.close()

    def __enter__(self) -> "RagV2DevPipeline":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
