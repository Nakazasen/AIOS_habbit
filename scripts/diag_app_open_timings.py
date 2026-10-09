"""Script chẩn đoán và đo phân rã đường mở sổ trong Workspace Chat (APP-OPEN-DIAG-PC0575).

Đo đạc chính xác thời gian từng khâu khi người dùng bấm vào sổ:
1. Tải / khởi tạo trang
2. Đọc metadata sổ
3. Liệt kê cuộc trò chuyện
4. Truy vấn cơ sở dữ liệu hội thoại
5. Chuẩn bị / phạm vi nguồn
6. Nạp mô hình / worker nền
7. Dòng trạng thái kho & kiểm tra vân tay chỉ mục (tách nhỏ: connect, count chunks, count docs, compute fingerprint)
8. Các khâu khác và tổng thời gian toàn trình
"""

import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Dict, List, Tuple


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

LOG_FILE = REPO_ROOT / "docs" / "phieu-viec" / "ket-qua" / "app-open-diag-pc0575-raw.log"
RESULTS_JSON = REPO_ROOT / "docs" / "phieu-viec" / "ket-qua" / "app-open-diag-pc0575-timings.json"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_step(msg: str) -> None:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{now_str}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        print(line.encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def profile_single_notebook_open(notebook_id: str, is_cold: bool, step_name: str) -> Dict[str, Any]:
    """Đo phân rã chi tiết từng khâu khi mở một sổ cụ thể."""
    log_step(f"=== BẮT ĐẦU ĐO: {step_name} (Sổ: {notebook_id}, Lạnh: {is_cold}) ===")
    timings: Dict[str, float] = {}
    details: Dict[str, Any] = {}
    t_start_total = time.perf_counter()

    # Khâu 1: Tải / Khởi tạo trang & imports cốt lõi
    t0 = time.perf_counter()
    from aios_habit.workspace_chat_models import (
        DEFAULT_COLLECTION_ID,
        ChatMessage,
        WorkspaceConversation,
        DocumentNotebook,
    )
    from aios_habit.workspace_chat_store import (
        load_active_notebooks,
        load_collections,
        load_conversations,
        load_conversation,
        load_messages,
        load_notebook_sources,
        load_enabled_sources_for_conversation,
        resolve_conversation_id,
    )
    from aios_habit.notebook_readiness import NotebookReadinessStore
    from aios_habit.workspace_memory_service import get_workspace_memory_enabled_preference
    from aios_habit.index_status import (
        get_cached_index_status_line,
        get_index_status_info,
        resolve_active_index_db_path,
        compute_logical_fingerprint,
        _INDEX_STATUS_MEMORY_CACHE,
    )
    from aios_habit.workspace_chat_app import (
        ensure_workspace_chat_worker_warming,
        is_workspace_chat_worker_warmed,
        list_pending_ide_requests,
    )
    timings["1_tai_khoi_tao_trang"] = round(time.perf_counter() - t0, 4)
    log_step(f"  [1] Tải / Khởi tạo trang: {timings['1_tai_khoi_tao_trang']:.4f}s")

    # Nếu đo lạnh: xóa sạch in-memory cache của index_status
    if is_cold:
        _INDEX_STATUS_MEMORY_CACHE.clear()
        log_step("  [*] Đã làm sạch in-memory cache tiến trình (_INDEX_STATUS_MEMORY_CACHE.clear())")

    # Khâu 2: Đọc metadata sổ
    t0 = time.perf_counter()
    active_notebooks = load_active_notebooks()
    target_nb = next((nb for nb in active_notebooks if nb.id == notebook_id), None)
    collections = load_collections()
    timings["2_doc_metadata_so"] = round(time.perf_counter() - t0, 4)
    details["notebook_title"] = target_nb.title if target_nb else "Không tìm thấy"
    details["collection_id"] = getattr(target_nb, "collection_id", "") or DEFAULT_COLLECTION_ID
    log_step(f"  [2] Đọc metadata sổ ({details['notebook_title']}): {timings['2_doc_metadata_so']:.4f}s")

    # Khâu 3: Liệt kê cuộc trò chuyện
    t0 = time.perf_counter()
    conversations = load_conversations(notebook_id)
    active_conv_id = resolve_conversation_id(notebook_id, None)
    timings["3_liet_ke_cuoc_tro_chuyen"] = round(time.perf_counter() - t0, 4)
    details["conversation_count"] = len(conversations)
    details["active_conv_id"] = active_conv_id
    log_step(f"  [3] Liệt kê cuộc trò chuyện ({len(conversations)} cuộc): {timings['3_liet_ke_cuoc_tro_chuyen']:.4f}s")

    # Khâu 4: Truy vấn cơ sở dữ liệu hội thoại
    t0 = time.perf_counter()
    conv = load_conversation(active_conv_id) if active_conv_id else None
    messages = load_messages(active_conv_id) if active_conv_id else []
    timings["4_truy_van_co_so_du_lieu_hoi_thoai"] = round(time.perf_counter() - t0, 4)
    details["message_count"] = len(messages)
    log_step(f"  [4] Truy vấn CSDL hội thoại ({len(messages)} tin nhắn): {timings['4_truy_van_co_so_du_lieu_hoi_thoai']:.4f}s")

    # Khâu 5: Chuẩn bị / phạm vi nguồn
    t0 = time.perf_counter()
    nb_sources = load_notebook_sources(notebook_id)
    nb_ready_store = NotebookReadinessStore()
    nb_snap = nb_ready_store.lay(notebook_id)
    enabled_selections = load_enabled_sources_for_conversation(active_conv_id) if active_conv_id else []
    timings["5_chuan_bi_pham_vi_nguon"] = round(time.perf_counter() - t0, 4)
    details["notebook_sources_count"] = len(nb_sources)
    details["enabled_selections_count"] = len(enabled_selections)
    log_step(f"  [5] Chuẩn bị/phạm vi nguồn ({len(nb_sources)} nguồn): {timings['5_chuan_bi_pham_vi_nguon']:.4f}s")

    # Khâu 6: Kiểm tra nạp mô hình / worker nền
    t0 = time.perf_counter()
    try:
        worker_warmed = is_workspace_chat_worker_warmed()
    except Exception as exc:
        worker_warmed = False
    timings["6_nap_mo_hinh_worker_nen"] = round(time.perf_counter() - t0, 4)
    details["worker_warmed"] = worker_warmed
    log_step(f"  [6] Kiểm tra mô hình/worker nền (warmed={worker_warmed}): {timings['6_nap_mo_hinh_worker_nen']:.4f}s")

    # Khâu 7: Dòng trạng thái kho & tính vân tay logic (Phân rã sâu khâu này)
    # Khâu 7: Dòng trạng thái kho & tính vân tay logic
    t0_idx_total = time.perf_counter()
    idx_path = resolve_active_index_db_path(getattr(conv, "collection_id", None) or details["collection_id"])
    details["index_db_path"] = str(idx_path) if idx_path else ""

    info = get_index_status_info(idx_path, backend_name="onnx")
    timings["7_dong_trang_thai_kho_va_van_tay"] = round(time.perf_counter() - t0_idx_total, 4)
    details["status_line"] = info.status_line
    details["doc_count"] = info.doc_count
    details["chunk_count"] = info.chunk_count
    details["fingerprint_12"] = info.fingerprint_12
    log_step(f"  [7] Dòng trạng thái kho: {timings['7_dong_trang_thai_kho_va_van_tay']:.4f}s -> {info.status_line}")

    # Khâu 8: Các khâu khác (Memory pref, pending IDE requests, v.v.)
    t0 = time.perf_counter()
    _ = get_workspace_memory_enabled_preference()
    if active_conv_id:
        _ = list_pending_ide_requests(active_conv_id)
    timings["8_cac_khau_khac"] = round(time.perf_counter() - t0, 4)
    log_step(f"  [8] Các khâu khác (Memory, IDE pending requests): {timings['8_cac_khau_khac']:.4f}s")

    t_total = round(time.perf_counter() - t_start_total, 4)
    timings["tong_thoi_gian_toan_trinh_s"] = t_total
    log_step(f"=== KẾT THÚC {step_name}: TỔNG {t_total:.4f}s ===\n")

    return {
        "step_name": step_name,
        "notebook_id": notebook_id,
        "is_cold": is_cold,
        "timings": timings,
        "details": details,
        "tong_thoi_gian_s": t_total,
    }


def main():
    log_step("=====================================================================")
    log_step("KHỞI ĐỘNG CHUỖI ĐO PHÂN RÃ THỜI GIAN MỞ SỔ (APP-OPEN-DIAG-PC0575)")
    log_step(f"Thời gian: {datetime.datetime.now().isoformat()}")
    log_step(f"Python interpreter: {sys.executable} (version {sys.version.split()[0]})")
    log_step("=====================================================================\n")

    all_results = {}

    # (a) Bấm vào sổ MOM — lần mở đầu tiên sau khi khởi động lại app (lạnh)
    res_mom_cold = profile_single_notebook_open(
        notebook_id="mom_opcenter",
        is_cold=True,
        step_name="(a) Bấm vào sổ MOM - Mở lần đầu sau khởi động app (LẠNH)",
    )
    all_results["so_mom_lan_1_lanh"] = res_mom_cold

    # (b) Bấm vào sổ MOM — lần mở thứ hai (ấm)
    res_mom_warm = profile_single_notebook_open(
        notebook_id="mom_opcenter",
        is_cold=False,
        step_name="(b) Bấm vào sổ MOM - Mở lần thứ hai (ẤM)",
    )
    all_results["so_mom_lan_2_am"] = res_mom_warm

    # (c1) Bấm vào sổ LSU (NB-E35A7BEE) — lần đầu (ấm sau khi MOM đã nạp DB, hoặc test độc lập)
    res_lsu_first = profile_single_notebook_open(
        notebook_id="NB-E35A7BEE",
        is_cold=False,
        step_name="(c1) Bấm vào sổ LSU (NB-E35A7BEE) - Lần đầu (sau khi MOM đã nạp)",
    )
    all_results["so_lsu_lan_1"] = res_lsu_first

    # (c2) Bấm vào sổ LSU (NB-E35A7BEE) — lần thứ hai (ấm)
    res_lsu_second = profile_single_notebook_open(
        notebook_id="NB-E35A7BEE",
        is_cold=False,
        step_name="(c2) Bấm vào sổ LSU (NB-E35A7BEE) - Lần thứ hai (ẤM)",
    )
    all_results["so_lsu_lan_2_am"] = res_lsu_second

    # Lưu kết quả JSON
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    log_step(f"Đã lưu kết quả đo đạc phân rã vào: {RESULTS_JSON}")
    log_step(f"Đã lưu toàn văn log thô vào: {LOG_FILE}")


if __name__ == "__main__":
    main()
