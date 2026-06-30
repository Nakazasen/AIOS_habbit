# NotebookLM Manual Collection Runbook

Use this when `nlm` cannot safely automate import/query/output collection.

1. Create or choose a NotebookLM notebook for the MOM/WMS comparison.
2. Import the approved local documents from `[LOCAL_SOURCE_ROOT]` using NotebookLM UI or supported `nlm` commands.
3. Open `local_runs/notebooklm_compare/questions.jsonl` locally.
4. Ask each question in the same order.
5. Save answers and citations to `local_runs/notebooklm_compare/notebooklm_answers.jsonl`.
6. Do not commit the answer file.
7. Run `aios-habit notebooklm-compare evaluate` after both AIOS and NotebookLM answer files exist.

Do not paste API keys, `.env`, or unrelated company material. Do not claim parity from this run alone.
