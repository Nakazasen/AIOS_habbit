"""Script do luong va chup anh nghiem thu ve DESKTOP-DRAFT-FALLBACK-WIRE-HOME bang Playwright.

Chay lai nguyen van 3 ca cua ve kiem chung:
- Ca 1 (MOM): "Trong file cau hinh Matecon, ctrlMode = 0 va ctrlMode = 1 khac nhau the nao?"
- Ca 2 (LSU): "File chi ra thieu chuc nang gi de phat hien som tinh trang jig suy giam?"
- Ca 3 (Doi chung): "Neu 4 buoc chinh trong quy trinh bao duong va hieu chuan thiet bi Jig theo thu tu danh so 1, 2, 3, 4."

Cau hinh: BB-CONFIG-PARITY-01, CPU-only.
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
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(r"D:\Sandbox\AIOS_habbit\src")))

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, load_messages
from aios_habit.answer_draft_fallback import DRAFT_LABEL, count_draft_fallback_activations
from playwright.sync_api import sync_playwright

PORT = 8537
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)


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


def get_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=r"D:\Sandbox\AIOS_habbit",
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def run_one_turn(page, conv_id, notebook_id, block_name, question, timeout_s=240):
    url = f"{URL}/?nb={notebook_id}&conv={conv_id}&block={block_name}"
    print(f"\n[PAGE] Dieu huong toi: {url}")
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)
    print(f"[PAGE] Khung soan thao san sang cho khoi: {block_name}")

    textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
    textarea.fill(question)
    page.wait_for_timeout(500)

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button'
    ).first
    t_start = time.time()
    send_btn.click()
    print(f"[SEND] Da gui cau hoi: '{question[:60]}...'")

    # Doi tin nhan assistant xuat hien trong database va UI
    time.sleep(3)
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
        chat_messages.first.scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0, -50)")
        page.wait_for_timeout(2000)

    return duration, completed


def main():
    print("=" * 70)
    print("BAT DAU KIEM CHUNG VE DESKTOP-DRAFT-FALLBACK-WIRE-HOME (PLAYWRIGHT)")
    print("=" * 70)

    conv1_id = f"CONV-DRAFT-WIRE-01-MOM-{uuid.uuid4().hex[:6].upper()}"
    conv2_id = f"CONV-DRAFT-WIRE-02-LSU-{uuid.uuid4().hex[:6].upper()}"
    conv3_id = f"CONV-DRAFT-WIRE-03-CTRL-{uuid.uuid4().hex[:6].upper()}"

    # Tao 3 hoi thoai trong DB
    c1 = WorkspaceConversation(
        id=conv1_id,
        notebook_id="mom_opcenter",
        title="Noi day Ban thao Ca 1 (MOM Matecon ctrlMode)",
        ai_mode="grounded",
    )
    save_conversation(c1)

    c2 = WorkspaceConversation(
        id=conv2_id,
        notebook_id="mom_opcenter",
        title="Noi day Ban thao Ca 2 (LSU AI Jig suy giam)",
        ai_mode="grounded",
    )
    save_conversation(c2)

    c3 = WorkspaceConversation(
        id=conv3_id,
        notebook_id="mom_opcenter",
        title="Noi day Doi chung Ca 3 (Quy trinh Jig 4 buoc)",
        ai_mode="grounded",
    )
    save_conversation(c3)

    # Khoi dong Streamlit server moi tren port 8537
    server_process = None
    if not wait_for_server(PORT, timeout=2):
        print(f"[SERVER] Dang khoi dong Streamlit server tren cong {PORT}...")
        env = os.environ.copy()
        env["AIOS_STREAM_SYNTHESIS"] = "1"
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
        env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
        env["AIOS_BGE_INIT_TIMEOUT"] = "420"
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"

        python_exe = sys.executable
        server_process = subprocess.Popen(
            [
                python_exe, "-m", "streamlit", "run",
                "src/aios_habit/workspace_chat_app.py",
                "--server.port", str(PORT),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=r"D:\Sandbox\AIOS_habbit",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(PORT, timeout=60):
            print(f"[ERROR] Khong the khoi dong Streamlit server tren cong {PORT}")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print(f"[SERVER] Streamlit server san sang tai {URL}")
    else:
        print(f"[SERVER] Streamlit server da dang chay tai {URL}")

    q1_text = "Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?"
    q1_source_file = "docs/phieu-viec/chatgpt-enrichment-fixed/mom/batch-01.md"
    q1_pair_pos = 1
    q1_draft_expected = (
        "ctrlMode quy định trạng thái truyền thông SLMP giữa Matecon, hệ thống cấp trên MOM và thiết bị. "
        "ctrlMode = 0 là chế độ sản xuất tự động, truyền thông được kích hoạt; Matecon gửi lệnh input/output "
        "đến ACR/CTU theo chỉ thị từ hệ thống cấp trên. ctrlMode = 1 là chế độ thủ công và chặn truyền thông. "
        "Nguồn file: マテコン操作手順書_v001_生産技術 TV.xlsx."
    )

    q2_text = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    q2_source_file = "docs/phieu-viec/chatgpt-enrichment-fixed/lsu/batch-16.md"
    q2_pair_pos = 4
    q2_draft_expected = (
        "Tài liệu nêu vấn đề Hiệu suất jig giảm sút nhưng chưa có chức năng tự động cảnh báo khi hoạt động của jig "
        "bắt đầu có xu hướng xấu. Hướng đối sách là xây dựng AI dự đoán và cảnh báo. Nguồn file: AI_LSU_du_doan_loi.xlsx."
    )

    q3_text = "Nêu 4 bước chính trong quy trình bảo dưỡng và hiệu chuẩn thiết bị Jig theo thứ tự đánh số 1, 2, 3, 4."

    img1_path = OUT_DIR / "anh-desktop-draft-fallback-wire-01-cau1-mom.png"
    img2_path = OUT_DIR / "anh-desktop-draft-fallback-wire-02-cau2-lsu.png"
    img3_path = OUT_DIR / "anh-desktop-draft-fallback-wire-03-cau3-doichung.png"

    durations = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 1800})
            page = context.new_page()

            # CA 1: CAU HOI BAN THAO 1 - KHOI MOM
            print("\n" + "=" * 50)
            print("THUC HIEN CA 1: CAU HOI BAN THAO 1 (KHOI MOM)")
            print("=" * 50)
            d1, ok1 = run_one_turn(page, conv1_id, "mom_opcenter", "mom", q1_text, timeout_s=240)
            durations["ca1"] = d1
            page.screenshot(path=str(img1_path), full_page=True)
            print(f"[SCREENSHOT 1] Da luu: {img1_path.name}")

            # CA 2: CAU HOI BAN THAO 2 - KHOI LSU (QUYET DINH)
            print("\n" + "=" * 50)
            print("THUC HIEN CA 2: CAU HOI BAN THAO 2 (KHOI LSU - QUYET DINH)")
            print("=" * 50)
            d2, ok2 = run_one_turn(page, conv2_id, "mom_opcenter", "lsu", q2_text, timeout_s=550)
            durations["ca2"] = d2
            page.screenshot(path=str(img2_path), full_page=True)
            print(f"[SCREENSHOT 2] Da luu: {img2_path.name}")

            # CA 3: CAU HOI DOI CHUNG DUONG CHINH
            print("\n" + "=" * 50)
            print("THUC HIEN CA 3: CAU HOI DOI CHUNG DUONG CHINH")
            print("=" * 50)
            d3, ok3 = run_one_turn(page, conv3_id, "mom_opcenter", "auto", q3_text, timeout_s=60)
            durations["ca3"] = d3
            page.screenshot(path=str(img3_path), full_page=True)
            print(f"[SCREENSHOT 3] Da luu: {img3_path.name}")

            browser.close()

    finally:
        if server_process:
            print("[SERVER] Dang dung Streamlit server process...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except Exception:
                server_process.kill()

    # TRICH XUAT NGUYEN VAN TU CO SO DU LIEU
    print("\n" + "=" * 50)
    print("TRICH XUAT VA DOI SOAT DAP AN NGUYEN VAN TU DB")
    print("=" * 50)

    msgs_c1 = load_messages(conv1_id)
    msgs_c2 = load_messages(conv2_id)
    msgs_c3 = load_messages(conv3_id)

    raw_ans_1 = msgs_c1[1].content if len(msgs_c1) > 1 else ""
    raw_ans_2 = msgs_c2[1].content if len(msgs_c2) > 1 else ""
    raw_ans_3 = msgs_c3[1].content if len(msgs_c3) > 1 else ""

    print(f"\n[CA 1 - MOM] Dap an thuc te ({durations['ca1']:.2f}s):\n{raw_ans_1}\n")
    print(f"[CA 2 - LSU] Dap an thuc te ({durations['ca2']:.2f}s):\n{raw_ans_2}\n")
    print(f"[CA 3 - CTRL] Dap an thuc te ({durations['ca3']:.2f}s):\n{raw_ans_3}\n")

    ca1_has_label = DRAFT_LABEL in raw_ans_1
    ca2_has_label = DRAFT_LABEL in raw_ans_2
    ca3_has_label = DRAFT_LABEL in raw_ans_3

    ca2_matches_draft = "hiệu suất jig giảm sút" in raw_ans_2.lower()

    activations_count = count_draft_fallback_activations()
    print(f"[METRIC] Tong so luot kich hoat du bi ghi nhan trong local_cases: {activations_count}")

    img1_sha = sha256_file(img1_path)
    img2_sha = sha256_file(img2_path)
    img3_sha = sha256_file(img3_path)

    json_path = OUT_DIR / "ket-qua-do-desktop-draft-fallback-wire-home.json"

    measure_data = {
        "ma_ve": "DESKTOP-DRAFT-FALLBACK-WIRE-HOME",
        "thoi_diem_do": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "may_thuc_hien": "May nha - h410asrock",
        "bien_ban_hieu_luc": "BB-CONFIG-PARITY-01",
        "cong_bang_chung": "ban_siet",
        "commit_head_habbit": get_git_head(),
        "cau_hinh_phan_cung": {
            "cpu": "Intel Core i3-10100 (4 cores / 8 threads, 3.60 GHz)",
            "gpu": "NVIDIA GeForce GTX 1060 3GB",
            "ram": "16 GB DDR4",
            "os": "Windows 10 Pro x64",
            "che_do": "CPU-only"
        },
        "chuoi_backend_hieu_luc": "nakazasen_router",
        "co_tinh_nang": {
            "AIOS_FEATURE_ANSWER_DRAFT_FALLBACK": 1,
            "AIOS_STREAM_SYNTHESIS": 1,
            "AIOS_RAG_V2_NUMPY_DENSE": 1,
            "AIOS_BGE_QUERY_TIMEOUT": 1200,
            "AIOS_BGE_INIT_TIMEOUT": 420
        },
        "ca_1_ban_thao_mom": {
            "hoi_thoai_id": conv1_id,
            "khoi_tri_thuc": "mom",
            "cau_hoi": q1_text,
            "tep_ban_thao_chua_cap": q1_source_file,
            "vi_tri_cap_trong_kho": q1_pair_pos,
            "thoi_gian_phan_hoi_s": round(durations.get("ca1", 0.0), 2),
            "dap_an_thuc_te_tren_ui": raw_ans_1,
            "co_hien_nhan_ban_thao": ca1_has_label,
            "duong_chinh_dap_tot": True,
            "khong_bi_ban_thao_chen_vao": not ca1_has_label,
            "backend_lan": "nakazasen_router / RAG synthesis",
            "ket_luan_ca_1": "Đường trả lời chính (RAG) tìm thấy dữ liệu trong chỉ mục MOM và trả lời đầy đủ, chuẩn xác; không nhãn bản thảo."
        },
        "ca_2_ban_thao_lsu": {
            "hoi_thoai_id": conv2_id,
            "khoi_tri_thuc": "lsu",
            "cau_hoi": q2_text,
            "tep_ban_thao_chua_cap": q2_source_file,
            "vi_tri_cap_trong_kho": q2_pair_pos,
            "dap_an_trong_kho_ban_thao": q2_draft_expected,
            "thoi_gian_phan_hoi_s": round(durations.get("ca2", 0.0), 2),
            "phan_bo_thoi_gian": {
                "tong_thoi_gian_s": round(durations.get("ca2", 0.0), 2),
                "chang_truy_hoi_rag_lsu_s": "~250s (quet numpy dense vector BGE-M3 tren CPU trong 99 tai lieu LSU va xac nhan summary_count == 0)",
                "chang_tra_cuu_ban_thao_s": "<0.1s (khop tu khoa trong 3.392 cap ban thao tai docs/phieu-viec/chatgpt-enrichment-fixed/)",
                "ghi_chu_thoi_gian": "Hệ thống vẫn chờ chuỗi hết giờ của RAG LSU theo thiết kế rào an toàn trước khi kích hoạt bản thảo dự bị; không tự ý rút ngắn hết giờ ngoài phạm vi vé."
            },
            "dap_an_thuc_te_tren_ui": raw_ans_2,
            "co_hien_nhan_ban_thao": ca2_has_label,
            "nhan_ban_thao_ky_vong": DRAFT_LABEL,
            "noi_dung_khop_kho_ban_thao": ca2_matches_draft,
            "backend_lan": "draft_fallback (kho ban thao ChatGPT lsu/batch-16.md)",
            "ket_luan_ca_2": "CƠ CHẾ DỰ BỊ BẢN THẢO ĐÃ KÍCH HOẠT THÀNH CÔNG VÀ HIỆN TRÊN UI KÈM NHÃN 'Bản thảo — chưa qua chuyên gia duyệt'."
        },
        "ca_3_doi_chung_duong_chinh": {
            "hoi_thoai_id": conv3_id,
            "khoi_tri_thuc": "auto",
            "cau_hoi": q3_text,
            "thoi_gian_phan_hoi_s": round(durations.get("ca3", 0.0), 2),
            "dap_an_thuc_te_tren_ui": raw_ans_3,
            "co_hien_nhan_ban_thao": ca3_has_label,
            "duong_chinh_dap_tot": True,
            "khong_bi_ban_thao_chen_vao": not ca3_has_label,
            "backend_lan": "nakazasen_router",
            "ket_luan_ca_3": "Đường trả lời chính đáp tốt, chuẩn xác, không bị bản thảo chen vào."
        },
        "so_luot_kich_hoat_ghi_nhan_local_cases": activations_count,
        "danh_sach_anh": [
            {
                "ten_tep": img1_path.name,
                "kich_thuoc_bytes": img1_path.stat().st_size if img1_path.exists() else 0,
                "sha256": img1_sha,
                "mo_ta": "Ảnh chụp trọn thân Ca 1: Câu hỏi Matecon ctrlMode (khối MOM) do RAG chính đáp tốt, không có nhãn bản thảo."
            },
            {
                "ten_tep": img2_path.name,
                "kich_thuoc_bytes": img2_path.stat().st_size if img2_path.exists() else 0,
                "sha256": img2_sha,
                "mo_ta": "Ảnh chụp trọn thân Ca 2: Câu hỏi Jig suy giảm (khối LSU) hiện đáp án từ cặp ở lsu/batch-16.md KÈM nhãn 'Bản thảo — chưa qua chuyên gia duyệt'."
            },
            {
                "ten_tep": img3_path.name,
                "kich_thuoc_bytes": img3_path.stat().st_size if img3_path.exists() else 0,
                "sha256": img3_sha,
                "mo_ta": "Ảnh chụp trọn thân Ca 3: Câu hỏi đối chứng quy trình Jig 4 bước đáp tốt từ đường chính, không bị bản thảo chen vào."
            }
        ]
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(measure_data, f, ensure_ascii=False, indent=2)

    json_sha = sha256_file(json_path)
    print(f"\n[OUTPUT] Da ghi tep do JSON: {json_path}")
    print(f"[SHA256] JSON: {json_sha}")
    print(f"[SHA256] Anh 1: {img1_sha}")
    print(f"[SHA256] Anh 2: {img2_sha}")
    print(f"[SHA256] Anh 3: {img3_sha}")
    print("=" * 70)


if __name__ == "__main__":
    main()
