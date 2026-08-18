# Quickstart: Implement and verify adaptive reranking

## 1. Establish the current state

```powershell
git branch --show-current
git status --short
graphify query "Where does Workspace Chat choose and execute RAG retrieval and report fallback?" --budget 3000 --graph graphify-out/graph.json
```

Do not clean, reset, stage or commit unrelated existing changes. Record the initial dirty paths in the implementation report.

## 2. Read the feature package

```powershell
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/spec.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/plan.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/data-model.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/contracts/adaptive-retrieval-routing.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/tasks.md
```

Implement tasks in order and check a task only after its stated tests/evidence pass.

## 3. Focused verification

```powershell
py -3 -m pytest -q tests/test_adaptive_retrieval.py tests/test_rag_v2_pipeline.py tests/test_workspace_chat_rag_v2_adapter.py tests/test_workspace_chat_rag_v2_deployment.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_ui_copy.py
py -3 -m compileall src tests
git diff --check
```

## 4. Frozen adaptive benchmark

The future implementation script must support an inspectable command equivalent to:

```powershell
py -3 scripts/benchmark_adaptive_reranking.py --cases tests/fixtures/adaptive_routing_cases.json --windows 10,20,30 --output local_runs/adaptive_reranking/report.json
```

The report must include:

- dataset checksum and policy version;
- route confusion matrix and distribution;
- explicit Deep and uncertain escalation rates;
- Hybrid vs rerank Recall@10/MRR@10;
- fast/deep p50/p95;
- peak process RSS, available RAM and runtime init count;
- requested/effective paths and degradation counts;
- a privacy scan result;
- one final `PASS`, `PARTIAL` or `FAIL` with per-gate reasons.

The report must not contain query text, source snippets, titles, paths or secrets.

## 5. Full project gates

```powershell
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
```

Record each command separately. A focused pass is not a full-suite pass. CLI audit must explicitly report `"status": "PASS"`.

## 6. Documentation and graph

```powershell
graphify update . --no-cluster
git diff --check
git status --short
```

Update architecture, roadmap, operator runbook, performance baseline, troubleshooting, quality strategy and `PROJECT_HANDOVER.md`. Do not mark feature complete if any gate is pending.

## 7. Rollback rehearsal

1. Disable adaptive reranking in the local manifest/flag.
2. Restart Workspace Chat.
3. Ask one Auto and one Deep-marked test question.
4. Verify both execute the approved Hybrid base or return an explicit Deep-unavailable status.
5. Verify no index rebuild and no conversation/source loss.

## 8. Handoff

Use [GEMINI_IMPLEMENTATION_PROMPT.md](GEMINI_IMPLEMENTATION_PROMPT.md) for implementation and [TERRA_AUDIT_PROMPT.md](TERRA_AUDIT_PROMPT.md) for the independent read-only audit.
