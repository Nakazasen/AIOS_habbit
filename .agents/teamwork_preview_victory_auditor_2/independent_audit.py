import json
import os
import re
import sys

TARGET_PATH = r"d:\Sandbox\AIOS_habbit\.understand-anything\knowledge-graph.json"
INTERMEDIATE_PATH = r"d:\Sandbox\AIOS_habbit\.understand-anything\intermediate\assembled-graph.json"
SCAN_PATH = r"d:\Sandbox\AIOS_habbit\.understand-anything\intermediate\scan-result.json"

def run_audit():
    print("=== STARTING INDEPENDENT VICTORY AUDIT ===")
    
    if not os.path.exists(TARGET_PATH):
        print(f"FAIL: Target file not found at {TARGET_PATH}")
        return
        
    # Read raw bytes to check encoding and replacement characters
    with open(TARGET_PATH, "rb") as f:
        raw_bytes = f.read()
        
    print(f"File size: {len(raw_bytes)} bytes")
    
    # Check UTF-8 decoding
    try:
        raw_text = raw_bytes.decode("utf-8")
        print("UTF-8 Decoding: PASS")
    except UnicodeDecodeError as e:
        print(f"UTF-8 Decoding: FAIL - {e}")
        return

    # Check for replacement character \ufffd
    if "\ufffd" in raw_text:
        print("Replacement char \\ufffd: FAIL (Corrupted characters found)")
    else:
        print("Replacement char \\ufffd: PASS (Clean encoding)")
        
    # JSON Parse Check
    try:
        data = json.loads(raw_text)
        print("JSON.parse / json.loads: PASS (Valid JSON syntax)")
    except Exception as e:
        print(f"JSON.parse / json.loads: FAIL - {e}")
        return

    # Schema Validation
    top_keys = list(data.keys())
    print(f"Top-level keys: {top_keys}")
    
    required_top = ["version", "project", "nodes", "edges", "layers", "tour"]
    missing_top = [k for k in required_top if k not in data]
    if missing_top:
        print(f"Missing top-level keys: {missing_top} -> FAIL")
    else:
        print("Top-level keys check: PASS")

    # Project metadata check
    project = data.get("project", {})
    proj_desc = project.get("description", "")
    print(f"Project name: {project.get('name')}")
    print(f"Project description: {proj_desc}")
    
    # Check Vietnamese in project description
    vn_chars_regex = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE)
    if not vn_chars_regex.search(proj_desc):
        print("Project description Vietnamese check: FAIL (No VN diacritics)")
    else:
        print("Project description Vietnamese check: PASS")
        
    # Nodes audit
    nodes = data.get("nodes", [])
    print(f"Total nodes count: {len(nodes)}")
    
    node_ids = set()
    duplicate_node_ids = []
    untranslated_nodes = []
    empty_summary_nodes = []
    mock_summary_nodes = []
    valid_vn_nodes = []
    
    mock_patterns = [
        r"^TODO", r"^TBD", r"^placeholder", r"^mock", r"^dummy", r"^xxx", r"^test", r"lorem ipsum",
        r"^summary$", r"^node summary$", r"^translation here$"
    ]
    mock_regex = re.compile("|".join(mock_patterns), re.IGNORECASE)
    
    # Common English-only indicator (sentences that have multiple common English stopwords and 0 Vietnamese diacritics)
    english_stopwords = {"the", "and", "is", "for", "with", "this", "that", "from", "which", "provides", "implements", "contains", "handles", "stores"}
    
    for idx, node in enumerate(nodes):
        nid = node.get("id")
        if not nid:
            print(f"Node at index {idx} has missing id! -> FAIL")
            continue
        if nid in node_ids:
            duplicate_node_ids.append(nid)
        node_ids.add(nid)
        
        summary = node.get("summary", "")
        if not summary or summary.strip() == "":
            empty_summary_nodes.append((idx, nid))
            continue
            
        if mock_regex.search(summary.strip()):
            mock_summary_nodes.append((idx, nid, summary))
            
        # Check if contains VN diacritics
        has_vn = bool(vn_chars_regex.search(summary))
        
        # Check pure english words
        words = set(re.findall(r"\b[a-zA-Z]+\b", summary.lower()))
        common_en_matches = words.intersection(english_stopwords)
        
        if not has_vn and len(common_en_matches) >= 2:
            untranslated_nodes.append((idx, nid, summary))
        elif has_vn:
            valid_vn_nodes.append(nid)
            
    print(f"Unique nodes: {len(node_ids)}, Duplicates: {len(duplicate_node_ids)}")
    print(f"Nodes with valid VN summaries: {len(valid_vn_nodes)} / {len(nodes)}")
    print(f"Empty summary nodes: {len(empty_summary_nodes)}")
    print(f"Mock/Dummy summary nodes: {len(mock_summary_nodes)}")
    print(f"Untranslated English nodes: {len(untranslated_nodes)}")
    
    if duplicate_node_ids:
        print(f"Duplicate Node IDs: {duplicate_node_ids[:5]} -> FAIL")
    if empty_summary_nodes:
        print(f"Empty summary sample: {empty_summary_nodes[:5]} -> FAIL")
    if mock_summary_nodes:
        print(f"Mock summary sample: {mock_summary_nodes[:5]} -> FAIL")
    if untranslated_nodes:
        print(f"Untranslated sample: {untranslated_nodes[:5]} -> FAIL")
        
    # Layers audit
    layers = data.get("layers", [])
    print(f"Total layers count: {len(layers)}")
    untranslated_layers = []
    for idx, layer in enumerate(layers):
        lname = layer.get("name", "")
        ldesc = layer.get("description", "")
        lnodes = layer.get("nodeIds", [])
        has_vn_name = bool(vn_chars_regex.search(lname))
        has_vn_desc = bool(vn_chars_regex.search(ldesc))
        print(f"  Layer {idx+1} [{layer.get('id')}]: name='{lname}', nodes_count={len(lnodes)}")
        print(f"    Desc preview: {ldesc[:80]}...")
        if not (has_vn_name or has_vn_desc):
            untranslated_layers.append((layer.get("id"), lname, ldesc))
            
    if untranslated_layers:
        print(f"Untranslated layers: {untranslated_layers} -> FAIL")
    else:
        print("Layers Vietnamese localization check: PASS")
        
    # Tour audit
    tour = data.get("tour", [])
    print(f"Total tour steps count: {len(tour)}")
    untranslated_tour = []
    for idx, step in enumerate(tour):
        stitle = step.get("title", "")
        sdesc = step.get("description", "")
        sorder = step.get("order")
        snid = step.get("nodeId")
        has_vn_title = bool(vn_chars_regex.search(stitle))
        has_vn_desc = bool(vn_chars_regex.search(sdesc))
        print(f"  Tour Step {sorder} [{snid}]: title='{stitle}'")
        print(f"    Desc preview: {sdesc[:80]}...")
        if not (has_vn_title or has_vn_desc):
            untranslated_tour.append((snid, stitle, sdesc))
            
    if untranslated_tour:
        print(f"Untranslated tour steps: {untranslated_tour} -> FAIL")
    else:
        print("Tour Vietnamese localization check: PASS")
        
    # Edges audit & Schema compliance
    edges = data.get("edges", [])
    print(f"Total edges count: {len(edges)}")
    
    # Valid types in understand-anything schema:
    # Node types: "file", "directory", "symbol"
    # Edge types: "imports", "calls", "extends", "implements", "references", "contains", "belongs_to", "depends_on"
    valid_node_types = {"file", "directory", "symbol"}
    valid_edge_types = {"imports", "calls", "extends", "implements", "references", "contains", "belongs_to", "depends_on"}
    
    invalid_node_types = []
    for node in nodes:
        ntype = node.get("type")
        if ntype not in valid_node_types:
            invalid_node_types.append((node.get("id"), ntype))
            
    invalid_edge_types = []
    broken_edges = []
    missing_weight_edges = []
    
    for idx, edge in enumerate(edges):
        src = edge.get("source")
        tgt = edge.get("target")
        etype = edge.get("type")
        w = edge.get("weight")
        
        if etype not in valid_edge_types:
            invalid_edge_types.append((idx, etype, src, tgt))
        if src not in node_ids or tgt not in node_ids:
            broken_edges.append((idx, src, tgt))
        if w is None or not isinstance(w, (int, float)):
            missing_weight_edges.append(idx)
            
    print(f"Invalid node types: {len(invalid_node_types)}")
    print(f"Invalid edge types: {len(invalid_edge_types)}")
    print(f"Broken edge references: {len(broken_edges)}")
    print(f"Missing edge weights: {len(missing_weight_edges)}")
    
    if invalid_node_types:
        print(f"Invalid node types sample: {invalid_node_types[:5]} -> FAIL")
    if invalid_edge_types:
        print(f"Invalid edge types sample: {invalid_edge_types[:5]} -> FAIL")
    if broken_edges:
        print(f"Broken edges sample: {broken_edges[:5]} -> FAIL")
    if missing_weight_edges:
        print(f"Missing edge weights sample: {missing_weight_edges[:5]} -> FAIL")
        
    # Check IT Terms preservation
    it_terms = ["Agent", "Local Storage", "Orchestration", "Framework", "Dashboard", "SQLite", "Streamlit", "JSONL", "RAG", "CLI"]
    found_terms = {}
    full_corpus = raw_text
    for term in it_terms:
        matches = len(re.findall(re.escape(term), full_corpus, re.IGNORECASE))
        exact_matches = len(re.findall(r"\b" + re.escape(term) + r"\b", full_corpus))
        found_terms[term] = {"total_occurrences": matches, "exact_case_occurrences": exact_matches}
        
    print("\nIT Terms Preservation Analysis:")
    for term, counts in found_terms.items():
        print(f"  - '{term}': {counts['exact_case_occurrences']} exact matches ({counts['total_occurrences']} case-insensitive)")
        
    # Compare with intermediate assembled-graph.json if available
    if os.path.exists(INTERMEDIATE_PATH):
        with open(INTERMEDIATE_PATH, "r", encoding="utf-8") as f:
            assembled_data = json.load(f)
        print(f"\nIntermediate assembled-graph.json comparison:")
        print(f"  Intermediate nodes: {len(assembled_data.get('nodes', []))}")
        print(f"  Intermediate edges: {len(assembled_data.get('edges', []))}")
        print(f"  Intermediate layers: {len(assembled_data.get('layers', []))}")
        print(f"  Intermediate tour: {len(assembled_data.get('tour', []))}")
        
    print("\n=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    run_audit()
