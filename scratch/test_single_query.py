import json
import time
import sqlite3
from pathlib import Path

import aios_habit.workspace_chat_rag_v2_adapter as adapter
from aios_habit.rag_v2.pipeline import RagV2DevPipeline, RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.synthesis import synthesize_evidence

stage_manifest_path = Path("local_runs/battle_workspace_stage_cache/00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074/workspace_stage_manifest.json")
deployment_manifest = Path("config/workspace_chat_rag_v2.local.json")

with open(stage_manifest_path, "r", encoding="utf-8") as f:
    stage_data = json.load(f)

db_path = Path(stage_data["index_path"])
conn = sqlite3.connect(db_path)
distinct_docs = conn.execute("SELECT DISTINCT document_id, source_path, source_name FROM chunks").fetchall()
print(f"Loaded {len(distinct_docs)} distinct docs from SQLite chunks table.")

sources = [
    SourceSpec(
        path=Path(r[1]),
        document_id=r[0],
        source_id=r[0],
        privacy_labels=("local_only", "cloud_safe", "public"),
        owner_consent=True
    )
    for r in distinct_docs
]

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

print("Initializing worker...")
adapter._SUBPROCESS_CLIENT.initialize_worker(pipe_cfg)
pipeline = RagV2DevPipeline(pipe_cfg)

t0 = time.time()
q = "What is the overall system architecture for production history registration?"
res = pipeline.query(q, sources)
pack = res.evidence_pack
t_query = time.time() - t0
print(f"Query returned in {t_query:.2f}s | {len(pack.items)} evidence items:")
for it in pack.items[:5]:
    print(f"  - {it.source_name} | {it.citation_label} | score: {it.score:.4f} | len: {len(it.text)}")

# Test synthesis
t1 = time.time()
synth = synthesize_evidence(pack)
t_synth = time.time() - t1
print(f"Local synthesis completed in {t_synth:.2f}s:")
print(f"Answer: {synth.answer}")
