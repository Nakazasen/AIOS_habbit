# AIOS WorkLens VPS Deployment & Data Isolation Contract

## 1. Scope & Isolation Guarantees
- **Single-Tenant Isolation**: Each VPS instance operates in its own isolated container and data volume (`aios_local_data` mounted at `/app/local_cases`).
- **Runtime Offline (Zero Cloud Egress)**: Evidence traces, documents, and chat sessions are stored purely in local files under `/app/local_cases/workspace_chat/`. No telemetry or data is synced to external servers at runtime.
- **Dedicated Linux Wheelhouse (`vendor/wheels_linux/`)**: Contains all 87 Python wheels compiled for Linux x86_64 / `manylinux` and verified with `checksums.json`, allowing 100% offline Docker container builds without Internet access.
- **Build Distinction**: Standard container build utilizes the base `python:3.11-slim` and system font packages; all runtime operations and Python packages are 100% self-contained and offline.

## 2. Deployment Instructions

```bash
# From repository root:
docker compose -f packaging/vps/docker-compose.yml up -d --build

# Verify container health
docker compose -f packaging/vps/docker-compose.yml ps
```

## 3. Security & Non-Root Execution
- Container runs under user `aios` (UID 1000).
- `no-new-privileges` flag is enforced.
- Port 8501 binds to `127.0.0.1` by default to prevent unintended exposure without a reverse proxy.
