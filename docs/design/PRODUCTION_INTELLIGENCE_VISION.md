# Production Intelligence Vision

Status: `PLANNED — future design reference; no delivery gate opened`

Owner role: Project owner / product architect  
Last reviewed: 2026-08-08  
Review cadence: Before opening any production-traceability, alerting, prediction, or prevention Gate Card

## Purpose

AIOS WorkLens may evolve from local-first work intelligence into a
**local-first production-quality decision-support capability**. It will help a
human investigate and prevent manufacturing quality problems by retaining a
reviewable chain from a component lot to the observed manufacturing outcome.

This is a future design direction, not a claim that AIOS currently predicts
production failures. It does not open Phase 9, P1.0, a dependency change, or any
runtime behavior.

## North-star outcome

When a new production lot is assessed, an authorized user should eventually be
able to receive a bounded, evidence-backed result such as:

```text
Risk: medium, not a release/block decision.
Why: similar historical lots, measurements, line conditions, and jig outcomes.
Evidence: linked lot, Unit, test, defect, and investigation records.
Uncertainty: what is missing, conflicting, or not yet confirmed.
Suggested next check: a human-approved containment or verification step.
```

The system must never silently decide that a lot is good/bad, block production,
release product, or state a root cause as confirmed without the required human
and evidence controls.

## Traceability chain

The desired minimum chain is:

```text
Supplier / Component / Component Lot
              ↓
Incoming inspection and raw measurements
              ↓
BOM relation and Unit serial number
              ↓
Process run: line, station, machine, shift, time, controlled conditions
              ↓
Jig/test step, raw measurement, pass/fail, error code
              ↓
Defect, repair, disposition and final quality result
              ↓
Investigation: suspected cause, confirmed cause, false alarm, containment result
```

Each link needs stable identifiers, timestamps, source pointers, classification,
and provenance. Missing links must remain visibly missing—not invented from
similar names or an LLM assumption.

## Product maturity stages

### Stage 0 — trustworthy document intelligence (current prerequisite)

- Read local documents, tables, logs and reports.
- Retrieve evidence and provide citations.
- Abstain when evidence is insufficient.
- Measure answer quality without weakening privacy or provenance.

This is the current RAG v2 quality focus. It must mature before production
intelligence claims are made.

### Stage 1 — historical traceability and investigation

- Ingest structured, local production records with a published schema.
- Answer traceability questions, for example: which lots are shared by Units
  with a particular jig failure?
- Link operating records with applicable work instructions, repair notes and
  investigation reports.
- Show the chain and source records, including gaps and contradictory records.

No forecasting claim is allowed at this stage.

### Stage 2 — transparent alerts

- Evaluate reviewed rules and local statistical control signals.
- Flag unusual defect rates, test measurements, yield shifts or lot associations.
- Explain the specific rule/signal, comparison window and supporting records.
- Require an operator to acknowledge, investigate, dismiss or label the alert.

Alerts are investigation prompts. They are not automatic production controls.

### Stage 3 — human-reviewed risk prediction

- Train/evaluate a versioned local model only on a governed dataset with known
  outcomes and leakage controls.
- Return risk, calibration/uncertainty, influential factors and comparable
  historical evidence.
- Preserve the prediction version, feature schema, dataset identity and review
  decision.
- Require human review before any operational consequence.

A prediction must not be represented as causal proof.

### Stage 4 — evidence-backed prevention support

- Recommend verified containment, inspection, sampling or escalation actions.
- Explain which historical cases support the recommendation and where the
  evidence remains uncertain.
- Record the human decision and the later outcome so the system can learn from
  validated practice rather than copied chat language.

## Data and learning contract

### Minimum governed records

| Record | Required examples |
|---|---|
| Component and lot | `part_id`, `supplier_id`, `lot_id`, receipt/inspection time |
| Unit/BOM relation | `unit_serial`, assembly time, component `lot_id`, quantity/position where available |
| Process run | line, station, machine, shift, operator pseudonym where approved, controlled conditions |
| Jig/test | test ID/version, step, raw value/unit, limit/version, pass/fail, error code, timestamp |
| Quality outcome | defect code, repair/rework, final disposition, yield denominator |
| Investigation | suspected vs confirmed cause, evidence IDs, owner decision, containment and effectiveness |

### Data-quality rules

- Preserve raw measurements and their units; never retain only a rounded label.
- Keep test limit/version, jig/firmware/process revision and time so changes are
  not mistaken for material or supplier effects.
- Use stable IDs and explicit mapping records; names alone are not joins.
- Timestamp every event and distinguish event time from data-arrival time.
- Keep source hash/pointer and local privacy classification for each import.
- Separate facts, hypotheses, confirmed causes and recommendations.
- Record unknown/missing fields; do not silently replace them with defaults.

### Learning labels

The system may learn only from outcome labels that distinguish at least:

- `suspected`: a lead requiring investigation;
- `confirmed`: human-reviewed cause/outcome with retained evidence;
- `false_alarm`: signal was investigated and not confirmed;
- `unknown`: insufficient evidence to classify;
- `effective` / `ineffective`: reviewed outcome of a containment or corrective
  action.

Training/evaluation must prevent outcome leakage—for example, a final repair
code must not be used to predict a risk at lot-receipt time. Data splits must
respect time and relevant lot/supplier/Unit grouping so the test result is not a
copy of an already-seen production chain.

## Safety, privacy and operational boundaries

1. **Human authority:** output supports an authorized human decision; it never
   auto-blocks, auto-releases, auto-reworks, or changes process parameters.
2. **Evidence first:** every alert, prediction and recommendation identifies its
   evidence, rules/model version and known uncertainty.
3. **Local first:** production data remains `local_only` unless an explicit,
   approved policy and consent boundary authorizes a narrower external route.
4. **No domain hard-code in RAG v2 core:** production-specific schema, rules and
   adapters remain outside generic RAG/evidence contracts.
5. **Conflict visible:** conflicting limits, dates, test versions or outcomes
   are presented as a conflict requiring review, not silently merged.
6. **Rollback:** imports, rules, models and recommendations must be versioned,
   disableable and traceable to a recovery path.
7. **No causal overclaim:** correlation, similarity and risk scores are distinct
   from a confirmed root cause.

## Architecture direction

The future capability is a layered extension, not a replacement for RAG v2:

```text
Structured production imports and source documents
       ↓
Traceability records + provenance links
       ↓
Rule/statistical alert engine and, later, governed risk models
       ↓
Evidence selection, cited explanation and Workspace Chat
       ↓
Human review, decision record and validated outcome feedback
```

RAG v2 remains responsible for retrieving documentary evidence and explaining a
result in clear Vietnamese. Structured traceability, alerts and prediction must
be independently auditable; an LLM is not the calculator of record for a
threshold, a yield denominator, or a production release decision.

## Selective Semantica-inspired practices

Future work may adapt these concepts in lightweight, local implementations:

- typed relations between lot, Unit, test, defect and action;
- provenance/lineage attached to facts and decisions;
- explicit conflict states rather than forced merging;
- temporal validity of measurements, limits and process revisions;
- graph traversal only as an additional candidate-retrieval channel;
- decision records that link a recommendation to the human decision and outcome.

AIOS must not adopt the full Semantica framework by default. It introduces a
large, overlapping runtime and a second potential source of truth before any
answer-level or operational benefit is proven.

## Gate-opening evidence

No Stage 1–4 delivery Gate Card should open without the relevant evidence:

| Stage | Minimum evidence before opening implementation |
|---|---|
| 1: Traceability | Owner-approved data dictionary; sample records with stable joins; privacy classification; query acceptance set; import rollback plan |
| 2: Alerts | Baseline/control-window definition; reviewed thresholds; alert acknowledgement workflow; false-positive measurement plan; safe disable switch |
| 3: Prediction | Sufficient confirmed/negative outcomes; temporal/group leakage review; frozen evaluation protocol; calibration and bias review; owner approval for decision use |
| 4: Prevention | Reviewed corrective-action library; effectiveness evidence; human approval workflow; rollback/escalation policy; post-action outcome capture |

Each prospective gate must define its own success measures, false-alarm cost,
missed-detection risk, privacy boundary and full validation plan. A good average
score cannot override data leakage, missing lineage, unreviewed automatic action,
or a privacy violation.

## Relationship to current roadmap

- The canonical current state remains [ROADMAP.md](../../ROADMAP.md).
- The active RAG v2 answer-quality gate is unchanged and must remain frozen
  during its blinded evaluation.
- This vision elaborates the existing long-term **Phase 9 — Production
  Traceability Foundation** positioning; it is not the Phase 9 implementation
  plan.
- Future planning must start with a dedicated specification and Gate Card rather
  than treating this vision as pre-approved code scope.
