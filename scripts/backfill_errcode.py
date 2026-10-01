#!/usr/bin/env python3
"""BK-ERRCODE: backfill mã thật cho ca thiếu mã (chạy trên BẢN COPY của DB).

Quy trình an toàn:
  1. Từ chối chạy nếu --db trỏ tới DB production/gốc (danh sách cấm).
  2. Mặc định DRY-RUN: chỉ đếm, không ghi gì (mở DB ở chế độ chỉ đọc).
  3. --apply mới ghi: migrate thêm cột provenance, cập nhật trong MỘT
     transaction, integrity_check trước/sau.
  4. Ca không tìm được mã -> xuất CSV để rà tay, KHÔNG bịa mã.

Ví dụ (máy nhà):
  python scripts/backfill_errcode.py --db C:/tmp/bk-errcode/error_cases_copy.db --ktd-dir "D:/.../C Call"
  python scripts/backfill_errcode.py --db C:/tmp/bk-errcode/error_cases_copy.db --ktd-dir ... --apply --csv-out C:/tmp/bk-errcode/manual.csv
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aios_habit.error_cases import (  # noqa: E402
    backfill_error_code_i_extended,
    connect,
    write_manual_csv,
)

# Basename của các DB production/gốc đã biết — không bao giờ được ghi.
DENY_BASENAMES = frozenset({
    "error_cases_deploy.db",   # DB deploy mặc định sản phẩm (schema cũ)
    "error_cases_lsu.db",      # DB LSU đối chứng
})


def _is_denied(db_path: Path, extra: list[str]) -> str | None:
    """Trả về lý do từ chối, hoặc None nếu được phép."""
    resolved = db_path.resolve()
    if resolved.name in DENY_BASENAMES:
        return f"tên file {resolved.name} nằm trong danh sách DB production bị cấm ghi"
    if "production" in (p.lower() for p in resolved.parts):
        return "đường dẫn chứa thư mục 'production'"
    for e in extra:
        if resolved == Path(e).expanduser().resolve():
            return f"trùng DB production đã khai báo: {e}"
    return None


def _integrity(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "unknown"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill error_code_i trên BẢN COPY (dry-run mặc định)."
    )
    parser.add_argument("--db", required=True, help="Đường dẫn DB COPY (không phải DB gốc)")
    parser.add_argument("--ktd-dir", default=None, help="Thư mục chứa KTD-*.xlsx (đối chiếu theo tên file)")
    parser.add_argument("--apply", action="store_true", help="Ghi thật (mặc định chỉ dry-run)")
    parser.add_argument("--csv-out", default="bk_errcode_manual.csv", help="CSV ca cần rà tay")
    parser.add_argument("--production-db", action="append", default=[],
                        help="Đường dẫn DB production tuyệt đối (cấm ghi; dùng được nhiều lần)")
    args = parser.parse_args(argv)

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"LỖI: không tìm thấy DB: {db_path}", file=sys.stderr)
        return 2
    reason = _is_denied(db_path, args.production_db)
    if reason:
        print(f"TỪ CHỐI: {reason}. Script này chỉ chạy trên bản COPY.", file=sys.stderr)
        return 3

    if args.apply:
        conn = connect(db_path)
        print(f"integrity_check trước apply: {_integrity(conn)}")
        try:
            result = backfill_error_code_i_extended(
                conn, apply=True,
                ktd_dir=args.ktd_dir,
            )
        finally:
            pass
        print(f"integrity_check sau apply: {_integrity(conn)}")
        conn.close()
    else:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            result = backfill_error_code_i_extended(
                conn, apply=False, ktd_dir=args.ktd_dir, migrate=False,
            )
        finally:
            conn.close()

    n_manual = write_manual_csv(args.csv_out, result.pop("manual"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    c = result
    print(
        f"\nTóm tắt: đọc {c['rows_read']} ca | thiếu mã {c['missing_code']} | "
        f"trích tự động {c['extracted_auto']} | KTD khớp {c['ktd_auto']} | "
        f"đóng dấu nguồn {c['src_stamped']} | đã ghi {c['updated']} | "
        f"cần rà tay {c['manual_list']} (CSV: {args.csv_out}, {n_manual} dòng)"
    )
    if not args.apply:
        print("DRY-RUN: chưa ghi gì vào DB. Thêm --apply để ghi thật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
