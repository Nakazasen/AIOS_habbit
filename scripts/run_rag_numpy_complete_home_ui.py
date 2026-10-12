"""Runner thuc thi do luong UI cho ve DESKTOP-RAG-NUMPY-COMPLETE-HOME (Playwright).

Pham vi:
- May nha h410asrock, CPU-only, cau hinh BB-CONFIG-PARITY-01
- Port: 8538
- Kho ma: D:\\Sandbox\\AIOS_habbit (nhanh phieu-viec/rag-fix1)
- Bo 4 cau hoi chuan tu dot quet khoi tri thuc (KB-QA-1, KB-QA-2, KB-QA-3, KB-QA-4)
- Mo hoi thoai trong notebook NB-C26E1C84 (So nghiem thu DESKTOP 2026-10-10)
- Bat co AIOS_RAG_V2_NUMPY_SCORING=1 va AIOS_RAG_V2_NUMPY_DENSE=1
- Chup 5 anh nghiem thu:
  1. anh-desktop-rag-numpy-01-app-ready.png
  2. anh-desktop-rag-numpy-02-lsu.png
  3. anh-desktop-rag-numpy-03-dieu-tra-loi.png
  4. anh-desktop-rag-numpy-04-mom.png
  5. anh-desktop-rag-numpy-05-cau-mo-ho.png
- Kiem tra SHA-256 khong trung byte giua cac anh
- Ghi log server, trace, va xuat ket-qua-do-desktop-rag-numpy-complete-home.json
"""

import os
import sys
import time
import json
import uuid
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

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, load_messages
from playwright.sync_api import sync_playwright

PORT = 8538
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG_PATH = OUT_DIR / "rag_numpy_complete_home_ui.log"
NOTEBOOK_ID = "NB-C26E1C84"

QA_ITEMS = [
    {
        "stt": 1,
        "id": "KB-QA-1",
        "block": "lsu",
        "block_label": "Khối LSU",
        "question": "Ý nghĩa thông số DMT và PMT trong đo kiểm quang học Iris LSU là gì?",
        "baseline_s": 116.69,
        "img_name": "anh-desktop-rag-numpy-02-lsu.png",
    },
    {
        "stt": 2,
        "id": "KB-QA-2",
        "block": "dieu_tra_loi",
        "block_label": "Khối Điều tra lỗi",
        "question": "Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, nguyên nhân và đối sách xử lý ra sao?",
        "baseline_s": 40.56,
        "img_name": "anh-desktop-rag-numpy-03-dieu-tra-loi.png",
    },
    {
        "stt": 3,
        "id": "KB-QA-3",
        "block": "mom",
        "block_label": "Khối MOM",
        "question": "Quy trình xuất kho qua AGV và liên kết với bảng staging oricon trong hệ thống MOM Opcenter như thế nào?",
        "baseline_s": 120.00,
        "img_name": "anh-desktop-rag-numpy-04-mom.png",
    },
    {
        "stt": 4,
        "id": "KB-QA-4",
        "block": "auto",
        "block_label": "Khối Tự động (Mơ hồ)",
        "question": "Làm thế nào để kiểm tra và tối ưu hiệu suất làm việc hàng ngày của thiết bị?",
        "baseline_s": 139.46,
        "img_name": "anh-desktop-rag-numpy-05-cau-mo-ho.png",
    },
]


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_git_head(repo_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


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


def parse_log_markers_for_conv(log_file: Path, conv_id: str) -> dict:
    markers = {
        "start": None,
        "first_token": None,
        "complete": None,
        "ttft_s": None,
        "total_s": None,
        "backend": None,
        "ok": None,
    }
    if not log_file.exists():
        return markers

    try:
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines:
            if conv_id not in line:
                continue
            if "[STREAMING_QA_START]" in line:
                markers["start"] = line.strip()
            elif "[STREAMING_QA_FIRST_TOKEN]" in line:
                markers["first_token"] = line.strip()
                if "ttft_s=" in line:
                    try:
                        part = line.split("ttft_s=")[1].split()[0]
                        markers["ttft_s"] = float(part)
                    except Exception:
                        pass
            elif "[STREAMING_QA_COMPLETE]" in line:
                markers["complete"] = line.strip()
                if "total_s=" in line:
                    try:
                        part = line.split("total_s=")[1].split()[0]
                        markers["total_s"] = float(part)
                    except Exception:
                        pass
                if "backend=" in line:
                    try:
                        backend_part = line.split("backend=")[1].split(" ok=")[0].strip()
                        markers["backend"] = backend_part
                    except Exception:
                        pass
                if "ok=" in line:
                    try:
                        ok_part = line.split("ok=")[1].split()[0].strip()
                        markers["ok"] = ok_part.lower() == "true"
                    except Exception:
                        pass
    except Exception as e:
        print(f"[WARN] Loi doc log markers cho {conv_id}: {e}")

    return markers


def get_trace_for_conv(conv_id: str) -> dict:
    traces_file = APP_DIR / "local_cases" / "workspace_chat" / "traces.jsonl"
    if not traces_file.exists():
        return {}
    try:
        lines = [l for l in traces_file.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
        for l in reversed(lines):
            t = json.loads(l)
            if t.get("conversation_id") == conv_id:
                return t
    except Exception as e:
        print(f"[WARN] Loi doc trace cho {conv_id}: {e}")
    return {}


def run_one_turn(page, conv_id, notebook_id, block_name, question, timeout_s=360):
    url = f"{URL}/?nb={notebook_id}&conv={conv_id}&block={block_name}"
    print(f"\n[PAGE] Dieu huong toi: {url}")
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    # Cho khung soan thao san sang
    page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)

    # Kiem tra toolbar block indicator
    try:
        block_container = page.locator(f'[class*="st-key-wsc-block-{conv_id}"]')
        btn_text = block_container.inner_text() if block_container.count() > 0 else ""
        print(f"[TOOLBAR] Block indicator text: {btn_text.strip()}")
    except Exception as e:
        print(f"[TOOLBAR] Khong doc duoc block text: {e}")

    textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
    textarea.fill(question)
    page.wait_for_timeout(1000)

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button'
    )
    t_start = time.time()
    if send_btn.count() > 0:
        send_btn.first.click()
    else:
        textarea.press("Control+Enter")
    print(f"[SEND] Da gui cau hoi: '{question[:60]}...'")

    # Xac nhan tin nhan nguoi dung da duoc ghi nhan vao database
    for attempt in range(6):
        time.sleep(1.5)
        msgs = load_messages(conv_id)
        if any(m.role == "user" for m in msgs):
            print(f"[SEND] Da xac nhan tin nhan nguoi dung vao he thong (lan {attempt+1})")
            break
        print(f"[SEND] Thu nhan lai Control+Enter (lan {attempt+1})...")
        textarea.press("Control+Enter")
        page.wait_for_timeout(1500)

    # Cho assistant tra loi
    t0 = time.time()
    completed = False
    while time.time() - t0 < timeout_s:
        msgs = load_messages(conv_id)
        if len(msgs) >= 2 and msgs[-1].role == "assistant":
            completed = True
            break
        page.wait_for_timeout(2000)

    duration = time.time() - t_start
    print(f"[REPLY] Luot hoi hoan tat trong {duration:.2f}s (completed={completed})")

    # Cho UI render va reload neu can de hien thi day du bong bong
    page.wait_for_timeout(3000)
    try:
        page.wait_for_selector('[data-testid="stChatMessage"]:nth-of-type(2)', timeout=15000)
    except Exception:
        print("[PAGE] Goi page.reload() de UI cap nhat day du...")
        page.reload(wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

    chat_messages = page.locator('[data-testid="stChatMessage"]')
    print(f"[UI] So bong bong tin nhan tren UI: {chat_messages.count()}")
    if chat_messages.count() >= 2:
        assistant_bubble = chat_messages.nth(1)
        assistant_bubble.scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0, -80)")
        page.wait_for_timeout(2000)

    return duration, completed


def main():
    print("=" * 75)
    print("BAT DAU THUC THI VE DESKTOP-RAG-NUMPY-COMPLETE-HOME (UI PLAYWRIGHT)")
    print("=" * 75)

    head_habbit = get_git_head(APP_DIR)
    head_dieuphoi = get_git_head(Path(r"D:\Sandbox\aios-dieu-phoi"))
    print(f"[GIT] HEAD app (AIOS_habbit): {head_habbit}")
    print(f"[GIT] HEAD dieu phoi: {head_dieuphoi}")

    server_process = None
    server_log_file = None
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

        server_log_file = open(SERVER_LOG_PATH, "w", encoding="utf-8")
        server_log_file.write(f"=== PHIEN CHAY DESKTOP-RAG-NUMPY-COMPLETE-HOME {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n")
        server_log_file.flush()

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
            stdout=server_log_file,
            stderr=subprocess.STDOUT,
        )
        if not wait_for_server(PORT, timeout=90):
            print(f"[ERROR] Khong the khoi dong Streamlit server tren cong {PORT}")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print(f"[SERVER] Streamlit server san sang tai {URL}")
    else:
        print(f"[SERVER] Streamlit server da dang chay tai {URL}")

    only_stt = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    out_json = OUT_DIR / "ket-qua-do-desktop-rag-numpy-complete-home.json"
    existing_results = {}
    if out_json.exists():
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for r in old_data.get("results", []):
                    existing_results[r["stt"]] = r
        except Exception:
            pass

    img_ready_path = OUT_DIR / "anh-desktop-rag-numpy-01-app-ready.png"
    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1400})
            page = context.new_page()

            # 1. Chup anh trang thai khoi dong app-ready (neu chua co hoac khong chay rieng)
            if not only_stt or not img_ready_path.exists():
                print("\n[READY] Chup anh trang thai app ready...")
                init_conv_id = f"CONV-RAG-NUMPY-READY-{uuid.uuid4().hex[:6].upper()}"
                init_c = WorkspaceConversation(
                    id=init_conv_id,
                    notebook_id=NOTEBOOK_ID,
                    title="RAG-NUMPY Khoi dong san sang",
                    ai_mode="grounded",
                )
                save_conversation(init_c)
                page.goto(f"{URL}/?nb={NOTEBOOK_ID}&conv={init_conv_id}&block=lsu", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)
                page.screenshot(path=str(img_ready_path), full_page=True)
                print(f"[READY] Da luu anh app ready: {img_ready_path.name}")

            # 2. Chay 4 cau hoi chuan
            for item in QA_ITEMS:
                stt = item["stt"]
                if only_stt and stt != only_stt:
                    if stt in existing_results:
                        results.append(existing_results[stt])
                    continue
                qid = item["id"]
                block = item["block"]
                block_label = item["block_label"]
                q_text = item["question"]
                baseline_s = item["baseline_s"]
                img_name = item["img_name"]
                img_path = OUT_DIR / img_name

                conv_id = f"CONV-RAG-NUMPY-{qid}-{uuid.uuid4().hex[:6].upper()}"
                c = WorkspaceConversation(
                    id=conv_id,
                    notebook_id=NOTEBOOK_ID,
                    title=f"RAG-NUMPY {qid} {block} {q_text[:30]}",
                    ai_mode="grounded",
                )
                save_conversation(c)

                print("\n" + "=" * 60)
                print(f"THUC HIEN CAU {stt}/4: [{qid}] ({block_label})")
                print(f"Cau hoi: {q_text}")
                print(f"Moc so sanh truoc do: {baseline_s}s")
                print("=" * 60)

                duration, completed = run_one_turn(
                    page, conv_id, NOTEBOOK_ID, block, q_text, timeout_s=360
                )

                # Chup anh hoan tat
                page.screenshot(path=str(img_path), full_page=True)
                print(f"[SCREENSHOT] Da luu anh: {img_name}")

                # Doc tin nhan assistant
                msgs = load_messages(conv_id)
                raw_ans = ""
                for m in msgs:
                    if m.role == "assistant":
                        raw_ans = m.content
                        break

                # Doc trace va markers
                trace = get_trace_for_conv(conv_id)
                trace_id = trace.get("trace_id", "")
                badge_info = trace.get("metadata", {}).get("retrieval_summary", "") if trace else ""
                markers = parse_log_markers_for_conv(SERVER_LOG_PATH, conv_id)

                img_bytes = img_path.stat().st_size
                img_sha = sha256_file(img_path)

                item_res = {
                    "stt": stt,
                    "id": qid,
                    "khoi": block_label,
                    "khoi_code": block,
                    "cau_hoi": q_text,
                    "baseline_s": baseline_s,
                    "duration_s": round(duration, 2),
                    "log_total_s": markers.get("total_s"),
                    "log_ttft_s": markers.get("ttft_s"),
                    "backend": markers.get("backend") or trace.get("ai_backend", "nakazasen_router"),
                    "completed": completed,
                    "ans_len": len(raw_ans),
                    "ans_preview": raw_ans[:120].replace("\n", " "),
                    "badge_info": badge_info,
                    "conversation_id": conv_id,
                    "trace_id": trace_id,
                    "img_name": img_name,
                    "img_bytes": img_bytes,
                    "img_sha256": img_sha,
                }
                results.append(item_res)
                diff_s = duration - baseline_s
                diff_pct = (diff_s / baseline_s) * 100.0
                print(f"[KET QUA CAU {stt}] Thoi gian do: {duration:.2f}s vs Moc: {baseline_s:.2f}s (Chenh lech: {diff_s:+.2f}s / {diff_pct:+.1f}%)")
                print(f"[KET QUA CAU {stt}] Do dai dap an: {len(raw_ans)} ky tu, Hoan tat: {completed}")

            browser.close()

    finally:
        if server_process:
            print("\n[CLEANUP] Dang tat Streamlit server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except Exception:
                server_process.kill()
        if server_log_file:
            server_log_file.close()

    results.sort(key=lambda x: x["stt"])

    # Kiem tra tinh duy nhat cua anh (SHA-256)
    img_shas = {
        img_ready_path.name: sha256_file(img_ready_path)
    }
    for r in results:
        img_shas[r["img_name"]] = r["img_sha256"]

    sha_values = list(img_shas.values())
    unique_shas = set(sha_values)
    is_sha_unique = len(sha_values) == len(unique_shas)

    print("\n" + "=" * 75)
    print("BANG KIEM TRA ANH NGHIEM THU (SHA-256 UNIQUE GATE)")
    print("=" * 75)
    for name, sha in img_shas.items():
        print(f"  {name:45s} | {sha}")
    print(f"Ket qua kiem dinh trung byte: {'DAT (100% doc nhat)' if is_sha_unique else 'KHONG DAT (trung byte)'}")

    # Xuat ket qua
    summary_data = {
        "ma_ve": "DESKTOP-RAG-NUMPY-COMPLETE-HOME",
        "trang_thai": "HOAN_THANH",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "commit_app": head_habbit,
        "commit_dieu_phoi": head_dieuphoi,
        "port": PORT,
        "sha_unique_pass": is_sha_unique,
        "results": results,
    }

    out_json = OUT_DIR / "ket-qua-do-desktop-rag-numpy-complete-home.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"\nDa luu JSON tong hop: {out_json}")

    out_jsonl = OUT_DIR / "rows-desktop-rag-numpy-complete-home.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Da luu JSONL rows: {out_jsonl}")

    print("\n" + "=" * 75)
    print("BANG TONG HOP SO SANH THOI GIAN GIAO DIEN (SO VOI MOC BASELINE)")
    print("=" * 75)
    print(f"{'STT':<4} | {'ID':<10} | {'Khoi':<20} | {'Moc cu (s)':<12} | {'Do lai (s)':<12} | {'Chenh lech':<15} | {'Trang thai'}")
    print("-" * 85)
    for r in results:
        diff_s = r["duration_s"] - r["baseline_s"]
        diff_pct = (diff_s / r["baseline_s"]) * 100.0
        diff_str = f"{diff_s:+.2f}s ({diff_pct:+.1f}%)"
        status_str = "HOAN TAT" if r["completed"] else "TREO"
        print(f"{r['stt']:<4} | {r['id']:<10} | {r['khoi']:<20} | {r['baseline_s']:<12.2f} | {r['duration_s']:<12.2f} | {diff_str:<15} | {status_str}")
    print("=" * 85)


if __name__ == "__main__":
    main()
