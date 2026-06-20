import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
WORKSPACES_FILE = LOCAL_CASES_DIR / "workspaces.jsonl"
NOTEBOOKS_FILE = LOCAL_CASES_DIR / "notebooks.jsonl"

@dataclass
class Workspace:
    workspace_id: str
    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    default_privacy: str = "local_only"
    tags: List[str] = field(default_factory=list)

@dataclass
class KnowledgeNotebook:
    notebook_id: str
    workspace_id: str
    name: str
    description: str = ""
    domain_tags: List[str] = field(default_factory=list)
    privacy_level: str = "local_only"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

def init_workspace_store():
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKSPACES_FILE.exists():
        WORKSPACES_FILE.touch()
    if not NOTEBOOKS_FILE.exists():
        NOTEBOOKS_FILE.touch()
    
    # Auto-initialize default workspace if workspaces.jsonl is empty
    workspaces = load_workspaces()
    if not workspaces:
        default_ws = Workspace(
            workspace_id="default",
            name="Workspace mặc định",
            description="Không gian làm việc mặc định ban đầu"
        )
        save_workspace(default_ws)

def load_workspaces() -> List[Workspace]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKSPACES_FILE.exists():
        return []
    workspaces = []
    with open(WORKSPACES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    workspaces.append(Workspace(**data))
                except Exception:
                    pass
    return workspaces

def load_notebooks() -> List[KnowledgeNotebook]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTEBOOKS_FILE.exists():
        return []
    notebooks = []
    with open(NOTEBOOKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    notebooks.append(KnowledgeNotebook(**data))
                except Exception:
                    pass
    return notebooks

def save_workspace(ws: Workspace):
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    workspaces = load_workspaces()
    found = False
    for i, w in enumerate(workspaces):
        if w.workspace_id == ws.workspace_id:
            workspaces[i] = ws
            found = True
            break
    if not found:
        workspaces.append(ws)
    
    with open(WORKSPACES_FILE, 'w', encoding='utf-8') as f:
        for w in workspaces:
            f.write(json.dumps(asdict(w), ensure_ascii=False) + '\n')

def save_notebook(nb: KnowledgeNotebook):
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    notebooks = load_notebooks()
    found = False
    for i, n in enumerate(notebooks):
        if n.notebook_id == nb.notebook_id:
            notebooks[i] = nb
            found = True
            break
    if not found:
        notebooks.append(nb)
    
    with open(NOTEBOOKS_FILE, 'w', encoding='utf-8') as f:
        for n in notebooks:
            f.write(json.dumps(asdict(n), ensure_ascii=False) + '\n')
