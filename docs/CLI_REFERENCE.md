# CLI Reference
All commands have help text.
- `aios-habit status`
- `aios-habit discover --root D:\Sandbox --dry-run` metadata-only discovery.
- `aios-habit evidence add/list/validate` evidence pointers, not raw content.
- `aios-habit memory add/list/validate/export` verified memory requires evidence.
- `aios-habit extract` creates review candidates only; it does not auto-verify.
- `aios-habit workflow add/list/validate`
- `aios-habit decision add/list/validate`
- `aios-habit profile build` uses verified/export-allowed memory only.
- `aios-habit export --target generic|gpt|gemini|claude|grok` audit before use.
- `aios-habit audit`
- `aios-habit phase validate --phase N`
- `aios-habit handover build`
