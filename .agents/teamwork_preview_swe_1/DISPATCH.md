## 2026-08-21T06:34:10Z

Task: Install BGE-M3 retrieval dependencies (FlagEmbedding, PyTorch CPU, transformers), download the pinned BAAI/bge-m3 model weights, and configure the local RAG v2 activation manifest in AIOS Habit for CPU-based semantic retrieval.

Requirements:
1. R1. Dependency Installation & Virtual Environment Provisioning
- Install the required BGE-M3 ML packages into `.venv` with CPU support (`torch==2.5.1` or CPU wheel, `FlagEmbedding==1.3.5`, `transformers==4.44.2`, `sentence-transformers==3.1.1`).
- Ensure no dependency conflicts with the existing virtual environment.

2. R2. Model Weights Acquisition & Checksum Validation
- Download the `BAAI/bge-m3` model snapshot matching the pinned revision (`5617a9f61b028005a4858fdac845db406aefb181`) into the local model directory or HuggingFace cache.
- Validate that the model files and embeddings pipeline initialize properly in CPU mode.

3. R3. Deployment Manifest & Pipeline Activation
- Generate and activate the local deployment manifest (`config/workspace_chat_rag_v2.local.json`) or set the corresponding environment variables in `.env` (`AIOS_RETRIEVAL_DEVICE=cpu`, `AIOS_BGE_M3_MODEL_PATH`, `AIOS_BGE_M3_MODEL_REVISION`).
- Ensure the isolated subprocess worker (`bge_subprocess_worker.py`) can be spawned and serve retrieval requests without crashing the main Streamlit process.

4. Verification:
- Ensure FlagEmbedding and torch can be imported inside `.venv` without errors.
- Ensure `bge_subprocess_worker.py` starts, successfully loads `BAAI/bge-m3` on CPU, and responds to encode/retrieval test queries.
- Run targeted BGE-M3 test suite:
  uv run --no-sync pytest tests/test_rag_v2_semantic.py tests/test_bge_subprocess_client.py tests/test_bge_subprocess_worker.py -q
- Ensure Streamlit Workspace Chat UI detects BGE-M3 semantic capability as active/ready.
