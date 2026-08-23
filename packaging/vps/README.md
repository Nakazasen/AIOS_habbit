# AIOS WorkLens VPS Deployment & Data Isolation Contract

## 1. Scope & Isolation Guarantees
- **Single-Tenant Isolation**: Each VPS instance operates in its own isolated container and data volume (`aios_local_data` mounted at `/app/local_cases`).
- **Local data boundary**: Evidence traces, documents, and chat sessions are stored under `/app/local_cases/workspace_chat/`. Provider or bridge traffic depends on the selected runtime configuration and must be reviewed separately for confidential data.
- **Dedicated Linux Wheelhouse (`vendor/wheels_linux/`)**: A versioned, checksum-verified Linux wheelhouse supports offline Python dependency installation. Pull Git LFS artifacts before building the image.
- **Model boundary**: The BGE-M3 model pack is a separately managed, checksum-verified artifact. The image or its mounted volume must provide it; Git LFS does not store the model.

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
