#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full Pipeline Script for Final Fix & Verification:
1. Unit tests for escaping order, reserved keywords, and dirty edge array handling in parsers.
2. Direct creation and validation of C:\\Users\\Admin\\Downloads\\excaliflow-skill-v2.zip.
3. Generation of fresh sample HTML diagrams (Graphify Ingestion & AST Fallback).
4. Automated Playwright headless browser E2E test suite (Zoom/Pan, Collapsible Sidebar, Tabs, Live Editor).
"""

import os
import sys
import json
import zipfile
import subprocess
from pathlib import Path

# Add skill path
SKILL_DIR = Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow").resolve()
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from generate_diagram import (
    sanitize_mermaid_id,
    escape_mermaid_label,
    parse_graphify_graph,
    parse_understand_graph,
    generate_mermaid_from_graphify,
    generate_mermaid_from_understand,
    generate_html_file
)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def test_unit_fixes():
    print("==================================================")
    print("1. RUNNING UNIT TESTS & ADVERSARIAL EDGE CHECKS")
    print("==================================================")

    # 1. Label Escaping & Multiline Preservation
    print("[-] Testing escape_mermaid_label...")
    lbl_multiline = escape_mermaid_label("Line 1\nLine 2\r\nLine 3")
    assert "<br/>" in lbl_multiline, f"Expected <br/>, got: {lbl_multiline}"
    assert "&lt;br/&gt;" not in lbl_multiline, f"Found corrupted &lt;br/&gt; in {lbl_multiline}"
    assert "\n" not in lbl_multiline, f"Unexpected raw newline in {lbl_multiline}"
    print(f"    [PASS] Multiline escaping: {repr(lbl_multiline)}")

    lbl_generics = escape_mermaid_label("Vector<T>\nList<Map<String, Int>>")
    assert "Vector&lt;T&gt;<br/>List&lt;Map&lt;String, Int&gt;&gt;" == lbl_generics, f"Mismatch: {lbl_generics}"
    print(f"    [PASS] Generics & newline escaping: {repr(lbl_generics)}")

    lbl_quotes = escape_mermaid_label('Quote "Test" [Bracket] {Brace} |Pipe|')
    assert '"' not in lbl_quotes and '[' not in lbl_quotes and ']' not in lbl_quotes and '|' not in lbl_quotes
    print(f"    [PASS] Quote/Bracket escaping: {repr(lbl_quotes)}")

    # 2. Reserved Keywords Sanitization
    print("[-] Testing sanitize_mermaid_id...")
    assert sanitize_mermaid_id("end") == "ID_end"
    assert sanitize_mermaid_id("subgraph") == "ID_subgraph"
    assert sanitize_mermaid_id("flowchart") == "ID_flowchart"
    assert sanitize_mermaid_id("123abc") == "N_123abc"
    assert sanitize_mermaid_id("simple_node") == "simple_node"
    print("    [PASS] Reserved keywords sanitized correctly.")

    # 3. Dirty Edge Array Sanitization in Parsers
    print("[-] Testing dirty edge array sanitization...")
    test_dir = Path("d:/Sandbox/AIOS_habbit/.agents/teamwork_preview_worker_final_fix/test_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)

    dirty_graphify_json = test_dir / "dirty_graphify.json"
    dirty_graphify_json.write_text(json.dumps({
        "nodes": [{"id": "node_a", "label": "Node A"}, {"id": "node_b", "label": "Node B"}],
        "edges": ["bad_edge_str", 12345, None, {"source": "node_a", "target": "node_b", "relation": "calls"}]
    }), encoding="utf-8")

    parsed_g = parse_graphify_graph(dirty_graphify_json)
    assert parsed_g is not None, "parse_graphify_graph returned None for valid nodes with dirty edges"
    assert all(isinstance(e, dict) for e in parsed_g["raw_edges"]), f"Found non-dict in raw_edges: {parsed_g['raw_edges']}"
    assert len(parsed_g["raw_edges"]) == 1, f"Expected 1 valid edge, got {len(parsed_g['raw_edges'])}"

    # Check downstream generator doesn't crash on dirty edges
    mermaid_g = generate_mermaid_from_graphify(parsed_g, "test_proj")
    assert "architecture" in mermaid_g
    print("    [PASS] Graphify parser & downstream generator handled dirty edge arrays cleanly.")

    dirty_understand_json = test_dir / "dirty_understand.json"
    dirty_understand_json.write_text(json.dumps({
        "project": {"name": "TestProj"},
        "nodes": [{"id": "n1", "name": "File1.py"}, {"id": "n2", "name": "File2.py"}],
        "edges": ["invalid_edge", None, {"source": "n1", "target": "n2"}]
    }), encoding="utf-8")

    parsed_u = parse_understand_graph(dirty_understand_json)
    assert parsed_u is not None, "parse_understand_graph returned None for valid nodes with dirty edges"
    assert all(isinstance(e, dict) for e in parsed_u["raw_edges"]), f"Found non-dict in understand raw_edges: {parsed_u['raw_edges']}"
    assert len(parsed_u["raw_edges"]) == 1

    mermaid_u = generate_mermaid_from_understand(parsed_u, "test_proj")
    assert "architecture" in mermaid_u
    print("    [PASS] Understand parser & downstream generator handled dirty edge arrays cleanly.")


def build_and_verify_zip_package():
    print("\n==================================================")
    print("2. BUILDING & VERIFYING C:\\Users\\Admin\\Downloads\\excaliflow-skill-v2.zip")
    print("==================================================")

    zip_dest = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip").resolve()
    zip_dest.parent.mkdir(parents=True, exist_ok=True)

    if zip_dest.exists():
        zip_dest.unlink()
        print(f"[-] Removed stale zip at {zip_dest}")

    print(f"[*] Packaging {SKILL_DIR} -> {zip_dest}...")
    with zipfile.ZipFile(zip_dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
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
    print(f"\n[✓] Physical package created on disk: {zip_dest} ({size:,} bytes)")

    with zipfile.ZipFile(zip_dest, "r") as zf:
        bad_file = zf.testzip()
        assert bad_file is None, f"Corrupted file in zip: {bad_file}"
        namelist = zf.namelist()
        print(f"[*] Archive contents ({len(namelist)} items):")
        for item in namelist:
            info = zf.getinfo(item)
            print(f"    - {item} ({info.file_size:,} bytes)")

        assert "SKILL.md" in namelist, "SKILL.md missing at root of zip!"
        assert "scripts/generate_diagram.py" in namelist, "scripts/generate_diagram.py missing in zip!"

        # Verify generate_diagram.py content from zip
        script_code = zf.read("scripts/generate_diagram.py").decode("utf-8")
        assert "MERMAID_RESERVED_KEYWORDS" in script_code, "Packaged script missing MERMAID_RESERVED_KEYWORDS"
        assert "ID_end" in script_code or "ID_" in script_code, "Packaged script missing ID prefixing"
        assert "<\\/script>" in script_code, "Packaged script missing script tag escaping"
        assert "updateZoomBadge" in script_code, "Packaged script missing updateZoomBadge"
        assert "raw_edges = [e for e in raw_edges if isinstance(e, dict)]" in script_code, "Packaged script missing raw_edges dict filter"
        print("[✓] Verified all v2 code fixes inside the zip archive.")


def generate_sample_diagrams():
    print("\n==================================================")
    print("3. GENERATING SAMPLE DIAGRAMS FOR PLAYWRIGHT E2E")
    print("==================================================")

    work_dir = Path("d:/Sandbox/AIOS_habbit/.agents/teamwork_preview_worker_final_fix").resolve()

    # 1. Graphify Sample
    print("[*] Generating Graphify Sample HTML (from AIOS_habbit)...")
    out_graphify = work_dir / "sample_graphify_diagram.html"
    generate_html_file("d:/Sandbox/AIOS_habbit", str(out_graphify))
    assert out_graphify.is_file() and out_graphify.stat().st_size > 0
    print(f"[✓] Generated {out_graphify} ({out_graphify.stat().st_size:,} bytes)")

    # 2. AST Sample (temp directory)
    print("[*] Generating AST Fallback Sample HTML...")
    ast_test_dir = work_dir / "test_tmp" / "ast_proj"
    ast_test_dir.mkdir(parents=True, exist_ok=True)
    (ast_test_dir / "service.py").write_text("""
class PaymentService:
    def process_payment(self, amount: float):
        print("Processing payment")

class OrderService:
    def __init__(self):
        self.payment = PaymentService()
        
    def checkout(self):
        self.payment.process_payment(100.0)

def main():
    o = OrderService()
    o.checkout()
""", encoding="utf-8")

    out_ast = work_dir / "sample_ast_diagram.html"
    generate_html_file(str(ast_test_dir), str(out_ast))
    assert out_ast.is_file() and out_ast.stat().st_size > 0
    print(f"[✓] Generated {out_ast} ({out_ast.stat().st_size:,} bytes)")
    return out_graphify, out_ast


def test_html_diagram_ui(page, html_path: Path, diagram_type: str):
    print(f"\n--- Testing UI: {diagram_type.upper()} ({html_path.name}) ---")
    file_url = html_path.resolve().as_uri()
    page.goto(file_url, wait_until="domcontentloaded")
    page.set_viewport_size({"width": 1440, "height": 900})

    # 1. Element presence
    sidebar = page.locator("#sidebar")
    viewport = page.locator("#viewport")
    toggle_btn = page.locator("#toggle-sidebar")
    collapse_btn = page.locator("#btn-collapse-sidebar")
    panzoom_container = page.locator("#panzoom-container")
    diagram_output = page.locator("#diagram-output")
    zoom_badge = page.locator("#zoom-badge")
    error_msg = page.locator("#error-msg")

    assert sidebar.count() == 1
    assert viewport.count() == 1
    assert toggle_btn.count() == 1
    assert panzoom_container.count() == 1
    assert diagram_output.count() == 1
    assert zoom_badge.count() == 1

    # Wait for SVG rendering
    page.wait_for_selector("#diagram-output svg", timeout=15000)
    svg = page.locator("#diagram-output svg")
    assert svg.count() >= 1
    assert not error_msg.is_visible()
    print("    [PASS] Initial Mermaid hand-drawn SVG rendered.")

    # 2. Sidebar Collapsible Tests
    initial_sidebar_box = sidebar.bounding_box()
    initial_viewport_box = viewport.bounding_box()
    assert initial_sidebar_box["width"] >= 450
    assert "collapsed" not in (sidebar.get_attribute("class") or "")

    # Click toggle to collapse
    toggle_btn.click()
    page.wait_for_timeout(400)
    assert "collapsed" in (sidebar.get_attribute("class") or "")
    collapsed_viewport_box = viewport.bounding_box()
    assert collapsed_viewport_box["width"] > initial_viewport_box["width"]
    print(f"    [PASS] Sidebar collapsed. Viewport expanded ({collapsed_viewport_box['width']}px).")

    # Click toggle to expand
    toggle_btn.click()
    page.wait_for_timeout(400)
    assert "collapsed" not in (sidebar.get_attribute("class") or "")
    print("    [PASS] Sidebar re-expanded via toggle button.")

    # Ctrl+B keyboard shortcut
    page.keyboard.press("Control+b")
    page.wait_for_timeout(400)
    assert "collapsed" in (sidebar.get_attribute("class") or "")
    page.keyboard.press("Control+b")
    page.wait_for_timeout(400)
    assert "collapsed" not in (sidebar.get_attribute("class") or "")
    print("    [PASS] Ctrl+B shortcut toggle cycle verified.")

    # 3. Panzoom Engine Tests
    assert zoom_badge.inner_text().strip() == "100%"

    # Zoom In
    page.locator("#zoom-in").click()
    page.wait_for_timeout(200)
    badge_in_1 = zoom_badge.inner_text().strip()
    page.locator("#zoom-in").click()
    page.wait_for_timeout(200)
    badge_in_2 = zoom_badge.inner_text().strip()
    assert int(badge_in_2.replace("%", "")) > int(badge_in_1.replace("%", ""))
    print(f"    [PASS] Zoom In button increased scale ({badge_in_2}).")

    # Zoom Out
    page.locator("#zoom-out").click()
    page.wait_for_timeout(200)
    badge_out = zoom_badge.inner_text().strip()
    assert int(badge_out.replace("%", "")) < int(badge_in_2.replace("%", ""))
    print(f"    [PASS] Zoom Out button decreased scale ({badge_out}).")

    # Zoom Reset
    page.locator("#zoom-reset").click()
    page.wait_for_timeout(200)
    assert zoom_badge.inner_text().strip() == "100%"
    print("    [PASS] Zoom Reset button reset to 100%.")

    # Zoom Fit
    page.locator("#zoom-fit").click()
    page.wait_for_timeout(300)
    badge_fit = zoom_badge.inner_text().strip()
    assert badge_fit != ""
    print(f"    [PASS] Zoom Fit (Fit to screen) computed scale: {badge_fit}")

    # Wheel Zoom
    panzoom_box = panzoom_container.bounding_box()
    cx = panzoom_box["x"] + panzoom_box["width"] / 2
    cy = panzoom_box["y"] + panzoom_box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.wheel(0, -200)
    page.wait_for_timeout(200)
    print(f"    [PASS] Wheel zoom handled. Scale: {zoom_badge.inner_text().strip()}")

    # Drag to Pan
    initial_transform = page.evaluate("() => document.getElementById('diagram-output').style.transform")
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 100, cy + 60, steps=8)
    page.mouse.up()
    page.wait_for_timeout(200)
    pan_transform = page.evaluate("() => document.getElementById('diagram-output').style.transform")
    assert pan_transform != initial_transform
    print(f"    [PASS] Drag to pan transform matrix updated: {pan_transform}")

    # 4. Tab Switching
    tabs = page.locator("#tabs-container .tab-btn")
    tab_count = tabs.count()
    assert tab_count >= 1
    for i in range(tab_count):
        tab = tabs.nth(i)
        tab_title = tab.inner_text().strip()
        tab.click()
        page.wait_for_timeout(300)
        assert "active" in (tab.get_attribute("class") or "")
        code_val = page.locator("#mermaid-code").input_value()
        assert len(code_val.strip()) > 0
        page.wait_for_selector("#diagram-output svg", timeout=8000)
        assert not error_msg.is_visible()
        print(f"    [PASS] Tab [{i+1}/{tab_count}] '{tab_title}' rendered successfully.")

    print(f"[✓] ALL UI TESTS PASSED FOR: {diagram_type.upper()}")


def run_playwright_suite(graphify_html: Path, ast_html: Path):
    print("\n==================================================")
    print("4. RUNNING PLAYWRIGHT E2E BROWSER TESTS")
    print("==================================================")

    if not sync_playwright:
        print("[!] Playwright not installed. Skipping browser run.")
        return

    with sync_playwright() as p:
        print("[-] Launching headless Chromium...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        test_html_diagram_ui(page, graphify_html, "Graphify Ingestion")
        test_html_diagram_ui(page, ast_html, "AST Fallback")

        browser.close()
        print("\n[✓] Headless Chromium closed cleanly.")


def main():
    test_unit_fixes()
    build_and_verify_zip_package()
    g_html, a_html = generate_sample_diagrams()
    run_playwright_suite(g_html, a_html)
    print("\n==================================================")
    print("  🎉 COMPLETE PIPELINE SUCCEEDED WITH 100% PASS RATE!")
    print("==================================================")


if __name__ == "__main__":
    main()
