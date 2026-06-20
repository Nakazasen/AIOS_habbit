from pathlib import Path

from .models import ProjectCard, nid

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "inbox_local_only",
    "raw",
    "cache",
    "private",
    "secrets",
}

MARKERS = [
    ".git",
    "README.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "ARCHITECTURE.md",
    "AGENT_RULES.md",
    "pyproject.toml",
    "package.json",
    "docs",
    "prompts",
    "specs",
]


def discover_projects(root: Path, max_depth: int = 2) -> list[ProjectCard]:
    root = root.resolve()
    cards: list[ProjectCard] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth or directory.name in IGNORE_DIRS:
            return
        try:
            children = list(directory.iterdir())
        except OSError:
            return

        names = {child.name for child in children}
        signals = [marker for marker in MARKERS if marker in names]
        if signals:
            cards.append(
                ProjectCard(
                    project_id=nid("PRJ"),
                    name=directory.name,
                    path=str(directory),
                    detected_signals=signals,
                    risks=["metadata_only_inventory_no_raw_ingest"],
                )
            )

        for child in children:
            if child.is_dir() and child.name not in IGNORE_DIRS:
                walk(child, depth + 1)

    walk(root, 0)
    return cards
