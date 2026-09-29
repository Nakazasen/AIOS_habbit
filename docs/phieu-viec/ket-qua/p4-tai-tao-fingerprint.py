#!/usr/bin/env python3
"""P4 — Tai tao fingerprint 016c5255… bang SemanticModelDescriptor.fingerprint.

Vé: docs/phieu-viec/mailbox-pc0575/prompt.md (p4-deploy-constants).
CHI DOC + TINH TOAN: script khong doi env, khong ghi index, khong embed,
khong ghi byte nao len he thong file (ngoai stdout/file output do nguoi goi chon).

Quet to hop 9 truong cua SemanticModelDescriptor tren tap ung vien:
- artifact_checksum: cac checksum da gap trong repo/bao cao/may nay + rong
- device, runtime, runtime_version, model_id, revision: cac bien the trong code/bao cao
- dimension=1024, distance="cosine", normalized ∈ {True, False} (mac dinh + doi chieu)

Chay (tu repo root):
    uv run --no-sync --group dev python docs/phieu-viec/ket-qua/p4-tai-tao-fingerprint.py
Hoac:
    .venv/Scripts/python.exe -B docs/phieu-viec/ket-qua/p4-tai-tao-fingerprint.py

Exit 0 = tai tao duoc dung chuoi 64 hex (in JSON to hop thang).
Exit 1 = khong tai tao duoc (in JSON da thu gi, dung doan bua).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sqlite3
import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from aios_habit.rag_v2.semantic import SemanticModelDescriptor

TARGET = "016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb"
INDEX = REPO / "local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite"

# --- Tap ung vien (nguon tung gia tri ghi trong ngoac) -------------------------
CHECKSUMS = {
    "sha256:9f81075f…b11093 (sidecar FIX2 may nha: models/bge-m3-onnx-fp32.sha256)":
        "sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093",
    "sha256:b1d887e0…320b61 (manifest pin: src/aios_habit/bge_m3_manifest.json)":
        "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
    "sha256:697a97c3…d40fda (manifest approved #2 / FIX2 bao cao)":
        "sha256:697a97c33326734d8152b6f026297cd1421587039c301f52c39c34896bd40fda",
    "sha256:dad14a24…4bd4 (cay onnx PC0575, 8 file truoc sparse head)":
        "sha256:dad14a2492262ad3259a0be58b6b8c517897d71141685b97c2af924c520e4bd4",
    "sha256:728c9eb7…76baa (cay onnx PC0575, 10 file sau sparse head)":
        "sha256:728c9eb7ee48a66ac4b6d567e3408433398911a6abcce9685d8a048eb8766baa",
    "rong": "",
}
DEVICES = ["cpu", "cuda", ""]
MODEL_IDS = ["BAAI/bge-m3"]
RUNTIMES = ["onnxruntime-int8", "onnxruntime", ""]
REVISIONS = ["5617a9f61b028005a4858fdac845db406aefb181", ""]
DIMENSIONS = [1024]
DISTANCES = ["cosine"]
NORMALIZED = [True, False]


def _installed_onnxruntime() -> str:
    try:
        return _pkg_version("onnxruntime")
    except Exception:  # noqa: BLE001 - best-effort metadata lookup only
        return ""


def _sealed_fingerprint() -> dict[str, object]:
    """Read-only: dominant fingerprint(s) sealed in the production index."""
    try:
        con = sqlite3.connect(f"file:{INDEX.as_posix()}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT model_fingerprint, COUNT(*) FROM chunk_embeddings "
                "GROUP BY 1 ORDER BY 2 DESC"
            ).fetchall()
        finally:
            con.close()
        return {"ok": True, "rows": [{"fingerprint": r[0], "n": r[1]} for r in rows]}
    except Exception as exc:  # noqa: BLE001 - diagnostic only
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    runtime_versions = ["1.28.0", "1.29.0", ""]
    installed = _installed_onnxruntime()
    if installed and installed not in runtime_versions:
        runtime_versions.append(installed)

    sealed = _sealed_fingerprint()
    target = TARGET
    if sealed.get("ok") and sealed["rows"]:
        top = max(sealed["rows"], key=lambda r: r["n"])  # type: ignore[index]
        if isinstance(top.get("fingerprint"), str) and top["fingerprint"]:
            target = top["fingerprint"]

    combos = itertools.product(
        CHECKSUMS.items(), DEVICES, MODEL_IDS, RUNTIMES, runtime_versions,
        REVISIONS, DIMENSIONS, DISTANCES, NORMALIZED,
    )
    checked = 0
    winners: list[dict[str, object]] = []
    for (checksum_label, checksum), device, model_id, runtime, runtime_version, revision, dim, dist, norm in combos:
        descriptor = SemanticModelDescriptor(
            model_id=model_id,
            revision=revision,
            runtime=runtime,
            runtime_version=runtime_version,
            dimension=dim,
            distance=dist,
            normalized=norm,
            artifact_checksum=checksum,
            device=device,
        )
        checked += 1
        if descriptor.fingerprint == target:
            winners.append({
                "artifact_checksum": checksum,
                "artifact_checksum_source": checksum_label,
                "device": device,
                "dimension": dim,
                "distance": dist,
                "model_id": model_id,
                "normalized": norm,
                "revision": revision,
                "runtime": runtime,
                "runtime_version": runtime_version,
            })

    counterfactuals = []
    for label, checksum in [
        ("cay onnx PC0575 8 file truoc sparse head (dad14a24)",
         "sha256:dad14a2492262ad3259a0be58b6b8c517897d71141685b97c2af924c520e4bd4"),
        ("cay onnx PC0575 10 file sau sparse head (728c9eb7)",
         "sha256:728c9eb7ee48a66ac4b6d567e3408433398911a6abcce9685d8a048eb8766baa"),
        ("khong checksum (rong)",
         ""),
        ("manifest pack PyTorch pin (b1d887e0)",
         "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61"),
    ]:
        probe = SemanticModelDescriptor(
            model_id="BAAI/bge-m3",
            revision="5617a9f61b028005a4858fdac845db406aefb181",
            runtime="onnxruntime-int8",
            runtime_version="1.28.0",
            dimension=1024,
            normalized=True,
            artifact_checksum=checksum,
            device="cpu",
        )
        counterfactuals.append({
            "label": label,
            "artifact_checksum": checksum,
            "fingerprint": probe.fingerprint,
            "matches_target": probe.fingerprint == target,
        })

    result = {
        "status": "REPRODUCED" if winners else "NOT_REPRODUCED",
        "target": target,
        "sealed_from_index": sealed,
        "installed_onnxruntime": installed,
        "checked_combos": checked,
        "winners_count": len(winners),
        "winners": winners,
        "counterfactuals": counterfactuals,
        "candidates": {
            "artifact_checksum": list(CHECKSUMS),
            "device": DEVICES,
            "model_id": MODEL_IDS,
            "runtime": RUNTIMES,
            "runtime_version": runtime_versions,
            "revision": REVISIONS,
            "dimension": DIMENSIONS,
            "distance": DISTANCES,
            "normalized": NORMALIZED,
        },
        "winner": winners[0] if winners else None,
        "payload_preimage": None,
    }
    if winners:
        payload = {
            "artifact_checksum": winners[0]["artifact_checksum"],
            "device": winners[0]["device"],
            "dimension": winners[0]["dimension"],
            "distance": winners[0]["distance"],
            "model_id": winners[0]["model_id"],
            "normalized": winners[0]["normalized"],
            "revision": winners[0]["revision"],
            "runtime": winners[0]["runtime"],
            "runtime_version": winners[0]["runtime_version"],
        }
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        result["payload_preimage"] = encoded
        result["sha256_of_preimage"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if winners else 1


if __name__ == "__main__":
    raise SystemExit(main())
