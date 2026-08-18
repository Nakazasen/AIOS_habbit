import json
import time
import sqlite3
from pathlib import Path

import aios_habit.workspace_chat_rag_v2_adapter as adapter
from aios_habit.rag_v2.pipeline import RagV2DevPipeline, RagV2DevConfig
from aios_habit.rag_v2.query_planning import build_query_plan

stage_manifest_path = Path("local_runs/battle_workspace_stage_cache/00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074/workspace_stage_manifest.json")
deployment_manifest = Path("config/workspace_chat_rag_v2.local.json")

with open(stage_manifest_path, "r", encoding="utf-8") as f:
    stage_data = json.load(f)

db_path = Path(stage_data["index_path"])
deployment = adapter.load_workspace_chat_rag_v2_deployment(deployment_manifest, allow_unsealed_diagnostic=True)
pipe_cfg = RagV2DevConfig(
    runtime_root=db_path.parent,
    index_filename=db_path.name,
    retrieval_profile="bge_m3_hybrid",
    bge_m3_model_path=deployment.model_path,
    bge_m3_model_revision=deployment.model_revision,
    bge_m3_model_checksum=deployment.model_checksum,
    retrieval_device="cpu"
)

pipeline = RagV2DevPipeline(pipe_cfg)
q = "What is the overall system architecture for production history registration?"
plan = build_query_plan(q)

t0 = time.time()
results = pipeline._index.search_hybrid(plan, limit=9)
t_search = time.time() - t0
print(f"Index search_hybrid returned {len(results)} results in {t_search:.2f}s:")
for r in results[:5]:
    print(f"  - {r.source_name} | score: {r.score:.4f} | len: {len(r.text)}")
    print(f"    Snippet: {r.text[:120].strip()}...")
