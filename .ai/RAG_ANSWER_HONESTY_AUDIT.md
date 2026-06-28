# RAG Answer Honesty Audit

## Why current "AIOS answer" is misleading
The output from the local deterministic template (in `rag_answer_composer.py`) simply lists citations and calls them an "answer". This is presented to the user and evaluator as if it's a semantic, synthesized AI response, when in reality it's just a raw concatenation of retrieved snippets.

## Where metadata-only chunks are created
In `src/aios_habit/notebooklm_compare.py` (lines ~114-118), when the MVP harness processes unsupported files (like PDFs, PPTX, or binary files that the extractor cannot parse), it generates a fallback chunk with text like:
`"Metadata-only source record for <filename>. Relative path: <path>. File type: <ext>. Raw binary content was not extracted by the MVP harness."`

## Where metadata-only is treated as usable evidence
In `src/aios_habit/rag_evidence.py`, the system ranks all search results based on FTS matches. A query might match the filename or path in the metadata-only text, causing this placeholder chunk to be retrieved as valid evidence. The composer then blindly extracts this "Metadata-only" text and uses it as a citation.

## Where confidence high is assigned incorrectly
Also in `src/aios_habit/rag_evidence.py` (around line 174), confidence is assigned purely heuristically: `if top_score > 10.0 and document_count > 1: confidence_label = "high"`. Because SQLite FTS can give scores > 10 for exact matches on filename keywords, the system assigns "high" confidence even if the text is entirely metadata-only.

## Why local composer is not a model answer
`rag_answer_composer.py` does not invoke an LLM. It performs deterministic formatting. A final model answer implies semantic synthesis, reasoning, and hallucination safety via a true language model. 

## What needs to be renamed/relabelled
- Output from `rag_answer_composer.py` must be explicitly named **Local Evidence Draft** (or `local_evidence_draft`), not "AIOS answer" or "final answer".
- Reports and variables (like `aios_answers`) should clarify they refer to the "local draft".

## What must block final answer generation
A final answer generation must be blocked if:
- The evidence contains NO real extracted content (i.e., only metadata).
- If only metadata is retrieved, the composer must abstain and state that only file metadata was found, not document content.

## Status
- NotebookLM parity claimed: NO
- P1.0 opened: NO
