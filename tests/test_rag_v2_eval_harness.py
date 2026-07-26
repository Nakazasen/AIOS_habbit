import json

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import LocalChunkIndex
from aios_habit.rag_v2.eval_harness import (
    BenchmarkConfig,
    BenchmarkQuestion,
    BenchmarkSummary,
    benchmark_summary_to_dict,
    format_benchmark_summary,
    run_benchmark,
    summarize_results,
    BenchmarkResult,
)


def _build_index(tmp_path, chunks):
    """Build an in-memory LocalChunkIndex from generic DocumentChunk objects."""
    db_path = tmp_path / "test_eval.db"
    index = LocalChunkIndex(db_path)
    index.upsert_chunks(chunks)
    return index


def _generic_chunks():
    """Synthetic generic chunks — no protected terms."""
    return [
        DocumentChunk(
            chunk_id="c-report-1",
            document_id="doc-report",
            source_path="/workspace/report.txt",
            source_name="Annual Report",
            file_type="txt",
            text="The project will launch in Q3 2026. Budget is approved.",
            normalized_text="the project will launch in q3 2026 budget is approved",
            element_ids=("e1",),
            element_types=("text",),
            privacy_labels=("cloud_safe",),
            source_fingerprint="fp-report-1",
            metadata={},
        ),
        DocumentChunk(
            chunk_id="c-finance-1",
            document_id="doc-finance",
            source_path="/workspace/finance.csv",
            source_name="Finance Data",
            file_type="csv",
            text="Revenue target is five million. Internal only.",
            normalized_text="revenue target is five million internal only",
            element_ids=("e2",),
            element_types=("table",),
            privacy_labels=("local_only",),
            source_fingerprint="fp-finance-1",
            metadata={},
        ),
        DocumentChunk(
            chunk_id="c-guide-1",
            document_id="doc-guide",
            source_path="/workspace/guide.md",
            source_name="User Guide",
            file_type="md",
            text="Step 1: Open the application. Step 2: Select sources.",
            normalized_text="step 1 open the application step 2 select sources",
            element_ids=("e3",),
            element_types=("text",),
            privacy_labels=("cloud_safe",),
            source_fingerprint="fp-guide-1",
            metadata={},
        ),
    ]


def _generic_questions():
    return [
        BenchmarkQuestion(
            question_id="Q1",
            question="When will the project launch?",
            expected_answer_type="answerable",
            expected_chunk_ids=("c-report-1",),
            expected_document_ids=("doc-report",),
            expected_source_names=("Annual Report",),
            expected_privacy="cloud_safe",
        ),
        BenchmarkQuestion(
            question_id="Q2",
            question="What is the revenue target?",
            expected_answer_type="answerable",
            expected_chunk_ids=("c-finance-1",),
            expected_document_ids=("doc-finance",),
            expected_source_names=("Finance Data",),
            expected_privacy="local_only",
        ),
        BenchmarkQuestion(
            question_id="Q3",
            question="How to open the application?",
            expected_answer_type="answerable",
            expected_chunk_ids=("c-guide-1",),
            expected_document_ids=("doc-guide",),
            expected_source_names=("User Guide",),
        ),
        BenchmarkQuestion(
            question_id="Q4",
            question="What is the secret recipe for the ancient potion?",
            expected_answer_type="insufficient",
        ),
    ]


# --- Full pipeline PASS -----------------------------------------------------

def test_full_pipeline_pass(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    questions = _generic_questions()
    summary = run_benchmark(index, questions)

    assert summary.question_count == 4
    assert summary.answerable_count == 3
    assert summary.insufficient_count == 1
    assert summary.benchmark_id.startswith("BMK-")
    assert summary.retrieval_hit_rate >= 0.0
    assert summary.privacy_pass_rate == 1.0
    assert summary.grounded_answer_rate == 1.0
    assert summary.citation_validity_rate == 1.0
    assert summary.abstention_accuracy == 1.0
    assert summary.local_execution_pass_rate == 1.0
    assert all(result.local_execution_ok for result in summary.results)
    assert summary.pass_fail in {"PASS", "FAIL", "PASS_WITH_WARNINGS"}


# --- Hit@k miss detection --------------------------------------------------

def test_hit_miss_detected(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    questions = [
        BenchmarkQuestion(
            question_id="MISS",
            question="project launch timeline",
            expected_answer_type="answerable",
            expected_chunk_ids=("nonexistent-chunk",),
            expected_document_ids=("nonexistent-doc",),
        ),
    ]
    summary = run_benchmark(index, questions)

    assert summary.results[0].hit_expected_chunk is False
    assert summary.results[0].hit_expected_document is False
    assert summary.results[0].primary_error_class == "CANDIDATE_RECALL_MISS"
    assert summary.results[0].retrieval_candidate_count == 1
    assert summary.results[0].retrieval_result_count == 1
    assert summary.results[0].planned_facet_count == 1
    assert summary.results[0].covered_facet_count == 1
    assert summary.results[0].missing_facet_count == 0
    assert summary.retrieval_hit_rate == 0.0


# --- Insufficiency detection ------------------------------------------------

def test_insufficiency_correctly_detected(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    questions = [
        BenchmarkQuestion(
            question_id="INSUF",
            question="quantum teleportation warp drive specifications",
            expected_answer_type="insufficient",
        ),
    ]
    summary = run_benchmark(index, questions)

    assert summary.results[0].insufficiency_detected is True
    assert summary.results[0].answer_mode == "abstain"
    assert "no_lexical_or_metadata_match" in (
        summary.results[0].hard_insufficiency_reasons
    )
    assert "no_evidence_items" in summary.results[0].hard_insufficiency_reasons
    assert summary.results[0].primary_error_class == ""
    assert summary.insufficiency_detection_rate == 1.0


# --- Privacy compliance -----------------------------------------------------

def test_privacy_local_only_passes(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    questions = [
        BenchmarkQuestion(
            question_id="PRIV",
            question="revenue target",
            expected_answer_type="answerable",
            expected_document_ids=("doc-finance",),
            expected_privacy="local_only",
        ),
    ]
    summary = run_benchmark(index, questions)
    assert summary.results[0].privacy_ok is True


# --- Forbidden term violation -----------------------------------------------

def test_forbidden_term_violation(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    questions = [
        BenchmarkQuestion(
            question_id="FORBID",
            question="project launch budget",
            expected_answer_type="answerable",
            expected_document_ids=("doc-report",),
            forbidden_terms=("budget",),
        ),
    ]
    summary = run_benchmark(index, questions)

    assert summary.results[0].forbidden_term_found is True
    assert "budget" in summary.results[0].forbidden_terms_present
    assert summary.results[0].primary_error_class == "PRIVACY_OR_STALE_BREACH"


# --- Stable benchmark ID ---------------------------------------------------

def test_stable_benchmark_id(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    questions = _generic_questions()

    config1 = BenchmarkConfig(top_k=5)
    config2 = BenchmarkConfig(top_k=10)

    s1 = run_benchmark(index, questions, config1)
    s2 = run_benchmark(index, questions, config1)
    s3 = run_benchmark(index, questions, config2)

    assert s1.benchmark_id == s2.benchmark_id
    assert s1.benchmark_id != s3.benchmark_id


# --- Summary formatting ----------------------------------------------------

def test_summary_formatting(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    summary = run_benchmark(index, _generic_questions())
    text = format_benchmark_summary(summary)

    assert summary.benchmark_id in text
    assert summary.pass_fail in text
    assert "Retrieval Hit Rate" in text
    assert "Grounded Answer Rate" in text
    assert "Citation Validity Rate" in text
    assert "Abstention Accuracy" in text
    assert "Local Execution Pass Rate" in text
    assert "not LLM generation" in text


# --- Serialization ----------------------------------------------------------

def test_summary_serialization(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    summary = run_benchmark(index, _generic_questions())
    d = benchmark_summary_to_dict(summary)

    assert isinstance(d, dict)
    assert isinstance(d["results"], list)
    assert d["benchmark_id"].startswith("BMK-")
    assert d["grounded_answer_rate"] == 1.0
    assert d["citation_validity_rate"] == 1.0
    assert d["abstention_accuracy"] == 1.0
    assert d["local_execution_pass_rate"] == 1.0
    assert d["results"][0]["answer_mode"] in {
        "answer",
        "answer_with_limits",
        "abstain",
    }
    assert isinstance(d["results"][0]["hard_insufficiency_reasons"], list)
    assert d["results"][0]["planned_facet_count"] == 1
    assert d["results"][0]["covered_facet_count"] == 1
    assert d["results"][0]["missing_facet_count"] == 0
    assert "primary_error_class" in d["results"][0]
    # Verify JSON roundtrip works
    json_str = json.dumps(d)
    assert "BMK-" in json_str


# --- Config threshold FAIL --------------------------------------------------

def test_config_threshold_causes_fail():
    strict_config = BenchmarkConfig(min_retrieval_hit_rate=1.0)
    result = BenchmarkResult(
        question_id="A",
        question="q",
        expected_answer_type="answerable",
        hit_expected_chunk=False,
        hit_expected_document=False,
        privacy_ok=True,
    )
    summary = summarize_results([result], strict_config)
    assert summary.pass_fail == "FAIL"
    assert any("hit rate" in w.lower() for w in summary.warnings)


def test_provider_execution_is_a_hard_failure():
    result = BenchmarkResult(
        question_id="LOCAL-ONLY",
        question="q",
        expected_answer_type="answerable",
        hit_expected_chunk=True,
        hit_expected_document=True,
        hit_expected_source=True,
        synthesis_grounded=True,
        citation_valid=True,
        local_execution_ok=False,
        privacy_ok=True,
    )
    summary = summarize_results(
        [result],
        BenchmarkConfig(
            min_retrieval_hit_rate=1.0,
            min_document_hit_rate=1.0,
            min_citation_source_hit_rate=1.0,
            min_grounded_answer_rate=1.0,
            min_citation_validity_rate=1.0,
        ),
    )

    assert summary.local_execution_pass_rate == 0.0
    assert summary.pass_fail == "FAIL"
    assert any("Local execution pass rate" in warning for warning in summary.warnings)


# --- No output files --------------------------------------------------------

def test_no_output_files_created(tmp_path):
    index = _build_index(tmp_path, _generic_chunks())
    before = set(tmp_path.iterdir())
    run_benchmark(index, _generic_questions())
    after = set(tmp_path.iterdir())

    # Only the database file should exist (created by _build_index)
    new_files = after - before
    assert len(new_files) == 0
