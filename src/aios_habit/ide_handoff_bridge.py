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
    inbox_response_path: Path | None = None
    status_path: Path | None = None

@dataclass
class ImportValidationResult:
    ok: bool
    final_answer: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)



@dataclass
class PendingIdeRequest:
    request_id: str
    created_at: str
    case_id: str
    question: str
    bundle_scope: str
    privacy_mode: str
    state: str
    response_exists: bool
    response_path: Path
    status_path: Path
    warnings: list[str] = field(default_factory=list)


def _safe_read_json(path: Path) -> tuple[dict[str, Any], str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except Exception as exc:
        return {}, str(exc)


def find_response_for_request(request_id: str, base_dir: str | Path = HANDOFF_ROOT) -> Path | None:
    if not str(request_id).strip():
        return None
    root = Path(base_dir)
    candidates = [root / "inbox" / request_id / "response.json", root / "inbox" / f"RESP-{request_id}.json"]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def list_pending_ide_requests(base_dir: str | Path = HANDOFF_ROOT) -> list[PendingIdeRequest]:
    root = Path(base_dir)
    outbox = root / "outbox"
    if not outbox.exists():
        return []
    requests: list[PendingIdeRequest] = []
    for folder in outbox.iterdir():
        if not folder.is_dir():
            continue
        manifest_path = folder / "manifest.json"
        status_path = folder / "request_status.json"
        if not manifest_path.exists():
            continue
        manifest, manifest_error = _safe_read_json(manifest_path)
        if manifest_error or not manifest.get("request_id"):
            continue
        status, status_error = _safe_read_json(status_path) if status_path.exists() else ({}, "")
        request_id = str(manifest.get("request_id", folder.name))
        response_path = find_response_for_request(request_id, root)
        warnings = []
        if status_error:
            warnings.append("request_status.json is malformed")
        requests.append(PendingIdeRequest(
            request_id=request_id,
            created_at=str(manifest.get("created_at", "")),
            case_id=str(manifest.get("case_id", "")),
            question=str(manifest.get("question", "")),
            bundle_scope=str(manifest.get("bundle_scope", "")),
            privacy_mode=str(manifest.get("privacy_mode", manifest.get("privacy_level", ""))),
            state=str(status.get("state", "created")),
            response_exists=response_path is not None,
            response_path=response_path or (root / "inbox" / request_id / "response.json"),
            status_path=status_path,
            warnings=warnings,
        ))
    return sorted(requests, key=lambda r: (r.created_at, r.request_id), reverse=True)


def get_latest_pending_ide_request(base_dir: str | Path = HANDOFF_ROOT) -> PendingIdeRequest | None:
    requests = list_pending_ide_requests(base_dir)
    return requests[0] if requests else None


def summarize_pending_request(request: PendingIdeRequest) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "created_at": request.created_at,
        "case_id": request.case_id,
        "question": request.question,
        "bundle_scope": request.bundle_scope,
        "privacy_mode": request.privacy_mode,
        "state": request.state,
        "response_json_exists": request.response_exists,
        "next_action": "Nhập phản hồi và kiểm tra bằng chứng" if request.response_exists else "Dán câu trả lời Markdown từ Antigravity hoặc chờ response.json",
        "warnings": list(request.warnings),
    }


def convert_markdown_answer_to_ide_response(
    request_id: str,
    markdown_text: str,
    cited_evidence_ids: list[str] | None = None,
    confidence: str = "medium",
    limitations: list[str] | None = None,
    recommended_next_actions: list[str] | None = None,
    *,
    privacy_acknowledged: bool = False,
    used_full_bundle: bool = False,
    model_tool_name: str = "Antigravity IDE AI",
    unsupported_claims: list[str] | None = None,
) -> dict[str, Any]:
    if not str(request_id).strip():
        raise ValueError("request_id is required")
    ids = list(cited_evidence_ids or [])
    lims = list(limitations or [])
    if not ids and "No explicit evidence IDs were provided." not in lims:
        lims.append("No explicit evidence IDs were provided.")
    return {
        "request_id": str(request_id).strip(),
        "answer_markdown": str(markdown_text or ""),
        "cited_evidence_ids": ids,
        "evidence_ids_used": ids,
        "limitations": lims,
        "confidence": confidence,
        "confidence_label": confidence,
        "privacy_acknowledged": privacy_acknowledged is True,
        "used_full_bundle": used_full_bundle is True,
        "unsupported_claims": list(unsupported_claims or []),
        "recommended_next_actions": list(recommended_next_actions or []),
        "model_tool_name": model_tool_name,
    }


def import_markdown_ide_response(
    request_id: str,
    markdown_text: str,
    *,
    root: str | Path = HANDOFF_ROOT,
    cited_evidence_ids: list[str] | None = None,
    confidence: str = "medium",
    limitations: list[str] | None = None,
    recommended_next_actions: list[str] | None = None,
    privacy_acknowledged: bool = False,
    used_full_bundle: bool = False,
    model_tool_name: str = "Antigravity IDE AI",
) -> ImportValidationResult:
    response = convert_markdown_answer_to_ide_response(
        request_id,
        markdown_text,
        cited_evidence_ids=cited_evidence_ids,
        confidence=confidence,
        limitations=limitations,
        recommended_next_actions=recommended_next_actions,
        privacy_acknowledged=privacy_acknowledged,
        used_full_bundle=used_full_bundle,
        model_tool_name=model_tool_name,
    )
    temp_dir = Path(root) / "inbox" / request_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    draft_path = temp_dir / "response_draft_from_markdown.json"
    draft_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return import_ide_response(draft_path, root=root)

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

def build_ide_task_instruction(request_id: str, bundle_dir: str | Path, privacy_mode: str, inbox_response_path: str | Path | None = None) -> str:
    warning = ""
    if privacy_mode == "local_only":
        warning = "\nPRIVACY WARNING: This bundle contains local_only evidence. Only use an IDE/model path explicitly approved by the owner. AIOS did not call a cloud provider."
    response_path = Path(inbox_response_path) if inbox_response_path else HANDOFF_ROOT / "inbox" / request_id / "response.json"
    return "\n".join([f"Read the COMPLETE full-bundle request at: {Path(bundle_dir)}", f"Request ID: {request_id}", "Read evidence_bundle.json first, then manifest.json, evidence_full.jsonl, evidence_full.md, source_manifest.json, and completeness.json before answering.", "Answer only from evidence in the bundle. Cite evidence_ids_used/cited_evidence_ids. List missing evidence. Do not invent facts.", "Do not claim NotebookLM parity. Do not claim P1.0 is opened.", f"Write response JSON to: {response_path}", "Required response fields: request_id, answer_markdown, cited_evidence_ids, limitations, confidence, privacy_acknowledged, used_full_bundle, unsupported_claims, recommended_next_actions.", warning]).strip()

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
    instruction = build_ide_task_instruction(rid, HANDOFF_ROOT / "outbox" / rid, privacy, HANDOFF_ROOT / "inbox" / rid / "response.json")
    manifest = {"request_id": rid, "created_at": datetime.now().isoformat(), "case_id": case_id, "question": question, "bundle_scope": bundle_scope, "privacy_mode": privacy, "privacy_level": privacy, "local_only": privacy == "local_only", "allowed_external": privacy != "local_only", "source_count": len(source_files), "evidence_item_count": len(items), "chunk_count": len(records), "total_text_chars": total_chars, "extraction_formats": extraction_formats, "source_files": source_files, "allowed_source_ids": [r["evidence_id"] for r in records], "evidence_refs": [{"evidence_id": r["evidence_id"], "title": r["title"], "source_type": r["source_type"], "privacy_level": r["privacy_level"]} for r in records], "expected_response_schema": RESPONSE_SCHEMA_VERSION, "omitted_items_count": 0, "omitted_reason": "", "FULL_BUNDLE_COMPLETE": "YES", "bundle_sha256": bundle_sha, "model_instruction": instruction, "response_schema_version": RESPONSE_SCHEMA_VERSION, "owner_note": owner_note, "target_model_tool_name": target_model_tool_name, "automatic_provider_call_made": False, "notebooklm_parity_claimed": False, "p1_opened": False}
    source_manifest = {"request_id": rid, "source_files": [{"source_path": p, "basename": Path(p).name} for p in source_files], "evidence_ids": [r["evidence_id"] for r in records]}
    return manifest, records, source_manifest, instruction

def build_prompt_md(manifest: dict[str, Any]) -> str:
    inbox_path = HANDOFF_ROOT / "inbox" / manifest["request_id"] / "response.json"
    schema = {"request_id": manifest["request_id"], "answer_markdown": "...", "cited_evidence_ids": ["..."], "evidence_ids_used": ["..."], "limitations": ["..."], "confidence": "high|medium|low", "privacy_acknowledged": True, "used_full_bundle": True, "unsupported_claims": [], "recommended_next_actions": ["..."], "model_tool_name": "Antigravity IDE AI"}
    return "\n".join(["# Antigravity Local Handoff Task", "", f"Question: {manifest['question']}", "", "1. Read every file in this bundle. Start with evidence_bundle.json in this folder.", "2. Use only evidence in this bundle. Do not invent sources or use external web unless explicitly allowed.", "3. Preserve privacy. If local_only is true, do not send raw content to unapproved cloud/provider paths.", "4. If evidence is insufficient, say so in limitations and unsupported_claims.", "5. Save exactly one JSON file to the expected inbox path below.", "", f"Expected inbox response path: `{inbox_path}`", "", "FORMAT REQUIREMENT: Use inline citations and cite only IDs from allowed_source_ids/evidence_refs.", "", "Return JSON with schema:", "", "```json", json.dumps(schema, ensure_ascii=False, indent=2), "```", "", "NotebookLM parity claimed: NO. P1.0 opened: NO.", ""])

def build_evidence_markdown(records: list[dict[str, Any]]) -> str:
    lines = ["# Full Evidence Bundle", ""]
    for record in records:
        lines += [f"## {record['evidence_id']} - {record['title']}", f"- source_type: `{record['source_type']}`", f"- metadata_only: `{record['metadata_only']}`", "", "```text", record["text"], "```", ""]
    return "\n".join(lines)

def write_ide_handoff_bundle(case_id: str, question: str, bundle_scope: str, evidence_items: Iterable[EvidenceItem], *, root: str | Path = HANDOFF_ROOT, owner_note: str = "", target_model_tool_name: str = "Antigravity IDE AI", max_total_text_chars: int = 2_000_000, request_id: str | None = None) -> FullBundleRequest:
    root = Path(root)
    manifest, records, source_manifest, instruction = build_full_bundle_request(case_id, question, bundle_scope, evidence_items, owner_note=owner_note, target_model_tool_name=target_model_tool_name, max_total_text_chars=max_total_text_chars, request_id=request_id)
    bundle_dir = root / "outbox" / manifest["request_id"]
    bundle_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir = root / "inbox" / manifest["request_id"]
    processed_dir = root / "processed" / manifest["request_id"]
    inbox_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "evidence_bundle.json").write_text(json.dumps({k: manifest[k] for k in ["case_id", "request_id", "question", "evidence_refs", "allowed_source_ids", "privacy_level", "local_only", "created_at", "expected_response_schema"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "question.md").write_text(f"# Question\n\n{question}\n", encoding="utf-8")
    prompt_md = build_prompt_md(manifest)
    (bundle_dir / "prompt.md").write_text(prompt_md, encoding="utf-8")
    (bundle_dir / "prompt_for_antigravity.md").write_text(prompt_md, encoding="utf-8")
    (bundle_dir / "evidence_full.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\n" if records else ""), encoding="utf-8")
    (bundle_dir / "evidence_full.md").write_text(build_evidence_markdown(records), encoding="utf-8")
    (bundle_dir / "source_manifest.json").write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    completeness = {k: manifest[k] for k in ["request_id", "FULL_BUNDLE_COMPLETE", "omitted_items_count", "bundle_sha256", "evidence_item_count", "chunk_count"]}
    (bundle_dir / "completeness.json").write_text(json.dumps(completeness, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "README_FOR_IDE.md").write_text(instruction + "\n", encoding="utf-8")
    status = {"request_id": manifest["request_id"], "state": "created", "created_at": manifest["created_at"], "outbox_dir": str(bundle_dir), "expected_inbox_response_path": str(inbox_dir / "response.json"), "imported_at": "", "error": ""}
    status_path = bundle_dir / "request_status.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return FullBundleRequest(manifest["request_id"], bundle_dir, manifest, instruction, inbox_dir / "response.json", status_path)

def validate_handoff_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    required = ["manifest.json", "evidence_bundle.json", "question.md", "prompt.md", "prompt_for_antigravity.md", "evidence_full.jsonl", "evidence_full.md", "source_manifest.json", "completeness.json", "README_FOR_IDE.md", "request_status.json"]
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
    try:
        response = json.loads(Path(response_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ImportValidationResult(False, False, errors=[f"response file not found: {response_path}"])
    except json.JSONDecodeError as exc:
        return ImportValidationResult(False, False, errors=[f"malformed JSON response: {exc}"])
    errors: list[str] = []
    warnings: list[str] = []
    request_id = str(response.get("request_id", ""))
    if not request_id:
        return ImportValidationResult(False, False, errors=["request_id is required"], response=response)
    try:
        _bundle_dir, manifest, allowed_ids = _load_manifest_for_request(request_id, root)
    except ValueError as exc:
        return ImportValidationResult(False, False, errors=[str(exc)], response=response)
    answer_text = str(response.get("answer_text") or response.get("answer_markdown") or "").strip()
    if not answer_text:
        errors.append("answer_markdown is required")
    if not str(response.get("model_tool_name", "")).strip():
        errors.append("model_tool_name is required")
    if manifest.get("privacy_mode") == "local_only" and response.get("privacy_acknowledged") is not True:
        errors.append("privacy_acknowledged must be true for local_only bundle")
    if response.get("used_full_bundle") is not True:
        errors.append("used_full_bundle must be true")
    used_ids = set(response.get("evidence_ids_used") or response.get("cited_evidence_ids") or [])
    unknown = sorted(used_ids - allowed_ids)
    if unknown:
        errors.append(f"unknown evidence_ids_used: {', '.join(unknown)}")
    final_answer = not errors and bool(used_ids)
    if not used_ids:
        warnings.append("No evidence_ids_used; import is review_required and not final")
    if "answer_text" not in response and "answer_markdown" in response:
        response["answer_text"] = response["answer_markdown"]
    if "evidence_ids_used" not in response and "cited_evidence_ids" in response:
        response["evidence_ids_used"] = response["cited_evidence_ids"]
    if "confidence_label" not in response and "confidence" in response:
        response["confidence_label"] = response["confidence"]
    return ImportValidationResult(not errors, final_answer, warnings, errors, response, manifest)

def save_imported_ide_answer(case_id: str, validation: ImportValidationResult, *, root: str | Path = HANDOFF_ROOT) -> PastedStrongModelAnswer:
    if not validation.ok:
        raise ValueError("cannot save invalid IDE response: " + "; ".join(validation.errors))
    response, manifest = validation.response, validation.manifest
    evidence_ids = list(response.get("evidence_ids_used") or [])
    answer = PastedStrongModelAnswer(draft_id=f"IDE-{uuid.uuid4().hex[:12].upper()}", pack_id=manifest["request_id"], query=manifest["question"], answer_text=response["answer_text"].strip(), citation_ids=evidence_ids, evidence_ids=evidence_ids, privacy_mode=manifest.get("privacy_mode", "local_only"), allowed_external=manifest.get("allowed_external", False), insufficient_evidence=not validation.final_answer, confidence_label=response.get("confidence_label", "low"), warnings=list(validation.warnings), final_answer=validation.final_answer, model_tool_name=response["model_tool_name"].strip(), route_summary="ide_full_bundle_handoff", prompt_pack_id=manifest["request_id"], metadata={"answer_kind": "ide_handoff_strong_answer", "route_summary": "ide_full_bundle_handoff", "risk_label": response.get("risk_label", ""), "used_full_bundle": str(response.get("used_full_bundle")), "request_id": manifest["request_id"]})
    save_evidence(EvidenceItem(evidence_id=answer.draft_id, case_id=case_id, source_type="ide_handoff_strong_answer", source_path=f"ide_handoff:{manifest['request_id']}", title=f"Câu trả lời AI IDE full bundle - {answer.model_tool_name}", extracted_text=answer.answer_text, structured_summary=json.dumps(asdict(answer), ensure_ascii=False), confidence=answer.confidence_label, privacy_level=answer.privacy_mode, review_status="reviewed" if answer.final_answer else "draft", source_origin="ide_handoff", verification_status="reviewed" if answer.final_answer else "draft"))
    processed_dir = Path(root) / "processed" / manifest["request_id"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    resp_path = Path(root) / "inbox" / manifest["request_id"] / "response.json"
    legacy_resp_path = Path(root) / "inbox" / f"RESP-{manifest['request_id']}.json"
    if resp_path.exists():
        shutil.copy2(resp_path, processed_dir / "response.json")
    elif legacy_resp_path.exists():
        shutil.copy2(legacy_resp_path, processed_dir / "response.json")
    import_result = {"request_id": manifest["request_id"], "ok": validation.ok, "final_answer": validation.final_answer, "warnings": validation.warnings, "errors": validation.errors, "saved_answer_id": answer.draft_id, "imported_at": datetime.now().isoformat()}
    (processed_dir / "import_result.json").write_text(json.dumps(import_result, ensure_ascii=False, indent=2), encoding="utf-8")
    status_path = Path(root) / "outbox" / manifest["request_id"] / "request_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status.update({"state": "imported", "imported_at": import_result["imported_at"], "error": ""})
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return answer

def pending_handoff_request_ids(*, root: str | Path = HANDOFF_ROOT) -> list[str]:
    return [req.request_id for req in list_pending_ide_requests(root)]

def expected_inbox_response_path(request_id: str, *, root: str | Path = HANDOFF_ROOT) -> Path:
    return Path(root) / "inbox" / request_id / "response.json"

def import_pending_ide_response(request_id: str, *, root: str | Path = HANDOFF_ROOT) -> ImportValidationResult:
    path = find_response_for_request(request_id, root)
    if not path:
        expected = expected_inbox_response_path(request_id, root=root)
        return ImportValidationResult(False, False, errors=[f"response file not found: {expected}"])
    return import_ide_response(path, root=root)

def vietnamese_next_step_instruction(request_id: str, outbox_dir: str | Path, inbox_response_path: str | Path, privacy_mode: str) -> str:
    warning = " Dữ liệu local_only: chỉ dùng Antigravity/model đã được owner cho phép." if privacy_mode == "local_only" else ""
    return f"Mở Antigravity, đọc gói tại {outbox_dir}, làm theo prompt_for_antigravity.md, rồi lưu response.json vào {inbox_response_path}. Quay lại màn hình này và bấm Kiểm tra phản hồi từ Antigravity.{warning}"
def block_cloud_provider_for_local_only(manifest: dict[str, Any]) -> tuple[bool, str]:
    if manifest.get("local_only") or manifest.get("privacy_mode") == "local_only":
        return True, "Bị chặn: bundle local_only không được gửi cloud/provider tự động."
    return False, "Cho phép nếu provider đã được owner phê duyệt."
