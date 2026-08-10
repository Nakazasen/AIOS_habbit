from __future__ import annotations

import gc
import importlib.util
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from aios_habit.ocr_engines import clear_engine_cache, ocr_cpu_threads


@dataclass(frozen=True)
class DeepParseResult:
    text: str = ""
    parser: str = "none"
    elapsed_seconds: float = 0.0
    warning: str = ""
    failure_reason: str = ""

    @property
    def succeeded(self) -> bool:
        return bool(self.text.strip()) and not self.failure_reason


def deep_parser_availability() -> dict[str, bool]:
    return {
        "docling": importlib.util.find_spec("docling") is not None,
        "marker": shutil.which("marker_single") is not None,
    }


def _timeout_seconds() -> int:
    try:
        return max(30, min(1800, int(os.environ.get("AIOS_DEEP_PARSE_TIMEOUT_SECONDS", "300"))))
    except (TypeError, ValueError):
        return 300


def run_docling(path: str | Path) -> DeepParseResult:
    started = time.perf_counter()
    if not deep_parser_availability()["docling"]:
        return DeepParseResult(parser="docling", failure_reason="docling_unavailable")
    clear_engine_cache()
    gc.collect()
    try:
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions(
            document_timeout=float(_timeout_seconds()),
            accelerator_options=AcceleratorOptions(
                num_threads=ocr_cpu_threads(), device=AcceleratorDevice.CPU,
            ),
            enable_remote_services=False,
            allow_external_plugins=False,
            do_ocr=True,
            do_table_structure=True,
            do_chart_extraction=False,
            do_picture_description=False,
            ocr_batch_size=1,
            layout_batch_size=1,
            table_batch_size=1,
            queue_max_size=4,
        )
        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
        )
        conversion = converter.convert(str(path))
        document = getattr(conversion, "document", None)
        text = document.export_to_markdown().strip() if document is not None else ""
        return DeepParseResult(
            text=text,
            parser="docling-cpu",
            elapsed_seconds=time.perf_counter() - started,
            failure_reason="" if text else "docling_returned_no_text",
        )
    except Exception as exc:  # noqa: BLE001
        return DeepParseResult(
            parser="docling-cpu",
            elapsed_seconds=time.perf_counter() - started,
            failure_reason=f"docling_failed: {type(exc).__name__}: {exc}",
        )
    finally:
        gc.collect()


def run_marker(path: str | Path) -> DeepParseResult:
    started = time.perf_counter()
    executable = shutil.which("marker_single")
    if not executable:
        return DeepParseResult(parser="marker", failure_reason="marker_unavailable")
    clear_engine_cache()
    gc.collect()
    try:
        with tempfile.TemporaryDirectory(prefix="aios_marker_") as temp_dir:
            command = [
                executable, str(path), "--output_dir", temp_dir,
                "--output_format", "markdown", "--disable_image_extraction",
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=_timeout_seconds(), check=False,
                env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
            )
            markdown_files = sorted(Path(temp_dir).rglob("*.md"))
            text = "\n\n".join(
                item.read_text(encoding="utf-8", errors="replace").strip()
                for item in markdown_files
            ).strip()
            if completed.returncode != 0 and not text:
                reason = (completed.stderr or completed.stdout or "marker failed").strip()[-1000:]
                return DeepParseResult(
                    parser="marker-cpu", elapsed_seconds=time.perf_counter() - started,
                    failure_reason=f"marker_failed: {reason}",
                )
            return DeepParseResult(
                text=text, parser="marker-cpu",
                elapsed_seconds=time.perf_counter() - started,
                failure_reason="" if text else "marker_returned_no_text",
            )
    except Exception as exc:  # noqa: BLE001
        return DeepParseResult(
            parser="marker-cpu", elapsed_seconds=time.perf_counter() - started,
            failure_reason=f"marker_failed: {type(exc).__name__}: {exc}",
        )
    finally:
        gc.collect()


def run_deep_parser(path: str | Path, mode: str) -> DeepParseResult:
    """Run at most one memory-heavy parser at a time, with documented fallback."""
    if mode == "offline_max":
        marker = run_marker(path)
        if marker.succeeded:
            return marker
        docling = run_docling(path)
        if docling.succeeded:
            return DeepParseResult(
                **{**docling.__dict__, "warning": marker.failure_reason or marker.warning}
            )
        return DeepParseResult(
            parser="marker+docling",
            elapsed_seconds=marker.elapsed_seconds + docling.elapsed_seconds,
            warning=marker.failure_reason,
            failure_reason=docling.failure_reason or marker.failure_reason,
        )
    return run_docling(path)

