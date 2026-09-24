"""Chat wiring for US12: route Omnibar text to JIG ingest, alert config, or persona.

Pure logic with injected dependencies (no Streamlit import) so contract
tests run fast. The app passes session_state dict, save callbacks, and a
config path; tests pass fakes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aios_habit.production_prediction.alert_config_chat import (
    AlertConfig,
    parse_config_command,
    render_text_dashboard,
)
from aios_habit.production_prediction.chart_selection import (
    TEN_LOAI_BIEU_DO,
    dung_du_lieu_bieu_do,
    hieu_lenh_ve_bieu_do,
)
from aios_habit.production_prediction.jig_alert_cards import build_instant_log_card
from aios_habit.production_prediction.jig_log_ingest import (
    ban_ghi_iris_sang_dong_log,
    evaluate_single_log_ewma,
    is_jig_log_line,
    la_dong_log_iris_that,
    nhan_dien_khoi_log_dan,
    parse_dong_log_iris_dan,
    parse_jig_log_line,
    thong_diep_dong_log_iris,
)
from aios_habit.production_prediction.iris_log_adapter import parse_khoi_depth_dan, thong_diep_khoi_depth
from aios_habit.production_prediction.log_archive import (
    GIOI_HAN_DONG_MOI_LAN,
    MAC_DINH_KHO_PATH,
    bang_tom_tat_kho_van_ban,
    ghi_ban_ghi,
    ghi_dong_log_jig,
    la_lenh_kho_log,
)
from aios_habit.production_prediction.chart_selection import (
    ma_chi_so_chuan,
    tra_nguong_theo_chi_so,
)
from aios_habit.production_prediction.metric_limits import (
    KhoNguong,
    MAC_DINH_NGUONG_PATH,
    bang_nguong_van_ban,
    doc_nguong,
    la_lenh_nguong,
    luu_nguong,
    xu_ly_lenh_nguong,
)
from aios_habit.production_prediction.session_isolation import (
    SessionPersona,
    parse_persona_command,
)

_CONFIG_VERBS = (
    "them email", "thêm email", "xoa email", "xóa email",
    "nguong", "ngưỡng", "gian cach", "giãn cách",
    "gop tin", "gộp tin",
)
_CONFIG_DASHBOARD_HINTS = ("cau hinh", "cấu hình", "cai dat", "cài đặt", "bang cau", "bảng cấu hình")
_CONFIG_SCOPES = ("canh bao", "cảnh báo", "lsu", "jig", "email", "nguong", "ngưỡng")
_PERSONA_HINTS = ("truc ban", "trực ban", "ca nhan", "cá nhân")
_CHART_HINTS = ("bieu do", "biểu đồ")
_LUU_Y_TAM_DUNG = ("tạm dừng luồng", "tam dung luong", "dung cap nhat", "dừng cập nhật")
_LUU_Y_TIEP_TUC = ("tiếp tục luồng", "tiep tuc luong", "bat lai hien thi", "bật lại hiển thị")


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def is_config_intent(text: str) -> bool:
    """Detect natural-language alert-config requests on the Omnibar."""
    norm = _norm(text)
    if any(verb in norm for verb in _CONFIG_VERBS):
        return True
    if any(hint in norm for hint in _CONFIG_DASHBOARD_HINTS) and any(
        scope in norm for scope in _CONFIG_SCOPES
    ):
        return True
    return False


def is_persona_intent(text: str) -> bool:
    """Detect one-touch watchdog/personal mode requests."""
    norm = _norm(text)
    return any(hint in norm for hint in _PERSONA_HINTS)


def is_chart_intent(text: str) -> bool:
    """Detect natural-language chart requests for 015-csv-chart-selector."""
    return any(hint in _norm(text) for hint in _CHART_HINTS)


def is_stream_pause_intent(text: str) -> Optional[bool]:
    """Detect pause/resume requests for the live stream display (007 US8)."""
    norm = _norm(text)
    if any(hint in norm for hint in _LUU_Y_TAM_DUNG):
        return True
    if any(hint in norm for hint in _LUU_Y_TIEP_TUC):
        return False
    return None


def load_alert_config(path: str | Path) -> AlertConfig:
    """Load alert config from a local JSON file; default when missing."""
    config_path = Path(path)
    if not config_path.exists():
        return AlertConfig()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return AlertConfig()
    if not isinstance(data, dict):
        return AlertConfig()
    recipients = [str(e) for e in data.get("nguoi_nhan", []) if str(e).strip()]
    try:
        threshold = float(data.get("nguong_phan_tram", 80.0))
    except (ValueError, TypeError):
        threshold = 80.0
    try:
        cooldown = int(data.get("gian_cach_phut", 30))
    except (ValueError, TypeError):
        cooldown = 30
    return AlertConfig(
        nguoi_nhan=recipients,
        nguong_phan_tram=threshold,
        gian_cach_phut=cooldown,
        gop_tin=bool(data.get("gop_tin", True)),
        theo_doi_ewma=bool(data.get("theo_doi_ewma", True)),
    )


def save_alert_config(config: AlertConfig, path: str | Path) -> None:
    """Persist alert config locally (runtime file, never committed)."""
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _doi_moc_iso(gia_tri: Any) -> Any:
    """Đổi mốc ISO của dòng log thành ``datetime`` để tra ngưỡng theo thời điểm."""
    if not gia_tri:
        return None
    try:
        from datetime import datetime

        moc = datetime.fromisoformat(str(gia_tri))
    except (TypeError, ValueError):
        return None
    return moc.replace(tzinfo=None) if moc.tzinfo else moc


def _muc_ket_luan(trang_thai: str) -> str:
    """Map an EWMA status to a one-word nontech verdict."""
    trang_thai = (trang_thai or "").strip().lower()
    if "vi phạm" in trang_thai:
        return "Nguy cơ"
    if "đạt" in trang_thai or "bình thường" in trang_thai:
        return "Bình thường"
    return "Cần kiểm tra"


def format_instant_card_text(card: Dict[str, Any]) -> str:
    """Render the instant log card as chat message text."""
    muc = _muc_ket_luan(str(card.get("trang_thai", "")))
    lines = [
        f"Kết luận: {muc} — {card.get('ma_unit', '—')} — {card.get('thong_so', '—')} ({card.get('trang_thai', '')})",
        f"Giá trị: {card.get('gia_tri', '—')} {card.get('don_vi', '')} | JIG: {card.get('ma_jig', '—')}",
        str(card.get("chi_tiet", "")),
        str(card.get("nguong_tham_khao", "")),
        "Gợi ý: " + ", ".join(str(g) for g in card.get("goi_y", [])),
    ]
    return "\n".join(line for line in lines if line.strip())


def _quyet_dinh_ve_bieu_do(
    text: str,
    chart_rows_provider: Optional[Callable[[], Any]],
    kho_nguong: Optional[KhoNguong] = None,
) -> JigChatOutcome:
    """Handle a Vietnamese chart request with the shared builder (015)."""
    cac_hang = _cac_hang_ve(chart_rows_provider)
    if not cac_hang:
        return JigChatOutcome(
            handled=True,
            assistant_text=(
                "Chưa có dữ liệu để vẽ biểu đồ. "
                "Vui lòng mở mục Kiểm tra dữ liệu LSU, tải tệp và chờ báo dữ liệu hợp lệ trước."
            ),
        )
    danh_sach_jig = sorted({str(h.get("jig_id", "")).strip() for h in cac_hang
                             if isinstance(h, dict) and str(h.get("jig_id", "")).strip()})
    danh_sach_chi_so = sorted({str(h.get("metric_name", "")).strip() for h in cac_hang
                                if isinstance(h, dict) and str(h.get("metric_name", "")).strip()})
    lenh = hieu_lenh_ve_bieu_do(text, danh_sach_jig, danh_sach_chi_so)
    if lenh.con_thieu:
        return JigChatOutcome(
            handled=True,
            assistant_text=(
                f"Tôi chưa rõ {', '.join(lenh.con_thieu)}. "
                "Vui lòng cho biết thêm, ví dụ: vẽ biểu đồ độ lệch cho 2ND-1035."
            ),
        )
    try:
        from aios_habit.production_prediction.spc_chart import render_chart_png

        if lenh.loai_bieu_do == "so_sanh_mau":
            cac_dau_vao = []
            for chi_so in danh_sach_chi_so[:4]:
                try:
                    cac_dau_vao.append(dung_du_lieu_bieu_do(lenh.ma_jig, chi_so, cac_hang, kho_nguong=kho_nguong))
                except ValueError:
                    continue
            if not cac_dau_vao:
                return JigChatOutcome(
                    handled=True,
                    assistant_text="Không đủ dữ liệu để so sánh. Vui lòng chọn loại biểu đồ xu hướng hoặc phân bố.",
                )
            du_lieu: Any = cac_dau_vao
        else:
            du_lieu = dung_du_lieu_bieu_do(lenh.ma_jig, lenh.ten_chi_so, cac_hang, kho_nguong=kho_nguong)
        import tempfile
        from pathlib import Path as _Path

        with tempfile.TemporaryDirectory() as tmp_d:
            duong_anh = _Path(tmp_d) / "bieu_do_chat.png"
            render_chart_png(du_lieu, lenh.loai_bieu_do, duong_anh)
            anh_bytes = duong_anh.read_bytes()
    except ValueError as loi:
        return JigChatOutcome(handled=True, assistant_text=f"⚠️ {loi}")
    except Exception:
        return JigChatOutcome(
            handled=True,
            assistant_text="Không vẽ được biểu đồ lúc này. Vui lòng thử lại hoặc chọn chỉ số khác ở Thẻ 1.",
        )
    ten_loai = TEN_LOAI_BIEU_DO.get(lenh.loai_bieu_do, lenh.loai_bieu_do)
    bang_so = _bang_so_van_ban(du_lieu)
    # Biểu đồ thiếu giới hạn thật: nói rõ thiếu gì, nhập gì, và rằng ảnh là mô phỏng.
    ghi_chu_thieu_nguong = ""
    try:
        from aios_habit.production_prediction.chart_selection import huong_dan_thieu_nguong

        mau_dau = du_lieu
        if isinstance(du_lieu, (list, tuple)):
            mau_dau = du_lieu[0] if du_lieu else None
        if mau_dau is not None and getattr(mau_dau, "mo_phong", False):
            ghi_chu_thieu_nguong = "\n\n⚠️ " + huong_dan_thieu_nguong(lenh.ten_chi_so)
    except Exception:
        ghi_chu_thieu_nguong = ""
    return JigChatOutcome(
        handled=True,
        assistant_text=(
            f"Đã vẽ {ten_loai} cho {lenh.ma_jig} — {lenh.ten_chi_so}. "
            "Ảnh đã lưu vào phiên để xem lại ở Thẻ 1 và dùng cho email cảnh báo."
            + bang_so
            + ghi_chu_thieu_nguong
        ),
        chart_png=anh_bytes,
        chart_meta={"ma_jig": lenh.ma_jig, "ten_chi_so": lenh.ten_chi_so,
                    "loai_bieu_do": lenh.loai_bieu_do,
                    "mo_phong": bool(getattr(du_lieu, "mo_phong", False))
                    if not isinstance(du_lieu, (list, tuple)) else False},
    )


def _bang_so_van_ban(du_lieu: Any, so_diem: int = 5) -> str:
    """Render the last data points as a text table for screen-reader fallback."""
    try:
        cac_gia_tri = list(getattr(du_lieu, "values", []) or [])
        cac_nhan = list(getattr(du_lieu, "nhan_thoi_gian", []) or [])
        don_vi = str(getattr(du_lieu, "unit", "") or "")
    except Exception:
        return ""
    if not cac_gia_tri:
        return ""
    cap = list(zip(cac_nhan, cac_gia_tri))[-so_diem:]
    dong = [f"- {nhan or 'Điểm'}: {gia_tri:g} {don_vi}".rstrip() for nhan, gia_tri in cap]
    return "\nBảng số (%d điểm gần nhất):\n" % len(cap) + "\n".join(dong)


@dataclass
class JigChatOutcome:
    handled: bool = False
    assistant_text: str = ""
    new_persona: Optional[str] = None
    config_changed: bool = False
    chart_png: Optional[bytes] = None
    chart_meta: Optional[Dict[str, Any]] = None
    stream_paused: Optional[bool] = None
    nguong_changed: bool = False
    kho_nguong: Optional[KhoNguong] = None


def _cac_hang_ve(rows_provider: Optional[Callable[[], Any]]) -> List[Any]:
    if rows_provider is None:
        return []
    try:
        rows = rows_provider()
    except Exception:
        return []
    if not rows:
        return []
    return list(rows)


def decide_jig_action(
    text: str,
    *,
    persona_che_do: str = "ca_nhan",
    alert_config: Optional[AlertConfig] = None,
    history_provider: Optional[Callable[[str, str], List[float]]] = None,
    chart_rows_provider: Optional[Callable[[], Any]] = None,
    nguong: Optional[KhoNguong] = None,
    kho_log_path: str | Path = MAC_DINH_KHO_PATH,
) -> JigChatOutcome:
    """Pure decision: JIG log, config command, persona command, or nothing."""
    config = alert_config or AlertConfig()
    kho = nguong or KhoNguong()
    first_line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    # Real Iris wide-matrix rows (optionally pasted with their header) are
    # parsed by the adapter: one row expands into many named measurements.
    # Khối đo sâu dán thẳng vào chat: tự nhận diện và tách giá trị.
    if nhan_dien_khoi_log_dan(text or "") == "depth":
        ket_qua_depth = parse_khoi_depth_dan(text or "")
        hop_le_depth = ket_qua_depth.ban_ghi_hop_le()
        if hop_le_depth:
            try:
                ket_qua_ghi_depth = ghi_ban_ghi(
                    hop_le_depth, nguon="dan_tay", tep="", kho=kho_log_path
                )
            except Exception:
                ket_qua_ghi_depth = {"da_ghi": 0, "bi_cat": 0}
            # Yêu cầu "log nào cũng có cảnh báo theo ngưỡng": khối đo sâu cũng phải
            # ra thẻ kết luận như dòng log rộng, không chỉ tóm tắt số lượng.
            uu_tien_depth = None
            for ban_ghi in hop_le_depth:
                ung_vien = tra_nguong_theo_chi_so(
                    kho,
                    ban_ghi.jig_id,
                    ban_ghi.metric_name,
                    ban_ghi.unit_serial,
                    ban_ghi.event_time,
                )
                if ung_vien is not None and ung_vien.hieu_luc():
                    uu_tien_depth = ban_ghi
                    break
            chon_depth = uu_tien_depth or hop_le_depth[0]
            first_depth = ban_ghi_iris_sang_dong_log(chon_depth)
            history_depth: List[float] = []
            if history_provider is not None:
                try:
                    history_depth = list(
                        history_provider(first_depth.jig_id, first_depth.metric) or []
                    )
                except Exception:
                    history_depth = []
            nguong_depth = tra_nguong_theo_chi_so(
                kho,
                first_depth.jig_id,
                first_depth.metric,
                first_depth.unit_serial,
                _doi_moc_iso(first_depth.timestamp),
            )
            ket_luan_depth = evaluate_single_log_ewma(
                first_depth.value, history_depth, nguong=nguong_depth
            )
            the_depth = build_instant_log_card(first_depth.to_dict(), ket_luan_depth)
            return JigChatOutcome(
                handled=True,
                assistant_text=(
                    format_instant_card_text(the_depth)
                    + "\n\n"
                    + thong_diep_khoi_depth(ket_qua_depth)
                    + f" Đã lưu {ket_qua_ghi_depth['da_ghi']:,} giá trị vào kho log để phân tích lại."
                    + (
                        f" Bỏ qua {ket_qua_depth.bo_qua_canh_loi:,} ô canh lỗi."
                        if ket_qua_depth.bo_qua_canh_loi
                        else ""
                    )
                    + (
                        f" Lưu ý: kho chỉ nhận {GIOI_HAN_DONG_MOI_LAN:,} dòng mỗi lần, "
                        f"còn {ket_qua_ghi_depth['bi_cat']:,} giá trị chưa lưu."
                        if ket_qua_ghi_depth.get("bi_cat")
                        else ""
                    )
                    + (
                        ""
                        if uu_tien_depth is not None
                        else " Chưa có ngưỡng thật cho chỉ số này nên mới đối chiếu xu hướng EWMA."
                    )
                ),
            )
    if first_line and la_dong_log_iris_that(first_line):
        ket_qua = parse_dong_log_iris_dan(text or "")
        if ket_qua.thieu_cot:
            return JigChatOutcome(handled=True, assistant_text=thong_diep_dong_log_iris(ket_qua))
        hop_le = ket_qua.ban_ghi_hop_le()
        if not hop_le:
            return JigChatOutcome(handled=True, assistant_text=thong_diep_dong_log_iris(ket_qua))
        # Ưu tiên chỉ số có ngưỡng thật: đó mới là thứ quyết định cảnh báo.
        def _tra_nguong(ban_ghi: Any) -> Any:
            return tra_nguong_theo_chi_so(
                kho,
                ban_ghi.jig_id,
                ban_ghi.metric_name,
                ban_ghi.unit_serial,
                ban_ghi.event_time,
            )

        uu_tien = None
        for ban_ghi in hop_le:
            ung_vien = _tra_nguong(ban_ghi)
            if ung_vien is not None and ung_vien.hieu_luc():
                uu_tien = ban_ghi
                break
        chon = uu_tien or hop_le[0]
        first = ban_ghi_iris_sang_dong_log(chon)
        # "Cho từng dòng log vào file": lưu ngay mọi giá trị tách được để lần sau
        # AI còn dữ liệu phân tích, không chỉ nằm trong tin nhắn chat.
        try:
            ket_qua_ghi = ghi_ban_ghi(hop_le, nguon="dan_tay", tep="", kho=kho_log_path)
        except Exception:
            ket_qua_ghi = {"da_ghi": 0, "bi_cat": 0}
        history: List[float] = []
        if history_provider is not None:
            try:
                history = list(history_provider(first.jig_id, first.metric) or [])
            except Exception:
                history = []
        nguong_chi_so = _tra_nguong(chon)
        result = evaluate_single_log_ewma(first.value, history, nguong=nguong_chi_so)
        card = build_instant_log_card(first.to_dict(), result)
        reply = format_instant_card_text(card)
        reply += (
            f"\nĐã tách {len(hop_le)} giá trị đo từ dòng log Iris "
            f"({first.unit_serial}, {first.jig_id})."
        )
        if ket_qua.bo_qua_canh_loi:
            reply += f" Bỏ qua {ket_qua.bo_qua_canh_loi} ô mang giá trị canh lỗi (máy không đo được)."
        if ket_qua_ghi.get("bi_cat"):
            reply += (
                f" Lưu ý: kho log chỉ nhận {GIOI_HAN_DONG_MOI_LAN:,} dòng mỗi lần, "
                f"còn {ket_qua_ghi['bi_cat']:,} giá trị chưa lưu."
            )
        if uu_tien is None:
            reply += " Chưa có ngưỡng thật cho chỉ số này nên mới đối chiếu xu hướng EWMA."
        return JigChatOutcome(handled=True, assistant_text=reply)
    if first_line and is_jig_log_line(first_line):
        parsed = [p for line in (text or "").splitlines() if (p := parse_jig_log_line(line))]
        if not parsed:
            return JigChatOutcome(
                handled=True,
                assistant_text="Dòng log chưa đủ thông tin mã Unit và tên thông số để kiểm tra.",
            )
        first = parsed[0]
        try:
            ghi_dong_log_jig(parsed, kho=kho_log_path)
        except Exception:
            pass
        history: List[float] = []
        if history_provider is not None:
            try:
                history = list(history_provider(first.jig_id, first.metric) or [])
            except Exception:
                history = []
        nguong_chi_so = tra_nguong_theo_chi_so(
            kho,
            first.jig_id,
            first.metric,
            first.unit_serial,
            _doi_moc_iso(first.timestamp),
        )
        result = evaluate_single_log_ewma(first.value, history, nguong=nguong_chi_so)
        card = build_instant_log_card(first.to_dict(), result)
        reply = format_instant_card_text(card)
        if len(parsed) > 1:
            reply += f"\nĐã nhận thêm {len(parsed) - 1} dòng log trong cùng tin nhắn."
        return JigChatOutcome(handled=True, assistant_text=reply)
    if is_chart_intent(text):
        return _quyet_dinh_ve_bieu_do(text, chart_rows_provider, kho_nguong=kho)
    tam_dung = is_stream_pause_intent(text)
    if tam_dung is not None:
        return JigChatOutcome(
            handled=True,
            assistant_text=(
                "Đã tạm dừng hiển thị luồng. Dữ liệu JIG vẫn ghi ngầm."
                if tam_dung
                else "Đã bật lại hiển thị luồng JIG trực tiếp."
            ),
            stream_paused=tam_dung,
        )
    if la_lenh_kho_log(text):
        return JigChatOutcome(
            handled=True,
            assistant_text=bang_tom_tat_kho_van_ban(kho_log_path),
        )
    if la_lenh_nguong(text):
        # So trên bản sao để phát hiện thay đổi thật: xu_ly_lenh_nguong sửa
        # trực tiếp kho nên so với chính nó sẽ luôn ra "không đổi".
        kho_truoc = KhoNguong.from_dict(kho.to_dict())
        kho_moi, loi_nhan = xu_ly_lenh_nguong(text, kho, jig_id="")
        return JigChatOutcome(
            handled=True,
            assistant_text=loi_nhan,
            nguong_changed=kho_moi.to_dict() != kho_truoc.to_dict(),
            kho_nguong=kho_moi,
        )
    if is_config_intent(text):
        updated, loi_nhan = parse_config_command(text, config)
        changed = updated.to_dict() != config.to_dict()
        config.nguoi_nhan = updated.nguoi_nhan
        config.nguong_phan_tram = updated.nguong_phan_tram
        config.gian_cach_phut = updated.gian_cach_phut
        config.gop_tin = updated.gop_tin
        config.theo_doi_ewma = updated.theo_doi_ewma
        return JigChatOutcome(
            handled=True,
            assistant_text=loi_nhan + "\n\n" + render_text_dashboard(config),
            config_changed=changed,
        )
    if is_persona_intent(text):
        current = SessionPersona(ten_phien="", che_do=persona_che_do)
        updated_persona, loi_nhan = parse_persona_command(text, current)
        return JigChatOutcome(
            handled=True,
            assistant_text=loi_nhan,
            new_persona=updated_persona.che_do,
        )
    return JigChatOutcome(handled=False)


def handle_jig_chat_text(
    text: str,
    *,
    conversation_id: str,
    locale: str = "vi",
    session_state: Any,
    save_user: Callable[[str], None],
    save_assistant: Callable[[str], None],
    config_path: str | Path = Path("local_cases") / "jig_alert_config.json",
    history_provider: Optional[Callable[[str, str], List[float]]] = None,
    chart_rows_provider: Optional[Callable[[], Any]] = None,
    limits_path: str | Path = MAC_DINH_NGUONG_PATH,
    kho_log_path: str | Path = MAC_DINH_KHO_PATH,
) -> bool:
    """App entry: persist user message, handle JIG/config/persona, reply.

    Returns True when handled (caller should rerun instead of RAG/Agent).
    """
    del locale  # Reply text is Vietnamese by module contract.
    try:
        persona_che_do = str(session_state.get("wsc_jig_persona", "ca_nhan"))
    except Exception:
        persona_che_do = "ca_nhan"
    config = load_alert_config(config_path)
    kho = doc_nguong(limits_path)
    outcome = decide_jig_action(
        text,
        persona_che_do=persona_che_do,
        alert_config=config,
        history_provider=history_provider,
        chart_rows_provider=chart_rows_provider,
        nguong=kho,
        kho_log_path=kho_log_path,
    )
    if not outcome.handled:
        return False
    save_user((text or "").strip())
    if outcome.stream_paused is not None:
        try:
            session_state[f"wsc_stream_paused_{conversation_id}"] = outcome.stream_paused
        except Exception:
            pass
    if outcome.chart_png:
        try:
            session_state["wsc_last_chart_png"] = outcome.chart_png
            session_state["wsc_last_chart_meta"] = outcome.chart_meta or {}
        except Exception:
            pass
    if outcome.new_persona in ("ca_nhan", "truc_ban"):
        try:
            session_state["wsc_jig_persona"] = outcome.new_persona
        except Exception:
            pass
    if outcome.config_changed:
        save_alert_config(config, config_path)
    if outcome.nguong_changed and outcome.kho_nguong is not None:
        luu_nguong(outcome.kho_nguong, limits_path)
    save_assistant(outcome.assistant_text)
    return True
