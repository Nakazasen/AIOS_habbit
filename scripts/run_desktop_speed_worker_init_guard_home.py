"""Script nghiem thu song ve DESKTOP-SPEED-WORKER-INIT-GUARD-HOME tren may nha h410asrock (CPU-only).

Yeu cau bat buoc cua ve:
- Cau hinh BB-CONFIG-PARITY-01, CPU-only.
- Co tinh dua worker ve trang thai chua san sang (khoi dong lai app, KHONG lam am truoc).
- Dat cau C7620 khoi LSU:
  "Ma loi C7620 tren dong may in Kyocera la loi gi, nguyen nhan va doi sach xu ly ra sao?"
- Luot phai hoan tat va co dong RETRIEVAL_MICRO_TIMING cua chinh luot trong nhat ky.
- KHONG xuat hien bge_worker_persist_timeout tren duong luot.
- Tong thoi gian luot phai giai trinh duoc bang marker.
- Trich nguyen van dong nhat ky kem ma hoi thoai.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

# Reconfigure encoding
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
DIEU_PHOI_DIR = Path(r"D:\Sandbox\aios-dieu-phoi")
OUT_DIR = DIEU_PHOI_DIR / "hop-thu" / "lan-desktop" / "ket-qua"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_MD_PATH = OUT_DIR / "DESKTOP-SPEED-WORKER-INIT-GUARD-HOME.md"
TIMINGS_JSON_PATH = OUT_DIR / "ket-qua-do-desktop-speed-worker-init-guard-home.json"
SERVER_LOG_PATH = OUT_DIR / "desktop_speed_worker_init_guard_home.log"
SESSION_LOG_PATH = OUT_DIR / "session_desktop_speed_worker_init_guard_home.log"

PORT = 8555
URL = f"http://localhost:{PORT}"
NOTEBOOK_LSU = "NB-C26E1C84"

sys.path.insert(0, str(APP_DIR / "src"))

import aios_habit.workspace_chat_store as store
store.LOCAL_CHAT_DIR = APP_DIR / "local_cases" / "workspace_chat"
store.NOTEBOOKS_FILE = store.LOCAL_CHAT_DIR / "notebooks.jsonl"
store.COLLECTIONS_FILE = store.LOCAL_CHAT_DIR / "collections.jsonl"
store.CONVERSATIONS_FILE = store.LOCAL_CHAT_DIR / "conversations.jsonl"
store.MESSAGES_FILE = store.LOCAL_CHAT_DIR / "messages.jsonl"
store.TEMPORARY_SOURCES_FILE = store.LOCAL_CHAT_DIR / "temporary_sources.jsonl"
store.NOTEBOOK_SOURCES_FILE = store.LOCAL_CHAT_DIR / "notebook_sources.jsonl"
store.SOURCE_SELECTIONS_FILE = store.LOCAL_CHAT_DIR / "conversation_source_selections.jsonl"
store.TRACES_FILE = store.LOCAL_CHAT_DIR / "traces.jsonl"
store.EXTERNAL_AI_USAGE_FILE = store.LOCAL_CHAT_DIR / "external_ai_usage.jsonl"

from aios_habit.workspace_chat_models import WorkspaceConversation
from playwright.sync_api import sync_playwright


def get_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(APP_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def wait_for_server(port: int, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_streamlit_server(log_file: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
    env["AIOS_BGE_INIT_TIMEOUT"] = "420"
    env["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "420"
    env["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "120"
    env["AIOS_AI_BACKEND"] = "nakazasen_router"
    env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["AIOS_STREAM_SYNTHESIS"] = "1"
    env["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    log_handle = open(log_file, "a", encoding="utf-8")
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc


def kill_server(proc: subprocess.Popen):
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass


def parse_turn_markers(log_file: Path, conv_id: str) -> dict:
    markers: dict = {
        "start": None,
        "first_token": None,
        "complete": None,
        "draft_fallback": None,
        "router_synth_start": None,
        "router_synth_done": None,
        "retrieval_micro": None,
        "retrieval_micro_raw": None,
        "ttft_s": None,
        "total_s": None,
        "backend": None,
        "ok": None,
        "warm_loop_steps": [],
        "warm_loop_exit": None,
        "has_persist_timeout": False,
        "all_turn_lines": [],
    }
    if not log_file.exists():
        return markers

    try:
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        start_idx = -1
        for i, l in enumerate(lines):
            if f"[STREAMING_QA_START] conv={conv_id}" in l:
                start_idx = i
                markers["start"] = l.strip()
                break

        if start_idx != -1:
            end_idx = len(lines)
            for j in range(start_idx, len(lines)):
                l = lines[j]
                if f"[STREAMING_QA_COMPLETE] conv={conv_id}" in l:
                    markers["complete"] = l.strip()
                    end_idx = j + 1
                    break
                elif f"[DRAFT_FALLBACK_COMPLETE] conv={conv_id}" in l:
                    markers["draft_fallback"] = l.strip()
                    end_idx = j + 1
                    break

            turn_lines = lines[start_idx:end_idx]
            markers["all_turn_lines"] = turn_lines

            for l in turn_lines:
                if "bge_worker_persist_timeout" in l:
                    markers["has_persist_timeout"] = True
                if "[STREAMING_QA_FIRST_TOKEN]" in l and f"conv={conv_id}" in l:
                    markers["first_token"] = l.strip()
                    if "ttft_s=" in l:
                        try:
                            markers["ttft_s"] = float(l.split("ttft_s=")[1].split()[0])
                        except Exception:
                            pass
                if "[ROUTER_SYNTH_START]" in l and f"conv={conv_id}" in l:
                    markers["router_synth_start"] = l.strip()
                if "[ROUTER_SYNTH_DONE]" in l and f"conv={conv_id}" in l:
                    markers["router_synth_done"] = l.strip()
                if "[RETRIEVAL_MICRO_TIMING]" in l:
                    markers["retrieval_micro_raw"] = l.strip()
                    # Parse micro timing
                    parts = l.split("[RETRIEVAL_MICRO_TIMING]")[1].strip().split()
                    res = {}
                    for p in parts:
                        if "=" in p:
                            k, v = p.split("=", 1)
                            if k in ("embed_ms", "dense_ms", "sparse_ms", "fuse_ms", "dense_load_ms"):
                                try:
                                    res[k] = float(v)
                                except Exception:
                                    res[k] = 0.0
                            elif k == "dense_resident":
                                res[k] = (v.lower() == "true")
                            else:
                                res[k] = v
                    if "embed_ms" in res and "dense_ms" in res:
                        res["total_retrieval_ms"] = round(
                            res.get("embed_ms", 0.0)
                            + res.get("dense_ms", 0.0)
                            + res.get("sparse_ms", 0.0)
                            + res.get("fuse_ms", 0.0),
                            2,
                        )
                        res["total_retrieval_s"] = round(res["total_retrieval_ms"] / 1000.0, 3)
                    markers["retrieval_micro"] = res
                if "[WORKER_WARM_LOOP_STEP]" in l:
                    markers["warm_loop_steps"].append(l.strip())
                if "[WORKER_WARM_LOOP_EXIT]" in l:
                    markers["warm_loop_exit"] = l.strip()

            comp_line = markers["complete"] or markers["draft_fallback"] or ""
            if comp_line:
                if "total_s=" in comp_line:
                    try:
                        markers["total_s"] = float(comp_line.split("total_s=")[1].split()[0])
                    except Exception:
                        pass
                if "backend=" in comp_line:
                    try:
                        markers["backend"] = comp_line.split("backend=")[1].split()[0]
                    except Exception:
                        pass
                if "ok=" in comp_line:
                    try:
                        markers["ok"] = (comp_line.split("ok=")[1].split()[0].lower() == "true")
                    except Exception:
                        pass
    except Exception as exc:
        print(f"[WARN] parse_turn_markers error: {exc}")

    return markers


def main():
    head_commit = get_git_head()
    print("=" * 80)
    print("NGHIEM THU SONG VE: DESKTOP-SPEED-WORKER-INIT-GUARD-HOME")
    print(f"Commit: {head_commit} | Python: 3.11.14 | Port: {PORT}")
    print("Dieu kien nghiem thu: Worker chua san sang (cold), hoi cau C7620 khoi LSU")
    print("=" * 80)

    if SERVER_LOG_PATH.exists():
        SERVER_LOG_PATH.unlink()
    if SESSION_LOG_PATH.exists():
        SESSION_LOG_PATH.unlink()

    session_logs: list[str] = []

    def log(msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} [INFO] {msg}"
        session_logs.append(line)
        print(line)
        with open(SESSION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("Khoi dong Streamlit server...")
    t_boot = time.perf_counter()
    server_proc = start_streamlit_server(SERVER_LOG_PATH, PORT)

    if not wait_for_server(PORT, timeout=90):
        log(f"[ERROR] Streamlit server khong khoi dong kip tren port {PORT}!")
        kill_server(server_proc)
        sys.exit(1)

    t_boot_ready = round(time.perf_counter() - t_boot, 3)
    log(f"Streamlit HTTP 200 san sang sau: {t_boot_ready}s")
    log("KHONG chay warming thu cong! Worker co tinh de o trang thai CHUA SAN SANG.")

    conv_id = f"CONV-GUARD-LSU-{uuid.uuid4().hex[:6].upper()}"
    question = "Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, nguyên nhân và đối sách xử lý ra sao?"
    khoi_code = "lsu"
    khoi_name = "LSU"
    so_id = NOTEBOOK_LSU

    conv = WorkspaceConversation(
        id=conv_id,
        notebook_id=so_id,
        title=f"Guard LSU {conv_id}",
        ai_mode="grounded",
    )
    store.save_conversation(conv)
    log(f"Da tao cuoc hoi thoai: {conv_id} tai so {so_id}")

    img_answer = OUT_DIR / "anh-speed-worker-init-guard-c7620-lsu.png"

    log("Khoi chay Playwright Chromium...")
    t_ui_total = 0.0
    ans_text = ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1800})
            page = context.new_page()

            nav_url = f"{URL}/?nb={so_id}&conv={conv_id}&block={khoi_code}"
            log(f"Dieu huong URL: {nav_url}")
            t_nav = time.perf_counter()
            page.goto(nav_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)
            log(f"Giao dien Chromium san sang sau: {time.perf_counter() - t_nav:.2f}s")

            # Kiem tra chip khoi LSU
            block_container = page.locator(f'[class*="st-key-wsc-block-{conv_id}"]')
            popover_btn = block_container.locator("button").first
            chip_text = popover_btn.inner_text().strip() if popover_btn.count() > 0 else ""
            log(f"Trang thai chip khoi hien tai: {chip_text}")

            if "LSU" not in chip_text and popover_btn.count() > 0:
                log("Chon lai khoi LSU...")
                popover_btn.click()
                page.wait_for_timeout(1000)
                pick_btn = page.locator(f'[class*="st-key-wsc_block_pick_{conv_id}_{khoi_code}"] button').first
                if pick_btn.count() > 0:
                    pick_btn.click(force=True)
                else:
                    popover_body = page.locator('[data-testid="stPopoverBody"]').first
                    target_btn = popover_body.locator('button:has-text("LSU")').first
                    if target_btn.count() > 0:
                        target_btn.click(force=True)
                page.wait_for_timeout(2500)
                chip_text = popover_btn.inner_text().strip()
                log(f"Chip sau khi chon: {chip_text}")

            # Dien cau hoi
            textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
            textarea.fill(question)
            page.wait_for_timeout(500)

            log(f"Bam gui cau hoi C7620 khoi LSU luc {time.strftime('%H:%M:%S')}...")
            t_send = time.perf_counter()
            send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button')
            if send_btn.count() > 0 and send_btn.first.is_visible():
                send_btn.first.click()
            else:
                textarea.press("Control+Enter")

            # Cho xac nhan luu tin nhan user vao DB (khong bam lai Control+Enter de tranh rerun huy task)
            user_saved = False
            for attempt in range(15):
                time.sleep(1.0)
                msgs = store.load_messages(conv_id)
                if any(m.role == "user" for m in msgs):
                    log(f"Tin nhan user da duoc luu DB (lan thu {attempt+1})")
                    user_saved = True
                    break
            if not user_saved:
                log("[WARN] Chua thay tin nhan user trong DB sau 15s, van tiep tuc theo doi...")

            # Cho assistant tra loi
            log("Dang cho assistant phan hoi (worker dang duoc khoi tao qua single-flight / warm loop)...")
            completed = False
            t_deadline = time.time() + 600
            while time.time() < t_deadline:
                msgs = store.load_messages(conv_id)
                asst_msg_cur = next((m for m in msgs if m.role == "assistant"), None)
                if asst_msg_cur and asst_msg_cur.content:
                    completed = True
                    ans_text = asst_msg_cur.content
                    break
                if SERVER_LOG_PATH.exists():
                    try:
                        log_txt = SERVER_LOG_PATH.read_text(encoding="utf-8", errors="ignore")
                        if (f"[STREAMING_QA_COMPLETE] conv={conv_id}" in log_txt or 
                            f"[DRAFT_FALLBACK_COMPLETE] conv={conv_id}" in log_txt):
                            time.sleep(2.0)
                            msgs = store.load_messages(conv_id)
                            asst_msg_cur = next((m for m in msgs if m.role == "assistant"), None)
                            if asst_msg_cur and asst_msg_cur.content:
                                completed = True
                                ans_text = asst_msg_cur.content
                                break
                    except Exception:
                        pass
                page.wait_for_timeout(2000)

            t_ui_total = round(time.perf_counter() - t_send, 3)
            log(f"Luot hoan tat tren UI: {t_ui_total}s (completed={completed})")

            page.wait_for_timeout(3000)
            page.screenshot(path=str(img_answer), full_page=True)
            log(f"Da chup anh giao dien: {img_answer.name} ({img_answer.stat().st_size:,} bytes)")
            browser.close()
    except Exception as exc:
        log(f"[FATAL in Playwright] {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        kill_server(server_proc)
        log("Da tat server Streamlit.")

    # Doc log markers
    markers = parse_turn_markers(SERVER_LOG_PATH, conv_id)
    log(f"Ket qua phan tich markers: {json.dumps({k: v for k, v in markers.items() if k != 'all_turn_lines'}, ensure_ascii=False, indent=2)}")

    # Kiem tra cac dieu kien nghiem thu
    has_micro = bool(markers.get("retrieval_micro"))
    has_timeout = markers.get("has_persist_timeout", False)
    backend = markers.get("backend", "")
    ok = markers.get("ok", False)
    has_draft_fallback = bool(markers.get("draft_fallback"))

    print("\n" + "=" * 80)
    print("KET QUA KIEM TRA DIEU KIEN VE:")
    print(f"1. Co dong RETRIEVAL_MICRO_TIMING cua chinh luot: {has_micro} ({markers.get('retrieval_micro_raw')})")
    print(f"2. KHONG xuat hien bge_worker_persist_timeout: {not has_timeout}")
    print(f"3. Backend thuc thi: {backend} (ok={ok})")
    print(f"4. Co bi roi vao draft fallback khong: {has_draft_fallback}")
    print(f"5. So buoc worker warm loop step: {len(markers.get('warm_loop_steps', []))}")
    print(f"6. Tong thoi gian luot: {markers.get('total_s', t_ui_total)}s")
    print("=" * 80)

    # Luu JSON ket qua
    result_data = {
        "ma_ve": "DESKTOP-SPEED-WORKER-INIT-GUARD-HOME",
        "commit": head_commit,
        "thoi_diem": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "conv_id": conv_id,
        "cau_hoi": question,
        "khoi": "lsu",
        "t_boot_ready_s": t_boot_ready,
        "t_ui_total_s": t_ui_total,
        "markers": {k: v for k, v in markers.items() if k != "all_turn_lines"},
        "dap_an_snippet": ans_text[:300] + "..." if len(ans_text) > 300 else ans_text,
        "tieu_chi_nghiem_thu": {
            "co_dong_retrieval_micro_timing": has_micro,
            "khong_dinh_persist_timeout": not has_timeout,
            "khong_dinh_draft_fallback": not has_draft_fallback,
            "backend_router_ok": (backend == "nakazasen_router" and ok),
        },
    }
    with open(TIMINGS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    log(f"Da ghi file JSON: {TIMINGS_JSON_PATH.name}")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
