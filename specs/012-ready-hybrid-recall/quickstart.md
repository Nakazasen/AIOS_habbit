# Kiểm chứng: 012-ready-hybrid-recall

```powershell
uv run --no-sync --group dev pytest tests/test_rag_v2_script_family.py tests/test_workspace_chat_rag_v2_adapter.py tests/test_rag_v2_index.py tests/test_rag_v2_query_planning.py -q
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev python -m aios_habit.cli audit
```

Kỳ vọng: test tập trung đạt. Không tuyên bố ngang NotebookLM. Không commit `local_runs/`.
