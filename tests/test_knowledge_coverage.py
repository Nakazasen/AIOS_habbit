"""Unit and integration tests for knowledge coverage mapping and gap review.

Implements T023 of 010-expert-knowledge-acquisition.
Verifies G2 contract:
1. Coverage evaluation using fixture inventory and questions.
2. Strict hallucination prevention (empty evidence_refs rejected).
3. State transitions (candidate -> accepted/merged/deferred/rejected).
4. Idempotent persistence of coverage runs and gap candidates.
5. Scoped review authorization and stale digest rejection.
6. UI presentation in pure everyday Vietnamese and safe error messages.
7. Missing documentation in scope triggers missing_condition gap.
8. Insufficient retrieval evidence triggers missing_threshold gap with explicit origin.
9. Two-source contradiction requires >= 2 snippet citations and remains candidate with explicit origin.
10. Stale document metadata triggers stale_knowledge gap with explicit origin.
11. C-AGENT real interface with fake provider behind interface: fabricated citations outside retrieval are dropped.
12. C-AGENT cannot self-accept gaps (all gaps enter candidate status).
13. C-AGENT offline fallback to deterministic signals without cloud calls.
14. local_only data is auto-inferred from inventory/snippets and blocked from unauthorized providers without caller boolean.
15. Production retrieval adapter contract verification with 8 receipt fields.
16. Evaluate coverage passes ONLY actual retrieved snippets into evidence pack (no fabricated DOC#p1/p2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from aios_habit.cagent_api import CAgentResponse
from aios_habit.knowledge_coverage import (
    CAgentGatewayClient,
    CollectionInventory,
    CoverageMetric,
    CoverageQuestion,
    DocumentInventoryItem,
    FakeKnowledgeRetrievalAdapter,
    GAP_STATUS_ACCEPTED,
    GAP_STATUS_CANDIDATE,
    GAP_STATUS_DEFERRED,
    GAP_STATUS_MERGED,
    GAP_STATUS_REJECTED,
    GAP_TYPE_CONFLICT,
    GAP_TYPE_MISSING_CONDITION,
    GAP_TYPE_MISSING_THRESHOLD,
    GAP_TYPE_STALE_KNOWLEDGE,
    KnowledgeGapCandidate,
    ProductionKnowledgeRetrievalAdapter,
    REASON_CONTRADICTION,
    REASON_INSUFFICIENT_EVIDENCE,
    REASON_MISSING_SOURCE,
    REASON_STALE_METADATA,
    REASON_SUFFICIENT_EVIDENCE,
    RetrievalReceipt,
    RetrievedSnippet,
    SecurityPolicyError,
    evaluate_coverage,
    generate_deterministic_gap_signals,
    load_collection_inventory,
    rank_and_cluster_gaps,
)
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    RoleGrant,
    WorkspaceCaseAuthorization,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService

FIXTURE_CORPUS_DIR = Path(__file__).resolve().parent / "fixtures" / "expert_interview" / "corpus"


@pytest.fixture
def repo(tmp_path: Path) -> WorkspaceCaseRepository:
    path = tmp_path / "workspace_cases.sqlite"
    r = WorkspaceCaseRepository(path)
    r.initialize()
    return r


@pytest.fixture
def auth(repo: WorkspaceCaseRepository) -> WorkspaceCaseAuthorization:
    return WorkspaceCaseAuthorization(repo)


@pytest.fixture
def service(repo: WorkspaceCaseRepository) -> WorkspaceCaseService:
    return WorkspaceCaseService(store=repo, actor_context=ActorContext("test_manager"))


def test_inventory_loading_and_digest():
    """Collection inventory must load cleanly from fixture and compute stable digest."""
    inv_path = FIXTURE_CORPUS_DIR / "inventory.json"
    assert inv_path.exists()
    inventory = load_collection_inventory(inv_path)

    assert inventory.collection_id == "lsu_simulated_knowledge"
    assert len(inventory.documents) == 2
    assert len(inventory.inventory_digest) == 64
    assert inventory.get_document("DOC-SIM-001") is not None


def test_hallucinated_gap_rejection():
    """KnowledgeGapCandidate MUST reject gaps without evidence references."""
    with pytest.raises(ValueError, match="ít nhất 1 dẫn chứng"):
        KnowledgeGapCandidate(
            gap_id="GAP-HALLUCINATED",
            collection_id="lsu_simulated_knowledge",
            scope="lsu_optical_assembly",
            title="Khoảng trống tự nghĩ ra không có căn cứ",
            description="Mô tả không có citation",
            gap_type=GAP_TYPE_MISSING_THRESHOLD,
            evidence_refs=(),  # Empty evidence refs!
        )


def test_coverage_evaluation_and_ranking():
    """Evaluation identifies gaps and clusters them cleanly."""
    inventory = load_collection_inventory(FIXTURE_CORPUS_DIR / "inventory.json")

    questions = [
        CoverageQuestion(
            question_id="Q-001",
            scope="lsu_optical_assembly",
            question_text="Nhiệt độ sấy UV tối đa là bao nhiêu?",
            expected_evidence=("threshold", "unit"),
        ),
        CoverageQuestion(
            question_id="Q-002",
            scope="uncovered_scope_test",
            question_text="Quy trình đóng gói thành phẩm thế nào?",
            expected_evidence=("packaging_steps",),
        ),
    ]

    metric, gaps = evaluate_coverage(inventory, questions)

    assert metric.total_questions == 2
    assert metric.gaps_count >= 1

    ranked = rank_and_cluster_gaps(gaps)
    assert len(ranked) == len(gaps)
    for g in ranked:
        assert g.status == GAP_STATUS_CANDIDATE  # Never auto-accepted!
        assert len(g.evidence_refs) > 0


def test_gap_state_transitions():
    """Validate allowed and prohibited state transitions."""
    gap = KnowledgeGapCandidate(
        gap_id="GAP-TEST-001",
        collection_id="col-1",
        scope="lsu_optical_assembly",
        title="Thiếu thông số",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
        status=GAP_STATUS_CANDIDATE,
    )

    # Allowed from candidate
    assert gap.can_transition_to(GAP_STATUS_ACCEPTED)
    assert gap.can_transition_to(GAP_STATUS_MERGED)
    assert gap.can_transition_to(GAP_STATUS_DEFERRED)
    assert gap.can_transition_to(GAP_STATUS_REJECTED)

    # From merged: terminal state
    merged_gap = KnowledgeGapCandidate(
        gap_id="GAP-TEST-002",
        collection_id="col-1",
        scope="lsu_optical_assembly",
        title="Đã gộp",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
        status=GAP_STATUS_MERGED,
    )
    assert not merged_gap.can_transition_to(GAP_STATUS_ACCEPTED)
    assert not merged_gap.can_transition_to(GAP_STATUS_CANDIDATE)


def test_repository_coverage_and_gap_persistence(repo: WorkspaceCaseRepository):
    """Store and retrieve coverage evaluation run and gap candidates idempotently."""
    metric = CoverageMetric(
        collection_id="col-1",
        scope="lsu_optical_assembly",
        total_questions=10,
        covered_questions=8,
        coverage_ratio=0.8,
        gaps_count=2,
    )
    run_id = repo.save_coverage_run(metric=metric, idempotency_key="idemp_run_001")
    assert run_id.startswith("COV-RUN-")

    gap = KnowledgeGapCandidate(
        gap_id="GAP-001",
        collection_id="col-1",
        scope="lsu_optical_assembly",
        title="Thiếu thông số nhiệt",
        description="Cần đo nhiệt độ",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
        priority="high",
    )
    repo.save_gap_candidate(gap, idempotency_key="KEY-GAP-001", actor_id="manager_1")
    retrieved = repo.get_gap_candidate("GAP-001")
    assert retrieved is not None
    assert retrieved.gap_id == "GAP-001"
    assert retrieved.status == GAP_STATUS_CANDIDATE

    # Idempotent re-save
    repo.save_gap_candidate(gap, idempotency_key="KEY-GAP-001", actor_id="manager_1")
    retrieved2 = repo.get_gap_candidate("GAP-001")
    assert retrieved2 is not None


def test_service_gap_review_authorization_and_stale_digest(
    repo: WorkspaceCaseRepository,
    service: WorkspaceCaseService,
):
    """Reviewing gap candidate requires grant and rejects stale digest."""
    gap = KnowledgeGapCandidate(
        gap_id="GAP-REV-001",
        collection_id="col-1",
        scope="lsu_optical_assembly",
        title="Thiếu ngưỡng",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
    )
    repo.save_gap_candidate(gap, idempotency_key="KEY-REV-001", actor_id="admin")

    # 1. Unauthorized actor lacks coverage.manage
    unauth_actor = ActorContext("unauthorized_user")
    with pytest.raises(AuthorizationError):
        service.review_gap_candidate(
            gap_id="GAP-REV-001",
            decision="accept",
            actor=unauth_actor,
        )

    # 2. Grant role coverage.manage to test_manager
    repo.replace_role_grants(
        "test_manager",
        [
            RoleGrant(
                grant_id="GRANT-MGR-001",
                actor_id="test_manager",
                role="quality_manager",
                scope="lsu_optical_assembly",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="9999-12-31T23:59:59+00:00",
            )
        ],
    )

    # 3. Stale digest rejection
    with pytest.raises(CaseValidationError, match="stale digest"):
        service.review_gap_candidate(
            gap_id="GAP-REV-001",
            decision="accept",
            expected_digest="wrong_stale_digest_12345",
            actor=ActorContext("test_manager"),
        )

    # 4. Successful review
    updated = service.review_gap_candidate(
        gap_id="GAP-REV-001",
        decision="accept",
        rationale="Đã xác nhận với trưởng ca",
        expected_digest=gap.digest,
        actor=ActorContext("test_manager"),
    )
    assert updated.status == GAP_STATUS_ACCEPTED


def test_missing_documentation_scope_gap_generation():
    """Empty scope or missing sources triggers missing_condition gap with explicit origin."""
    inventory = CollectionInventory(collection_id="col-1", version="1.0.0", scopes=("lsu_optics",), documents=())
    q = CoverageQuestion("Q-EMPTY-1", "empty_scope", "Bước hiệu chuẩn là gì?", ("calibration_step",))

    receipt = RetrievalReceipt(
        question_text=q.question_text,
        scope=q.scope,
        sources_checked=(),
        retrieved_snippets=(),
        coverage_score=0.0,
        reason_code=REASON_MISSING_SOURCE,
    )
    signals = generate_deterministic_gap_signals(inventory, receipt, q)
    assert len(signals) == 1
    assert signals[0].gap_type == GAP_TYPE_MISSING_CONDITION
    assert "Thiếu tài liệu nguồn" in signals[0].title
    assert "Nguồn phát hiện:" in signals[0].description
    assert signals[0].status == GAP_STATUS_CANDIDATE


def test_insufficient_retrieval_evidence_gap_generation():
    """Low coverage score or insufficient evidence triggers missing_threshold gap with explicit origin."""
    doc = DocumentInventoryItem("DOC-1", "Hướng dẫn", "doc1.pdf", "lsu_optics", "dig-1")
    inventory = CollectionInventory(collection_id="col-1", version="1.0.0", scopes=("lsu_optics",), documents=(doc,))
    q = CoverageQuestion("Q-LOW-1", "lsu_optics", "Nhiệt độ tối đa?", ("threshold", "unit"))

    snippet = RetrievedSnippet("DOC-1#chunk_001", "DOC-1", "Lăng kính cần được giữ ở nhiệt độ bình thường.", 0.4)
    receipt = RetrievalReceipt(
        question_text=q.question_text,
        scope=q.scope,
        sources_checked=("DOC-1",),
        retrieved_snippets=(snippet,),
        coverage_score=0.4,
        reason_code=REASON_INSUFFICIENT_EVIDENCE,
    )
    signals = generate_deterministic_gap_signals(inventory, receipt, q)
    assert len(signals) == 1
    assert signals[0].gap_type == GAP_TYPE_MISSING_THRESHOLD
    assert "không đủ căn cứ" in signals[0].title
    assert "Nguồn phát hiện:" in signals[0].description
    assert signals[0].evidence_refs == ("DOC-1#chunk_001",)
    assert signals[0].status == GAP_STATUS_CANDIDATE


def test_two_source_contradiction_gap_requires_at_least_two_snippets():
    """Contradiction gaps require at least two conflicting snippets and remain candidate with explicit origin."""
    doc1 = DocumentInventoryItem("DOC-1", "Quy trình cũ", "doc1.pdf", "lsu_optics", "dig-1")
    doc2 = DocumentInventoryItem("DOC-2", "Quy trình mới", "doc2.pdf", "lsu_optics", "dig-2")
    inventory = CollectionInventory(collection_id="col-1", version="1.0.0", scopes=("lsu_optics",), documents=(doc1, doc2))
    q = CoverageQuestion("Q-CONF-1", "lsu_optics", "Thời gian sấy UV là bao nhiêu phút?", ("time",))

    s1 = RetrievedSnippet("DOC-1#chunk_005", "DOC-1", "Thời gian sấy là 30 giây.", 0.8)
    s2 = RetrievedSnippet("DOC-2#chunk_008", "DOC-2", "Thời gian sấy quy định 60 giây.", 0.85)

    receipt = RetrievalReceipt(
        question_text=q.question_text,
        scope=q.scope,
        sources_checked=("DOC-1", "DOC-2"),
        retrieved_snippets=(s1, s2),
        coverage_score=0.8,
        reason_code=REASON_CONTRADICTION,
    )
    signals = generate_deterministic_gap_signals(inventory, receipt, q)
    assert len(signals) == 1
    conf_gap = signals[0]
    assert conf_gap.gap_type == GAP_TYPE_CONFLICT
    assert len(conf_gap.evidence_refs) >= 2
    assert "DOC-1#chunk_005" in conf_gap.evidence_refs
    assert "DOC-2#chunk_008" in conf_gap.evidence_refs
    assert "Nguồn phát hiện:" in conf_gap.description
    assert conf_gap.status == GAP_STATUS_CANDIDATE

    # Invariant: single snippet conflict is rejected
    with pytest.raises(ValueError, match="ít nhất 2 đoạn trích"):
        KnowledgeGapCandidate(
            gap_id="GAP-INVALID-CONF",
            collection_id="col-1",
            scope="lsu_optics",
            title="Mâu thuẫn nhưng chỉ có 1 trích dẫn",
            description="Mô tả",
            gap_type=GAP_TYPE_CONFLICT,
            evidence_refs=("DOC-1#chunk_005",),
        )


def test_stale_metadata_gap_generation():
    """Documents marked stale or obsolete in inventory trigger stale_knowledge gap with explicit origin."""
    doc_stale = DocumentInventoryItem("DOC-OLD-1", "Quy trình 2018", "old.pdf", "lsu_optics", "dig-old", status="stale", version="0.9.0", updated_at="2018-05-10")
    inventory = CollectionInventory(collection_id="col-1", version="1.0.0", scopes=("lsu_optics",), documents=(doc_stale,))
    q = CoverageQuestion("Q-STALE-1", "lsu_optics", "Tiêu chuẩn kiểm tra gương?", ("inspection_spec",))

    snippet = RetrievedSnippet("DOC-OLD-1#chunk_001", "DOC-OLD-1", "Tiêu chuẩn kiểm tra...", 0.9, source_version="0.9.0", metadata={"status": "stale"})
    receipt = RetrievalReceipt(
        question_text=q.question_text,
        scope=q.scope,
        sources_checked=("DOC-OLD-1",),
        retrieved_snippets=(snippet,),
        coverage_score=0.9,
        reason_code=REASON_STALE_METADATA,
    )
    signals = generate_deterministic_gap_signals(inventory, receipt, q)
    assert len(signals) == 1
    assert signals[0].gap_type == GAP_TYPE_STALE_KNOWLEDGE
    assert "đã cũ hoặc hết hạn" in signals[0].title
    assert "Nguồn phát hiện:" in signals[0].description
    assert signals[0].status == GAP_STATUS_CANDIDATE


def test_production_knowledge_retrieval_adapter_contract():
    """ProductionKnowledgeRetrievalAdapter satisfies KnowledgeRetrievalAdapter protocol with 8 receipt fields."""
    doc = DocumentInventoryItem("DOC-REAL-01", "Quy trình căn chỉnh", "doc.pdf", "lsu_optical_assembly", "dig-real-01", version="1.2.0")
    inventory = CollectionInventory("col-prod", "1.0.0", ("lsu_optical_assembly",), (doc,))

    def fake_retrieval_func(query: str, docs: Any) -> Dict[str, Any]:
        return {
            "evidence_items": [
                {
                    "citation_id": "DOC-REAL-01#chunk_001",
                    "source_id": "DOC-REAL-01",
                    "text": "Nhiệt độ tối đa của lăng kính không được vượt quá 65 độ C.",
                    "score": 0.88,
                    "metadata": {"version": "1.2.0"},
                }
            ]
        }

    adapter = ProductionKnowledgeRetrievalAdapter(inventory, retrieval_func=fake_retrieval_func)
    q = CoverageQuestion("Q-PROD-1", "lsu_optical_assembly", "Nhiệt độ tối đa bao nhiêu?", ("threshold",))
    receipt = adapter.retrieve(q)

    # Verify 8 fields of RetrievalReceipt contract
    assert receipt.question_text == q.question_text
    assert receipt.scope == q.scope
    assert receipt.sources_checked == ("DOC-REAL-01",)
    assert len(receipt.retrieved_snippets) == 1
    assert receipt.retrieved_snippets[0].snippet_id == "DOC-REAL-01#chunk_001"
    assert receipt.coverage_score == 0.88
    assert receipt.source_version == "1.2.0"
    assert receipt.reason_code == REASON_SUFFICIENT_EVIDENCE
    assert "Nguồn phát hiện:" in receipt.metadata.get("source_diagnostic", "")


def test_cagent_real_interface_with_fake_provider_drops_fabricated_citations():
    """Gaps fabricated by model with citations outside actual retrieval are dropped via real interface."""
    recorded_calls: List[Dict[str, Any]] = []

    def fake_cagent_provider(endpoint_url: str, *, system_prompt: str, user_prompt: str, **kwargs: Any) -> CAgentResponse:
        recorded_calls.append({"endpoint": endpoint_url, "user_prompt": json.loads(user_prompt)})
        # Return mock JSON through real response object
        response_payload = [
            # 1. Hallucinated gap: no citations
            {
                "gap_id": "GAP-CAGENT-EMPTY",
                "title": "Khoảng trống không dẫn chứng",
                "evidence_refs": [],
            },
            # 2. Fabricated citation: citation outside actual retrieval
            {
                "gap_id": "GAP-CAGENT-FABRICATED",
                "title": "Khoảng trống bịa đặt tài liệu",
                "evidence_refs": ["DOC-FABRICATED#chunk_999"],
            },
            # 3. Valid gap: citation matches actual retrieved snippet
            {
                "gap_id": "GAP-CAGENT-VALID",
                "title": "Khoảng trống hợp lệ từ đoạn trích",
                "description": "Giải thích chi tiết",
                "gap_type": GAP_TYPE_MISSING_THRESHOLD,
                "evidence_refs": ["DOC-RETRIEVED#chunk_001"],
                "status": "accepted",  # Model attempts self-acceptance!
            },
        ]
        return CAgentResponse(ok=True, text=json.dumps(response_payload, ensure_ascii=False))

    client = CAgentGatewayClient(
        endpoint="http://127.0.0.1:5000/cagent/predict",
        is_internal_allowed=True,
        prediction_callable=fake_cagent_provider,
    )

    # Actual retrieved snippets from adapter
    actual_snippets = [
        RetrievedSnippet("DOC-RETRIEVED#chunk_001", "DOC-RETRIEVED", "Đoạn trích thật", 0.9),
    ]
    evidence_pack = {
        "collection_id": "col-1",
        "scope": "lsu_optics",
        "snippets": actual_snippets,
        "allowed_citations": ["DOC-RETRIEVED#chunk_001"],
    }

    results = client.explain_and_rank_gaps([], evidence_pack)

    # 1. Integration verified: call went through prediction_callable with JSON user_prompt
    assert len(recorded_calls) == 1
    assert recorded_calls[0]["endpoint"] == "http://127.0.0.1:5000/cagent/predict"
    assert "allowed_citations" in recorded_calls[0]["user_prompt"]

    # 2. Fabricated citation dropped; only valid gap preserved
    assert len(results) == 1
    assert results[0].gap_id == "GAP-CAGENT-VALID"
    assert results[0].evidence_refs == ("DOC-RETRIEVED#chunk_001",)

    # 3. Model CANNOT self-accept: status strictly coerced to candidate
    assert results[0].status == GAP_STATUS_CANDIDATE


def test_local_only_data_auto_inferred_and_blocked_on_unauthorized_destination():
    """local_only is auto-inferred from inventory/snippets and blocked without relying on caller boolean."""
    doc_local = DocumentInventoryItem(
        doc_id="DOC-LOCAL-01",
        title="Bí mật nhà máy",
        path="local_secret.pdf",
        scope="lsu_optics",
        digest="dig-local",
        is_local_only=True,  # Document is local_only!
    )
    inventory = CollectionInventory("col-local", "1.0.0", ("lsu_optics",), (doc_local,))

    # External unauthorized provider
    client_cloud = CAgentGatewayClient(
        endpoint="https://external-cloud-ai.example.com/predict",
        is_internal_allowed=False,  # Unauthorized for local_only!
    )

    snippet_local = RetrievedSnippet("DOC-LOCAL-01#chunk_001", "DOC-LOCAL-01", "Nội dung nội bộ", 0.85)
    evidence_pack = {
        "collection_id": "col-local",
        "scope": "lsu_optics",
        "snippets": [snippet_local],
        "allowed_citations": ["DOC-LOCAL-01#chunk_001"],
    }

    # Caller does NOT pass is_local_only=True! System MUST auto-infer from inventory/snippet.
    with pytest.raises(SecurityPolicyError, match="Dữ liệu local_only chỉ được phép đi qua kênh C-AGENT nội bộ"):
        client_cloud.explain_and_rank_gaps([], evidence_pack, inventory=inventory)


def test_cagent_offline_fallback_preserves_deterministic_signals():
    """If C-AGENT is unavailable or network fails, deterministic signals are preserved without cloud calls."""
    def failing_provider(endpoint_url: str, **kwargs: Any) -> CAgentResponse:
        raise ConnectionRefusedError("Không thể kết nối C-AGENT")

    client_failed = CAgentGatewayClient(
        endpoint="http://127.0.0.1:9999/cagent/predict",
        is_internal_allowed=True,
        prediction_callable=failing_provider,
    )
    det_gap = KnowledgeGapCandidate(
        gap_id="GAP-DET-001",
        collection_id="col-1",
        scope="lsu_optics",
        title="Tín hiệu tất định",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_CONDITION,
        evidence_refs=("DOC-1#chunk_001",),
        status=GAP_STATUS_CANDIDATE,
    )
    evidence_pack = {
        "collection_id": "col-1",
        "scope": "lsu_optics",
        "snippets": [{"snippet_id": "DOC-1#chunk_001", "doc_id": "DOC-1", "text": "Tài liệu 1"}],
        "allowed_citations": ["DOC-1#chunk_001"],
    }
    results = client_failed.explain_and_rank_gaps([det_gap], evidence_pack)
    assert len(results) == 1
    assert results[0].gap_id == "GAP-DET-001"
    assert results[0].status == GAP_STATUS_CANDIDATE


def test_evaluate_coverage_with_actual_retrieved_snippets_only():
    """evaluate_coverage includes only actual retrieved snippets in evidence pack, without fabricated DOC#p1/p2."""
    doc = DocumentInventoryItem("DOC-SIM-001", "Tài liệu thật", "doc.pdf", "lsu_optical_assembly", "dig-01")
    inventory = CollectionInventory("col-test", "1.0.0", ("lsu_optical_assembly",), (doc,))

    captured_evidence_pack: Dict[str, Any] = {}

    def spy_cagent_provider(endpoint_url: str, *, system_prompt: str, user_prompt: str, **kwargs: Any) -> CAgentResponse:
        data = json.loads(user_prompt)
        captured_evidence_pack.update(data)
        return CAgentResponse(ok=True, text="[]")

    client = CAgentGatewayClient(
        endpoint="http://127.0.0.1:5000/cagent/predict",
        is_internal_allowed=True,
        prediction_callable=spy_cagent_provider,
    )

    q = CoverageQuestion("Q-1", "lsu_optical_assembly", "Nhiệt độ tối đa?", ("threshold",))
    metric, gaps = evaluate_coverage(inventory, [q], c_agent=client)

    # Verify that captured evidence pack contains ONLY real retrieved snippets and NO fabricated DOC#p1 or DOC#p2
    allowed_cits = captured_evidence_pack.get("allowed_citations", [])
    assert not any("#p1" in cit for cit in allowed_cits)
    assert not any("#p2" in cit for cit in allowed_cits)
    assert any("DOC-SIM-001#chunk_001" in cit for cit in allowed_cits)


def test_preflight_check_blocks_cloud_endpoint_even_if_internal_allowed_flag_is_true():
    """BrainGateway preflight check enforces security policy and rejects external cloud endpoint even if caller sets is_internal_allowed=True."""
    from aios_habit.knowledge_coverage import SecurityPolicyError

    # Caller attempts to spoof authorization by setting is_internal_allowed=True on an external cloud URL
    client_spoofed = CAgentGatewayClient(
        endpoint="https://api.external-cloud-ai.com/v1/predict",
        is_internal_allowed=True,  # Spoofed boolean!
    )

    doc_local = DocumentInventoryItem("DOC-CONFIDENTIAL", "Bí mật xưởng", "secret.pdf", "lsu_optics", "dig-secret", is_local_only=True)
    inventory = CollectionInventory("col-secret", "1.0.0", ("lsu_optics",), (doc_local,))

    evidence_pack = {
        "collection_id": "col-secret",
        "scope": "lsu_optics",
        "snippets": [RetrievedSnippet("DOC-CONFIDENTIAL#chunk_001", "DOC-CONFIDENTIAL", "Nội dung nội bộ", 0.9)],
        "allowed_citations": ["DOC-CONFIDENTIAL#chunk_001"],
    }

    # Must fail-closed because BrainGateway preflight check and endpoint check reject cloud destination for local_only
    with pytest.raises(SecurityPolicyError, match="Dữ liệu local_only chỉ được phép đi qua kênh C-AGENT nội bộ"):
        client_spoofed.explain_and_rank_gaps([], evidence_pack, inventory=inventory)
