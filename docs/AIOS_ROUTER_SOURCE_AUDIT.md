# AIOS ROUTER SOURCE AUDIT REPORT

Gate: AIOS-Router-0 — Source Audit + Vietnamese Auto Policy Plan

## AIOS baseline

- HEAD: `8db94bb Add local AI provider bridge`
- Current expected HEAD: matches `8db94bb`
- tests: `py -3 -m pytest` => `197 passed in 8.01s`
- package import: `package import ok`
- CLI audit: `{"errors": [], "status": "PASS", "warnings": []}`
- clean status:
  - tracked worktree before this audit doc: clean
  - ignored runtime/cache data present: `.pytest_cache/`, `local_cases/`, `src/aios_habit.egg-info/`, `__pycache__/`, and generated AIOS output folders

## Repo availability

### translation_app

- local path: `D:\Sandbox\translation_app`
- exists: yes
- remote: `https://github.com/Nakazasen/translation_app.git`
- branch: `wip/phase-5n-f-ocr-benchmark`
- HEAD: `f105ffb3ac84b9ec38f03e882656826b2001d341`
- status: only untracked `.vscode/`
- important files: `core/provider_router.py`, `core/providers/`, `core/provider_health_checker.py`, `core/ai_service.py`, router/provider tests

### nvidia-server

- local path: `D:\Sandbox\Nvidia`
- exists: yes
- remote: `https://github.com/Nakazasen/nvidia-server`
- branch: `main`
- HEAD: `77e45e44e8589d24618c5ea59ec1dd31945dcf89`
- status: no tracked/untracked changes reported by `git status --short`
- important files: `tools/agent-core.mjs`, `electron-main.js`, `nvidia_playground.html`, `package.json`, `README.md`, `docs/`, `tests/`

### mat-the-website

- local path before audit: missing
- action: cloned from `https://github.com/Nakazasen/mat-the-website`
- exists after clone: yes
- remote: `https://github.com/Nakazasen/mat-the-website`
- branch: `main`
- HEAD: `e393bd4b9e6b64cbc60f9abcf4970adf622ae636`
- status: clean after clone
- important files: `backend/ai_providers/router.py`, `backend/ai_providers/`, `backend/rate_limit.py`, `backend/security_utils.py`, `backend/main.py`

## translation_app findings

### provider router

- `core/provider_router.py` is the strongest router source found.
- It implements provider registration, candidate iteration, provider/model/key state, retry/fallback, dynamic ordering, cooldown, circuit breaker behavior, and attempt tracing.
- It is synchronous and translation-specific, so AIOS should port concepts, not copy the module directly.

Classification:

- PORT_NOW: provider state model, error classification ideas, cooldown behavior, health snapshot shape, attempt trace model, key/model candidate rotation concept.
- PORT_LATER: strict provider/model pinning, Google Translate last-resort behavior only if AIOS has a matching use case.
- NEEDS_REWRITE: `TranslationRequest` / `TranslationResult` into AIOS Q&A/case request/result types, and direct dependency on `translation_app.core.ai_service`.
- DO_NOT_PORT: translation-only prompt building and UI text that exposes technical router labels.

### providers

Provider support is broad and 9router-like:

- Gemini
- Google Translate fallback
- ChatAnyWhere
- DeepSeek
- NVIDIA NIM
- generic OpenAI-compatible endpoint
- Groq
- Cerebras
- OpenRouter
- Mistral AI
- SambaNova
- Cloudflare Workers AI
- HuggingFace
- GitHub Models
- AI21 Studio

The key reusable provider catalog is `core/providers/profiles.py`.

Classification:

- PORT_NOW: provider catalog normalization, public redacted provider config view, display names, base URL/model defaults.
- PORT_LATER: Cloudflare and HuggingFace custom adapters.
- NEEDS_REWRITE: provider request contract for AIOS grounded Q&A and WorkLens.
- DO_NOT_PORT: translation-specific provider names in AIOS UX.

### fallback

- Router tries providers in resolved order.
- Failed attempts are recorded and the next candidate/provider is tried.
- Final error includes the last attempt and an exhausted message.

Classification: PORT_NOW after adapting to AIOS result schema.

### cooldown

- Quota/rate-limit and transient errors trigger cooldown.
- `Retry-After` support is present.
- Some providers have minimum inter-request intervals.

Classification: PORT_NOW.

### circuit breaker

- Authentication errors mark a provider unavailable.
- The router attempts to persistently disable invalid providers via config manager.
- Health status can become `dead`, `cooldown`, `degraded`, or `healthy`.

Classification:

- PORT_NOW: runtime circuit breaker behavior.
- PORT_LATER: persistent auto-disable, only after AIOS has a safe settings UI.

### key rotation/secrets

- `ProviderProfile` supports multiple API keys.
- `OpenAICompatibleProvider.iter_candidates()` expands model x key candidates.
- `mark_success()` and `mark_failure()` rotate keys/models.
- Keys are masked via suffix (`****1234`) for public status.
- `AIConfigManager` separates config and secrets, supports backup loading and secret overlay.

Classification:

- PORT_NOW: masked key id in route logs, key candidate rotation, config-vs-secret separation concept.
- PORT_LATER: full secret store migration.
- DO_NOT_PORT: any real keys or generated local config files.

### health

- `core/provider_health_checker.py` checks provider/model responsiveness.
- It maps low-level errors to Vietnamese user messages and suggestions.
- It updates router health where possible.

Classification:

- PORT_NOW: health status display concept and Vietnamese health messages rewritten for AIOS terms.
- PORT_LATER: live provider probing, because this audit must not call real keyed providers.

### tests

Strong router-related test coverage exists:

- `tests/test_provider_router.py`
- `tests/test_free_llm_pool.py`
- `tests/test_provider_health_checker.py`
- `tests/test_provider_model_catalog.py`
- `tests/test_provider_model_discovery.py`
- `tests/test_provider_priority_ui.py`
- `tests/test_specific_provider_fallback.py`

Classification: PORT_NOW as test design references, not direct copied source.

### reusable components

1. Provider catalog with normalized profiles.
2. OpenAI-compatible adapter pattern.
3. Candidate expansion across model pool and key pool.
4. Cooldown and circuit breaker error classification.
5. Health snapshot and attempts trace.
6. Vietnamese status/suggestion style for non-technical users.
7. Tests for fallback, quota, health, and priority behavior.

## nvidia-server findings

### provider abstraction

- No mature multi-provider pool comparable to `translation_app` was found.
- The strongest code is not provider routing but agent workspace/runtime infrastructure.
- `tools/agent-core.mjs` uses an offline lexical provider for semantic index fallback, not a full AI provider router.

Classification:

- use now for router: no
- use later for AIOS Agent Runtime: yes

### MCP/CLI runtime

`tools/agent-core.mjs` provides file tools, search, indexing, git tools, pending edits, command execution, background command jobs, job status, and cancellation.

Classification: PORT_LATER for `AIOS-Agent-Later`, not AIOS-Router-1.

### context picker

- Builds an index cache with file metadata and line chunks.
- Skips unsafe/heavy folders such as `.git`, `.brain`, `.nvidia-agent`, `node_modules`, `.venv`, caches, build outputs.
- Supports lexical search over chunks and boosts changed/recent files.
- Redacts secrets when indexing/returning content.

Classification: PORT_LATER for WorkLens context picker and agent runtime.

### job manager

- `startCommandJobTool`, `commandJobStatusTool`, and `cancelCommandJobTool` manage long-running shell jobs.
- Jobs retain stdout/stderr and support chunked offsets.

Classification: PORT_LATER for AIOS agent jobs and audit trails.

### safety/audit

Useful patterns:

- workspace trust gate before write/command operations
- path containment checks
- destructive action confirmation
- pending edits before writes
- secret redaction for outputs/logs
- permission definitions with risk levels and approval requirements

Classification: PORT_LATER for AIOS Agent Runtime.

### reusable concepts

1. Workspace trust.
2. Pending edit queue.
3. Command job manager.
4. Tool permission table.
5. Secret redaction.
6. Context indexing and retrieval.

## mat-the-website findings

### AI router

- Contrary to the initial expectation, this repo does contain AI router code.
- `backend/ai_providers/router.py` explicitly says it was ported from `translation_app.core.provider_router.ProviderRouter` and converted to async for FastAPI.
- It supports waterfall fallback, `ai_pool_auto`, provider health state, cooldown, key/model candidate attempts, and attempt trace.
- It is useful as an async adaptation reference, but less authoritative than the original `translation_app` router.

Classification:

- AI router relevant: yes, as an async derivative.
- PORT_LATER: async route API patterns if AIOS later exposes router over web backend.
- NEEDS_REWRITE: dependencies and web-novel translation domain specifics.

### backend/security pieces

Relevant backend patterns:

- `backend/rate_limit.py`
- `backend/security_utils.py`
- `backend/ai_providers/error_classifier.py`
- `backend/ai_providers/health.py`
- `backend/main.py` integration examples

Classification: backend pattern only; not primary router source.

### recommendation

- Do not use `mat-the-website` as the source of truth for the router.
- Use it to learn how the router was adapted to async FastAPI and backend route integration.
- Keep AIOS-Router-0 focused on `translation_app` for router maturity.

## Ranking

1. `translation_app` — best provider router source.
2. `mat-the-website` — useful async/backend derivative.
3. `nvidia-server` — best agent runtime source, not router source.

## Comparative matrix

| Criterion | translation_app | nvidia-server | mat-the-website |
|---|---:|---:|---:|
| AI provider router maturity | High | Low | Medium |
| Number of providers supported | High | Low | Medium |
| Fallback/cooldown/circuit breaker | High | Low | Medium-High |
| Key/security handling | High | Medium-High for runtime redaction | Medium |
| Tests | High | Medium | Medium |
| Ease of porting to AIOS | Medium | Low for router, Medium for agent runtime | Medium |
| Relevance to AIOS WorkLens router | High | Low now, High later for agent runtime | Medium |

## Vietnamese UX policy

The UI must use only these Vietnamese user-facing modes and explanations. It must not expose raw implementation terms.

### Tự động

- AIOS tự đoán mức an toàn của tài liệu.
- Đường dẫn hoặc nội dung liên quan MOM, WMS, ERP, nhà máy, công ty, nội bộ, hợp đồng, nhân sự, tài chính, khách hàng mặc định được xử lý theo chế độ an toàn cho công ty.
- Nếu AIOS không chắc, hỏi người dùng: “Đây có phải tài liệu công ty hoặc tài liệu mật không?”
- Người dùng không cần hiểu nhà cung cấp AI, tuyến xử lý, endpoint, hay nhãn kỹ thuật.

### Tài liệu công ty / tài liệu mật

- Không gửi ra ngoài.
- Chỉ dùng dữ liệu cục bộ, AI nội bộ, hoặc điểm kết nối đã được tin cậy.
- Nếu chưa có AI nội bộ, AIOS vẫn trả lời bằng dữ liệu cục bộ và nói rõ phần nào chưa đủ bằng chứng.
- Không âm thầm chuyển sang AI bên ngoài.

### Tài liệu thường

- Dùng toàn bộ nguồn AI đã cấu hình.
- Tự chọn nguồn AI tốt nhất.
- Tự đổi nguồn khi lỗi, hết lượt, quá tải, hoặc phản hồi chậm.
- Tự đổi key nếu người dùng đã cấu hình nhiều key.
- Có thể hỏi nhiều AI cùng lúc nếu bật chế độ nhanh.
- Ghi “Nhật ký AI đã dùng” để người dùng biết AIOS đã dùng nguồn nào.
- Không hạn chế giả tạo ngoài giới hạn thật về lượt dùng, chi phí, tốc độ, và cấu hình của người dùng.

### terms removed from UI

The following raw terms must not appear in user-facing UX for this roadmap:

- `cloud_allowed`
- `local_only`
- `provider policy`
- `route policy`
- raw enum names
- raw provider routing jargon where a Vietnamese non-technical phrase is available

Acceptable Vietnamese replacements:

- “Tự động”
- “Tài liệu công ty / tài liệu mật”
- “Tài liệu thường”
- “Không gửi ra ngoài”
- “Dùng toàn bộ nguồn AI đã cấu hình”
- “Nhật ký AI đã dùng”
- “Tự đổi nguồn khi lỗi/hết lượt/quá tải”

## Integration roadmap

### AIOS-Router-1: Vietnamese Safety Mode UX

- Add visible Vietnamese modes: “Tự động”, “Tài liệu công ty / tài liệu mật”, “Tài liệu thường”.
- Hide all raw technical routing labels from user-facing UI.
- Add automatic classification explanation in plain Vietnamese.
- If uncertain, ask: “Đây có phải tài liệu công ty hoặc tài liệu mật không?”

### AIOS-Router-2: Provider catalog from translation_app

- Add AIOS provider catalog based on `translation_app` concepts.
- Support configured source list and health status.
- Keep secrets out of committed config.
- Show only masked key suffixes in user-visible status.
- Do not copy source directly; rewrite for AIOS request/response types.

### AIOS-Router-3: automatic router for “Tài liệu thường”

- Use provider pool for normal documents.
- Add retry, fallback, key rotation, cooldown, and circuit breaker behavior.
- Preserve deterministic/local fallback if no provider works.

### AIOS-Router-4: route log UI

- Add “Nhật ký AI đã dùng”.
- Show provider display name, model display name, masked key suffix, status, latency, and reason in Vietnamese.
- Never show raw API keys.

### AIOS-Router-5: optional parallel race

- Add optional “Hỏi nhiều AI cùng lúc để lấy câu nhanh/tốt hơn”.
- Only for “Tài liệu thường”.
- Respect configured quotas/cost/rate limits.

### AIOS-Router-6: privacy audit

- Prove company/confidential documents do not go to external AI.
- Prove normal documents can use provider pool.
- Prove secrets are masked.
- Prove route trace is correct.

### AIOS-Router-7: DOM/unit audit

- Prove user never sees raw technical route labels.
- Prove automatic mode works.
- Prove normal docs use provider pool.
- Prove company docs block external AI.
- Prove route log is visible.

### AIOS-Agent-Later

Learn from `nvidia-server`:

- context picker
- MCP/CLI bridge ideas
- job manager
- tool approval
- pending edits
- workspace trust
- audit trail
- secret redaction

This is explicitly later and must not open P1.0.

## Safety

- no secret commit: PASS. This audit doc contains no API keys or secrets.
- no cloud for company/mật: required by roadmap. No real provider calls were made in this audit.
- cloud/free pool for tài liệu thường: planned only after user-visible Vietnamese safety UX exists.
- no P1.0: PASS. This audit did not open P1.0.
- no copied third-party source into AIOS: PASS. This document summarizes findings only.
- no MOM/company document upload: PASS. No company documents were sent to cloud.
- no fake Antigravity bridge: PASS. Existing AIOS result remains that Antigravity direct API has no callable HTTP/MCP/CLI runtime for this app.

## Overall verdict

TRANSLATION_APP_ROUTER_BEST_SOURCE

Additional verified verdicts:

- NVIDIA_RUNTIME_BEST_SOURCE
- MAT_WEBSITE_NOT_RELEVANT_FOR_ROUTER is not fully true after audit; it has a derivative router, but it is not the best source.

## Recommended next

1. Implement AIOS-Router-1 Vietnamese Safety Mode UX

Reason:

- AIOS must first protect users from technical routing concepts.
- It must ensure company/confidential documents are safely handled before enabling the broad provider pool for normal documents.
- This creates the correct UX and safety foundation for AIOS-Router-2 and AIOS-Router-3.
