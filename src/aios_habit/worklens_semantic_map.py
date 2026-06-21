import logging
from typing import List, Dict, Any, Optional

from aios_habit.workspace_models import load_notebooks
from aios_habit.source_ingest import load_sources
from aios_habit.case_store import load_cases, load_evidence
from aios_habit.learning_models import load_learning_cards
from aios_habit.notebook_import_store import load_bridge_imports
from aios_habit.knowledge_map_view import sanitize_id

logger = logging.getLogger(__name__)

def build_worklens_semantic_graph(
    workspace: Optional[str] = None,
    notebooks: Optional[List[Any]] = None,
    sources: Optional[List[Any]] = None,
    cases: Optional[List[Any]] = None,
    evidence: Optional[List[Any]] = None,
    learning_cards: Optional[List[Any]] = None,
    bridge_imports: Optional[List[Any]] = None,
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
    if bridge_imports is None:
        bridge_imports = load_bridge_imports()

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

    def add_node(nid: str, label: str, ntype: str, description: str = "", source_ref: str = "", confidence: str = ""):
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
        valid_types = {"system", "process", "setting", "error", "cause", "action", "document", "case", "component", "other"}
        if ntype not in valid_types:
            ntype = "other"
            
        nodes_list.append({
            "id": clean_id,
            "label": label,
            "type": ntype,
            "description": description,
            "source_ref": source_ref,
            "confidence": confidence
        })
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
        case_nid = f"case_{case.case_id}"
        add_node(case_nid, label=case.title, ntype="case", description=case.current_situation, source_ref=case.case_id, confidence=case.priority)
        
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
        ev_nid = f"evidence_{ev.evidence_id}"
        add_node(ev_nid, label=ev.title, ntype="document", description=ev.structured_summary or ev.extracted_text[:200], source_ref=ev.source_path, confidence=ev.confidence)
        case_nid = f"case_{ev.case_id}"
        if sanitize_id(case_nid) in added_node_ids:
            add_edge(case_nid, ev_nid, relation="HAS_EVIDENCE", confidence=ev.confidence, source_ref=ev.source_path)
            add_edge(ev_nid, case_nid, relation="SUPPORTS", confidence=ev.confidence, source_ref=ev.source_path)

    # 5. Build Senior Learning Cards
    for lc in learning_cards:
        lrn_nid = f"learning_{lc.learning_id}"
        label = f"Bài học: {lc.reusable_lesson[:40]}..." if lc.reusable_lesson else f"Bài học {lc.learning_id}"
        add_node(lrn_nid, label=label, ntype="document", description=lc.reusable_lesson, source_ref=lc.learning_id, confidence=lc.confidence)
        
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
                
                add_node(
                    imp_nid, 
                    label=node.get("label", orig_id), 
                    ntype=node.get("type", "other"), 
                    description=node.get("description", ""), 
                    source_ref=node.get("source_ref") or bi.title, 
                    confidence=node.get("confidence", "")
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
                add_node(sym_nid, label=f"Triệu chứng: {sym}", ntype="error", description="Triệu chứng từ phân tích NotebookLM", source_ref=bi.title)
                symptom_ids.append(sym_nid)
                if sanitize_id(nb_nid) in added_node_ids:
                    add_edge(nb_nid, sym_nid, relation="CONTAINS")
                    
            hyp_ids = []
            for i, hyp in enumerate(hypotheses):
                hyp_nid = f"imp_hyp_{bi.import_id}_{i}"
                add_node(hyp_nid, label=f"Giả thuyết: {hyp}", ntype="cause", description="Giả thuyết từ phân tích NotebookLM", source_ref=bi.title)
                hyp_ids.append(hyp_nid)
                if sanitize_id(nb_nid) in added_node_ids:
                    add_edge(nb_nid, hyp_nid, relation="CONTAINS")
                for sym_nid in symptom_ids:
                    add_edge(hyp_nid, sym_nid, relation="EXPLAINS")
                    
            for i, evc in enumerate(evc_list):
                evc_nid = f"imp_evc_{bi.import_id}_{i}"
                add_node(evc_nid, label=f"Cần check: {evc}", ntype="action", description="Bằng chứng cần kiểm tra theo gợi ý", source_ref=bi.title)
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
        "meta": {
            "graph_kind": graph_kind,
            "uses_sample_data": uses_sample_data,
            "warnings": warnings
        }
    }
