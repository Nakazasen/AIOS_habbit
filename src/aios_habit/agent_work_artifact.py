"""Local, evidence-bound artifacts for the daily-work assistant MVP."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_habit.excel_extractors import extract_excel


@dataclass(frozen=True)
class FactoryErrorReportResult:
    payload: dict[str, Any]
    report_path: Path
    status_vi: str
    approval_required: bool
    previous_content: bytes | None

    def undo(self) -> None:
        undo_factory_error_report(self)


@dataclass(frozen=True)
class ProcessDesignReviewResult:
    payload: dict[str, Any]
    report_path: Path
    status_vi: str
    approval_required: bool
    previous_content: bytes | None

    def undo(self) -> None:
        undo_factory_error_report(self)


@dataclass(frozen=True)
class _TabularAnalysis:
    visual: dict[str, Any] | None
    missing_vi: tuple[str, ...]


@dataclass(frozen=True)
class _Constraint:
    kind: str
    low: float | None
    high: float | None
    unit: str
    locator: str
    raw_line: str


_TEXT_SUFFIXES = {".log", ".txt", ".md"}
_TABULAR_SUFFIXES = {".csv", ".xlsx", ".xlsm"}
_TIME_HINTS = ("time", "date", "day", "datetime", "timestamp", "ngay", "thoi", "gio")
_UNIT_HINTS = ("unit", "donvi", "uom")
_INSPECTED_HINTS = ("inspect", "checked", "sample", "total", "kiem", "mau")
_METRIC_HINTS = ("defect", "error", "fault", "failure", "reject", "loi", "hong", "rate", "ratio")
_MAX_HINTS = ("khong vuot", "khong qua", "toi da", "maximum", "max", "not exceed", "<=")
_MIN_HINTS = ("it nhat", "toi thieu", "minimum", "min", ">=")
_QUANTITY_RE = re.compile(r"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>%|[A-Za-zÀ-ỹµ]+)", re.IGNORECASE)
_RANGE_RE = re.compile(
    r"(?P<low>-?\d+(?:[.,]\d+)?)\s*(?:%|[A-Za-zÀ-ỹµ]+)?\s*(?:-|–|đến|to)\s*"
    r"(?P<high>-?\d+(?:[.,]\d+)?)\s*(?P<unit>%|[A-Za-zÀ-ỹµ]+)",
    re.IGNORECASE,
)


# Units can be Vietnamese, Latin, symbols, or unit strings from the source.
# The parser does not privilege any particular engineering unit.
_QUANTITY_RE = re.compile(r"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>%|[^\d\s,.;:()]+)", re.IGNORECASE)
_RANGE_RE = re.compile(
    r"(?P<low>-?\d+(?:[.,]\d+)?)\s*(?:%|[^\d\s,.;:()]+)?\s*(?:-|–|đến|to)\s*"
    r"(?P<high>-?\d+(?:[.,]\d+)?)\s*(?P<unit>%|[^\d\s,.;:()]+)",
    re.IGNORECASE,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_reference(path: Path, locator: str = "toàn bộ tệp") -> dict[str, str]:
    return {"source_file": path.name, "locator": locator, "digest": _sha256(path.read_bytes())}


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9%]+", "", without_marks.replace("đ", "d"))


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(" ", ""))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _display_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _header_unit(header: str) -> str:
    parenthesized = re.search(r"\(([^)]+)\)", header)
    if parenthesized:
        return parenthesized.group(1).strip()
    return "%" if "%" in header else ""


def _find_header(headers: list[str], hints: tuple[str, ...]) -> str | None:
    for header in headers:
        normalized = _normalized(header)
        if any(hint in normalized for hint in hints):
            return header
    return None


def _analyse_table(
    *, path: Path, headers: list[str], rows: list[dict[str, Any]], filters: str
) -> _TabularAnalysis:
    if not headers or not rows:
        return _TabularAnalysis(None, ("bảng không có dòng dữ liệu",))

    time_header = _find_header(headers, _TIME_HINTS)
    unit_header = _find_header(headers, _UNIT_HINTS)
    inspected_header = _find_header(headers, _INSPECTED_HINTS)
    numeric_headers = [
        header for header in headers
        if header != time_header and any(_number(row.get(header, "")) is not None for row in rows)
    ]
    metric_header = next(
        (header for header in numeric_headers if any(hint in _normalized(header) for hint in _METRIC_HINTS)),
        None,
    )
    if metric_header is None:
        metric_header = next(
            (header for header in numeric_headers if header != inspected_header),
            numeric_headers[0] if numeric_headers else None,
        )

    missing: list[str] = []
    if time_header is None:
        missing.append("cột thời gian hoặc ngày")
    if metric_header is None:
        missing.append("cột số để theo dõi")
    if time_header is None or metric_header is None:
        return _TabularAnalysis(None, tuple(missing))

    unit = ""
    if unit_header:
        unit = next((str(row.get(unit_header, "")).strip() for row in rows if str(row.get(unit_header, "")).strip()), "")
    unit = unit or _header_unit(metric_header)
    if not unit:
        return _TabularAnalysis(None, ("đơn vị của cột số",))

    points: list[tuple[str, float, float | None]] = []
    for row in rows:
        moment = str(row.get(time_header, "")).strip()
        metric = _number(row.get(metric_header, ""))
        if not moment or metric is None:
            continue
        inspected = _number(row.get(inspected_header, "")) if inspected_header else None
        points.append((moment, metric, inspected))
    if not points:
        return _TabularAnalysis(None, (f"giá trị số hợp lệ trong cột {metric_header}",))

    labels = ", ".join(point[0][-12:].replace(",", " ") for point in points)
    values = ", ".join(_display_number(point[1]) for point in points)
    inspected_total = sum(point[2] or 0 for point in points)
    peak = max(points, key=lambda point: point[1])
    return _TabularAnalysis(
        {
            "title_vi": f"{metric_header} theo {time_header}",
            "type": "mermaid_xychart",
            "source_refs": [path.name],
            "source_columns": [time_header, metric_header],
            "units": unit,
            "filters": filters,
            "aggregation": "giữ nguyên từng mốc thời gian",
            "data_digest": _sha256(path.read_bytes()),
            "defect_total": sum(point[1] for point in points),
            "inspected_total": inspected_total,
            "peak_time": peak[0],
            "metric_label": metric_header,
            "content": "\n".join(
                (
                    "xychart-beta",
                    f'    title "{metric_header} theo {time_header}"',
                    f"    x-axis [{labels}]",
                    f'    y-axis "{metric_header} ({unit})" 0 --> {_display_number(max(point[1] for point in points) + 1)}',
                    f"    line [{values}]",
                )
            ),
        },
        (),
    )


def _csv_analysis(path: Path) -> _TabularAnalysis:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    headers = list(rows[0]) if rows else []
    return _analyse_table(path=path, headers=headers, rows=rows, filters="toàn bộ bảng CSV nguồn")


def _xlsx_analysis(path: Path) -> _TabularAnalysis:
    extraction = extract_excel(path, include_images=False, include_charts=True)
    if not extraction.succeeded:
        return _TabularAnalysis(None, ("bảng Excel có thể đọc được",))
    missing: list[str] = []
    for region in extraction.regions:
        headers = list(region.headers)
        data_rows = region.rows[len(region.header_rows):]
        rows = [dict(zip(headers, row)) for row in data_rows if len(row) >= len(headers)]
        analysis = _analyse_table(
            path=path,
            headers=headers,
            rows=rows,
            filters=f"sheet {region.sheet}, vùng {region.cell_range}",
        )
        if analysis.visual:
            analysis.visual["excel_chart_metadata"] = [
                {"sheet": chart.sheet, "title": chart.title, "references": list(chart.references)}
                for chart in extraction.charts
            ]
            return analysis
        missing.extend(analysis.missing_vi)
    return _TabularAnalysis(None, tuple(dict.fromkeys(missing)) or ("bảng dữ liệu phù hợp",))


def _text_excerpt(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    excerpt = next((line for line in lines if line and not line.startswith("#")), "")
    return excerpt[:280]


def _digest_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256(canonical)


def create_factory_error_report(
    *, source_paths: list[str | Path], output_dir: str | Path, work_id: str
) -> FactoryErrorReportResult:
    paths = [Path(item) for item in source_paths]
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("Cần ít nhất một nguồn cục bộ để tạo báo cáo lỗi.")

    references = [_relative_reference(path) for path in paths]
    excerpts = [f"{path.name}: “{_text_excerpt(path)}”" for path in paths if path.suffix.lower() in _TEXT_SUFFIXES and _text_excerpt(path)]
    phenomenon = " ".join(excerpts[:2]) or "Chưa có đoạn văn bản mô tả hiện tượng trong các nguồn đã chọn."
    table_analyses = [
        _csv_analysis(path) if path.suffix.lower() == ".csv" else _xlsx_analysis(path)
        for path in paths if path.suffix.lower() in _TABULAR_SUFFIXES
    ]
    visual = next((analysis.visual for analysis in table_analyses if analysis.visual), None)
    missing = tuple(dict.fromkeys(item for analysis in table_analyses for item in analysis.missing_vi))

    if visual:
        total = visual["defect_total"]
        inspected = visual["inspected_total"]
        unit = visual["units"]
        impact = f"Nguồn ghi tổng {_display_number(total)} {unit} ở cột {visual['metric_label']}"
        if inspected:
            impact += f" trên {_display_number(inspected)} mẫu hoặc lượt kiểm."
        else:
            impact += "."
        analysis = f"Giá trị cao nhất ở mốc {visual['peak_time']}; biểu đồ giữ nguyên từng mốc từ {visual['source_refs'][0]}."
        uncertainty = "Nguồn chưa đủ để kết luận nguyên nhân gốc."
    else:
        impact = "Chưa có bằng chứng số đủ để định lượng phạm vi ảnh hưởng."
        analysis = "Báo cáo chỉ tóm tắt các đoạn và bảng có trong nguồn đã chọn."
        uncertainty = (
            "Thiếu " + ", ".join(missing) + "."
            if missing else "Chưa có bảng số liệu trong các nguồn đã chọn."
        )

    actions = []
    if excerpts:
        actions.append("Đối chiếu lại đoạn được trích trong nguồn trước khi kết luận nguyên nhân.")
    if visual:
        actions.append(f"Kiểm tra mốc {visual['peak_time']} trong nguồn {visual['source_refs'][0]}.")
    if not actions:
        actions.append("Bổ sung nguồn mô tả hoặc bảng số liệu trước khi phân tích tiếp.")
    payload: dict[str, Any] = {
        "schema_version": "aios_factory_error_report_v1",
        "artifact_id": f"bao-cao-{work_id.lower()}",
        "work_id": work_id,
        "title_vi": "Báo cáo lỗi kỹ thuật",
        "status": "completed",
        "phenomenon_vi": phenomenon,
        "impact_vi": impact,
        "evidence": references,
        "analysis_vi": analysis,
        "hypotheses": [{
            "statement_vi": "Cần đối chiếu thêm nguồn trước khi kết luận nguyên nhân.",
            "evidence_status": "proposal",
        }],
        "uncertainties_vi": uncertainty,
        "next_actions_vi": actions[:5],
        "visuals": [visual] if visual else [],
        "created_at": _utc_now(),
    }
    payload["artifact_digest"] = _digest_payload(payload)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / f"bao_cao_loi_{work_id}.md"
    previous_content = report_path.read_bytes() if report_path.exists() else None
    lines = [
        f"# {payload['title_vi']}", "", "## Hiện tượng", payload["phenomenon_vi"], "",
        "## Ảnh hưởng", payload["impact_vi"], "", "## Phân tích", payload["analysis_vi"], "",
        "## Phần chưa chắc chắn", payload["uncertainties_vi"], "", "## Việc nên làm tiếp",
        *[f"- {item}" for item in payload["next_actions_vi"]], "", "## Nguồn",
        *[f"- {item['source_file']} — {item['locator']}" for item in references],
    ]
    if visual:
        lines.extend(("", "## Biểu đồ có căn cứ", "```mermaid", visual["content"], "```"))
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return FactoryErrorReportResult(payload, report_path, "Đã xong", False, previous_content)


def undo_factory_error_report(result: FactoryErrorReportResult | ProcessDesignReviewResult) -> None:
    if result.previous_content is None:
        result.report_path.unlink(missing_ok=True)
    else:
        result.report_path.write_bytes(result.previous_content)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _process_source_roles(paths: list[Path]) -> tuple[list[Path], list[Path], list[Path]]:
    guideline_words = ("guideline", "standard", "tieuchuan", "quychuan", "quydinh")
    design_words = ("sop", "thietke", "huongdan", "design")
    guidelines = [path for path in paths if any(word in _normalized(path.name) for word in guideline_words)]
    if not guidelines:
        return [], [], paths
    designs = [path for path in paths if path not in guidelines and any(word in _normalized(path.name) for word in design_words)]
    contexts = [path for path in paths if path not in guidelines and path not in designs]
    return guidelines, designs, contexts


def _source_lines(path: Path) -> list[tuple[int, str]]:
    return [(index, line.strip()) for index, line in enumerate(_read_text(path).splitlines(), start=1) if line.strip()]


def _quantity_pairs(line: str) -> list[tuple[float, str]]:
    return [(_number(match.group("value")) or 0.0, match.group("unit").casefold()) for match in _QUANTITY_RE.finditer(line)]


def _constraints(path: Path) -> tuple[list[_Constraint], list[tuple[int, str]]]:
    constraints: list[_Constraint] = []
    unmatched: list[tuple[int, str]] = []
    for line_number, line in _source_lines(path):
        normalized = _normalized(line)
        range_match = _RANGE_RE.search(line)
        if range_match:
            constraints.append(_Constraint(
                "range", _number(range_match.group("low")), _number(range_match.group("high")),
                range_match.group("unit").casefold(), f"Dòng {line_number}", line,
            ))
            continue
        pairs = _quantity_pairs(line)
        if not pairs:
            continue
        value, unit = pairs[0]
        if any(token and token in normalized for token in (_normalized(hint) for hint in _MAX_HINTS)):
            constraints.append(_Constraint("max", None, value, unit, f"Dòng {line_number}", line))
        elif any(token and token in normalized for token in (_normalized(hint) for hint in _MIN_HINTS)):
            constraints.append(_Constraint("min", value, None, unit, f"Dòng {line_number}", line))
        else:
            unmatched.append((line_number, line))
    return constraints, unmatched


def _design_values(path: Path) -> list[tuple[float, str, str]]:
    values: list[tuple[float, str, str]] = []
    for line_number, line in _source_lines(path):
        values.extend((value, unit, f"Dòng {line_number}") for value, unit in _quantity_pairs(line))
    return values


def _version_markers(path: Path) -> set[str]:
    text = f"{path.stem}\n{_read_text(path)}"
    markers = {
        marker.casefold()
        for marker in re.findall(r"(?:phiên\s*bản|version|ver\.?|\bv)\s*[-:]?\s*(\d+(?:\.\d+)*)", text, flags=re.IGNORECASE)
    }
    markers.update(re.findall(r"(?:^|[_\-\s])v(\d+(?:\.\d+)*)", path.stem, flags=re.IGNORECASE))
    return {marker.casefold() for marker in markers}


def _comparison_statement(constraint: _Constraint, value: float, verdict: str) -> str:
    actual = f"{_display_number(value)} {constraint.unit}"
    if constraint.kind == "range":
        expected = f"{_display_number(constraint.low or 0)}–{_display_number(constraint.high or 0)} {constraint.unit}"
    elif constraint.kind == "max":
        expected = f"không quá {_display_number(constraint.high or 0)} {constraint.unit}"
    else:
        expected = f"ít nhất {_display_number(constraint.low or 0)} {constraint.unit}"
    return f"Giá trị thiết kế {actual} {'phù hợp' if verdict == 'pass' else 'không phù hợp'} với giới hạn {expected}."


def create_process_design_review(
    *, source_paths: list[str | Path], output_dir: str | Path, work_id: str
) -> ProcessDesignReviewResult:
    paths = [Path(item) for item in source_paths]
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("Cần ít nhất một tài liệu cục bộ để rà soát thiết kế công đoạn.")

    guidelines, designs, contexts = _process_source_roles(paths)
    guideline_refs = [_relative_reference(path) for path in guidelines]
    design_refs = [_relative_reference(path) for path in designs]
    context_refs = [_relative_reference(path) for path in contexts]
    checks: list[dict[str, Any]] = []

    if not guidelines or not designs:
        checks.append({
            "check_id": "CHECK-ROLE-001", "guideline_locator": None, "design_locator": None,
            "verdict": "insufficient", "statement_vi": "Chưa tách được tài liệu luật và bản thiết kế — hãy chọn thêm Guideline.",
            "source_refs": [], "evidence_status": "insufficient",
        })
    else:
        for guideline in guidelines:
            constraints, unmatched_lines = _constraints(guideline)
            design_values = [(design, *value) for design in designs for value in _design_values(design)]
            for index, constraint in enumerate(constraints, start=1):
                matched = next((item for item in design_values if item[2] == constraint.unit), None)
                if matched is None:
                    checks.append({
                        "check_id": f"CHECK-{guideline.stem.upper()}-{index}",
                        "guideline_locator": constraint.locator, "design_locator": None,
                        "verdict": "insufficient",
                        "statement_vi": f"Không tìm thấy giá trị {constraint.unit} tương ứng trong bản thiết kế để đối chiếu.",
                        "source_refs": [], "evidence_status": "insufficient",
                    })
                    continue
                design_path, actual, _unit, design_locator = matched
                within = (
                    constraint.low <= actual <= constraint.high if constraint.kind == "range"
                    else actual <= (constraint.high or actual) if constraint.kind == "max"
                    else actual >= (constraint.low or actual)
                )
                verdict = "pass" if within else "violate"
                checks.append({
                    "check_id": f"CHECK-{guideline.stem.upper()}-{index}",
                    "guideline_locator": constraint.locator, "design_locator": design_locator,
                    "verdict": verdict, "statement_vi": _comparison_statement(constraint, actual, verdict),
                    "source_refs": [_relative_reference(guideline, constraint.locator), _relative_reference(design_path, design_locator)],
                    "evidence_status": "supported",
                })
            for line_number, _line in unmatched_lines:
                checks.append({
                    "check_id": f"CHECK-{guideline.stem.upper()}-UNRESOLVED-{line_number}",
                    "guideline_locator": f"Dòng {line_number}", "design_locator": None,
                    "verdict": "insufficient",
                    "statement_vi": "Có số liệu trong Guideline nhưng không xác định được quan hệ giới hạn để đối chiếu an toàn.",
                    "source_refs": [], "evidence_status": "insufficient",
                })
        versions = {marker for guideline in guidelines for marker in _version_markers(guideline)}
        if len(versions) > 1:
            checks.append({
                "check_id": "CHECK-VERSION-001",
                "guideline_locator": "; ".join(path.name for path in guidelines),
                "design_locator": None, "verdict": "insufficient",
                "statement_vi": "Các nguồn Guideline nêu phiên bản khác nhau; cần xác nhận phiên bản áp dụng.",
                "source_refs": [_relative_reference(path) for path in guidelines], "evidence_status": "conflicting",
            })
        if not checks:
            checks.append({
                "check_id": "CHECK-EVIDENCE-001", "guideline_locator": None, "design_locator": None,
                "verdict": "insufficient", "statement_vi": "Không tìm thấy giới hạn định lượng có thể đối chiếu trong các nguồn đã chọn.",
                "source_refs": [], "evidence_status": "insufficient",
            })

    violations = [item for item in checks if item["verdict"] == "violate"]
    proposals = [{
        "statement_vi": f"Đối chiếu lại phát hiện: {violations[0]['statement_vi']} trước khi cập nhật bản nháp.",
        "evidence_status": "proposal",
    }] if violations else [{
        "statement_vi": "Bổ sung giới hạn hoặc giá trị tương ứng còn thiếu trước khi cập nhật bản nháp.",
        "evidence_status": "proposal",
    }]
    questions = [
        f"Giới hạn tại {violations[0]['guideline_locator']} có được xác nhận là áp dụng cho bản thiết kế này?"
        if violations else "Nguồn nào có thể bổ sung giới hạn hoặc giá trị còn thiếu để đối chiếu?"
    ]
    payload: dict[str, Any] = {
        "schema_version": "aios_process_design_review_v1", "artifact_id": f"ra-soat-{work_id.lower()}",
        "work_id": work_id, "title_vi": "Bản nháp rà soát thiết kế công đoạn", "status": "verified_draft",
        "guideline_refs": guideline_refs, "design_refs": design_refs, "context_refs": context_refs,
        "as_is_vi": "Bản nháp đối chiếu các tài liệu cục bộ đã chọn; không sửa tài liệu gốc.",
        "checks": checks,
        "impacts_vi": "Các mục vi phạm hoặc chưa đủ bằng chứng cần được kỹ sư xác nhận trước khi áp dụng.",
        "proposals": proposals, "expert_questions_vi": questions,
        "diagrams": [{
            "type": "mermaid", "locator": "bản nháp rà soát",
            "source_refs": [item["source_file"] for item in guideline_refs + design_refs],
            "content": "flowchart LR\n  G[Guideline] --> R[Rà soát]\n  D[Bản thiết kế] --> R",
        }] if guideline_refs and design_refs else [],
        "created_at": _utc_now(),
    }
    payload["artifact_digest"] = _digest_payload(payload)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / f"ra_soat_thiet_ke_{work_id}.md"
    previous_content = report_path.read_bytes() if report_path.exists() else None
    lines = [
        f"# {payload['title_vi']}", "", "Đây là bản nháp đã rà soát, không phải SOP hoặc Guideline đã phê duyệt.", "",
        "## Hiện trạng", payload["as_is_vi"], "", "## Kết quả đối chiếu",
        *[f"- {item['verdict']}: {item['statement_vi']}" for item in checks], "", "## Ảnh hưởng",
        payload["impacts_vi"], "", "## Đề xuất", *[f"- {item['statement_vi']}" for item in proposals], "",
        "## Câu hỏi cần xác nhận", *[f"- {item}" for item in questions],
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ProcessDesignReviewResult(payload, report_path, "Đã xong", False, previous_content)


def detect_agent_work_intent(prompt: str) -> str | None:
    """Classify user conversational prompt into agent task intents (error_report, process_design_review, code_change) or None."""
    if not prompt or not prompt.strip():
        return None
    p = prompt.strip().casefold()
    decomposed = unicodedata.normalize("NFKD", p)
    norm_no_marks = "".join(char for char in decomposed if not unicodedata.combining(char)).replace("đ", "d")

    error_patterns = (
        "bao cao loi", "tao bao cao loi", "lap bao cao loi", "xuat bao cao loi",
        "bao cao su co", "tao bao cao su co", "lap bao cao su co",
        "phan tich loi", "tong hop loi", "tong hop su co", "bien ban su co",
        "error report", "defect report", "bien ban loi",
    )
    if any(pattern in norm_no_marks for pattern in error_patterns):
        return "error_report"

    review_patterns = (
        "ra soat thiet ke", "danh gia thiet ke", "doi chieu thiet ke",
        "ra soat cong doan", "kiem tra cong doan", "soat xet quy trinh",
        "ra soat quy trinh", "tham dinh quy trinh", "tham tra thiet ke",
        "kiem tra thiet ke", "review thiet ke", "process design review",
        "ra soat guideline", "doi chieu guideline", "danh gia cong doan",
    )
    if any(pattern in norm_no_marks for pattern in review_patterns):
        return "process_design_review"

    code_patterns = (
        "sua ma nguon", "sua ma", "sua code", "fix bug", "sua loi ma nguon",
        "kiem tra ma", "sua loi code", "code change", "sua ma trong worktree",
    )
    if any(pattern in norm_no_marks for pattern in code_patterns):
        return "code_change"

    return None


def format_artifact_card(
    *,
    work_type: str,
    work_id: str,
    result_path: str | Path,
    checkpoint_path: str | Path,
    payload: dict[str, Any],
    status_vi: str = "Đã xong",
) -> str:
    """Builds a rich, interactive Grokbot-style artifact card in markdown with embedded metadata."""
    res_path = Path(result_path)
    ckpt_path = Path(checkpoint_path)
    lines: list[str] = []

    if work_type == "error_report":
        lines.append("### 📋 Báo cáo lỗi kỹ thuật")
        lines.append(f"**Trạng thái:** ✅ {status_vi}\n")
        lines.append("#### 🔍 Tóm tắt phát hiện chính")
        lines.append(f"- **Hiện tượng:** {payload.get('phenomenon_vi', 'Chưa có mô tả')}")
        lines.append(f"- **Phạm vi ảnh hưởng:** {payload.get('impact_vi', 'Chưa có dữ liệu định lượng')}")
        lines.append(f"- **Phân tích kỹ thuật:** {payload.get('analysis_vi', 'Báo cáo trích xuất từ dữ liệu nguồn')}")
        if payload.get("uncertainties_vi"):
            lines.append(f"- **Phần chưa chắc chắn:** {payload.get('uncertainties_vi')}")

        actions = payload.get("next_actions_vi") or []
        if actions:
            lines.append("\n#### 🛠️ Việc nên làm tiếp")
            for act in actions:
                lines.append(f"- {act}")

        visuals = payload.get("visuals") or []
        if visuals:
            lines.append("\n#### 📊 Biểu đồ số liệu có căn cứ")
            for vis in visuals:
                lines.append("```mermaid")
                lines.append(vis.get("content", ""))
                lines.append("```")
                ref_file = vis.get("source_refs", [""])[0]
                cols = ", ".join(vis.get("source_columns", []))
                unit = vis.get("units", "")
                lines.append(f"*(Căn cứ nguồn: `{ref_file}` — Cột: `{cols}` — Đơn vị: {unit})*")

        evidence = payload.get("evidence") or []
        if evidence:
            lines.append("\n#### 📌 Căn cứ dữ liệu nguồn")
            for ev in evidence:
                lines.append(f"- `{ev.get('source_file', '')}`: {ev.get('locator', 'toàn bộ tệp')}")

    elif work_type == "process_design_review":
        lines.append("### 📐 Bản nháp rà soát thiết kế công đoạn")
        lines.append(f"**Trạng thái:** ✅ {status_vi}")
        lines.append("*(Lưu ý: Đây là bản nháp đối chiếu các tài liệu cục bộ đã chọn; không sửa đổi tài liệu gốc)*\n")
        lines.append("#### 🔍 Tóm tắt kết quả đối chiếu")
        lines.append(f"- **Hiện trạng:** {payload.get('as_is_vi', '')}")
        lines.append(f"- **Ảnh hưởng:** {payload.get('impacts_vi', '')}")

        checks = payload.get("checks") or []
        if checks:
            lines.append("\n#### 📋 Chi tiết các điểm kiểm tra")
            for chk in checks:
                verdict = chk.get("verdict", "")
                icon = "✅" if verdict == "pass" else "⚠️" if verdict == "violate" else "ℹ️"
                lines.append(f"- {icon} **[{verdict.upper()}]** {chk.get('statement_vi', '')}")

        proposals = payload.get("proposals") or []
        if proposals:
            lines.append("\n#### 💡 Đề xuất cải tiến")
            for prop in proposals:
                lines.append(f"- {prop.get('statement_vi', '')}")

        questions = payload.get("expert_questions_vi") or []
        if questions:
            lines.append("\n#### ❓ Câu hỏi cần xác nhận với kỹ sư")
            for q in questions:
                lines.append(f"- {q}")

        diagrams = payload.get("diagrams") or []
        if diagrams:
            lines.append("\n#### 📊 Sơ đồ quy trình đối chiếu")
            for diag in diagrams:
                lines.append("```mermaid")
                lines.append(diag.get("content", ""))
                lines.append("```")

    else:
        lines.append("### 💻 Tác vụ mã nguồn")
        lines.append(f"**Trạng thái:** ✅ {status_vi}\n")
        lines.append(f"- **Mục tiêu:** {payload.get('goal_vi', work_id)}")

    meta_payload = {
        "work_id": work_id,
        "work_type": work_type,
        "result_path": str(res_path),
        "checkpoint_path": str(ckpt_path),
    }
    meta_json = json.dumps(meta_payload, ensure_ascii=False)
    lines.append(f"\n<!-- aios_chat_artifact: {meta_json} -->")

    return "\n".join(lines)


def extract_chat_artifact_metadata(content: str) -> dict[str, Any] | None:
    """Extracts embedded JSON metadata from a chat artifact message comment."""
    if not content or "<!-- aios_chat_artifact:" not in content:
        return None
    try:
        start_tag = "<!-- aios_chat_artifact:"
        start_idx = content.index(start_tag) + len(start_tag)
        end_idx = content.index("-->", start_idx)
        raw_json = content[start_idx:end_idx].strip()
        return json.loads(raw_json)
    except Exception:
        return None

