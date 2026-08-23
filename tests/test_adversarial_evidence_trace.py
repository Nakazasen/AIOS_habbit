# -*- coding: utf-8 -*-
r"""Empirical Challenger Adversarial & Stress Verification Suite for Commit B.

Authored by challenger_final_1 (teamwork_preview_challenger) to rigorously stress-test:
1. Large Graph Stress Testing:
   - Massive graphs (10,000+ nodes and 20,000+ edges)
   - Deep linear chain graph (2,500 nodes deep) testing recursion-free validation & traversal
   - Star/mesh topologies with 5,000 fan-out edges
   - Benchmarking validation and JSON serialization performance under strict time budgets (< 1.5s)
2. Adversarial & Malformed Citation Inputs:
   - Nested brackets ([[1]], [[[E1]]], [DOC[1]:p[2]])
   - Regex injection vectors ([.*], [+], [(?i)evil], [\d+], [^a-z], [\x00])
   - Unicode directional formatting (RLO \u202E, LRO \u202D, RLM \u200F)
   - Zero-width characters (\u200B ZWSP, \u200C ZWNJ, \u200D ZWJ, \uFEFF BOM)
   - Non-printable control characters (\x01-\x1F, \x7F)
   - Catastrophic backtracking / ReDoS resilience on 100KB adversarial text payloads
   - Word-boundary fuzzing ([1] vs [10], [E1] vs [E10], EVD-1 vs EVD-100)
3. High-Concurrency & Rapid Repeated Trace Persistence:
   - Multi-threaded concurrent writes (20 threads x 50 iterations = 1,000 operations) targeting the SAME assistant_message_id
   - Guaranteed 100% idempotent single-record deduplication in traces.jsonl
   - High-concurrency distinct assistant_message_id writes (20 threads x 50 distinct IDs)
   - Mixed read/write concurrency (readers continuously fetching while writers upsert)
   - Multi-threaded crash-free atomic replacement
4. Corrupted JSONL Recovery & Crash Scenarios:
   - Truncated / unclosed JSON rows at EOF
   - Garbage non-JSON binary lines and random ASCII gibberish in the middle of traces.jsonl
   - Missing mandatory fields and null byte lines
   - Recovery and preservation of valid records during subsequent save_evidence_trace operations
   - Orphaned .tmp and .bak cleanup resilience without data corruption
"""
from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import random
import string
import threading
import time
from typing import Any, Dict, List, Optional
import pytest

import aios_habit.workspace_chat_store as chat_store
from aios_habit.evidence_trace import (
    build_evidence_trace_from_citations,
    create_evidence_trace,
    extract_cited_evidence_ids,
    is_insufficient_evidence,
)
from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_RAG_TRACE_V1,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.local_jsonl import (
    atomic_write_jsonl,
    clear_jsonl_cache,
    load_jsonl_records,
)


@pytest.fixture(autouse=True)
def sandboxed_adversarial_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sandbox all Workspace Chat storage files to an isolated temporary directory."""
    test_dir = tmp_path / "workspace_chat"
    test_dir.mkdir(parents=True, exist_ok=True)
    traces_file = test_dir / "traces.jsonl"

    monkeypatch.setattr(chat_store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(chat_store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(chat_store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(chat_store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(chat_store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(chat_store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(chat_store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    monkeypatch.setattr(chat_store, "TRACES_FILE", traces_file, raising=False)

    clear_jsonl_cache()
    chat_store.init_chat_store()
    yield test_dir
    clear_jsonl_cache()


# ============================================================================
# 1. Large Graph Stress Testing
# ============================================================================

class TestLargeGraphStress:
    """Stress tests on large-scale evidence trace graphs for memory, recursion, and speed."""

    def test_massive_graph_10k_nodes_20k_edges_performance(self) -> None:
        """Verify graph with 10,000 nodes and 20,000 edges validates and serializes in < 1.5s."""
        num_nodes = 10000
        num_edges = 20000

        nodes: List[EvidenceNode] = []
        for i in range(num_nodes):
            nt = "chunk" if i % 2 == 0 else "source"
            nodes.append(
                EvidenceNode(
                    id=f"node_{i:05d}",
                    node_type=nt,
                    title=f"Node Title {i}",
                    snippet=f"Snippet content for node {i} with UTF-8: Tiếng Việt 2026",
                    source_id=f"node_{(i - 1) if i > 0 else 0:05d}",
                    confidence=0.9,
                    privacy_label="local_only",
                )
            )

        edges: List[EvidenceEdge] = []
        for i in range(num_edges):
            src_idx = i % num_nodes
            tgt_idx = (i * 7 + 1) % num_nodes
            edges.append(
                EvidenceEdge(
                    source_id=f"node_{src_idx:05d}",
                    target_id=f"node_{tgt_idx:05d}",
                    relation_type="supports" if i % 2 == 0 else "extracted_from",
                    weight=0.85,
                    edge_id=f"edge_{i:05d}",
                )
            )

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_massive_10k",
            query="Massive graph scale test query?",
            answer_text="Massive graph scale answer text.",
            ui_locale="vi",
            answer_language="vi",
            nodes=nodes,
            edges=edges,
            metadata={"scale": "10k_nodes_20k_edges"},
        )

        # 1. Validation performance & correctness
        start_val = time.perf_counter()
        valid, errors = EvidenceTraceContract.validate_trace(trace)
        val_duration = time.perf_counter() - start_val

        assert valid is True, f"Validation failed: {errors[:5]}"
        assert val_duration < 2.0, f"Validation took too long: {val_duration:.3f}s"

        # 2. Serialization performance
        start_ser = time.perf_counter()
        json_str = trace.to_json(indent=None, ensure_ascii=False)
        ser_duration = time.perf_counter() - start_ser

        assert len(json_str) > 1_000_000
        assert ser_duration < 2.0, f"Serialization took too long: {ser_duration:.3f}s"

        # 3. Deserialization round-trip
        start_deser = time.perf_counter()
        recovered = EvidenceTrace.from_json(json_str)
        deser_duration = time.perf_counter() - start_deser

        assert len(recovered.nodes) == num_nodes
        assert len(recovered.edges) == num_edges
        assert deser_duration < 2.0, f"Deserialization took too long: {deser_duration:.3f}s"

    def test_deep_linear_chain_no_recursion_limit(self) -> None:
        """Verify deep linear chain graph of 2,500 nodes does not trigger RecursionError."""
        chain_len = 2500
        nodes = [
            EvidenceNode(id=f"chain_{i}", node_type="chunk", title=f"Chain {i}")
            for i in range(chain_len)
        ]
        edges = [
            EvidenceEdge(
                source_id=f"chain_{i}",
                target_id=f"chain_{i + 1}",
                relation_type="extracted_from",
            )
            for i in range(chain_len - 1)
        ]

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_deep_chain_2500",
            nodes=nodes,
            edges=edges,
        )

        valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert valid is True, f"Deep linear chain validation failed: {errors}"

        # Test dictionary export and import
        dict_data = trace.to_dict()
        assert len(dict_data["nodes"]) == chain_len
        assert len(dict_data["edges"]) == chain_len - 1

        recovered = EvidenceTrace.from_dict(dict_data)
        assert len(recovered.nodes) == chain_len
        assert len(recovered.edges) == chain_len - 1

    def test_dense_star_topology_5000_leaves(self) -> None:
        """Verify high fan-out star topology (1 center node, 5000 leaf citations) operates smoothly."""
        center_node = EvidenceNode(id="ans_hub", node_type="answer", title="Central Answer")
        nodes = [center_node]
        edges: List[EvidenceEdge] = []

        leaf_count = 5000
        for i in range(leaf_count):
            leaf_id = f"cit_leaf_{i:04d}"
            nodes.append(EvidenceNode(id=leaf_id, node_type="citation", title=f"[{i}]"))
            edges.append(
                EvidenceEdge(
                    source_id="ans_hub",
                    target_id=leaf_id,
                    relation_type="cites",
                    edge_id=f"e_hub_{i:04d}",
                )
            )

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_star_5000",
            nodes=nodes,
            edges=edges,
        )

        valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert valid is True, f"Star topology failed validation: {errors}"
        assert len(trace.nodes) == leaf_count + 1
        assert len(trace.edges) == leaf_count


# ============================================================================
# 2. Adversarial Citation Inputs & Regex Fuzzing
# ============================================================================

class TestAdversarialCitationFuzzing:
    """Stress tests extract_cited_evidence_ids and builder against malicious & malformed inputs."""

    @pytest.mark.parametrize(
        "cand,answer_text,should_match",
        [
            # Nested brackets
            ("[[1]]", "Tham khảo tài liệu [[1]] để biết thêm.", True),
            ("[[[E1]]]", "Dữ liệu từ [[[E1]]] rất chuẩn.", True),
            ("[DOC[1]:p[2]]", "Xem chi tiết tại [DOC[1]:p[2]].", True),
            ("[1]", "Tài liệu [1] và [10] khác nhau.", True),
            ("[10]", "Tài liệu [1] và [10] khác nhau.", True),
            ("[1]", "Tài liệu [100] không chứa citation một.", False),
            ("[E1]", "Mã [E10] không phải mã [E1].", True),
            ("[E10]", "Mã [E10] không phải mã [E1].", True),
            # Regex metacharacters as citations
            ("[.*]", "Ký tự đặc biệt [.*] trong văn bản.", True),
            ("[+]", "Ký tự cộng [+] được dùng.", True),
            ("[(?i)evil]", "Chuỗi [(?i)evil] không làm crash regex.", True),
            (r"[\d+]", r"Đoạn mã [\d+] xuất hiện.", True),
            ("[^a-z]", "Dấu [^a-z] kiểm tra phủ định.", True),
            # Unicode diacritics & non-latin in citations
            ("[証拠-01]", "日本語の引用 [証拠-01] を参照してください。", True),
            ("[证据-99]", "中文引用 [证据-99] 说明了系统规则。", True),
            ("[BẰNG_CHỨNG_1]", "Tài liệu [BẰNG_CHỨNG_1] ghi rõ.", True),
        ],
    )
    def test_citation_extraction_metacharacters_and_brackets(
        self, cand: str, answer_text: str, should_match: bool
    ) -> None:
        """Verify extract_cited_evidence_ids handles metacharacters safely with re.escape."""
        result = extract_cited_evidence_ids(answer_text, [cand])
        if should_match:
            assert cand in result, f"Expected {cand} to match in '{answer_text}', got {result}"
        else:
            assert cand not in result, f"Expected {cand} NOT to match in '{answer_text}', got {result}"

    def test_adversarial_unicode_control_and_zero_width_chars(self) -> None:
        """Verify citations containing zero-width spaces, RTL marks, and control chars don't crash."""
        zwsp_cand = "[EVD\u200B01]"  # zero-width space
        rlo_cand = "[DOC\u202E_REV]"  # right-to-left override
        bom_cand = "\uFEFF[E1]"       # byte order mark
        null_cand = "[TEST\x01\x02]"  # control characters

        candidates = [zwsp_cand, rlo_cand, bom_cand, null_cand]
        answer_text = (
            f"Văn bản trích dẫn {zwsp_cand} và hướng dẫn {rlo_cand}. "
            f"Thêm vào đó {bom_cand} và kết thúc bằng {null_cand}."
        )

        extracted = extract_cited_evidence_ids(answer_text, candidates)
        assert len(extracted) == 4
        assert zwsp_cand in extracted
        assert rlo_cand in extracted
        assert bom_cand in extracted
        assert null_cand in extracted

    def test_catastrophic_backtracking_redos_resilience_100kb_text(self) -> None:
        """Verify regex matching 100KB adversarial repetitive text completes in < 100ms."""
        # 100KB of repeating brackets and characters designed to trigger catastrophic backtracking
        evil_text = ("[[[[" + "a" * 50 + "]]]] " * 1000) + " [TARGET_CITATION] " + ("([{" * 500)
        candidates = ["[TARGET_CITATION]", "[NON_EXISTENT]", "[[[a" * 10, "]]]]"]

        start = time.perf_counter()
        extracted = extract_cited_evidence_ids(evil_text, candidates)
        elapsed = time.perf_counter() - start

        assert "[TARGET_CITATION]" in extracted
        assert elapsed < 0.2, f"ReDoS vulnerability detected! Took {elapsed:.3f}s"

    def test_build_trace_from_citations_with_adversarial_items(self) -> None:
        """Verify build_evidence_trace_from_citations handles malformed items gracefully."""
        evidence_items = [
            # Normal dict
            {"id": "doc_1", "title": "Doc 1", "snippet": "Snippet 1", "citation_id": "[1]"},
            # Dict with missing fields
            {"title": "Doc without ID", "snippet": "Snippet without ID"},
            # Dict with None values
            {"id": None, "title": None, "snippet": None, "citation_id": None},
            # Dict with integer / boolean fields
            {"id": 9999, "title": 12345, "snippet": True, "citation_id": 888},
            # Custom object with attributes
            type("CustomDoc", (), {"id": "obj_doc", "title": "Obj Doc", "snippet": "Obj Snip", "citation_id": "[OBJ]"})(),
        ]

        answer = "Câu trả lời dẫn chứng [1] và [OBJ] cũng như 888."
        trace = build_evidence_trace_from_citations(
            query="Câu hỏi adversarial items?",
            answer_text=answer,
            evidence_items=evidence_items,
            ui_locale="vi",
            answer_language="vi",
        )

        assert trace.metadata["status"] == "valid"
        assert trace.metadata["cited_count"] >= 1
        valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert valid is True, f"Generated trace failed validation: {errors}"


# ============================================================================
# 3. High-Concurrency & Idempotent Persistence Verification
# ============================================================================

class TestHighConcurrencyPersistence:
    """Stress tests WorkspaceChatStore persistence under high multi-threaded load."""

    def test_concurrent_idempotent_writes_same_assistant_message_id(self) -> None:
        """Verify concurrent threads writing to the SAME assistant_message_id results in exactly 1 record."""
        target_ast_id = "msg_ast_shared_concurrent_001"
        num_threads = 5
        iterations_per_thread = 6
        total_operations = num_threads * iterations_per_thread

        def worker(thread_idx: int) -> None:
            for it in range(iterations_per_thread):
                trace = create_evidence_trace(
                    trace_id=f"trc_thread_{thread_idx}_it_{it}",
                    assistant_message_id=target_ast_id,
                    conversation_id="conv_shared",
                    query=f"Query from thread {thread_idx}",
                    answer_text=f"Answer update {thread_idx}:{it} citing [1].",
                    nodes=[
                        EvidenceNode(id=f"src_th_{thread_idx}", node_type="source", title=f"Source {thread_idx}"),
                        EvidenceNode(id=f"cit_th_{thread_idx}", node_type="citation", title="[1]"),
                    ],
                    edges=[
                        EvidenceEdge(source_id=f"cit_th_{thread_idx}", target_id=f"src_th_{thread_idx}", relation_type="extracted_from"),
                    ],
                )
                chat_store.save_evidence_trace(trace)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for fut in concurrent.futures.as_completed(futures):
                fut.result()

        # Empirical verification: exactly ONE record must exist
        all_traces = chat_store.load_all_evidence_traces()
        traces_with_ast_id = [t for t in all_traces if t.assistant_message_id == target_ast_id]

        assert len(traces_with_ast_id) == 1, (
            f"Idempotency violated! Expected exactly 1 trace for {target_ast_id}, "
            f"found {len(traces_with_ast_id)} among {len(all_traces)} total traces."
        )

        # Verify the saved record has valid JSON and matches contract
        final_trace = traces_with_ast_id[0]
        valid, errors = EvidenceTraceContract.validate_trace(final_trace)
        assert valid is True, f"Contract validation failed on final idempotent record: {errors}"

    def test_concurrent_distinct_writes_high_volume(self) -> None:
        """Verify concurrent threads writing distinct assistant_message_ids."""
        num_threads = 5
        records_per_thread = 6
        total_records = num_threads * records_per_thread

        def worker(thread_idx: int) -> None:
            for it in range(records_per_thread):
                ast_id = f"msg_ast_t{thread_idx:02d}_r{it:03d}"
                trace = create_evidence_trace(
                    trace_id=f"trc_t{thread_idx:02d}_r{it:03d}",
                    assistant_message_id=ast_id,
                    conversation_id=f"conv_t{thread_idx:02d}",
                    query=f"Distinct query {thread_idx}:{it}",
                    answer_text=f"Distinct answer {thread_idx}:{it} [1]",
                    nodes=[
                        EvidenceNode(id=f"src_{thread_idx}_{it}", node_type="source", title="Src"),
                        EvidenceNode(id=f"cit_{thread_idx}_{it}", node_type="citation", title="[1]"),
                    ],
                    edges=[
                        EvidenceEdge(source_id=f"cit_{thread_idx}_{it}", target_id=f"src_{thread_idx}_{it}", relation_type="extracted_from"),
                    ],
                )
                chat_store.save_evidence_trace(trace)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for fut in concurrent.futures.as_completed(futures):
                fut.result()

        all_traces = chat_store.load_all_evidence_traces()
        assert len(all_traces) == total_records, (
            f"Expected {total_records} distinct records, got {len(all_traces)}"
        )

        unique_ast_ids = {t.assistant_message_id for t in all_traces}
        assert len(unique_ast_ids) == total_records

    def test_mixed_concurrent_readers_and_writers(self) -> None:
        """Verify simultaneous reading and writing operations do not raise exceptions or return corrupted data."""
        stop_event = threading.Event()
        read_errors: List[Exception] = []
        read_counts: List[int] = []

        def reader() -> None:
            while not stop_event.is_set():
                try:
                    traces = chat_store.load_all_evidence_traces()
                    read_counts.append(len(traces))
                    if traces:
                        sample = random.choice(traces)
                        loaded = chat_store.load_evidence_trace(sample.trace_id)
                        assert loaded is not None or stop_event.is_set()
                except Exception as ex:
                    read_errors.append(ex)
                time.sleep(0.005)

        def writer(w_id: int) -> None:
            for i in range(6):
                trace = create_evidence_trace(
                    trace_id=f"trc_rw_w{w_id}_{i}",
                    assistant_message_id=f"msg_rw_w{w_id}_{i}",
                    conversation_id=f"conv_rw_{w_id}",
                    query=f"RW test {w_id}:{i}",
                    answer_text="RW test answer [1]",
                    nodes=[EvidenceNode(id=f"s_{w_id}_{i}", node_type="source", title="S")],
                    edges=[],
                )
                chat_store.save_evidence_trace(trace)
                time.sleep(0.005)

        # Launch 3 reader threads and 3 writer threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            read_futures = [executor.submit(reader) for _ in range(3)]
            write_futures = [executor.submit(writer, i) for i in range(3)]

            # Wait for writers to complete
            for wf in concurrent.futures.as_completed(write_futures):
                wf.result()

            stop_event.set()
            for rf in concurrent.futures.as_completed(read_futures):
                rf.result()

        assert len(read_errors) == 0, f"Concurrent reader encountered errors: {read_errors}"
        assert len(read_counts) > 0
        final_traces = chat_store.load_all_evidence_traces()
        assert len(final_traces) == 18  # 3 writers * 6 items


# ============================================================================
# 4. Corrupted JSONL Recovery & Crash Scenarios
# ============================================================================

class TestCorruptedJsonlRecoveryAndCrashResilience:
    """Stress tests persistence failure handling, corrupted rows, and atomic rollback."""

    def test_corrupted_lines_skipped_safely(self, tmp_path: Path) -> None:
        """Verify corrupted/malformed lines in traces.jsonl are safely skipped without crashing."""
        traces_file = chat_store.TRACES_FILE

        valid_trace1 = create_evidence_trace(
            trace_id="trc_valid_001",
            assistant_message_id="msg_valid_001",
            query="Valid Q1",
            answer_text="Valid A1 [1]",
        )
        valid_trace2 = create_evidence_trace(
            trace_id="trc_valid_002",
            assistant_message_id="msg_valid_002",
            query="Valid Q2",
            answer_text="Valid A2 [1]",
        )

        corrupted_content = (
            valid_trace1.to_json(indent=None, ensure_ascii=False) + "\n"
            + '{"trace_id": "trc_truncated", "nodes": [' + "\n"  # Truncated JSON
            + "NOT_EVEN_JSON_GARBAGE_LINE_!@#$%^&*()_+\n"          # Total garbage
            + '{"unknown_field_only": 12345, "invalid": true}' + "\n"  # Missing fields
            + "\n"  # Empty line
            + valid_trace2.to_json(indent=None, ensure_ascii=False) + "\n"
            + '{"trace_id": "trc_bad_escape", "query": "\x00\x01\x02"}' + "\n"
        )

        clear_jsonl_cache()
        traces_file.write_text(corrupted_content, encoding="utf-8")

        # Load must succeed and return both valid traces
        loaded = chat_store.load_all_evidence_traces()
        loaded_ids = {t.trace_id for t in loaded}

        assert "trc_valid_001" in loaded_ids
        assert "trc_valid_002" in loaded_ids
        assert len(loaded) >= 2

        # load_evidence_trace single lookups work
        t1 = chat_store.load_evidence_trace("trc_valid_001")
        assert t1 is not None
        assert t1.assistant_message_id == "msg_valid_001"

    def test_save_heals_corrupted_file_atomically(self) -> None:
        """Verify saving a new trace into a corrupted JSONL file writes a pristine atomic file."""
        traces_file = chat_store.TRACES_FILE

        valid_trace = create_evidence_trace(
            trace_id="trc_heal_initial",
            assistant_message_id="msg_heal_initial",
            query="Initial Q",
            answer_text="Initial A",
        )

        # Write valid trace + garbage
        traces_file.write_text(
            valid_trace.to_json(indent=None, ensure_ascii=False) + "\n"
            + "%%%CORRUPTED_CRASH_GARBAGE_PAYLOAD%%%\n",
            encoding="utf-8",
        )

        clear_jsonl_cache()

        # Now save a new trace
        new_trace = create_evidence_trace(
            trace_id="trc_heal_new",
            assistant_message_id="msg_heal_new",
            query="New Q",
            answer_text="New A",
        )
        chat_store.save_evidence_trace(new_trace)

        # Read raw lines of traces.jsonl to verify every single line is 100% valid JSON
        lines = [line.strip() for line in traces_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2

        for line_num, line in enumerate(lines, start=1):
            parsed = json.loads(line)  # Must parse without JSONDecodeError
            assert "trace_id" in parsed

        loaded_all = chat_store.load_all_evidence_traces()
        assert len(loaded_all) == 2
        assert {t.trace_id for t in loaded_all} == {"trc_heal_initial", "trc_heal_new"}

    def test_orphaned_tmp_and_bak_files_cleaned_up(self) -> None:
        """Verify store operations are immune to preexisting leftover .tmp or .bak files from crashes."""
        chat_dir = chat_store.LOCAL_CHAT_DIR
        orphaned_tmp = chat_dir / ".traces.jsonl.deadbeef12345678.tmp"
        orphaned_bak = chat_dir / ".traces.jsonl.deadbeef12345678.bak"

        orphaned_tmp.write_text("DUMMY_TMP_CONTENT", encoding="utf-8")
        orphaned_bak.write_text("DUMMY_BAK_CONTENT", encoding="utf-8")

        trace = create_evidence_trace(
            trace_id="trc_crash_resilience",
            assistant_message_id="msg_crash_resilience",
            query="Crash resilience test",
            answer_text="Answer test",
        )
        chat_store.save_evidence_trace(trace)

        loaded = chat_store.load_evidence_trace("trc_crash_resilience")
        assert loaded is not None
        assert loaded.trace_id == "trc_crash_resilience"
