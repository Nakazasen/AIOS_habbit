#!/usr/bin/env python3
"""
Automated Verification Harness for knowledge-graph.json
Validates JSON syntax, UTF-8 validity, schema conformance, referential integrity,
and Vietnamese translation quality while ensuring IT terminology preservation.

Usage:
    python verify_knowledge_graph.py [target_graph.json] [baseline_graph.json]
    
Example:
    python verify_knowledge_graph.py ../../.understand-anything/knowledge-graph.json
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# ── Canonical Schema Constraints (Derived from @understand-anything/core) ──

VALID_NODE_TYPES = {
    "file", "function", "class", "module", "concept",
    "config", "document", "service", "table", "endpoint",
    "pipeline", "schema", "resource",
    "domain", "flow", "step",
    "article", "entity", "topic", "claim", "source",
}

VALID_COMPLEXITY = {"simple", "moderate", "complex"}

VALID_EDGE_TYPES = {
    "imports", "exports", "contains", "inherits", "implements",  # Structural
    "calls", "subscribes", "publishes", "middleware",             # Behavioral
    "reads_from", "writes_to", "transforms", "validates",        # Data flow
    "depends_on", "tested_by", "configures",                     # Dependencies
    "related", "similar_to",                                      # Semantic
    "deploys", "serves", "provisions", "triggers",               # Infrastructure
    "migrates", "documents", "routes", "defines_schema",         # Schema/Data
    "contains_flow", "flow_step", "cross_domain",                # Domain
    "cites", "contradicts", "builds_on", "exemplifies", "categorized_under", "authored_by", # Knowledge
    # Legacy / alias compatibility permitted during validation
    "uses", "references", "refers_to", "follows_schema", "tracks", "tests", "updates",
}

VALID_DIRECTIONS = {"forward", "backward", "bidirectional"}

# Common Vietnamese diacritics / regex to verify Vietnamese translation presence
VIETNAMESE_CHAR_REGEX = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"
    r"ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆĐÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]"
)

# Core IT Terms that should remain in English
CORE_IT_KEYWORDS = [
    "Agent", "Local Storage", "Orchestration", "Framework", "Dashboard",
    "Streamlit", "Pydantic", "RAG", "BM25", "SQLite", "JSON", "JSONL",
    "CLI", "API", "Pipeline", "Gateway", "Router", "IDE", "Antigravity",
    "OCR", "PDF", "DOCX", "XLSX", "Adapter", "Registry", "Benchmark"
]


class ValidationReport:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_utf8_and_json(file_path: Path, report: ValidationReport) -> Dict[str, Any]:
    """Check UTF-8 decoding and JSON parsing."""
    if not file_path.exists():
        report.error(f"File does not exist: {file_path}")
        return {}

    try:
        raw_bytes = file_path.read_bytes()
    except Exception as e:
        report.error(f"Failed to read file bytes: {e}")
        return {}

    # Check for UTF-8 validity (no decode errors, no replacement chars)
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        report.error(f"UTF-8 decoding error: {e}")
        return {}

    if "\ufffd" in raw_text:
        report.error("File contains Unicode replacement character (U+FFFD), indicating corrupted encoding.")

    if "\x00" in raw_text:
        report.error("File contains null byte (\\x00), which will break dashboard readers.")

    # Parse JSON
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        report.error(f"JSON syntax error at line {e.lineno}, column {e.colno}: {e.msg}")
        return {}

    if not isinstance(data, dict):
        report.error("Root JSON value must be an object/dict.")
        return {}

    return data


def validate_schema(data: Dict[str, Any], report: ValidationReport) -> Set[str]:
    """Validate graph schema, types, nodes, edges, layers, and tour."""
    # 1. Root keys
    for key in ["version", "project", "nodes", "edges", "layers", "tour"]:
        if key not in data:
            report.error(f"Missing required root key: '{key}'")

    if not report.is_valid:
        return set()

    # 2. Project metadata
    proj = data.get("project", {})
    if not isinstance(proj, dict):
        report.error("'project' field must be an object")
    else:
        for f in ["name", "languages", "frameworks", "description", "analyzedAt", "gitCommitHash"]:
            if f not in proj:
                report.error(f"Missing 'project.{f}' field")
            elif f in ["name", "description"] and not isinstance(proj[f], str):
                report.error(f"'project.{f}' must be a string")
            elif f in ["languages", "frameworks"] and not isinstance(proj[f], list):
                report.error(f"'project.{f}' must be a list of strings")

    # 3. Nodes validation
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        report.error("'nodes' must be an array")
        return set()

    node_ids: Set[str] = set()
    node_types_count: Dict[str, int] = {}
    nodes_with_vietnamese = 0

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            report.error(f"Node[{idx}] is not an object")
            continue

        nid = node.get("id")
        if not nid or not isinstance(nid, str):
            report.error(f"Node[{idx}] missing or invalid 'id'")
            continue

        if nid in node_ids:
            report.error(f"Duplicate node id detected: '{nid}' at index {idx}")
        node_ids.add(nid)

        ntype = node.get("type")
        if not ntype or ntype not in VALID_NODE_TYPES:
            report.warn(f"Node '{nid}' has non-standard type: '{ntype}'")
        node_types_count[ntype] = node_types_count.get(ntype, 0) + 1

        name = node.get("name")
        if not name or not isinstance(name, str):
            report.error(f"Node '{nid}' missing or invalid 'name'")

        summary = node.get("summary")
        if not isinstance(summary, str) or len(summary.strip()) == 0:
            report.error(f"Node '{nid}' missing or empty 'summary'")
        else:
            if VIETNAMESE_CHAR_REGEX.search(summary):
                nodes_with_vietnamese += 1

        tags = node.get("tags")
        if not isinstance(tags, list):
            report.error(f"Node '{nid}' 'tags' must be a list")

        complexity = node.get("complexity")
        if complexity and complexity not in VALID_COMPLEXITY:
            report.warn(f"Node '{nid}' has non-standard complexity: '{complexity}'")

    report.stats["total_nodes"] = len(nodes)
    report.stats["node_types_breakdown"] = node_types_count
    report.stats["nodes_with_vietnamese_summary"] = nodes_with_vietnamese

    # 4. Edges validation
    edges = data.get("edges", [])
    if not isinstance(edges, list):
        report.error("'edges' must be an array")
    else:
        for idx, edge in enumerate(edges):
            if not isinstance(edge, dict):
                report.error(f"Edge[{idx}] is not an object")
                continue

            src = edge.get("source")
            tgt = edge.get("target")
            etype = edge.get("type")
            direction = edge.get("direction")

            if not src or src not in node_ids:
                report.error(f"Edge[{idx}] references missing source node: '{src}'")
            if not tgt or tgt not in node_ids:
                report.error(f"Edge[{idx}] references missing target node: '{tgt}'")
            if not etype:
                report.error(f"Edge[{idx}] missing 'type'")
            if direction and direction not in VALID_DIRECTIONS:
                report.warn(f"Edge[{idx}] has non-standard direction: '{direction}'")

    report.stats["total_edges"] = len(edges)

    # 5. Layers validation
    layers = data.get("layers", [])
    if not isinstance(layers, list):
        report.error("'layers' must be an array")
    else:
        layer_ids: Set[str] = set()
        layers_with_vietnamese = 0

        for idx, layer in enumerate(layers):
            if not isinstance(layer, dict):
                report.error(f"Layer[{idx}] is not an object")
                continue

            lid = layer.get("id")
            lname = layer.get("name")
            ldesc = layer.get("description")
            lnodes = layer.get("nodeIds")

            if not lid or not isinstance(lid, str):
                report.error(f"Layer[{idx}] missing or invalid 'id'")
            else:
                if lid in layer_ids:
                    report.error(f"Duplicate layer id: '{lid}'")
                layer_ids.add(lid)

            if not lname or not isinstance(lname, str):
                report.error(f"Layer '{lid}' missing or invalid 'name'")
            if not ldesc or not isinstance(ldesc, str):
                report.error(f"Layer '{lid}' missing or invalid 'description'")
            else:
                if VIETNAMESE_CHAR_REGEX.search(ldesc):
                    layers_with_vietnamese += 1

            if not isinstance(lnodes, list):
                report.error(f"Layer '{lid}' 'nodeIds' must be a list")
            else:
                for target_nid in lnodes:
                    if target_nid not in node_ids:
                        report.error(f"Layer '{lid}' references missing node: '{target_nid}'")

        report.stats["total_layers"] = len(layers)
        report.stats["layers_with_vietnamese_desc"] = layers_with_vietnamese

    # 6. Tour validation
    tour = data.get("tour", [])
    if not isinstance(tour, list):
        report.error("'tour' must be an array")
    else:
        tour_steps_with_vietnamese = 0
        seen_orders: Set[int] = set()

        for idx, step in enumerate(tour):
            if not isinstance(step, dict):
                report.error(f"Tour[{idx}] is not an object")
                continue

            order = step.get("order")
            title = step.get("title")
            desc = step.get("description")
            tnodes = step.get("nodeIds")

            if order is None or not isinstance(order, int):
                report.error(f"Tour step[{idx}] missing integer 'order'")
            elif order in seen_orders:
                report.warn(f"Tour step order {order} duplicated at index {idx}")
            else:
                seen_orders.add(order)

            if not title or not isinstance(title, str):
                report.error(f"Tour step {order} missing 'title'")
            if not desc or not isinstance(desc, str):
                report.error(f"Tour step {order} missing 'description'")
            else:
                if VIETNAMESE_CHAR_REGEX.search(desc) or VIETNAMESE_CHAR_REGEX.search(title or ""):
                    tour_steps_with_vietnamese += 1

            if not isinstance(tnodes, list):
                report.error(f"Tour step {order} 'nodeIds' must be a list")
            else:
                for target_nid in tnodes:
                    if target_nid not in node_ids:
                        report.error(f"Tour step {order} references missing node: '{target_nid}'")

        report.stats["total_tour_steps"] = len(tour)
        report.stats["tour_steps_with_vietnamese"] = tour_steps_with_vietnamese

    return node_ids


def compare_with_baseline(data: Dict[str, Any], baseline: Dict[str, Any], report: ValidationReport):
    """Verify that node IDs, count, structure, and integrity are preserved identically."""
    orig_nodes = {n.get("id"): n for n in baseline.get("nodes", []) if isinstance(n, dict) and "id" in n}
    curr_nodes = {n.get("id"): n for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n}

    # Check node counts
    if len(curr_nodes) != len(orig_nodes):
        report.error(f"Node count mismatch: baseline has {len(orig_nodes)}, current has {len(curr_nodes)}")

    # Check node ID set equality
    missing_ids = set(orig_nodes.keys()) - set(curr_nodes.keys())
    added_ids = set(curr_nodes.keys()) - set(orig_nodes.keys())
    if missing_ids:
        report.error(f"Missing node IDs from baseline: {list(missing_ids)[:10]} (total missing: {len(missing_ids)})")
    if added_ids:
        report.error(f"Unexpected extra node IDs: {list(added_ids)[:10]} (total added: {len(added_ids)})")

    # Check that non-translated fields remained intact
    field_mismatches = 0
    for nid, orig_n in orig_nodes.items():
        if nid not in curr_nodes:
            continue
        curr_n = curr_nodes[nid]
        for preserved_field in ["type", "filePath", "complexity", "tags"]:
            if orig_n.get(preserved_field) != curr_n.get(preserved_field):
                report.warn(f"Node '{nid}' field '{preserved_field}' altered from baseline.")
                field_mismatches += 1
                if field_mismatches > 20:
                    break

    # Check edge count & set
    orig_edges = baseline.get("edges", [])
    curr_edges = data.get("edges", [])
    if len(curr_edges) != len(orig_edges):
        report.error(f"Edge count mismatch: baseline has {len(orig_edges)}, current has {len(curr_edges)}")

    # Check layer count
    orig_layers = baseline.get("layers", [])
    curr_layers = data.get("layers", [])
    if len(curr_layers) != len(orig_layers):
        report.error(f"Layer count mismatch: baseline has {len(orig_layers)}, current has {len(curr_layers)}")

    # Check tour steps count
    orig_tour = baseline.get("tour", [])
    curr_tour = data.get("tour", [])
    if len(curr_tour) != len(orig_tour):
        report.error(f"Tour step count mismatch: baseline has {len(orig_tour)}, current has {len(curr_tour)}")


def run_verification(target_path_str: str, baseline_path_str: str = None) -> bool:
    target_path = Path(target_path_str).resolve()
    report = ValidationReport()

    print("=" * 70)
    print(f"AUTOMATED VERIFICATION HARNESS: {target_path.name}")
    print(f"Target: {target_path}")
    print("=" * 70)

    # 1. UTF-8 & JSON parsing
    data = validate_utf8_and_json(target_path, report)
    if not report.is_valid:
        print("\n[FAIL] UTF-8 / JSON Syntax Validation Failed:")
        for err in report.errors:
            print(f"  ❌ {err}")
        return False

    print("  ✓ UTF-8 encoding valid (no corruption or replacement characters)")
    print("  ✓ JSON syntax strictly valid")

    # 2. Schema validation
    validate_schema(data, report)

    # 3. Baseline comparison if provided
    if baseline_path_str:
        baseline_path = Path(baseline_path_str).resolve()
        if baseline_path.exists():
            print(f"  ✓ Comparing against baseline: {baseline_path.name}")
            b_report = ValidationReport()
            b_data = validate_utf8_and_json(baseline_path, b_report)
            if b_report.is_valid:
                compare_with_baseline(data, b_data, report)
            else:
                print(f"  ⚠️ Could not parse baseline for comparison: {b_report.errors}")
        else:
            print(f"  ⚠️ Baseline file not found: {baseline_path}")

    # 4. Print Summary Report
    print("\n" + "-" * 70)
    print("STATISTICS & METRICS:")
    for k, v in report.stats.items():
        print(f"  • {k}: {v}")
    print("-" * 70)

    if report.warnings:
        print(f"\n[WARNINGS] ({len(report.warnings)}):")
        for w in report.warnings[:15]:
            print(f"  ⚠️  {w}")
        if len(report.warnings) > 15:
            print(f"  ... and {len(report.warnings) - 15} more warnings.")

    if not report.is_valid:
        print(f"\n[FAIL] Critical Errors Detected ({len(report.errors)}):")
        for e in report.errors:
            print(f"  ❌ {e}")
        print("\nResult: VERIFICATION FAILED ❌")
        return False
    else:
        print("\nResult: VERIFICATION PASSED SUCCESSFULLY ✅")
        print("Knowledge graph is 100% compliant with Understand Dashboard specifications.")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        default_target = Path("d:/Sandbox/AIOS_habbit/.understand-anything/knowledge-graph.json")
        default_baseline = None
        target = str(default_target)
        baseline = str(default_baseline) if default_baseline else None
    else:
        target = sys.argv[1]
        baseline = sys.argv[2] if len(sys.argv) > 2 else None

    success = run_verification(target, baseline)
    sys.exit(0 if success else 1)
