import sqlite3
import json
from pathlib import Path

stage_manifest_path = Path("local_runs/battle_workspace_stage_cache/00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074/workspace_stage_manifest.json")
with open(stage_manifest_path, "r", encoding="utf-8") as f:
    stage_data = json.load(f)

db_path = Path(stage_data["index_path"])
conn = sqlite3.connect(db_path)
cols = [r[1] for r in conn.execute("PRAGMA table_info(chunks)").fetchall()]
print("Columns in chunks:", cols)
sample = conn.execute("SELECT chunk_id, document_id, source_name, source_path, text FROM chunks LIMIT 3").fetchall()
for s in sample:
    print("Sample:", s[0], "|", s[1], "|", s[2], "|", s[3], "| len text:", len(s[4]))
