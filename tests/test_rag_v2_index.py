from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
from aios_habit.rag_v2.chunking import StructureAwareChunker
from aios_habit.rag_v2.index import LocalChunkIndex


def make_chunk(text="alpha beta beta", labels=("private",)):
    element = DocumentElement(
        element_id="e1",
        document_id="doc1",
        source_path="/tmp/source.txt",
        source_name="source.txt",
        file_type="txt",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text=text,
        privacy_labels=labels,
        source_fingerprint="fp1",
        page=5,
    )
    return StructureAwareChunker(max_chars=120).chunk_elements([element])[0]


def test_local_index_add_and_search_chunks(tmp_path):
    db_path = tmp_path / "rag_chunks.sqlite"
    chunk = make_chunk()
    with LocalChunkIndex(db_path) as index:
        assert index.upsert_chunks([chunk]) == 1
        results = index.search("beta")
        assert len(results) == 1
        assert results[0].chunk_id == chunk.chunk_id
        assert results[0].score == 2.0
        assert results[0].metadata["page_range"] == [5, 5]
    assert db_path.exists()


def test_upsert_does_not_duplicate_same_chunk_id(tmp_path):
    chunk = make_chunk()
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([chunk])
        index.upsert_chunks([chunk])
        assert index.count() == 1


def test_search_returns_metadata_and_privacy_labels(tmp_path):
    chunk = make_chunk(labels=("private", "review"))
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([chunk])
        result = index.search("alpha")[0]
        assert result.document_id == "doc1"
        assert result.source_name == "source.txt"
        assert result.file_type == "txt"
        assert result.privacy_labels == ("private", "review")
        assert result.metadata["element_ids"] == ["e1"]


def test_empty_query_is_safe(tmp_path):
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([make_chunk()])
        assert index.search("") == []
        assert index.search("   ") == []
        assert index.search("alpha", limit=0) == []


def test_clear_removes_chunks(tmp_path):
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([make_chunk()])
        assert index.count() == 1
        index.clear()
        assert index.count() == 0


def make_ranked_chunk(
    chunk_id,
    document_id,
    text,
    *,
    source_name="notes.txt",
    source_path="/workspace/notes.txt",
    labels=("allowed",),
    element_types=("text",),
    section_path=(),
    fingerprint="v1",
):
    from aios_habit.rag_v2.chunking import DocumentChunk

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source_path=source_path,
        source_name=source_name,
        file_type="txt",
        text=text,
        normalized_text=text.lower(),
        element_ids=(f"element-{chunk_id}",),
        element_types=element_types,
        section_path=section_path,
        privacy_labels=labels,
        source_fingerprint=fingerprint,
        checksum=f"checksum-{chunk_id}",
    )


def test_hybrid_search_promotes_exact_phrase_and_exposes_signals(tmp_path):
    chunks = [
        make_ranked_chunk("partial", "d1", "archive rapid mode reference"),
        make_ranked_chunk("phrase", "d2", "archive mode reference"),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary("archive mode")

    assert [result.chunk_id for result in response.results] == ["phrase", "partial"]
    assert response.results[0].ranking_signals["exact_text_phrase"] == 4.0
    assert response.results[0].term_coverage == 1.0


def test_hybrid_search_uses_generic_source_structure_and_table_signals(tmp_path):
    chunks = [
        make_ranked_chunk("plain", "d1", "planning notes"),
        make_ranked_chunk(
            "structured",
            "d2",
            "planning notes",
            source_name="ledger overview.txt",
            source_path="/workspace/ledger/overview.txt",
            section_path=("Ledger overview",),
        ),
        make_ranked_chunk("table", "d3", "record status", element_types=("table",)),
        make_ranked_chunk("text", "d4", "record status"),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        metadata_results = index.search("planning ledger")
        table_results = index.search("record")

    assert [result.chunk_id for result in metadata_results] == ["structured", "plain"]
    assert metadata_results[0].ranking_signals["source_metadata_match"] == 2.0
    assert metadata_results[0].ranking_signals["structure_metadata_match"] == 1.0
    assert [result.chunk_id for result in table_results] == ["table", "text"]
    assert table_results[0].ranking_signals["table_structure_match"] == 0.5


def test_hybrid_search_filters_privacy_and_stale_fingerprints_before_scoring(tmp_path):
    from aios_habit.rag_v2.index import SearchOptions

    chunks = [
        make_ranked_chunk("allowed", "d1", "shared signal", labels=("allowed",)),
        make_ranked_chunk("restricted", "d2", "shared signal signal", labels=("restricted",)),
        make_ranked_chunk("stale", "d3", "current signal", labels=("stale_only",), fingerprint="version-one"),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        allowed = index.search_with_summary(
            "shared signal",
            options=SearchOptions(allowed_privacy_labels=("allowed",)),
        )
        blocked = index.search_with_summary(
            "shared signal",
            options=SearchOptions(allowed_privacy_labels=("unknown",)),
        )
        selected = index.search_with_summary(
            "shared",
            options=SearchOptions(allowed_document_ids=("d1",)),
        )
        stale = index.search_with_summary(
            "current",
            options=SearchOptions(
                allowed_document_ids=("d3",),
                expected_source_fingerprints={"d3": "version-two"},
            ),
        )

    assert [result.chunk_id for result in allowed.results] == ["allowed"]
    assert allowed.summary.filtered_by_privacy_count == 2
    assert blocked.results == ()
    assert blocked.summary.insufficiency_reasons == ("privacy_filter_excluded_all_chunks",)
    assert [result.chunk_id for result in selected.results] == ["allowed"]
    assert selected.summary.filtered_by_source_count == 2
    assert stale.results == ()
    assert stale.summary.filtered_as_stale_count == 1
    assert "stale_fingerprint_excluded_all_chunks" in stale.summary.insufficiency_reasons


def test_hybrid_search_diversifies_and_is_deterministic(tmp_path):
    chunks = [
        make_ranked_chunk("one-a", "one", "signal detail"),
        make_ranked_chunk("one-b", "one", "signal detail"),
        make_ranked_chunk("one-c", "one", "signal detail"),
        make_ranked_chunk("two-a", "two", "signal detail"),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        first = index.search_with_summary("signal", limit=3)
        second = index.search_with_summary("signal", limit=3)
        tokenless = index.search_with_summary("!?.,")

    assert first == second
    assert [result.document_id for result in first.results] == ["one", "one", "two"]
    assert first.summary.diversity_limited_count == 1
    assert tokenless.results == ()
    assert tokenless.summary.insufficiency_reasons == ("empty_or_tokenless_query",)



def test_multilingual_query_plan_fuses_variant_hits_and_reports_provenance(tmp_path):
    from aios_habit.rag_v2.query_planning import build_query_plan

    chunks = [
        make_ranked_chunk("japanese", "ja", "生産 履歴 登録 システム 構成"),
        make_ranked_chunk("unrelated", "other", "general archive reference"),
    ]
    plan = build_query_plan(
        "What is the production history architecture?",
        {"variants": [{"text": "生産 履歴 登録 システム 構成", "language_hint": "ja", "origin": "translation"}]},
    )
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(plan)

    assert [result.chunk_id for result in response.results] == ["japanese"]
    assert response.results[0].matched_query_variants == ("生産 履歴 登録 システム 構成",)
    assert "multi_variant_rrf" in response.results[0].ranking_signals
    assert response.summary.query_variant_count == 2
    assert response.summary.expansion_status == "expanded"


def test_query_plan_is_deterministic_and_filters_apply_before_variants(tmp_path):
    from aios_habit.rag_v2.index import SearchOptions
    from aios_habit.rag_v2.query_planning import build_query_plan

    plan = build_query_plan(
        "source query",
        {"variants": [{"text": "dịch vụ nội bộ", "language_hint": "vi", "origin": "translation"}]},
    )
    chunks = [
        make_ranked_chunk("allowed", "safe", "dịch vụ nội bộ", labels=("allowed",)),
        make_ranked_chunk("blocked", "blocked", "dịch vụ nội bộ", labels=("restricted",)),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        first = index.search_with_summary(plan, options=SearchOptions(allowed_privacy_labels=("allowed",)))
        second = index.search_with_summary(plan, options=SearchOptions(allowed_privacy_labels=("allowed",)))

    assert first == second
    assert [result.chunk_id for result in first.results] == ["allowed"]
    assert first.summary.filtered_by_privacy_count == 1


def test_invalid_query_expansion_falls_back_without_weakening_abstention(tmp_path):
    from aios_habit.rag_v2.query_planning import build_query_plan

    plan = build_query_plan(
        "exact unsupported protocol",
        {"variants": [{"text": "x" * 241, "language_hint": "ja"}, {"text": "DROP; TABLE chunks", "language_hint": "en"}]},
    )
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([make_ranked_chunk("ordinary", "d1", "ordinary local document")])
        response = index.search_with_summary(plan)

    assert plan.expansion_status == "expansion_rejected"
    assert len(plan.variants) == 1
    assert response.results == ()
    assert "no_lexical_or_metadata_match" in response.summary.insufficiency_reasons


def test_stopword_only_overlap_is_not_retrieval_evidence(tmp_path):
    chunks = [
        make_ranked_chunk("report", "one", "the project will launch in 2026"),
        make_ranked_chunk("guide", "two", "open the application for setup"),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(
            "What is the secret recipe for the ancient potion?"
        )

    assert response.results == ()
    assert response.summary.candidate_count == 0
    assert response.summary.evidence_set_term_coverage == 0.0
    assert response.summary.insufficiency_reasons == (
        "no_lexical_or_metadata_match",
    )


def test_fts_backend_stays_synced_across_replace_and_delete(tmp_path):
    old = make_ranked_chunk("old", "stable", "obsolete token")
    new = make_ranked_chunk("new", "stable", "current token", fingerprint="v2")
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.replace_document_chunks("stable", [old])
        first = index.search_with_summary("obsolete")
        index.replace_document_chunks("stable", [new])
        obsolete = index.search_with_summary("obsolete")
        current = index.search_with_summary("current")
        removed = index.delete_document("stable")
        after_delete = index.search_with_summary("current")

        assert first.summary.candidate_backend == index.retrieval_backend
        assert [result.chunk_id for result in first.results] == ["old"]
        assert obsolete.results == ()
        assert [result.chunk_id for result in current.results] == ["new"]
        assert removed == 1
        assert after_delete.results == ()
        if index.retrieval_backend == "fts5_bm25":
            assert index._conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 0


def test_fts_and_deterministic_fallback_have_equivalent_generic_results(tmp_path):
    chunks = [
        make_ranked_chunk("phrase", "one", "archive mode reference"),
        make_ranked_chunk("partial", "two", "archive rapid mode reference"),
        make_ranked_chunk("other", "three", "unrelated material"),
    ]
    with LocalChunkIndex(tmp_path / "fts.sqlite", enable_fts5=True) as accelerated:
        accelerated.upsert_chunks(chunks)
        fts_response = accelerated.search_with_summary("archive mode")
    with LocalChunkIndex(tmp_path / "fallback.sqlite", enable_fts5=False) as fallback:
        fallback.upsert_chunks(chunks)
        fallback_response = fallback.search_with_summary("archive mode")

    assert [result.chunk_id for result in fts_response.results] == ["phrase", "partial"]
    assert [result.chunk_id for result in fallback_response.results] == ["phrase", "partial"]
    assert [result.score for result in fts_response.results] == [result.score for result in fallback_response.results]
    assert fts_response.summary.evidence_set_term_coverage == fallback_response.summary.evidence_set_term_coverage == 1.0
    assert fallback_response.summary.candidate_backend == "deterministic_scan"


def test_fts_candidate_generation_cannot_bypass_pre_scoring_filters(tmp_path):
    from aios_habit.rag_v2.index import SearchOptions

    chunks = [
        make_ranked_chunk("allowed", "safe", "shared signal", labels=("allowed",)),
        make_ranked_chunk("private", "blocked", "shared signal signal", labels=("restricted",)),
        make_ranked_chunk("stale", "old", "shared signal signal signal", fingerprint="old"),
    ]
    options = SearchOptions(
        allowed_privacy_labels=("allowed", "stale_only"),
        allowed_document_ids=("safe", "old"),
        expected_source_fingerprints={"old": "current"},
    )
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary("shared signal", options=options)

    assert [result.chunk_id for result in response.results] == ["allowed"]
    assert response.summary.filtered_by_source_count == 1
    assert response.summary.filtered_as_stale_count == 1
    assert all(result.document_id not in {"blocked", "old"} for result in response.results)


def test_evidence_set_coverage_combines_complementary_results(tmp_path):
    chunks = [
        make_ranked_chunk("alpha", "one", "alpha detail"),
        make_ranked_chunk("omega", "two", "omega detail"),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary("alpha omega", limit=2)

    assert {result.chunk_id for result in response.results} == {"alpha", "omega"}
    assert response.summary.best_term_coverage == 0.5
    assert response.summary.evidence_set_term_coverage == 1.0
    assert "incomplete_query_term_coverage" not in response.summary.insufficiency_reasons


def test_structural_query_facets_are_deterministic_and_bounded():
    from aios_habit.rag_v2.query_planning import identity_query_plan

    query = "alpha protocol; omega checklist; delta owner; gamma deadline; extra note"
    first = identity_query_plan(query)
    second = identity_query_plan(query)

    assert first == second
    assert first.expansion_status == "faceted"
    assert len(first.variants) == 5  # original plus four bounded facets
    assert first.facet_ids == ("query", "facet_1", "facet_2", "facet_3", "facet_4")
    assert [item.variant_id for item in first.variants] == [
        "query_original",
        "facet_1",
        "facet_2",
        "facet_3",
        "facet_4",
    ]


def test_facet_aware_retrieval_preserves_coverage_with_tight_budget(tmp_path):
    from aios_habit.rag_v2.query_planning import identity_query_plan

    chunks = [
        make_ranked_chunk("alpha", "one", "alpha protocol details"),
        make_ranked_chunk("omega", "two", "omega checklist details"),
        make_ranked_chunk("noise", "three", "unrelated archive"),
    ]
    plan = identity_query_plan("alpha protocol; omega checklist")
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(plan, limit=2)

    assert [result.chunk_id for result in response.results] == ["alpha", "omega"]
    assert response.summary.planned_facet_ids == ("query", "facet_1", "facet_2")
    assert response.summary.covered_facet_ids == ("query", "facet_1", "facet_2")
    assert response.summary.missing_facet_ids == ()
    assert response.results[0].matched_query_facets == ("query", "facet_1")
    assert response.results[1].matched_query_facets == ("query", "facet_2")


def test_diagnosis_intent_penalizes_raw_dumps_and_promotes_actionable_guides(tmp_path):
    from aios_habit.rag_v2.query_planning import identity_query_plan

    raw_dump_text = (
        "process process process process process log dump bop bop bop bop bop bop "
        "bop bop bop bop bop bop bop bop bop bop bop bop bop bop bop bop bop bop"
    )
    actionable_guide_text = (
        "Process Error Handling Guide: When process failure or fault occurs, "
        "check error code and execute resolution step."
    )
    chunks = [
        make_ranked_chunk("dump_chunk", "doc1", raw_dump_text),
        make_ranked_chunk("action_chunk", "doc2", actionable_guide_text),
    ]

    plan = identity_query_plan("What errors occur in the process and how to handle them?")
    assert plan.intent_category == "diagnosis"

    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(plan, limit=2)

    assert [result.chunk_id for result in response.results] == ["action_chunk", "dump_chunk"]
    assert "actionable_diagnosis_match" in response.results[0].ranking_signals
    assert "repetitive_dump_penalty" in response.results[1].ranking_signals


def test_diagnosis_dump_resistance_caps_repeated_query_terms(tmp_path):
    from aios_habit.rag_v2.query_planning import identity_query_plan

    chunks = [
        make_ranked_chunk("dump", "d1", "process error handling " * 80),
        make_ranked_chunk(
            "guide",
            "d2",
            "Process failure: check the logs, then restart the worker to recover.",
        ),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(
            identity_query_plan("process error handling"), limit=2
        )

    assert response.results[0].chunk_id == "guide"
    assert "lexical_frequency_capped" in response.results[1].ranking_signals
    assert "repetitive_dump_penalty" in response.results[1].ranking_signals


def test_diagnosis_retrieval_exposes_stable_obligation_coverage(tmp_path):
    from aios_habit.rag_v2.query_planning import identity_query_plan

    chunks = [
        make_ranked_chunk("problem", "d1", "A service outage causes an error."),
        make_ranked_chunk("check", "d2", "Check the logs and verify service status."),
        make_ranked_chunk("action", "d3", "Restart the worker to recover service."),
    ]
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(
            identity_query_plan("Why is the service unavailable and how do I recover?"),
            limit=3,
        )

    assert response.summary.planned_obligation_ids == ("problem", "check", "action")
    assert response.summary.covered_obligation_ids == ("problem", "check", "action")
    assert response.summary.missing_obligation_ids == ()
    assert all(result.matched_obligations for result in response.results)
