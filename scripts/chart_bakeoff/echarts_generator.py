# -*- coding: utf-8 -*-
"""Apache ECharts chart generator and headless Playwright renderer for bakeoff.

Renders high-fidelity, production-grade 1500x900 PNG charts with zero legend overlap.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from playwright.sync_api import sync_playwright, Browser, Page

VENDOR_ECHARTS_JS = Path(__file__).parent / "vendor" / "echarts.min.js"


class EChartsRenderer:
    """Manages headless Playwright Chromium session for fast, offline ECharts rendering."""

    def __init__(self, width: int = 1500, height: int = 900):
        self.width = width
        self.height = height
        self._pw = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

        if VENDOR_ECHARTS_JS.exists():
            self._js_content = VENDOR_ECHARTS_JS.read_text(encoding="utf-8")
        else:
            self._js_content = ""

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        if self._browser is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=True,
                args=["--disable-web-security", "--allow-file-access-from-files", "--no-sandbox"],
            )
            self._page = self._browser.new_page(
                viewport={"width": self.width, "height": self.height},
                device_scale_factor=1,
            )

    def close(self):
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None

    def render_png(self, option: Dict[str, Any]) -> Tuple[bytes, float]:
        """Renders an ECharts option dict to 1500x900 PNG and returns (png_bytes, duration_seconds)."""
        if self._browser is None or self._page is None:
            self.start()

        opt_json = json.dumps(option, ensure_ascii=False)
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #ffffff; width: {self.width}px; height: {self.height}px; overflow: hidden; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; }}
    #chart {{ width: {self.width}px; height: {self.height}px; }}
  </style>
  <script>{self._js_content}</script>
</head>
<body>
  <div id="chart"></div>
  <script>
    var chartDom = document.getElementById('chart');
    var myChart = echarts.init(chartDom, null, {{ renderer: 'canvas', animation: false }});
    var option = {opt_json};
    myChart.setOption(option);
    window.chartReady = true;
  </script>
</body>
</html>"""

        t0 = time.perf_counter()
        self._page.set_content(html, wait_until="load")
        self._page.wait_for_function("window.chartReady === true")
        png_bytes = self._page.locator("#chart").screenshot(type="png")
        duration = time.perf_counter() - t0
        return png_bytes, duration


def build_run_sma_echarts(
    times: List[str],
    raw_y: List[float],
    sma_y: List[Optional[float]],
    metric_name: str = "SKEW:BLACK",
    jig_id: str = "2ND-1002",
    unit: str = "µm",
) -> Dict[str, Any]:
    """Builds ECharts option for Run chart + SMA(20). Legend strictly outside plot area."""
    time_sampled = times
    # Sample ticks for X axis to prevent crowding
    tick_interval = max(1, len(times) // 8)

    option = {
        "backgroundColor": "#ffffff",
        "title": {
            "text": f"Biểu đồ xu hướng (Run Chart) — {metric_name} [{unit}] — JIG {jig_id}",
            "subtext": f"N = {len(raw_y)} điểm đo thực tế | Phủ đường trung bình động SMA(20) nét đứt tím",
            "left": "center",
            "top": 15,
            "textStyle": {"fontSize": 18, "fontWeight": "bold", "color": "#1a237e", "fontFamily": "Segoe UI"},
            "subtextStyle": {"fontSize": 12, "color": "#546e7a", "fontFamily": "Segoe UI"},
        },
        "legend": {
            "orient": "horizontal",
            "top": 65,
            "left": "center",
            "itemGap": 30,
            "itemWidth": 25,
            "itemHeight": 14,
            "textStyle": {"fontSize": 13, "color": "#263238", "fontFamily": "Segoe UI"},
            "data": [
                {"name": f"Giá trị đo ({metric_name})", "icon": "roundRect"},
                {"name": "Đường SMA(20)", "icon": "line"},
            ],
        },
        "grid": {
            "left": 90,
            "right": 90,
            "top": 130,
            "bottom": 85,
            "containLabel": False,
        },
        "xAxis": {
            "type": "category",
            "data": time_sampled,
            "axisLabel": {
                "interval": tick_interval,
                "rotate": 20,
                "fontSize": 10,
                "color": "#37474f",
                "fontFamily": "Segoe UI",
            },
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"show": True, "lineStyle": {"color": "#eceff1", "type": "dashed"}},
            "name": "Thời gian đo lường",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
        },
        "yAxis": {
            "type": "value",
            "name": f"Độ lệch [{unit}]",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
            "axisLabel": {"fontSize": 11, "color": "#37474f", "fontFamily": "Segoe UI"},
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"lineStyle": {"color": "#eceff1", "type": "dashed"}},
        },
        "series": [
            {
                "name": f"Giá trị đo ({metric_name})",
                "type": "line",
                "data": raw_y,
                "showSymbol": True,
                "symbol": "circle",
                "symbolSize": 5,
                "itemStyle": {"color": "#1565c0"},
                "lineStyle": {"color": "#1565c0", "width": 1.8},
                "z": 2,
            },
            {
                "name": "Đường SMA(20)",
                "type": "line",
                "data": [v if v is not None else "-" for v in sma_y],
                "showSymbol": False,
                "itemStyle": {"color": "#7b1fa2"},
                "lineStyle": {"color": "#7b1fa2", "width": 2.6, "type": "dashed"},
                "z": 4,
            },
        ],
    }
    return option


def build_spc_echarts(
    times: List[str],
    vals: List[float],
    cl: float = 4.60,
    ucl: float = 4.85,
    lcl: float = 4.35,
    sigma: float = 0.08,
    jig_id: str = "JIG-1003_1",
    metric_name: str = "MeasureFieldCurvatureYellow",
    unit: str = "sec",
) -> Dict[str, Any]:
    """Builds ECharts option for SPC chart with CL/UCL/LCL, Zone A/B/C, and NG anomaly markers.
    Legend is positioned horizontally at top (Y=65), strictly outside grid (top=130),
    eliminating any occlusion of rising NG data points in top-right!
    """
    normal_data: List[Optional[float]] = []
    ng_data: List[Optional[float]] = []
    for v in vals:
        if v > ucl or v < lcl:
            normal_data.append(v)
            ng_data.append(v)
        else:
            normal_data.append(v)
            ng_data.append(None)

    ng_count = sum(1 for v in vals if v > ucl or v < lcl)

    option = {
        "backgroundColor": "#ffffff",
        "title": {
            "text": f"Biểu đồ kiểm soát SPC — {metric_name} — JIG {jig_id} [{unit}]",
            "subtext": f"Đoạn trôi dốc tuần 21-28 ({ng_count} điểm NG liên tiếp vượt UCL) | CL={cl:.2f}, UCL={ucl:.2f}, LCL={lcl:.2f}, σ={sigma:.2f}",
            "left": "center",
            "top": 15,
            "textStyle": {"fontSize": 18, "fontWeight": "bold", "color": "#1a237e", "fontFamily": "Segoe UI"},
            "subtextStyle": {"fontSize": 12, "color": "#546e7a", "fontFamily": "Segoe UI"},
        },
        "legend": {
            "orient": "horizontal",
            "top": 65,
            "left": "center",
            "itemGap": 25,
            "itemWidth": 25,
            "itemHeight": 14,
            "textStyle": {"fontSize": 12.5, "color": "#263238", "fontFamily": "Segoe UI"},
            "data": [
                {"name": "Dữ liệu đo tuần", "icon": "roundRect"},
                {"name": f"Điểm vượt ngưỡng / NG ({ng_count})", "icon": "circle"},
                {"name": f"UCL (+3σ) = {ucl:.2f}", "icon": "line"},
                {"name": f"CL (Trung tâm) = {cl:.2f}", "icon": "line"},
                {"name": f"LCL (-3σ) = {lcl:.2f}", "icon": "line"},
            ],
        },
        "grid": {
            "left": 90,
            "right": 90,
            "top": 130,
            "bottom": 85,
            "containLabel": False,
        },
        "xAxis": {
            "type": "category",
            "data": times,
            "axisLabel": {
                "interval": 0,
                "rotate": 25,
                "fontSize": 10,
                "color": "#37474f",
                "fontFamily": "Segoe UI",
            },
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"show": True, "lineStyle": {"color": "#eceff1", "type": "dashed"}},
            "name": "Tuần sản xuất",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
        },
        "yAxis": {
            "type": "value",
            "min": 4.25,
            "max": 5.40,
            "name": f"Độ cong [{unit}]",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
            "axisLabel": {"fontSize": 11, "color": "#37474f", "fontFamily": "Segoe UI"},
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"lineStyle": {"color": "#eceff1", "type": "dashed"}},
        },
        "series": [
            {
                "name": "Dữ liệu đo tuần",
                "type": "line",
                "data": normal_data,
                "showSymbol": True,
                "symbol": "circle",
                "symbolSize": 7,
                "itemStyle": {"color": "#1565c0"},
                "lineStyle": {"color": "#1565c0", "width": 2.2},
                "z": 3,
                "markArea": {
                    "silent": True,
                    "itemStyle": {"opacity": 0.45},
                    "data": [
                        [
                            {"name": "Zone A (An toàn ±1σ)", "yAxis": cl - sigma, "itemStyle": {"color": "rgba(76, 175, 80, 0.16)"}},
                            {"yAxis": cl + sigma},
                        ],
                        [
                            {"name": "Zone B (Cảnh báo 1σ-2σ)", "yAxis": cl + sigma, "itemStyle": {"color": "rgba(255, 152, 0, 0.16)"}},
                            {"yAxis": cl + 2 * sigma},
                        ],
                        [
                            {"yAxis": cl - 2 * sigma, "itemStyle": {"color": "rgba(255, 152, 0, 0.16)"}},
                            {"yAxis": cl - sigma},
                        ],
                        [
                            {"name": "Zone C (Nguy cơ 2σ-3σ)", "yAxis": cl + 2 * sigma, "itemStyle": {"color": "rgba(244, 67, 54, 0.16)"}},
                            {"yAxis": ucl},
                        ],
                        [
                            {"yAxis": lcl, "itemStyle": {"color": "rgba(244, 67, 54, 0.16)"}},
                            {"yAxis": cl - 2 * sigma},
                        ],
                    ],
                },
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "data": [
                        {
                            "name": f"UCL (+3σ) = {ucl:.2f}",
                            "yAxis": ucl,
                            "lineStyle": {"color": "#c62828", "width": 2.0, "type": "dashed"},
                            "label": {"position": "end", "formatter": f"UCL={ucl:.2f}", "color": "#c62828", "fontSize": 11},
                        },
                        {
                            "name": f"CL (Trung tâm) = {cl:.2f}",
                            "yAxis": cl,
                            "lineStyle": {"color": "#2e7d32", "width": 2.0, "type": "solid"},
                            "label": {"position": "end", "formatter": f"CL={cl:.2f}", "color": "#2e7d32", "fontSize": 11},
                        },
                        {
                            "name": f"LCL (-3σ) = {lcl:.2f}",
                            "yAxis": lcl,
                            "lineStyle": {"color": "#c62828", "width": 2.0, "type": "dashed"},
                            "label": {"position": "end", "formatter": f"LCL={lcl:.2f}", "color": "#c62828", "fontSize": 11},
                        },
                    ],
                },
            },
            {
                "name": f"Điểm vượt ngưỡng / NG ({ng_count})",
                "type": "scatter",
                "data": [v if v is not None else "-" for v in ng_data],
                "symbol": "circle",
                "symbolSize": 13,
                "itemStyle": {"color": "#d50000", "borderColor": "#ffffff", "borderWidth": 2},
                "z": 5,
            },
            # Dummy series to give legend handles for limits
            {"name": f"UCL (+3σ) = {ucl:.2f}", "type": "line", "data": [], "itemStyle": {"color": "#c62828"}, "lineStyle": {"type": "dashed"}},
            {"name": f"CL (Trung tâm) = {cl:.2f}", "type": "line", "data": [], "itemStyle": {"color": "#2e7d32"}, "lineStyle": {"type": "solid"}},
            {"name": f"LCL (-3σ) = {lcl:.2f}", "type": "line", "data": [], "itemStyle": {"color": "#c62828"}, "lineStyle": {"type": "dashed"}},
        ],
    }
    return option


def build_pareto_echarts(
    categories: List[str],
    frequencies: List[int],
    title_suffix: str = "JIG 2ND-1002",
) -> Dict[str, Any]:
    """Builds ECharts option for Pareto Chart (Frequency Bar + Cumulative % Line + 80% Cutoff)."""
    total = sum(frequencies)
    cum_pct = []
    run = 0.0
    for f in frequencies:
        run += f
        cum_pct.append(round((run / total) * 100.0, 2))

    option = {
        "backgroundColor": "#ffffff",
        "title": {
            "text": f"Biểu đồ Pareto phân tích lỗi kiểm tra — {title_suffix}",
            "subtext": f"Tổng cộng {total:,} lượt lỗi ghi nhận | Quy tắc 80/20 xác định nguyên nhân cốt lõi",
            "left": "center",
            "top": 15,
            "textStyle": {"fontSize": 18, "fontWeight": "bold", "color": "#1a237e", "fontFamily": "Segoe UI"},
            "subtextStyle": {"fontSize": 12, "color": "#546e7a", "fontFamily": "Segoe UI"},
        },
        "legend": {
            "orient": "horizontal",
            "top": 65,
            "left": "center",
            "itemGap": 30,
            "itemWidth": 25,
            "itemHeight": 14,
            "textStyle": {"fontSize": 13, "color": "#263238", "fontFamily": "Segoe UI"},
            "data": [
                {"name": "Tần suất lỗi (Số lượng)", "icon": "roundRect"},
                {"name": "Phần trăm lũy kế (%)", "icon": "line"},
                {"name": "Ngưỡng 80% Pareto", "icon": "line"},
            ],
        },
        "grid": {
            "left": 90,
            "right": 90,
            "top": 130,
            "bottom": 85,
            "containLabel": False,
        },
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {
                "interval": 0,
                "rotate": 20,
                "fontSize": 11,
                "color": "#37474f",
                "fontFamily": "Segoe UI",
            },
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"show": False},
            "name": "Hạng mục kiểm tra / Mã lỗi",
            "nameLocation": "middle",
            "nameGap": 48,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Tần suất [lần]",
                "nameLocation": "middle",
                "nameGap": 55,
                "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#1565c0"},
                "axisLabel": {"fontSize": 11, "color": "#1565c0", "fontFamily": "Segoe UI"},
                "axisLine": {"lineStyle": {"color": "#1565c0"}},
                "splitLine": {"lineStyle": {"color": "#eceff1", "type": "dashed"}},
            },
            {
                "type": "value",
                "min": 0,
                "max": 105,
                "name": "Lũy kế [%]",
                "nameLocation": "middle",
                "nameGap": 55,
                "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#ef6c00"},
                "axisLabel": {
                    "formatter": "{value}%",
                    "fontSize": 11,
                    "color": "#ef6c00",
                    "fontFamily": "Segoe UI",
                },
                "axisLine": {"lineStyle": {"color": "#ef6c00"}},
                "splitLine": {"show": False},
            },
        ],
        "series": [
            {
                "name": "Tần suất lỗi (Số lượng)",
                "type": "bar",
                "data": frequencies,
                "barWidth": "48%",
                "itemStyle": {
                    "color": "#1565c0",
                    "borderRadius": [4, 4, 0, 0],
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c}",
                    "fontSize": 11,
                    "fontWeight": "bold",
                    "color": "#1565c0",
                },
                "yAxisIndex": 0,
                "z": 2,
            },
            {
                "name": "Phần trăm lũy kế (%)",
                "type": "line",
                "data": cum_pct,
                "yAxisIndex": 1,
                "itemStyle": {"color": "#ef6c00"},
                "lineStyle": {"color": "#ef6c00", "width": 2.6},
                "symbol": "circle",
                "symbolSize": 8,
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{c}%",
                    "fontSize": 10.5,
                    "fontWeight": "bold",
                    "color": "#e65100",
                },
                "z": 4,
            },
            {
                "name": "Ngưỡng 80% Pareto",
                "type": "line",
                "yAxisIndex": 1,
                "data": [80.0] * len(categories),
                "itemStyle": {"color": "#c62828"},
                "lineStyle": {"color": "#c62828", "width": 2.0, "type": "dashed"},
                "symbol": "none",
                "z": 3,
            },
        ],
    }
    return option


def build_histogram_echarts(
    bin_labels: List[str],
    counts: List[int],
    mean_val: float,
    metric_name: str = "SKEW:BLACK",
    unit: str = "µm",
) -> Dict[str, Any]:
    """Builds ECharts option for Histogram chart with vertical Mean line and clean layout."""
    option = {
        "backgroundColor": "#ffffff",
        "title": {
            "text": f"Histogram phân bố giá trị đo — {metric_name} [{unit}]",
            "subtext": f"Phân bố tần suất qua các khoảng đo | Giá trị trung bình: {mean_val:.2f} {unit}",
            "left": "center",
            "top": 15,
            "textStyle": {"fontSize": 18, "fontWeight": "bold", "color": "#1a237e", "fontFamily": "Segoe UI"},
            "subtextStyle": {"fontSize": 12, "color": "#546e7a", "fontFamily": "Segoe UI"},
        },
        "legend": {
            "orient": "horizontal",
            "top": 65,
            "left": "center",
            "itemGap": 30,
            "itemWidth": 25,
            "itemHeight": 14,
            "textStyle": {"fontSize": 13, "color": "#263238", "fontFamily": "Segoe UI"},
            "data": [
                {"name": "Tần suất (Số mẫu)", "icon": "roundRect"},
                {"name": f"Trung bình = {mean_val:.2f}", "icon": "line"},
            ],
        },
        "grid": {
            "left": 90,
            "right": 90,
            "top": 130,
            "bottom": 85,
            "containLabel": False,
        },
        "xAxis": {
            "type": "category",
            "data": bin_labels,
            "axisLabel": {
                "interval": 0,
                "rotate": 20,
                "fontSize": 10.5,
                "color": "#37474f",
                "fontFamily": "Segoe UI",
            },
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"show": False},
            "name": f"Khoảng giá trị đo [{unit}]",
            "nameLocation": "middle",
            "nameGap": 48,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
        },
        "yAxis": {
            "type": "value",
            "name": "Tần suất xuất hiện [lần]",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#263238"},
            "axisLabel": {"fontSize": 11, "color": "#37474f", "fontFamily": "Segoe UI"},
            "axisLine": {"lineStyle": {"color": "#cfd8dc"}},
            "splitLine": {"lineStyle": {"color": "#eceff1", "type": "dashed"}},
        },
        "series": [
            {
                "name": "Tần suất (Số mẫu)",
                "type": "bar",
                "data": counts,
                "barWidth": "88%",
                "itemStyle": {
                    "color": "#1565c0",
                    "borderColor": "#ffffff",
                    "borderWidth": 1.5,
                    "borderRadius": [3, 3, 0, 0],
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c}",
                    "fontSize": 10.5,
                    "color": "#1565c0",
                    "fontWeight": "bold",
                },
                "z": 2,
            },
            {
                "name": f"Trung bình = {mean_val:.2f}",
                "type": "line",
                "data": [],
                "itemStyle": {"color": "#c62828"},
                "lineStyle": {"color": "#c62828", "width": 2.2, "type": "dashed"},
            },
        ],
    }
    return option


def build_large_n_echarts(
    x_data: List[int],
    y_data: List[float],
    use_lttb: bool = True,
    metric_name: str = "BOW:BLACK:-70",
    unit: str = "µm",
) -> Dict[str, Any]:
    """Builds ECharts option for performance testing with >= 10,000 points."""
    sampling_mode = "lttb" if use_lttb else None
    option = {
        "backgroundColor": "#ffffff",
        "title": {
            "text": f"ECharts Benchmark (N = {len(y_data):,} điểm) — {metric_name} [{unit}]",
            "subtext": f"Cấu hình: sampling={sampling_mode}, large={use_lttb}",
            "left": "center",
            "top": 15,
            "textStyle": {"fontSize": 18, "fontWeight": "bold", "color": "#1a237e"},
            "subtextStyle": {"fontSize": 12, "color": "#546e7a"},
        },
        "legend": {
            "orient": "horizontal",
            "top": 65,
            "left": "center",
            "data": ["Chuỗi dữ liệu lớn"],
        },
        "grid": {"left": 80, "right": 80, "top": 120, "bottom": 70},
        "xAxis": {"type": "category", "data": [str(i) for i in x_data]},
        "yAxis": {"type": "value"},
        "series": [
            {
                "name": "Chuỗi dữ liệu lớn",
                "type": "line",
                "data": y_data,
                "sampling": sampling_mode,
                "large": use_lttb,
                "showSymbol": False,
                "lineStyle": {"color": "#1565c0", "width": 1.0},
            }
        ],
    }
    return option
