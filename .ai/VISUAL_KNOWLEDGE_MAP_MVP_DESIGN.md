# Visual Knowledge Map MVP Design

## Purpose

The Visual Knowledge Map MVP turns AIOS case work into a local-first, evidence-grounded work graph. It is not only a pretty note graph. Its job is to show how cases, sources, evidence, claims, answers, decisions, actions, risks, and learning cards connect, with enough traceability for an owner to inspect why a relationship exists before acting.

The map supports the product direction already stated in the roadmap: Case -> Evidence -> Map -> Action -> Learning -> Memory. It should help the owner answer practical questions:

- What evidence supports this answer or decision?
- Which claims are unsupported or limited?
- What action is blocked by missing evidence?
- What lesson should be reused next time?
- Which privacy constraints prevent export or external model use?

## Relation To Obsidian And Claude-Style Graphs

The user-visible inspiration is an Obsidian/Claude-style graph: nodes and links make a work topic easier to see. AIOS should borrow the clarity of a graph, not the weak assumptions of a note graph.

Obsidian-style graphs usually connect notes by backlinks. AIOS must connect work objects by typed relationships and evidence. A note can be "related" to another note without proof; an AIOS edge must say why it exists, which evidence supports it, and how confident it is.

Claude/LLM-generated graphs can be useful for brainstorming, but AIOS must treat generated graph content as draft unless it is tied back to local evidence. Imported model graph data can be displayed as unverified, but it must not silently become trusted business knowledge.

## How AIOS Differs From Obsidian And NotebookLM

AIOS differs from Obsidian:

- Graph nodes are work objects, not just markdown notes.
- Edges are typed and reasoned, not generic backlinks.
- Claims require evidence or explicit missing-evidence markers.
- Privacy metadata travels with nodes and edges.
- The graph drives decisions, next actions, and learning reuse.

AIOS differs from NotebookLM:

- The source of truth stays local-first.
- Graph export modes enforce privacy before any external use.
- AIOS does not claim NotebookLM replacement or parity from this design.
- The graph can include local case state, owner decisions, actions, and learning cards that are not simply source-document summaries.
- Generated or imported model outputs remain bounded by claim guard and evidence validation.

## Current Repo Context

Existing useful surfaces:

- `Case` in `src/aios_habit/case_models.py` has `case_id`, title, status, priority, sources, evidence IDs, timeline events, hypotheses, next actions, decisions, route summary, privacy, and verification status.
- `EvidenceItem` has `evidence_id`, `case_id`, source type/path, title, extracted text, structured summary, confidence, privacy, source origin, review status, and verification status.
- `case_store.py` loads and saves local JSONL case/evidence state under ignored local runtime folders.
- `learning_models.py` stores senior learning cards with causes, actions taken, reusable lessons, check-first-next-time, useful phrases, and confidence.
- `final_answer_composer.py` creates final owner answers with citations, evidence IDs, warnings, insufficient-evidence flags, confidence, domain playbook metadata, and no NotebookLM/P1.0 overclaim.
- `ide_handoff_bridge.py` imports strong Antigravity answers with request validation, evidence IDs, privacy acknowledgement, full-bundle use, and save-back as `ide_handoff_strong_answer`.
- `claim_guard.py` blocks broad NotebookLM/P1.0/replacement claims without sufficient scope and review.
- `worklens_semantic_map.py`, `knowledge_map_view.py`, `knowledge_map_html.py`, and `visual_knowledge_map.py` contain earlier map/graph concepts. The MVP should reuse lessons from them, but the next implementation must upgrade schema discipline, typed relationships, privacy filtering, and claim coverage.

Gaps to address in the next implementation:

- Current visual graph edges are relation strings but do not yet enforce the required typed edge set.
- Current graph nodes do not yet carry the full required schema.
- Claim, limitation, missing evidence, privacy export mode, and claim guard results are not first-class graph objects.
- The current visual export is useful as a prototype, not the final MVP contract.

## Graph Layers

### 1. Case Graph

Connects the active case to its work state:

- `case -> evidence`
- `case -> answer`
- `case -> decision`
- `case -> action`
- `case -> learning_card`
- `case -> risk`

Purpose: show one active case as a work board with evidence, answer, action, and learning context.

### 2. Evidence Graph

Connects evidence to source material and the claims it can support:

- `evidence -> source`
- `evidence -> extracted_fact`
- `evidence -> claim`
- `evidence -> limitation`

Purpose: make the user inspect source-backed facts before trusting a decision or answer.

### 3. Decision Graph

Connects decisions and answers to support, uncertainty, and next steps:

- `answer -> supporting evidence`
- `answer -> unsupported claim`
- `answer -> confidence`
- `answer -> missing_evidence`
- `decision -> next action`

Purpose: show what is safe to act on, what is still weak, and why.

### 4. Action Graph

Connects actions to ownership, status, prerequisites, and results:

- `action -> person_or_role`
- `action -> due status`
- `action -> required evidence`
- `action -> blocker`
- `action -> result`

Purpose: make the map operational, not just descriptive.

### 5. Learning Graph

Connects reusable learning to cases, checklists, and useful language:

- `learning_card -> similar cases`
- `learning_card -> checklist_item`
- `learning_card -> useful phrase/email/chat`
- `learning_card -> check_first_next_time`

Purpose: turn resolved work into reusable senior memory.

### 6. Risk/Claim Graph

Connects claims and risks to evidence strength and overclaim protection:

- `claim -> evidence strength`
- `claim -> missing evidence`
- `claim -> privacy constraint`
- `claim -> claim_guard result`

Purpose: prevent fake confidence, privacy leaks, and broad claims from narrow evidence.

## Node Schema

All nodes use this generic schema:

```json
{
  "node_id": "node_case_CASE-123",
  "node_type": "case",
  "title": "Owner-visible title",
  "short_label": "Short label",
  "description": "What this node means",
  "source_case_id": "CASE-123",
  "evidence_ids": ["EVD-1"],
  "privacy_level": "local_only",
  "confidence": "low|medium|high|confirmed|unknown",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "domain": "general|hr|accounting|japanese_learning|it_manual|legal|manufacturing|office",
  "tags": ["topic"],
  "status": "draft|reviewed|verified|blocked|done|open",
  "local_only": true,
  "display_title": "Redacted or safe title for UI/export",
  "limitations": ["optional limitation"],
  "metadata": {}
}
```

Required node types:

- `case`: a Case Cockpit case.
- `source`: a source file or imported source record.
- `evidence`: an `EvidenceItem`.
- `extracted_fact`: a fact extracted from evidence.
- `claim`: a statement that needs support or limitation.
- `answer`: local final owner answer, strong answer, or imported IDE answer.
- `decision`: owner decision or recommended decision.
- `action`: next action, follow-up, or checklist action.
- `risk`: risk, blocker, privacy risk, or operational risk.
- `missing_evidence`: needed source, log, screenshot, record, confirmation, or owner input.
- `learning_card`: senior learning card.
- `checklist_item`: reusable check-first-next-time item.
- `person_or_role`: role such as owner, reviewer, requester, operator, accountant, HR, legal reviewer.
- `system_or_tool`: system, application, AI tool, IDE, workflow, or local model.
- `tag/topic`: topic, entity, process, issue family, or workstream tag.
- `domain_playbook`: the selected generic/domain playbook used to guide interpretation.

Privacy and identity rules:

- Do not put real personal names in display fields unless owner approval exists and export mode allows it.
- Redact employee IDs and personal identifiers by default.
- Store safe placeholders such as `[PERSON_REDACTED]`, `[EMPLOYEE_ID_REDACTED]`, and `[LOCAL_SOURCE]`.
- Use safe basenames for sources; avoid absolute local paths in display/export.

Multi-domain requirement:

The same schema must work for HR policy, accounting invoice/payment cases, Japanese learning, IT manuals, legal contract review, manufacturing issues, and general office work. Domain-specific terms may appear only as node data or optional playbook metadata, not as hardcoded graph logic.

## Edge Schema

All edges use this generic schema:

```json
{
  "edge_id": "edge_CASE-123_EVD-1_supports",
  "from_node_id": "node_evidence_EVD-1",
  "to_node_id": "node_claim_CLM-1",
  "edge_type": "supports",
  "reason": "The evidence text directly states the claim boundary.",
  "evidence_ids": ["EVD-1"],
  "confidence": "medium",
  "direction": "directed",
  "created_at": "ISO-8601",
  "privacy_level": "local_only",
  "local_only": true,
  "metadata": {}
}
```

Required edge types:

- `cites`
- `supports`
- `contradicts`
- `derived_from`
- `requires`
- `blocks`
- `follows_up`
- `similar_to`
- `caused_by`
- `mitigates`
- `assigned_to`
- `belongs_to`
- `extracted_from`
- `answered_by`
- `has_limitation`
- `has_missing_evidence`
- `updates_learning`
- `uses_domain_playbook`

Rules:

- Do not create untyped edges.
- Do not use `related` as a default relationship. If no better edge type exists, omit the edge or mark it as a low-confidence candidate in an implementation-only review queue.
- Every important edge must include a human-readable reason.
- Important edges must include evidence IDs or a clear explanation that they are owner-entered case state.

## Graph Generation Pipeline

The MVP generation pipeline is deterministic-first.

Inputs:

- cases
- evidence items
- final owner answers
- strong answers imported from Antigravity
- senior learning cards
- claim guard output
- source metadata
- route/source metadata
- domain playbook selection

Outputs:

- graph JSON
- optional Mermaid summary
- optional UI-ready graph data
- owner-readable summary

Pipeline:

1. Collect graph candidates from case state, evidence, answers, decisions, actions, learning cards, source records, and claim guard results.
2. Normalize nodes into the required schema.
3. Normalize edges into the required typed edge schema.
4. Attach evidence references and source references to every claim/answer/decision edge where possible.
5. Apply privacy filter by export mode.
6. Apply confidence and claim guard results.
7. Collapse low-value duplicates by stable IDs and normalized labels.
8. Export graph JSON.
9. Export owner-readable summary with warnings, missing evidence, and next actions.

Deterministic-first means:

- Existing case/evidence/answer structures are parsed first.
- LLM extraction can be a later optional assist, never the source of truth.
- Any model-generated node or edge must be marked draft until supported by evidence or owner review.

## Privacy Model

Graph export modes:

- `local_full`: full local graph for local UI only.
- `local_redacted`: local graph with personal identifiers and unsafe source paths redacted.
- `cloud_safe_summary`: summary graph with no local-only content, no raw confidential text, and no unsafe paths.
- `notebooklm_safe`: export-safe graph summary for manual NotebookLM-related workflows, without claiming replacement or parity.

Rules:

- `local_only` nodes cannot be exported to cloud, NotebookLM, or provider paths.
- If a node is `local_only`, all edges exposing it are `local_only` or redacted.
- Person names and employee IDs are redacted by default unless explicit owner approval exists.
- Source paths display as safe filenames or `[LOCAL_SOURCE]`.
- `cloud_safe_summary` must omit raw source text and local-only evidence snippets.
- Any graph export should include `export_mode`, `privacy_summary`, and `redaction_summary`.

## UI MVP Design

Design only. No UI implementation in this sprint.

Proposed Case Cockpit section:

`Bản đồ tri thức công việc`

MVP views:

1. Current Case Map
   - Shows this case, evidence, answer, decisions, actions, risks, and learning.
2. Work Stream Map
   - Shows related cases, topics, and actions across time.
3. Evidence Map
   - Shows which sources/evidence support which claims.
4. Learning Map
   - Shows reusable lessons, checklists, and check-first-next-time items.

Required interactions:

- filter by domain
- filter by privacy
- filter by confidence
- filter by node type
- click node to see evidence
- click edge to see relationship reason
- show missing evidence and risk clearly
- export local JSON
- export safe Mermaid
- no CLI required for owner flow

Interaction details:

- Node click payload should show node schema fields, safe source references, evidence IDs, limitations, confidence, and privacy.
- Edge click payload should show edge type, reason, evidence IDs, confidence, and privacy.
- Missing evidence should be visible as first-class nodes, not hidden warnings.
- Claim guard blocks should appear as risk/claim nodes and `blocks` edges.

## MVP Boundaries

The MVP must not attempt:

- automatic perfect knowledge graph from all files
- global semantic ontology
- production prediction
- NotebookLM replacement claim
- automatic personal identity inference
- graph generation from confidential raw data without privacy filtering
- new graph UI library selection
- MOM/WMS-only graph logic

The MVP should do:

- generate a useful graph for one active case
- connect case/evidence/answer/decision/action/learning
- show missing evidence
- show confidence and limitations
- support future expansion to multi-case Work Stream Map
- remain generic across domains

## Implementation Phases

### Phase A - Schema Contract

- Add `visual_map_models.py` or equivalent schema module.
- Define node/edge dataclasses or typed dictionaries.
- Add validators for required fields, typed edges, evidence references, privacy, and confidence.
- Keep exports deterministic and local.

### Phase B - Current Case Graph Builder

- Build from one active case.
- Include case, evidence, source, answers, decisions, actions, risks, missing evidence, learning cards, and domain playbook.
- Map current answer warnings and unsupported claims to claim/risk/missing-evidence nodes.

### Phase C - Privacy-Safe Export

- Implement `local_full`, `local_redacted`, `cloud_safe_summary`, and `notebooklm_safe`.
- Redact paths, names, employee IDs, and local-only snippets.
- Add safety tests before UI work.

### Phase D - Owner UI MVP

- Add Case Cockpit section after schema and export tests pass.
- Start with tables and simple local JSON/Mermaid export.
- Only then consider a visualization library.

### Phase E - Work Stream Expansion

- Add multi-case graph from reviewed local data.
- Add learning reuse and similar-case edges.
- Keep import-derived graphs visibly unverified.

## Tests To Add

Future implementation tests:

1. creates case/evidence/action/learning graph nodes
2. creates typed edges, no untyped edge
3. every claim node has evidence or missing_evidence edge
4. local_only evidence is blocked from cloud_safe export
5. personal/local paths are redacted in graph export
6. graph works for HR sample case
7. graph works for accounting sample case
8. graph works for Japanese learning sample case
9. graph works for IT manual sample case
10. graph works for manufacturing case without hardcoding manufacturing terms
11. duplicate evidence nodes are collapsed
12. node click payload includes source/evidence reference
13. edge click payload includes reason
14. confidence and limitations are visible
15. no NotebookLM/P1.0 claim appears in graph output

Additional useful tests:

- claim guard blocked claims become risk/claim nodes
- imported Antigravity strong answer creates answer -> evidence `cites` edges
- final owner answer warning creates `has_limitation` edge
- missing evidence warning creates missing_evidence node
- source path export uses safe basename or `[LOCAL_SOURCE]`

## Risks

- A graph can look more authoritative than the evidence supports.
- Imported model graph data can be mistaken for verified knowledge.
- Untyped edges can make the map noisy and misleading.
- Privacy leaks can occur if local paths or personal identifiers are copied into export labels.
- Overfitting to one manufacturing benchmark would weaken the general work-brain goal.
- Adding a visualization library too early can distract from schema correctness.

## Non-Goals

- No graph UI implementation in this sprint.
- No new visualization library in this sprint.
- No automatic all-files knowledge graph.
- No graph database decision yet.
- No NotebookLM replacement or parity claim.
- No P1.0 opening.
- No domain-specific MOM/WMS-only logic.

## Claim Discipline

Allowed claim after this design:

- AIOS has a design for a Visual Knowledge Map MVP.
- The design is local-first, evidence-grounded, typed-edge, privacy-aware, and generic.

Not allowed:

- AIOS has implemented the Visual Knowledge Map MVP.
- AIOS replaces NotebookLM.
- AIOS has global parity with NotebookLM.
- P1.0 is open.
- Graph output is verified unless evidence and owner review prove it.
