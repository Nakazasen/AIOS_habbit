# Integration Decision Log

## Decision 0001 - Product Center and Inheritance Strategy
- Date: 2026-06-20
- Decision: AIOS_habbit is the central product repo for AIOS WorkLens / AIOS Case Cockpit.
- Decision: ABW_NVIDIA_FUSION_CONTROL, skill-Anti-brain-wiki_note, and Nvidia become inheritance sources.
- Decision: Do not merge or port code from inheritance sources before read-only audit.
- Decision: Case Cockpit is the survival vertical slice.
- Decision: Product loop is Case → Evidence → Map → Action → Learning.
- Consequence: All future features must justify contribution to the loop or be paused.
