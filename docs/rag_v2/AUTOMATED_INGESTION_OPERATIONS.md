# Automated RAG v2 Ingestion Operations

## User experience

Users add documents or select a synchronized folder. Ingestion runs in the background and the currently active index remains available for questions. The new index is activated only after identity, checksum, SQLite integrity, and deployment checks pass.

| Internal state | User-facing text |
| --- | --- |
| `QUEUED`, `EXTRACTING` | Đang chuẩn bị |
| `EMBEDDING`, `VERIFYING`, `DEPLOYING` | Đang xử lý |
| `WAITING_FOR_CAPACITY` | Đang chờ GPU |
| `READY` | Sẵn sàng |
| `FAILED` | Có file cần xem lại |

## Reliability contract

- Duplicate submissions return the same logical job.
- Workers use leases; an expired lease can be reclaimed after a crash.
- Checkpoints are immutable and hash-verified before resume.
- Network or GPU-capacity failures do not affect the active index.
- `local_only` data cannot be routed to a remote worker.
- Upload and bundle download resume from acknowledged byte offsets.
- Bundles must pass identity, SHA-256, and SQLite integrity checks.
- Deployment uses atomic `candidate`, `active`, and `previous` pointers.

## Worker selection

Priority is local CUDA, managed CUDA, eligible remote worker, then throttled local CPU. CUDA policy uses FP16 and a VRAM-sized batch. An out-of-memory error halves the batch until one item; after that the scheduler selects another worker or waits for capacity.

Free Colab or Kaggle sessions are opportunistic workers only, not the control plane, because sessions and quotas can disappear without notice.

## Security and privacy

- Keep service tokens in the operating-system secret store and expose them through a token callback.
- Never log tokens, API keys, source contents, or raw exception details.
- Cloud workers accept only `cloud_safe` and `public` jobs.
- Apply source and artifact retention after verified delivery.

## Recovery drills

1. Kill a worker after a checkpoint; its replacement resumes without changing committed checkpoints.
2. Interrupt upload and download; transfer continues at the acknowledged offset.
3. Tamper with the bundle; verification rejects it.
4. Simulate CUDA OOM; batch size decreases and fallback remains available.
5. Stop the machine during deployment; an intact active or previous bundle remains.
6. Run concurrent questions during ingestion; active retrieval remains available.

## Validation commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_rag_v2_ingestion_jobs.py tests\test_rag_v2_index_bundle.py tests\test_rag_v2_ingestion_workers.py tests\test_rag_v2_remote_ingestion_client.py tests\test_rag_v2_ingestion_service.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall src tests
.\.venv\Scripts\python.exe scripts\check_docs.py
git diff --check
```
