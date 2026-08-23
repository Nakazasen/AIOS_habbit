# syntax=docker/dockerfile:1
# AIOS WorkLens VPS Production Image
# Container Architecture: Runtime Offline with Single-Tenant Data Isolation.
# Uses pre-packaged dedicated Linux wheelhouse (vendor/wheels_linux/) for all Python dependencies.

FROM python:3.11-slim AS builder

WORKDIR /build

# Copy dependency manifests and Linux vendored wheels
COPY pyproject.toml ./
COPY vendor/wheels_linux/ ./vendor/wheels_linux/

# Create virtual environment and install all dependencies strictly offline from Linux wheelhouse
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN /opt/venv/bin/pip install --no-index --find-links=vendor/wheels_linux "aios-habit[rag-retrieval-lab,rag-semantic,rag-ingestion-cpu,rag-ingestion-xls]"

# Runtime stage: Self-Contained, Runtime Offline
FROM python:3.11-slim AS runtime

# System runtime dependencies for fonts and rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    fonts-noto-core \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and directories
RUN groupadd -r aios && useradd -r -g aios -u 1000 -d /app -m aios
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source, packaging manifests and assets
COPY src/ /app/src/
COPY packaging/ /app/packaging/
COPY .agents/skills/excaliflow/assets/ /app/excaliflow/assets/
COPY pyproject.toml /app/

# Create and isolate single-tenant storage volume and read-only model mount point
RUN mkdir -p /app/local_cases /opt/aios/models/bge-m3-5617a9f && chown -R aios:aios /app /opt/aios

USER aios

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    AIOS_WORKSPACE_RAG_V2_CANARY_ENABLED=1 \
    AIOS_WORKSPACE_RAG_V2_LOCAL_PILOT_ENABLED=1 \
    AIOS_WORKSPACE_RAG_V2_PROFILE=bge_m3_hybrid \
    AIOS_BGE_M3_MODEL_PATH=/opt/aios/models/bge-m3-5617a9f \
    AIOS_BGE_M3_MODEL_REVISION=5617a9f61b028005a4858fdac845db406aefb181 \
    AIOS_BGE_M3_MODEL_CHECKSUM=sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61 \
    AIOS_RETRIEVAL_DEVICE=cpu \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

EXPOSE 8501

VOLUME ["/app/local_cases", "/opt/aios/models/bge-m3-5617a9f"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "src/aios_habit/workspace_chat_app.py"]
