from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PIL import Image

from aios_habit.ocr_engines import clear_engine_cache, run_paddleocr, run_rapidocr

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _images(path: Path):
    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
        yield path
        return
    for item in sorted(path.rglob("*")):
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            yield item


def _run(engine: str, image):
    if engine == "rapidocr":
        return run_rapidocr(image)
    if engine == "paddleocr":
        return run_paddleocr(image)
    raise ValueError(f"Unsupported benchmark engine: {engine}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local OCR engines sequentially on real page images.")
    parser.add_argument("input", type=Path, help="Image file or directory of rendered PDF page images")
    parser.add_argument("--engines", default="rapidocr", help="Comma-separated: rapidocr,paddleocr")
    parser.add_argument("--output", type=Path, default=Path("ocr_benchmark.jsonl"))
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()

    os.environ["AIOS_OCR_CPU_THREADS"] = str(max(1, min(8, args.threads)))
    engines = [item.strip().lower() for item in args.engines.split(",") if item.strip()]
    images = list(_images(args.input))
    if not images:
        parser.error("No supported images found")

    rows = []
    for engine in engines:
        clear_engine_cache()
        for image_path in images:
            started = time.perf_counter()
            with Image.open(image_path) as image:
                image.load()
                result = _run(engine, image)
            row = {
                "file": str(image_path),
                "engine": result.engine,
                "backend": result.backend,
                "confidence": round(result.confidence, 3),
                "confidence_samples": result.confidence_samples,
                "seconds": round(time.perf_counter() - started, 4),
                "text": result.text,
                "failure_reason": result.failure_reason,
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False))
        clear_engine_cache()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    for engine in engines:
        subset = [row for row in rows if row["engine"] == engine and not row["failure_reason"]]
        if subset:
            print(json.dumps({
                "summary_engine": engine,
                "documents": len(subset),
                "median_seconds": round(statistics.median(row["seconds"] for row in subset), 4),
                "mean_confidence": round(statistics.mean(row["confidence"] for row in subset), 3),
            }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

