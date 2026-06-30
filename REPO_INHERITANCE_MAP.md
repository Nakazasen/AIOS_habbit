# Repository Inheritance Map

| Repo | Current Role | Future Role | What to Keep | What to Wrap | What to Port Later | What to Pause | What to Drop Only If Proven Useless | Risks | Evidence Path |
|---|---|---|---|---|---|---|---|---|---|
| AIOS_habbit | Central product repo with CLI, Studio, Case Cockpit | AIOS WorkLens product center | Case Cockpit, privacy governance, tests, docs | CLI helpers behind UI | More modular architecture after pilot | Large refactor | Nothing yet | Feature creep, local data leaks | `[LOCAL_WORKSPACE]\AIOS_habbit` |
| ABW_NVIDIA_FUSION_CONTROL | Governance/control documentation repo for ABW/NVIDIA fusion | Governance reference source | Constitutional governance, bridge architecture, runtime status concepts | Governance checklist ideas | Decision log and safety contracts if mapped to WorkLens | Provider/runtime branding | Nothing yet | Encoding issues in docs, abstract governance could slow product | `[LOCAL_WORKSPACE]\ABW_NVIDIA_FUSION_CONTROL` |
| skill-Anti-brain-wiki_note | ABW skill/wiki/knowledge package | Knowledge governance and workflow reference | `.brain` structure, raw/processed/wiki pipeline, audit/eval discipline | Query/ingest workflow patterns | Safe wiki packaging and continuation patterns | Full ABW workflow surface in product UI | Nothing yet | Large surface area; may distract from Case Cockpit | `[LOCAL_WORKSPACE]\skill-Anti-brain-wiki_note` |
| Nvidia | Active agent runtime / provider shell | Agent bridge reference only | Provider abstraction, tool calling, command jobs, browser smoke patterns | CLI bridge concepts | Optional agent bridge after prompt packs stabilize | Electron/IDE clone, provider-heavy runtime | Nothing yet | Contains `.env`, node_modules, large runtime state; do not copy blindly | `[LOCAL_WORKSPACE]\Nvidia` |

No repository is classified as trash. All non-central repos remain inheritance sources pending deeper evidence-backed audit.

