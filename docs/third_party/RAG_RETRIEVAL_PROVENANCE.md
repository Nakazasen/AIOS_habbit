# RAG retrieval third-party provenance

This file records externally maintained packages and model families used by the optional
Gate H retrieval laboratory. The default AIOS Habit installation does not install or load
these components.

## FlagEmbedding / BGE-M3

- Upstream repository: https://github.com/FlagOpen/FlagEmbedding
- Package: `FlagEmbedding==1.3.5`
- License: MIT (verify the installed distribution and selected model card before promotion)
- Integration: public `BGEM3FlagModel` API through
  `src/aios_habit/rag_v2/retrieval_backends.py`
- Behavior used: multilingual dense embeddings and learned sparse lexical weights
- Locality policy: the configured model path must exist locally; the complete directory tree
  is checked against the configured SHA-256 digest before model construction; network access
  is disabled during construction and inference.
- Model pin: runtime configuration must supply an explicit model revision and directory-tree
  checksum. No model weights are committed to this repository.

## BGE reranker v2 M3

- Model family: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Runtime package: `FlagEmbedding==1.3.5`
- License: verify the selected model card before promotion
- Integration: public `FlagReranker` API through
  `src/aios_habit/rag_v2/retrieval_backends.py`
- Behavior used: multilingual query-document cross-encoder scoring
- Locality policy: identical fail-closed path, revision, checksum, and offline constraints as
  BGE-M3.

## Haystack and RAGFlow

Haystack and RAGFlow informed the architectural review (separate retrievers, rank fusion,
reranking, and stage provenance), but no source code from either repository is copied in the
current Gate H implementation. If the stop-rule triggers and an adapter spike is implemented,
record its exact repository commit, source files, license, and modifications here.

## Verification requirements before promotion

1. Record the exact local model directory checksum in the tournament run metadata.
2. Record package versions, device, model revision, dimension, and measured runtime latency.
3. Run with network disabled after model acquisition is performed outside the benchmark.
4. Confirm dense, sparse, fused, and reranked pools are non-empty for applicable arms.
5. Preserve upstream notices if direct source is ever copied rather than called via public API.
