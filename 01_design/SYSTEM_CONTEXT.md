# System Context

AIOS Habit nằm giữa người dùng, project local và nhiều hệ AI khác nhau.

```text
User
 |
 | provides approved sources / feedback / validation
 v
AIOS Habit Local Repository
 |
 +--> Memory Vault
 +--> Project Index
 +--> Workflow Library
 +--> AI Export Packs
 |
 v
External AI Systems: GPT / Gemini / Claude / Grok / Future AI
```

## External Systems

- Local filesystem.
- Git repositories.
- AI chat transcripts if user approved.
- Markdown knowledge bases.
- Future AI tools.

## Boundary

AIOS Habit là source of truth cục bộ. External AI chỉ là execution environment.
