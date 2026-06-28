# Source-Aware Retrieval Design

## Current Retrieval Pipeline
Currently, `rag_search.py` relies on SQLite FTS5 (BM25) or fallback token matching. It fetches candidates and adds minor boosts if exact query terms appear in the text or source title. `rag_evidence.py` then takes the top-N results based on this generic `score`, without deep understanding of whether a particular document is the authoritative source for the query's specific domain (e.g., interface spec vs. general presentation).

## How PDF Adapter Changed Evidence Volume
The PyMuPDF extraction adapter successfully converted previously opaque PDFs into rich text chunks. While this improved answers overall by making content available, it drastically increased the volume of searchable text. A general PDF like a production history overview can now dominate search results due to repeated keywords, overshadowing shorter, highly-specific Excel staging tables or interface specs.

## Why Q3 Regressed
Q3 asks highly specific questions about "manual shipping," "Manual Supply Line," and "staging/table preconditions." Because general documents (like generic inventory cleanups or `MaterialQueue` descriptions) contain similar manufacturing terminology, FTS matched them highly. The system lacked an awareness that an Excel file named `補足資料_要件内容反映版` or a sheet named `ステージングテーブル` should be treated as the authoritative source for interface/staging logic, causing the strong model to hallucinate a generic process.

## Proposed Source-Aware Scoring Rules
1. **Query Intent Extraction**: Use a lightweight deterministic intent classifier (regex/keyword based) to categorize the query (e.g., `manual_shipping`, `design_change`).
2. **Intent-Based Boosts**:
   - *Explicit Filename Match*: High boost.
   - *Preferred Source/Sheet Term Match*: Medium-High boost.
   - *Content Term Match*: Medium boost.
3. **Penalties**:
   - *Metadata-Only*: Penalize if content-rich alternatives exist.
   - *Off-Topic*: Penalize generic files when the query is highly targeted and targeted sources are found.
4. **Transparency**: Each chunk must retain a `score_explanation` detailing why it was ranked (e.g., "Boosted: Explicit filename match for 'ステージングテーブル'").

## Preserving Recall While Improving Precision
To avoid missing answers when the specific target file isn't present, the system will not strictly *filter* out non-targeted files; it will only *rank* them lower. If targeted sources are absent, the highest lexical matches (even from broad PDFs) will bubble up to the top, ensuring fallback capability.

## Avoiding Hardcoded Factory Cases
The intent definitions will be built around generic document types (e.g., "interface", "staging", "workflow", "manual shipping", "design change") rather than hardcoding exact hashes of specific MOM documents. This ensures the rules generalize to other production lines or factories that use similar documentation conventions.

- NotebookLM parity claimed: NO
- P1.0 opened: NO
