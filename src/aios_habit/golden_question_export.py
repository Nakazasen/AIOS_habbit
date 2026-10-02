"""Batch exporter for golden questions: JSONL + human-readable Markdown + manifest.

Per design doc section 3.3, every batch produces:
1. batch_<id>_questions.jsonl - one JSON per line: question + case context +
   gap context + hypotheses + answer-form schema.
2. batch_<id>_phieu_hoi.md - readable form for batch answering (Copilot 365 /
   a real expert): one section per phenomenon, one empty answer form per
   question following the GoldenAnswer schema exactly.
3. batch_<id>_manifest.json - batch_id, version, created_at, question ids,
   SHA-256 per file and for the whole batch. The importer verifies it.

CLI:
    python -m aios_habit.golden_question_export --phenomena-json FILE --out-dir DIR
    python -m aios_habit.golden_question_export --error-db error_cases_dict.db --out-dir DIR
    python -m aios_habit.golden_question_export --fixture --out-dir DIR

Pilot scope: 5 REAL F CALL phenomena from the error DB. On machines without
the real DB, --fixture builds a batch from clearly-labeled SYNTHETIC data
(never presented as real).

Python 3.11 compatible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from aios_habit.golden_question_generator import (
    PhenomenonContext,
    Hypothesis,
    default_gap_for_phenomenon,
    generate_candidates,
)
from aios_habit.golden_question_schema import (
    GoldenQuestion,
    GoldenSchemaError,
    answer_form_json_schema,
)
from aios_habit.golden_question_scorer import SelectionResult, select_top_k
from aios_habit.knowledge_coverage import KnowledgeGapCandidate


class GoldenExportError(ValueError):
    """Raised when a batch cannot be exported."""


PILOT_QUESTIONS_PER_PHENOMENON = 3
MIN_SCORE_DEFAULT = 55.0


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExportedBatch:
    """Paths and summary of one exported batch."""

    batch_id: str
    version: int
    out_dir: Path
    questions_path: Path
    form_path: Path
    manifest_path: Path
    total_questions: int
    per_phenomenon: Tuple[Tuple[str, int], ...]
    constraints_met: Tuple[Tuple[str, Dict[str, bool]], ...]


def _question_jsonl_line(
    q: GoldenQuestion,
    ctx: PhenomenonContext,
    gap: KnowledgeGapCandidate,
    batch_version: int,
) -> str:
    payload = {
        "batch_id": ctx.batch_id,
        "batch_version": batch_version,
        "question": q.to_dict(),
        "case_context": {
            "error_code": ctx.error_code,
            "error_group": ctx.error_group,
            "phenomenon": ctx.phenomenon,
            "model_line_station": ctx.model_line_station,
            "case_ids": list(ctx.case_ids),
        },
        "gap_context": {
            "gap_id": gap.gap_id,
            "gap_type": gap.gap_type,
            "title": gap.title,
            "priority": gap.priority,
        },
        "hypotheses": [
            {"hypothesis_id": h.hypothesis_id, "text": h.text} for h in ctx.hypotheses
        ],
        "hypothesis_source_note": ctx.hypothesis_source_note,
        "answer_form_schema": answer_form_json_schema(),
    }
    return json.dumps(payload, ensure_ascii=False)


# Empty-form hints per GoldenAnswer field (rendered in the Markdown form).
_FORM_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("answer_text", "Nội dung trả lời (ít nhất 20 ký tự)"),
    ("answer_state", "answered / uncertain / unknown"),
    ("hypotheses", "Các giả thuyết nguyên nhân (bắt buộc khi answered)"),
    ("causal_mechanism", "Cơ chế gây lỗi dạng A → B → C (bắt buộc khi answered)"),
    ("m4_branches", "Nhóm 4M: Man / Machine / Material / Method (bắt buộc khi answered)"),
    ("evidence_to_collect", "Bằng chứng cần thu thập để kiểm chứng (bắt buộc khi answered)"),
    ("confirm_criteria", "Tiêu chí XÁC NHẬN giả thuyết (bắt buộc khi answered)"),
    ("refute_criteria", "Tiêu chí BÁC BỎ giả thuyết (khuyến nghị)"),
    ("discriminate_notes", "Cách phân biệt với giả thuyết khác (bắt buộc nếu câu loại discriminator)"),
    ("thresholds", "Danh sách {name, value, unit, tolerance} nếu có"),
    ("exceptions", "Ngoại lệ đã biết nếu có"),
    ("temp_countermeasure", "Đối sách tạm thời (được ghi 'chua_xac_dinh' nếu chưa rõ)"),
    ("perm_countermeasure", "Đối sách lâu dài (được ghi 'chua_xac_dinh' nếu chưa rõ)"),
    ("recurrence_condition", "Điều kiện tái phát (khuyến nghị)"),
    ("related_cases", "Mã ca liên quan nếu có"),
    ("related_docs", "Tài liệu/SOP liên quan nếu có"),
    ("needs_expert_review", "Liệt kê field cần chuyên gia phản hồi (bắt buộc khi chưa chắc chắn)"),
    ("confidence", "Độ tự tin 0.0–1.0"),
)


def _render_form_markdown(
    batch_id: str,
    selections: Sequence[Tuple[PhenomenonContext, SelectionResult]],
    data_source_label: str,
) -> str:
    """Render the human-readable batch form (Vietnamese)."""
    lines: List[str] = []
    lines.append("# Phiếu câu hỏi vàng — batch %s" % batch_id)
    lines.append("")
    lines.append("Nguồn hiện tượng: %s" % data_source_label)
    lines.append("")
    lines.append(
        "> Mỗi hiện tượng trả lời trong MỘT lượt chat. "
        "Điền đúng schema form bên dưới cho từng câu hỏi. "
        "Đáp án 'answered' mà thiếu nhân quả (giả thuyết, cơ chế, 4M) hoặc "
        "bằng chứng (cần thu thập gì, tiêu chí xác nhận) sẽ bị từ chối khi nhập."
    )
    lines.append("")
    lines.append(
        "> Khi hỏi trên Copilot 365: bật chế độ **Work IQ** và chế độ suy nghĩ "
        "**Think deeper** trước khi paste phiếu."
    )
    lines.append("")
    for ctx, selection in selections:
        lines.append("## Hiện tượng: %s — %s" % (ctx.error_code, ctx.phenomenon))
        lines.append("")
        if ctx.model_line_station:
            lines.append("Model/line/công đoạn: %s" % ctx.model_line_station)
            lines.append("")
        lines.append("Mã ca: %s" % ", ".join(ctx.case_ids))
        lines.append("")
        if ctx.hypotheses:
            lines.append("Giả thuyết nguyên nhân đã ghi:")
            lines.append("")
            for h in ctx.hypotheses:
                lines.append("- %s: %s" % (h.hypothesis_id, h.text))
            lines.append("")
        for order, q in enumerate(selection.selected, 1):
            lines.append("### Câu %d — %s" % (order, q.question_id))
            lines.append("")
            lines.append("**Câu hỏi:** %s" % q.text)
            lines.append("")
            lines.append("Mục tiêu: %s" % q.muc_tieu)
            lines.append("")
            lines.append("Loại câu hỏi: `%s` — Bằng chứng kỳ vọng: %s" % (
                q.loai_cau_hoi,
                ", ".join(q.expected_evidence) if q.expected_evidence else "—",
            ))
            lines.append("")
            lines.append("Điểm: %.1f (D=%.2f G=%.2f E=%.2f W=%.2f N=%.2f F=%.2f)" % (
                q.diem,
                q.diem_thanh_phan.get("D", 0.0),
                q.diem_thanh_phan.get("G", 0.0),
                q.diem_thanh_phan.get("E", 0.0),
                q.diem_thanh_phan.get("W", 0.0),
                q.diem_thanh_phan.get("N", 0.0),
                q.diem_thanh_phan.get("F", 0.0),
            ))
            lines.append("")
            lines.append("**Phiếu trả lời (để trống, điền theo đúng schema):**")
            lines.append("")
            lines.append("```")
            lines.append("answer_id: GA-%s-1" % q.question_id)
            lines.append("question_id: %s" % q.question_id)
            lines.append("gap_id: %s" % q.target_gap_id)
            lines.append("case_ids: %s" % ", ".join(q.target_case_ids))
            lines.append("error_code: %s" % ctx.error_code)
            lines.append("error_group: %s" % ctx.error_group)
            lines.append("phenomenon: %s" % ctx.phenomenon)
            lines.append("question_loai: %s" % q.loai_cau_hoi)
            for fname, hint in _FORM_FIELDS:
                lines.append("%s:   # %s" % (fname, hint))
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def export_batch(
    batch_id: str,
    phenomena: Sequence[PhenomenonContext],
    out_dir: Path,
    questions_per_phenomenon: int = PILOT_QUESTIONS_PER_PHENOMENON,
    min_score: float = MIN_SCORE_DEFAULT,
    version: int = 1,
    data_source_label: str = "DB lỗi (5 hiện tượng F CALL thật)",
) -> ExportedBatch:
    """Generate, score, select and export one full batch."""
    if not phenomena:
        raise GoldenExportError("Batch cần ít nhất 1 hiện tượng.")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    selections: List[Tuple[PhenomenonContext, SelectionResult]] = []
    next_index = 1  # question ids run batch-wide: GQ-<batch>-01, -02, ...
    for ctx in phenomena:
        gaps = list(ctx.gaps) or [default_gap_for_phenomenon(ctx)]
        gap_by_id = {g.gap_id: g for g in gaps}
        ctx_with_gaps = PhenomenonContext(
            batch_id=ctx.batch_id,
            error_code=ctx.error_code,
            phenomenon=ctx.phenomenon,
            case_ids=ctx.case_ids,
            error_group=ctx.error_group,
            model_line_station=ctx.model_line_station,
            gaps=tuple(gaps),
            hypotheses=ctx.hypotheses,
            hypothesis_source_note=ctx.hypothesis_source_note,
        )
        candidates = generate_candidates(ctx_with_gaps, start_index=next_index)
        next_index += len(candidates)
        selection = select_top_k(
            ctx_with_gaps, candidates, k=questions_per_phenomenon, min_score=min_score
        )
        selections.append((ctx_with_gaps, selection))

    # Batch-wide uniqueness guard for question ids.
    seen_ids = set()
    for _, selection in selections:
        for q in selection.selected:
            if q.question_id in seen_ids:
                raise GoldenExportError(
                    "Trùng question_id trong batch: %s." % q.question_id
                )
            seen_ids.add(q.question_id)

    questions_path = out / ("batch_%s_questions.jsonl" % batch_id)
    form_path = out / ("batch_%s_phieu_hoi.md" % batch_id)
    manifest_path = out / ("batch_%s_manifest.json" % batch_id)

    question_ids: List[str] = []
    with questions_path.open("w", encoding="utf-8") as handle:
        for ctx, selection in selections:
            gap_by_id = {g.gap_id: g for g in ctx.gaps}
            for q in selection.selected:
                gap = gap_by_id[q.target_gap_id]
                handle.write(_question_jsonl_line(q, ctx, gap, version) + "\n")
                question_ids.append(q.question_id)

    form_path.write_text(
        _render_form_markdown(batch_id, selections, data_source_label), encoding="utf-8"
    )

    files = []
    for path in (questions_path, form_path):
        files.append(
            {
                "name": path.name,
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    batch_digest = hashlib.sha256(
        "|".join(sorted(f["sha256"] for f in files)).encode("utf-8")
    ).hexdigest()
    manifest = {
        "batch_id": batch_id,
        "version": version,
        "created_at": _utc_now_iso(),
        "question_ids": question_ids,
        "files": files,
        "batch_sha256": batch_digest,
        "note": "Importer kiểm tra manifest trước khi nhập đáp án.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return ExportedBatch(
        batch_id=batch_id,
        version=version,
        out_dir=out,
        questions_path=questions_path,
        form_path=form_path,
        manifest_path=manifest_path,
        total_questions=len(question_ids),
        per_phenomenon=tuple((ctx.phenomenon, len(sel.selected)) for ctx, sel in selections),
        constraints_met=tuple((ctx.error_code, dict(sel.constraints_met)) for ctx, sel in selections),
    )


# ---------------------------------------------------------------------------
# Phenomena loading: real error DB (best effort) or explicit JSON / fixture
# ---------------------------------------------------------------------------

FIXTURE_LABEL = "FIXTURE — DỮ LIỆU GIẢ LẬP CHO TEST, KHÔNG PHẢI DỮ LIỆU THẬT"


def fixture_phenomena(batch_id: str) -> List[PhenomenonContext]:
    """Five clearly-labeled SYNTHETIC phenomena for testing on machines
    without the real error DB. Never presented as real data."""
    specs = [
        ("F100", "Máy dừng đột ngột khi đang chạy, màn hình báo F100", ("CASE-FIX-001", "CASE-FIX-002")),
        ("F205", "Băng tải kẹt sản phẩm tại vị trí chuyển tiếp", ("CASE-FIX-003",)),
        ("F310", "Cảm biến không nhận tín hiệu sau khi đổi lot", ("CASE-FIX-004", "CASE-FIX-005")),
        ("F412", "Nhiệt độ buồng sấy vượt ngưỡng cài đặt", ("CASE-FIX-006",)),
        ("F520", "Màn hình cảm ứng đơ, không nhận thao tác", ("CASE-FIX-007", "CASE-FIX-008")),
    ]
    out: List[PhenomenonContext] = []
    for code, phenomenon, case_ids in specs:
        out.append(
            PhenomenonContext(
                batch_id=batch_id,
                error_code=code,
                phenomenon=phenomenon,
                case_ids=tuple(case_ids),
                hypotheses=(
                    # Hypothesis ids are namespaced per phenomenon so pairs never
                    # collide across phenomena in quality measurement (M4).
                    Hypothesis("H1-%s" % code, "Giả thuyết A cho %s (giả lập)" % code),
                    Hypothesis("H2-%s" % code, "Giả thuyết B cho %s (giả lập)" % code),
                ),
                hypothesis_source_note=FIXTURE_LABEL,
            )
        )
    return out


def load_phenomena_json(path: Path, batch_id: str) -> List[PhenomenonContext]:
    """Load phenomena from an explicit JSON file (produced from the real DB).

    Expected format: {"phenomena": [ {"error_code":..., "phenomenon":...,
    "case_ids":[...], "error_group":..., "model_line_station":...,
    "hypotheses":[{"hypothesis_id":..., "text":...}], "gaps":[...] (optional) } ]}.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("phenomena", data) if isinstance(data, dict) else data
    out: List[PhenomenonContext] = []
    for item in items:
        gaps = []
        for g in item.get("gaps") or []:
            gaps.append(
                KnowledgeGapCandidate(
                    gap_id=str(g["gap_id"]),
                    collection_id=str(g.get("collection_id", "error_cases")),
                    scope=str(g.get("scope", item.get("error_group", "F CALL"))),
                    title=str(g["title"]),
                    description=str(g.get("description", g["title"])),
                    gap_type=str(g.get("gap_type", "missing_condition")),
                    evidence_refs=tuple(str(x) for x in g.get("evidence_refs", item.get("case_ids", []))),
                    priority=str(g.get("priority", "medium")),
                )
            )
        out.append(
            PhenomenonContext(
                batch_id=batch_id,
                error_code=str(item.get("error_code", "UNKNOWN")),
                phenomenon=str(item["phenomenon"]),
                case_ids=tuple(str(x) for x in item["case_ids"]),
                error_group=str(item.get("error_group", "F CALL")),
                model_line_station=str(item.get("model_line_station", "")),
                gaps=tuple(gaps),
                hypotheses=tuple(
                    Hypothesis(str(h["hypothesis_id"]), str(h["text"]))
                    for h in (item.get("hypotheses") or [])
                ),
                hypothesis_source_note=str(item.get("hypothesis_source_note", "")),
            )
        )
    return out


def extract_phenomena_from_error_db(
    db_path: Path, batch_id: str, limit: int = 5
) -> List[PhenomenonContext]:
    """Best-effort extraction of F CALL phenomena from the real error DB.

    The real DB schema lives on the owner's machines; this probes tables for
    code/group/phenomenon-like columns and filters group LIKE '%F CALL%'.
    Raises GoldenExportError with guidance when the schema is not recognized.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        if not tables:
            raise GoldenExportError("DB không có bảng nào: %s" % db_path)

        def _columns(table: str) -> List[str]:
            return [row[1] for row in conn.execute("PRAGMA table_info(%s)" % table)]

        def _find(columns: List[str], *needles: str) -> Optional[str]:
            lowered = {c.lower(): c for c in columns}
            for needle in needles:
                for key, original in lowered.items():
                    if needle in key:
                        return original
            return None

        best = None
        for table in tables:
            cols = _columns(table)
            code_col = _find(cols, "error_code", "errorcode", "ma_loi")
            phen_col = _find(cols, "phenomenon", "hien_tuong", "mo_ta", "description")
            group_col = _find(cols, "error_group", "nhom_loi", "group")
            if code_col and phen_col:
                count = conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
                score = (2 if group_col else 0) + (1 if count > 0 else 0)
                if best is None or (score, count) > (best[0], best[1]):
                    best = (score, count, table, code_col, phen_col, group_col)
        if best is None:
            raise GoldenExportError(
                "Không nhận ra schema DB lỗi (cần cột mã lỗi + hiện tượng). "
                "Hãy xuất phenomena ra JSON rồi dùng --phenomena-json."
            )
        _, _, table, code_col, phen_col, group_col = best
        if group_col:
            rows = conn.execute(
                "SELECT %s, %s, %s FROM %s WHERE %s LIKE '%%F CALL%%' "
                "GROUP BY %s, %s LIMIT %d"
                % (code_col, phen_col, group_col, table, group_col, code_col, phen_col, limit * 3)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT %s, %s FROM %s GROUP BY %s, %s LIMIT %d"
                % (code_col, phen_col, table, code_col, phen_col, limit * 3)
            ).fetchall()
            rows = [(r[0], r[1], "F CALL") for r in rows]

        phenomena: List[PhenomenonContext] = []
        seen = set()
        for code, phenomenon, group in rows:
            phenomenon = (phenomenon or "").strip()
            if not phenomenon or phenomenon in seen:
                continue
            seen.add(phenomenon)
            phenomena.append(
                PhenomenonContext(
                    batch_id=batch_id,
                    error_code=str(code or "UNKNOWN").strip(),
                    phenomenon=phenomenon,
                    case_ids=("%s:%s" % (table, str(code or "UNKNOWN").strip()),),
                    error_group=str(group or "F CALL").strip(),
                    hypothesis_source_note="Trích từ DB lỗi %s (bảng %s)" % (db_path.name, table),
                )
            )
            if len(phenomena) >= limit:
                break
        if not phenomena:
            raise GoldenExportError(
                "Không tìm thấy hiện tượng F CALL nào trong DB %s (bảng %s)." % (db_path, table)
            )
        return phenomena
    finally:
        conn.close()


def _default_batch_id() -> str:
    return "KB-%s-FCALL-01" % datetime.now(timezone.utc).strftime("%Y%m%d")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Xuất batch câu hỏi vàng: JSONL + phiếu Markdown + manifest SHA-256."
    )
    parser.add_argument("--batch-id", default=None, help="Mã batch (mặc định sinh theo ngày).")
    parser.add_argument("--out-dir", required=True, help="Thư mục ghi batch.")
    parser.add_argument("--phenomena-json", default=None,
                        help="File JSON liệt kê 5 hiện tượng F CALL thật.")
    parser.add_argument("--error-db", default=None,
                        help="DB lỗi sqlite để trích 5 hiện tượng F CALL (best-effort).")
    parser.add_argument("--fixture", action="store_true",
                        help="Dùng dữ liệu GIẢ LẬP gắn nhãn FIXTURE (chỉ cho test).")
    parser.add_argument("--limit", type=int, default=5, help="Số hiện tượng (mặc định 5).")
    parser.add_argument("--k", type=int, default=PILOT_QUESTIONS_PER_PHENOMENON,
                        help="Số câu hỏi mỗi hiện tượng (mặc định 3).")
    parser.add_argument("--min-score", type=float, default=MIN_SCORE_DEFAULT,
                        help="Ngưỡng điểm tối thiểu (mặc định 55).")
    args = parser.parse_args(argv)

    batch_id = args.batch_id or _default_batch_id()
    try:
        if args.fixture:
            phenomena = fixture_phenomena(batch_id)
            label = FIXTURE_LABEL
        elif args.phenomena_json:
            phenomena = load_phenomena_json(Path(args.phenomena_json), batch_id)
            label = "File phenomena JSON: %s" % args.phenomena_json
        elif args.error_db:
            phenomena = extract_phenomena_from_error_db(Path(args.error_db), batch_id, args.limit)
            label = "DB lỗi thật: %s" % args.error_db
        else:
            print("Thiếu nguồn hiện tượng: dùng --phenomena-json, --error-db hoặc --fixture.",
                  file=sys.stderr)
            return 2
        exported = export_batch(
            batch_id,
            phenomena[: args.limit],
            Path(args.out_dir),
            questions_per_phenomenon=args.k,
            min_score=args.min_score,
            data_source_label=label,
        )
    except (GoldenExportError, GoldenSchemaError) as exc:
        print("Lỗi xuất batch: %s" % exc, file=sys.stderr)
        return 1

    print("Đã xuất batch %s: %d câu hỏi." % (exported.batch_id, exported.total_questions))
    print("  JSONL:    %s" % exported.questions_path)
    print("  Phiếu:    %s" % exported.form_path)
    print("  Manifest: %s" % exported.manifest_path)
    for phenomenon, count in exported.per_phenomenon:
        print("  - %s: %d câu" % (phenomenon[:60], count))
    for code, met in exported.constraints_met:
        missing = [k for k, v in met.items() if not v]
        if missing:
            print("  CẢNH BÁO %s: chưa đạt ràng buộc %s" % (code, ", ".join(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
