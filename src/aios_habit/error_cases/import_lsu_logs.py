"""LSU-1: importer for LSU production logs ("log jig" / "log 6 pcs") -> error_cases.

Bộ dữ liệu LSU thật (khảo sát 2026-10-01 trên bản copy ở
``C:/tmp/lsu1-deploy/data/lsu``; nguồn gốc: ổ D "Tài liệu của tất cả dòng máy"
+ bản công khai trên Drive AIOS_Data) gồm các định dạng log:

- ``cam_error``   ``DATE,TIME,CAM_ID,ERR_NUM`` — mỗi dòng là một sự kiện lỗi
  camera (Iris). Đã được nhận diện từ trước ở ``line_log_parser``; ở đây nhập
  vào kho phiếu lỗi ``error_cases`` để chạy pipeline Bước 0–5.
- ``jig_result``  ``SelNo,Date,Time,JigNo,FinTest,...`` — dòng có ``FinTest``
  khác ``OK`` là sự kiện (6thA3 "Lỗi JIG BEAM").
- ``unit_judge``  có ít nhất một cột chứa chữ ``judge`` (``TotalJudge``,
  ``Black_Judge``, ``Black_TotalJudge``, ``Judge:Black``…) — dòng có bất kỳ cột
  judge nào bằng ``NG`` là sự kiện (Iris + Sirius).
- ``unit_result`` có cột ``RESULT`` / ``RESULT:<MÀU>`` — dòng có bất kỳ cột
  result nào bằng ``NG`` là sự kiện (Iris).

Ánh xạ vào ``error_cases`` (provenance-first, dòng nguồn giữ nguyên trên đĩa):

- ``no_dvd``       = ``LSU/{đường_dẫn_tương_đối_bỏ_đuôi}/{dòng}`` — log không
  có số phiếu; đây là khoá truy vết duy nhất, ổn định theo tệp + dòng.
- ``machine_type`` = ``LSU``
- ``line``         = họ sản phẩm lấy từ thư mục gốc: ``6thA3`` | ``Iris`` | ``Sirius``
- ``error_code_h`` = ``ERR_NUM`` (chỉ ``cam_error``); định dạng khác để trống
- ``investigation``= mô tả hiện tượng (cột nào NG / FinTest / CamError)
- ``department`` / ``handler`` / cause / fix để trống — log không mang
  nguyên nhân/đối sách; đây là số liệu thật cho gate F3b của Bước 0.
- ``raw_json``     = ``{"format": "lsu_log", "dialect", "family", "source_file",
  "source_row", "date", "cause", "fix", "stage", "key_columns", "columns_total",
  "row_sha256"}`` — cột đo đạc của ma trận rộng (tới 992 cột) không nhân bản
  vào DB; toàn bộ dòng nguồn được đánh dấu bằng digest để tái lập từ tệp gốc
  còn nguyên trên đĩa.

Re-import cùng (tệp, sha256, dialect) bị bỏ qua trừ khi ``force=True``. Chỉ
đọc nguồn; chỉ ghi vào DB ``error_cases`` được truyền vào. Không chạm index RAG.
"""
from __future__ import annotations

import csv
import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import store
from .import_history import find_existing_batch

DIALECTS: Tuple[str, ...] = ("cam_error", "jig_result", "unit_judge", "unit_result")

#: Guard chống tệp khổng lồ ngoài dự kiến (lớn nhất thật ~1.000 dòng/sự kiện).
MAX_ROWS_PER_FILE = 1_000_000

_DATE_ALIASES = frozenset({"date"})
_TIME_ALIASES = frozenset({"time"})
_SERIAL_ALIASES = frozenset({"serial", "serial number", "s/n", "sn", "unit", "selno"})
_JIG_ALIASES = frozenset({"jigno", "jignumber", "jig"})


def normalize_header(name: Any) -> str:
    """Chuẩn hoá tên cột: bỏ khoảng trắng thừa, thường hoá, '-' -> '_'.

    Header thật của log Iris/Sirius có khoảng trắng đầu cột không nhất quán
    (``' DATE'``, ``' S/N'``, ``' Mode'``), nên mọi ánh xạ đều đi qua đây.
    """
    raw = str(name or "").strip().lower().replace("-", "_")
    return " ".join(raw.split())


def detect_lsu_dialect(headers: Sequence[Any]) -> Optional[str]:
    """Định dạng log LSU theo bộ tên cột đã chuẩn hoá; None khi không nhận diện."""
    names = {normalize_header(item) for item in headers}
    if {"date", "time", "cam_id", "err_num"} <= names:
        return "cam_error"
    if {"selno", "jigno", "fintest"} <= names:
        return "jig_result"
    if any("judge" in name for name in names):
        return "unit_judge"
    if any(name == "result" or name.startswith("result:") for name in names):
        return "unit_result"
    return None


def _is_result_column(name: str) -> bool:
    return name == "result" or name.startswith("result:")


def _is_judge_column(name: str) -> bool:
    return "judge" in name


def _is_key_column(name: str) -> bool:
    return name in _DATE_ALIASES or name in _TIME_ALIASES \
        or name in _SERIAL_ALIASES or name in _JIG_ALIASES


def _cell(row: Sequence[Any], index: int) -> str:
    if index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else str(value).strip()


def _row_digest(cells: Sequence[str]) -> str:
    raw = "\x1f".join(cells).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def _joined_date(columns: Dict[str, str]) -> str:
    date = columns.get("date", "")
    time = columns.get("time", "")
    return f"{date} {time}".strip()


def _first(columns: Dict[str, str], aliases: Iterable[str]) -> str:
    for alias in aliases:
        value = columns.get(alias, "")
        if value:
            return value
    return ""


def _describe(dialect: str, columns: Dict[str, str], ng_raw_names: List[str]) -> str:
    if dialect == "cam_error":
        return f"CamError: CAM_ID={columns.get('cam_id', '')} ERR_NUM={columns.get('err_num', '')}"
    if dialect == "jig_result":
        return (
            f"Lỗi JIG BEAM: FinTest={columns.get('fintest', '')}"
            f" (JigNo={columns.get('jigno', '')}, SelNo={columns.get('selno', '')})"
        )
    serial = _first(columns, ("serial number", "s/n", "serial", "sn"))
    jig = _first(columns, ("jignumber", "jigno", "jig"))
    parts = [f"UnitTest NG: {', '.join(ng_raw_names)}"]
    extra = []
    if serial:
        extra.append(f"S/N={serial}")
    if jig:
        extra.append(f"Jig={jig}")
    if extra:
        parts.append("(" + ", ".join(extra) + ")")
    return " ".join(parts)


@dataclass
class LsuLogParseResult:
    dialect: Optional[str]
    columns_total: int
    rows_read: int = 0
    truncated: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)


def read_lsu_events(csv_path: str | Path) -> LsuLogParseResult:
    """Đọc một tệp CSV log LSU; trả về các dòng là sự kiện lỗi.

    Chỉ đọc phần thân khi header thuộc một định dạng nhận diện được.
    """
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return LsuLogParseResult(None, 0)
        dialect = detect_lsu_dialect(header)
        parsed = LsuLogParseResult(dialect, len(header))
        if dialect is None:
            return parsed

        names = [normalize_header(item) for item in header]
        # Cột hiển thị trong raw_json: cột khoá + cột kết quả/judge của định dạng.
        key_indexes = [i for i, name in enumerate(names) if _is_key_column(name)]
        if dialect == "jig_result":
            key_indexes += [i for i, name in enumerate(names) if name == "fintest"]
        elif dialect == "cam_error":
            key_indexes += [i for i, name in enumerate(names) if name in ("cam_id", "err_num")]
        elif dialect == "unit_judge":
            key_indexes += [i for i, name in enumerate(names) if _is_judge_column(name)]
        elif dialect == "unit_result":
            key_indexes += [i for i, name in enumerate(names) if _is_result_column(name)]
        key_indexes = sorted(set(key_indexes))

        ng_indexes = [
            i
            for i, name in enumerate(names)
            if (dialect == "unit_judge" and _is_judge_column(name))
            or (dialect == "unit_result" and _is_result_column(name))
        ]

        row_no = 0
        for row in reader:
            if not row or all(not (str(cell or "").strip()) for cell in row):
                continue
            row_no += 1
            if row_no > MAX_ROWS_PER_FILE:
                parsed.truncated = True
                break
            parsed.rows_read += 1

            cells = [_cell(row, i) for i in range(len(names))]
            if dialect == "cam_error":
                is_event = True
            elif dialect == "jig_result":
                fin = _cell(row, names.index("fintest"))
                is_event = fin.strip().upper() not in ("", "OK")
            else:
                is_event = any(cells[i].upper() == "NG" for i in ng_indexes)
            if not is_event:
                continue

            ng_raw_names = [header[i] for i in ng_indexes if cells[i].upper() == "NG"]
            columns = {header[i]: cells[i] for i in key_indexes}
            columns_lookup = {names[i]: cells[i] for i in key_indexes}
            parsed.events.append(
                {
                    "row_no": row_no,
                    "date": _joined_date(columns_lookup),
                    "code": columns_lookup.get("err_num", "") if dialect == "cam_error" else "",
                    "investigation": _describe(dialect, columns_lookup, ng_raw_names),
                    "stage": _first(columns_lookup, ("jignumber", "jigno", "jig")),
                    "key_columns": columns,
                    "row_sha256": _row_digest(cells),
                }
            )
    return parsed


def _case_no_dvd(rel_name: str, row_no: int) -> str:
    stem = str(rel_name or "").replace("\\", "/")
    if stem.lower().endswith(".csv"):
        stem = stem[:-4]
    return f"LSU/{stem}/{row_no}"


def import_lsu_log(
    conn: sqlite3.Connection,
    csv_path: str | Path,
    *,
    family: str,
    rel_name: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Nhập một tệp log LSU vào error_cases. Trả dict kết quả.

    status: "imported" | "skipped" (tệp cũ chưa đổi) | "skipped_unknown"
    (không nhận diện được định dạng; không đọc phần thân).
    """
    path = Path(csv_path)
    rel = (rel_name or path.name).replace("\\", "/")
    parsed = read_lsu_events(path)
    if parsed.dialect is None:
        return {
            "status": "skipped_unknown",
            "dialect": None,
            "rows_read": 0,
            "rows_imported": 0,
            "rows_skipped": 0,
            "columns_total": parsed.columns_total,
        }

    sha = store.sha256_file(path)
    if not force:
        existing = find_existing_batch(conn, rel, sha, parsed.dialect)
        if existing is not None:
            return {
                "status": "skipped",
                "dialect": parsed.dialect,
                "batch_id": existing,
                "rows_read": 0,
                "rows_imported": 0,
                "rows_skipped": 0,
            }

    batch_id = store.start_batch(
        conn,
        source_file=rel,
        file_sha256=sha,
        sheet_name=parsed.dialect,
        sheet_type=None,
        header_row=1,
        notes=f"LSU-1: lsu_log importer (dialect={parsed.dialect}, family={family})",
    )

    rows_imported = 0
    for event in parsed.events:
        raw = {
            "format": "lsu_log",
            "dialect": parsed.dialect,
            "family": family,
            "source_file": rel,
            "source_row": event["row_no"],
            "date": event["date"],
            "cause": "",
            "fix": "",
            "stage": event["stage"],
            "key_columns": event["key_columns"],
            "columns_total": parsed.columns_total,
            "row_sha256": event["row_sha256"],
        }
        fields = {
            "no_dvd": _case_no_dvd(rel, event["row_no"]),
            "machine_type": "LSU",
            "line": family,
            "error_code_h": event["code"] or None,
            "investigation": event["investigation"],
            "raw": raw,
        }
        store.upsert_case(
            conn,
            batch_id=batch_id,
            source_row=event["row_no"],
            fields=fields,
            skip_cells=[],
            format="lsu_log",
        )
        rows_imported += 1

    store.finish_batch(
        conn,
        batch_id,
        rows_read=parsed.rows_read,
        rows_imported=rows_imported,
        rows_skipped=parsed.rows_read - rows_imported,
    )
    return {
        "status": "imported",
        "dialect": parsed.dialect,
        "batch_id": batch_id,
        "rows_read": parsed.rows_read,
        "rows_imported": rows_imported,
        "rows_skipped": parsed.rows_read - rows_imported,
        "truncated": parsed.truncated,
    }


def import_lsu_tree(
    conn: sqlite3.Connection,
    root: str | Path,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Nhập toàn bộ cây dữ liệu LSU (đệ quy ``*.csv``).

    Họ sản phẩm (line) lấy từ thư mục gốc của mỗi tệp: ``6thA3 LSU`` -> ``6thA3``.
    Tệp không nhận diện được định dạng chỉ được đếm, không đọc phần thân.
    """
    base = Path(root)
    summary: Dict[str, Any] = {
        "root": str(base),
        "files_scanned": 0,
        "files_imported": 0,
        "files_skipped": 0,
        "files_skipped_unknown": 0,
        "rows_read": 0,
        "rows_imported": 0,
        "rows_skipped": 0,
        "by_dialect": {},
        "by_family": {},
        "unknown_files": [],
        "truncated_files": [],
    }

    def bump(table: str, key: str, field: str, amount: int = 1) -> None:
        entry = summary[table].setdefault(key, {
            "files": 0, "rows_read": 0, "rows_imported": 0,
        })
        entry[field] += amount

    for path in sorted(base.rglob("*.csv")):
        rel = path.relative_to(base).as_posix()
        top = rel.split("/")[0]
        family = top[:-4] if top.endswith(" LSU") else top
        result = import_lsu_log(conn, path, family=family, rel_name=rel, force=force)
        summary["files_scanned"] += 1
        status = result["status"]
        if status == "imported":
            summary["files_imported"] += 1
            summary["rows_read"] += result["rows_read"]
            summary["rows_imported"] += result["rows_imported"]
            summary["rows_skipped"] += result["rows_skipped"]
            bump("by_dialect", result["dialect"] or "?", "files")
            bump("by_dialect", result["dialect"] or "?", "rows_read", result["rows_read"])
            bump("by_dialect", result["dialect"] or "?", "rows_imported", result["rows_imported"])
            bump("by_family", family, "files")
            bump("by_family", family, "rows_read", result["rows_read"])
            bump("by_family", family, "rows_imported", result["rows_imported"])
            if result.get("truncated"):
                summary["truncated_files"].append(rel)
        elif status == "skipped":
            summary["files_skipped"] += 1
        else:
            summary["files_skipped_unknown"] += 1
            summary["unknown_files"].append(rel)
    return summary


def sha256_file(path: str | Path) -> str:  # re-export tiện dụng cho runner
    return store.sha256_file(path)
