# Strong Model Answer Bridge Design

## Current State

*   **Local Evidence Draft**: The `rag_answer_composer.py` currently builds a deterministic template (`LocalAnswerDraft`) based strictly on extracted evidence snippets. It uses labels like `Confidence`, `Warnings`, and `Evidence-grounded points`.
*   **Privacy**: Currently, metadata-only chunks or evidence labeled `local_only` block external exportation and warn the user.
*   **IDE Prompt Pack / Paste-back**: Currently done via `.ai/` prompt exports manually, and the owner pastes the answer back. There is no automated IDE-to-model bridge linked directly to the RAG pipeline that records the exact `provider_name` and `evidence_refs`.
*   **Provider Router/Safety**: `ai_provider_bridge.py` exists with `ProviderConfig`, `ProviderResult`, and `answer_with_provider`. The catalog in `provider_catalog.py` lists various open-source and proprietary models categorized by privacy/safety.

## Where Strong Model Answer Plugs In

The strong model answer generation should plug into the RAG pipeline **after** `RAGEvidencePack` is generated and **before** finalizing the answer.

Flow:
1. User submits question.
2. Search and rerank yields `RAGEvidencePack`.
3. Check `pack.privacy_mode` and `config.locality`.
4. If allowed, invoke `StrongAnswerProvider.generate_answer()` to build `StrongModelAnswer`.
5. If blocked, fallback to `LocalAnswerDraft` and suggest exporting a prompt pack for manual paste-back (`PastedStrongModelAnswer`).

## Privacy Modes & Rules

*   **Public/Normal (`cloud_safe`)**: Provider call to cloud APIs (OpenAI, Gemini, Claude, etc.) is **allowed** if configured.
*   **Company/Confidential/Local-only (`local_only`)**: Provider call to cloud APIs is **blocked** unless the provider locality is `local` (e.g., `ollama`, `lm_studio` running locally) or explicit override exists. If blocked, fall back to exporting the prompt for a trusted channel.
*   **Local Model**: Always allowed as long as the endpoint is verified as local.

## Goal Alignment
*   **No NotebookLM parity claim**. This is a foundation for AIOS to stand on its own.
*   **No P1.0 release**. This feature is an internal improvement.
