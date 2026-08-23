# AIOS WorkLens Desktop Packaging Guide

## Overview

AIOS WorkLens Desktop has an offline build path. The wheelhouse is versioned
through Git LFS, while the BGE-M3 model artifact is supplied separately and
verified before it is copied into a desktop bundle. The build includes:
- Python runtime (>=3.11, <3.12)
- Graphify in-process engine (`graphifyy==0.9.32`)
- ExcaliFlow Studio in-process visual engine (`vendor/wheels/excaliflow-0.1.1-py3-none-any.whl`)
- Nakazasen AI Router (`vendor/wheels/nakazasen_ai_router-0.8.0-py3-none-any.whl`)
- CJK multi-locale font stack (Vietnamese, Japanese, Simplified Chinese)

## Clean-Machine Offline Installation

Pull the repository's LFS artifacts once. Afterwards the installation below
uses only the local wheelhouse and does not download packages from PyPI or
GitHub.

```bash
# 1. Fetch the repository's offline wheelhouse
git lfs install
git lfs pull

# 2. Create a clean virtualenv
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install from local wheels directory
pip install --no-index --find-links=vendor/wheels aios-habit
```

## Running Build Verification
```bash
python packaging/desktop/desktop_build.py
```

The build is fail-closed: it stops if the BGE-M3 model pack is missing,
corrupted, or does not match the pinned manifest. The model is not fetched by
this command and is not stored in Git LFS.
