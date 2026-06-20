# Inheritance Audit Summary

## Summary
AIOS_habbit remains the central product repository. The other three repositories are valuable inheritance sources, not parallel products.

## Repo Roles
- `AIOS_habbit`: central WorkLens / Case Cockpit product.
- `ABW_NVIDIA_FUSION_CONTROL`: governance and bridge strategy reference.
- `skill-Anti-brain-wiki_note`: knowledge workflow and evidence governance reference.
- `Nvidia`: agent runtime/provider/tooling reference.

## Immediate Harvest Guidance
No source code should be ported yet. All candidates remain NEEDS_AUDIT or PAUSE.

## Strongest Candidates
1. No-fake-success governance discipline from ABW.
2. Decision/recovery logs from ABW_NVIDIA_FUSION_CONTROL.
3. Browser smoke testing patterns from Nvidia.
4. Raw/processed/wiki separation from skill-Anti-brain-wiki_note.

## Paused Candidates
- Electron desktop shell.
- Full provider runtime.
- Full ABW workflow surface.
- Predictive failure intelligence.

## Case Loop Fit
The only candidates to pursue next are those that strengthen:
Case → Evidence → Map → Action → Learning.
