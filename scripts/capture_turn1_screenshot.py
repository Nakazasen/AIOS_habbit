"""Chup lai anh man hinh cho Cau 1 tu hoi thoai hoan tat CONV-RAG-NUMPY-KB-QA-1-7AC8BC."""

import os
import sys
import time
import json
import hashlib
import subprocess
import urllib.request
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

PORT = 8538
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
CONV_ID = "CONV-RAG-NUMPY-KB-QA-1-7AC8BC"
NOTEBOOK_ID = "NB-C26E1C84"


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def wait_for_server(port: int, timeout: int = 60) -> bool:
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


def main():
    server_process = None
    if not wait_for_server(PORT, timeout=2):
        print(f"[SERVER] Dang khoi dong Streamlit server tren cong {PORT}...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(APP_DIR / "src") + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
        env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
        env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
        env["AIOS_BGE_INIT_TIMEOUT"] = "420"
        env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
        env["AIOS_FEATURE_CHAT_ACTION"] = "1"
        env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
        env["AIOS_STREAM_SYNTHESIS"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        python_exe = str(APP_DIR / ".venv" / "Scripts" / "python.exe")
        server_process = subprocess.Popen(
            [
                python_exe, "-m", "streamlit", "run",
                "src/aios_habit/workspace_chat_app.py",
                "--server.port", str(PORT),
                "--server.headless", "true",
                "--server.fileWatcherType", "none",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=str(APP_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(PORT, timeout=90):
            print(f"[ERROR] Khong the khoi dong Streamlit server tren cong {PORT}")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print(f"[SERVER] Streamlit server san sang tai {URL}")

    img_path = OUT_DIR / "anh-desktop-rag-numpy-02-lsu.png"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1400})
            page = context.new_page()

            url = f"{URL}/?nb={NOTEBOOK_ID}&conv={CONV_ID}&block=lsu"
            print(f"[PAGE] Dieu huong toi: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            # Thu reload mot lan de dam bao session state dong bo voi conv query param
            page.reload(wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Kiem tra bong bong tin nhan
            chat_messages = page.locator('[data-testid="stChatMessage"]')
            print(f"[UI] So bong bong tin nhan tren UI: {chat_messages.count()}")
            if chat_messages.count() >= 2:
                assistant_bubble = chat_messages.nth(1)
                assistant_bubble.scroll_into_view_if_needed()
                page.evaluate("window.scrollBy(0, -80)")
                page.wait_for_timeout(2000)

            page.screenshot(path=str(img_path), full_page=True)
            print(f"[SCREENSHOT] Da chup lai thanh cong: {img_path.name}")
            browser.close()

    finally:
        if server_process:
            print("[CLEANUP] Tat server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except Exception:
                server_process.kill()

    # Cap nhat JSON tong hop
    out_json = OUT_DIR / "ket-qua-do-desktop-rag-numpy-complete-home.json"
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    img_bytes = img_path.stat().st_size
    img_sha = sha256_file(img_path)

    item_1 = {
        "stt": 1,
        "id": "KB-QA-1",
        "khoi": "Khối LSU",
        "khoi_code": "lsu",
        "cau_hoi": "Ý nghĩa thông số DMT và PMT trong đo kiểm quang học Iris LSU là gì?",
        "baseline_s": 116.69,
        "duration_s": 171.43,
        "log_total_s": 168.22,
        "log_ttft_s": None,
        "backend": "Bản thảo ChatGPT",
        "completed": True,
        "ans_len": 206,
        "ans_preview": "Opcenter App Server là OEXP1VAP, IP 10.170.162.169. Sơ đồ ghi server này chạy Opcenter trên JVM và Windows Server 2019...",
        "badge_info": "",
        "conversation_id": CONV_ID,
        "trace_id": "trc_1bdc55b146f1",
        "img_name": "anh-desktop-rag-numpy-02-lsu.png",
        "img_bytes": img_bytes,
        "img_sha256": img_sha,
    }

    # Cap nhat results[0]
    for idx, r in enumerate(data.get("results", [])):
        if r.get("stt") == 1:
            data["results"][idx] = item_1
            break

    data["results"].sort(key=lambda x: x["stt"])

    # Kiem tra SHA-256 duy nhat
    img_ready_path = OUT_DIR / "anh-desktop-rag-numpy-01-app-ready.png"
    img_shas = {
        img_ready_path.name: sha256_file(img_ready_path)
    }
    for r in data["results"]:
        p = OUT_DIR / r["img_name"]
        img_shas[r["img_name"]] = sha256_file(p)
        r["img_bytes"] = p.stat().st_size
        r["img_sha256"] = img_shas[r["img_name"]]

    sha_values = list(img_shas.values())
    unique_shas = set(sha_values)
    is_sha_unique = len(sha_values) == len(unique_shas)
    data["sha_unique_pass"] = is_sha_unique

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[JSON] Da cap nhat: {out_json}")

    out_jsonl = OUT_DIR / "rows-desktop-rag-numpy-complete-home.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in data["results"]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[JSONL] Da cap nhat: {out_jsonl}")

    print("\n" + "=" * 75)
    print("BANG KIEM TRA ANH NGHIEM THU (SHA-256 UNIQUE GATE)")
    print("=" * 75)
    for name, sha in img_shas.items():
        print(f"  {name:45s} | {sha}")
    print(f"Ket qua kiem dinh trung byte: {'DAT (100% doc nhat)' if is_sha_unique else 'KHONG DAT'}")

    print("\n" + "=" * 75)
    print("BANG TONG HOP SO SANH THOI GIAN GIAO DIEN (SO VOI MOC BASELINE)")
    print("=" * 75)
    print(f"{'STT':<4} | {'ID':<10} | {'Khoi':<20} | {'Moc cu (s)':<12} | {'Do lai (s)':<12} | {'Chenh lech':<15} | {'Trang thai'}")
    print("-" * 85)
    for r in data["results"]:
        diff_s = r["duration_s"] - r["baseline_s"]
        diff_pct = (diff_s / r["baseline_s"]) * 100.0
        diff_str = f"{diff_s:+.2f}s ({diff_pct:+.1f}%)"
        status_str = "HOAN TAT" if r["completed"] else "TREO"
        print(f"{r['stt']:<4} | {r['id']:<10} | {r['khoi']:<20} | {r['baseline_s']:<12.2f} | {r['duration_s']:<12.2f} | {diff_str:<15} | {status_str}")
    print("=" * 85)


if __name__ == "__main__":
    main()
