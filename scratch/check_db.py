import sqlite3
import json
from pathlib import Path

stage_manifest_path = Path("local_runs/battle_workspace_stage_cache/00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074/workspace_stage_manifest.json")
with open(stage_manifest_path, "r", encoding="utf-8") as f:
    stage_data = json.load(f)

db_path = Path(stage_data["index_path"])
conn = sqlite3.connect(db_path)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)
for t in tables:
    count = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count} rows")
