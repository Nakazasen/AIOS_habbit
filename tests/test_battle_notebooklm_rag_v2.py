from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import battle_notebooklm_rag_v2 as runner


def test_question_set_is_frozen_and_stable():
    assert len(runner.BATTLE_QUESTIONS) == 12
    assert [question["id"] for question in runner.BATTLE_QUESTIONS] == [f"BQ{i:02d}" for i in range(1, 13)]
    assert runner.stable_hash(runner.BATTLE_QUESTIONS) == runner.stable_hash(tuple(runner.BATTLE_QUESTIONS))


def test_local_manifest_fingerprints_files_without_reading_content_into_output(tmp_path: Path):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text("private document content", encoding="utf-8")

    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)

    assert manifest["supported_file_count"] == 1
    assert manifest["files"][0]["sha256"]
    assert "private document content" not in json.dumps(manifest)


def test_duplicate_titles_are_flagged_without_blocking_capability_audit():
    sources = [runner.NotebookSourceRecord("n1", "same.pdf", "pdf", 2, False)]
    local = {
        "all_file_count": 2,
        "business_file_count": 2,
        "unsupported_files": [],
        "files": [
            {"relative_path": "a/same.pdf", "display_name": "same.pdf", "extension": ".pdf", "sha256": "a"},
            {"relative_path": "b/same.pdf", "display_name": "same.pdf", "extension": ".pdf", "sha256": "b"},
        ],
    }

    audit = runner.classify_corpus_capabilities(sources, local)

    assert audit["status"] == "PASS"
    assert audit["ambiguous"][0]["reason"] == "duplicate_title"
    assert audit["shared_count"] == 0


def test_capability_audit_allows_different_source_counts():
    sources = [runner.NotebookSourceRecord("n1", "manual.pdf", "pdf", 2, False)]
    local = {
        "all_file_count": 2,
        "business_file_count": 2,
        "unsupported_files": [],
        "files": [
            {"relative_path": "manual.pdf", "display_name": "manual.pdf", "extension": ".pdf", "sha256": "1"},
            {"relative_path": "native.xlsx", "display_name": "native.xlsx", "extension": ".xlsx", "sha256": "2"},
        ],
    }

    audit = runner.classify_corpus_capabilities(sources, local)

    assert audit["status"] == "PASS"
    assert audit["shared_count"] == 1
    assert [row["relative_path"] for row in audit["aios_native_only"]] == ["native.xlsx"]


def test_workflow_applicability_marks_excel_as_native_per_system():
    question = next(row for row in runner.BATTLE_QUESTIONS if row["category"] == "excel_native")
    local = {"business_file_count": 1, "files": [{"extension": ".xlsx"}]}
    notebook = {"sources": [{"title": "manual.pdf"}]}

    assert runner.workflow_applicability(question, "rag_v2", local, notebook)["applicable"] is True
    assert runner.workflow_applicability(question, "notebooklm", local, notebook) == {
        "applicable": False,
        "reason": "notebook_has_no_native_spreadsheet_source",
    }


def test_key_parser_does_not_depend_on_fixed_line_number(tmp_path: Path):
    key_file = tmp_path / "API Key.txt"
    key_file.write_text("unrelated\nDEEPSEEK_API_KEY=secret-value\n", encoding="utf-8")

    assert runner.read_key_from_file(key_file) == "secret-value"


def test_key_parser_accepts_label_followed_by_value(tmp_path: Path):
    key_file = tmp_path / "API Key.txt"
    key_file.write_text("DeepSeek API Key\nsecret-value\n", encoding="utf-8")

    assert runner.read_key_from_file(key_file) == "secret-value"


def test_blind_assignment_is_deterministic_and_permutations_vary():
    assignments = [runner.blinded_assignment(f"BQ{i:02d}", "question-hash") for i in range(1, 13)]

    assert assignments == [runner.blinded_assignment(f"BQ{i:02d}", "question-hash") for i in range(1, 13)]
    assert all(set(assignment) == {"rag_v2", "workspace_chat", "notebooklm"} for assignment in assignments)
    assert len(set(assignments)) > 1


def test_blind_bundle_contains_all_three_systems():
    question = runner.BATTLE_QUESTIONS[0]
    results = {
        "rag_v2": [{"question_id": question["id"], "status": "success", "answer": "candidate"}],
        "workspace_chat": [{"question_id": question["id"], "status": "success", "answer": "production"}],
        "notebooklm": [{"question_id": question["id"], "status": "success", "answer": "comparison"}],
    }

    bundle, assignment = runner.make_blind_bundle([question], results, "question-hash")

    assert set(assignment[question["id"]].values()) == set(results)
    assert {bundle[0][label] for label in ("system_a", "system_b", "system_c")} == {"candidate", "production", "comparison"}


def test_non_applicable_rows_are_not_quality_review_rows():
    question = runner.BATTLE_QUESTIONS[0]
    row = runner.triage_row(question, {"rag_v2": {"status": "success"}}, {"rag_v2": True, "workspace_chat": False, "notebooklm": False})

    assert row["status"] == "NOT_APPLICABLE"
    assert row["winner"] == "NOT_APPLICABLE"


def test_provider_errors_are_separate_from_quality_review():
    question = runner.BATTLE_QUESTIONS[0]
    row = runner.triage_row(question, {"rag_v2": {"status": "provider_error"}, "notebooklm": {"status": "success"}}, {"rag_v2": True, "workspace_chat": False, "notebooklm": True})

    assert row["status"] == "PROVIDER_ERROR"


def test_retrieval_only_rows_are_not_marked_ready_for_human_quality_review():
    question = runner.BATTLE_QUESTIONS[0]
    results = {system: {"status": "retrieval_only"} for system in ("rag_v2", "workspace_chat")}
    results["notebooklm"] = {"status": "not_queried"}

    row = runner.triage_row(question, results, {system: True for system in results})

    assert row["status"] == "DRY_RUN_ONLY"


def test_question_ids_cli_accepts_bounded_smoke_selection():
    args = runner.parse_args(["--source-root", ".", "--dry-run", "--question-ids", "BQ01,BQ11"])

    assert args.question_ids == "BQ01,BQ11"


def test_notebooklm_query_retries_transient_failure(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(command, timeout_seconds=120):
        calls.append((command, timeout_seconds))
        if len(calls) == 1:
            raise runner.BenchmarkError("temporary timeout")
        return {"answer": "recovered answer"}

    monkeypatch.setattr(runner, "run_json_command", fake_run)

    result = runner.query_notebooklm(
        "question",
        "notebook-id",
        max_attempts=2,
        timeout_seconds=9,
        retry_backoff_seconds=0,
    )

    assert result["status"] == "success"
    assert result["answer"] == "recovered answer"
    assert result["attempt_count"] == 2
    assert [timeout for _, timeout in calls] == [9, 9]


def test_notebooklm_query_stops_after_bounded_attempts(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(command, timeout_seconds=120):
        calls.append((command, timeout_seconds))
        raise runner.BenchmarkError("still unavailable")

    monkeypatch.setattr(runner, "run_json_command", fake_run)

    result = runner.query_notebooklm(
        "question",
        "notebook-id",
        max_attempts=3,
        retry_backoff_seconds=0,
    )

    assert result["status"] == "provider_error"
    assert result["attempt_count"] == 3
    assert len(calls) == 3
    assert "still unavailable" in result["error"]


def test_score_import_rejects_out_of_range_ratings(tmp_path: Path):
    score_file = tmp_path / "scores.json"
    fields = ("correctness", "completeness", "citation_support", "faithfulness", "insufficiency_handling", "actionability", "cross_source_synthesis", "spreadsheet_handling")
    ratings = {field: 3 for field in fields}
    score_file.write_text(json.dumps([{
        "question_id": "BQ01",
        "system_a": {**ratings, "correctness": 6},
        "system_b": ratings,
        "system_c": ratings,
    }]), encoding="utf-8")
    assignment = {"BQ01": {"system_a": "rag_v2", "system_b": "workspace_chat", "system_c": "notebooklm"}}

    with pytest.raises(runner.BenchmarkError, match="Score validation failed"):
        runner.import_scores(score_file, assignment, {"BQ01"})


def test_score_import_calculates_three_system_aggregate_without_raw_answers(tmp_path: Path):
    score_file = tmp_path / "scores.json"
    fields = ("correctness", "completeness", "citation_support", "faithfulness", "insufficiency_handling", "actionability", "cross_source_synthesis", "spreadsheet_handling")
    ratings = {field: 4 for field in fields}
    score_file.write_text(json.dumps([{"question_id": "BQ01", "system_a": ratings, "system_b": {**ratings, "correctness": 3}, "system_c": {**ratings, "correctness": 2}, "reviewer_notes": "reviewed"}]), encoding="utf-8")
    assignment = {"BQ01": {"system_a": "rag_v2", "system_b": "workspace_chat", "system_c": "notebooklm"}}

    result = runner.import_scores(score_file, assignment, {"BQ01"})

    assert result["aggregates"]["rows_scored"] == 1
    assert result["aggregates"]["systems"]["rag_v2"]["wins"] == 1
    assert result["aggregates"]["systems"]["workspace_chat"]["rows_scored"] == 1
    assert "answer" not in json.dumps(result)



def test_workspace_battle_ingestion_preserves_approved_cloud_safe_label(tmp_path: Path):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text("safe benchmark source", encoding="utf-8")
    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)

    sources, coverage = runner.ingest_workspace_sources(tmp_path, manifest, privacy_label="cloud_safe")

    assert coverage["status"] == "PASS"
    assert sources
    assert {source.privacy_label for source in sources} == {"cloud_safe"}


def test_workspace_battle_ingestion_keeps_local_only_non_sendable(tmp_path: Path):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text("local benchmark source", encoding="utf-8")
    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)

    sources, _ = runner.ingest_workspace_sources(tmp_path, manifest, privacy_label="local_only")

    assert sources
    assert {source.privacy_label for source in sources} == {"local_only"}


def test_expansion_fallback_never_routes_without_an_approved_label(tmp_path: Path):
    plan, metadata = runner.expand_query_for_retrieval(
        "neutral question",
        api_key_file=tmp_path / "missing-key.txt",
        privacy_label="local_only",
        cache_dir=tmp_path / "cache",
    )

    assert len(plan.variants) == 1
    assert metadata["status"] == "local_only"



def test_project_root_prefers_canonical_tailieugoc_and_excludes_generated_state(tmp_path: Path):
    canonical = tmp_path / "tailieugoc"
    canonical.mkdir()
    (canonical / "manual.txt").write_text("canonical procedure", encoding="utf-8")
    generated = tmp_path / ".brain" / "runner_artifacts"
    generated.mkdir(parents=True)
    (generated / "prior_answer.txt").write_text("do not benchmark generated answers", encoding="utf-8")
    (tmp_path / "README.md").write_text("project control file", encoding="utf-8")

    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)

    assert manifest["source_root_name"] == "tailieugoc"
    assert [row["relative_path"] for row in manifest["files"]] == ["manual.txt"]
    assert manifest["business_file_count"] == 1


def test_rag_battle_arm_uses_dev_pipeline_without_provider(tmp_path: Path):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text(
        "The project launch date is 2031-04-09 and the launch owner is Operations.",
        encoding="utf-8",
    )
    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)
    sources = runner.build_rag_v2_sources(
        tmp_path,
        manifest,
        privacy_label="cloud_safe",
    )
    config = runner.RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        allowed_privacy_labels=("cloud_safe",),
    )

    with runner.RagV2DevPipeline(config) as pipeline:
        report = pipeline.ingest(sources)
        result = runner.answer_one(
            pipeline,
            sources,
            {
                "id": "BQ-SYNTHETIC",
                "question": "What is the project launch date?",
                "category": "precise_lookup",
                "expected_type": "answerable",
            },
            api_key_file=tmp_path / "missing-key.txt",
            privacy_label="cloud_safe",
            do_synthesis=False,
        )

    assert report.indexed_chunk_count == 1
    assert result["status"] == "retrieval_only"
    assert result["pipeline"]["name"] == "RagV2DevPipeline"
    assert result["pipeline"]["provider_used"] is False
    assert result["item_count"] >= 1


def test_soft_warning_reaches_provider_synthesis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text(
        "The project launch date is 2031-04-09 and the launch owner is Operations.",
        encoding="utf-8",
    )
    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)
    sources = runner.build_rag_v2_sources(
        tmp_path,
        manifest,
        privacy_label="cloud_safe",
    )
    provider_calls = []

    def fake_router_synthesis(question, evidence_pack, **_kwargs):
        provider_calls.append((question, evidence_pack.answer_mode.value))
        return {
            "status": "success",
            "answer": "Grounded provider answer [1]",
            "error": "",
            "route": {"status": "provider_synthesis", "externally_sent": True},
        }

    monkeypatch.setattr(runner, "run_router_synthesis", fake_router_synthesis)
    config = runner.RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        allowed_privacy_labels=("cloud_safe",),
    )
    with runner.RagV2DevPipeline(config) as pipeline:
        pipeline.ingest(sources)
        result = runner.answer_one(
            pipeline,
            sources,
            {
                "id": "BQ-SOFT-WARNING",
                "question": "What is the project launch date and accountable owner?",
                "category": "precise_lookup",
                "expected_type": "answerable",
            },
            api_key_file=tmp_path / "unused-key.txt",
            privacy_label="cloud_safe",
            do_synthesis=True,
        )

    assert result["answer_mode"] == "answer_with_limits"
    assert result["hard_insufficiency_reasons"] == []
    assert result["soft_warning_reasons"]
    assert result["status"] == "success"
    assert result["route"]["status"] == "provider_synthesis"
    assert provider_calls == [
        ("What is the project launch date and accountable owner?", "answer_with_limits")
    ]


def test_router_synthesis_falls_back_when_provider_answer_is_uncited(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text(
        "The project launch date is 2031-04-09 and the launch owner is Operations.",
        encoding="utf-8",
    )
    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)
    sources = runner.build_rag_v2_sources(
        tmp_path,
        manifest,
        privacy_label="cloud_safe",
    )
    config = runner.RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        allowed_privacy_labels=("cloud_safe",),
    )
    with runner.RagV2DevPipeline(config) as pipeline:
        pipeline.ingest(sources)
        pack = pipeline.query("project launch date", sources).evidence_pack

    class FakeRouter:
        def route_outcome(self, _request):
            return SimpleNamespace(
                status="success",
                error_type="",
                attempts=(),
                result=SimpleNamespace(
                    text="The launch date is 2031-04-09.",
                    metadata={},
                    provider_name="fake-provider",
                ),
            )

    import nakazasen_ai_router

    monkeypatch.setattr(runner, "read_key_from_file", lambda _path: "configured")
    monkeypatch.setattr(
        nakazasen_ai_router,
        "create_router_from_env",
        lambda **_kwargs: FakeRouter(),
    )

    result = runner.run_router_synthesis(
        "What is the project launch date?",
        pack,
        api_key_file=tmp_path / "unused-key.txt",
        privacy_label="cloud_safe",
    )

    assert result["status"] == "success"
    assert result["error"] == "provider_citation_validation_failed"
    assert result["route"]["status"] == "provider_validation_fallback"
    assert result["validation"]["valid"] is False
    assert "provider_answer_missing_citations" in result["validation"]["errors"]
    assert "[1]" in result["answer"]


def test_hard_insufficiency_vetoes_provider_synthesis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    source = root / "manual.txt"
    source.write_text("The project launch date is 2031-04-09.", encoding="utf-8")
    manifest = runner.build_local_manifest(tmp_path, allow_partial=True)
    sources = runner.build_rag_v2_sources(
        tmp_path,
        manifest,
        privacy_label="cloud_safe",
    )

    def unexpected_provider_call(*_args, **_kwargs):
        raise AssertionError("hard abstention must veto provider synthesis")

    monkeypatch.setattr(runner, "run_router_synthesis", unexpected_provider_call)
    config = runner.RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        allowed_privacy_labels=("cloud_safe",),
    )
    with runner.RagV2DevPipeline(config) as pipeline:
        pipeline.ingest(sources)
        result = runner.answer_one(
            pipeline,
            sources,
            {
                "id": "BQ-HARD-ABSTAIN",
                "question": "What is the secret recipe for the ancient potion?",
                "category": "insufficient",
                "expected_type": "insufficient",
            },
            api_key_file=tmp_path / "unused-key.txt",
            privacy_label="cloud_safe",
            do_synthesis=True,
        )

    assert result["answer_mode"] == "abstain"
    assert "no_lexical_or_metadata_match" in result["hard_insufficiency_reasons"]
    assert result["route"] == {
        "status": "hard_abstention",
        "externally_sent": False,
    }
    assert result["llm_latency_ms"] == 0.0


def test_live_battle_rejects_local_only_before_network(tmp_path: Path):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    args = runner.parse_args([
        "--source-root",
        str(tmp_path),
        "--run",
        "--privacy-label",
        "local_only",
    ])

    with pytest.raises(
        runner.BenchmarkError,
        match="Live synthesis requires cloud_safe or public sources",
    ):
        runner.run_dry_or_live(
            args,
            {"local_manifest": {}, "corpus_audit": {}},
            live=True,
            output_dir=tmp_path / "output",
        )


def test_dry_preflight_skips_notebook_and_router_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    (root / "manual.txt").write_text("local procedure", encoding="utf-8")
    args = runner.parse_args([
        "--source-root",
        str(tmp_path),
        "--dry-run",
        "--privacy-label",
        "local_only",
        "--allow-partial",
    ])

    def unexpected_external_call(*_args, **_kwargs):
        raise AssertionError("dry preflight attempted an external or credential call")

    monkeypatch.setattr(runner, "verify_notebook", unexpected_external_call)
    monkeypatch.setattr(runner, "router_readiness", unexpected_external_call)

    result = runner.build_preflight(args)

    assert result["status"] == "PASS"
    assert result["mode"] == "local_only"
    assert result["notebook"]["status"] == "SKIPPED_LOCAL_ONLY"
    assert result["router"]["status"] == "SKIPPED_LOCAL_ONLY"
    assert result["router"]["key_configured"] is False
    candidate = result["candidate"]
    assert len(candidate["candidate_fingerprint"]) == 64
    assert len(candidate["synthesis_contract_fingerprint"]) == 64
    assert len(candidate["config_fingerprint"]) == 64
    assert candidate["effective_config"]["router_provider"] == "none"
    assert candidate["effective_config"]["privacy_label"] == "local_only"
    assert set(candidate["file_hashes"]) == set(runner._PROMOTION_CANDIDATE_FILES)


def _reference_fixture(tmp_path: Path) -> tuple[list[dict], dict, Path]:
    questions = [dict(question) for question in runner.BATTLE_QUESTIONS[:2]]
    sources = [{"source_id": "source-1", "title": "manual.pdf", "status": "READY"}]
    manifest = {
        "status": "PASS",
        "notebook_id": runner.NOTEBOOK_ID,
        "title": runner.NOTEBOOK_TITLE,
        "source_count": len(sources),
        "ready_count": len(sources),
        "all_ready": True,
        "sources": sources,
    }
    manifest["manifest_hash"] = runner.stable_hash(sources)
    corpus_fingerprint = "corpus-fingerprint"
    answers = [
        {"status": "success", "answer": "Grounded answer", "latency_ms": 12.0, "error": ""},
        {"status": "not_applicable", "answer": "", "latency_ms": 0.0, "error": "test_not_applicable"},
    ]
    preflight = {
        "notebook_manifest": manifest,
        "local_manifest": {"corpus_fingerprint": corpus_fingerprint, "source_root_name": "tailieugoc"},
        "corpus_audit": {"audit_hash": "audit-hash"},
    }
    snapshot = runner.build_reference_snapshot(preflight, questions, answers, notebook_id=runner.NOTEBOOK_ID)
    path = tmp_path / "notebooklm_reference.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    return questions, snapshot, path


def test_reference_snapshot_round_trips_with_strict_identity(tmp_path: Path):
    questions, snapshot, path = _reference_fixture(tmp_path)

    loaded = runner.load_reference_snapshot(
        path,
        questions,
        notebook_id=runner.NOTEBOOK_ID,
        corpus_fingerprint="corpus-fingerprint",
    )

    assert loaded["snapshot"]["reference_capture_id"] == snapshot["reference_capture_id"]
    assert loaded["answers"]["BQ01"]["answer"] == "Grounded answer"
    assert loaded["answers"]["BQ02"]["status"] == "not_applicable"


@pytest.mark.parametrize("mutation", ["question", "manifest", "duplicate_answer"])
def test_reference_snapshot_rejects_provenance_or_answer_drift(tmp_path: Path, mutation: str):
    questions, snapshot, path = _reference_fixture(tmp_path)
    mutated = json.loads(json.dumps(snapshot))
    if mutation == "question":
        mutated["questions"][0]["question"] = "tampered question"
    elif mutation == "manifest":
        mutated["notebook_manifest"]["sources"][0]["title"] = "tampered.pdf"
    else:
        mutated["answers"].append(dict(mutated["answers"][0]))
    path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(runner.BenchmarkError, match="NotebookLM reference rejected"):
        runner.load_reference_snapshot(
            path,
            questions,
            notebook_id=runner.NOTEBOOK_ID,
            corpus_fingerprint="corpus-fingerprint",
        )


def test_cached_notebooklm_resolution_never_queries_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    questions, snapshot, _ = _reference_fixture(tmp_path)
    calls = []

    def unexpected_query(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("cached algorithm rerun queried NotebookLM")

    monkeypatch.setattr(runner, "query_notebooklm", unexpected_query)
    reference = runner.validate_reference_snapshot(
        snapshot,
        questions,
        notebook_id=runner.NOTEBOOK_ID,
        corpus_fingerprint="corpus-fingerprint",
    )

    result = runner.notebooklm_result_for_run(
        questions[0],
        {"applicable": True},
        live=True,
        reference=reference,
    )

    assert result["reference_mode"] == "cached_reference"
    assert result["status"] == "success"
    assert result["answer"] == "Grounded answer"
    assert calls == []


def test_live_run_requires_reference_before_execution(tmp_path: Path):
    root = tmp_path / "tailieugoc"
    root.mkdir()
    args = runner.parse_args(["--source-root", str(tmp_path), "--run"])

    assert runner.main(["--source-root", str(tmp_path), "--run"]) == 2
    assert args.run is True


def test_reference_snapshot_rejects_notebook_identity_drift(tmp_path: Path):
    questions, _snapshot, path = _reference_fixture(tmp_path)

    with pytest.raises(runner.BenchmarkError, match="notebook_id_mismatch"):
        runner.load_reference_snapshot(
            path,
            questions,
            notebook_id="different-notebook",
            corpus_fingerprint="corpus-fingerprint",
        )

def test_reference_acquisition_adds_question_identity_to_provider_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    questions = [dict(question) for question in runner.BATTLE_QUESTIONS]
    manifest = {
        "status": "PASS",
        "notebook_id": runner.NOTEBOOK_ID,
        "title": runner.NOTEBOOK_TITLE,
        "source_count": 1,
        "ready_count": 1,
        "all_ready": True,
        "sources": [{"source_id": "source-1", "title": "manual.pdf", "status": "READY"}],
    }
    manifest["manifest_hash"] = runner.stable_hash(manifest["sources"])
    preflight = {
        "notebook_manifest": manifest,
        "local_manifest": {"corpus_fingerprint": "corpus-fingerprint", "source_root_name": "tailieugoc"},
        "corpus_audit": {"audit_hash": "audit-hash"},
        "workflow_matrix": [
            {"question_id": question["id"], "systems": {"notebooklm": {"applicable": True}}}
            for question in questions
        ],
    }
    args = SimpleNamespace(
        question_ids="",
        notebook_id=runner.NOTEBOOK_ID,
        reference_output=str(tmp_path / "reference.json"),
    )
    monkeypatch.setattr(runner, "resolve_question_set_path", lambda _args: None)
    monkeypatch.setattr(runner, "load_question_set", lambda _path: questions)
    monkeypatch.setattr(
        runner,
        "query_notebooklm",
        lambda question, _notebook_id: {"status": "success", "answer": f"Answer for {question}", "latency_ms": 1.0, "error": ""},
    )

    result = runner.acquire_notebooklm_reference(args, preflight, tmp_path)
    snapshot = json.loads(Path(result["reference"]).read_text(encoding="utf-8"))

    assert result["notebook_query_count"] == len(questions)
    assert all(row["question_id"] == question["id"] for row, question in zip(snapshot["answers"], questions))
    assert all(row["question"] == question["question"] for row, question in zip(snapshot["answers"], questions))
    runner.validate_reference_snapshot(
        snapshot,
        questions,
        notebook_id=runner.NOTEBOOK_ID,
        corpus_fingerprint="corpus-fingerprint",
    )


def test_reference_acquisition_rejects_noncanonical_question_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    custom_questions = [dict(runner.BATTLE_QUESTIONS[0])]
    args = SimpleNamespace(question_ids="", notebook_id=runner.NOTEBOOK_ID, reference_output=str(tmp_path / "reference.json"))
    monkeypatch.setattr(runner, "resolve_question_set_path", lambda _args: None)
    monkeypatch.setattr(runner, "load_question_set", lambda _path: custom_questions)

    with pytest.raises(runner.BenchmarkError, match="owner-approved complete question set"):
        runner.acquire_notebooklm_reference(args, {"workflow_matrix": []}, tmp_path)
