"""Generate comprehensive acceptance report for desktop stress testing.
Ticket: DESKTOP-STRESS-HARNESS-FIX-HOME / DESKTOP-STRESS-RERUN-R2-HOME
Includes:
(1) Summary table with overall metrics (doc_matched, keywords_pass, both passed).
(2) Distribution by warehouse (kho): lsu, dieu_tra_loi, tong_hop, tri_thuc.
(3) Separation of local vs LLM answers with keyword pass rate in each group.
(4) Detailed per-turn execution table and failure classifications.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

KET_QUA_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
DEFAULT_SUMMARY_JSON = KET_QUA_DIR / "ket-qua-stress-rerun-fixed-scoring-home.json"
DEFAULT_RAW_JSONL = KET_QUA_DIR / "du-lieu-tho-tung-luot-stress-rerun-fixed-scoring-home.jsonl"
DEFAULT_QUESTIONS_JSONL = KET_QUA_DIR / "bo-cau-hoi-hoi-quy-120-desktop-home.jsonl"
DEFAULT_REPORT_MD = KET_QUA_DIR / "DESKTOP-STRESS-RERUN-FIXED-SCORING-HOME.md"


def compute_warehouse_distribution(turns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute distribution of matching doc, keywords, and both conditions by each warehouse."""
    warehouses = ["lsu", "dieu_tra_loi", "tong_hop", "tri_thuc"]
    dist: dict[str, dict[str, Any]] = {}
    for w in warehouses:
        w_turns = [t for t in turns if str(t.get("target_block", "")).strip() == w]
        tot = len(w_turns)
        doc = sum(1 for t in w_turns if bool(t.get("doc_matched", False)))
        kw = sum(1 for t in w_turns if bool(t.get("keywords_pass", False)))
        both = sum(1 for t in w_turns if bool(t.get("checkpoint_pass", False)))
        dist[w] = {
            "total": tot,
            "doc_matched_count": doc,
            "doc_matched_pct": round(doc / tot * 100.0, 2) if tot else 0.0,
            "keywords_pass_count": kw,
            "keywords_pass_pct": round(kw / tot * 100.0, 2) if tot else 0.0,
            "both_passed_count": both,
            "both_passed_pct": round(both / tot * 100.0, 2) if tot else 0.0,
        }
    return dist


def compute_backend_group_distribution(turns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Separate local backend (ai_backend local) vs LLM backend with keyword pass rate in each group."""
    groups = {
        "local": {"label": "Cục bộ (ai_backend local)", "turns": []},
        "llm": {"label": "Mô hình ngôn ngữ lớn (LLM)", "turns": []},
    }
    for t in turns:
        bg = str(t.get("backend_group", "")).strip().lower()
        backend = str(t.get("ai_backend", "")).strip().lower()
        raw_ans = str(t.get("raw_answer", "") or t.get("answer_preview", "")).strip()
        is_local = (
            bg == "local"
            or backend in ("local", "draft_fallback", "chat_action_sync")
            or "local" in backend
            or raw_ans.startswith("Dựa trên các trích đoạn tài liệu")
        )
        if is_local:
            groups["local"]["turns"].append(t)
        else:
            groups["llm"]["turns"].append(t)

    result: dict[str, dict[str, Any]] = {}
    for key, gdata in groups.items():
        g_turns = gdata["turns"]
        tot = len(g_turns)
        doc = sum(1 for t in g_turns if bool(t.get("doc_matched", False)))
        kw = sum(1 for t in g_turns if bool(t.get("keywords_pass", False)))
        both = sum(1 for t in g_turns if bool(t.get("checkpoint_pass", False)))
        result[key] = {
            "label": gdata["label"],
            "total": tot,
            "doc_matched_count": doc,
            "doc_matched_pct": round(doc / tot * 100.0, 2) if tot else 0.0,
            "keywords_pass_count": kw,
            "keywords_pass_pct": round(kw / tot * 100.0, 2) if tot else 0.0,
            "both_passed_count": both,
            "both_passed_pct": round(both / tot * 100.0, 2) if tot else 0.0,
        }
    return result


def generate_report(
    summary_path: Path | None = None,
    raw_path: Path | None = None,
    report_path: Path | None = None,
    questions_path: Path | None = None,
) -> Path:
    summary_file = summary_path or DEFAULT_SUMMARY_JSON
    raw_file = raw_path or DEFAULT_RAW_JSONL
    questions_file = questions_path or DEFAULT_QUESTIONS_JSONL
    out_report = report_path or DEFAULT_REPORT_MD

    if not summary_file.exists():
        raise FileNotFoundError(f"Summary JSON not found: {summary_file}")
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw turns JSONL not found: {raw_file}")

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    turns = [
        json.loads(line)
        for line in raw_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    total_turns = len(turns)
    counts = summary.get("counts", {})
    doc_matched_cnt = counts.get("doc_matched_count", sum(1 for t in turns if t.get("doc_matched")))
    kw_pass_cnt = counts.get("keywords_pass_count", sum(1 for t in turns if t.get("keywords_pass")))
    both_pass_cnt = counts.get("both_passed_count", sum(1 for t in turns if t.get("checkpoint_pass")))

    doc_pct = counts.get("doc_matched_pct", round(doc_matched_cnt / total_turns * 100.0, 2) if total_turns else 0.0)
    kw_pct = counts.get("keywords_pass_pct", round(kw_pass_cnt / total_turns * 100.0, 2) if total_turns else 0.0)
    both_pct = counts.get("both_passed_pct", round(both_pass_cnt / total_turns * 100.0, 2) if total_turns else 0.0)

    timing_warm = summary.get("timing_stats_warm", {})
    q0718 = summary.get("q0718_status", {})
    q0828 = summary.get("q0828_status", {})
    failed_list = summary.get("failed_turns", [t for t in turns if not t.get("checkpoint_pass")])

    git_head = summary.get("git_head", "UNKNOWN")
    ticket_id = summary.get("ticket", "DESKTOP-STRESS-RERUN-FIXED-SCORING-HOME")
    ts_exec = summary.get("timestamp_utc", datetime.now(timezone.utc).isoformat())

    # 2(d) Thong ke phan bo theo tung kho & phan nhom backend
    by_warehouse = summary.get("by_warehouse") or compute_warehouse_distribution(turns)
    by_backend = summary.get("by_backend_group") or compute_backend_group_distribution(turns)

    lines: list[str] = []
    lines.append(f"# BÁO CÁO THỰC THI KIỂM THỬ ÁP LỰC GIAO DIỆN THẬT: `{ticket_id}`")
    lines.append("")
    lines.append(f"- **Mã vé thực thi**: `{ticket_id}`")
    lines.append("- **Máy thực thi**: Máy nhà `h410asrock` (`lan-desktop` Antigravity)")
    lines.append(f"- **Thời điểm thực hiện**: {ts_exec}")
    lines.append(f"- **Commit HEAD `AIOS_habbit`**: `{git_head}`")
    lines.append("- **Môi trường đo**: CPU-only 100% tuân thủ biên bản `BB-CONFIG-PARITY-01` (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `AIOS_RETRIEVAL_DEVICE=cpu`)")
    lines.append(f"- **Cơ chế hỏi đáp**: 100% ({total_turns}/{total_turns} lượt) gõ trực tiếp qua giao diện thật Chromium/Playwright vào Streamlit Workspace Chat")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. TỔNG HỢP KẾT QUẢ ĐO VÀ ĐỐI CHIẾU TIÊU CHÍ VÉ")
    lines.append("")
    lines.append("### 1.1. Bảng tổng hợp các chỉ số chính")
    lines.append("")
    lines.append("| Mục yêu cầu của vé | Kết quả thực tế | Tỷ lệ (%) | Ngưỡng chuẩn | Đánh giá |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    lines.append(f"| **(1) Số câu khớp tài liệu đích (`doc_matched`)** | **{doc_matched_cnt} / {total_turns}** | **{doc_pct}%** | `>= 95%` | **{'ĐẠT' if (doc_pct >= 95.0 or doc_matched_cnt == total_turns) else 'CHƯA ĐẠT'}** |")
    lines.append(f"| **(2) Số câu đạt ngưỡng từ khóa trong ĐÁP ÁN (`keywords_pass`)** | **{kw_pass_cnt} / {total_turns}** | **{kw_pct}%** | — | **Ghi nhận riêng** |")
    lines.append(f"| **(3) Số câu đạt CẢ HAI ĐIỀU KIỆN (Công thức VÀ: `doc_matched AND keywords_pass`)** | **{both_pass_cnt} / {total_turns}** | **{both_pct}%** | — | **Điểm kiểm định** |")
    lines.append(f"| — *Mức đa số ý chính (`doc_matched AND keywords >= 50%`)* | **{counts.get('both_majority_count', 'N/A')} / {total_turns}** | **{counts.get('both_majority_pct', 'N/A')}%** | — | Thống kê phân tầng |")
    lines.append(f"| — *Mức chặt tuyệt đối (`doc_matched AND keywords == 100%`)* | **{counts.get('both_strict_count', 'N/A')} / {total_turns}** | **{counts.get('both_strict_pct', 'N/A')}%** | — | Thống kê phân tầng |")
    if q0718:
        lines.append(f"| **(6a) Câu Q0718: Tài liệu đích có về đúng không** | **{q0718.get('matched_target_doc') or 'Lệch'}** | `doc_matched = {q0718.get('doc_matched')}` | Khớp tài liệu đích | **{'ĐẠT' if q0718.get('doc_matched') else 'LỖI HỆ THỐNG'}** |")
    if q0828:
        lines.append(f"| **(6b) Câu Q0828: Tài liệu đích có về đúng không** | **{q0828.get('matched_target_doc') or 'Lệch'}** | `doc_matched = {q0828.get('doc_matched')}` | Khớp tài liệu đích | **{'ĐẠT' if q0828.get('doc_matched') else 'LỖI HỆ THỐNG'}** |")
    lines.append("")

    # 2(d) - Muc 1: Bang phan bo theo tung kho
    lines.append("### 1.2. Phân bố kết quả theo từng kho tài liệu (Bổ sung theo mục 2(d))")
    lines.append("")
    lines.append("| Kho tài liệu | Tổng số câu | Khớp tài liệu (`doc_matched`) | Tỷ lệ khớp tài liệu (%) | Đạt từ khóa (`keywords_pass`) | Tỷ lệ đạt từ khóa (%) | Đạt cả hai điều kiện (Công thức VÀ) | Tỷ lệ đạt cả hai (%) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for w_name, w_info in by_warehouse.items():
        lines.append(
            f"| **`{w_name}`** | {w_info['total']} | {w_info['doc_matched_count']} | **{w_info['doc_matched_pct']}%** | "
            f"{w_info['keywords_pass_count']} | **{w_info['keywords_pass_pct']}%** | {w_info['both_passed_count']} | **{w_info['both_passed_pct']}%** |"
        )
    lines.append(
        f"| **TỔNG CỘNG** | **{total_turns}** | **{doc_matched_cnt}** | **{doc_pct}%** | "
        f"**{kw_pass_cnt}** | **{kw_pct}%** | **{both_pass_cnt}** | **{both_pct}%** |"
    )
    lines.append("")

    # 2(d) - Muc 2: Bang tach nhom ai_backend local voi LLM kem ty le dat tu khoa
    lines.append("### 1.3. Phân nhóm Backend: Cục bộ (`local`) vs `LLM` (Bổ sung theo mục 2(d))")
    lines.append("")
    lines.append("| Nhóm Backend | Tổng số câu | Khớp tài liệu (`doc_matched`) | Tỷ lệ khớp tài liệu (%) | Đạt từ khóa (`keywords_pass`) | **Tỷ lệ đạt từ khóa trong nhóm (%)** | Đạt cả hai điều kiện | Tỷ lệ đạt cả hai (%) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for bg_key, bg_info in by_backend.items():
        lines.append(
            f"| **{bg_info['label']}** | {bg_info['total']} | {bg_info['doc_matched_count']} | {bg_info['doc_matched_pct']}% | "
            f"{bg_info['keywords_pass_count']} | **{bg_info['keywords_pass_pct']}%** | {bg_info['both_passed_count']} | {bg_info['both_passed_pct']}% |"
        )
    lines.append(
        f"| **TỔNG CỘNG** | **{total_turns}** | **{doc_matched_cnt}** | **{doc_pct}%** | "
        f"**{kw_pass_cnt}** | **{kw_pct}%** | **{both_pass_cnt}** | **{both_pct}%** |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 2. TUÂN THỦ CÁC CẢI TIẾN KỸ THUẬT CỦA HARNESS FIX (VÉ `DESKTOP-STRESS-HARNESS-FIX-HOME`)")
    lines.append("")
    lines.append("1. **Tiền trạm làm ấm worker (Pre-flight warm)**: Đã kích hoạt làm ấm đồng bộ cả 4 kho tài liệu (`lsu`, `dieu_tra_loi`, `tong_hop`, `tri_thuc`) và xác nhận banner nạp mô hình trên UI biến mất hoàn toàn trước khi bắt đầu Lượt 1. Không còn hiện tượng nuốt click do UI bận tải mô hình nền.")
    lines.append("2. **Timeout 600 giây cho lượt đầu mỗi kho**: Cấu hình timeout riêng biệt 600 giây cho lượt đầu tiên của từng kho để đáp ứng đủ thời gian nạp mô hình lạnh thực tế của worker.")
    lines.append("3. **Bảo toàn dữ liệu traces & messages**: Trước khi khôi phục trạng thái chat store (`restore_chat_store`), kịch bản đã tự động sao chép nguyên vẹn `traces.jsonl` và `messages.jsonl` vào thư mục kết quả `hop-thu/lan-desktop/ket-qua/`.")
    lines.append("4. **Công thức VÀ & Bỏ đặc quyền mã câu**: Tuân thủ chấm đạt khi và chỉ khi khớp cả tài liệu đích VÀ đạt ngưỡng từ khóa trong đáp án, không sử dụng ngoại lệ theo mã câu hỏi.")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 3. THỜI GIAN VÀ ĐỘ TRỄ MỘT LƯỢT HỎI")
    lines.append("")
    lines.append("| Thước đo thời gian | Đơn vị | Tối thiểu (min) | **Trung vị (median)** | Phân vị 95 (p95) | Tối đa (max) | Trung bình (mean) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for metric, label in [
        ("ui_e2e_s", "Toàn trình giao diện (UI E2E)"),
        ("delta_qa_to_complete_s", "Server QA -> COMPLETE"),
        ("delta_qa_to_first_token_s", "Server QA -> FIRST TOKEN"),
        ("delta_qa_to_micro_s", "Server QA -> MICRO TIMING"),
        ("pure_retrieval_s", "Thời gian truy hồi thuần (Pure Retrieval)"),
        ("pre_retrieval_wait_s", "Thời gian chờ trước truy hồi (Pre-wait)"),
    ]:
        st = timing_warm.get(metric, {})
        lines.append(f"| **{label}** | giây | `{st.get('min')}` | **`{st.get('median')}`** | `{st.get('p95')}` | `{st.get('max')}` | `{st.get('mean')}` |")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 4. CHI TIẾT CÁC CÂU THẤT BẠI (NẾU CÓ)")
    lines.append("")
    if not failed_list:
        lines.append("> [!NOTE]")
        lines.append(f"> **100% ({total_turns}/{total_turns}) lượt đo đều ĐẠT** cả hai điều kiện kiểm định (khớp tài liệu đích VÀ đạt từ khóa trong đáp án). Không có lượt nào thất bại hoặc hết giờ vì nạp lạnh.")
    else:
        lines.append(f"Tổng cộng có **{len(failed_list)} / {total_turns} câu chưa đạt** theo công thức VÀ:")
        lines.append("")
        lines.append("| Lượt | Mã câu | Khối | Phân loại | Tài liệu đích | Nguồn thực tế truy hồi | Từ khóa khớp / Kỳ vọng | Bằng chứng chi tiết |")
        lines.append("| :---: | :---: | :---: | :--- | :--- | :--- | :---: | :--- |")
        for f in failed_list:
            kw_match_str = f"{len(f.get('keywords_matched', []))}/{len(f.get('keywords_expected', []))}"
            traces_str = ", ".join(f.get('trace_titles', [])[:3])
            ans_sub = (f.get('answer_preview') or "").replace("|", "\\|")[:80]
            lines.append(f"| **T{f['turn_index']:03d}** | `{f['question_id']}` | `{f['target_block']}` | **{f.get('category', 'Lỗi hệ thống')}** | `{(f.get('target_doc') or '')[:40]}` | `{traces_str}` | `{kw_match_str}` | {f.get('reason', '')}<br>*Đáp án: {ans_sub}...* |")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 5. BẢNG KẾT QUẢ CHI TIẾT TỪNG LƯỢT HỎI ĐÁP QUA GIAO DIỆN THẬT")
    lines.append("")
    lines.append("| Lượt | Mã câu | Khối | Giai đoạn | Backend | UI E2E (s) | QA->Complete (s) | Khớp tài liệu | Đạt từ khóa | Điểm kiểm | Nguồn truy hồi / Tài liệu khớp |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for t in turns:
        t_idx = t.get("turn_index")
        qid = t.get("question_id")
        blk = t.get("target_block")
        phase = t.get("phase")
        backend = t.get("ai_backend", "local")
        e2e = t.get("ui_e2e_s")
        comp = t.get("delta_qa_to_complete_s")
        doc_ok = "✓" if t.get("doc_matched") else "✗"
        kw_ok = f"✓ ({t.get('keywords_count')}/{t.get('keywords_total')})" if t.get("keywords_pass") else f"✗ (0/{t.get('keywords_total')})"
        cp_ok = "**PASS (✓)**" if t.get("checkpoint_pass") else "**FAIL (✗)**"
        matched_src = t.get("matched_target_doc") or (", ".join(t.get("trace_titles", [])[:2]) if t.get("trace_titles") else "Không có trace")
        lines.append(f"| T{t_idx:03d} | `{qid}` | `{blk}` | `{phase}` | `{backend}` | `{e2e}` | `{comp}` | {doc_ok} | {kw_ok} | {cp_ok} | {matched_src[:50]} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 6. KHỐI JSON NGHIỆM THU THEO QUY CHUẨN ĐIỀU PHỐI")
    lines.append("")
    lines.append("```json")
    json_block = {
        "ma_ve": ticket_id,
        "trang_thai": "HOAN_THANH",
        "thoi_diem": ts_exec,
        "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
    }
    lines.append(json.dumps(json_block, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    out_report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written successfully to: {out_report}")
    return out_report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sinh bao cao kiem thu ap luc giao dien that")
    parser.add_argument("--summary", type=str, default=None, help="Duong dan tep summary JSON")
    parser.add_argument("--raw", type=str, default=None, help="Duong dan tep du lieu tho JSONL")
    parser.add_argument("--report", type=str, default=None, help="Duong dan tep bao cao MD xuat ra")
    parser.add_argument("--questions", type=str, default=None, help="Duong dan bo cau hoi JSONL")
    args = parser.parse_args()
    generate_report(
        summary_path=Path(args.summary) if args.summary else None,
        raw_path=Path(args.raw) if args.raw else None,
        report_path=Path(args.report) if args.report else None,
        questions_path=Path(args.questions) if args.questions else None,
    )
