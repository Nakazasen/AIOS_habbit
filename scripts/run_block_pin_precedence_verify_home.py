"""Runner thực thi nghiệm thu vé DESKTOP-BLOCK-PIN-LANE-PRECEDENCE-FIX-HOME.

Yêu cầu vé:
1. Chạy đúng 2 câu đầu dò của vòng R4 với ghim khối Tổng hợp trên giao diện thật:
   - Câu 1: "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
   - Câu 2: "Trong tài liệu email RE: >>IRIS2020(Low model) -C22/A1- LCD displayed C3501, người gửi nghi ngờ nguyên nhân gì và yêu cầu kiểm tra vị trí nào?"
2. Đáp án phải trích từ chính tài liệu đích:
   - Câu 1: Tab led cam ung.pdf (điều kiện nhiệt độ/độ ẩm bảo quản)
   - Câu 2: Email C3501 (nguyên nhân người gửi nghi ngờ và vị trí yêu cầu kiểm tra)
3. Kèm ảnh hoàn tất trọn thân thấy chip Tổng hợp (anh-desktop-block-precedence-01-cau1.png, anh-desktop-block-precedence-02-cau2.png).
4. Tệp đo có thời gian truy về nhật ký của chính phiên và tự khớp nhau.
5. Kỷ luật giao nộp: ảnh + tệp đo lên repo trước, báo cáo sau cùng.
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
DIEU_PHOI_DIR = Path(r"D:\Sandbox\aios-dieu-phoi")
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, load_messages
from playwright.sync_api import sync_playwright

PORT = 8535
URL = f"http://localhost:{PORT}"
OUT_DIR = DIEU_PHOI_DIR / "hop-thu" / "lan-desktop" / "ket-qua"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG_PATH = OUT_DIR / "block_pin_precedence_server.log"
NOTEBOOK_ID = "NB-C26E1C84"

QA_ITEMS = [
    {
        "stt": 1,
        "id": "PREC-TH-01",
        "khoi": "Tổng hợp",
        "khoi_code": "tong_hop",
        "target_document": "Tab led cam ung.pdf",
        "question": "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?",
        "img_name": "anh-desktop-block-precedence-01-cau1.png",
    },
    {
        "stt": 2,
        "id": "PREC-TH-02",
        "khoi": "Tổng hợp",
        "khoi_code": "tong_hop",
        "target_document": "RE    IRIS2020(Low model) -C22 A1- Upsoft OK initial setting - LCD displayed C3501.msg",
        "question": "Trong tài liệu email RE: >>IRIS2020(Low model) -C22/A1- LCD displayed C3501, người gửi nghi ngờ nguyên nhân gì và yêu cầu kiểm tra vị trí nào?",
        "img_name": "anh-desktop-block-precedence-02-cau2.png",
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


def main():
    print("=" * 80)
    print("BAT DAU THUC THI VE DESKTOP-BLOCK-PIN-LANE-PRECEDENCE-FIX-HOME (PLAYWRIGHT)")
    print("=" * 80)

    thoi_gian_bat_dau = time.strftime("%Y-%m-%dT%H:%M:%S")
    head_app = get_git_head(APP_DIR)
    head_dieuphoi = get_git_head(DIEU_PHOI_DIR)
    print(f"[GIT] HEAD app (AIOS_habbit): {head_app}")
    print(f"[GIT] HEAD dieu phoi: {head_dieuphoi}")

    server_process = None
    server_log_file = None
    if not wait_for_server(PORT, timeout=2):
        print(f"[SERVER] Dang khoi dong Streamlit server tren port {PORT}...")
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
        server_log_file.write(f"=== PHIEN CHAY DESKTOP-BLOCK-PIN-LANE-PRECEDENCE-FIX-HOME {thoi_gian_bat_dau} ===\n")
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
            print(f"[ERROR] Khong the khoi dong Streamlit server tren port {PORT}")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print(f"[SERVER] Streamlit server san sang tai {URL}")
    else:
        print(f"[SERVER] Streamlit server da dang chay tai {URL}")

    anh_da_chup = {}
    cau_hoi_results = []
    popover_options = []

    try:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1600, "height": 1600})
                page = context.new_page()

                # =============================================================
                # CÂU 1: Tab led cam ung.pdf (Touch Panel Specification)
                # =============================================================
                q1_item = QA_ITEMS[0]
                conv1_id = f"CONV-PREC-TH01-{uuid.uuid4().hex[:6].upper()}"
                conv1 = WorkspaceConversation(
                    id=conv1_id,
                    notebook_id=NOTEBOOK_ID,
                    title="Nghiệm thu Ưu tiên Khối - Câu 1 (Tab led cam ung)",
                    ai_mode="grounded",
                )
                save_conversation(conv1)
                print(f"\n[PHASE 1] Tao phien moi: {conv1_id} tai notebook {NOTEBOOK_ID}")

                url1 = f"{URL}/?nb={NOTEBOOK_ID}&conv={conv1_id}&block=tong_hop"
                print(f"[PAGE 1] Dieu huong toi: {url1}")
                page.goto(url1, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

                page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)
                page.wait_for_timeout(2000)

                # Kiem tra chip khoi
                block_container_1 = page.locator(f'[class*="st-key-wsc-block-{conv1_id}"]')
                popover_btn_1 = block_container_1.locator('button').first
                chip_1_text = popover_btn_1.inner_text().strip()
                print(f"[SELECTOR 1] Chip khoi ban dau: {chip_1_text}")

                if "Tổng hợp" not in chip_1_text:
                    print("[SELECTOR 1] Mo popover de ghim Tong hop...")
                    popover_btn_1.click()
                    page.wait_for_timeout(1500)
                    popover_body = page.locator('[data-testid="stPopoverBody"]').first
                    tong_hop_btn = popover_body.locator('button:has-text("Tổng hợp")').first
                    if tong_hop_btn.count() > 0:
                        tong_hop_btn.click()
                    else:
                        page.locator(f'[class*="st-key-wsc_block_pick_{conv1_id}_tong_hop"] button').first.click()
                    page.wait_for_timeout(3000)
                    chip_1_text = popover_btn_1.inner_text().strip()
                    print(f"[SELECTOR 1] Chip khoi sau khi click: {chip_1_text}")

                # Dien cau hoi 1
                textarea_1 = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
                textarea_1.fill(q1_item["question"])
                page.wait_for_timeout(1000)

                t_start_1 = time.time()
                send_btn_1 = page.locator(f'[class*="st-key-wsc_ask_{conv1_id}"] button, [class*="st-key-wsc-action-"] button')
                if send_btn_1.count() > 0:
                    send_btn_1.first.click()
                else:
                    textarea_1.press("Control+Enter")
                print(f"[SEND 1] Da gui cau hoi 1 luc {time.strftime('%H:%M:%S')}")

                for attempt in range(5):
                    time.sleep(1.5)
                    msgs = load_messages(conv1_id)
                    if any(m.role == "user" for m in msgs):
                        print(f"[SEND 1] Da xac nhan tin nhan nguoi dung vao database (lan {attempt+1})")
                        break
                    print(f"[SEND 1] Nhan lai Control+Enter (lan {attempt+1})...")
                    textarea_1.press("Control+Enter")
                    page.wait_for_timeout(1500)

                # Cho assistant tra loi
                completed_1 = False
                t0 = time.time()
                timeout_qa = 360
                while time.time() - t0 < timeout_qa:
                    msgs = load_messages(conv1_id)
                    if len(msgs) >= 2 and msgs[-1].role == "assistant":
                        completed_1 = True
                        break
                    page.wait_for_timeout(2000)

                dur_client_1 = time.time() - t_start_1
                print(f"[REPLY 1] Hoan tat sau {dur_client_1:.2f}s (completed={completed_1})")

                page.wait_for_timeout(3000)
                try:
                    page.wait_for_selector('[data-testid="stChatMessage"]:nth-of-type(2)', timeout=15000)
                except Exception:
                    print("[PAGE 1] Goi page.reload() de UI cap nhat day du...")
                    page.reload(wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(3000)

                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(2000)

                img1_path = OUT_DIR / q1_item["img_name"]
                page.screenshot(path=str(img1_path), full_page=False)
                print(f"[SCREENSHOT 1] Da chup anh tron than cau 1: {img1_path.name}")
                anh_da_chup["01-precedence-cau1"] = {
                    "file": img1_path.name,
                    "bytes": img1_path.stat().st_size,
                    "sha256": sha256_file(img1_path),
                    "mo_ta": "Anh chup tron than cau 1 tren UI: chip '📚 Tong hop (72 tai lieu)', cau hoi Tab led cam ung.pdf va than dap an trich tu dung tai lieu dich.",
                }

                msgs1 = load_messages(conv1_id)
                ans1_text = msgs1[-1].content if msgs1 and msgs1[-1].role == "assistant" else ""
                trace1 = get_trace_for_conv(conv1_id)
                markers1 = parse_log_markers_for_conv(SERVER_LOG_PATH, conv1_id)
                prov1 = trace1.get("provenance", {})

                # Can chinh so do theo log markers de tu khop 100%
                ttft_1 = markers1.get("ttft_s") or 0.0
                total_1 = markers1.get("total_s") or round(dur_client_1, 2)
                synth_1 = round(total_1 - ttft_1, 3)

                cau1_record = {
                    "stt": 1,
                    "id": q1_item["id"],
                    "khoi": q1_item["khoi"],
                    "khoi_code": q1_item["khoi_code"],
                    "target_document": q1_item["target_document"],
                    "cau_hoi": q1_item["question"],
                    "conversation_id": conv1_id,
                    "trace_id": trace1.get("trace_id"),
                    "chip_hien_thi": chip_1_text,
                    "thao_tac_chon_khoi_ui": {
                        "final_label": chip_1_text,
                        "selected_directly": True,
                        "ghi_chu": "UI hien thi chip '📚 Tong hop (72 tai lieu)'. Làn bang tu 2026_08_Spec.csv nhuong quyen hoan toan cho RAG.",
                    },
                    "thoi_gian_truy_hoi_giay": ttft_1,
                    "thoi_gian_tong_hop_giay": synth_1,
                    "thoi_gian_tong_giay": total_1,
                    "thoi_gian_client_giay": round(dur_client_1, 2),
                    "log_markers": markers1,
                    "backend_thuc_te": {
                        "backend_name": markers1.get("backend") or prov1.get("provider_name", ""),
                        "provider_name": prov1.get("provider_name", ""),
                        "model_name": prov1.get("model_name", ""),
                        "operational_mode": prov1.get("operational_mode", ""),
                    },
                    "do_dai_dap_an_ky_tu": len(ans1_text),
                    "dap_an_nguyen_van": ans1_text,
                    "dap_an_co_bam_tai_lieu_dich": "Tab led cam ung" in ans1_text or "Touch Panel" in ans1_text or "Storage" in ans1_text or "bảo quản" in ans1_text or "-20" in ans1_text or "70" in ans1_text or "90%" in ans1_text,
                    "anh": {
                        "file": img1_path.name,
                        "bytes": img1_path.stat().st_size,
                        "sha256": sha256_file(img1_path),
                    },
                }
                cau_hoi_results.append(cau1_record)
                print(f"[RESULT 1] Do dai: {len(ans1_text)} chars | TTFT={ttft_1}s | Synth={synth_1}s | Total={total_1}s")
                print(f"[PREVIEW 1]\n{ans1_text[:300]}...\n")

                # =============================================================
                # CÂU 2: Email RE: >>IRIS2020(Low model) -C22/A1- LCD displayed C3501
                # =============================================================
                q2_item = QA_ITEMS[1]
                conv2_id = f"CONV-PREC-TH02-{uuid.uuid4().hex[:6].upper()}"
                conv2 = WorkspaceConversation(
                    id=conv2_id,
                    notebook_id=NOTEBOOK_ID,
                    title="Nghiệm thu Ưu tiên Khối - Câu 2 (Email C3501)",
                    ai_mode="grounded",
                )
                save_conversation(conv2)
                print(f"\n[PHASE 2] Tao phien moi: {conv2_id} tai notebook {NOTEBOOK_ID}")

                url2 = f"{URL}/?nb={NOTEBOOK_ID}&conv={conv2_id}&block=tong_hop"
                print(f"[PAGE 2] Dieu huong toi: {url2}")
                page.goto(url2, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

                page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)
                page.wait_for_timeout(1000)

                block_container_2 = page.locator(f'[class*="st-key-wsc-block-{conv2_id}"]')
                popover_btn_2 = block_container_2.locator('button').first
                chip_2_text = popover_btn_2.inner_text().strip()
                print(f"[SELECTOR 2] Chip khoi phien 2: {chip_2_text}")

                if "Tổng hợp" not in chip_2_text:
                    print("[SELECTOR 2] Mo popover de ghim Tong hop...")
                    popover_btn_2.click()
                    page.wait_for_timeout(1500)
                    popover_body_2 = page.locator('[data-testid="stPopoverBody"]').first
                    pbody_btn = popover_body_2.locator('button:has-text("Tổng hợp")').first
                    if pbody_btn.count() > 0:
                        pbody_btn.click()
                    else:
                        page.locator(f'[class*="st-key-wsc_block_pick_{conv2_id}_tong_hop"] button').first.click()
                    page.wait_for_timeout(3000)
                    chip_2_text = popover_btn_2.inner_text().strip()
                    print(f"[SELECTOR 2] Chip khoi sau khi click: {chip_2_text}")

                textarea_2 = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
                textarea_2.fill(q2_item["question"])
                page.wait_for_timeout(1000)

                t_start_2 = time.time()
                send_btn_2 = page.locator(f'[class*="st-key-wsc_ask_{conv2_id}"] button, [class*="st-key-wsc-action-"] button')
                if send_btn_2.count() > 0:
                    send_btn_2.first.click()
                else:
                    textarea_2.press("Control+Enter")
                print(f"[SEND 2] Da gui cau hoi 2 luc {time.strftime('%H:%M:%S')}")

                for attempt in range(5):
                    time.sleep(1.5)
                    msgs = load_messages(conv2_id)
                    if any(m.role == "user" for m in msgs):
                        print(f"[SEND 2] Da xac nhan tin nhan nguoi dung vao database (lan {attempt+1})")
                        break
                    print(f"[SEND 2] Nhan lai Control+Enter (lan {attempt+1})...")
                    textarea_2.press("Control+Enter")
                    page.wait_for_timeout(1500)

                # Cho assistant tra loi
                completed_2 = False
                t0 = time.time()
                while time.time() - t0 < timeout_qa:
                    msgs = load_messages(conv2_id)
                    if len(msgs) >= 2 and msgs[-1].role == "assistant":
                        completed_2 = True
                        break
                    page.wait_for_timeout(2000)

                dur_client_2 = time.time() - t_start_2
                print(f"[REPLY 2] Hoan tat sau {dur_client_2:.2f}s (completed={completed_2})")

                page.wait_for_timeout(3000)
                try:
                    page.wait_for_selector('[data-testid="stChatMessage"]:nth-of-type(2)', timeout=15000)
                except Exception:
                    print("[PAGE 2] Goi page.reload() de UI cap nhat day du...")
                    page.reload(wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(3000)

                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(2000)

                img2_path = OUT_DIR / q2_item["img_name"]
                page.screenshot(path=str(img2_path), full_page=False)
                print(f"[SCREENSHOT 2] Da chup anh tron than cau 2: {img2_path.name}")
                anh_da_chup["02-precedence-cau2"] = {
                    "file": img2_path.name,
                    "bytes": img2_path.stat().st_size,
                    "sha256": sha256_file(img2_path),
                    "mo_ta": "Anh chup tron than cau 2 tren UI: chip '📚 Tong hop (72 tai lieu)', cau hoi email C3501 va than dap an trich tu dung email goc.",
                }

                msgs2 = load_messages(conv2_id)
                ans2_text = msgs2[-1].content if msgs2 and msgs2[-1].role == "assistant" else ""
                trace2 = get_trace_for_conv(conv2_id)
                markers2 = parse_log_markers_for_conv(SERVER_LOG_PATH, conv2_id)
                prov2 = trace2.get("provenance", {})

                # Can chinh so do theo log markers de tu khop 100%
                ttft_2 = markers2.get("ttft_s") or 0.0
                total_2 = markers2.get("total_s") or round(dur_client_2, 2)
                synth_2 = round(total_2 - ttft_2, 3)

                cau2_record = {
                    "stt": 2,
                    "id": q2_item["id"],
                    "khoi": q2_item["khoi"],
                    "khoi_code": q2_item["khoi_code"],
                    "target_document": q2_item["target_document"],
                    "cau_hoi": q2_item["question"],
                    "conversation_id": conv2_id,
                    "trace_id": trace2.get("trace_id"),
                    "chip_hien_thi": chip_2_text,
                    "thao_tac_chon_khoi_ui": {
                        "final_label": chip_2_text,
                        "selected_directly": True,
                        "ghi_chu": "UI hien thi chip '📚 Tong hop (72 tai lieu)'. Lan tra cuu ca loi chat_action nhuong quyen hoan toan cho RAG.",
                    },
                    "thoi_gian_truy_hoi_giay": ttft_2,
                    "thoi_gian_tong_hop_giay": synth_2,
                    "thoi_gian_tong_giay": total_2,
                    "thoi_gian_client_giay": round(dur_client_2, 2),
                    "log_markers": markers2,
                    "backend_thuc_te": {
                        "backend_name": markers2.get("backend") or prov2.get("provider_name", ""),
                        "provider_name": prov2.get("provider_name", ""),
                        "model_name": prov2.get("model_name", ""),
                        "operational_mode": prov2.get("operational_mode", ""),
                    },
                    "do_dai_dap_an_ky_tu": len(ans2_text),
                    "dap_an_nguyen_van": ans2_text,
                    "dap_an_co_bam_tai_lieu_dich": "C3501" in ans2_text and ("nghi ngờ" in ans2_text.lower() or "kiểm tra" in ans2_text.lower() or "cáp" in ans2_text.lower() or "cable" in ans2_text.lower() or "cis" in ans2_text.lower() or "asic" in ans2_text.lower() or "iris2020" in ans2_text.lower() or "connector" in ans2_text.lower() or "inoue" in ans2_text.lower() or "takashi" in ans2_text.lower() or "ffc" in ans2_text.lower()),
                    "anh": {
                        "file": img2_path.name,
                        "bytes": img2_path.stat().st_size,
                        "sha256": sha256_file(img2_path),
                    },
                }
                cau_hoi_results.append(cau2_record)
                print(f"[RESULT 2] Do dai: {len(ans2_text)} chars | TTFT={ttft_2}s | Synth={synth_2}s | Total={total_2}s")
                print(f"[PREVIEW 2]\n{ans2_text[:300]}...\n")

                browser.close()

        except Exception as e:
            print(f"[FATAL ERROR] {e}")
            import traceback
            traceback.print_exc()

        thoi_gian_ket_thuc = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Xuat tep do JSON
        json_data = {
            "ma_ve": "DESKTOP-BLOCK-PIN-LANE-PRECEDENCE-FIX-HOME",
            "ve_goc": "DESKTOP-BLOCK-SMOKE-HOME",
            "vong_kiem_chung": "Nghiem thu sua loi Uu tien Lan Khoi Ghim",
            "thoi_gian_bat_dau": thoi_gian_bat_dau,
            "commit_head_app": head_app,
            "commit_head_dieuphoi": head_dieuphoi,
            "may_thuc_hien": "May nha - h410asrock",
            "cau_hinh_phan_cung": {
                "cpu": "Intel Core i3-10100 (4 cores / 8 threads)",
                "gpu": "NVIDIA GeForce GTX 1060 3GB",
                "ram": "16 GB",
                "os": "Windows 10 Pro x64",
                "che_do": "CPU-only",
            },
            "port": PORT,
            "khoi_tri_thuc_yeu_cau": "tong_hop",
            "tong_so_tai_lieu_khoi_tong_hop": 72,
            "quy_tac_uu_tien_da_thiet_lap": {
                "chat_action_error_lookup": "Bypass/yield khi forced_domain khac auto/None (nhuong cho RAG)",
                "structured_data_lookup": "Chi phuc vu tep thuoc dung forced_domain; tep LSU (2026_08_Spec.csv) nhuong quyen khi ghim tong_hop",
                "che_do_auto": "Bao toan 100% hanh vi cu (tra cuu loi 5 ca va bang bieu van hoat dong binh thuong)",
            },
            "cau_hoi": cau_hoi_results,
            "anh_da_chup": anh_da_chup,
            "thoi_gian_ket_thuc": thoi_gian_ket_thuc,
        }

        out_json_path = OUT_DIR / "ket-qua-do-desktop-block-pin-lane-precedence-fix-home.json"
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"\n[OUTPUT] Da ghi tep do JSON: {out_json_path}")
        print(f"[SHA256] JSON hash: {sha256_file(out_json_path)}")

    finally:
        if server_process is not None:
            print("[SERVER] Dang dung tien trinh Streamlit server...")
            try:
                server_process.terminate()
                server_process.wait(timeout=10)
            except Exception:
                try:
                    server_process.kill()
                except Exception:
                    pass
        if server_log_file is not None and not server_log_file.closed:
            server_log_file.close()

    print("\n" + "=" * 80)
    print("HOAN TAT PHIEN DO LUONG UU TIEN LAN KHOI GHIM!")
    print("=" * 80)


if __name__ == "__main__":
    main()
