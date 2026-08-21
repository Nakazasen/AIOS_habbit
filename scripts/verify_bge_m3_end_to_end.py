import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 1. Verify ML imports
print("=== 1. Verifying ML Dependencies ===")
import torch
import FlagEmbedding
import transformers
import sentence_transformers

print(f"  torch: {torch.__version__} (device: {'cuda' if torch.cuda.is_available() else 'cpu'})")
print(f"  FlagEmbedding: {FlagEmbedding.__version__ if hasattr(FlagEmbedding, '__version__') else 'installed'}")
print(f"  transformers: {transformers.__version__}")
print(f"  sentence_transformers: {sentence_transformers.__version__}")

# 2. Verify Canary Config from .env
print("\n=== 2. Verifying Canary Config from .env ===")
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    WorkspaceAIContextSource,
    retrieve_workspace_chat_evidence,
    schedule_workspace_chat_source_preparation,
    get_workspace_chat_source_preparation_status,
    close_workspace_chat_rag_v2_runtimes,
)

# Load env variables manually from .env if needed
with open(PROJECT_ROOT / ".env", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

canary_cfg = WorkspaceChatRagV2CanaryConfig.from_env()
print(f"  Canary enabled: {canary_cfg.enabled}")
print(f"  Requested profile: {canary_cfg.requested_profile}")
print(f"  Model path: {canary_cfg.bge_m3_model_path}")
print(f"  Model revision: {canary_cfg.bge_m3_model_revision}")
print(f"  Model checksum: {canary_cfg.bge_m3_model_checksum}")
print(f"  Device: {canary_cfg.retrieval_device}")
assert canary_cfg.enabled is True, "Canary config should be enabled"
assert canary_cfg.bge_m3_model_path.is_dir(), "BGE-M3 model directory must exist"

# 3. Test BGE Subprocess Worker & Client directly with BGE-M3
print("\n=== 3. Testing BGE Subprocess Worker & Client with BGE-M3 ===")
from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.pipeline import RagV2DevConfig, SourceSpec

worker_config = RagV2DevConfig(
    runtime_root=PROJECT_ROOT / "local_runs" / "test_verify_runtime",
    retrieval_profile="bge_m3_hybrid",
    bge_m3_model_path=canary_cfg.bge_m3_model_path,
    bge_m3_model_revision=canary_cfg.bge_m3_model_revision,
    bge_m3_model_checksum=canary_cfg.bge_m3_model_checksum,
    retrieval_device="cpu",
)

doc_path = PROJECT_ROOT / "local_runs" / "test_verify_runtime" / "doc.txt"
doc_path.parent.mkdir(parents=True, exist_ok=True)
doc_path.write_text(
    "Nhiem vu RAG v2: Minh phu trach ho so ORCHID-731 can hoan thanh kiem tra CPU BGE-M3.",
    encoding="utf-8",
)
spec = SourceSpec(path=doc_path, source_id="s1", document_id="d1")

client = BgeSubprocessWorkerClient()
try:
    print("  Spawning and initializing BGE subprocess worker...")
    t0 = time.perf_counter()
    init_res = client.initialize_worker(worker_config)
    t1 = time.perf_counter()
    print(f"  Worker initialized in {t1 - t0:.2f}s (PID: {init_res['readiness']['pid']})")

    print("  Preparing source document...")
    prep_res = client.prepare_sources([spec], worker_config)
    print(f"  Ingest report: {prep_res}")

    print("  Executing semantic query...")
    query_res = client.query(
        question="Ai phu trach ho so ORCHID-731?",
        specs=[spec],
        config=worker_config,
    )
    print(f"  Query returned {len(query_res['items'])} items")
    print(f"  Candidate backend: {query_res['summary']['candidate_backend']}")
    print(f"  Top snippet: {query_res['items'][0]['text']}")
    assert len(query_res["items"]) >= 1, "Expected at least 1 retrieved item"
    assert "ORCHID-731" in query_res["items"][0]["text"]
finally:
    client.close()
    print("  Worker closed cleanly.")

# 4. Test Workspace Chat Adapter End-to-End
print("\n=== 4. Testing Workspace Chat Adapter End-to-End ===")
source = WorkspaceAIContextSource(
    source_id="test_src_1",
    source_scope="temporary",
    source_type="pasted_text",
    title="test_doc.txt",
    privacy_label="local_only",
    text="He thong AIOS Habit da kich hoat mo hinh BGE-M3 tren CPU thanh cong.",
    included_chars=69,
    truncated=False,
)

print("  Scheduling background source preparation...")
schedule_workspace_chat_source_preparation([source], config=canary_cfg)
print("  Waiting for background source preparation to complete...")
for _ in range(60):
    status = get_workspace_chat_source_preparation_status([source], config=canary_cfg)
    if status.get("temporary:test_src_1") == "ready":
        print(f"  Source preparation complete: {status}")
        break
    time.sleep(2)
else:
    raise TimeoutError("Background source preparation timed out")

print("  Testing retrieve_workspace_chat_evidence...")
evidence = retrieve_workspace_chat_evidence(
    question="Trang thai kich hoat mo hinh BGE-M3?",
    context_sources=[source],
    config=canary_cfg,
)
print(f"  Retrieval applied: {evidence.get('retrieval_applied')}")
print(f"  Owner message: {evidence.get('safe_owner_message')}")
print(f"  Telemetry: {evidence.get('rag_v2_canary')}")
print(f"  Evidence items returned: {len(evidence.get('evidence_items', []))}")
assert evidence.get("retrieval_applied") is True, f"Expected retrieval_applied=True, got {evidence}"
assert evidence.get("rag_v2_canary", {}).get("backend") == "rag_v2_subprocess"
assert evidence.get("rag_v2_canary", {}).get("effective_profile") == "bge_m3_hybrid"
assert evidence.get("summary_count", 0) >= 1

close_workspace_chat_rag_v2_runtimes()

print("\n>>> ALL VERIFICATION STEPS PASSED SUCCESSFULLY! <<<")
