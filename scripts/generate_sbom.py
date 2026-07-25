#!/usr/bin/env python3
"""Generate a local CycloneDX-style SBOM without paths, credentials or environment values."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Iterable


def component_from_distribution(distribution: Distribution) -> dict[str, str]:
    name = distribution.metadata.get("Name") or distribution.name
    version = distribution.version
    normalized = name.lower().replace("_", "-")
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{normalized}@{version}",
    }


def build_sbom(items: Iterable[Distribution] | None = None) -> dict:
    resolved = items if items is not None else distributions()
    components = sorted(
        (component_from_distribution(item) for item in resolved),
        key=lambda component: (component["name"].lower(), component["version"]),
    )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:owner-generated-local-sbom",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "component": {
                "type": "application",
                "name": "aios-habit",
            },
            "tools": [{"vendor": "AIOS WorkLens", "name": "scripts/generate_sbom.py"}],
        },
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("local_runs/sbom/aios-habit-sbom.json"),
        help="Ignored local output path; inspect before sharing.",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build_sbom(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SBOM_WRITTEN={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
