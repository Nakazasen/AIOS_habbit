import logging
from typing import List, Dict, Any, Optional

from aios_habit.workspace_models import load_notebooks
from aios_habit.source_ingest import load_sources
from aios_habit.case_store import load_cases, load_evidence
from aios_habit.learning_models import load_learning_cards
from aios_habit.notebook_import_store import load_bridge_imports
from aios_habit.knowledge_map_view import sanitize_id

logger = logging.getLogger(__name__)

VERIFIED_STATUSES = {"verified", "confirmed", "local_confirmed"}
DRAFT_STATUSES = {"draft", "unverified"}
IMPORT_ORIGINS = {"notebooklm_import", "import_draft", "sample"}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _classify_business_record(record: Any, record_kind: str) -> Dict[str, Any]:
    source_origin = _norm(getattr(record, "source_origin", "unknown")) or "unknown"
    verification_status = _norm(getattr(record, "verification_status", "unknown")) or "unknown"
    review_status = _norm(getattr(record, "review_status", ""))
    confidence = _norm(getattr(record, "confidence", ""))

    verified = False
    if record_kind == "evidence":
        verified = review_status == "verified" or verification_status in VERIFIED_STATUSES
    elif record_kind == "learning":
        verified = confidence == "confirmed"
    else:
        verified = verification_status in VERIFIED_STATUSES

    if verified:
        return {
            "bucket": "verified",
            "label": "đã xác minh",
            "source_origin": source_origin,
            "verification_status": verification_status,
            "is_verified": True,
            "is_unverified": False,
            "is_unknown": False,
        }

    if source_origin in IMPORT_ORIGINS or verification_status in DRAFT_STATUSES or source_origin == "mom_official_local":
        if source_origin == "mom_official_local":
            label = "MOM local/draft"
            bucket = "mom_local_draft"
        elif source_origin == "manual":
            label = "nháp/manual"
            bucket = "manual_draft"
        elif source_origin in IMPORT_ORIGINS:
            label = "nháp/import"
            bucket = "import_draft"
        else:
            label = "cần xác minh"
            bucket = "unverified"
        return {
            "bucket": bucket,
            "label": label,
            "source_origin": source_origin,
            "verification_status": verification_status,
            "is_verified": False,
            "is_unverified": True,
            "is_unknown": False,
        }

    return {
        "bucket": "unknown",
        "label": "chưa rõ nguồn gốc",
        "source_origin": source_origin,
        "verification_status": verification_status,
        "is_verified": False,
        "is_unverified": False,
        "is_unknown": True,
    }


def _business_meta(cases: List[Any], evidence: List[Any], learning_cards: List[Any], warnings: List[str], graph_kind: str, uses_sample_data: bool) -> Dict[str, Any]:
    records = []
    records.extend(_classify_business_record(c, "case") for c in cases)
    records.extend(_classify_business_record(e, "evidence") for e in evidence)
    records.extend(_classify_business_record(lc, "learning") for lc in learning_cards)

    counts = {
        "verified": 0,
        "import_draft": 0,
        "manual_draft": 0,
        "mom_local_draft": 0,
        "unverified": 0,
        "unknown": 0,
    }
    for rec in records:
        counts[rec["bucket"]] = counts.get(rec["bucket"], 0) + 1

    has_verified = any(rec["is_verified"] for rec in records)
    has_unverified = any(rec["is_unverified"] for rec in records)
    has_unknown = any(rec["is_unknown"] for rec in records)

    if not records:
        business_state = "empty"
    elif has_verified:
        business_state = "verified"
    elif has_unverified:
        business_state = "needs_verification"
    else:
        business_state = "unknown"

    return {
        "graph_kind": graph_kind,
        "uses_sample_data": uses_sample_data,
        "warnings": warnings,
        "business_verification_state": business_state,
        "has_verified_business_data": has_verified,
        "has_unverified_business_data": has_unverified,
        "has_unknown_business_data": has_unknown,
        "provenance_counts": counts,
    }


def build_worklens_semantic_graph(
    workspace: Optional[str] = None,
    notebooks: Optional[List[Any]] = None,
    sources: Optional[List[Any]] = None,
    cases: Optional[List[Any]] = None,
    evidence: Optional[List[Any]] = None,
    learning_cards: Optional[List[Any]] = None,
    bridge_imports: Optional[List[Any]] = None,
    include_bridge_imports: bool = False,
    max_nodes: int = 80,
    max_edges: int = 160,
) -> dict:
    # 1. Load data if None
    if notebooks is None:
        notebooks = load_notebooks()
    if sources is None:
        sources = load_sources()
    if cases is None:
        cases = load_cases()
    if evidence is None:
        evidence = load_evidence()
    if learning_cards is None:
        learning_cards = load_learning_cards()
    if include_bridge_imports and bridge_imports is None:
        bridge_imports = load_bridge_imports()
    elif not include_bridge_imports:
        bridge_imports = []
    else:
        bridge_imports = bridge_imports or []

    # 2. Filtering by Workspace
    if workspace:
        notebooks = [n for n in notebooks if n.workspace_id == workspace]
        cases = [c for c in cases if c.workspace_id == workspace]
        bridge_imports = [bi for bi in bridge_imports if bi.workspace_id == workspace]
        
        active_nb_ids = {n.notebook_id for n in notebooks}
        active_case_ids = {c.case_id for c in cases}
        
        sources = [s for s in sources if s.notebook_id in active_nb_ids]
        evidence = [e for e in evidence if e.case_id in active_case_ids]
        learning_cards = [lc for lc in learning_cards if lc.case_id in active_case_ids]

    # Graph containers
    nodes_list = []
    edges_list = []
    added_node_ids = set()
    warnings = []

    def add_node(
        nid: str,
        label: str,
        ntype: str,
        description: str = "",
        source_ref: str = "",
        confidence: str = "",
        source_origin: str = "",
        verification_status: str = "",
        provenance_label: str = "",
    ):
        if not nid:
            return False
        clean_id = sanitize_id(nid)
        if clean_id in added_node_ids:
            return True
        if len(nodes_list) >= max_nodes:
            if "Nút vượt quá giới hạn đã bị cắt bớt" not in warnings:
                warnings.append("Nút vượt quá giới hạn đã bị cắt bớt")
            return False
        added_node_ids.add(clean_id)
        
        # Ensure type is valid or fallback to other
        valid_types = {"system", "process", "setting", "error", "cause", "action", "learning", "document", "evidence", "case", "component", "other"}
        if ntype not in valid_types:
            ntype = "other"

        node = {
            "id": clean_id,
            "label": label,
            "type": ntype,
            "description": description,
            "source_ref": source_ref,
            "confidence": confidence,
        }
        if source_origin:
            node["source_origin"] = source_origin
        if verification_status:
            node["verification_status"] = verification_status
        if provenance_label:
            node["provenance_label"] = provenance_label
        nodes_list.append(node)
        return True

    def add_edge(from_id: str, to_id: str, relation: str, description: str = "", source_ref: str = "", confidence: str = ""):
        if not from_id or not to_id:
            return
        clean_from = sanitize_id(from_id)
        clean_to = sanitize_id(to_id)
        
        if len(edges_list) >= max_edges:
            if "Liên kết vượt quá giới hạn đã bị cắt bớt" not in warnings:
                warnings.append("Liên kết vượt quá giới hạn đã bị cắt bớt")
            return
            
        edges_list.append({
            "from": clean_from,
            "to": clean_to,
            "relation": relation,
            "description": description,
            "source_ref": source_ref,
            "confidence": confidence
        })

    # Track semantic state
    has_real_cases = len(cases) > 0
    has_real_evidence = len(evidence) > 0
    has_real_learning = len(learning_cards) > 0

    # 3. Build Notebooks and Sources
    for nb in notebooks:
        nb_nid = f"notebook_{nb.notebook_id}"
        add_node(nb_nid, label=f"Sổ tri thức: {nb.name}", ntype="other", description=nb.description)
        
    for src in sources:
        src_nid = f"source_{src.source_id}"
        add_node(src_nid, label=src.title, ntype="document", description=src.description, source_ref=src.source_id)
        nb_nid = f"notebook_{src.notebook_id}"
        if sanitize_id(nb_nid) in added_node_ids:
            add_edge(nb_nid, src_nid, relation="CONTAINS")

    # 4. Build Cases & Evidence
    for case in cases:
        case_prov = _classify_business_record(case, "case")
        case_nid = f"case_{case.case_id}"
        add_node(
            case_nid,
            label=case.title,
            ntype="case",
            description=case.current_situation,
            source_ref=case.case_id,
            confidence=case.priority,
            source_origin=case_prov["source_origin"],
            verification_status=case_prov["verification_status"],
            provenance_label=case_prov["label"],
        )
        
        # Link case to notebooks
        for nb_id in getattr(case, "linked_notebook_ids", []):
            nb_nid = f"notebook_{nb_id}"
            if sanitize_id(nb_nid) in added_node_ids:
                add_edge(case_nid, nb_nid, relation="liên_kết")

        # Hypotheses
        for i, hypo in enumerate(case.hypotheses):
            hypo_nid = f"hypo_{case.case_id}_{i}"
            add_node(hypo_nid, label=f"Giả thuyết: {hypo}", ntype="cause", description=f"Giả thuyết cho {case.title}", source_ref=case.case_id)
            add_edge(case_nid, hypo_nid, relation="khảo_sát")

        # Next Actions
        for i, act in enumerate(case.next_actions):
            act_nid = f"action_{case.case_id}_{i}"
            add_node(act_nid, label=f"Cần làm: {act}", ntype="action", description=f"Hành động cho {case.title}", source_ref=case.case_id)
            add_edge(case_nid, act_nid, relation="cần_làm")

        # Decisions
        for i, dec in enumerate(case.decisions):
            dec_nid = f"decision_{case.case_id}_{i}"
            add_node(dec_nid, label=f"Quyết định: {dec}", ntype="setting", description=f"Quyết định cho {case.title}", source_ref=case.case_id)
            add_edge(case_nid, dec_nid, relation="dẫn_đến")

    # Add evidence items
    for ev in evidence:
        ev_prov = _classify_business_record(ev, "evidence")
        ev_nid = f"evidence_{ev.evidence_id}"
        add_node(
            ev_nid,
            label=ev.title,
            ntype="evidence",
            description=ev.structured_summary or ev.extracted_text[:200],
            source_ref=ev.source_path,
            confidence=ev.confidence,
            source_origin=ev_prov["source_origin"],
            verification_status=ev_prov["verification_status"],
            provenance_label=ev_prov["label"],
        )
        case_nid = f"case_{ev.case_id}"
        if sanitize_id(case_nid) in added_node_ids:
            add_edge(case_nid, ev_nid, relation="HAS_EVIDENCE", confidence=ev.confidence, source_ref=ev.source_path)
            add_edge(ev_nid, case_nid, relation="SUPPORTS", confidence=ev.confidence, source_ref=ev.source_path)

    # 5. Build Senior Learning Cards
    for lc in learning_cards:
        lc_prov = _classify_business_record(lc, "learning")
        lrn_nid = f"learning_{lc.learning_id}"
        label = f"Bài học: {lc.reusable_lesson[:40]}..." if lc.reusable_lesson else f"Bài học {lc.learning_id}"
        learning_desc = f"Bài học kinh nghiệm: {lc.reusable_lesson}" if lc.reusable_lesson else "Bài học kinh nghiệm"
        add_node(
            lrn_nid,
            label=label,
            ntype="learning",
            description=learning_desc,
            source_ref=lc.learning_id,
            confidence=lc.confidence,
            source_origin=lc_prov["source_origin"],
            verification_status=lc_prov["verification_status"],
            provenance_label=lc_prov["label"],
        )
        
        case_nid = f"case_{lc.case_id}"
        if sanitize_id(case_nid) in added_node_ids:
            add_edge(lrn_nid, case_nid, relation="LEARNED_FROM")

        # Suggestions & Causes
        if lc.check_first_next_time:
            nc_nid = f"action_{lc.learning_id}_nextcheck"
            add_node(nc_nid, label=f"Kiểm tra trước: {lc.check_first_next_time}", ntype="action", description="Hành động kiểm tra đề xuất lần sau", source_ref=lc.learning_id)
            add_edge(lrn_nid, nc_nid, relation="SUGGESTS_NEXT_CHECK")
            
        if lc.true_cause:
            rc_nid = f"cause_{lc.learning_id}_cause"
            add_node(rc_nid, label=f"Nguyên nhân: {lc.true_cause}", ntype="cause", description="Nguyên nhân cốt lõi đúc kết", source_ref=lc.learning_id)
            add_edge(lrn_nid, rc_nid, relation="DESCRIBES_ROOT_CAUSE")
            
        if lc.actions_taken:
            cm_nid = f"action_{lc.learning_id}_countermeasure"
            add_node(cm_nid, label=f"Biện pháp: {lc.actions_taken}", ntype="action", description="Biện pháp xử lý đã thực hiện", source_ref=lc.learning_id)
            add_edge(lrn_nid, cm_nid, relation="DESCRIBES_COUNTERMEASURE")

    # 6. Parse and merge NotebookLM Bridge imports if available
    uses_sample_data = False
    for bi in bridge_imports:
        if bi.import_id == "IMP-C707A8DF":
            uses_sample_data = True
            
        parsed = bi.parsed_json or {}
        
        # Merge knowledge_graph_json
        if bi.import_type == "knowledge_graph_json" and "nodes" in parsed:
            nb_nid = f"notebook_{bi.notebook_id}"
            
            # Map of imported node ID -> clean prefixed ID
            id_map = {}
            for node in parsed.get("nodes", []):
                orig_id = node.get("id")
                if not orig_id:
                    continue
                imp_nid = f"imp_{bi.import_id}_{orig_id}"
                id_map[orig_id] = imp_nid
                
                node_desc = node.get("description", "")
                imported_desc = f"NotebookLM import — chưa xác nhận: {node_desc}" if node_desc else "NotebookLM import — chưa xác nhận"
                add_node(
                    imp_nid, 
                    label=node.get("label", orig_id), 
                    ntype=node.get("type", "other"), 
                    description=imported_desc, 
                    source_ref=node.get("source_ref") or bi.title, 
                    confidence=node.get("confidence", ""),
                    source_origin="notebooklm_import",
                    verification_status="draft",
                    provenance_label="nháp/import",
                )
                if sanitize_id(nb_nid) in added_node_ids:
                    add_edge(nb_nid, imp_nid, relation="CONTAINS")
                    
            for edge in parsed.get("edges", []):
                orig_from = edge.get("from")
                orig_to = edge.get("to")
                if orig_from in id_map and orig_to in id_map:
                    add_edge(
                        id_map[orig_from],
                        id_map[orig_to],
                        relation=edge.get("relation", ""),
                        description=edge.get("description", ""),
                        source_ref=edge.get("source_ref", ""),
                        confidence=edge.get("confidence", "")
                    )
                    
        # Merge case_investigation_json
        elif bi.import_type == "case_investigation_json":
            nb_nid = f"notebook_{bi.notebook_id}"
            symptoms = parsed.get("symptoms", [])
            hypotheses = parsed.get("hypotheses", [])
            evc_list = parsed.get("evidence_to_check", [])
            
            symptom_ids = []
            for i, sym in enumerate(symptoms):
                sym_nid = f"imp_sym_{bi.import_id}_{i}"
                add_node(sym_nid, label=f"Triệu chứng: {sym}", ntype="error", description="Triệu chứng từ phân tích NotebookLM", source_ref=bi.title, source_origin="notebooklm_import", verification_status="draft", provenance_label="nháp/import")
                symptom_ids.append(sym_nid)
                if sanitize_id(nb_nid) in added_node_ids:
                    add_edge(nb_nid, sym_nid, relation="CONTAINS")
                    
            hyp_ids = []
            for i, hyp in enumerate(hypotheses):
                hyp_nid = f"imp_hyp_{bi.import_id}_{i}"
                add_node(hyp_nid, label=f"Giả thuyết: {hyp}", ntype="cause", description="Giả thuyết từ phân tích NotebookLM", source_ref=bi.title, source_origin="notebooklm_import", verification_status="draft", provenance_label="nháp/import")
                hyp_ids.append(hyp_nid)
                if sanitize_id(nb_nid) in added_node_ids:
                    add_edge(nb_nid, hyp_nid, relation="CONTAINS")
                for sym_nid in symptom_ids:
                    add_edge(hyp_nid, sym_nid, relation="EXPLAINS")
                    
            for i, evc in enumerate(evc_list):
                evc_nid = f"imp_evc_{bi.import_id}_{i}"
                add_node(evc_nid, label=f"Cần check: {evc}", ntype="action", description="Bằng chứng cần kiểm tra theo gợi ý", source_ref=bi.title, source_origin="notebooklm_import", verification_status="draft", provenance_label="nháp/import")
                if sanitize_id(nb_nid) in added_node_ids:
                    add_edge(nb_nid, evc_nid, relation="CONTAINS")
                for hyp_nid in hyp_ids:
                    add_edge(hyp_nid, evc_nid, relation="SUGGESTS_CHECK")

    # Clean edges to keep only existing node connections
    clean_edges = []
    for e in edges_list:
        if e["from"] in added_node_ids and e["to"] in added_node_ids:
            clean_edges.append(e)

    # 7. Metadata classification
    if has_real_cases or has_real_evidence or has_real_learning:
        graph_kind = "semantic"
    elif len(nodes_list) > 0:
        # Check if they are only structural or only imports
        has_imports = any(bi.import_type in ("knowledge_graph_json", "case_investigation_json") for bi in bridge_imports)
        graph_kind = "imported" if has_imports else "structural"
    else:
        graph_kind = "empty"

    return {
        "nodes": nodes_list,
        "edges": clean_edges,
        "meta": _business_meta(cases, evidence, learning_cards, warnings, graph_kind, uses_sample_data)
    }
