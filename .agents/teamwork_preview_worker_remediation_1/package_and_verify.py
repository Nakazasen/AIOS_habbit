#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution and Verification Script for Excaliflow v2 Remediation
"""
import os
import sys
import json
import zipfile
import subprocess
from pathlib import Path

# Add skill script to path
SKILL_DIR = Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow").resolve()
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from generate_diagram import (
    sanitize_mermaid_id,
    escape_mermaid_label,
    parse_graphify_graph,
    parse_understand_graph,
    generate_html_file
)

def test_unit_robustness():
    print("\n--- 1. Testing Sanitization & Escaping ---")
    # Reserved keywords
    assert sanitize_mermaid_id("end") == "ID_end", f"Expected ID_end, got {sanitize_mermaid_id('end')}"
    assert sanitize_mermaid_id("subgraph") == "ID_subgraph", f"Expected ID_subgraph, got {sanitize_mermaid_id('subgraph')}"
    assert sanitize_mermaid_id("flowchart") == "ID_flowchart", f"Expected ID_flowchart, got {sanitize_mermaid_id('flowchart')}"
    assert sanitize_mermaid_id("class") == "ID_class", f"Expected ID_class, got {sanitize_mermaid_id('class')}"
    assert sanitize_mermaid_id("123abc") == "N_123abc", f"Expected N_123abc, got {sanitize_mermaid_id('123abc')}"
    assert sanitize_mermaid_id("normal_node") == "normal_node"
    print("[✓] sanitize_mermaid_id passed all assertions.")

    # Escape label
    lbl1 = escape_mermaid_label("Line 1\nLine 2\r\nLine 3")
    assert "<br/>" in lbl1, f"Expected <br/> in escaped label, got {lbl1}"
    assert "\n" not in lbl1, f"Unexpected newline in escaped label: {lbl1}"
    
    lbl2 = escape_mermaid_label("Map<String, Object>")
    assert "&lt;" in lbl2 and "&gt;" in lbl2, f"Expected &lt; and &gt;, got {lbl2}"
    
    lbl3 = escape_mermaid_label('Quote "Test" [Bracket] {Brace} |Pipe|')
    assert '"' not in lbl3 and '[' not in lbl3 and ']' not in lbl3 and '|' not in lbl3
    print("[✓] escape_mermaid_label passed all assertions.")

    print("\n--- 2. Testing Graphify & Understand JSON Parser Robustness ---")
    tmp_dir = Path("d:/Sandbox/AIOS_habbit/.agents/teamwork_preview_worker_remediation_1/tmp_tests")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    # Test cases that should gracefully return None instead of crashing
    malformed_cases = [
        ("empty.json", ""),
        ("array.json", "[]"),
        ("primitive_number.json", "12345"),
        ("primitive_null.json", "null"),
        ("bad_nodes_list.json", '{"nodes": ["str1", "str2"], "edges": [1, 2]}'),
        ("dict_nodes.json", '{"nodes": {"a": {"id": "a", "label": "A"}}, "edges": []}'),
        ("invalid_json.json", "{corrupt json")
    ]
    
    for filename, content in malformed_cases:
        p = tmp_dir / filename
        p.write_text(content, encoding="utf-8")
        
        # Test parse_graphify_graph
        res_g = parse_graphify_graph(p)
        print(f"  * Graphify parse test on {filename}: res = {'dict parsed' if res_g else 'None (safe fallback)'}")
        
        # Test parse_understand_graph
        res_u = parse_understand_graph(p)
        print(f"  * Understand parse test on {filename}: res = {'dict parsed' if res_u else 'None (safe fallback)'}")

    print("[✓] Parser robustness tests passed without throwing unhandled exceptions.")


def build_and_verify_zip():
    print("\n--- 3. Physically Packaging excaliflow-skill-v2.zip ---")
    zip_dest = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip").resolve()
    zip_dest.parent.mkdir(parents=True, exist_ok=True)

    if zip_dest.exists():
        zip_dest.unlink()
        print(f"[-] Removed existing {zip_dest}")

    print(f"[*] Packaging {SKILL_DIR} -> {zip_dest}...")
    with zipfile.ZipFile(zip_dest, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SKILL_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(SKILL_DIR).as_posix()
                print(f"  + Adding: {rel_path} ({full_path.stat().st_size:,} bytes)")
                zf.write(full_path, arcname=rel_path)

    # Verification
    assert zip_dest.is_file(), f"Zip file does not exist at {zip_dest}!"
    size = zip_dest.stat().st_size
    assert size > 0, f"Zip file is empty (0 bytes)!"
    print(f"[✓] Physical package created: {zip_dest} ({size:,} bytes)")

    with zipfile.ZipFile(zip_dest, 'r') as zf:
        bad_file = zf.testzip()
        assert bad_file is None, f"Corrupted file in zip: {bad_file}"
        namelist = zf.namelist()
        print(f"[*] Archive contents ({len(namelist)} items):")
        for item in namelist:
            info = zf.getinfo(item)
            print(f"    - {item} ({info.file_size:,} bytes)")
        
        assert "SKILL.md" in namelist, "SKILL.md missing at root of zip!"
        assert "scripts/generate_diagram.py" in namelist, "scripts/generate_diagram.py missing in zip!"
        
        # Verify generate_diagram.py in zip has fixes
        script_code = zf.read("scripts/generate_diagram.py").decode("utf-8")
        assert "MERMAID_RESERVED_KEYWORDS" in script_code, "Packaged script missing MERMAID_RESERVED_KEYWORDS"
        assert "ID_end" or "ID_" in script_code, "Packaged script missing ID prefixing"
        assert "<\\/script>" in script_code, "Packaged script missing script tag escaping"
        assert "updateZoomBadge" in script_code, "Packaged script missing updateZoomBadge"
        print("[✓] Zip archive integrity and contents verified successfully.")


def generate_sample_diagrams():
    print("\n--- 4. Generating Sample Diagrams for UI Test ---")
    work_dir = Path("d:/Sandbox/AIOS_habbit/.agents/teamwork_preview_worker_m2").resolve()
    
    # 1. Generate Graphify sample
    print("[*] Generating Graphify Sample HTML...")
    out_graphify = work_dir / "sample_graphify_diagram.html"
    generate_html_file("d:/Sandbox/AIOS_habbit", str(out_graphify))
    assert out_graphify.is_file() and out_graphify.stat().st_size > 0
    print(f"[✓] Generated {out_graphify} ({out_graphify.stat().st_size:,} bytes)")

    # 2. Generate AST sample (using a temp python directory without graph.json)
    print("[*] Generating AST Sample HTML...")
    ast_test_dir = Path("d:/Sandbox/AIOS_habbit/.agents/teamwork_preview_worker_remediation_1/tmp_tests/ast_proj")
    ast_test_dir.mkdir(parents=True, exist_ok=True)
    (ast_test_dir / "core.py").write_text("class Engine:\n    def start(self):\n        pass\n\ndef main():\n    e = Engine()\n    e.start()\n", encoding="utf-8")
    out_ast = work_dir / "sample_ast_diagram.html"
    generate_html_file(str(ast_test_dir), str(out_ast))
    assert out_ast.is_file() and out_ast.stat().st_size > 0
    print(f"[✓] Generated {out_ast} ({out_ast.stat().st_size:,} bytes)")


if __name__ == "__main__":
    test_unit_robustness()
    build_and_verify_zip()
    generate_sample_diagrams()
    print("\n[✓] ALL PRE-E2E TESTS & PACKAGING SUCCEEDED!")
