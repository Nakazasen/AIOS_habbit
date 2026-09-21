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
    evaluate_single_log_ewma,
    is_jig_log_line,
    parse_jig_log_line,
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
                    cac_dau_vao.append(dung_du_lieu_bieu_do(lenh.ma_jig, chi_so, cac_hang))
                except ValueError:
                    continue
            if not cac_dau_vao:
                return JigChatOutcome(
                    handled=True,
                    assistant_text="Không đủ dữ liệu để so sánh. Vui lòng chọn loại biểu đồ xu hướng hoặc phân bố.",
                )
            du_lieu: Any = cac_dau_vao
        else:
            du_lieu = dung_du_lieu_bieu_do(lenh.ma_jig, lenh.ten_chi_so, cac_hang)
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
    return JigChatOutcome(
        handled=True,
        assistant_text=(
            f"Đã vẽ {ten_loai} cho {lenh.ma_jig} — {lenh.ten_chi_so}. "
            "Ảnh đã lưu vào phiên để xem lại ở Thẻ 1 và dùng cho email cảnh báo."
            + bang_so
        ),
        chart_png=anh_bytes,
        chart_meta={"ma_jig": lenh.ma_jig, "ten_chi_so": lenh.ten_chi_so,
                    "loai_bieu_do": lenh.loai_bieu_do},
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
) -> JigChatOutcome:
    """Pure decision: JIG log, config command, persona command, or nothing."""
    config = alert_config or AlertConfig()
    first_line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    if first_line and is_jig_log_line(first_line):
        parsed = [p for line in (text or "").splitlines() if (p := parse_jig_log_line(line))]
        if not parsed:
            return JigChatOutcome(
                handled=True,
                assistant_text="Dòng log chưa đủ thông tin mã Unit và tên thông số để kiểm tra.",
            )
        first = parsed[0]
        history: List[float] = []
        if history_provider is not None:
            try:
                history = list(history_provider(first.jig_id, first.metric) or [])
            except Exception:
                history = []
        result = evaluate_single_log_ewma(first.value, history)
        card = build_instant_log_card(first.to_dict(), result)
        reply = format_instant_card_text(card)
        if len(parsed) > 1:
            reply += f"\nĐã nhận thêm {len(parsed) - 1} dòng log trong cùng tin nhắn."
        return JigChatOutcome(handled=True, assistant_text=reply)
    if is_chart_intent(text):
        return _quyet_dinh_ve_bieu_do(text, chart_rows_provider)
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
    outcome = decide_jig_action(
        text,
        persona_che_do=persona_che_do,
        alert_config=config,
        history_provider=history_provider,
        chart_rows_provider=chart_rows_provider,
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
    save_assistant(outcome.assistant_text)
    return True
