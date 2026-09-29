"""Builtin chat action: LSU Iris shadow-risk prediction over the local store.

Wires the `production_prediction` package + `prediction_shadow_ui` presenters
(TOOL-1 inventory: the prediction group was reachable only through the JIG chat
wire and the LSU panel) into the chat through the `chat_action` framework:

- `ProductionPredictionRepository` (read-only mode) lists the registered data
  packages and loads the selected snapshot / unit trace.
- `lsu_iris.normalize_records` + `join_lsu_trace` rebuild the in-memory traces.
- `shadow.ManualShadowRunner` + `evaluation.ReplayProtocol.default_lsu_iris`
  recompute the EWMA shadow risk in memory (`repository=None`, nothing saved).
- `prediction_shadow_ui.format_shadow_risk_view` / `format_unit_trace_view`
  render the Vietnamese tables shown in the answer bubble.

Read-only: opens the SQLite store in `mode=ro`, never migrates or backs up,
never writes assessments or outcomes, and never touches the chat store.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)

ACTION_NAME = "du_doan_rui_ro"
ACTION_TITLE = "Dự đoán rủi ro (LSU Iris)"

_HINTS = ("dự đoán",)

# Leading words stripped from the target tail: "rủi ro cho SYN_UNIT_002" -> "SYN_UNIT_002".
_TARGET_LEADING_WORDS = (
    "về",
    "cho",
    "giúp tôi",
    "hộ",
    "xem",
    "gói dữ liệu",
    "mã gói",
    "gói",
    "mã",
    "số",
    "sản phẩm",
    "unit",
    "lỗi",
    "rủi ro",
    "của",
    "các",
    "những",
)

_PUNCTUATION = " \t\r\n.,:;!?…\"'“”‘’()[]"

_MAX_SNAPSHOTS_SCANNED = 10
_MAX_UNITS_RUN = 200
_MAX_RISK_ROWS = 15
_MAX_TRACE_ROWS = 8


@dataclass(frozen=True)
class _Selection:
    """Chosen data package plus the optional unit-serial filter."""

    snap: Any
    unit_serials: Tuple[str, ...]
    kind: str  # "latest" | "snapshot" | "unit"


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _default_prediction_db_path() -> Path:
    return Path("local_cases") / "production_prediction.sqlite"


def _protocol() -> Any:
    from aios_habit.production_prediction.evaluation import ReplayProtocol

    return ReplayProtocol.default_lsu_iris()


def _target_from_question(question: str) -> str:
    """Extract the free-text target typed after "dự đoán" (keeps typed accents)."""
    raw = str(question or "")
    lowered = raw.lower()
    index = lowered.find("dự đoán")
    if index >= 0:
        return _clean_target(raw[index + len("dự đoán") :])
    normalized = normalize_text(raw)
    index = normalized.find("du doan")
    if index >= 0:
        return _clean_target(normalized[index + len("du doan") :])
    return ""


def _clean_target(tail: str) -> str:
    cleaned = str(tail or "").strip(_PUNCTUATION)
    changed = True
    while changed and cleaned:
        changed = False
        lowered = cleaned.lower()
        for word in _TARGET_LEADING_WORDS:
            if lowered == word:
                return ""
            if lowered.startswith(word + " "):
                cleaned = cleaned[len(word) :].strip(_PUNCTUATION)
                changed = True
                break
    return cleaned


def _unit_serials(snap: Any) -> Tuple[str, ...]:
    serials = {
        str(unit.unit_serial)
        for unit in snap.unit_links
        if str(unit.unit_serial or "").strip()
    }
    serials |= {
        str(jig.unit_serial)
        for jig in snap.jig_outcomes
        if str(jig.unit_serial or "").strip()
    }
    return tuple(sorted(serials))


def _select_snapshot(repo: Any, snapshots: Sequence[Any], target_norm: str) -> Optional[_Selection]:
    if not target_norm:
        snap = repo.load_lsu_snapshot(str(snapshots[0]["snapshot_id"]))
        return _Selection(snap, (), "latest") if snap is not None else None
    for info in snapshots[:_MAX_SNAPSHOTS_SCANNED]:
        snapshot_id = str(info["snapshot_id"])
        if target_norm in normalize_text(snapshot_id):
            snap = repo.load_lsu_snapshot(snapshot_id)
            if snap is not None:
                return _Selection(snap, (), "snapshot")
    for info in snapshots[:_MAX_SNAPSHOTS_SCANNED]:
        snap = repo.load_lsu_snapshot(str(info["snapshot_id"]))
        if snap is None:
            continue
        matched = tuple(
            serial for serial in _unit_serials(snap) if target_norm in normalize_text(serial)
        )
        if matched:
            return _Selection(snap, matched, "unit")
    return None


def _created_label(snap: Any) -> str:
    created = getattr(snap, "created_at", None)
    if hasattr(created, "strftime"):
        return created.strftime("%d/%m/%Y %H:%M")
    return str(created or "chưa rõ")


def _summary_line(snap: Any, selection: _Selection, result: Any) -> str:
    scope = (
        f"đơn vị {', '.join(selection.unit_serials)}"
        if selection.unit_serials
        else "toàn bộ đơn vị trong gói"
    )
    return (
        f"Dự đoán EWMA (LSU Iris) trên gói dữ liệu “{str(snap.snapshot_id)[:12]}…” "
        f"(tạo {_created_label(snap)}), phạm vi {scope}: đã xử lý "
        f"{result.processed_units}/{result.total_units} đơn vị, "
        f"{result.alerted_units} đơn vị cần kiểm tra. Chỉ đọc — không ghi kho dự đoán."
    )


def _unit_trace_blocks(trace: Any) -> list:
    from aios_habit.prediction_shadow_ui import format_unit_trace_view

    view = format_unit_trace_view(trace)
    blocks = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=(
                f"Hồ sơ đơn vị “{view['unit_serial']}”: {view['label_desc']} — "
                f"{view['fail_desc']}."
            ),
        )
    ]
    lots = view.get("lot_measurements", [])[:_MAX_TRACE_ROWS]
    if lots:
        headers = tuple(lots[0].keys())
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=headers,
                rows=[tuple(str(row.get(key, "")) for key in headers) for row in lots],
                caption="Các lô linh kiện gắn với đơn vị (rút gọn).",
            )
        )
    jigs = view.get("jig_measurements", [])[:_MAX_TRACE_ROWS]
    if jigs:
        headers = tuple(jigs[0].keys())
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=headers,
                rows=[tuple(str(row.get(key, "")) for key in headers) for row in jigs],
                caption="Kết quả đo JIG của đơn vị (rút gọn).",
            )
        )
    return blocks


def _risk_block(result: Any) -> ChatActionBlock:
    from aios_habit.prediction_shadow_ui import format_shadow_risk_view

    assessments = sorted(result.risk_assessments, key=lambda item: str(item.unit_serial))
    if not assessments:
        return ChatActionBlock(
            BLOCK_MARKDOWN,
            text=(
                "Không phát hiện đơn vị nào vượt ngưỡng cảnh báo trong phạm vi đã chạy "
                f"(ngưỡng {_protocol().control_limit_std:.1f} độ lệch chuẩn, "
                f"tối thiểu {_protocol().baseline_minimum_points} điểm mỗi chỉ số)."
            ),
        )
    rows = []
    for index, assessment in enumerate(assessments[:_MAX_RISK_ROWS], start=1):
        view = format_shadow_risk_view(assessment)
        factors = " · ".join(
            f"{factor.get('Mã lô linh kiện', '')} / {factor.get('Thông số kỹ thuật', '')} "
            f"({factor.get('Độ lệch chuẩn', '')})"
            for factor in view.get("factors", [])[:2]
        )
        rows.append(
            (
                str(index),
                str(view.get("unit_serial", "")),
                str(view.get("risk_level", "")),
                factors or "—",
                str(view.get("as_of_time", "") or "—"),
            )
        )
    notes = []
    if len(assessments) > _MAX_RISK_ROWS:
        notes.append(f"Hiện {_MAX_RISK_ROWS}/{len(assessments)} đơn vị rủi ro.")
    if str(result.status) == "stopped":
        notes.append(f"Dừng sau {result.processed_units} đơn vị để giữ phản hồi nhanh.")
    return ChatActionBlock(
        BLOCK_TABLE,
        headers=("#", "Đơn vị", "Mức rủi ro", "Yếu tố chính", "Thời điểm"),
        rows=rows,
        caption=" ".join(notes),
    )


def _run_prediction(selection: _Selection) -> ChatActionOutcome:
    from aios_habit.production_prediction.lsu_iris import join_lsu_trace, normalize_records
    from aios_habit.production_prediction.shadow import ManualShadowRunner

    snap = selection.snap
    normalized = normalize_records(snap)
    traces = join_lsu_trace(normalized)
    if selection.unit_serials:
        traces = {
            serial: trace
            for serial, trace in traces.items()
            if serial in selection.unit_serials
        }
    if not traces:
        return _message("Gói dữ liệu này chưa có đơn vị nào để chạy dự đoán.")

    runner = ManualShadowRunner(protocol=_protocol(), batch_size=10)
    result = runner.run(normalized, traces, stop_after_units=_MAX_UNITS_RUN, repository=None)

    blocks = [ChatActionBlock(BLOCK_MARKDOWN, text=_summary_line(snap, selection, result))]
    if selection.unit_serials:
        first = selection.unit_serials[0]
        trace = traces.get(first)
        if trace is not None:
            blocks.extend(_unit_trace_blocks(trace))
    blocks.append(_risk_block(result))
    return ChatActionOutcome(action=ACTION_NAME, title=ACTION_TITLE, blocks=tuple(blocks))


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    target = _target_from_question(request.question)
    target_norm = normalize_text(target)
    raw_path = str(request.context.get("prediction_db_path") or "").strip()
    db_path = Path(raw_path) if raw_path else _default_prediction_db_path()
    if not db_path.exists():
        return _message(
            "Máy này chưa có kho dự đoán cục bộ nên chưa chạy được dự đoán. "
            "Hãy mở mục Dự đoán (LSU) trong workspace để nạp và đăng ký dữ liệu trước nhé."
        )

    try:
        from aios_habit.production_prediction.repository import ProductionPredictionRepository

        repo = ProductionPredictionRepository(db_path, read_only=True)
        snapshots = list(repo.list_snapshots())
    except Exception:
        return _message(
            "Chưa đọc được kho dự đoán cục bộ lúc này. "
            "Hãy mở mục Dự đoán (LSU) trong workspace để kiểm tra kho, rồi thử lại nhé."
        )
    if not snapshots:
        return _message(
            "Kho dự đoán cục bộ chưa có gói dữ liệu nào được đăng ký. "
            "Hãy mở mục Dự đoán (LSU) trong workspace để nạp và đăng ký dữ liệu trước nhé."
        )

    try:
        selection = _select_snapshot(repo, snapshots, target_norm)
    except Exception:
        return _message("Chưa đọc được gói dữ liệu trong kho dự đoán lúc này. Bạn thử lại sau nhé.")
    if selection is None:
        return _message(
            f"Không tìm thấy gói dữ liệu hoặc mã đơn vị “{target}” trong kho dự đoán cục bộ. "
            f"Kho đang có {len(snapshots)} gói; hãy nêu mã đơn vị (ví dụ SYN_UNIT_001) "
            "hoặc 12 ký tự đầu của mã gói dữ liệu."
        )

    try:
        return _run_prediction(selection)
    except Exception:
        return _message("Chưa chạy được dự đoán trên gói dữ liệu này lúc này. Bạn thử lại sau nhé.")


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Chạy dự đoán rủi ro EWMA (LSU Iris) trên gói dữ liệu đã đăng ký trong kho "
                "dự đoán cục bộ — nối nhóm module production_prediction/prediction_shadow_ui, chỉ đọc."
            ),
        )
    )


register()
