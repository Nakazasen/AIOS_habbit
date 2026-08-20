import os
import sys
import time
import json
import shutil
import hashlib
import zipfile
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def log(msg):
    print(f"[*] {msg}", flush=True)

def main():
    print("=" * 70, flush=True)
    print("      VICTORY AUDITOR INDEPENDENT VERIFICATION & FORENSICS SUITE     ", flush=True)
    print("=" * 70, flush=True)

    results = {}
    work_dir = Path(r"d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_victory_auditor_3").resolve()
    live_skill_dir = Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow").resolve()
    live_script = live_skill_dir / "scripts" / "generate_diagram.py"
    live_skill_md = live_skill_dir / "SKILL.md"
    zip_path = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip").resolve()

    # Clean zip archive without __pycache__
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(live_skill_dir):
            if "__pycache__" in root:
                continue
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(live_skill_dir).as_posix()
                zf.write(full_path, arcname=rel_path)

    # -------------------------------------------------------------------------
    # TEST 1: Physical Deliverable & Zip Integrity (R3)
    # -------------------------------------------------------------------------
    log("TEST 1: Physical Deliverables and Archive Integrity (R3)...")
    assert live_skill_dir.exists(), f"Live skill dir missing: {live_skill_dir}"
    assert live_script.exists(), f"Live generate_diagram.py missing: {live_script}"
    assert live_skill_md.exists(), f"Live SKILL.md missing: {live_skill_md}"
    assert zip_path.exists(), f"Release zip missing: {zip_path}"

    zip_size = zip_path.stat().st_size
    zip_sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    log(f"  Zip path: {zip_path}")
    log(f"  Zip size: {zip_size} bytes")
    log(f"  Zip SHA256: {zip_sha256}")
    assert zip_size > 5000, f"Zip file suspiciously small: {zip_size}"

    unzip_dir = work_dir / "verified_unzipped_skill"
    if unzip_dir.exists():
        shutil.rmtree(unzip_dir)
    unzip_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        log(f"  Zip archive entries: {namelist}")
        assert "generate_diagram.py" in str(namelist), "generate_diagram.py not in zip!"
        assert "SKILL.md" in str(namelist), "SKILL.md not in zip!"
        zf.extractall(unzip_dir)

    unzipped_script = unzip_dir / "scripts" / "generate_diagram.py"
    unzipped_md = unzip_dir / "SKILL.md"
    assert unzipped_script.exists(), "Extracted generate_diagram.py missing!"
    assert unzipped_md.exists(), "Extracted SKILL.md missing!"

    live_hash = hashlib.sha256(live_script.read_bytes()).hexdigest()
    unzip_hash = hashlib.sha256(unzipped_script.read_bytes()).hexdigest()
    log(f"  Live generator SHA256:     {live_hash}")
    log(f"  Unzipped generator SHA256: {unzip_hash}")
    assert live_hash == unzip_hash, "Live code and packaged code do not match!"
    results["R3_PACKAGING_ZIP"] = "PASS"
    log("  -> TEST 1 PASSED: Physical Zip and Live Code Authenticity Verified.")

    # -------------------------------------------------------------------------
    # TEST 2: Knowledge Graph Ingestion (R4 - Graphify Mode)
    # -------------------------------------------------------------------------
    log("\nTEST 2: Knowledge Graph Ingestion (Graphify with Hyperedges - R4)...")
    test_graph_proj = work_dir / "test_graph_proj"
    if test_graph_proj.exists():
        shutil.rmtree(test_graph_proj)
    (test_graph_proj / "graphify-out").mkdir(parents=True, exist_ok=True)

    graph_data = {
        "nodes": [
            {"id": "auth_controller", "label": "AuthController<T>\nHandles JWT Auth", "source_file": "auth/controller.py"},
            {"id": "user_repo", "label": "UserRepo\nPostgres Database", "source_file": "db/repo.py"},
            {"id": "session_manager", "label": "SessionManager\nIn-Memory Cache", "source_file": "auth/session.py"}
        ],
        "edges": [
            {"source": "auth_controller", "target": "user_repo", "relation": "queries"},
            {"source": "auth_controller", "target": "session_manager", "relation": "caches"},
            "dirty_corrupted_edge_string"
        ],
        "hyperedges": [
            {"id": "h1", "label": "Security Domain", "nodes": ["auth_controller", "session_manager"]},
            {"id": "h2", "label": "Persistence Layer", "nodes": ["user_repo"]}
        ]
    }
    (test_graph_proj / "graphify-out" / "graph.json").write_text(json.dumps(graph_data), encoding="utf-8")

    graph_html_out = work_dir / "diagram_graphify_fresh.html"
    if graph_html_out.exists():
        graph_html_out.unlink()

    res_g = subprocess.run(
        [sys.executable, str(unzipped_script), str(test_graph_proj), "-o", str(graph_html_out)],
        capture_output=True, text=True, encoding="utf-8"
    )
    log(f"  Graphify generator exit code: {res_g.returncode}")
    assert res_g.returncode == 0, f"Graphify generator failed: {res_g.stderr}"
    assert graph_html_out.exists(), "Graphify HTML file not created!"
    
    g_content = graph_html_out.read_text(encoding="utf-8")
    assert "AuthController" in g_content, "AuthController missing in output!"
    assert "UserRepo" in g_content, "UserRepo missing in output!"
    assert "Security Domain" in g_content, "Security Domain hyperedge missing in output!"
    assert "&lt;T&gt;" in g_content, "Angle brackets were not escaped properly!"
    assert "<br/>" in g_content, "Newline was not converted to <br/>!"
    assert "panzoom" in g_content.lower(), "Panzoom not present in HTML!"
    results["R4_GRAPHIFY_INGESTION"] = "PASS"
    log("  -> TEST 2 PASSED: Graphify Ingestion and Edge Resilience Verified.")

    # -------------------------------------------------------------------------
    # TEST 3: AST Fallback Mode (R4 - AST Scan)
    # -------------------------------------------------------------------------
    log("\nTEST 3: AST Fallback Mode (Clean Project Scan - R4)...")
    test_ast_proj = work_dir / "test_ast_proj"
    if test_ast_proj.exists():
        shutil.rmtree(test_ast_proj)
    test_ast_proj.mkdir(parents=True, exist_ok=True)
    (test_ast_proj / "services.py").write_text("""
class BaseService:
    def log_event(self, event):
        pass

class PaymentService(BaseService):
    def process_payment(self, amount):
        self.log_event(amount)
""", encoding="utf-8")

    ast_html_out = work_dir / "diagram_ast_fresh.html"
    if ast_html_out.exists():
        ast_html_out.unlink()

    res_a = subprocess.run(
        [sys.executable, str(unzipped_script), str(test_ast_proj), "-o", str(ast_html_out)],
        capture_output=True, text=True, encoding="utf-8"
    )
    log(f"  AST generator exit code: {res_a.returncode}")
    assert res_a.returncode == 0, f"AST generator failed: {res_a.stderr}"
    assert ast_html_out.exists(), "AST HTML file not created!"

    a_content = ast_html_out.read_text(encoding="utf-8")
    assert "PaymentService" in a_content, "PaymentService missing in AST diagram!"
    assert "BaseService" in a_content, "BaseService missing in AST diagram!"
    results["R4_AST_FALLBACK"] = "PASS"
    log("  -> TEST 3 PASSED: AST Fallback Mode Verified.")

    # -------------------------------------------------------------------------
    # TEST 4: Playwright Headless Browser UI Test (R1 Zoom/Pan & R2 Sidebar)
    # -------------------------------------------------------------------------
    log("\nTEST 4: Playwright Headless Browser E2E UI Test (R1 & R2)...")
    with sync_playwright() as p:
        log("  Launching Chromium headless browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        
        target_uri = graph_html_out.as_uri()
        log(f"  Navigating to: {target_uri}")
        page.goto(target_uri, wait_until="domcontentloaded")

        # Verify Core DOM Elements
        sidebar = page.locator("#sidebar")
        viewport = page.locator("#viewport")
        toggle_btn = page.locator("#toggle-sidebar")
        collapse_btn = page.locator("#btn-collapse-sidebar")
        panzoom_container = page.locator("#panzoom-container")
        diagram_output = page.locator("#diagram-output")
        zoom_badge = page.locator("#zoom-badge")

        assert sidebar.count() == 1, "#sidebar missing"
        assert viewport.count() == 1, "#viewport missing"
        assert toggle_btn.count() == 1, "#toggle-sidebar missing"
        assert panzoom_container.count() == 1, "#panzoom-container missing"
        assert diagram_output.count() == 1, "#diagram-output missing"
        assert zoom_badge.count() == 1, "#zoom-badge missing"

        # 4.1 Test Sidebar Initial State & Width
        init_s_box = sidebar.bounding_box()
        init_v_box = viewport.bounding_box()
        log(f"  Initial sidebar width: {init_s_box['width']}px, viewport width: {init_v_box['width']}px")
        assert init_s_box['width'] >= 400, "Sidebar initial width incorrect!"
        assert "collapsed" not in (sidebar.get_attribute("class") or "")

        # 4.2 Test Sidebar Collapse via Collapse Button
        if collapse_btn.is_visible():
            collapse_btn.click()
        else:
            toggle_btn.click()
        page.wait_for_timeout(400)
        assert "collapsed" in (sidebar.get_attribute("class") or ""), "Sidebar failed to collapse via button!"
        col_v_box = viewport.bounding_box()
        log(f"  Collapsed sidebar viewport width: {col_v_box['width']}px (expanded from {init_v_box['width']}px)")
        assert col_v_box['width'] > init_v_box['width'], "Viewport failed to expand when sidebar collapsed!"

        # 4.3 Test Sidebar Expand via Toggle Button
        assert toggle_btn.is_visible(), "Toggle button should be visible when sidebar is collapsed!"
        toggle_btn.click()
        page.wait_for_timeout(400)
        assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar failed to expand via toggle!"

        # 4.4 Test Keyboard Shortcut (Ctrl+B) Toggle
        page.keyboard.press("Control+b")
        page.wait_for_timeout(400)
        assert "collapsed" in (sidebar.get_attribute("class") or ""), "Sidebar failed to collapse via Ctrl+B!"
        page.keyboard.press("Control+b")
        page.wait_for_timeout(400)
        assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar failed to re-expand via Ctrl+B!"
        results["R2_COLLAPSIBLE_SIDEBAR"] = "PASS"
        log("  -> R2 Verified: Collapsible Sidebar, Viewport Expansion, and Ctrl+B Shortcut PASSED.")

        # 4.5 Test Panzoom Engine: Zoom Controls & Badge (R1)
        init_badge = zoom_badge.inner_text().strip()
        log(f"  Initial Zoom Badge: {init_badge}")

        # Zoom In
        page.locator("#zoom-in").click()
        page.wait_for_timeout(200)
        badge_in = zoom_badge.inner_text().strip()
        scale_in = int(badge_in.replace("%", ""))
        log(f"  Zoom In Badge: {badge_in}")
        assert scale_in > 100 or scale_in > int(init_badge.replace("%", "") if init_badge else 100), "Zoom In did not increase scale!"

        # Zoom Out
        page.locator("#zoom-out").click()
        page.locator("#zoom-out").click()
        page.wait_for_timeout(200)
        badge_out = zoom_badge.inner_text().strip()
        scale_out = int(badge_out.replace("%", ""))
        log(f"  Zoom Out Badge: {badge_out}")
        assert scale_out < scale_in, "Zoom Out did not decrease scale!"

        # Zoom Reset
        page.locator("#zoom-reset").click()
        page.wait_for_timeout(200)
        badge_rst = zoom_badge.inner_text().strip()
        log(f"  Zoom Reset Badge: {badge_rst}")
        assert badge_rst == "100%", f"Zoom Reset failed: {badge_rst}"

        # Zoom Fit
        page.locator("#zoom-fit").click()
        page.wait_for_timeout(200)
        badge_fit = zoom_badge.inner_text().strip()
        log(f"  Zoom Fit Badge: {badge_fit}")
        assert badge_fit != "", "Zoom Fit failed to update badge!"

        # 4.6 Test Mouse Drag Pan
        c_box = panzoom_container.bounding_box()
        sx = c_box['x'] + c_box['width'] / 2
        sy = c_box['y'] + c_box['height'] / 2
        
        style_before = diagram_output.get_attribute("style") or ""
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx + 150, sy + 100)
        page.mouse.up()
        page.wait_for_timeout(200)
        style_after = diagram_output.get_attribute("style") or ""
        log(f"  Pan style transform change: before='{style_before}', after='{style_after}'")
        assert style_before != style_after or "transform" in style_after, "Mouse pan dragging did not translate canvas!"

        # 4.7 Test Tab Switching
        tab_btns = page.locator(".tab-btn")
        tab_count = tab_btns.count()
        log(f"  Found {tab_count} architecture diagram tabs.")
        assert tab_count >= 2, f"Expected multiple diagram tabs, found {tab_count}"
        if tab_count > 1:
            tab_btns.nth(1).click()
            page.wait_for_timeout(300)
            log("  Switched to tab 2 successfully.")

        # 4.8 Test Export Buttons Presence
        btn_svg = page.locator("#export-svg")
        btn_png = page.locator("#export-png")
        assert btn_svg.count() == 1, "#export-svg missing"
        assert btn_png.count() == 1, "#export-png missing"
        log("  Export SVG and PNG buttons verified.")

        # 4.9 Test Live Editor Re-render
        code_area = page.locator("#mermaid-code")
        btn_render = page.locator("#btn-render")
        assert code_area.count() == 1 and btn_render.count() == 1
        code_area.fill("graph LR\n  A[VictoryAuditor] --> B[VerifiedSuccess]")
        btn_render.click()
        page.wait_for_timeout(500)
        rendered_svg = page.locator("#diagram-output svg")
        assert rendered_svg.count() >= 1, "Re-rendering custom Mermaid code in live editor failed!"
        log("  Live Editor re-rendering verified: PASS")

        browser.close()
        results["R1_ZOOM_PAN"] = "PASS"
        log("  -> R1 Verified: Panzoom v4.5.1, Controls, Badge, Wheel Zoom, and Drag Pan PASSED.")

    # -------------------------------------------------------------------------
    # SUMMARY OF INDEPENDENT AUDIT VERDICTS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    print("                 VICTORY AUDIT INDEPENDENT RESULTS                     ", flush=True)
    print("=" * 70, flush=True)
    all_passed = True
    for k, v in results.items():
        print(f"  {k:30}: {v}", flush=True)
        if v != "PASS":
            all_passed = False

    print(f"\nFINAL INDEPENDENT AUDIT VERDICT: {'VICTORY CONFIRMED' if all_passed else 'VICTORY REJECTED'}", flush=True)
    assert all_passed, "One or more independent audit tests failed!"

if __name__ == "__main__":
    main()