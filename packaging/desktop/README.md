# AIOS WorkLens Desktop Packaging Guide

## Overview
AIOS WorkLens Desktop is packaged as a 100% offline, self-contained bundle. It includes:
- Python runtime (>=3.11, <3.12)
- Graphify in-process engine (`graphifyy==0.9.32`)
- ExcaliFlow Studio in-process visual engine (`vendor/wheels/excaliflow-0.1.1-py3-none-any.whl`)
- Nakazasen AI Router (`vendor/wheels/nakazasen_ai_router-0.8.0-py3-none-any.whl`)
- CJK multi-locale font stack (Vietnamese, Japanese, Simplified Chinese)

## Clean-Machine Offline Installation
No internet access or GitHub downloads are required during installation.

```bash
# 1. Create a clean virtualenv
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install from local wheels directory
pip install --no-index --find-links=vendor/wheels aios-habit
```

## Running Build Verification
```bash
python packaging/desktop/desktop_build.py
```
