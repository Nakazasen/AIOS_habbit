# -*- coding: utf-8 -*-
"""Đo lường trước/sau tích hợp Indra OCR cho 3 tệp mẫu và 1 tệp đối chứng âm.

Chạy nghiệm thu theo vé DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE:
(a) Báo cáo 8D nhà cung cấp KDTVN (5 trang)
(b) Sơ đồ mạch 7PA1187DCZ (11 trang)
(c) Tài liệu scan thuần C6610 (31 trang)
(d) Đối chứng âm Service manual 165MB (1.758 trang)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Đảm bảo output tiếng Việt không lỗi mã hóa cp932 trên Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Đảm bảo import đúng src
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aios_habit.document_extractors import _extract_pdf, extract_text_chunks_from_file
from aios_habit.indra_ocr_adapter import (
    ENV_INDRA_OCR_ENABLED,
    get_last_indra_stats,
)

FILES = {
    "8d": {
        "name": "Báo cáo 8D nhà cung cấp KDTVN",
        "path": Path(r"C:\tmp\indra_test_files\8d_kdtvn_5p.pdf"),
        "pages": 5,
        "type": "PDF kỹ thuật chữ mỏng + bảng biểu",
    },
    "7pa": {
        "name": "Sơ đồ mạch 7PA1187DCZ",
        "path": Path(r"C:\tmp\indra_test_files\7pa1187dcz_11p.pdf"),
        "pages": 11,
        "type": "Sơ đồ mạch điện tử + tiếng Nhật",
    },
    "c6610": {
        "name": "Tài liệu scan thuần C6610 (N00137687_thực hành)",
        "path": Path(r"C:\tmp\indra_test_files\c6610_n00137687_scan_31p.pdf"),
        "pages": 31,
        "type": "Tài liệu scan thuần 100% không có lớp chữ",
    },
    "smkdj": {
        "name": "Service manual 2xd_smkdj_jpn (Đối chứng âm)",
        "path": Path(r"C:\tmp\indra_test_files\2xd_smkdj_jpn_service_manual_1758p.pdf"),
        "pages": 1758,
        "type": "Service manual dung lượng lớn 165MB",
    },
}


def measure_old_path(file_path: Path) -> dict:
    """Đo đường cũ khi tắt cấu hình Indra."""
    os.environ[ENV_INDRA_OCR_ENABLED] = "0"
    t0 = time.perf_counter()
    results = _extract_pdf(file_path)
    elapsed = time.perf_counter() - t0

    full_text = "".join(r.text for r in results)
    ocr_pages = sum(1 for r in results if "ocr" in r.extractor_name.lower())
    return {
        "chars": len(full_text),
        "bytes": len(full_text.encode("utf-8")),
        "ocr_pages": ocr_pages,
        "elapsed_seconds": round(elapsed, 4),
        "results_count": len(results),
    }


def measure_new_path(file_path: Path) -> dict:
    """Đo đường mới khi bật Indra OCR."""
    os.environ[ENV_INDRA_OCR_ENABLED] = "1"
    t0 = time.perf_counter()
    results = _extract_pdf(file_path)
    elapsed = time.perf_counter() - t0

    full_text = "".join(r.text for r in results)
    stats = get_last_indra_stats(file_path)

    ocr_pages = stats.ocr_pages if stats else 0
    used_indra = stats.used_indra if stats else False
    gate_rule = stats.gate_rule if stats else "none"

    return {
        "chars": len(full_text),
        "bytes": len(full_text.encode("utf-8")),
        "ocr_pages": ocr_pages,
        "elapsed_seconds": round(elapsed, 4),
        "results_count": len(results),
        "used_indra": used_indra,
        "gate_rule": gate_rule,
        "stats": stats.to_dict() if stats else {},
    }


def main():
    print("=" * 80)
    print("BẮT ĐẦU ĐO LƯỜNG TRƯỚC VÀ SAU TÍCH HỢP INDRA OCR")
    print("=" * 80)

    summary = {}

    for key, info in FILES.items():
        p = info["path"]
        if not p.exists():
            print(f"❌ Không tìm thấy tệp: {p}")
            continue

        print(f"\n--- Đang đo: {info['name']} ({info['pages']} trang, {p.stat().st_size:,} bytes) ---")

        # 1. Đường cũ
        print("  -> Đo đường cũ (AIOS_INDRA_OCR_ENABLED=0)...", flush=True)
        old_metrics = measure_old_path(p)
        print(f"     Đường cũ: {old_metrics['chars']:,} ký tự ({old_metrics['bytes']:,} bytes), "
              f"{old_metrics['ocr_pages']} trang OCR, {old_metrics['elapsed_seconds']:.2f}s")

        # 2. Đường mới
        print("  -> Đo đường mới (AIOS_INDRA_OCR_ENABLED=1)...", flush=True)
        new_metrics = measure_new_path(p)
        print(f"     Đường mới: {new_metrics['chars']:,} ký tự ({new_metrics['bytes']:,} bytes), "
              f"{new_metrics['ocr_pages']} trang OCR, {new_metrics['elapsed_seconds']:.2f}s, "
              f"used_indra={new_metrics['used_indra']}, gate={new_metrics['gate_rule']}")

        summary[key] = {
            "name": info["name"],
            "type": info["type"],
            "pages": info["pages"],
            "file_size": p.stat().st_size,
            "old": old_metrics,
            "new": new_metrics,
        }

    # Xuất tệp JSON kết quả
    out_json = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\indra_before_after_measurement.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nĐã ghi kết quả đo lường vào: {out_json}")


if __name__ == "__main__":
    main()
