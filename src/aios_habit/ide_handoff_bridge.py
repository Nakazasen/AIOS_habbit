from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from aios_habit.case_models import EvidenceItem
from aios_habit.case_store import save_evidence
from aios_habit.rag_answer_composer import PastedStrongModelAnswer

HANDOFF_ROOT = Path("local_runs") / "ide_handoff"
RESPONSE_SCHEMA_VERSION = "ide_handoff_response_v1"
VALID_SCOPES = {"active_case_all", "selected_folder_all", "current_question_retrieval_plus_full_scope_manifest"}

@dataclass
class FullBundleRequest:
    request_id: str
    bundle_dir: Path
    manifest: dict[str, Any]
    ide_instruction: str

@dataclass
class ImportValidationResult:
    ok: bool
    final_answer: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)

def _now_id() -> str:
    return f"REQ-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"

def _privacy_mode(items: list[EvidenceItem]) -> str:
    return "local_only" if not items or any(i.privacy_level == "local_only" for i in items) else "cloud_safe"

def _source_text(item: EvidenceItem) -> str:
    text = (item.extracted_text or item.structured_summary or "").strip()
    return text or f"Metadata-only evidence: {item.title}. Content was not extracted."

def _is_metadata_only(item: EvidenceItem) -> bool:
    return not (item.extracted_text or item.structured_summary or "").strip()

def _evidence_record(item: EvidenceItem, index: int) -> dict[str, Any]:
    text = _source_text(item)
    return {"index": index, "evidence_id": item.evidence_id, "chunk_id": f"{item.evidence_id}-FULL-{index:04d}", "case_id": item.case_id, "title": item.title, "source_type": item.source_type, "source_path": item.source_path, "privacy_level": item.privacy_level, "review_status": item.review_status, "verification_status": item.verification_status, "metadata_only": _is_metadata_only(item), "warning": "metadata-only; content not extracted" if _is_metadata_only(item) else "", "text": text, "text_chars": len(text)}

def build_ide_task_instruction(request_id: str, bundle_dir: str | Path, privacy_mode: str) -> str:
    warning = ""
    if privacy_mode == "local_only":
        warning = "\nPRIVACY WARNING: This bundle contains local_only evidence. Only use an IDE/model path explicitly approved by the owner. AIOS did not call a cloud provider."
    return "\n".join([f"Read the COMPLETE full-bundle request at: {Path(bundle_dir)}", f"Request ID: {request_id}", "Read manifest.json, evidence_full.jsonl, evidence_full.md, source_manifest.json, and completeness.json before answering.", "Answer only from evidence in the bundle. Cite evidence_ids_used. List missing evidence. Do not invent facts.", "Do not claim NotebookLM parity. Do not claim P1.0 is opened.", "Write response JSON to local_runs/ide_handoff/inbox/RESP-<request_id>.json using the documented schema.", warning]).strip()

def build_full_bundle_request(case_id: str, question: str, bundle_scope: str, evidence_items: Iterable[EvidenceItem], *, owner_note: str = "", target_model_tool_name: str = "Antigravity IDE AI", max_total_text_chars: int = 2_000_000, request_id: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], str]:
    if not question.strip():
        raise ValueError("question is required")
    if bundle_scope not in VALID_SCOPES:
        raise ValueError(f"unsupported bundle_scope: {bundle_scope}")
    items = list(evidence_items)
    records = [_evidence_record(item, idx) for idx, item in enumerate(items, start=1)]
    total_chars = sum(record["text_chars"] for record in records)
    if total_chars > max_total_text_chars:
        raise ValueError("full bundle size guard triggered; export stopped without omission")
    rid = request_id or _now_id()
    privacy = _privacy_mode(items)
    source_files = sorted({item.source_path or item.title for item in items})
    extraction_formats = sorted({item.source_type for item in items})
    payload = "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
    bundle_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    instruction = build_ide_task_instruction(rid, HANDOFF_ROOT / "outbox" / rid, privacy)
    manifest = {"request_id": rid, "created_at": datetime.now().isoformat(), "case_id": case_id, "question": question, "bundle_scope": bundle_scope, "privacy_mode": privacy, "allowed_external": privacy != "local_only", "source_count": len(source_files), "evidence_item_count": len(items), "chunk_count": len(records), "total_text_chars": total_chars, "extraction_formats": extraction_formats, "source_files": source_files, "omitted_items_count": 0, "omitted_reason": "", "FULL_BUNDLE_COMPLETE": "YES", "bundle_sha256": bundle_sha, "model_instruction": instruction, "response_schema_version": RESPONSE_SCHEMA_VERSION, "owner_note": owner_note, "target_model_tool_name": target_model_tool_name, "automatic_provider_call_made": False, "notebooklm_parity_claimed": False, "p1_opened": False}
    source_manifest = {"request_id": rid, "source_files": [{"source_path": p, "basename": Path(p).name} for p in source_files], "evidence_ids": [r["evidence_id"] for r in records]}
    return manifest, records, source_manifest, instruction

def build_prompt_md(manifest: dict[str, Any]) -> str:
    schema = {"request_id": manifest["request_id"], "model_tool_name": "...", "answer_text": "...", "evidence_ids_used": ["..."], "source_files_used": ["..."], "missing_evidence": ["..."], "confidence_label": "high|medium|low", "risk_label": "low|medium|high", "privacy_acknowledged": True, "used_full_bundle": True, "notes": "..."}
    return "\n".join(["# IDE Full-Bundle Task", "", f"Question: {manifest['question']}", "", "Read every file in this bundle before answering. Use only evidence IDs from evidence_full.jsonl.", "", "Return JSON with schema:", "", "```json", json.dumps(schema, ensure_ascii=False, indent=2), "```", "", "NotebookLM parity claimed: NO. P1.0 opened: NO.", ""])

def build_evidence_markdown(records: list[dict[str, Any]]) -> str:
    lines = ["# Full Evidence Bundle", ""]
    for record in records:
        lines += [f"## {record['evidence_id']} — {record['title']}", f"- source_type: `{record['source_type']}`", f"- metadata_only: `{record['metadata_only']}`", "", "```text", record["text"], "```", ""]
    return "\n".join(lines)

def write_ide_handoff_bundle(case_id: str, question: str, bundle_scope: str, evidence_items: Iterable[EvidenceItem], *, root: str | Path = HANDOFF_ROOT, owner_note: str = "", target_model_tool_name: str = "Antigravity IDE AI", max_total_text_chars: int = 2_000_000, request_id: str | None = None) -> FullBundleRequest:
    root = Path(root)
    manifest, records, source_manifest, instruction = build_full_bundle_request(case_id, question, bundle_scope, evidence_items, owner_note=owner_note, target_model_tool_name=target_model_tool_name, max_total_text_chars=max_total_text_chars, request_id=request_id)
    bundle_dir = root / "outbox" / manifest["request_id"]
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "imported").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "question.md").write_text(f"# Question\n\n{question}\n", encoding="utf-8")
    (bundle_dir / "prompt.md").write_text(build_prompt_md(manifest), encoding="utf-8")
    (bundle_dir / "evidence_full.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\n" if records else ""), encoding="utf-8")
    (bundle_dir / "evidence_full.md").write_text(build_evidence_markdown(records), encoding="utf-8")
    (bundle_dir / "source_manifest.json").write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    completeness = {k: manifest[k] for k in ["request_id", "FULL_BUNDLE_COMPLETE", "omitted_items_count", "bundle_sha256", "evidence_item_count", "chunk_count"]}
    (bundle_dir / "completeness.json").write_text(json.dumps(completeness, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "README_FOR_IDE.md").write_text(instruction + "\n", encoding="utf-8")
    return FullBundleRequest(manifest["request_id"], bundle_dir, manifest, instruction)

def validate_handoff_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    required = ["manifest.json", "question.md", "prompt.md", "evidence_full.jsonl", "evidence_full.md", "source_manifest.json", "completeness.json", "README_FOR_IDE.md"]
    missing = [name for name in required if not (bundle_dir / name).exists()]
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8")) if not missing else {}
    return {"ok": not missing and manifest.get("FULL_BUNDLE_COMPLETE") == "YES", "missing": missing, "manifest": manifest}

def _load_manifest_for_request(request_id: str, root: str | Path) -> tuple[Path, dict[str, Any], set[str]]:
    bundle_dir = Path(root) / "outbox" / request_id
    if not (bundle_dir / "manifest.json").exists():
        raise ValueError(f"outbox request not found: {request_id}")
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    evidence_ids = set()
    for line in (bundle_dir / "evidence_full.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            evidence_ids.add(json.loads(line)["evidence_id"])
    return bundle_dir, manifest, evidence_ids

def import_ide_response(response_path: str | Path, *, root: str | Path = HANDOFF_ROOT) -> ImportValidationResult:
    response = json.loads(Path(response_path).read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    request_id = str(response.get("request_id", ""))
    if not request_id:
        return ImportValidationResult(False, False, errors=["request_id is required"], response=response)
    try:
        _bundle_dir, manifest, allowed_ids = _load_manifest_for_request(request_id, root)
    except ValueError as exc:
        return ImportValidationResult(False, False, errors=[str(exc)], response=response)
    if not str(response.get("answer_text", "")).strip():
        errors.append("answer_text is required")
    if not str(response.get("model_tool_name", "")).strip():
        errors.append("model_tool_name is required")
    if manifest.get("privacy_mode") == "local_only" and response.get("privacy_acknowledged") is not True:
        errors.append("privacy_acknowledged must be true for local_only bundle")
    if response.get("used_full_bundle") is not True:
        errors.append("used_full_bundle must be true")
    used_ids = set(response.get("evidence_ids_used") or [])
    unknown = sorted(used_ids - allowed_ids)
    if unknown:
        errors.append(f"unknown evidence_ids_used: {', '.join(unknown)}")
    final_answer = not errors and bool(used_ids)
    if not used_ids:
        warnings.append("No evidence_ids_used; import is review_required and not final")
    return ImportValidationResult(not errors, final_answer, warnings, errors, response, manifest)

def save_imported_ide_answer(case_id: str, validation: ImportValidationResult, *, root: str | Path = HANDOFF_ROOT) -> PastedStrongModelAnswer:
    if not validation.ok:
        raise ValueError("cannot save invalid IDE response: " + "; ".join(validation.errors))
    response, manifest = validation.response, validation.manifest
    evidence_ids = list(response.get("evidence_ids_used") or [])
    answer = PastedStrongModelAnswer(draft_id=f"IDE-{uuid.uuid4().hex[:12].upper()}", pack_id=manifest["request_id"], query=manifest["question"], answer_text=response["answer_text"].strip(), citation_ids=evidence_ids, evidence_ids=evidence_ids, privacy_mode=manifest.get("privacy_mode", "local_only"), allowed_external=manifest.get("allowed_external", False), insufficient_evidence=not validation.final_answer, confidence_label=response.get("confidence_label", "low"), warnings=list(validation.warnings), final_answer=validation.final_answer, model_tool_name=response["model_tool_name"].strip(), route_summary="ide_full_bundle_handoff", prompt_pack_id=manifest["request_id"], metadata={"answer_kind": "ide_handoff_strong_answer", "route_summary": "ide_full_bundle_handoff", "risk_label": response.get("risk_label", ""), "used_full_bundle": str(response.get("used_full_bundle")), "request_id": manifest["request_id"]})
    save_evidence(EvidenceItem(evidence_id=answer.draft_id, case_id=case_id, source_type="ide_handoff_strong_answer", source_path=f"ide_handoff:{manifest['request_id']}", title=f"Câu trả lời AI IDE full bundle - {answer.model_tool_name}", extracted_text=answer.answer_text, structured_summary=json.dumps(asdict(answer), ensure_ascii=False), confidence=answer.confidence_label, privacy_level=answer.privacy_mode, review_status="reviewed" if answer.final_answer else "draft", source_origin="ide_handoff", verification_status="reviewed" if answer.final_answer else "draft"))
    imported_dir = Path(root) / "imported"
    imported_dir.mkdir(parents=True, exist_ok=True)
    resp_path = Path(root) / "inbox" / f"RESP-{manifest['request_id']}.json"
    if resp_path.exists():
        shutil.copy2(resp_path, imported_dir / resp_path.name)
    return answer
