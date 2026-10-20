# -*- coding: utf-8 -*-
"""Bo phan tich va doc cau truc file log tong quat (CSV, Excel, Text log).

Nhiem vu:
- Nhan dien tu dong dau phan cach (comma, tab, semicolon, pipe, whitespace).
- Nhan dien dong tieu de (header row) du khong nam o dong dau tien.
- Phan loai kieu cot: datetime (thoi gian), categorical (ma/phan loai), numeric (so do), result (OK/NG).
- Ben vung truoc file xau, file rat lon (gioi han tran so dong va lay mau), bo qua dong chu thich.
- Khong bao gio crash app: bat loi ro rang bang tieng Viet.
"""

from __future__ import annotations

import csv
import io
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

try:
    import openpyxl
except ImportError:
    openpyxl = None


class LogParseError(Exception):
    """Loi doc cau truc file log khong thanh cong."""
    pass


# 4 kieu cot tieu chuan
ROLE_DATETIME = "datetime"
ROLE_CATEGORICAL = "categorical"
ROLE_NUMERIC = "numeric"
ROLE_RESULT = "result"

VALID_ROLES = (ROLE_DATETIME, ROLE_CATEGORICAL, ROLE_NUMERIC, ROLE_RESULT)

# Cac gia tri tieu bieu cho cot ket qua OK/NG
RESULT_KEYWORDS = {
    "ok", "ng", "pass", "fail", "good", "bad", "dat", "khong dat",
    "true", "false", "0", "1", "pass/fail", "ok/ng", "hop le", "loi"
}

# Cac tu khoa tieu de dac trung trong san xuat
HEADER_HINT_WORDS = {
    "date", "time", "timestamp", "datetime", "ngay", "gio", "thoidiem",
    "serial", "id", "lot", "batch", "ma", "so", "line", "chuyen", "station", "tram",
    "machine", "may", "jig", "fixture", "tool", "operator", "congnhan",
    "result", "ketqua", "status", "trangthai", "verdict",
    "val", "value", "giatri", "skew", "bow", "beam", "power", "volt", "voltage",
    "curr", "current", "temp", "temperature", "press", "pressure", "speed",
    "height", "width", "len", "length", "offset", "delta", "diff", "error", "loi"
}

CANDIDATE_DELIMITERS = [",", "\t", ";", "|"]


@dataclass
class ColumnMeta:
    """Thong tin cau truc cua mot cot trong file log."""
    name: str
    role: str
    sample_values: List[str] = field(default_factory=list)
    null_count: int = 0
    unique_count: int = 0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None


@dataclass
class ParsedLogTable:
    """Bang du lieu log da duoc phan tich cau truc."""
    file_name: str
    total_rows: int
    columns: List[ColumnMeta]
    rows: List[Dict[str, Any]]
    delimiter: str = ","
    header_row_index: int = 0
    provenance_note: str = ""

    def get_column_names(self) -> List[str]:
        return [col.name for col in self.columns]

    def get_column_meta(self, col_name: str) -> Optional[ColumnMeta]:
        for col in self.columns:
            if col.name == col_name:
                return col
        return None

    def get_columns_by_role(self, role: str) -> List[ColumnMeta]:
        return [col for col in self.columns if col.role == role]

    def get_series(self, col_name: str, max_points: Optional[int] = None) -> List[Any]:
        vals = [row.get(col_name) for row in self.rows if col_name in row]
        if max_points and len(vals) > max_points:
            step = max(1, len(vals) // max_points)
            return vals[::step][:max_points]
        return vals

    def get_numeric_series(self, col_name: str, max_points: Optional[int] = None) -> List[float]:
        clean: List[float] = []
        for row in self.rows:
            v = row.get(col_name)
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                try:
                    clean.append(float(v))
                except (ValueError, TypeError):
                    continue
        if max_points and len(clean) > max_points:
            step = max(1, len(clean) // max_points)
            return clean[::step][:max_points]
        return clean

    def filter_rows(self, predicate: Callable[[Dict[str, Any]], bool]) -> "ParsedLogTable":
        filtered = [r for r in self.rows if predicate(r)]
        # Re-derive simple stats for filtered
        return ParsedLogTable(
            file_name=self.file_name,
            total_rows=len(filtered),
            columns=self.columns,
            rows=filtered,
            delimiter=self.delimiter,
            header_row_index=self.header_row_index,
            provenance_note=f"{self.provenance_note} (Loc con {len(filtered)} dong)",
        )


def _decode_bytes(raw_bytes: bytes) -> str:
    """Thu cac bang ma pho bien trong nha may san xuat (Viet/Anh/Nhat)."""
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "shift_jis"]
    for enc in encodings:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def sniff_delimiter(sample_lines: Sequence[str]) -> str:
    """Nhan dien dau phan cach toi uu dua tren tan suat va tinh on dinh."""
    valid_lines = [l for l in sample_lines if l.strip() and not l.strip().startswith(("#", "//", "---"))]
    if not valid_lines:
        return ","

    best_delim = ","
    best_score = -1.0

    for delim in CANDIDATE_DELIMITERS:
        counts = [line.count(delim) for line in valid_lines[:20]]
        if not counts:
            continue
        avg_cnt = sum(counts) / len(counts)
        if avg_cnt < 1.0:
            continue
        # Tinh do lech chuan: cang dong deu giua cac dong cang tot
        variance = sum((c - avg_cnt) ** 2 for c in counts) / len(counts)
        score = (avg_cnt * 10.0) / (1.0 + variance)
        if score > best_score:
            best_score = score
            best_delim = delim

    # Kiem tra neu khong co dau phan cach dac biet, thu xem co phai phan cach bang nhieu khoang trang
    if best_score < 0:
        space_counts = [len(re.split(r"\s{2,}|\t", l.strip())) for l in valid_lines[:15]]
        if space_counts and sum(space_counts) / len(space_counts) >= 2:
            return r"\s+"

    return best_delim


def _split_line(line: str, delimiter: str) -> List[str]:
    """Tach dong theo dau phan cach hoac regex khoang trang."""
    if delimiter == r"\s+":
        return [tok.strip() for tok in re.split(r"\s{2,}|\t", line.strip()) if tok.strip()]
    
    # Su dung csv.reader cho 1 dong de xu ly ca dau ngoac kep
    try:
        reader = csv.reader([line], delimiter=delimiter)
        for row in reader:
            return [col.strip() for col in row]
    except Exception:
        pass
    return [col.strip() for col in line.split(delimiter)]


def detect_header_row(lines: Sequence[str], delimiter: str) -> Tuple[int, List[str]]:
    """Tim dong tieu de (co the bo qua cac dong chu thich, config, thong so ban dau)."""
    best_idx = 0
    best_score = -999.0
    best_columns: List[str] = []

    clean_lines = lines[:40]
    for idx, raw_line in enumerate(clean_lines):
        line = raw_line.strip()
        if not line or line.startswith(("#", "//", "---", "===")):
            continue

        tokens = _split_line(line, delimiter)
        if len(tokens) < 2:
            continue

        # Tinh diem cho dong tieu de
        score = 0.0
        non_empty_tokens = [t for t in tokens if t]
        if not non_empty_tokens:
            continue

        # Uu tien so luong cot hop ly
        score += min(len(non_empty_tokens), 30) * 1.5

        # Uu tien cac tu khoa tieu de san xuat
        matched_words = 0
        numeric_count = 0
        date_count = 0

        for tok in non_empty_tokens:
            tok_lower = tok.lower()
            # Bo ky tu ngoac don/vuong nhu [um], (mm)
            tok_norm = re.sub(r"\[.*?\]|\(.*?\)", "", tok_lower).strip()

            if any(w in tok_norm for w in HEADER_HINT_WORDS):
                matched_words += 1
            if _is_numeric(tok):
                numeric_count += 1
            if _is_datetime_str(tok):
                date_count += 1

        score += matched_words * 4.0
        score -= numeric_count * 2.0
        score -= date_count * 3.0

        # Kiem tra dong ngay sau no: neu dong sau chu yeu la so hoac datetime thi dong nay rat co the la tieu de
        if idx + 1 < len(clean_lines):
            next_line = clean_lines[idx + 1].strip()
            if next_line and not next_line.startswith(("#", "//")):
                next_tokens = _split_line(next_line, delimiter)
                next_numerics = sum(1 for t in next_tokens if _is_numeric(t) or _is_datetime_str(t))
                if next_numerics >= len(next_tokens) * 0.4:
                    score += 5.0

        if score > best_score:
            best_score = score
            best_idx = idx
            best_columns = tokens

    if not best_columns:
        # Fallback: lay dong khong rong dau tien
        for idx, l in enumerate(lines):
            if l.strip():
                best_idx = idx
                best_columns = _split_line(l, delimiter)
                break

    # Lam sach va tranh trung ten cot
    sanitized_cols: List[str] = []
    seen: Dict[str, int] = {}
    for col in best_columns:
        c = col.strip() or "COT_KHONG_TEN"
        if c in seen:
            seen[c] += 1
            sanitized_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 1
            sanitized_cols.append(c)

    return best_idx, sanitized_cols


def _is_numeric(val: Any) -> bool:
    """Kiem tra gia tri co phai dang so (int/float, chap nhan dau phay/cham)."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return not (isinstance(val, float) and (math.isnan(val) or math.isinf(val)))
    s = str(val).strip()
    if not s:
        return False
    # Bo dau % hoac don vi trong ngoac
    s_clean = re.sub(r"[%\s]", "", s)
    # Thu chuyen doi
    try:
        float(s_clean)
        return True
    except ValueError:
        pass
    # Thu voi dau phay thap phan chau Au/Viet
    if "," in s_clean and "." not in s_clean:
        try:
            float(s_clean.replace(",", "."))
            return True
        except ValueError:
            pass
    return False


def _to_float(val: Any) -> Optional[float]:
    """Chuyen doi linh hoat sang float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if not (isinstance(val, float) and math.isnan(val)) else None
    s = str(val).strip()
    if not s:
        return None
    s_clean = re.sub(r"[%\s]", "", s)
    try:
        return float(s_clean)
    except ValueError:
        pass
    if "," in s_clean and "." not in s_clean:
        try:
            return float(s_clean.replace(",", "."))
        except ValueError:
            pass
    return None


def _is_datetime_str(val: Any) -> bool:
    """Nhan dien chuoi thoi gian/ngay thang."""
    if val is None:
        return False
    if isinstance(val, datetime):
        return True
    s = str(val).strip()
    if len(s) < 4:
        return False
    # Dang ISO / standard: 2026-10-20, 2026/10/20, 2026.10.20
    if re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", s):
        return True
    # Dang ngay/thang/nam: 20/10/2026
    if re.match(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", s):
        return True
    # Dang gio phut giay: 08:30:00, 16:35:11
    if re.match(r"^\d{1,2}:\d{2}(:\d{2})?", s):
        return True
    return False


def classify_column_role(col_name: str, sample_values: Sequence[Any]) -> str:
    """Phan loai kieu cot: datetime, result, numeric, hoac categorical."""
    name_lower = col_name.lower()

    # 1. Kiem tra ten cot uu tien
    if any(k in name_lower for k in ("result", "ket_qua", "ketqua", "status", "verdict", "danh_gia")):
        return ROLE_RESULT

    # 2. Thu thap cac gia tri hop le
    non_null_samples = [v for v in sample_values if v is not None and str(v).strip() != ""]
    if not non_null_samples:
        return ROLE_CATEGORICAL

    total_samples = len(non_null_samples)

    # 3. Kiem tra kieu Result (OK/NG/PASS/FAIL)
    result_matches = sum(1 for v in non_null_samples if str(v).strip().lower() in RESULT_KEYWORDS)
    if result_matches >= total_samples * 0.7:
        return ROLE_RESULT

    # 4. Kiem tra kieu Datetime
    dt_matches = sum(1 for v in non_null_samples if _is_datetime_str(v))
    if dt_matches >= total_samples * 0.6:
        return ROLE_DATETIME
    if any(k in name_lower for k in ("date", "time", "timestamp", "ngay", "gio", "thoi_gian")):
        if dt_matches >= total_samples * 0.3:
            return ROLE_DATETIME

    # 5. Kiem tra kieu Numeric
    num_matches = sum(1 for v in non_null_samples if _is_numeric(v))
    if num_matches >= total_samples * 0.7:
        return ROLE_NUMERIC

    # 6. Con lai mac dinh la Categorical
    return ROLE_CATEGORICAL


def parse_log_file(
    file_source: Union[str, Path, bytes],
    file_name: str = "log_data",
    max_rows: int = 30000,
    sample_for_stats: int = 100,
) -> ParsedLogTable:
    """Doc va phan tich cau truc bat ky file log nao (CSV, Excel, Text log)."""
    raw_bytes: bytes = b""
    path_obj: Optional[Path] = None

    if isinstance(file_source, (str, Path)):
        path_obj = Path(file_source)
        if not path_obj.exists():
            raise LogParseError(f"Tep khong ton tai tai duong dan: {path_obj}")
        if file_name == "log_data" or not file_name:
            file_name = path_obj.name
        try:
            raw_bytes = path_obj.read_bytes()
        except Exception as e:
            raise LogParseError(f"Khong the doc tep \"{file_name}\": {e}")
    elif isinstance(file_source, bytes):
        raw_bytes = file_source
    else:
        raise LogParseError("Nguon tep khong hop le (can duong dan hoac bytes).")

    if len(raw_bytes) == 0:
        raise LogParseError(f"Tep \"{file_name}\" rong, khong co du lieu de tao bieu do.")

    ext = Path(file_name).suffix.lower()

    # Xu ly file Excel
    if ext in (".xlsx", ".xls"):
        return _parse_excel(raw_bytes, file_name, max_rows=max_rows)

    # Xu ly file Text / CSV / Log
    text_content = _decode_bytes(raw_bytes)
    return _parse_text_table(text_content, file_name, max_rows=max_rows, sample_for_stats=sample_for_stats)


def _parse_excel(raw_bytes: bytes, file_name: str, max_rows: int = 30000) -> ParsedLogTable:
    """Doc file Excel an toan bang openpyxl (tranh crash C-extension)."""
    if openpyxl is None:
        raise LogParseError("Thu vien openpyxl chua duoc cai dat de doc tep Excel.")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True, read_only=True)
    except Exception as e:
        raise LogParseError(f"Khong the mo tep Excel \"{file_name}\": {e}")

    sheet_names = wb.sheetnames
    if not sheet_names:
        raise LogParseError(f"Tep Excel \"{file_name}\" khong co sheet nao.")

    sheet = wb[sheet_names[0]]

    raw_matrix: List[List[Any]] = []
    for row in sheet.iter_rows(values_only=True):
        if any(cell is not None for cell in row):
            raw_matrix.append(list(row))
        if len(raw_matrix) >= max_rows + 50:
            break

    if not raw_matrix:
        raise LogParseError(f"Tep Excel \"{file_name}\" khong co du lieu dong nao.")

    # Tim dong tieu de
    header_idx = 0
    best_score = -999.0
    best_cols: List[str] = []

    for idx, r in enumerate(raw_matrix[:30]):
        non_empty = [c for c in r if c is not None and str(c).strip()]
        if len(non_empty) < 2:
            continue
        score = len(non_empty) * 1.5
        for cell in non_empty:
            c_str = str(cell).lower()
            if any(w in c_str for w in HEADER_HINT_WORDS):
                score += 4.0
            if isinstance(cell, (int, float)):
                score -= 2.0
            if isinstance(cell, datetime):
                score -= 3.0
        if score > best_score:
            best_score = score
            header_idx = idx
            best_cols = [str(c).strip() if c is not None else "" for c in r]

    if not best_cols:
        header_idx = 0
        best_cols = [f"Cot_{i+1}" for i in range(len(raw_matrix[0]))]

    # Deduplicate columns
    col_names: List[str] = []
    seen: Dict[str, int] = {}
    for i, c in enumerate(best_cols):
        name = c if c else f"Cot_{i+1}"
        if name in seen:
            seen[name] += 1
            col_names.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 1
            col_names.append(name)

    data_rows: List[Dict[str, Any]] = []
    for row in raw_matrix[header_idx + 1: header_idx + 1 + max_rows]:
        row_dict: Dict[str, Any] = {}
        has_any = False
        for col_name, val in zip(col_names, row):
            if val is not None:
                has_any = True
                if isinstance(val, datetime):
                    row_dict[col_name] = val.strftime("%Y-%m-%d %H:%M:%S")
                elif _is_numeric(val):
                    row_dict[col_name] = _to_float(val)
                else:
                    row_dict[col_name] = str(val).strip()
            else:
                row_dict[col_name] = None
        if has_any:
            data_rows.append(row_dict)

    if not data_rows:
        raise LogParseError(f"Tep Excel \"{file_name}\" chi co tieu de, khong co du lieu.")

    # Phan loai cot
    columns_meta: List[ColumnMeta] = []
    for c_name in col_names:
        sample_vals = [r[c_name] for r in data_rows[:100] if r[c_name] is not None]
        role = classify_column_role(c_name, sample_vals)
        all_vals = [r[c_name] for r in data_rows]
        null_count = sum(1 for v in all_vals if v is None)
        uniques = len(set(str(v) for v in all_vals if v is not None))

        min_v, max_v, mean_v = None, None, None
        if role == ROLE_NUMERIC:
            nums = [_to_float(v) for v in all_vals if _is_numeric(v)]
            nums = [n for n in nums if n is not None]
            if nums:
                min_v = min(nums)
                max_v = max(nums)
                mean_v = sum(nums) / len(nums)

        columns_meta.append(
            ColumnMeta(
                name=c_name,
                role=role,
                sample_values=[str(v) for v in sample_vals[:5]],
                null_count=null_count,
                unique_count=uniques,
                min_val=min_v,
                max_val=max_v,
                mean_val=mean_v,
            )
        )

    return ParsedLogTable(
        file_name=file_name,
        total_rows=len(data_rows),
        columns=columns_meta,
        rows=data_rows,
        delimiter="excel",
        header_row_index=header_idx,
        provenance_note=f"Tep Excel: {file_name} ({len(data_rows)} dong, {len(col_names)} cot)",
    )


def _parse_text_table(
    text_content: str,
    file_name: str,
    max_rows: int = 30000,
    sample_for_stats: int = 100,
) -> ParsedLogTable:
    """Doc bang du lieu tu van ban (CSV, TSV, pipe-delimited, space-delimited)."""
    lines = [l for l in text_content.splitlines() if l.strip()]
    if not lines:
        raise LogParseError(f"Tep \"{file_name}\" khong chua noi dung van ban hop le.")

    delimiter = sniff_delimiter(lines[:30])
    header_idx, col_names = detect_header_row(lines, delimiter)

    data_rows: List[Dict[str, Any]] = []
    lines_to_read = lines[header_idx + 1: header_idx + 1 + max_rows]

    for raw_line in lines_to_read:
        line = raw_line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        tokens = _split_line(line, delimiter)
        if not tokens:
            continue
        row_dict: Dict[str, Any] = {}
        for i, c_name in enumerate(col_names):
            if i < len(tokens):
                tok = tokens[i].strip()
                if tok == "" or tok.lower() in ("null", "none", "nan", "-"):
                    row_dict[c_name] = None
                elif _is_numeric(tok):
                    row_dict[c_name] = _to_float(tok)
                else:
                    row_dict[c_name] = tok
            else:
                row_dict[c_name] = None
        data_rows.append(row_dict)

    if not data_rows:
        raise LogParseError(f"Khong tim thay dong du lieu nao sau dong tieu de trong tep \"{file_name}\".")

    # Phan loai cot
    columns_meta: List[ColumnMeta] = []
    for c_name in col_names:
        sample_vals = [r[c_name] for r in data_rows[:sample_for_stats] if r[c_name] is not None]
        role = classify_column_role(c_name, sample_vals)
        all_vals = [r[c_name] for r in data_rows]
        null_count = sum(1 for v in all_vals if v is None)
        uniques = len(set(str(v) for v in all_vals if v is not None))

        min_v, max_v, mean_v = None, None, None
        if role == ROLE_NUMERIC:
            nums = [_to_float(v) for v in all_vals if _is_numeric(v)]
            nums = [n for n in nums if n is not None]
            if nums:
                min_v = min(nums)
                max_v = max(nums)
                mean_v = sum(nums) / len(nums)

        columns_meta.append(
            ColumnMeta(
                name=c_name,
                role=role,
                sample_values=[str(v) for v in sample_vals[:5]],
                null_count=null_count,
                unique_count=uniques,
                min_val=min_v,
                max_val=max_v,
                mean_val=mean_v,
            )
        )

    delim_label = "dau phay (,)" if delimiter == "," else ("tab (\\t)" if delimiter == "\t" else f"ky tu \"{delimiter}\"")
    return ParsedLogTable(
        file_name=file_name,
        total_rows=len(data_rows),
        columns=columns_meta,
        rows=data_rows,
        delimiter=delimiter,
        header_row_index=header_idx,
        provenance_note=f"Tep text/CSV: {file_name} ({len(data_rows)} dong, {len(col_names)} cot, phan cach bang {delim_label})",
    )
