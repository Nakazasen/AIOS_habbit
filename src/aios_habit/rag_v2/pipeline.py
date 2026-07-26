"""Dev-only orchestration for the independent, local-first RAG v2 pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Tuple

from .adapters import ConversionContext
from .chunking import StructureAwareChunker
from .evidence import EvidencePack, EvidencePackConfig, build_evidence_pack
from .index import LocalChunkIndex, SearchOptions, SearchResponse
from .query_planning import RetrievalQueryPlan, build_query_plan, coerce_query_plan
from .registry import ConverterRegistry
from .schema import ExtractionStatus
from .synthesis import LocalSynthesisResult, synthesize_evidence

_CANONICAL_PRIVACY_LABELS = frozenset({
    "local_only", "confidential", "cloud_safe", "public",
})


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
    retrieval_limit: int = 10
    candidate_limit: int = 100
    per_document_limit: int = 3
    allowed_privacy_labels: Tuple[str, ...] = (
        "local_only", "confidential", "cloud_safe", "public",
    )
    enable_network: bool = False
    enable_provider_synthesis: bool = False

    def __post_init__(self) -> None:
        root = Path(self.runtime_root)
        object.__setattr__(self, "runtime_root", root)
        if root == Path("."):
            raise ValueError("runtime_root must be a dedicated directory")
        if Path(self.index_filename).name != self.index_filename:
            raise ValueError("index_filename must be a file name")
        if self.max_chunk_chars < 80:
            raise ValueError("max_chunk_chars must be at least 80")
        if self.retrieval_limit < 1 or self.candidate_limit < 1 or self.per_document_limit < 1:
            raise ValueError("retrieval limits must be positive")
        labels = tuple(dict.fromkeys(self.allowed_privacy_labels))
        if not labels or any(label not in _CANONICAL_PRIVACY_LABELS for label in labels):
            raise ValueError("allowed_privacy_labels must use canonical labels")
        object.__setattr__(self, "allowed_privacy_labels", labels)
        if self.enable_network or self.enable_provider_synthesis:
            raise ValueError("Dev pipeline is local-only; provider synthesis is a separate gate")

    @property
    def index_path(self) -> Path:
        return Path(self.runtime_root) / self.index_filename


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


class RagV2DevPipeline:
    """Compose existing RAG v2 primitives without touching Workspace Chat."""

    def __init__(
        self,
        config: Optional[RagV2DevConfig] = None,
        *,
        registry: Optional[ConverterRegistry] = None,
        chunker: Optional[StructureAwareChunker] = None,
        index: Optional[LocalChunkIndex] = None,
    ) -> None:
        self.config = config or RagV2DevConfig()
        Path(self.config.runtime_root).mkdir(parents=True, exist_ok=True)
        self.registry = registry or ConverterRegistry()
        self.chunker = chunker or StructureAwareChunker(self.config.max_chunk_chars)
        self.index = index or LocalChunkIndex(self.config.index_path)
        self._owns_index = index is None

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
                items.append(IngestionItemReport(
                    document_id=source.document_id,
                    source_name=source.path.name,
                    status="failed",
                    source_fingerprint=fingerprint,
                    element_count=len(elements),
                    warning_codes=("conversion_failed",),
                ))
                continue

            chunks = self.chunker.chunk_elements(usable)
            self.index.replace_document_chunks(source.document_id, chunks)
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
        )

    def query(
        self,
        question: str | RetrievalQueryPlan,
        sources: Iterable[SourceSpec],
        *,
        expansion: Optional[Mapping[str, Any]] = None,
        evidence_config: Optional[EvidencePackConfig] = None,
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
        options = SearchOptions(
            allowed_privacy_labels=self.config.allowed_privacy_labels,
            allowed_document_ids=tuple(allowed_documents),
            allowed_source_paths=tuple(allowed_paths),
            expected_source_fingerprints=expected,
            candidate_limit=self.config.candidate_limit,
            per_document_limit=self.config.per_document_limit,
        )
        response = self.index.search_with_summary(
            plan,
            limit=self.config.retrieval_limit,
            options=options,
        )
        pack = build_evidence_pack(plan, response, config=evidence_config)
        synthesis = synthesize_evidence(pack, answer_shape=plan.intent_category)
        return RagV2QueryResult(
            query_plan=plan,
            search_response=response,
            evidence_pack=pack,
            synthesis_result=synthesis,
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
        return {
            "mode": "local_only",
            "provider_used": False,
            "index_path": self.config.index_filename,
            "indexed_chunk_count": self.index.count(),
            "sources": states,
        }

    def close(self) -> None:
        if self._owns_index:
            self.index.close()

    def __enter__(self) -> "RagV2DevPipeline":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
