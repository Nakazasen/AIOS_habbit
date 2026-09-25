"""FIX 2 benchmark: ONNX int8 vs PyTorch BGE-M3 on the home machine.

Compares on the SAME texts (no DB writes, read-only index access):
  1. Embed latency per backend (cold init + warm embed, batch 1 and 8).
  2. Cosine(onnx_vec, pytorch_vec) per text -- must be ~= 1.0.
  3. max_length 512 vs 2048 cosine on the PyTorch path (ticket 5.3).
  4. Recall proxy: top-10 agreement of ONNX queries vs PyTorch queries
     against the SAME stored PyTorch corpus (battle index). The PyTorch
     top-10 is the ground truth; ONNX recall@10 = |intersection| / 10.

Usage:
  uv run --no-sync --group dev python scripts/bench_fix2_onnx.py \
      --corpus local_runs/battle_rag_v2_index_cache/<hash>/rag_v2_dev.sqlite \
      --n-corpus 1000 --n-query 20 --out local_runs/fix2_bench_home.json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

MODEL_PATH = Path(
    os.environ.get(
        "AIOS_BGE_M3_MODEL_PATH",
        "local_runs/retrieval_models/bge-m3-5617a9f",
    )
)
REVISION = os.environ.get(
    "AIOS_BGE_M3_MODEL_REVISION", "5617a9f61b028005a4858fdac845db406aefb181"
)
CHECKSUM = os.environ.get(
    "AIOS_BGE_M3_MODEL_CHECKSUM",
    "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
)


def _unpack_vector(blob: bytes, dim: int = 1024):
    import struct

    n = len(blob) // 4
    vals = struct.unpack(f"<{n}f", blob[: n * 4])
    if len(vals) == dim + 1:
        vals = vals[1:]
    return vals[:dim]
def load_corpus(db_path: Path, n_corpus: int, n_query: int):
    import numpy as np

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT chunk_id, vector_blob FROM chunk_embeddings LIMIT ?",
            (n_corpus + n_query,),
        ).fetchall()
    finally:
        con.close()
    if len(rows) < n_corpus + n_query:
        raise SystemExit(f"only {len(rows)} embeddings in {db_path}")
    corpus_ids = [r[0] for r in rows[:n_corpus]]
    corpus = np.array(
        [_unpack_vector(r[1]) for r in rows[:n_corpus]], dtype=np.float32
    )
    norms = np.linalg.norm(corpus, axis=1, keepdims=True)
    corpus = corpus / np.maximum(norms, 1e-12)
    query_ids = [r[0] for r in rows[n_corpus : n_corpus + n_query]]
    return corpus_ids, corpus, query_ids


def load_texts(db_path: Path, query_ids: list[str]) -> list[str]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        texts = []
        for qid in query_ids:
            row = con.execute(
                "SELECT text FROM chunks WHERE chunk_id = ?", (qid,)
            ).fetchone()
            texts.append(row[0] if row and row[0] else "")
    finally:
        con.close()
    if any(not t for t in texts):
        missing = sum(1 for t in texts if not t)
        raise SystemExit(f"{missing}/{len(texts)} query chunks have no text")
    return texts


def cosine(a, b) -> float:
    import numpy as np

    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(va @ vb / max(denom, 1e-12))


def top10(query_vec, corpus) -> list[int]:
    import numpy as np

    q = np.asarray(query_vec, dtype=np.float32)
    q = q / max(float(np.linalg.norm(q)), 1e-12)
    scores = corpus @ q
    k = min(10, len(scores))
    idx = np.argpartition(-scores, k - 1)[:k]
    return sorted(idx.tolist(), key=lambda i: -scores[i])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--n-corpus", type=int, default=1000)
    ap.add_argument("--n-query", type=int, default=20)
    ap.add_argument("--out", type=Path, default=Path("local_runs/fix2_bench_home.json"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    corpus_ids, corpus, query_ids = load_corpus(args.corpus, args.n_corpus, args.n_query)
    texts = load_texts(args.corpus, query_ids)
    print(f"[bench] corpus={len(corpus_ids)} queries={len(texts)} load={time.perf_counter()-t0:.1f}s", flush=True)

    from aios_habit.rag_v2.retrieval_backends import BgeM3Backend

    t0 = time.perf_counter()
    pytorch = BgeM3Backend(
        MODEL_PATH, revision=REVISION, artifact_checksum=CHECKSUM,
        batch_size=8, max_length=2048,
    )
    pytorch_init_s = time.perf_counter() - t0
    print(f"[bench] pytorch init {pytorch_init_s:.1f}s", flush=True)

    t0 = time.perf_counter()
    pt_vecs = pytorch.embed_documents(texts)
    pytorch_embed_s = time.perf_counter() - t0

    # Ticket 5.3: 512 vs 2048 on the same PyTorch model.
    pytorch._max_length = 512
    pt_vecs_512 = pytorch.embed_documents(texts[:1])
    cos_512_2048 = cosine(pt_vecs_512[0], pt_vecs[0])
    print(f"[bench] pytorch 512-vs-2048 cosine={cos_512_2048:.6f}", flush=True)

    from aios_habit.rag_v2.bge_onnx_backend import (
        OnnxInt8BgeM3Backend,
        resolve_onnx_checksum,
        resolve_onnx_model_path,
    )

    onnx_path = resolve_onnx_model_path()
    onnx_checksum = resolve_onnx_checksum(onnx_path)
    t0 = time.perf_counter()
    onnx_be = OnnxInt8BgeM3Backend(
        model_path=onnx_path, revision=REVISION,
        artifact_checksum=onnx_checksum, batch_size=8,
    )
    onnx_init_s = time.perf_counter() - t0
    print(f"[bench] onnx init {onnx_init_s:.1f}s", flush=True)

    t0 = time.perf_counter()
    onnx_vecs = onnx_be.embed_documents(texts)
    onnx_embed_s = time.perf_counter() - t0

    cosines = [cosine(o, p) for o, p in zip(onnx_vecs, pt_vecs)]
    import statistics

    agreements = []
    for o, p in zip(onnx_vecs, pt_vecs):
        top_o = top10(o, corpus)
        top_p = top10(p, corpus)
        agreements.append(len(set(top_o) & set(top_p)) / 10.0)

    result = {
        "model_path": str(MODEL_PATH),
        "onnx_path": str(onnx_path),
        "corpus_db": str(args.corpus),
        "n_corpus": len(corpus_ids),
        "n_query": len(texts),
        "pytorch_init_s": round(pytorch_init_s, 3),
        "onnx_init_s": round(onnx_init_s, 3),
        "pytorch_embed_s": round(pytorch_embed_s, 3),
        "onnx_embed_s": round(onnx_embed_s, 3),
        "embed_speedup": round(pytorch_embed_s / max(onnx_embed_s, 1e-9), 3),
        "pytorch_per_doc_ms": round(pytorch_embed_s / len(texts) * 1000, 2),
        "onnx_per_doc_ms": round(onnx_embed_s / len(texts) * 1000, 2),
        "cosine_512_vs_2048_pytorch": round(cos_512_2048, 6),
        "cosine_onnx_vs_pytorch_mean": round(statistics.mean(cosines), 6),
        "cosine_onnx_vs_pytorch_min": round(min(cosines), 6),
        "recall_proxy_mean": round(statistics.mean(agreements), 4),
        "recall_proxy_min": round(min(agreements), 4),
        "recall_proxy_delta": round(1.0 - statistics.mean(agreements), 4),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
