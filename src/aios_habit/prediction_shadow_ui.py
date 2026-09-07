"""UI components for LSU Iris data gate checking and unit trace lookup."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import streamlit as st

from aios_habit.i18n import t
from aios_habit.production_prediction.lsu_iris import (
    evaluate_data_gate_rubric,
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)
from aios_habit.production_prediction.models import (
    DataGateReport,
    DataGateStatus,
    JoinedUnitTrace,
    LsuDatasetSnapshot,
)
from aios_habit.production_prediction.repository import ProductionPredictionRepository

TECHNICAL_CODE_EXPLANATIONS = {
    "BOWSKEW_4_BEAM": "Kiểm tra độ lệch nghiêng 4 chùm tia quang học",
    "BOWSKEW_2_BEAM": "Kiểm tra độ lệch nghiêng 2 chùm tia quang học",
    "BEAM_4_BEAM": "Kiểm tra thông số chùm tia laser 4 beam",
    "LENS_COLLIMATOR": "Thấu kính chuẩn trực (Collimator Lens)",
    "LD_ARRAY": "Mảng diode laser phát quang (LD Array)",
    "FOCAL_LENGTH": "Tiêu cự thấu kính",
    "SURFACE_ROUGHNESS": "Độ nhám bề mặt quang học",
    "EMISSION_WAVELENGTH": "Bước sóng phát xạ trung tâm",
    "OUTPUT_POWER": "Công suất phát quang",
    "BOW_VALUE": "Độ lệch góc nghiêng tia đo được",
    "ERR_BOW_EXCEEDED": "Lỗi vượt ngưỡng dung sai độ lệch chùm tia",
}


def explain_technical_code(code: str) -> str:
    """Provide accessible Vietnamese explanation for technical codes and abbreviations."""
    return TECHNICAL_CODE_EXPLANATIONS.get(code.strip(), code.strip())


def data_gate_state_summary(state_key: str, detail: Optional[str] = None) -> Dict[str, str]:
    """Provide structured, safe Vietnamese messages and next steps for all data gate states."""
    states = {
        "unselected": {
            "status": "Chưa chọn tệp dữ liệu",
            "message": "Vui lòng chọn hoặc tải lên đủ 3 tệp dữ liệu: thông số linh kiện theo lot, liên kết Unit-lot và kết quả JIG.",
            "next_step": "Bước tiếp theo: Tải lên các tệp định dạng CSV hoặc XLSX hợp lệ.",
        },
        "reading": {
            "status": "Đang đọc tệp...",
            "message": "Hệ thống đang đọc và xác thực cấu trúc các tệp dữ liệu cục bộ.",
            "next_step": "Bước tiếp theo: Đợi hệ thống hoàn tất phân tích kiểm tra.",
        },
        "passed": {
            "status": "Dữ liệu hợp lệ theo tiêu chuẩn LSU Iris",
            "message": "Tất cả các điều kiện cổng dữ liệu bắt buộc đều đạt tiêu chuẩn an toàn.",
            "next_step": "Bước tiếp theo: Nhấn 'Đăng ký gói dữ liệu' để lưu dữ liệu vào kho dự đoán cục bộ.",
        },
        "passed_with_warning": {
            "status": "Dữ liệu đạt tiêu chuẩn có cảnh báo",
            "message": "Dữ liệu đủ điều kiện tối thiểu để chạy học hỏi ở chế độ chỉ đọc nhưng có một số lưu ý.",
            "next_step": "Bước tiếp theo: Xem lại các mục cảnh báo và tiến hành đăng ký nếu đồng ý tiếp tục.",
        },
        "missing_keys": {
            "status": "Thiếu trường khóa bắt buộc",
            "message": detail or "Tệp dữ liệu thiếu các trường khóa chính bắt buộc (như mã Unit hoặc mã lô linh kiện).",
            "next_step": "Bước tiếp theo: Bổ sung các trường khóa còn thiếu trong tệp nguồn trước khi kiểm tra lại.",
        },
        "conflicting_keys": {
            "status": "Phát hiện khóa chính trùng mâu thuẫn",
            "message": detail or "Có các bản ghi trùng lặp khóa chính nhưng mang giá trị đo hoặc kết quả mâu thuẫn nhau.",
            "next_step": "Bước tiếp theo: Làm sạch và loại bỏ các dòng mâu thuẫn trong tệp nguồn.",
        },
        "unsupported_format": {
            "status": "Định dạng tệp không được hỗ trợ",
            "message": detail or "Hệ thống chỉ hỗ trợ định dạng tệp CSV (chuẩn UTF-8) hoặc tệp Excel XLSX.",
            "next_step": "Bước tiếp theo: Xuất dữ liệu từ nguồn sang định dạng CSV hoặc XLSX tiêu chuẩn.",
        },
        "blocked": {
            "status": "Dữ liệu chưa đủ điều kiện để đăng ký",
            "message": detail or "Dữ liệu vi phạm quy tắc cổng (BLOCKED_DATA). Không được phép đăng ký gói dữ liệu bền vững.",
            "next_step": "Bước tiếp theo: Khắc phục các lỗi được liệt kê trong danh sách hành động.",
        },
    }
    return states.get(state_key, states["unselected"])


def shadow_state_summary(state_key: str, detail: Optional[str] = None) -> Dict[str, str]:
    """Provide structured, safe Vietnamese messages and next steps for shadow experiment states."""
    states = {
        "checking": {
            "status": "Đang kiểm tra dữ liệu",
            "message": "Hệ thống đang kiểm tra tính toàn vẹn và hợp lệ của gói dữ liệu trước khi chạy bóng.",
            "next_step": "Bước tiếp theo: Vui lòng đợi trong giây lát để hệ thống hoàn tất phân tích.",
        },
        "learning_shadow": {
            "status": "Đang chạy bóng để học",
            "message": "Chế độ chạy thử nghiệm bóng ở trạng thái học hỏi để thu thập dữ liệu kết quả thực tế (chưa đủ bằng chứng để tự động kích hoạt cảnh báo).",
            "next_step": "Bước tiếp theo: Tiếp tục chạy bóng và ghi nhận kết quả thực tế (outcome) từ xưởng để hoàn thiện mô hình.",
        },
        "auto_shadow": {
            "status": "Đang chạy bóng đạt tiêu chí",
            "message": "Dữ liệu và phương pháp đã đạt tiêu chuẩn rubric tự động, vận hành ở chế độ chỉ đọc an toàn.",
            "next_step": "Bước tiếp theo: Theo dõi danh sách sản phẩm có nguy cơ và tạo hồ sơ điều tra khi cần.",
        },
        "no_risk": {
            "status": "Không phát hiện nguy cơ",
            "message": "Không phát hiện sản phẩm nào có thông số linh kiện vượt ngưỡng dung sai trong lô vừa chạy.",
            "next_step": "Bước tiếp theo: Tiếp tục theo dõi các lô sản xuất tiếp theo hoặc kiểm tra gói dữ liệu khác.",
        },
        "has_risk": {
            "status": "Có sản phẩm cần kiểm tra",
            "message": "Phát hiện các sản phẩm có thông số linh kiện lệch chuẩn vượt ngưỡng dung sai kiểm soát (cần kiểm tra, không khẳng định chắc chắn hỏng).",
            "next_step": "Bước tiếp theo: Xem chi tiết các yếu tố cảnh báo và tạo hồ sơ điều tra cục bộ nếu cần.",
        },
        "stopped": {
            "status": "Đã dừng",
            "message": "Quá trình chạy bóng thử nghiệm đã được dừng an toàn theo yêu cầu của người dùng.",
            "next_step": "Bước tiếp theo: Bạn có thể tiếp tục chạy lại từ điểm dừng hoặc chọn lô dữ liệu khác.",
        },
        "error": {
            "status": "Có lỗi",
            "message": detail or "Có lỗi kỹ thuật xảy ra trong quá trình chạy thử nghiệm bóng.",
            "next_step": "Bước tiếp theo: Kiểm tra lại dữ liệu đầu vào hoặc xem hướng dẫn khắc phục.",
        },
    }
    return states.get(state_key, states["error"])


def format_shadow_risk_view(assessment: Any) -> Dict[str, Any]:
    """Prepare clean, safe presenter dictionary for a shadow risk assessment item."""
    factors_clean = []
    for f in getattr(assessment, "factors", []):
        factors_clean.append({
            "Mã lô linh kiện": f.get("component_lot_id", "Chưa rõ"),
            "Thông số kỹ thuật": explain_technical_code(f.get("metric_name", "")),
            "Độ lệch chuẩn": f"{f.get('z_score', 0.0):.2f} độ lệch chuẩn",
        })

    link_status_labels = {
        "linked": "Đã liên kết",
        "pending_case_link": "Chờ liên kết",
        "retryable_error": "Lỗi có thể thử lại",
        "failed": "Thất bại",
    }
    raw_link_status = getattr(assessment, "link_status", "")
    vn_link_status = link_status_labels.get(raw_link_status, "Chưa xác định")

    return {
        "unit_serial": assessment.unit_serial,
        "as_of_time": assessment.as_of_time or "Chưa ghi nhận",
        "risk_level": "Cần kiểm tra (Nguy cơ cao)" if assessment.risk_level == "HIGH" else "Cần kiểm tra",
        "verdict": "Cần kiểm tra",
        "reason": assessment.reason,
        "idempotency_key": assessment.idempotency_key[:16] + "...",
        "snapshot_id": assessment.snapshot_id[:16] + "...",
        "method_version": "EWMA cố định (Ngưỡng 3.0 độ lệch chuẩn)",
        "case_id": assessment.case_id,
        "link_status": vn_link_status,
        "factors": factors_clean,
    }


def format_unit_trace_view(trace: Optional[JoinedUnitTrace]) -> Dict[str, Any]:
    """Prepare clean, safe presenter dictionary for a Unit trace lookup."""
    if trace is None:
        return {
            "found": False,
            "message": "Không tìm thấy thông tin sản phẩm này trong gói dữ liệu hiện tại.",
            "next_step": "Bước tiếp theo: Kiểm tra lại mã sản phẩm hoặc chọn gói dữ liệu khác.",
        }

    label_desc = "Đạt tiêu chuẩn (OK)" if trace.target_label == "OK" else "Lỗi (NG)" if trace.target_label == "NG" else "Chưa xác định"
    fail_desc = explain_technical_code(trace.failure_code) if trace.failure_code else "Không có lỗi ghi nhận"

    lots = []
    for m in trace.lot_measurements:
        lots.append({
            "Mã lô": m.component_lot_id,
            "Loại linh kiện": explain_technical_code(m.component_code),
            "Thông số": explain_technical_code(m.metric_name),
            "Giá trị": f"{m.value} {m.unit}",
            "Thời điểm đo": m.event_time.strftime("%d/%m/%Y %H:%M:%S"),
        })

    jigs = []
    for j in trace.jig_measurements:
        jigs.append({
            "Mã JIG": explain_technical_code(j.jig_id),
            "Lần chạy": j.run_id,
            "Thông số": explain_technical_code(j.metric_name),
            "Giá trị": f"{j.value} {j.unit or ''}".strip(),
            "Kết quả": "Đạt (OK)" if j.target_label == "OK" else "Lỗi (NG)",
            "Thời điểm": j.event_time.strftime("%d/%m/%Y %H:%M:%S"),
        })

    return {
        "found": True,
        "unit_serial": trace.unit_serial,
        "target_label": trace.target_label,
        "label_desc": label_desc,
        "failure_code": trace.failure_code,
        "fail_desc": fail_desc,
        "assembly_time": trace.assembly_time.strftime("%d/%m/%Y %H:%M:%S") if trace.assembly_time else "Chưa có",
        "jig_event_time": trace.jig_event_time.strftime("%d/%m/%Y %H:%M:%S") if trace.jig_event_time else "Chưa có",
        "lot_measurements": lots,
        "jig_measurements": jigs,
    }


def render_lsu_data_gate(
    repository: ProductionPredictionRepository,
    on_close: Callable[[], None],
    locale: str = "vi",
    case_service: Optional[Any] = None,
) -> None:
    """Render the LSU Data Gate, Trace Viewer, and Manual Shadow Runner inside Workspace Chat."""
    st.markdown("## 🔍 Kiểm tra dữ liệu & Chạy bóng LSU Iris")
    st.caption("Cổng kiểm tra dữ liệu, tra cứu chuỗi vết và chạy bóng đánh giá nguy cơ chỉ đọc.")

    top_col1, top_col2 = st.columns([4, 1])
    with top_col2:
        if st.button("⬅️ Quay lại Sổ tài liệu", key="wsc_close_lsu_data_gate", use_container_width=True):
            on_close()
            return

    # Lazy load CaseService if not provided
    if case_service is None:
        try:
            from aios_habit.workspace_case_repository import WorkspaceCaseRepository
            from aios_habit.workspace_case_service import WorkspaceCaseService
            case_repo = WorkspaceCaseRepository(Path("local_cases/workspace_cases.sqlite"))
            case_service = WorkspaceCaseService(case_repo)
        except Exception:
            case_service = None

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Cổng kiểm tra dữ liệu",
        "🔎 Tra cứu chuỗi sản phẩm",
        "🚀 Chạy bóng thử nghiệm",
        "📝 Ghi nhận kết quả thực tế",
    ])

    with tab1:
        st.markdown("### 1. Chọn tệp dữ liệu kiểm tra")
        col_c, col_u, col_j = st.columns(3)
        with col_c:
            comp_file = st.file_uploader("1. Thông số lô linh kiện", type=["csv", "xlsx"], key="wsc_lsu_comp_file")
        with col_u:
            unit_file = st.file_uploader("2. Liên kết sản phẩm - lô linh kiện", type=["csv", "xlsx"], key="wsc_lsu_unit_file")
        with col_j:
            jig_file = st.file_uploader("3. Kết quả đo JIG & nhãn đánh giá", type=["csv", "xlsx"], key="wsc_lsu_jig_file")

        if not comp_file or not unit_file or not jig_file:
            unsel = data_gate_state_summary("unselected")
            st.info(f"ℹ️ **{unsel['status']}**\n\n{unsel['message']}\n\n*{unsel['next_step']}*")
        else:
            if st.button("🚀 Bắt đầu kiểm tra cổng dữ liệu", key="wsc_run_lsu_check", type="primary"):
                with st.spinner("Đang đọc tệp..."):
                    try:
                        with tempfile.TemporaryDirectory() as tmp_d:
                            tmp_path = Path(tmp_d)
                            p_comp = tmp_path / comp_file.name
                            p_unit = tmp_path / unit_file.name
                            p_jig = tmp_path / jig_file.name

                            p_comp.write_bytes(comp_file.getvalue())
                            p_unit.write_bytes(unit_file.getvalue())
                            p_jig.write_bytes(jig_file.getvalue())

                            snapshot = read_lsu_source(p_comp, p_unit, p_jig)
                            normalized = normalize_records(snapshot)
                            traces = join_lsu_trace(normalized)
                            gate_report = evaluate_data_gate_rubric(snapshot, normalized, traces)

                            st.session_state["wsc_last_lsu_snapshot"] = normalized
                            st.session_state["wsc_last_lsu_report"] = gate_report
                            st.session_state["wsc_last_lsu_traces"] = traces
                    except ValueError:
                        st.error("❌ Cấu trúc tệp dữ liệu không hợp lệ hoặc thiếu cột bắt buộc. Vui lòng kiểm tra lại định dạng tệp.")
                    except Exception:
                        st.error("❌ Có lỗi xảy ra khi đọc tệp. Hãy kiểm tra định dạng tệp.")

            if "wsc_last_lsu_report" in st.session_state:
                report: DataGateReport = st.session_state["wsc_last_lsu_report"]
                snap: LsuDatasetSnapshot = st.session_state["wsc_last_lsu_snapshot"]

                st.markdown("---")
                st.markdown("### 2. Kết quả đánh giá cổng dữ liệu")

                if report.status == DataGateStatus.PASS:
                    st.success("✅ **Dữ liệu hợp lệ theo tiêu chuẩn LSU Iris**")
                    st.info("Bước tiếp theo: Bạn có thể nhấn 'Đăng ký gói dữ liệu' bên dưới để lưu vào kho dự đoán cục bộ.")
                elif report.status == DataGateStatus.PASS_WITH_WARNING:
                    st.warning("⚠️ **Dữ liệu đạt tiêu chuẩn có cảnh báo**")
                    st.info("Bước tiếp theo: Xem lại các cảnh báo và tiến hành đăng ký nếu đồng ý.")
                else:
                    st.error("🛑 **Dữ liệu chưa đủ điều kiện để đăng ký (BLOCKED_DATA)**")
                    st.warning("Bước tiếp theo: Khắc phục các lỗi được liệt kê bên dưới trước khi thử lại.")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Tổng số bản ghi", f"{report.total_rows:,}")
                m2.metric("Tỷ lệ nối chuỗi", f"{report.join_coverage_percent:.1f}%")
                m3.metric("Số sản phẩm Đạt (OK)", f"{report.ok_count}")
                m4.metric("Số sản phẩm Lỗi (NG)", f"{report.ng_count}")

                if report.action_items:
                    st.markdown("#### Các điểm cần lưu ý và hành động khắc phục:")
                    for act in report.action_items:
                        st.write(f"- {act}")

                # Register button
                if report.status in (DataGateStatus.PASS, DataGateStatus.PASS_WITH_WARNING):
                    if st.button("💾 Đăng ký gói dữ liệu vào kho dự đoán", key="wsc_register_lsu_snap"):
                        try:
                            ok = repository.register_lsu_snapshot(snap, report)
                            if ok:
                                st.success("🎉 Đã đăng ký gói dữ liệu thành công vào cơ sở dữ liệu cục bộ!")
                        except Exception:
                            st.error("❌ Không thể đăng ký gói dữ liệu vào kho lúc này. Vui lòng thử lại.")

    with tab2:
        st.markdown("### Tra cứu chuỗi truy vết (Lô ➔ Sản phẩm ➔ JIG)")
        snapshots = repository.list_snapshots()
        if not snapshots:
            st.info("Chưa có gói dữ liệu nào được đăng ký trong kho dự đoán. Hãy tải lên và đăng ký dữ liệu ở Thẻ 1 trước.")
        else:
            snap_options = {s["snapshot_id"]: f"Gói dữ liệu {s['snapshot_id'][:12]} ({s['created_at'][:19]})" for s in snapshots}
            sel_snap_id = st.selectbox("Chọn gói dữ liệu", options=list(snap_options.keys()), format_func=lambda k: snap_options[k])

            search_unit = st.text_input("Nhập số sê-ri sản phẩm cần tra cứu (ví dụ: SYN_UNIT_001):", key="wsc_unit_search_input")
            if search_unit:
                trace = repository.load_unit_trace(sel_snap_id, search_unit.strip())
                trace_view = format_unit_trace_view(trace)

                if not trace_view["found"]:
                    st.warning(f"⚠️ {trace_view['message']}\n\n*{trace_view['next_step']}*")
                else:
                    st.success(f"Đã tìm thấy sản phẩm: **{trace_view['unit_serial']}**")
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Kết quả kiểm tra:** {trace_view['label_desc']}")
                    c2.markdown(f"**Chi tiết lỗi:** {trace_view['fail_desc']}")
                    c3.markdown(f"**Thời gian lắp ráp:** {trace_view['assembly_time']}")

                    if trace_view["lot_measurements"]:
                        st.markdown("#### 1. Thông số linh kiện các lô đã dùng")
                        st.table(trace_view["lot_measurements"])

                    if trace_view["jig_measurements"]:
                        st.markdown("#### 2. Kết quả đo kiểm tại các JIG")
                        st.table(trace_view["jig_measurements"])

    with tab3:
        st.markdown("### 🚀 Chạy bóng thử nghiệm thủ công")
        st.caption("Chế độ chạy thử nghiệm chỉ đọc, không can thiệp sản xuất và không gửi cảnh báo ra ngoài.")

        from aios_habit.production_prediction.evaluation import ReplayProtocol
        from aios_habit.production_prediction.shadow import (
            ManualShadowRunner,
            link_shadow_risk_to_workspace_case,
        )

        has_active_snap = "wsc_last_lsu_snapshot" in st.session_state and "wsc_last_lsu_traces" in st.session_state
        if not has_active_snap:
            st.info("Chưa có gói dữ liệu hợp lệ đang chọn. Vui lòng tải lên và kiểm tra dữ liệu ở Thẻ 1 trước.")
        else:
            rep: Optional[DataGateReport] = st.session_state.get("wsc_last_lsu_report")
            if rep is not None and rep.status == DataGateStatus.BLOCKED_DATA:
                st.error("🛑 **Dữ liệu chưa đạt tiêu chuẩn cổng (BLOCKED_DATA)**")
                st.warning(
                    "Dữ liệu đang ở trạng thái bị chặn do vi phạm quy tắc an toàn kỹ thuật. "
                    "Không được phép chạy thử nghiệm bóng trên tập dữ liệu này.\n\n"
                    "*Bước tiếp theo: Vui lòng quay lại Thẻ 1 để xem danh sách lỗi và khắc phục tệp nguồn.*"
                )
            else:
                snap: LsuDatasetSnapshot = st.session_state["wsc_last_lsu_snapshot"]
                raw_traces = st.session_state["wsc_last_lsu_traces"]
                if isinstance(raw_traces, dict):
                    traces_map = raw_traces
                elif isinstance(raw_traces, list):
                    traces_map = {t.unit_serial: t for t in raw_traces}
                else:
                    traces_map = {}

                # Synchronize rubric conclusion: Bắt buộc tuân thủ báo cáo rubric phát lại
                if replay_rep and isinstance(replay_rep, dict):
                    che_do = replay_rep.get("che_do_khuyen_nghi", "LEARNING_SHADOW")
                else:
                    # Khi chưa có báo cáo rubric phát lại, bắt buộc mặc định là LEARNING_SHADOW
                    che_do = "LEARNING_SHADOW"

                if che_do == "LEARNING_SHADOW":
                    st.warning(f"⚠️ **{state_info['status']}**\n\n{state_info['message']}\n\n*{state_info['next_step']}*")
                else:
                    st.success(f"✅ **{state_info['status']}**\n\n{state_info['message']}\n\n*{state_info['next_step']}*")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    batch_limit = st.selectbox(
                        "Kích thước lô kiểm tra (số lượng sản phẩm)",
                        options=[10, 20, 50, len(traces_map)],
                        format_func=lambda x: f"Toàn bộ ({x} sản phẩm)" if x == len(traces_map) else f"{x} sản phẩm",
                        key="wsc_shadow_batch_limit",
                    )
                with col_b2:
                    stop_requested = st.checkbox("Yêu cầu dừng sau lô hiện tại", key="wsc_shadow_stop_check")

                if st.button("🚀 Bắt đầu chạy bóng thủ công", key="wsc_start_shadow_btn", type="primary"):
                    if not traces_map or not snap:
                        st.warning("Không có dữ liệu hợp lệ để chạy thử nghiệm.")
                    else:
                        progress_bar = st.progress(0, text="Đang bắt đầu chạy bóng...")
                        status_text = st.empty()

                        def _progress_cb(p: Any) -> None:
                            pct = int((p.processed_units / max(1, p.total_units)) * 100)
                            progress_bar.progress(pct, text=f"Đang xử lý: {p.processed_units}/{p.total_units} sản phẩm")
                            status_text.write(f"Đã xử lý: **{p.processed_units}** sản phẩm | Cảnh báo: **{p.alerted_units}** sản phẩm")

                        runner = ManualShadowRunner(
                            protocol=ReplayProtocol(control_limit_std=3.0),
                            batch_size=10,
                        )
                        stop_limit = 10 if stop_requested else batch_limit
                        run_res = runner.run(
                            snapshot=snap,
                            traces=traces_map,
                            on_progress=_progress_cb,
                            stop_after_units=stop_limit,
                            repository=repository,
                        )
                        st.session_state["wsc_last_shadow_result"] = run_res

                if "wsc_last_shadow_result" in st.session_state:
                    res = st.session_state["wsc_last_shadow_result"]
                    st.markdown("---")
                    shadow_status_map = {
                        "completed": "Hoàn thành",
                        "stopped": "Đã dừng",
                        "failed": "Thất bại",
                        "running": "Đang chạy",
                    }
                    status_display = shadow_status_map.get(getattr(res, "status", ""), "Chưa xác định")
                    st.markdown(f"#### Kết quả chạy thử nghiệm bóng (Trạng thái: **{status_display}**)")

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Tổng sản phẩm cần chạy", f"{res.total_units}")
                    m2.metric("Đã xử lý", f"{res.processed_units}")
                    m3.metric("Số sản phẩm cần kiểm tra", f"{res.alerted_units}")

                    if res.status == "stopped":
                        st_info = shadow_state_summary("stopped")
                        st.info(f"⏹️ **{st_info['status']}**: {st_info['message']}")
                    elif res.status == "completed":
                        st.success("✅ **Đã hoàn thành lượt chạy thử nghiệm bóng.**")
                    elif res.status == "failed":
                        st.error("❌ **Lượt chạy thử nghiệm bóng gặp lỗi gián đoạn.**")

                    if not res.risk_assessments:
                        no_risk = shadow_state_summary("no_risk")
                        st.success(f"✅ **{no_risk['status']}**\n\n{no_risk['message']}\n\n*{no_risk['next_step']}*")
                    else:
                        has_risk = shadow_state_summary("has_risk")
                        st.warning(f"⚠️ **{has_risk['status']}**\n\n{has_risk['message']}\n\n*{has_risk['next_step']}*")

                        st.markdown("##### Danh sách các sản phẩm cần kiểm tra:")
                        for idx, assess in enumerate(res.risk_assessments, start=1):
                            view_dict = format_shadow_risk_view(assess)
                            with st.expander(f"⚠️ Sản phẩm: {view_dict['unit_serial']} — {view_dict['verdict']}"):
                                c1, c2 = st.columns(2)
                                c1.markdown(f"**Thời điểm đánh giá:** {view_dict['as_of_time']}")
                                c1.markdown(f"**Đánh giá an toàn:** {view_dict['verdict']} (*Không khẳng định hỏng*)")
                                c2.markdown(f"**Phương pháp:** {view_dict['method_version']}")
                                c2.markdown(f"**Mã định danh:** `{view_dict['idempotency_key']}`")

                                st.write(f"**Lý do:** {view_dict['reason']}")

                                if view_dict["factors"]:
                                    st.markdown("**Các yếu tố lệch chuẩn:**")
                                    st.table(view_dict["factors"])

                                # Case linkage
                                if case_service is not None:
                                    if assess.link_status == "linked" and assess.case_id:
                                        st.success(f"✅ Đã liên kết với hồ sơ điều tra: `{assess.case_id}`")
                                    else:
                                        if st.button(
                                            f"🔗 Tạo / Liên kết hồ sơ điều tra ({view_dict['unit_serial']})",
                                            key=f"wsc_link_case_{idx}",
                                        ):
                                            try:
                                                created_c = link_shadow_risk_to_workspace_case(assess, case_service, repository=repository)
                                                st.success(f"🎉 Đã liên kết thành công hồ sơ: `{created_c.case_id}`")
                                                st.session_state["wsc_last_shadow_result"] = res
                                            except Exception:
                                                st.error("❌ Không thể liên kết hồ sơ lúc này. Vui lòng thử lại.")

    with tab4:
        st.markdown("### 📝 Ghi nhận kết quả thực tế từ xưởng")
        st.caption("Cho phép kỹ thuật viên và kiểm tra chất lượng (QC) cập nhật kết quả kiểm tra thực tế cho từng sản phẩm để kiểm chứng độ chính xác.")

        from aios_habit.production_prediction.shadow import record_shadow_outcome

        u_input = st.text_input("1. Mã số sê-ri sản phẩm cần ghi nhận kết quả:", key="wsc_outcome_unit_input")
        lbl_input = st.selectbox(
            "2. Kết quả kiểm tra thực tế:",
            options=["OK", "NG", "UNKNOWN"],
            format_func=lambda x: "Đạt tiêu chuẩn (OK)" if x == "OK" else "Lỗi sản xuất (NG)" if x == "NG" else "Chưa xác định",
            key="wsc_outcome_lbl_input",
        )

        fail_code = ""
        is_missed = False
        if lbl_input == "NG":
            col_ng1, col_ng2 = st.columns(2)
            with col_ng1:
                fail_code = st.text_input("Mã lỗi (ví dụ: ERR_BOW_EXCEEDED):", value="ERR_BOW_EXCEEDED", key="wsc_outcome_code_input")
            with col_ng2:
                is_missed = st.checkbox(
                    "Đây là sản phẩm lỗi (NG) bị bỏ sót (không có cảnh báo trước đó)",
                    value=False,
                    key="wsc_outcome_missed_check",
                )

        c_conf, c_evi = st.columns(2)
        with c_conf:
            confirmed_by = st.text_input("3. Người xác nhận (bắt buộc):", value="Kỹ thuật viên QC", key="wsc_outcome_conf_by")
        with c_evi:
            evidence_note = st.text_input("4. Bằng chứng / Biên bản xác nhận:", value="Biên bản kiểm tra JIG quang học", key="wsc_outcome_evi_note")

        rationale = st.text_area("5. Lý do / Giải trình kết quả:", value="Kết quả đo kiểm lại tại công đoạn kiểm tra cuối cùng.", key="wsc_outcome_rationale")

        if st.button("💾 Lưu kết quả thực tế vào kho dự đoán", key="wsc_save_outcome_btn", type="primary"):
            if not u_input.strip():
                st.warning("⚠️ Vui lòng nhập mã số sê-ri sản phẩm trước khi lưu.")
            elif not confirmed_by.strip():
                st.warning("⚠️ Vui lòng nhập thông tin người xác nhận.")
            else:
                try:
                    out_rec = record_shadow_outcome(
                        repository=repository,
                        unit_serial=u_input.strip(),
                        target_label=lbl_input,
                        failure_code=fail_code.strip() if fail_code.strip() else None,
                        confirmed_by=confirmed_by.strip(),
                        rationale=f"{rationale.strip()} (Bằng chứng: {evidence_note.strip()})",
                        is_missed_alert=is_missed,
                    )
                    st.success(f"🎉 Đã ghi nhận thành công kết quả cho sản phẩm: **{out_rec.unit_serial}** (Mã kết quả: `{out_rec.outcome_id}`)")
                except Exception:
                    st.error("❌ Lỗi khi ghi nhận kết quả. Vui lòng kiểm tra lại kết nối kho dữ liệu.")