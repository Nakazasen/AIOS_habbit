# RAG Architecture Pattern Study

## Haystack
* **Relevant Patterns**: Pipeline and query routing design. The conditional router dynamically channels requests to the correct pipeline based on intent.
* **NOT Relevant Now**: Full replacement of our RAG core with their node/edge framework.
* **Minimal AIOS Patch Idea**: Implement a lightweight `classify_query_profile` function that checks the question intent against predefined categories and returns a `QueryProfile`.
* **Risk**: Copying their entire component architecture would introduce massive overhead.

## LlamaIndex
* **Relevant Patterns**: Node metadata, retriever/query engine separation, and especially the response synthesizer that uses different templates based on query types.
* **NOT Relevant Now**: The comprehensive indexing strategies (tree indices, graph indices).
* **Minimal AIOS Patch Idea**: Adapt the idea of a profile-specific response synthesizer. `final_answer_composer.py` should assemble different answer formats depending on the `QueryProfile`.
* **Risk**: Using LlamaIndex directly forces us to convert our evidence packs into their proprietary node structures.

## RAGFlow
* **Relevant Patterns**: Document and table layout understanding, and strict citation mapping.
* **NOT Relevant Now**: Deep vision/layout models.
* **Minimal AIOS Patch Idea**: Apply specific source-type targeting (e.g., demanding `spreadsheet` for table mapping profiles and `document` for processes) in `source_router.py`.
* **Risk**: High dependency risk if importing their vision models.

## RAGAS
* **Relevant Patterns**: RAG evaluator concepts, specifically context relevance, faithfulness, and answer relevance.
* **NOT Relevant Now**: Running the full LLM-as-a-judge suite in CI.
* **Minimal AIOS Patch Idea**: Add strict heuristic caps to the existing AIOS evaluator (`notebooklm_compare.py`) when source types or formats are mismatched (e.g., max 6/12 if profile mismatch).
* **Risk**: Too complex to configure as an automated test suite without a reliable LLM evaluator.

## GraphRAG (Microsoft) & LightRAG
* **Relevant Patterns**: Case-map and entity relation graphs. 
* **NOT Relevant Now**: Fully deferred. Do not implement now unless trivial.
* **Minimal AIOS Patch Idea**: None needed at this stage. Keep future design in mind.
