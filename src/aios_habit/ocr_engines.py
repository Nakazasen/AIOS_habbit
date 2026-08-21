from __future__ import annotations

import importlib.util
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

DEFAULT_OCR_MODE = "balanced"
SUPPORTED_OCR_MODES = {"fast", "balanced", "deep", "auto_deep", "offline_max", "legacy"}
_ENGINE_LOCK = threading.RLock()
_ENGINE_CACHE: dict[str, Any] = {}


@dataclass(frozen=True)
class OCREngineResult:
    text: str = ""
    confidence: float = 0.0
    confidence_samples: int = 0
    engine: str = "none"
    backend: str = ""
    model: str = ""
    preprocessing: str = ""
    elapsed_seconds: float = 0.0
    warning: str = ""
    failure_reason: str = ""

    @property
    def succeeded(self) -> bool:
        return bool(self.text.strip()) and not self.failure_reason


def ocr_mode() -> str:
    value = os.environ.get("AIOS_OCR_MODE", DEFAULT_OCR_MODE).strip().lower()
    return value if value in SUPPORTED_OCR_MODES else DEFAULT_OCR_MODE


def ocr_cpu_threads() -> int:
    default = min(4, os.cpu_count() or 1)
    try:
        return max(1, min(8, int(os.environ.get("AIOS_OCR_CPU_THREADS", default))))
    except (TypeError, ValueError):
        return default


def configured_engine_order(mode: str | None = None) -> list[str]:
    selected_mode = mode or ocr_mode()
    explicit = os.environ.get("AIOS_OCR_ENGINE_ORDER", "").strip()
    if explicit:
        requested = [item.strip().lower() for item in explicit.split(",") if item.strip()]
    elif selected_mode == "legacy":
        requested = ["tesseract"]
    elif selected_mode == "fast":
        requested = ["rapidocr"]
    else:
        requested = ["rapidocr", "paddleocr", "tesseract"]
    allowed = {"rapidocr", "paddleocr", "tesseract"}
    return list(dict.fromkeys(item for item in requested if item in allowed))


def engine_availability() -> dict[str, bool]:
    return {
        "rapidocr": importlib.util.find_spec("rapidocr") is not None
        and importlib.util.find_spec("onnxruntime") is not None,
        "paddleocr": importlib.util.find_spec("paddleocr") is not None
        and importlib.util.find_spec("paddle") is not None,
        "tesseract": importlib.util.find_spec("pytesseract") is not None,
    }


def clear_engine_cache() -> None:
    """Release model references before switching to a heavy document pipeline."""
    with _ENGINE_LOCK:
        _ENGINE_CACHE.clear()


def _mean_confidence(scores: Iterable[Any]) -> tuple[float, int]:
    normalized: list[float] = []
    for raw in scores:
        try:
            score = float(raw)
        except (TypeError, ValueError):
            continue
        normalized.append(score * 100.0 if 0.0 <= score <= 1.0 else score)
    return (sum(normalized) / len(normalized), len(normalized)) if normalized else (0.0, 0)


def _rapidocr_instance():
    with _ENGINE_LOCK:
        if "rapidocr" not in _ENGINE_CACHE:
            from rapidocr import RapidOCR

            params = {
                "Global.use_cls": True,
                "EngineConfig.onnxruntime.use_cuda": False,
                "EngineConfig.onnxruntime.intra_op_num_threads": ocr_cpu_threads(),
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            }
            try:
                _ENGINE_CACHE["rapidocr"] = RapidOCR(params=params)
            except Exception:
                _ENGINE_CACHE["rapidocr"] = RapidOCR()
        return _ENGINE_CACHE["rapidocr"]


def run_rapidocr(image: Any) -> OCREngineResult:
    started = time.perf_counter()
    try:
        import numpy as np

        output = _rapidocr_instance()(np.asarray(image.convert("RGB")))
        texts = list(getattr(output, "txts", None) or [])
        scores = list(getattr(output, "scores", None) or [])
        if not texts and isinstance(output, (list, tuple)):
            rows = [row for row in output if isinstance(row, (list, tuple)) and len(row) >= 3]
            texts = [str(row[1]) for row in rows]
            scores = [row[2] for row in rows]
        text = "\n".join(str(item).strip() for item in texts if str(item).strip()).strip()
        confidence, samples = _mean_confidence(scores)
        elapsed = float(getattr(output, "elapse", 0.0) or 0.0)
        return OCREngineResult(
            text=text,
            confidence=confidence,
            confidence_samples=samples,
            engine="rapidocr",
            backend="onnxruntime-cpu",
            model="pp-ocr",
            elapsed_seconds=elapsed or (time.perf_counter() - started),
            failure_reason="" if text else "no_meaningful_text",
        )
    except Exception as exc:  # noqa: BLE001
        return OCREngineResult(
            engine="rapidocr", backend="onnxruntime-cpu",
            elapsed_seconds=time.perf_counter() - started,
            failure_reason=f"rapidocr_failed: {type(exc).__name__}: {exc}",
        )


def _paddleocr_instance():
    with _ENGINE_LOCK:
        if "paddleocr" not in _ENGINE_CACHE:
            from paddleocr import PaddleOCR

            try:
                _ENGINE_CACHE["paddleocr"] = PaddleOCR(
                    device="cpu", enable_mkldnn=True, cpu_threads=ocr_cpu_threads(),
                    use_doc_orientation_classify=True, use_doc_unwarping=False,
                    use_textline_orientation=True,
                )
            except (TypeError, ValueError):
                _ENGINE_CACHE["paddleocr"] = PaddleOCR(
                    use_gpu=False, enable_mkldnn=True, cpu_threads=ocr_cpu_threads(),
                    use_angle_cls=True, show_log=False,
                )
        return _ENGINE_CACHE["paddleocr"]


def _parse_paddle_output(output: Any) -> tuple[list[str], list[float]]:
    texts: list[str] = []
    scores: list[float] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            rec_texts = value.get("rec_texts") or value.get("texts")
            rec_scores = value.get("rec_scores") or value.get("scores")
            if rec_texts:
                texts.extend(str(item) for item in rec_texts)
                scores.extend(float(item) for item in (rec_scores or []))
                return
            for nested in value.values():
                visit(nested)
        elif isinstance(value, (list, tuple)):
            if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], (int, float)):
                texts.append(value[0])
                scores.append(float(value[1]))
                return
            for nested in value:
                visit(nested)
        elif hasattr(value, "json"):
            payload = value.json
            visit(payload() if callable(payload) else payload)
        elif hasattr(value, "res"):
            visit(value.res)

    visit(output)
    return texts, scores


def run_paddleocr(image: Any) -> OCREngineResult:
    started = time.perf_counter()
    try:
        import numpy as np

        engine = _paddleocr_instance()
        pixels = np.asarray(image.convert("RGB"))
        output = engine.predict(pixels) if hasattr(engine, "predict") else engine.ocr(pixels, cls=True)
        texts, scores = _parse_paddle_output(output)
        text = "\n".join(item.strip() for item in texts if item.strip()).strip()
        confidence, samples = _mean_confidence(scores)
        return OCREngineResult(
            text=text, confidence=confidence, confidence_samples=samples,
            engine="paddleocr", backend="paddle-cpu-mkldnn", model="pp-ocr",
            elapsed_seconds=time.perf_counter() - started,
            failure_reason="" if text else "no_meaningful_text",
        )
    except Exception as exc:  # noqa: BLE001
        return OCREngineResult(
            engine="paddleocr", backend="paddle-cpu-mkldnn",
            elapsed_seconds=time.perf_counter() - started,
            failure_reason=f"paddleocr_failed: {type(exc).__name__}: {exc}",
        )


def run_ocr_router(
    image: Any,
    *,
    meaningful: Callable[[str], bool],
    minimum_confidence: float,
    tesseract_fallback: Callable[[Any], OCREngineResult] | None = None,
    mode: str | None = None,
) -> tuple[OCREngineResult, int]:
    """Escalate lightweight local engines only when the quality gate fails."""
    available = engine_availability()
    attempted = 0
    failures: list[str] = []
    last = OCREngineResult(failure_reason="no_ocr_engine_available")
    for engine_name in configured_engine_order(mode):
        if engine_name == "tesseract":
            if tesseract_fallback is None:
                continue
            fallback_res = tesseract_fallback(image)
            if fallback_res is None or (isinstance(fallback_res, OCREngineResult) and (fallback_res.engine == "none" or "unavailable" in fallback_res.failure_reason.lower())):
                result = fallback_res if isinstance(fallback_res, OCREngineResult) else OCREngineResult(engine="none", failure_reason="tesseract_unavailable")
            else:
                attempted += 1
                result = fallback_res if isinstance(fallback_res, OCREngineResult) else OCREngineResult(engine="tesseract")
        elif not available.get(engine_name, False):
            failures.append(f"{engine_name}_unavailable")
            continue
        else:
            attempted += 1
            result = run_rapidocr(image) if engine_name == "rapidocr" else run_paddleocr(image)
        last = result
        if result.succeeded and meaningful(result.text) and result.confidence >= minimum_confidence:
            if failures:
                result = OCREngineResult(**{**result.__dict__, "warning": "; ".join(failures)})
            return result, attempted
        failures.append(result.failure_reason or f"{engine_name}_quality_gate_failed")
    if failures:
        last = OCREngineResult(**{**last.__dict__, "warning": "; ".join(failures)})
    return last, attempted


def ocr_capabilities() -> dict[str, Any]:
    available = engine_availability()
    order = configured_engine_order()
    selected = next((name for name in order if available.get(name)), "none")
    return {
        "ocr_mode": ocr_mode(),
        "ocr_engine_order": order,
        "ocr_selected_engine": selected,
        "ocr_engine_availability": available,
        "ocr_cpu_threads": ocr_cpu_threads(),
    }

