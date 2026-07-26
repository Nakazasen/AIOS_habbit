"""Local SQLite index and generic local retrieval for RAG v2 chunks."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
import struct
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .chunking import DocumentChunk
from .query_planning import (
    RetrievalQueryPlan,
    coerce_query_plan,
    extract_content_terms,
    match_text_obligations,
)
from .semantic import (
    EmbeddingBackend,
    SemanticBackendError,
    SemanticCapability,
    cosine_similarity,
    normalize_vector,
)

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def _tokens(value: str) -> List[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(value or "")]


def _unique_tokens(value: str) -> Tuple[str, ...]:
    seen = set()
    ordered = []
    for token in _tokens(value):
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return tuple(ordered)


def _normalized_terms(value: str) -> str:
    return " ".join(_tokens(value))


def _embedding_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pack_vector(vector: Sequence[float], dimension: int) -> bytes:
    normalized = normalize_vector(vector, dimension=dimension)
    return struct.pack(f"<{dimension}f", *normalized)


def _unpack_vector(payload: bytes, dimension: int) -> tuple[float, ...]:
    expected_size = struct.calcsize(f"<{dimension}f")
    if len(payload) != expected_size:
        raise SemanticBackendError(
            f"embedding payload size mismatch: expected {expected_size}, received {len(payload)}"
        )
    return tuple(float(value) for value in struct.unpack(f"<{dimension}f", payload))


def _contains_phrase(value: str, phrase: str) -> bool:
    return bool(phrase and phrase in _normalized_terms(value))


def _text_values(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if isinstance(item, (str, int, float))]
    return []


def _numeric_metadata(metadata: Mapping[str, Any], key: str) -> Optional[float]:
    nested = metadata.get("metadata")
    value = metadata.get(key)
    if value is None and isinstance(nested, Mapping):
        value = nested.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return min(1.0, max(0.0, float(value)))
    return None


def _metadata_flag(metadata: Mapping[str, Any], key: str) -> bool:
    nested = metadata.get("metadata")
    value = metadata.get(key)
    if value is None and isinstance(nested, Mapping):
        value = nested.get(key)
    return value is True


@dataclass(frozen=True)
class SearchOptions:
    """Generic, local-only constraints for a RAG v2 retrieval request."""

    allowed_privacy_labels: Optional[Tuple[str, ...]] = None
    allowed_document_ids: Optional[Tuple[str, ...]] = None
    allowed_source_paths: Optional[Tuple[str, ...]] = None
    expected_source_fingerprints: Mapping[str, str] = field(default_factory=dict)
    candidate_limit: int = 100
    per_document_limit: int = 2

    def __post_init__(self) -> None:
        if self.candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        if self.per_document_limit < 1:
            raise ValueError("per_document_limit must be at least 1")


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    score: float
    text: str
    document_id: str
    source_path: str
    source_name: str
    file_type: str
    metadata: Dict[str, Any]
    privacy_labels: tuple[str, ...]
    ranking_signals: Dict[str, float] = field(default_factory=dict)
    matched_terms: tuple[str, ...] = field(default_factory=tuple)
    term_coverage: float = 0.0
    matched_query_variants: tuple[str, ...] = field(default_factory=tuple)
    matched_query_variant_ids: tuple[str, ...] = field(default_factory=tuple)
    matched_query_facets: tuple[str, ...] = field(default_factory=tuple)
    matched_obligations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SearchSummary:
    """Inspectable local retrieval outcome without exposing source text."""

    query: str
    indexed_chunk_count: int
    eligible_chunk_count: int
    candidate_count: int
    returned_count: int
    filtered_by_source_count: int = 0
    filtered_by_privacy_count: int = 0
    filtered_as_stale_count: int = 0
    diversity_limited_count: int = 0
    best_term_coverage: float = 0.0
    insufficiency_reasons: tuple[str, ...] = field(default_factory=tuple)
    query_variant_count: int = 1
    query_plan_fingerprint: str = ""
    expansion_status: str = "identity"
    candidate_backend: str = "deterministic_scan"
    evidence_set_term_coverage: float = 0.0
    planned_facet_ids: tuple[str, ...] = field(default_factory=tuple)
    covered_facet_ids: tuple[str, ...] = field(default_factory=tuple)
    missing_facet_ids: tuple[str, ...] = field(default_factory=tuple)
    planned_obligation_ids: tuple[str, ...] = field(default_factory=tuple)
    covered_obligation_ids: tuple[str, ...] = field(default_factory=tuple)
    missing_obligation_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[SearchResult, ...]
    summary: SearchSummary


class LocalChunkIndex:
    def __init__(
        self,
        db_path: str | Path,
        *,
        enable_fts5: bool = True,
        embedding_backend: Optional[EmbeddingBackend] = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row
        self._fts5_requested = enable_fts5
        self._fts5_available = False
        self._embedding_backend = embedding_backend
        self._create_schema()
        if embedding_backend is not None and embedding_backend.capability.available:
            self.ensure_embeddings()

    @property
    def retrieval_backend(self) -> str:
        return "fts5_bm25" if self._fts5_available else "deterministic_scan"

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                privacy_labels_json TEXT NOT NULL,
                source_fingerprint TEXT,
                checksum TEXT
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                model_fingerprint TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                runtime TEXT NOT NULL,
                runtime_version TEXT NOT NULL,
                dimension INTEGER NOT NULL CHECK (dimension > 0),
                dtype TEXT NOT NULL CHECK (dtype = 'float32-le'),
                normalized INTEGER NOT NULL CHECK (normalized IN (0, 1)),
                vector_blob BLOB NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chunk_id, model_fingerprint)
            );
            CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model
            ON chunk_embeddings(model_fingerprint, chunk_id);
            CREATE TRIGGER IF NOT EXISTS chunks_embeddings_content_update
            AFTER UPDATE OF text, normalized_text, checksum ON chunks
            WHEN old.text IS NOT new.text
              OR old.normalized_text IS NOT new.normalized_text
              OR old.checksum IS NOT new.checksum
            BEGIN
                DELETE FROM chunk_embeddings WHERE chunk_id = old.chunk_id;
            END;
            """
        )
        if self._fts5_requested:
            try:
                self._conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                        chunk_id UNINDEXED,
                        normalized_text,
                        source_name,
                        source_path,
                        metadata_json,
                        tokenize='unicode61'
                    )
                    """
                )
                self._conn.executescript(
                    """
                    CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON chunks BEGIN
                        INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                        VALUES (new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json);
                    END;
                    CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON chunks BEGIN
                        DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                    END;
                    CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON chunks BEGIN
                        DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                        INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                        VALUES (new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json);
                    END;
                    """
                )
                chunk_count = int(self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
                fts_count = int(self._conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0])
                if chunk_count != fts_count:
                    self._conn.execute("DELETE FROM chunks_fts")
                    self._conn.execute(
                        """
                        INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                        SELECT chunk_id, normalized_text, source_name, source_path, metadata_json FROM chunks
                        """
                    )
                self._fts5_available = True
            except sqlite3.OperationalError:
                self._fts5_available = False
        self._conn.commit()

    def upsert_chunks(self, chunks: Iterable[DocumentChunk]) -> int:
        prepared = tuple(chunks)
        rows = [self._chunk_row(chunk) for chunk in prepared]
        if not rows:
            return 0
        with self._conn:
            self._upsert_rows(rows)
            self._ensure_embeddings(tuple(chunk.chunk_id for chunk in prepared))
        return len(rows)

    def replace_document_chunks(
        self,
        document_id: str,
        chunks: Iterable[DocumentChunk],
    ) -> int:
        """Atomically replace one document while preserving valid embedding cache rows."""
        normalized_id = (document_id or "").strip()
        if not normalized_id:
            raise ValueError("document_id is required")
        prepared = tuple(chunks)
        if any(chunk.document_id != normalized_id for chunk in prepared):
            raise ValueError("all chunks must belong to document_id")
        rows = [self._chunk_row(chunk) for chunk in prepared]
        chunk_ids = tuple(chunk.chunk_id for chunk in prepared)
        with self._conn:
            if rows:
                self._upsert_rows(rows)
                placeholders = ",".join("?" for _ in chunk_ids)
                self._conn.execute(
                    f"DELETE FROM chunks WHERE document_id = ? AND chunk_id NOT IN ({placeholders})",
                    (normalized_id, *chunk_ids),
                )
                self._ensure_embeddings(chunk_ids)
            else:
                self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (normalized_id,))
        return len(rows)

    def delete_document(self, document_id: str) -> int:
        """Delete one selected document and return the number of removed chunks."""
        normalized_id = (document_id or "").strip()
        if not normalized_id:
            raise ValueError("document_id is required")
        with self._conn:
            cursor = self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (normalized_id,))
        return max(0, int(cursor.rowcount))

    def document_state(self, document_id: str) -> Dict[str, Any]:
        """Return safe incremental-index state without returning source text."""
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS chunk_count,
                   MIN(source_fingerprint) AS min_fingerprint,
                   MAX(source_fingerprint) AS max_fingerprint
            FROM chunks WHERE document_id = ?
            """,
            (document_id,),
        ).fetchone()
        count = int(row["chunk_count"] or 0)
        fingerprint = row["min_fingerprint"] if count and row["min_fingerprint"] == row["max_fingerprint"] else None
        return {
            "document_id": document_id,
            "chunk_count": count,
            "source_fingerprint": fingerprint,
        }

    def _upsert_rows(self, rows: Iterable[tuple[Any, ...]]) -> None:
        self._conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id=excluded.document_id,
                source_path=excluded.source_path,
                source_name=excluded.source_name,
                file_type=excluded.file_type,
                text=excluded.text,
                normalized_text=excluded.normalized_text,
                metadata_json=excluded.metadata_json,
                privacy_labels_json=excluded.privacy_labels_json,
                source_fingerprint=excluded.source_fingerprint,
                checksum=excluded.checksum
            """,
            rows,
        )

    @property
    def semantic_capability(self) -> Optional[SemanticCapability]:
        backend = self._embedding_backend
        return backend.capability if backend is not None else None

    def ensure_embeddings(self) -> int:
        """Persist only missing or stale vectors for the configured local model."""
        with self._conn:
            return self._ensure_embeddings()

    def _ensure_embeddings(self, chunk_ids: Sequence[str] = ()) -> int:
        backend = self._embedding_backend
        if backend is None or not backend.capability.available:
            return 0
        descriptor = backend.descriptor
        parameters: list[Any] = [descriptor.fingerprint]
        where = ""
        if chunk_ids:
            placeholders = ",".join("?" for _ in chunk_ids)
            where = f"WHERE c.chunk_id IN ({placeholders})"
            parameters.extend(chunk_ids)
        rows = self._conn.execute(
            f"""
            SELECT c.chunk_id, c.text, e.content_hash
            FROM chunks AS c
            LEFT JOIN chunk_embeddings AS e
              ON e.chunk_id = c.chunk_id AND e.model_fingerprint = ?
            {where}
            ORDER BY c.chunk_id
            """,
            parameters,
        ).fetchall()
        pending = [
            row for row in rows
            if row["content_hash"] != _embedding_content_hash(str(row["text"]))
        ]
        if not pending:
            return 0
        vectors = backend.embed_documents(tuple(str(row["text"]) for row in pending))
        if len(vectors) != len(pending):
            raise SemanticBackendError(
                f"embedding count mismatch: expected {len(pending)}, received {len(vectors)}"
            )
        created_at = datetime.now(timezone.utc).isoformat()
        records = []
        for row, vector in zip(pending, vectors):
            records.append((
                str(row["chunk_id"]),
                descriptor.fingerprint,
                _embedding_content_hash(str(row["text"])),
                descriptor.model_id,
                descriptor.revision,
                descriptor.runtime,
                descriptor.runtime_version,
                descriptor.dimension,
                "float32-le",
                int(descriptor.normalized),
                _pack_vector(vector, descriptor.dimension),
                created_at,
            ))
        self._conn.executemany(
            """
            INSERT INTO chunk_embeddings (
                chunk_id, model_fingerprint, content_hash, model_id, model_revision,
                runtime, runtime_version, dimension, dtype, normalized, vector_blob, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                content_hash=excluded.content_hash,
                model_id=excluded.model_id,
                model_revision=excluded.model_revision,
                runtime=excluded.runtime,
                runtime_version=excluded.runtime_version,
                dimension=excluded.dimension,
                dtype=excluded.dtype,
                normalized=excluded.normalized,
                vector_blob=excluded.vector_blob,
                created_at=excluded.created_at
            """,
            records,
        )
        return len(records)

    def embedding_status(self) -> Dict[str, Any]:
        """Return vector coverage/provenance without exposing text or vectors."""
        backend = self._embedding_backend
        total = self.count()
        if backend is None:
            return {
                "configured": False,
                "available": False,
                "indexed_chunk_count": total,
                "embedded_chunk_count": 0,
                "model": None,
            }
        descriptor = backend.descriptor
        embedded = int(self._conn.execute(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE model_fingerprint = ?",
            (descriptor.fingerprint,),
        ).fetchone()[0])
        return {
            "configured": True,
            "available": backend.capability.available,
            "reason": backend.capability.reason,
            "indexed_chunk_count": total,
            "embedded_chunk_count": embedded,
            "model": descriptor.to_safe_dict(),
        }

    def dense_candidates(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int = 100,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Return filtered local cosine candidates fused only across query variants."""
        backend = self._embedding_backend
        if backend is None:
            raise SemanticBackendError("embedding backend is not configured")
        backend.capability.require()
        if limit <= 0:
            return []
        options = options or SearchOptions()
        plan = coerce_query_plan(query)
        self.ensure_embeddings()
        descriptor = backend.descriptor
        rows = self._conn.execute(
            """
            SELECT c.*, e.dimension AS embedding_dimension, e.vector_blob
            FROM chunks AS c
            JOIN chunk_embeddings AS e ON e.chunk_id = c.chunk_id
            WHERE e.model_fingerprint = ? AND e.dtype = 'float32-le' AND e.normalized = 1
            """,
            (descriptor.fingerprint,),
        ).fetchall()
        eligible = []
        for row in rows:
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if not self._is_selected(row, options):
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                continue
            if self._is_stale(row, options):
                continue
            eligible.append((row, privacy_labels))

        fused: dict[str, dict[str, Any]] = {}
        for variant in plan.variants:
            query_vector = normalize_vector(
                backend.embed_query(variant.text),
                dimension=descriptor.dimension,
            )
            ranked = []
            for row, privacy_labels in eligible:
                dimension = int(row["embedding_dimension"])
                if dimension != descriptor.dimension:
                    continue
                vector = _unpack_vector(bytes(row["vector_blob"]), dimension)
                similarity = cosine_similarity(query_vector, vector)
                ranked.append((similarity, row, privacy_labels))
            ranked.sort(key=lambda item: (
                -item[0], item[1]["document_id"], item[1]["source_path"], item[1]["chunk_id"]
            ))
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, (similarity, row, privacy_labels) in enumerate(
                ranked[: options.candidate_limit], 1
            ):
                key = str(row["chunk_id"])
                record = fused.setdefault(key, {
                    "rrf_score": 0.0,
                    "best_similarity": similarity,
                    "row": row,
                    "privacy_labels": privacy_labels,
                    "variants": [],
                    "variant_ids": [],
                    "facet_ids": [],
                })
                record["rrf_score"] += variant_weight / (60.0 + rank)
                record["variants"].append(variant.text)
                record["variant_ids"].append(variant.variant_id)
                record["facet_ids"].append(variant.facet_id)
                if similarity > record["best_similarity"]:
                    record["best_similarity"] = similarity
                    record["row"] = row
                    record["privacy_labels"] = privacy_labels

        ordered = sorted(fused.values(), key=lambda item: (
            -item["rrf_score"], -item["best_similarity"], item["row"]["document_id"],
            item["row"]["source_path"], item["row"]["chunk_id"],
        ))[:limit]
        results = []
        for record in ordered:
            row = record["row"]
            metadata = json.loads(row["metadata_json"])
            section_text = " ".join(_text_values(metadata.get("section_path")))
            obligations = match_text_obligations(
                plan.intent_category,
                (str(row["normalized_text"]), section_text),
                required_obligations=plan.required_obligations,
            )
            results.append(SearchResult(
                chunk_id=row["chunk_id"],
                score=float(record["best_similarity"]),
                text=row["text"],
                document_id=row["document_id"],
                source_path=row["source_path"],
                source_name=row["source_name"],
                file_type=row["file_type"],
                metadata=metadata,
                privacy_labels=record["privacy_labels"],
                ranking_signals={
                    "dense_cosine": float(record["best_similarity"]),
                    "dense_multi_variant_rrf": float(record["rrf_score"]),
                },
                matched_query_variants=tuple(record["variants"]),
                matched_query_variant_ids=tuple(dict.fromkeys(record["variant_ids"])),
                matched_query_facets=tuple(dict.fromkeys(record["facet_ids"])),
                matched_obligations=tuple(obligations),
            ))
        return results

    def search(
        self,
        query: str | RetrievalQueryPlan,
        limit: int = 10,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Return generic local results while preserving the original list API."""
        return list(self.search_with_summary(query, limit=limit, options=options).results)

    def search_with_summary(
        self,
        query: str | RetrievalQueryPlan,
        limit: int = 10,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """Run filter, candidate, ranking, and diversity stages locally."""
        options = options or SearchOptions()
        query_plan = coerce_query_plan(query)
        query_text = query_plan.original_query
        terms = extract_content_terms(query_text)
        indexed_rows = self._conn.execute("SELECT * FROM chunks").fetchall()

        if not terms:
            return self._empty_response(
                query=query_text,
                indexed_chunk_count=len(indexed_rows),
                reason="empty_or_tokenless_query",
            )
        if limit <= 0:
            return self._empty_response(
                query=query_text,
                indexed_chunk_count=len(indexed_rows),
                reason="non_positive_limit",
            )

        eligible_rows: List[sqlite3.Row] = []
        filtered_by_source = 0
        filtered_by_privacy = 0
        filtered_as_stale = 0
        for row in indexed_rows:
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if not self._is_selected(row, options):
                filtered_by_source += 1
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                filtered_by_privacy += 1
                continue
            if self._is_stale(row, options):
                filtered_as_stale += 1
                continue
            eligible_rows.append(row)

        # Rank each validated query variant independently, then fuse by rank.
        # Filtering is already complete above, so FTS and variants can never bypass
        # privacy, source-selection, or stale-fingerprint constraints.
        per_variant_candidates: list[tuple[Any, list[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]]]] = []
        candidate_backend = self.retrieval_backend
        for variant in query_plan.variants:
            variant_terms = extract_content_terms(variant.text)
            if not variant_terms:
                continue
            candidate_rows, backend = self._candidate_rows(
                variant.text,
                eligible_rows,
                options.candidate_limit,
            )
            if backend != "fts5_bm25":
                candidate_backend = "deterministic_scan"
            ranked = []
            for candidate_position, row in enumerate(candidate_rows):
                candidate = self._score_candidate(row, variant_terms, query_plan=query_plan)
                if candidate is not None:
                    ranked.append((candidate_position, candidate))
            ranked.sort(
                key=lambda item: (
                    -item[1][0],
                    item[0],
                    item[1][1]["document_id"],
                    item[1][1]["source_path"],
                    item[1][1]["chunk_id"],
                )
            )
            per_variant_candidates.append(
                (variant, [item[1] for item in ranked[: options.candidate_limit]])
            )

        fused: dict[str, dict[str, Any]] = {}
        for variant, candidates_for_variant in per_variant_candidates:
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, candidate in enumerate(candidates_for_variant, 1):
                score, row, metadata, privacy_labels, signals, matched_terms, coverage = candidate
                key = str(row["chunk_id"])
                record = fused.setdefault(
                    key,
                    {
                        "rrf_score": 0.0,
                        "best_score": score,
                        "row": row,
                        "metadata": metadata,
                        "privacy_labels": privacy_labels,
                        "signals": dict(signals),
                        "matched_terms": matched_terms,
                        "coverage": coverage,
                        "variants": [],
                        "variant_ids": [],
                        "facet_ids": [],
                        "variant_term_matches": {},
                    },
                )
                record["rrf_score"] += (1.0 / (60.0 + rank)) * variant_weight
                record["variants"].append(variant.text)
                record["variant_ids"].append(variant.variant_id)
                record["facet_ids"].append(variant.facet_id)
                record["variant_term_matches"][variant.text] = matched_terms
                if score > record["best_score"]:
                    record.update(
                        best_score=score,
                        row=row,
                        metadata=metadata,
                        privacy_labels=privacy_labels,
                        signals=dict(signals),
                        matched_terms=matched_terms,
                        coverage=coverage,
                    )

        for candidate in fused.values():
            row = candidate["row"]
            metadata = candidate["metadata"]
            section_text = " ".join(_text_values(metadata.get("section_path")))
            candidate["obligation_ids"] = match_text_obligations(
                query_plan.intent_category,
                (str(row["normalized_text"]), section_text),
                required_obligations=query_plan.required_obligations,
            )

        planned_obligation_ids = tuple(
            obligation
            for obligation in query_plan.required_obligations
            if obligation != "query"
        )
        candidates = sorted(
            fused.values(),
            key=lambda item: (-item["rrf_score"], -item["best_score"], item["row"]["document_id"], item["row"]["source_path"], item["row"]["chunk_id"]),
        )[: options.candidate_limit]
        obligation_first = []
        selected_keys = set()
        for obligation_id in planned_obligation_ids:
            match = next(
                (
                    candidate
                    for candidate in candidates
                    if obligation_id in candidate["obligation_ids"]
                    and str(candidate["row"]["chunk_id"]) not in selected_keys
                ),
                None,
            )
            if match is not None:
                obligation_first.append(match)
                selected_keys.add(str(match["row"]["chunk_id"]))
        candidates = obligation_first + [
            candidate
            for candidate in candidates
            if str(candidate["row"]["chunk_id"]) not in selected_keys
        ]

        structural_facets = tuple(facet_id for facet_id in query_plan.facet_ids if facet_id != "query")
        if structural_facets:
            facet_first = []
            facet_selected_keys = set()
            for facet_id in structural_facets:
                match = next(
                    (
                        candidate
                        for candidate in candidates
                        if facet_id in candidate["facet_ids"]
                        and str(candidate["row"]["chunk_id"]) not in facet_selected_keys
                    ),
                    None,
                )
                if match is not None:
                    facet_first.append(match)
                    facet_selected_keys.add(str(match["row"]["chunk_id"]))
            candidates = facet_first + [
                candidate
                for candidate in candidates
                if str(candidate["row"]["chunk_id"]) not in facet_selected_keys
            ]

        results: List[SearchResult] = []
        returned_candidates: List[Dict[str, Any]] = []
        document_counts: Counter[str] = Counter()
        diversity_limited = 0
        for candidate in candidates:
            row = candidate["row"]
            document_key = row["document_id"] or row["source_path"]
            if document_counts[document_key] >= options.per_document_limit:
                diversity_limited += 1
                continue
            document_counts[document_key] += 1
            signals = dict(candidate["signals"])
            signals["multi_variant_rrf"] = candidate["rrf_score"]
            results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    score=float(candidate["best_score"]),
                    text=row["text"],
                    document_id=row["document_id"],
                    source_path=row["source_path"],
                    source_name=row["source_name"],
                    file_type=row["file_type"],
                    metadata=candidate["metadata"],
                    privacy_labels=candidate["privacy_labels"],
                    ranking_signals=signals,
                    matched_terms=candidate["matched_terms"],
                    term_coverage=float(candidate["coverage"]),
                    matched_query_variants=tuple(candidate["variants"]),
                    matched_query_variant_ids=tuple(dict.fromkeys(candidate["variant_ids"])),
                    matched_query_facets=tuple(dict.fromkeys(candidate["facet_ids"])),
                    matched_obligations=tuple(candidate["obligation_ids"]),
                )
            )
            returned_candidates.append(candidate)
            if len(results) >= limit:
                break

        best_term_coverage = max((result.term_coverage for result in results), default=0.0)
        evidence_set_coverage = self._evidence_set_term_coverage(returned_candidates, query_plan)

        reasons = self._insufficiency_reasons(
            indexed_count=len(indexed_rows),
            eligible_count=len(eligible_rows),
            candidate_count=len(candidates),
            result_count=len(results),
            filtered_by_source=filtered_by_source,
            filtered_by_privacy=filtered_by_privacy,
            filtered_as_stale=filtered_as_stale,
            best_coverage=evidence_set_coverage,
            term_count=len(query_plan.content_terms) or len(terms),
        )
        if query_plan.expansion_status not in {"identity", "faceted", "expanded"}:
            reasons = tuple(dict.fromkeys((*reasons, query_plan.expansion_status)))
        planned_facet_ids = query_plan.facet_ids
        covered_facet_ids = tuple(
            facet_id
            for facet_id in planned_facet_ids
            if any(facet_id in result.matched_query_facets for result in results)
        )
        missing_facet_ids = tuple(
            facet_id for facet_id in planned_facet_ids if facet_id not in covered_facet_ids
        )
        covered_obligation_ids = tuple(
            obligation_id
            for obligation_id in planned_obligation_ids
            if any(obligation_id in result.matched_obligations for result in results)
        )
        missing_obligation_ids = tuple(
            obligation_id
            for obligation_id in planned_obligation_ids
            if obligation_id not in covered_obligation_ids
        )
        summary = SearchSummary(
            query=query_text,
            indexed_chunk_count=len(indexed_rows),
            eligible_chunk_count=len(eligible_rows),
            candidate_count=len(candidates),
            returned_count=len(results),
            filtered_by_source_count=filtered_by_source,
            filtered_by_privacy_count=filtered_by_privacy,
            filtered_as_stale_count=filtered_as_stale,
            diversity_limited_count=diversity_limited,
            best_term_coverage=best_term_coverage,
            insufficiency_reasons=reasons,
            query_variant_count=len(query_plan.variants),
            query_plan_fingerprint=query_plan.fingerprint,
            expansion_status=query_plan.expansion_status,
            candidate_backend=candidate_backend,
            evidence_set_term_coverage=evidence_set_coverage,
            planned_facet_ids=planned_facet_ids,
            covered_facet_ids=covered_facet_ids,
            missing_facet_ids=missing_facet_ids,
            planned_obligation_ids=planned_obligation_ids,
            covered_obligation_ids=covered_obligation_ids,
            missing_obligation_ids=missing_obligation_ids,
        )
        return SearchResponse(results=tuple(results), summary=summary)

    def clear(self) -> None:
        self._conn.execute("DELETE FROM chunks")
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        return int(row["count"])

    def _candidate_rows(
        self,
        query: str,
        eligible_rows: List[sqlite3.Row],
        limit: int,
    ) -> tuple[List[sqlite3.Row], str]:
        if not self._fts5_available or not eligible_rows:
            return list(eligible_rows), "deterministic_scan"
        terms = extract_content_terms(query)
        if not terms:
            return [], "fts5_bm25"
        match_query = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
        try:
            self._conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS rag_v2_eligible_chunks (chunk_id TEXT PRIMARY KEY)"
            )
            self._conn.execute("DELETE FROM rag_v2_eligible_chunks")
            self._conn.executemany(
                "INSERT INTO rag_v2_eligible_chunks(chunk_id) VALUES (?)",
                ((row["chunk_id"],) for row in eligible_rows),
            )
            ranked_ids = self._conn.execute(
                """
                SELECT f.chunk_id
                FROM chunks_fts AS f
                JOIN rag_v2_eligible_chunks AS eligible ON eligible.chunk_id = f.chunk_id
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts, 0.0, 1.0, 2.0, 1.0, 0.75), f.chunk_id
                LIMIT ?
                """,
                (match_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            self._fts5_available = False
            return list(eligible_rows), "deterministic_scan"
        by_id = {str(row["chunk_id"]): row for row in eligible_rows}
        return [by_id[str(row["chunk_id"])] for row in ranked_ids if str(row["chunk_id"]) in by_id], "fts5_bm25"

    @staticmethod
    def _evidence_set_term_coverage(
        candidates: List[Dict[str, Any]],
        query_plan: RetrievalQueryPlan,
    ) -> float:
        coverages = []
        for variant in query_plan.variants:
            terms = set(extract_content_terms(variant.text))
            if not terms:
                continue
            matched = set()
            for candidate in candidates:
                matched.update(candidate["variant_term_matches"].get(variant.text, ()))
            coverages.append(len(matched & terms) / len(terms))
        return max(coverages, default=0.0)

    def close(self) -> None:
        self._conn.close()

    def _chunk_row(self, chunk: DocumentChunk) -> tuple[Any, ...]:
        metadata = chunk.to_dict()
        return (
            chunk.chunk_id,
            chunk.document_id,
            chunk.source_path,
            chunk.source_name,
            chunk.file_type,
            chunk.text,
            chunk.normalized_text,
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(list(chunk.privacy_labels), ensure_ascii=False),
            chunk.source_fingerprint,
            chunk.checksum,
        )

    @staticmethod
    def _is_selected(row: sqlite3.Row, options: SearchOptions) -> bool:
        if options.allowed_document_ids is not None and row["document_id"] not in options.allowed_document_ids:
            return False
        if options.allowed_source_paths is not None and row["source_path"] not in options.allowed_source_paths:
            return False
        return True

    @staticmethod
    def _privacy_is_allowed(privacy_labels: tuple[str, ...], options: SearchOptions) -> bool:
        if options.allowed_privacy_labels is None:
            return True
        allowed = set(options.allowed_privacy_labels)
        return bool(privacy_labels) and all(label in allowed for label in privacy_labels)

    @staticmethod
    def _is_stale(row: sqlite3.Row, options: SearchOptions) -> bool:
        expected = options.expected_source_fingerprints
        if row["document_id"] in expected:
            return row["source_fingerprint"] != expected[row["document_id"]]
        if row["source_path"] in expected:
            return row["source_fingerprint"] != expected[row["source_path"]]
        return False

    @staticmethod
    def _insufficiency_reasons(
        *,
        indexed_count: int,
        eligible_count: int,
        candidate_count: int,
        result_count: int,
        filtered_by_source: int,
        filtered_by_privacy: int,
        filtered_as_stale: int,
        best_coverage: float,
        term_count: int,
    ) -> tuple[str, ...]:
        reasons = []
        if indexed_count == 0:
            reasons.append("no_indexed_chunks")
        if eligible_count == 0 and filtered_by_source:
            reasons.append("source_filter_excluded_all_chunks")
        if eligible_count == 0 and filtered_by_privacy:
            reasons.append("privacy_filter_excluded_all_chunks")
        if eligible_count == 0 and filtered_as_stale:
            reasons.append("stale_fingerprint_excluded_all_chunks")
        if eligible_count > 0 and candidate_count == 0:
            reasons.append("no_lexical_or_metadata_match")
        if result_count > 0 and term_count > 1 and best_coverage < 1.0:
            reasons.append("incomplete_query_term_coverage")
        if result_count > 0 and term_count > 1 and best_coverage < 0.5:
            reasons.append("weak_query_term_coverage")
        return tuple(reasons)

    @staticmethod
    def _empty_response(query: str, indexed_chunk_count: int, reason: str) -> SearchResponse:
        return SearchResponse(
            results=(),
            summary=SearchSummary(
                query=query,
                indexed_chunk_count=indexed_chunk_count,
                eligible_chunk_count=0,
                candidate_count=0,
                returned_count=0,
                insufficiency_reasons=(reason,),
            ),
        )

    @staticmethod
    def _score_candidate(
        row: sqlite3.Row,
        terms: tuple[str, ...],
        query_plan: Optional[RetrievalQueryPlan] = None,
    ) -> Optional[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]]:
        metadata = json.loads(row["metadata_json"])
        privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
        text = row["normalized_text"]
        source_name = row["source_name"]
        source_path = row["source_path"]
        section_text = " ".join(_text_values(metadata.get("section_path")))
        sheet_text = " ".join(_text_values(metadata.get("sheet_names")))
        element_types = tuple(value.lower() for value in _text_values(metadata.get("element_types")))

        all_tokens = _tokens(text)
        text_counts = Counter(all_tokens)
        title_tokens = set(_tokens(source_name))
        path_tokens = set(_tokens(source_path))
        section_tokens = set(_tokens(section_text))
        sheet_tokens = set(_tokens(sheet_text))
        searchable_tokens = set(text_counts) | title_tokens | path_tokens | section_tokens | sheet_tokens
        matched_terms = tuple(term for term in terms if term in searchable_tokens)
        if not matched_terms:
            return None

        phrase = " ".join(terms)
        signals: Dict[str, float] = {}
        raw_lexical_count = float(sum(text_counts[term] for term in terms))
        lexical_count = min(5.0, raw_lexical_count)
        if lexical_count:
            signals["lexical_term_count"] = lexical_count
        if raw_lexical_count > lexical_count:
            signals["lexical_frequency_capped"] = raw_lexical_count - lexical_count

        source_token_matches = sum(term in title_tokens or term in path_tokens for term in terms)
        if source_token_matches:
            signals["source_metadata_match"] = float(source_token_matches) * 2.0

        structure_token_matches = sum(term in section_tokens or term in sheet_tokens for term in terms)
        if structure_token_matches:
            signals["structure_metadata_match"] = float(structure_token_matches)

        if len(terms) > 1 and _contains_phrase(text, phrase):
            signals["exact_text_phrase"] = 4.0
        if len(terms) > 1 and (_contains_phrase(source_name, phrase) or _contains_phrase(source_path, phrase)):
            signals["exact_source_phrase"] = 3.0
        if len(terms) > 1 and (_contains_phrase(section_text, phrase) or _contains_phrase(sheet_text, phrase)):
            signals["exact_structure_phrase"] = 1.5
        if "table" in element_types and lexical_count:
            signals["table_structure_match"] = min(1.0, lexical_count) * 0.5

        confidence = _numeric_metadata(metadata, "confidence")
        if confidence is not None:
            signals["confidence_metadata"] = confidence * 0.25
        freshness = _numeric_metadata(metadata, "freshness_score")
        if freshness is not None:
            signals["freshness_metadata"] = freshness * 0.25
        if _metadata_flag(metadata, "metadata_only") or _metadata_flag(metadata, "content_unavailable"):
            signals["metadata_only_penalty"] = -3.0

        # Domain-neutral intent & obligation scoring
        intent = query_plan.intent_category if query_plan else "general"
        action_words = {"check", "verify", "action", "handle", "handling", "step", "steps", "fix", "resolution", "solution", "xử", "khắc", "bước", "kiểm", "quản", "thực"}
        problem_words = {"error", "errors", "fault", "faults", "failure", "failures", "exception", "symptom", "issue", "lỗi", "sự", "hỏng", "thất"}

        has_problem = bool(set(text_counts) & problem_words) or any(w in section_text.lower() for w in problem_words)
        has_action = bool(set(text_counts) & action_words) or any(w in section_text.lower() for w in action_words)

        is_repetitive_dump = False
        if len(all_tokens) > 30 and text_counts:
            top_freq = max(text_counts.values())
            is_repetitive_dump = (top_freq / len(all_tokens)) > 0.25

        if intent == "diagnosis":
            if has_problem and has_action and not is_repetitive_dump:
                signals["actionable_diagnosis_match"] = 3.5
            elif has_problem and not has_action:
                signals["unactionable_problem_penalty"] = -0.25

        if intent in ("procedure", "actionable_output"):
            if has_action or "procedure" in section_text.lower() or "quy trình" in section_text.lower():
                signals["procedural_structure_boost"] = 2.0

        if intent in ("lookup", "table"):
            if "table" in element_types or sheet_text:
                signals["lookup_table_boost"] = 1.5

        # Check for repetitive / process log dumps
        if is_repetitive_dump and not has_action:
            signals["repetitive_dump_penalty"] = -4.0
        elif is_repetitive_dump:
            signals["repetitive_dump_penalty"] = -2.0

        score = float(sum(signals.values()))
        if is_repetitive_dump:
            score = min(score, 1.0)
        if score <= 0:
            return None
        coverage = len(matched_terms) / len(terms)
        return score, row, metadata, privacy_labels, signals, matched_terms, coverage

    def __enter__(self) -> "LocalChunkIndex":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
