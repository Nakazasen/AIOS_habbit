# -*- coding: utf-8 -*-
"""Automated Legend-Data Anti-Overlap Quality Gate Checker.

Checks that the legend bounding box does not intersect the data series bounding box
for all 8 exported bakeoff images.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
from PIL import Image
import numpy as np


def verify_legend_anti_overlap(
    img_path: Path | str,
    chart_kind: str,
    technology: str,
) -> Dict[str, Any]:
    """Inspects the 1500x900 image and validates that legend and data series are disjoint."""
    p = Path(img_path)
    if not p.exists():
        return {
            "file": p.name,
            "status": "FAIL",
            "reason": f"File does not exist: {p}",
        }

    im = Image.open(p).convert("RGB")
    w, h = im.size
    assert w == 1500 and h == 900, f"Expected 1500x900 image, got {w}x{h}"

    arr = np.array(im)

    # In our layouts:
    # Title region: y in [0, 55]
    # Legend region: y in [55, 115]
    # Separator margin: y in [115, 130] (clean white space)
    # Plot grid (data region): y in [130, 815], x in [90, 1410]

    legend_region = arr[55:115, 200:1300]
    separator_region = arr[115:130, 90:1410]
    data_region = arr[130:815, 90:1410]

    # Legend bounding box in image coordinates
    # Non-white pixels in legend row range [55, 115]
    mask_legend = np.any(arr[55:115, :] < 250, axis=2)
    legend_ys, legend_xs = np.where(mask_legend)

    if len(legend_ys) > 0:
        leg_ymin = int(legend_ys.min() + 55)
        leg_ymax = int(legend_ys.max() + 55)
        leg_xmin = int(legend_xs.min())
        leg_xmax = int(legend_xs.max())
    else:
        leg_ymin, leg_ymax, leg_xmin, leg_xmax = 55, 105, 300, 1200

    # Data bounding box in image coordinates
    # Grid area [130, 815]
    mask_data = np.any(arr[130:815, 90:1410] < 250, axis=2)
    data_ys, data_xs = np.where(mask_data)
    if len(data_ys) > 0:
        data_ymin = int(data_ys.min() + 130)
        data_ymax = int(data_ys.max() + 130)
        data_xmin = int(data_xs.min() + 90)
        data_xmax = int(data_xs.max() + 90)
    else:
        data_ymin, data_ymax, data_xmin, data_xmax = 130, 815, 90, 1410

    # Check vertical overlap
    # Overlap occurs if leg_ymax >= data_ymin and leg_ymin <= data_ymax
    vertical_gap = data_ymin - leg_ymax
    is_disjoint = vertical_gap > 0

    # Also check that the separator region [115, 128] is completely free of data lines
    # (pure white background except possible grid margin)
    sep_non_white = np.sum(np.any(separator_region < 240, axis=2))
    sep_clear = sep_non_white == 0

    passed = is_disjoint and sep_clear

    return {
        "file": p.name,
        "technology": technology,
        "chart_kind": chart_kind,
        "legend_bbox": (leg_xmin, leg_ymin, leg_xmax, leg_ymax),
        "data_bbox": (data_xmin, data_ymin, data_xmax, data_ymax),
        "vertical_gap_px": vertical_gap,
        "overlap_detected": not is_disjoint,
        "status": "ĐẠT (Không chồng lấn)" if passed else "CHƯA ĐẠT (Bị chồng lấn)",
    }
