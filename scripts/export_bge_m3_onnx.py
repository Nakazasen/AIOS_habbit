"""Export a local BGE-M3 tree to an int8 ONNX directory.

The pinned retrieval tree already contains ``onnx/model.onnx``. Re-exporting the
2.3GB PyTorch weights through optimum would load a second full copy and is the
path that exceeds a 16GB laptop. This script therefore quantizes that existing
ONNX graph, copies the tokenizer, and converts ``sparse_linear.pt`` to a numpy
head so hybrid retrieval does not need torch at query time.

Output defaults to ``models/bge-m3-onnx-int8/`` plus a sibling checksum file.
The directory is gitignored. Runtime stays on PyTorch until ``BGE_BACKEND=onnx_int8``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
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


def _quantized_path(output: Path) -> Path:
    return output / "model_quantized.onnx"


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
        raise SystemExit("source tree has no sparse_linear.pt; hybrid retrieval would lose its sparse channel")
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


def _quantize(source_model: Path, output_model: Path) -> None:
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as exc:
        raise SystemExit(
            "dynamic quantization needs the onnx package as well as onnxruntime: "
            "uv pip install onnx"
        ) from exc
    quantize_dynamic(
        model_input=str(source_model),
        model_output=str(output_model),
        weight_type=QuantType.QInt8,
        use_external_data_format=True,
        extra_options={"MatMulConstBOnly": True},
    )


def _write_checksum(output: Path) -> str:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from aios_habit.rag_v2.retrieval_backends import sha256_model_tree

    digest = sha256_model_tree(output)
    sidecar = output.parent / f"{output.name}.sha256"
    sidecar.write_text(digest + "\n", encoding="utf-8")
    return digest


def export_tree(source: Path, output: Path) -> str:
    source_model = source / "onnx" / "model.onnx"
    if not source_model.is_file():
        raise SystemExit(f"missing existing ONNX export: {source_model}")
    if output.exists():
        shutil.rmtree(output)
    _copy_tokenizer(source, output)
    _write_sparse_head(source, output)
    _quantize(source_model, _quantized_path(output))
    manifest = {
        "source": str(source.resolve()),
        "quantization": "dynamic-int8",
        "max_length": 512,
        "providers": ["CPUExecutionProvider"],
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
    args = parser.parse_args()
    digest = export_tree(args.source, args.output)
    print(f"exported {args.output}")
    print(digest)


if __name__ == "__main__":
    main()
