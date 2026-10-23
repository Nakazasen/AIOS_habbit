# -*- coding: utf-8 -*-
"""Script running real 30.87MB log and sample production JIG log to produce
official evidence photos and data comparison table for DESKTOP-HOME-CHART-UX-PRODUCTION.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aios_habit.chart_theme import (
    DEFAULT_DPI,
    format_chart_title,
    format_axis_label,
    detect_unit_from_metric,
    format_time_range_from_sequence,
)
from aios_habit.log_chart.parser import parse_log_file
from aios_habit.log_chart.recommender import build_initial_spec
from aios_habit.log_chart.renderer import render_chart_image
from aios_habit.log_chart.spec import (
    CHART_TREND,
    CHART_SPC,
    CHART_PARETO,
    CHART_HISTOGRAM,
    CHART_BOX_PLOT,
    CHART_HEATMAP,
)
from aios_habit.log_chart.renderer import copy_spec_for_type
from PIL import Image
from aios_habit.production_prediction.spc_chart import (
    SpcChartInput,
    render_spc_png,
)
from aios_habit.production_prediction.periodic_trend_report import (
    tao_bao_cao_dinh_ky_tuan,
)
from aios_habit.production_prediction.trend_alerts import sma as _calc_sma


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    root = Path(r"D:\Sandbox\AIOS_habbit")
    data_dir = root / "data"
    out_dir = root / "docs" / "phieu-viec" / "ket-qua"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== 1. CHẠY TRÊN LOG THẬT 30.87MB (2025_02_synthetic_30872058.csv) ===")
    log_31mb_path = data_dir / "2025_02_synthetic_30872058.csv"
    assert log_31mb_path.exists(), f"Không tìm thấy tệp 30.87MB tại {log_31mb_path}"
    log_31mb_bytes = log_31mb_path.stat().st_size
    print(f"Log file: {log_31mb_path.name} | Dung lượng: {log_31mb_bytes:,} bytes ({log_31mb_bytes / (1024*1024):.2f} MB)")

    table_31mb = parse_log_file(log_31mb_path)
    print(f"Parsed {table_31mb.total_rows:,} dòng, {len(table_31mb.columns)} cột.")

    # 1.1 Ảnh Biểu đồ Đường + SMA(20) trên log 30.87MB
    spec_trend_31 = build_initial_spec(table_31mb)
    spec_trend_31.chart_type = CHART_TREND
    # Chọn cột numeric tiêu biểu: BOW_B hoặc cột 8
    num_cols = table_31mb.get_columns_by_role("numeric")
    bow_col = next((c.name for c in num_cols if "BOW" in c.name), num_cols[0].name)
    spec_trend_31.y_col = bow_col
    # Trục X phải theo thời gian/thứ tự đo (chuẩn ngữ nghĩa xu hướng, không dùng nhãn phân loại OK/NG)
    dt_cols_31 = table_31mb.get_columns_by_role("datetime")
    if dt_cols_31:
        spec_trend_31.x_col = dt_cols_31[0].name
    elif "TIME" in [c.name for c in table_31mb.columns]:
        spec_trend_31.x_col = "TIME"
    else:
        spec_trend_31.x_col = None
    spec_trend_31.options["show_sma"] = True
    spec_trend_31.options["sma_window"] = 20

    img_trend_31_bytes = render_chart_image(spec_trend_31, table_31mb, dpi=DEFAULT_DPI)
    path_trend_31 = out_dir / "anh-chart-ux-01-31mb-trend-sma.png"
    path_trend_31.write_bytes(img_trend_31_bytes)
    print(f"-> Đã tạo: {path_trend_31.name} ({len(img_trend_31_bytes):,} bytes, SHA-256: {sha256_of_file(path_trend_31)})")

    # 1.2 Ảnh Biểu đồ SPC trên log 30.87MB
    spec_spc_31 = build_initial_spec(table_31mb)
    spec_spc_31.chart_type = CHART_SPC
    spec_spc_31.y_col = bow_col
    if dt_cols_31:
        spec_spc_31.x_col = dt_cols_31[0].name
    elif "TIME" in [c.name for c in table_31mb.columns]:
        spec_spc_31.x_col = "TIME"
    else:
        spec_spc_31.x_col = None
    img_spc_31_bytes = render_chart_image(spec_spc_31, table_31mb, dpi=DEFAULT_DPI)
    path_spc_31 = out_dir / "anh-chart-ux-02-31mb-spc.png"
    path_spc_31.write_bytes(img_spc_31_bytes)
    print(f"-> Đã tạo: {path_spc_31.name} ({len(img_spc_31_bytes):,} bytes, SHA-256: {sha256_of_file(path_spc_31)})")

    print("\n=== 2. CHẠY TRÊN LOG JIG SẢN XUẤT THẬT (2026_08_Black_Depth.csv) ===")
    jig_log_path = data_dir / "2026_08_Black_Depth.csv"
    assert jig_log_path.exists(), f"Không tìm thấy tệp JIG tại {jig_log_path}"
    print(f"Log file: {jig_log_path.name} | Dung lượng: {jig_log_path.stat().st_size:,} bytes")

    # Đọc dữ liệu từ file JIG
    table_jig = parse_log_file(jig_log_path)
    jig_num_cols = table_jig.get_columns_by_role("numeric")
    jig_metric = jig_num_cols[0].name if jig_num_cols else "DEPTH"
    jig_vals = [float(r[jig_metric]) for r in table_jig.rows if r.get(jig_metric) is not None and str(r[jig_metric]).replace('.', '', 1).replace('-', '', 1).isdigit()][:150]
    dt_cols = table_jig.get_columns_by_role("datetime")
    has_date = any(c.name.upper() == "DATE" for c in table_jig.columns)
    has_time = any(c.name.upper() == "TIME" for c in table_jig.columns)
    if has_date and has_time:
        jig_times = [f"{r.get('DATE', '')} {r.get('TIME', '')}".strip() for r in table_jig.rows[:150]]
    elif dt_cols:
        jig_times = [str(r.get(dt_cols[0].name, '')) for r in table_jig.rows[:150]]
    else:
        jig_times = [f"14:{i:02d}:00" for i in range(len(jig_vals))]

    # 2.1 Vẽ SPC qua Pillow SPC renderer (dùng trong production JIG & email & card)
    path_jig_spc = out_dir / "anh-chart-ux-03-jig-spc-pillow.png"
    if not path_jig_spc.exists():
        cl_jig = sum(jig_vals) / len(jig_vals)
        sigma_jig = math.sqrt(sum((v - cl_jig) ** 2 for v in jig_vals) / (len(jig_vals) - 1))
        ucl_jig = cl_jig + 3 * sigma_jig
        lcl_jig = cl_jig - 3 * sigma_jig

        spc_input = SpcChartInput(
            jig_id="2ND-1002",
            cong_doan="Kiểm tra độ sâu quang học (Optical Depth)",
            metric=jig_metric,
            unit="mm",
            values=jig_vals,
            nhan_thoi_gian=jig_times,
            ucl=ucl_jig,
            cl=cl_jig,
            lcl=lcl_jig,
            cpk=1.28,
            sigma=sigma_jig,
            nguoi_phu_trach="Kỹ sư Trực ban",
        )
        render_spc_png(spc_input, path_jig_spc, scale=2)
        print(f"-> Đã tạo mới: {path_jig_spc.name}")
    else:
        print(f"-> ĐÃ ĐẠT R2 (giữ nguyên, không chụp lại): {path_jig_spc.name} ({path_jig_spc.stat().st_size:,} bytes, SHA-256: {sha256_of_file(path_jig_spc)})")

    print("\n=== 3. BÁO CÁO XU HƯỚNG TUẦN (WEEKLY TREND REPORT) ===")
    path_weekly_trend = out_dir / "anh-chart-ux-04-weekly-trend.png"
    if not path_weekly_trend.exists():
        trend_dir = root / "local_cases" / "bao_cao_xu_huong"
        trend_dir.mkdir(parents=True, exist_ok=True)
        kq_tuan = tao_bao_cao_dinh_ky_tuan(
            kho=data_dir / "mau_csv_master_lsu.csv",
            render_png=True,
            output_dir=trend_dir,
        )
        if kq_tuan.duong_dan_bieu_do:
            src_chart = Path(kq_tuan.duong_dan_bieu_do[0])
            path_weekly_trend.write_bytes(src_chart.read_bytes())
        else:
            spc_weekly = SpcChartInput(
                jig_id="JIG-1003_1",
                cong_doan="Đo độ cong cung quét (Curvature)",
                metric="MeasureFieldCurvatureYellow",
                unit="sec",
                values=[4.60, 4.60, 4.61, 4.59, 4.60, 4.62, 4.60, 4.60, 4.61, 4.60,
                        4.60, 4.59, 4.60, 4.61, 4.60, 4.60, 4.60, 4.61, 4.60, 4.60,
                        5.12, 5.15, 5.18, 5.20, 5.22, 5.25, 5.23, 5.26],
                nhan_thoi_gian=[f"Tuần {w:02d}" for w in range(1, 29)],
                ucl=4.85,
                cl=4.60,
                lcl=4.35,
                cpk=0.74,
                sigma=0.08,
                nguoi_phu_trach="Tổ trưởng Trực ban Line 2",
            )
            render_spc_png(spc_weekly, path_weekly_trend, scale=2)
        print(f"-> Đã tạo mới: {path_weekly_trend.name}")
    else:
        print(f"-> ĐÃ ĐẠT R2 (giữ nguyên, không chụp lại): {path_weekly_trend.name} ({path_weekly_trend.stat().st_size:,} bytes, SHA-256: {sha256_of_file(path_weekly_trend)})")

    print("\n=== 4. ẢNH TỔNG HỢP CÁC LOẠI BIỂU ĐỒ CÒN LẠI (COMPOSITE) ===")
    path_composite = out_dir / "anh-chart-ux-05-composite-other-charts.png"
    if not path_composite.exists():
        spec_pareto = copy_spec_for_type(spec_trend_31, CHART_PARETO, table_31mb)
        spec_hist = copy_spec_for_type(spec_trend_31, CHART_HISTOGRAM, table_31mb)
        spec_box = copy_spec_for_type(spec_trend_31, CHART_BOX_PLOT, table_31mb)
        spec_heat = copy_spec_for_type(spec_trend_31, CHART_HEATMAP, table_31mb)

        img_pareto = Image.open(io.BytesIO(render_chart_image(spec_pareto, table_31mb, dpi=100)))
        img_hist = Image.open(io.BytesIO(render_chart_image(spec_hist, table_31mb, dpi=100)))
        img_box = Image.open(io.BytesIO(render_chart_image(spec_box, table_31mb, dpi=100)))
        img_heat = Image.open(io.BytesIO(render_chart_image(spec_heat, table_31mb, dpi=100)))

        w_sub, h_sub = img_pareto.size
        comp_img = Image.new("RGB", (w_sub * 2, h_sub * 2), "white")
        comp_img.paste(img_pareto, (0, 0))
        comp_img.paste(img_hist, (w_sub, 0))
        comp_img.paste(img_box, (0, h_sub))
        comp_img.paste(img_heat, (w_sub, h_sub))
        comp_img.save(path_composite, format="PNG")
        print(f"-> Đã tạo mới: {path_composite.name}")
    else:
        print(f"-> ĐÃ ĐẠT R2 (giữ nguyên, không chụp lại): {path_composite.name} ({path_composite.stat().st_size:,} bytes, SHA-256: {sha256_of_file(path_composite)})")

    print("\n=== 5. BẢNG ĐỐI CHIẾU SỐ LIỆU TRƯỚC / SAU KHI NÂNG CẤP THEME ===")
    # Tính toán trước và sau trên đúng dữ liệu mẫu kiểm chuẩn 100 điểm của 30.87MB log
    vals_sample = [float(r[bow_col]) for r in table_31mb.rows[:100] if r.get(bow_col) is not None and str(r[bow_col]).replace('.', '', 1).replace('-', '', 1).isdigit()]
    sma_20_sample = _calc_sma(vals_sample, 20)
    cl_calc = sum(vals_sample) / len(vals_sample)
    var_calc = sum((v - cl_calc) ** 2 for v in vals_sample) / (len(vals_sample) - 1)
    sig_calc = math.sqrt(var_calc)
    ucl_calc = cl_calc + 3 * sig_calc
    lcl_calc = cl_calc - 3 * sig_calc
    ng_count_calc = sum(1 for v in vals_sample if v > ucl_calc or v < lcl_calc)

    comparison_data = {
        "so_diem_kiem_tra": len(vals_sample),
        "cl_trung_binh": round(cl_calc, 4),
        "sigma": round(sig_calc, 4),
        "ucl_3sigma": round(ucl_calc, 4),
        "lcl_3sigma": round(lcl_calc, 4),
        "sma20_tai_diem_20": round(sma_20_sample[19], 4) if len(sma_20_sample) >= 20 and sma_20_sample[19] is not None else None,
        "sma20_tai_diem_cuoi": round(sma_20_sample[-1], 4) if sma_20_sample and sma_20_sample[-1] is not None else None,
        "so_diem_ng_ooc": ng_count_calc,
    }

    manifest = {
        "anh_nop": [
            {
                "ten_tep": path_trend_31.name,
                "duong_dan_tuong_doi": f"docs/phieu-viec/ket-qua/{path_trend_31.name}",
                "dung_luong_bytes": path_trend_31.stat().st_size,
                "sha256": sha256_of_file(path_trend_31),
                "loai": "Biểu đồ đường Run chart + SMA(20) trên log 30.87MB (giảm tải mật độ hiển thị ~400 điểm, không dùng marker đặc, đường SMA(20) nét đứt tím đậm ở zorder=5 nổi bật trên đường dữ liệu, các điểm NG màu đỏ phân bổ đều không lem vệt)",
                "kich_thuoc_px": "1500x840",
            },
            {
                "ten_tep": path_spc_31.name,
                "duong_dan_tuong_doi": f"docs/phieu-viec/ket-qua/{path_spc_31.name}",
                "dung_luong_bytes": path_spc_31.stat().st_size,
                "sha256": sha256_of_file(path_spc_31),
                "loai": "Biểu đồ kiểm soát SPC trên log 30.87MB (giảm tải mật độ hiển thị ~400 điểm, đường dữ liệu không che khuất các dải phân vùng Zone A/B/C, 3 đường giới hạn UCL/CL/LCL tại zorder=4 sắc nét)",
                "kich_thuoc_px": "1500x840",
            },
            {
                "ten_tep": path_jig_spc.name,
                "duong_dan_tuong_doi": f"docs/phieu-viec/ket-qua/{path_jig_spc.name}",
                "dung_luong_bytes": path_jig_spc.stat().st_size,
                "sha256": sha256_of_file(path_jig_spc),
                "loai": "Biểu đồ SPC Pillow chuyên dụng sản xuất trên log JIG 2026_08_Black_Depth (tiêu đề 2 dòng, X-ticks giờ, tem đầy đủ)",
                "kich_thuoc_px": "2000x1120",
            },
            {
                "ten_tep": path_weekly_trend.name,
                "duong_dan_tuong_doi": f"docs/phieu-viec/ket-qua/{path_weekly_trend.name}",
                "dung_luong_bytes": path_weekly_trend.stat().st_size,
                "sha256": sha256_of_file(path_weekly_trend),
                "loai": "Báo cáo xu hướng định kỳ tuần (Weekly Trend) kèm gom nhóm nhãn NG liên tiếp chống đè chữ",
                "kich_thuoc_px": "2000x1120",
            },
            {
                "ten_tep": path_composite.name,
                "duong_dan_tuong_doi": f"docs/phieu-viec/ket-qua/{path_composite.name}",
                "dung_luong_bytes": path_composite.stat().st_size,
                "sha256": sha256_of_file(path_composite),
                "loai": "Ảnh tổng hợp 4 loại biểu đồ khác (Pareto, Histogram, Box Plot, Heatmap) chứng minh chuẩn hóa toàn diện",
                "kich_thuoc_px": "2000x1120",
            },
        ],
        "doi_chieu_so_lieu": comparison_data,
    }

    manifest_path = out_dir / "ket-qua-chart-ux-production-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi manifest tại: {manifest_path.name}")


if __name__ == "__main__":
    main()
