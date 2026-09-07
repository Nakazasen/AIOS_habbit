"""Deterministic synthetic LSU fixture generator.

Creates synthetic CSV and XLSX test datasets adhering to
specs/008-evidence-case-loop/contracts/lsu-iris-input.md and
specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md.
"""

from __future__ import annotations

import csv
from pathlib import Path
import openpyxl


def make_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def make_xlsx(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(path)


def generate_all_fixtures(base_dir: Path) -> None:
    # 1. Valid fixtures
    valid_dir = base_dir / "valid"
    comp_headers = [
        "lot_measurement_id",
        "component_lot_id",
        "component_code",
        "metric_name",
        "value",
        "unit",
        "event_time",
    ]
    comp_rows = [
        ["M_001", "LOT_LENS_01", "LENS_COLLIMATOR", "FOCAL_LENGTH", "25.42", "mm", "2026-03-01T08:00:00+07:00"],
        ["M_002", "LOT_LENS_01", "LENS_COLLIMATOR", "SURFACE_ROUGHNESS", "0.012", "um", "2026-03-01T08:05:00+07:00"],
        ["M_003", "LOT_LD_01", "LD_ARRAY", "EMISSION_WAVELENGTH", "785.2", "nm", "2026-03-01T08:10:00+07:00"],
        ["M_004", "LOT_LD_01", "LD_ARRAY", "OUTPUT_POWER", "45.1", "mW", "2026-03-01T08:15:00+07:00"],
        ["M_005", "LOT_LENS_02", "LENS_COLLIMATOR", "FOCAL_LENGTH", "25.85", "mm", "2026-03-01T08:20:00+07:00"],
        ["M_006", "LOT_LD_02", "LD_ARRAY", "EMISSION_WAVELENGTH", "792.0", "nm", "2026-03-01T08:25:00+07:00"],
    ]
    make_csv(valid_dir / "component_lots.csv", comp_headers, comp_rows)
    make_xlsx(valid_dir / "component_lots.xlsx", comp_headers, comp_rows)

    unit_headers = [
        "link_id",
        "unit_serial",
        "component_lot_id",
        "component_code",
        "assembly_time",
    ]
    unit_rows = [
        ["L_001", "SYN_UNIT_001", "LOT_LENS_01", "LENS_COLLIMATOR", "2026-03-01T09:00:00+07:00"],
        ["L_002", "SYN_UNIT_001", "LOT_LD_01", "LD_ARRAY", "2026-03-01T09:05:00+07:00"],
        ["L_003", "SYN_UNIT_002", "LOT_LENS_02", "LENS_COLLIMATOR", "2026-03-01T09:10:00+07:00"],
        ["L_004", "SYN_UNIT_002", "LOT_LD_02", "LD_ARRAY", "2026-03-01T09:15:00+07:00"],
    ]
    make_csv(valid_dir / "unit_lots.csv", unit_headers, unit_rows)
    make_xlsx(valid_dir / "unit_lots.xlsx", unit_headers, unit_rows)

    jig_headers = [
        "jig_result_id",
        "unit_serial",
        "jig_id",
        "run_id",
        "event_time",
        "metric_name",
        "value",
        "unit",
        "jig_version",
        "process_version",
        "target_label",
        "failure_code",
        "retest_outcome",
    ]
    jig_rows = [
        ["J_001", "SYN_UNIT_001", "BOWSKEW_4_BEAM", "RUN_001", "2026-03-01T10:00:00+07:00", "BOW_VALUE", "0.12", "mrad", "v1.2", "p2.0", "OK", "", ""],
        ["J_002", "SYN_UNIT_002", "BOWSKEW_4_BEAM", "RUN_002", "2026-03-01T10:15:00+07:00", "BOW_VALUE", "0.88", "mrad", "v1.2", "p2.0", "NG", "ERR_BOW_EXCEEDED", ""],
    ]
    make_csv(valid_dir / "jig_outcomes.csv", jig_headers, jig_rows)
    make_xlsx(valid_dir / "jig_outcomes.xlsx", jig_headers, jig_rows)

    # 2. Missing keys fixtures
    missing_dir = base_dir / "missing_keys"
    comp_missing_rows = [
        ["M_001", "", "LENS_COLLIMATOR", "FOCAL_LENGTH", "25.42", "mm", "2026-03-01T08:00:00+07:00"],
    ]
    make_csv(missing_dir / "component_lots.csv", comp_headers, comp_missing_rows)
    unit_missing_rows = [
        ["L_001", "", "LOT_LENS_01", "LENS_COLLIMATOR", "2026-03-01T09:00:00+07:00"],
    ]
    make_csv(missing_dir / "unit_lots.csv", unit_headers, unit_missing_rows)
    jig_missing_rows = [
        ["J_001", "", "BOWSKEW_4_BEAM", "RUN_001", "2026-03-01T10:00:00+07:00", "BOW_VALUE", "0.12", "mrad", "v1.2", "p2.0", "OK", "", ""],
    ]
    make_csv(missing_dir / "jig_outcomes.csv", jig_headers, jig_missing_rows)

    # 3. Conflicting keys fixtures
    conflict_dir = base_dir / "conflicting_keys"
    comp_conflict_rows = [
        ["M_001", "LOT_LENS_01", "LENS_COLLIMATOR", "FOCAL_LENGTH", "25.42", "mm", "2026-03-01T08:00:00+07:00"],
        ["M_001", "LOT_LENS_01", "LENS_COLLIMATOR", "FOCAL_LENGTH", "99.99", "mm", "2026-03-01T08:00:00+07:00"],
    ]
    make_csv(conflict_dir / "component_lots.csv", comp_headers, comp_conflict_rows)
    unit_conflict_rows = [
        ["L_001", "SYN_UNIT_001", "LOT_LENS_01", "LENS_COLLIMATOR", "2026-03-01T09:00:00+07:00"],
    ]
    make_csv(conflict_dir / "unit_lots.csv", unit_headers, unit_conflict_rows)
    jig_conflict_rows = [
        ["J_001", "SYN_UNIT_001", "BOWSKEW_4_BEAM", "RUN_001", "2026-03-01T10:00:00+07:00", "BOW_VALUE", "0.12", "mrad", "v1.2", "p2.0", "OK", "", ""],
        ["J_001", "SYN_UNIT_001", "BOWSKEW_4_BEAM", "RUN_001", "2026-03-01T10:00:00+07:00", "BOW_VALUE", "0.85", "mrad", "v1.2", "p2.0", "NG", "ERR_BOW", ""],
    ]
    make_csv(conflict_dir / "jig_outcomes.csv", jig_headers, jig_conflict_rows)

    # 4. Orphan keys fixtures
    orphan_dir = base_dir / "orphan_keys"
    comp_orphan_rows = [
        ["M_001", "LOT_LENS_01", "LENS_COLLIMATOR", "FOCAL_LENGTH", "25.42", "mm", "2026-03-01T08:00:00+07:00"],
    ]
    make_csv(orphan_dir / "component_lots.csv", comp_headers, comp_orphan_rows)
    unit_orphan_rows = [
        ["L_001", "SYN_UNIT_001", "LOT_NONEXISTENT", "LENS_COLLIMATOR", "2026-03-01T09:00:00+07:00"],
    ]
    make_csv(orphan_dir / "unit_lots.csv", unit_headers, unit_orphan_rows)
    jig_orphan_rows = [
        ["J_001", "SYN_UNIT_ORPHAN", "BOWSKEW_4_BEAM", "RUN_001", "2026-03-01T10:00:00+07:00", "BOW_VALUE", "0.12", "mrad", "v1.2", "p2.0", "OK", "", ""],
    ]
    make_csv(orphan_dir / "jig_outcomes.csv", jig_headers, jig_orphan_rows)

    # 5. Future leak fixtures
    future_dir = base_dir / "future_leak"
    comp_future_rows = [
        ["M_001", "LOT_LENS_01", "LENS_COLLIMATOR", "FOCAL_LENGTH", "25.42", "mm", "2026-03-01T12:00:00+07:00"],
    ]
    make_csv(future_dir / "component_lots.csv", comp_headers, comp_future_rows)
    unit_future_rows = [
        ["L_001", "SYN_UNIT_001", "LOT_LENS_01", "LENS_COLLIMATOR", "2026-03-01T09:00:00+07:00"],
    ]
    make_csv(future_dir / "unit_lots.csv", unit_headers, unit_future_rows)
    jig_future_rows = [
        ["J_001", "SYN_UNIT_001", "BOWSKEW_4_BEAM", "RUN_001", "2026-03-01T10:00:00+07:00", "BOW_VALUE", "0.12", "mrad", "v1.2", "p2.0", "OK", "", ""],
    ]
    make_csv(future_dir / "jig_outcomes.csv", jig_headers, jig_future_rows)

    # 6. Corrupt fixtures
    corrupt_dir = base_dir / "corrupt"
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    (corrupt_dir / "empty.csv").write_text("", encoding="utf-8")
    (corrupt_dir / "invalid_syntax.csv").write_bytes(b"\xff\xfe\x00\x00broken_non_utf8_binary")
    (corrupt_dir / "not_an_excel.xlsx").write_text("This is plain text pretending to be xlsx", encoding="utf-8")

    # 7. Time series fixture (Multi-period dataset for Milestone 3 replay)
    ts_dir = base_dir / "time_series"
    ts_comp_rows = []
    ts_unit_rows = []
    ts_jig_rows = []

    m_idx = 1
    l_idx = 1
    j_idx = 1
    for day_idx, day_str in enumerate(["2026-03-01", "2026-03-02", "2026-03-03"], start=1):
        lot_id = f"LOT_BATCH_{day_idx:02d}"
        ts_comp_rows.append([f"M_{m_idx:03d}", lot_id, "LENS_COLLIMATOR", "FOCAL_LENGTH", f"{25.40 + day_idx * 0.1:.2f}", "mm", f"{day_str}T07:00:00+07:00"])
        m_idx += 1
        ts_comp_rows.append([f"M_{m_idx:03d}", lot_id, "LD_ARRAY", "EMISSION_WAVELENGTH", f"{785.0 + day_idx * 0.5:.1f}", "nm", f"{day_str}T07:15:00+07:00"])
        m_idx += 1

        for u in range(1, 6):
            u_num = (day_idx - 1) * 5 + u
            unit_serial = f"SYN_UNIT_{u_num:03d}"
            ts_unit_rows.append([f"L_{l_idx:03d}", unit_serial, lot_id, "LENS_COLLIMATOR", f"{day_str}T08:{u*10:02d}:00+07:00"])
            l_idx += 1

            is_ng = (u >= 4)
            label = "NG" if is_ng else "OK"
            val = f"{0.75 + u * 0.05:.2f}" if is_ng else f"{0.10 + u * 0.02:.2f}"
            fail_code = "ERR_BOW_EXCEEDED" if is_ng else ""

            ts_jig_rows.append([
                f"J_{j_idx:03d}",
                unit_serial,
                "BOWSKEW_4_BEAM",
                f"RUN_{u_num:03d}",
                f"{day_str}T10:{u*10:02d}:00+07:00",
                "BOW_VALUE",
                val,
                "mrad",
                "v1.2",
                "p2.0",
                label,
                fail_code,
                "",
            ])
            j_idx += 1

    make_csv(ts_dir / "component_lots.csv", comp_headers, ts_comp_rows)
    make_csv(ts_dir / "unit_lots.csv", unit_headers, ts_unit_rows)
    make_csv(ts_dir / "jig_outcomes.csv", jig_headers, ts_jig_rows)
    make_xlsx(ts_dir / "component_lots.xlsx", comp_headers, ts_comp_rows)
    make_xlsx(ts_dir / "unit_lots.xlsx", unit_headers, ts_unit_rows)
    make_xlsx(ts_dir / "jig_outcomes.xlsx", jig_headers, ts_jig_rows)

    print(f"LSU fixtures generated successfully in: {base_dir}")


if __name__ == "__main__":
    out = Path("tests/fixtures/lsu_iris")
    generate_all_fixtures(out)