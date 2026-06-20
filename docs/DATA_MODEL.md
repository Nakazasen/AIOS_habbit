# Data Model

## EvidenceRecord
Fields: evidence_id, title, source_type, source_path, source_pointer, captured_at, classification, summary, hash, risk_level, allowed_for_export, notes.

## MemoryUnit
Fields: memory_id, category, title, statement, evidence_ids, confidence, status, created_at, updated_at, tags, export_allowed, review_notes.

Verified memory requires at least one evidence id. Export-allowed memory must be verified.

## ProjectCard
Fields: project_id, name, path, status, description, detected_signals, evidence_ids, risks, last_seen_at, tags.

## WorkflowCard
Fields: workflow_id, title, trigger, context, steps, output, failure_modes, evidence_ids, status, tags.

## DecisionPattern
Fields: decision_id, title, context, criteria, tradeoffs, preferred_action, anti_patterns, evidence_ids, status, tags.
