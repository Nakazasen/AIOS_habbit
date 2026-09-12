# Data model: 012-ready-hybrid-recall

## ScriptFamily

`latin` | `cjk` | `mixed`

Quy tắc: số ký tự CJK (Hiragana/Katakana/Han/Hangul) so với Latin (kể dấu tiếng Việt). Bên nào nhiều hơn thắng; hòa → `mixed`.

## ReadyRetrievalWindow

Tập `WorkspaceAIContextSource` đưa vào hybrid.

- Đa ý (Goal 002) → toàn bộ ready
- Lệch hệ chữ (đa số nguồn) → toàn bộ ready
- Còn lại → `_select_semantic_candidate_sources` (tối đa 3)

## HybridRankingConfig

Đã có. Khi lệch chữ: `lexical_weight=0.25`, `dense_weight=1.5`, `sparse_weight=1.25` (mọi trọng số > 0).
