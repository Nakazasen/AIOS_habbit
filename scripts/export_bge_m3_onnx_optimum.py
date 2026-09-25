"""Export local BGE-M3 PyTorch tree to ONNX via optimum, then dynamic-int8 quantize.

Home-machine path: this checkout has no prebuilt ``onnx/model.onnx`` inside
``local_runs/retrieval_models/bge-m3-5617a9f`` (unlike the company machine),
so FIX 2 must re-export from the 2.27 GiB ``pytorch_model.bin`` first.

Memory guard: refuse to start unless free RAM exceeds ``--min-free-gb``
(default 6.0). BGE-M3 is XLM-Roberta (24 layers, 1024 hidden, 250002 vocab);
the export loads fp32 PyTorch weights (~2.3 GB) plus the ONNX encoder copy,
so a laptop needs the headroom the ticket asks for.

Output defaults to ``models/bge-m3-onnx-int8/`` plus a sibling checksum file.
The directory is gitignored (``/models/``). Runtime stays on PyTorch until
``BGE_BACKEND=onnx_int8``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f"
DEFAULT_OUTPUT = REPO_ROOT / "models" / "bge-m3-onnx-int8"
_TOKENIZER_FILES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
    "config.json",
)
_TIMINGS: dict[str, float] = {}


def _stage(name: str, started: float) -> None:
    _TIMINGS[name] = time.perf_counter() - started
    print(f"[export] stage {name}: {_TIMINGS[name]:.1f}s", flush=True)


def free_ram_gb() -> float:
    try:
        import psutil

        return psutil.virtual_memory().available / (1024**3)
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes

            class _Mem(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = _Mem()
            mem.dwLength = ctypes.sizeof(_Mem)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return mem.ullAvailPhys / (1024**3)
        except Exception:
            pass
    return -1.0


def check_free_ram(min_free_gb: float) -> float:
    free = free_ram_gb()
    print(f"[export] free RAM: {free:.2f} GiB (need > {min_free_gb:.1f})", flush=True)
    if free < 0:
        raise SystemExit("cannot measure free RAM on this machine; refusing export")
    if free <= min_free_gb:
        raise SystemExit(
            f"not enough free RAM ({free:.2f} GiB <= {min_free_gb:.1f} GiB); "
            "close heavy apps and retry"
        )
    return free


def _copy_tokenizer(source: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name in _TOKENIZER_FILES:
        source_path = source / name
        if source_path.is_file():
            shutil.copy2(source_path, output / name)
    if not (output / "tokenizer.json").is_file():
        raise SystemExit("source tree has no tokenizer.json")


def _write_sparse_head(source: Path, output: Path) -> None:
    weight_path = source / "sparse_linear.pt"
    if not weight_path.is_file():
        raise SystemExit(
            "source tree has no sparse_linear.pt; hybrid retrieval would lose its sparse channel"
        )
    import numpy as np
    import torch

    payload = torch.load(weight_path, map_location="cpu", weights_only=True)
    if isinstance(payload, dict):
        weight = payload.get("weight")
        bias = payload.get("bias")
    else:
        weight = getattr(payload, "weight", None)
        bias = getattr(payload, "bias", None)
    if weight is None:
        raise SystemExit("sparse_linear.pt has no weight tensor")
    np.save(output / "sparse_linear.npy", weight.detach().cpu().numpy().astype("float32"))
    if bias is not None:
        np.save(output / "sparse_linear_bias.npy", bias.detach().cpu().numpy().astype("float32"))


def _export_onnx_fp32_torch(source: Path, work_model: Path) -> None:
    """Export via torch.onnx.dynamo_export, bypassing optimum's task map.

    optimum 1.24 resolves ``feature-extraction`` through sentence-transformers
    (``get_model_class_for_task`` imports it), which segfaults in this venv
    (pyarrow C-extension access violation via pandas->sklearn chain).
    BGE-M3 is a plain XLM-Roberta encoder, so export the core transformer
    directly and keep the pooling (CLS) in the runtime backend, which already
    reads ``hidden[:, 0]``. Needs ``onnxscript`` (torch dynamo exporter).
    """
    started = time.perf_counter()
    import torch
    from transformers import AutoModel, AutoTokenizer

    model = AutoModel.from_pretrained(
        str(source), trust_remote_code=False, local_files_only=True
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(
        str(source), trust_remote_code=False, local_files_only=True
    )
    batch = tokenizer(
        ["kiểm tra xuất mô hình BGE-M3 sang ONNX", "second probe sentence"],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    with torch.no_grad():
        exported = torch.onnx.dynamo_export(
            model,
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
        )
    exported.save(str(work_model))
    _stage("torch_dynamo_export_fp32", started)


def _export_onnx_fp32_torchscript(source: Path, work_model: Path) -> None:
    """Export via torch.onnx.export (torchscript tracer), opset 17.

    dynamo_export (torch 2.5.1, opset 18 only) refuses to trace the HF
    XLMRoberta forward (``skip function XLMRobertaModel.forward``). The
    legacy tracer handles this encoder; dynamic axes keep variable length.
    BGE-M3 pooling stays in the runtime backend (CLS ``hidden[:, 0]``).
    """
    started = time.perf_counter()
    import torch
    from transformers import AutoModel, AutoTokenizer

    model = AutoModel.from_pretrained(
        str(source), trust_remote_code=False, local_files_only=True
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(
        str(source), trust_remote_code=False, local_files_only=True
    )
    batch = tokenizer(
        ["kiểm tra xuất mô hình BGE-M3 sang ONNX", "second probe sentence"],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    input_ids = batch["input_ids"]
    attention_mask = batch["attention_mask"]
    with torch.no_grad():
        torch.onnx.export(
            model,
            (input_ids, attention_mask),
            str(work_model),
            input_names=["input_ids", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "seq"},
                "attention_mask": {0: "batch", 1: "seq"},
                "last_hidden_state": {0: "batch", 1: "seq"},
            },
            opset_version=17,
            do_constant_folding=True,
        )
    _stage("torchscript_export_fp32", started)


def _export_onnx_fp32_optimum(source: Path, work_model: Path) -> None:
    started = time.perf_counter()
    try:
        from optimum.exporters.onnx import main_export
    except ImportError as exc:
        raise SystemExit(
            "optimum export needs the optimum package: see FIX2 report step 1"
        ) from exc
    main_export(
        str(source),
        output=str(work_model),
        task="feature-extraction",
        device="cpu",
        framework="pt",
        local_files_only=True,
        trust_remote_code=False,
        for_ort=True,
        do_validation=False,
    )
    _stage("optimum_export_fp32", started)


def _quantize(source_model: Path, output_model: Path) -> None:
    started = time.perf_counter()
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as exc:
        raise SystemExit(
            "dynamic quantization needs the onnx package as well as onnxruntime"
        ) from exc
    quantize_dynamic(
        model_input=str(source_model),
        model_output=str(output_model),
        weight_type=QuantType.QInt8,
        use_external_data_format=True,
        extra_options={"MatMulConstBOnly": True},
    )
    _stage("quantize_dynamic_int8", started)


def _write_checksum(output: Path) -> str:
    started = time.perf_counter()
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from aios_habit.rag_v2.retrieval_backends import sha256_model_tree

    digest = sha256_model_tree(output)
    sidecar = output.parent / f"{output.name}.sha256"
    sidecar.write_text(digest + "\n", encoding="utf-8")
    _stage("checksum", started)
    return digest


def export_tree(source: Path, output: Path, work_dir: Path, exporter: str = "torchscript") -> str:
    if not (source / "pytorch_model.bin").is_file():
        raise SystemExit(f"source tree has no pytorch_model.bin: {source}")
    work_model = work_dir / "model_fp32.onnx"
    quantized = output / "model_quantized.onnx"
    if output.exists():
        shutil.rmtree(output)
    work_dir.mkdir(parents=True, exist_ok=True)
    if exporter == "optimum":
        _export_onnx_fp32_optimum(source, work_model)
    elif exporter == "torch":
        _export_onnx_fp32_torch(source, work_model)
    else:
        _export_onnx_fp32_torchscript(source, work_model)
    _copy_tokenizer(source, output)
    _write_sparse_head(source, output)
    _quantize(work_model, quantized)
    manifest = {
        "source": str(source.resolve()),
        "export": ({"torch": "torch-dynamo-pt-cpu", "torchscript": "torch-tracer-pt-cpu"}.get(exporter, "optimum-feature-extraction-pt-cpu")),
        "quantization": "dynamic-int8",
        "max_length": 512,
        "providers": ["CPUExecutionProvider"],
        "stages_s": {k: round(v, 3) for k, v in _TIMINGS.items()},
    }
    (output / "export_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return _write_checksum(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_OUTPUT.parent / ".bge-m3-onnx-work")
    parser.add_argument("--min-free-gb", type=float, default=6.0)
    parser.add_argument("--exporter", choices=["torch", "torchscript", "optimum"], default="torchscript")
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()
    check_free_ram(args.min_free_gb)
    total = time.perf_counter()
    digest = export_tree(args.source, args.output, args.work_dir, args.exporter)
    _stage("total", total)
    if not args.keep_work:
        shutil.rmtree(args.work_dir, ignore_errors=True)
    print(f"exported {args.output}")
    print(digest)
    print(json.dumps({k: round(v, 3) for k, v in _TIMINGS.items()}, indent=2))


if __name__ == "__main__":
    main()
