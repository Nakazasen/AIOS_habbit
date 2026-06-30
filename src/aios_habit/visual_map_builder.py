import datetime
import hashlib
import re
from typing import List, Dict, Any, Optional
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.learning_models import SeniorLearningCard
from aios_habit.visual_map_models import (
    VisualKnowledgeGraph, VisualMapNode, VisualMapEdge, 
    ALLOWED_NODE_TYPES, ALLOWED_EDGE_TYPES
)

def _safe_node_key(value: str) -> str:
    raw = value or "unknown"
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
    if len(slug) > 48:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
        slug = f"{slug[:37]}_{digest}"
    return slug or "unknown"

def build_active_case_visual_graph(
    case: Case,
    evidence_items: List[EvidenceItem],
    final_answer: Optional[Dict[str, Any]] = None,
    strong_answer: Optional[Dict[str, Any]] = None,
    learning_cards: Optional[List[SeniorLearningCard]] = None,
    claim_guard_result: Optional[Dict[str, Any]] = None,
    domain_playbook: Optional[str] = None
) -> VisualKnowledgeGraph:
    graph = VisualKnowledgeGraph()
    now = datetime.datetime.now().isoformat()
    
    case_node = VisualMapNode(
        node_id=f"node_case_{case.case_id}",
        node_type="case",
        title=case.title or case.case_id,
        short_label=case.case_id,
        description=f"Active case {case.case_id}",
        source_case_id=case.case_id,
        evidence_ids=[],
        privacy_level=case.privacy_level or "local_only",
        confidence="high",
        created_at=now,
        updated_at=now,
        domain="general",
        tags=[],
        status=case.status or "open",
        local_only=case.privacy_level == "local_only",
        display_title=case.title or case.case_id,
    )
    graph.nodes.append(case_node)
    
    if domain_playbook:
        dp_node = VisualMapNode(
            node_id=f"node_dp_{domain_playbook}",
            node_type="domain_playbook",
            title=f"Domain Playbook: {domain_playbook}",
            short_label=domain_playbook,
            description="Domain Playbook",
            source_case_id=case.case_id,
            evidence_ids=[],
            privacy_level="safe",
            confidence="high",
            created_at=now,
            updated_at=now,
            domain=domain_playbook,
            tags=[],
            status="active",
            local_only=False,
            display_title=f"Playbook: {domain_playbook}",
        )
        graph.nodes.append(dp_node)
        graph.edges.append(VisualMapEdge(
            edge_id=f"edge_case_dp_{case.case_id}",
            from_node_id=case_node.node_id,
            to_node_id=dp_node.node_id,
            edge_type="uses_domain_playbook",
            reason="Case uses this domain playbook",
            evidence_ids=[],
            confidence="high",
            direction="directed",
            created_at=now,
            privacy_level="safe",
            local_only=False
        ))
        
    for ev in evidence_items:
        src_ref = ev.source_path or ev.evidence_id
        src_node_id = f"node_source_{_safe_node_key(ev.source_type)}_{_safe_node_key(src_ref)}"
        if not any(n.node_id == src_node_id for n in graph.nodes):
            src_node = VisualMapNode(
                node_id=src_node_id,
                node_type="source",
                title=f"Source: {ev.source_path or ev.source_type}",
                short_label="Source",
                description="Evidence Source",
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level=ev.privacy_level or "local_only",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="verified",
                local_only=ev.privacy_level == "local_only",
                display_title=ev.source_path or ev.source_type
            )
            graph.nodes.append(src_node)
            
        ev_node_id = f"node_evidence_{ev.evidence_id}"
        if not any(n.node_id == ev_node_id for n in graph.nodes):
            ev_node = VisualMapNode(
                node_id=ev_node_id,
                node_type="evidence",
                title=ev.title or ev.evidence_id,
                short_label=ev.evidence_id,
                description=ev.extracted_text[:100] if ev.extracted_text else "Evidence",
                source_case_id=case.case_id,
                evidence_ids=[ev.evidence_id],
                privacy_level=ev.privacy_level or "local_only",
                confidence=ev.confidence or "medium",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status=ev.review_status or "open",
                local_only=ev.privacy_level == "local_only",
                display_title=ev.title or ev.evidence_id,
            )
            graph.nodes.append(ev_node)
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_ev_src_{ev.evidence_id}",
                from_node_id=ev_node.node_id,
                to_node_id=src_node_id,
                edge_type="extracted_from",
                reason="Evidence extracted from source",
                evidence_ids=[ev.evidence_id],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level=ev.privacy_level or "local_only",
                local_only=ev.privacy_level == "local_only"
            ))
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_case_ev_{ev.evidence_id}",
                from_node_id=case_node.node_id,
                to_node_id=ev_node.node_id,
                edge_type="cites",
                reason="Case contains evidence",
                evidence_ids=[ev.evidence_id],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level=ev.privacy_level or "local_only",
                local_only=ev.privacy_level == "local_only"
            ))

    ans = strong_answer or final_answer
    if ans:
        ans_type = "final_owner_answer" if final_answer else "ide_handoff_strong_answer"
        
        evidence_ids = ans.get("evidence_ids_used", ans.get("cited_evidence_ids", []))
        privacy_level = "local_only" if any(e.privacy_level == "local_only" for e in evidence_items) else "safe"
        local_only = any(e.privacy_level == "local_only" for e in evidence_items)
        
        ans_node = VisualMapNode(
            node_id="node_answer_1",
            node_type="answer",
            title="Final Answer" if final_answer else "Strong Answer",
            short_label="Answer",
            description="Generated Answer",
            source_case_id=case.case_id,
            evidence_ids=evidence_ids,
            privacy_level=privacy_level,
            confidence=ans.get("confidence", "high"),
            created_at=now,
            updated_at=now,
            domain="general",
            tags=[],
            status="verified" if final_answer else "unverified",
            local_only=local_only,
            display_title="Final Answer" if final_answer else "Strong Answer",
            metadata={"source": ans_type}
        )
        graph.nodes.append(ans_node)
        
        for eid in ans_node.evidence_ids:
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_ans_cites_{eid}",
                from_node_id=ans_node.node_id,
                to_node_id=f"node_evidence_{eid}",
                edge_type="cites",
                reason="Answer cites evidence",
                evidence_ids=[eid],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level=privacy_level,
                local_only=local_only
            ))
            
        warnings = ans.get("warnings", [])
        if not warnings and ans.get("insufficient_evidence"):
            warnings.append("Insufficient evidence")
            
        for i, w in enumerate(warnings):
            is_missing = "insufficient" in w.lower() or "missing" in w.lower()
            w_node = VisualMapNode(
                node_id=f"node_warning_{i}",
                node_type="missing_evidence" if is_missing else "risk",
                title=w,
                short_label="Warning",
                description=w,
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="open",
                local_only=False,
                display_title=w
            )
            graph.nodes.append(w_node)
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_ans_warn_{i}",
                from_node_id=ans_node.node_id,
                to_node_id=w_node.node_id,
                edge_type="has_limitation",
                reason="Answer has limitation/warning",
                evidence_ids=[],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level="safe",
                local_only=False
            ))
            
        unsupported = ans.get("unsupported_claims", [])
        for i, u in enumerate(unsupported):
            u_node = VisualMapNode(
                node_id=f"node_claim_u_{i}",
                node_type="claim",
                title=u,
                short_label="Unsupported Claim",
                description=u,
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="local_only" if local_only else "safe",
                confidence="low",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="unverified",
                local_only=local_only,
                display_title=u
            )
            graph.nodes.append(u_node)
            me_node_id = f"node_missing_ev_u_{i}"
            me_node = VisualMapNode(
                node_id=me_node_id,
                node_type="missing_evidence",
                title="Missing evidence for claim",
                short_label="Missing Ev",
                description="Missing evidence",
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="open",
                local_only=False,
                display_title="Missing evidence"
            )
            graph.nodes.append(me_node)
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_claim_me_{i}",
                from_node_id=u_node.node_id,
                to_node_id=me_node_id,
                edge_type="has_missing_evidence",
                reason="Claim is unsupported",
                evidence_ids=[],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level="safe",
                local_only=False
            ))

        actions = ans.get("next_actions", ans.get("recommended_next_actions", []))
        for i, a in enumerate(actions):
            a_node = VisualMapNode(
                node_id=f"node_action_{i}",
                node_type="action",
                title=a,
                short_label="Action",
                description=a,
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="open",
                local_only=False,
                display_title=a
            )
            graph.nodes.append(a_node)
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_action_ans_{i}",
                from_node_id=a_node.node_id,
                to_node_id=ans_node.node_id,
                edge_type="follows_up",
                reason="Action follows up answer",
                evidence_ids=[],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level="safe",
                local_only=False
            ))

    if learning_cards:
        for i, lc in enumerate(learning_cards):
            lc_node = VisualMapNode(
                node_id=f"node_learning_{i}",
                node_type="learning_card",
                title=lc.learning_summary if hasattr(lc, 'learning_summary') else (lc.get("learning_summary", "Learning Card") if isinstance(lc, dict) else "Learning Card"),
                short_label="Learning",
                description="Learning Card",
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="verified",
                local_only=False,
                display_title="Learning Card"
            )
            graph.nodes.append(lc_node)
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_lc_case_{i}",
                from_node_id=lc_node.node_id,
                to_node_id=case_node.node_id,
                edge_type="updates_learning",
                reason="Learning card derived from case",
                evidence_ids=[],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level="safe",
                local_only=False
            ))

    if claim_guard_result and not claim_guard_result.get("ok", True):
        for i, reason in enumerate(claim_guard_result.get("reasons", [])):
            cg_node = VisualMapNode(
                node_id=f"node_cg_risk_{i}",
                node_type="risk",
                title=reason,
                short_label="Claim Guard Risk",
                description=reason,
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="open",
                local_only=False,
                display_title=reason
            )
            graph.nodes.append(cg_node)
            c_node = VisualMapNode(
                node_id=f"node_cg_claim_{i}",
                node_type="claim",
                title="Blocked claim",
                short_label="Claim",
                description="Blocked claim",
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="low",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="blocked",
                local_only=False,
                display_title="Blocked claim"
            )
            graph.nodes.append(c_node)
            me_node_id = f"node_cg_missing_ev_{i}"
            me_node = VisualMapNode(
                node_id=me_node_id,
                node_type="missing_evidence",
                title="Missing evidence for blocked claim",
                short_label="Missing Ev",
                description="Claim guard blocked this claim before evidence support was established",
                source_case_id=case.case_id,
                evidence_ids=[],
                privacy_level="safe",
                confidence="high",
                created_at=now,
                updated_at=now,
                domain="general",
                tags=[],
                status="open",
                local_only=False,
                display_title="Missing evidence for blocked claim"
            )
            graph.nodes.append(me_node)
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_cg_blocks_{i}",
                from_node_id=cg_node.node_id,
                to_node_id=c_node.node_id,
                edge_type="blocks",
                reason="Claim guard blocked claim",
                evidence_ids=[],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level="safe",
                local_only=False
            ))
            graph.edges.append(VisualMapEdge(
                edge_id=f"edge_cg_claim_me_{i}",
                from_node_id=c_node.node_id,
                to_node_id=me_node_id,
                edge_type="has_missing_evidence",
                reason="Blocked claim has no accepted supporting evidence",
                evidence_ids=[],
                confidence="high",
                direction="directed",
                created_at=now,
                privacy_level="safe",
                local_only=False
            ))
            
    # Collapse duplicate evidence nodes
    unique_ev_nodes = {}
    new_nodes = []
    for n in graph.nodes:
        if n.node_type == "evidence":
            if n.node_id not in unique_ev_nodes:
                unique_ev_nodes[n.node_id] = n
                new_nodes.append(n)
        else:
            new_nodes.append(n)
    graph.nodes = new_nodes
    
    return graph
