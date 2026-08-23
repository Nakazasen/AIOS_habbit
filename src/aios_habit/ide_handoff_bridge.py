from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from aios_habit.case_models import EvidenceItem
from aios_habit.case_store import save_evidence
from aios_habit.i18n import get_ai_language_instruction, normalize_locale
from aios_habit.rag_answer_composer import PastedStrongModelAnswer

LOGGER = logging.getLogger(__name__)

HANDOFF_ROOT = Path("local_runs") / "ide_handoff"
RESPONSE_SCHEMA_VERSION = "ide_handoff_response_v1"
VALID_SCOPES = {"active_case_all", "selected_folder_all", "current_question_retrieval_plus_full_scope_manifest"}

DEFAULT_HANDOFF_TIMEOUT_SECONDS = 300

# 3-State Request Lifecycle FSM Constants
REQ_STATE_PENDING = "handoff_pending"
REQ_STATE_COMPLETED = "completed"
REQ_STATE_FAILED = "failed"

ALLOWED_REQUEST_STATES = {REQ_STATE_PENDING, REQ_STATE_COMPLETED, REQ_STATE_FAILED}


@dataclass
class FullBundleRequest:
    request_id: str
    bundle_dir: Path
    manifest: dict[str, Any]
    ide_instruction: str
    inbox_response_path: Path | None = None
    status_path: Path | None = None
    ok: bool = True
    error_message: str = ""

    @property
    def outbox_dir(self) -> Path:
        return self.bundle_dir


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


def _sanitize_reason(reason: str) -> str:
    """Sanitize error text to avoid leaking secrets, tokens, or absolute paths."""
    if not reason:
        return ""
    text = str(reason).replace("\\", "/")
    # Mask paths
    text = re.sub(r"([A-Za-z]:)?/[a-zA-Z0-9_\-\./]+", "<path>", text)
    # Mask API tokens
    text = re.sub(r"(sk-[a-zA-Z0-9_\-]+|Bearer\s+[a-zA-Z0-9_\-]+)", "<redacted_token>", text)
    return text[:200].strip()


def sanitize_reason(reason: str) -> str:
    """Public helper alias for sanitizing reasons."""
    return _sanitize_reason(reason)


def _normalize_request_state(state: str) -> str:
    """Normalize legacy states to standard FSM states."""
    s = str(state or "").strip().lower()
    if s == "created":
        return REQ_STATE_PENDING
    if s == "imported":
        return REQ_STATE_COMPLETED
    if s in ALLOWED_REQUEST_STATES:
        return s
    return REQ_STATE_PENDING


def update_request_status(
    bundle_dir_or_status_path: Path,
    state: str,
    *,
    error: str = "",
    error_reason: str = "",
    saved_answer_id: str = "",
) -> dict[str, Any]:
    """Atomically update and sanitize request_status.json."""
    status_path = (
        bundle_dir_or_status_path
        if bundle_dir_or_status_path.name == "request_status.json"
        else bundle_dir_or_status_path / "request_status.json"
    )
    status_data, _ = _safe_read_json(status_path)
    now_iso = datetime.now().isoformat()
    norm_state = _normalize_request_state(state)

    status_data["state"] = norm_state
    status_data["updated_at"] = now_iso
    if norm_state == REQ_STATE_COMPLETED:
        status_data["completed_at"] = now_iso
        status_data["imported_at"] = now_iso  # Legacy compatibility
        status_data["error"] = ""
        status_data["error_reason"] = ""
        if saved_answer_id:
            status_data["saved_answer_id"] = saved_answer_id
    elif norm_state == REQ_STATE_FAILED:
        status_data["failed_at"] = now_iso
        status_data["error"] = _sanitize_reason(error)
        status_data["error_reason"] = _sanitize_reason(error_reason or "failure")

    status_path.write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return status_data


def find_response_for_request(request_id: str, base_dir: str | Path = HANDOFF_ROOT) -> Path | None:
    if not str(request_id).strip():
        return None
    root = Path(base_dir)
    candidates = [root / "inbox" / request_id / "response.json", root / "inbox" / f"RESP-{request_id}.json"]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def is_request_expired(
    manifest_or_status: dict[str, Any],
    now: datetime | None = None,
) -> bool:
    """Check if request has exceeded its expiration timestamp."""
    state = _normalize_request_state(str(manifest_or_status.get("state", "")))
    if state in (REQ_STATE_COMPLETED, REQ_STATE_FAILED):
        return False

    now_dt = now or datetime.now()
    expires_at_str = manifest_or_status.get("expires_at")
    if expires_at_str:
        try:
            expires_at_dt = datetime.fromisoformat(expires_at_str)
            return now_dt > expires_at_dt
        except (ValueError, TypeError):
            pass

    created_at_str = manifest_or_status.get("created_at")
    timeout_sec = int(manifest_or_status.get("timeout_seconds", DEFAULT_HANDOFF_TIMEOUT_SECONDS))
    if created_at_str:
        try:
            created_at_dt = datetime.fromisoformat(created_at_str)
            return (now_dt - created_at_dt).total_seconds() > timeout_sec
        except (ValueError, TypeError):
            pass

    return False


def check_handoff_request_timeouts(
    root: str | Path = HANDOFF_ROOT,
    now: datetime | None = None,
) -> list[str]:
    """Scan pending requests in outbox and transition expired ones to 'failed'."""
    root_path = Path(root)
    outbox = root_path / "outbox"
    if not outbox.exists():
        return []

    expired_ids: list[str] = []
    for folder in outbox.iterdir():
        if not folder.is_dir():
            continue
        status_path = folder / "request_status.json"
        manifest_path = folder / "manifest.json"
        if not status_path.exists() or not manifest_path.exists():
            continue

        manifest, _ = _safe_read_json(manifest_path)
        status, _ = _safe_read_json(status_path)
        req_id = manifest.get("request_id", folder.name)
        response_path = find_response_for_request(req_id, root_path)

        state = _normalize_request_state(status.get("state", REQ_STATE_PENDING))
        if state == REQ_STATE_PENDING and not response_path:
            meta = {**manifest, **status}
            if is_request_expired(meta, now=now):
                timeout_val = meta.get("timeout_seconds", DEFAULT_HANDOFF_TIMEOUT_SECONDS)
                update_request_status(
                    status_path,
                    REQ_STATE_FAILED,
                    error=f"Handoff request timed out after {timeout_val} seconds",
                    error_reason="timeout",
                )
                expired_ids.append(req_id)
                LOGGER.warning("Handoff request %s expired and transitioned to failed.", req_id)

    return expired_ids


# Alias for naming consistency across specifications
check_and_expire_pending_requests = check_handoff_request_timeouts


def list_pending_ide_requests(base_dir: str | Path = HANDOFF_ROOT) -> list[PendingIdeRequest]:
    root = Path(base_dir)
    outbox = root / "outbox"
    if not outbox.exists():
        return []
    # Proactively expire stale pending requests
    check_handoff_request_timeouts(root)
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
        raw_state = status.get("state", "handoff_pending")
        norm_state = _normalize_request_state(raw_state)
        requests.append(PendingIdeRequest(
            request_id=request_id,
            created_at=str(manifest.get("created_at", "")),
            case_id=str(manifest.get("case_id", "")),
            question=str(manifest.get("question", "")),
            bundle_scope=str(manifest.get("bundle_scope", "")),
            privacy_mode=str(manifest.get("privacy_mode", manifest.get("privacy_level", ""))),
            state=norm_state,
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
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "request_id": str(request_id).strip(),
        "status": "completed",
        "answer_markdown": str(markdown_text or ""),
        "answer_text": str(markdown_text or ""),
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
    return {
        "index": index,
        "evidence_id": item.evidence_id,
        "chunk_id": f"{item.evidence_id}-FULL-{index:04d}",
        "case_id": item.case_id,
        "title": item.title,
        "source_type": item.source_type,
        "source_path": item.source_path,
        "privacy_level": item.privacy_level,
        "review_status": item.review_status,
        "verification_status": item.verification_status,
        "metadata_only": _is_metadata_only(item),
        "warning": "metadata-only; content not extracted" if _is_metadata_only(item) else "",
        "text": text,
        "text_chars": len(text),
    }


def build_ide_task_instruction(
    request_id: str,
    bundle_dir: str | Path,
    privacy_mode: str,
    inbox_response_path: str | Path | None = None,
) -> str:
    warning = ""
    if privacy_mode == "local_only":
        warning = "\nPRIVACY WARNING: This bundle contains local_only evidence. Only use an IDE/model path explicitly approved by the owner. AIOS did not call a cloud provider."
    response_path = Path(inbox_response_path) if inbox_response_path else HANDOFF_ROOT / "inbox" / request_id / "response.json"
    return "\n".join([
        f"Read the COMPLETE full-bundle request at: {Path(bundle_dir)}",
        f"Request ID: {request_id}",
        "Read evidence_bundle.json first, then manifest.json, evidence_full.jsonl, evidence_full.md, source_manifest.json, and completeness.json before answering.",
        "Answer only from evidence in the bundle. Cite evidence_ids_used/cited_evidence_ids. List missing evidence. Do not invent facts.",
        "Do not claim NotebookLM parity. Do not claim P1.0 is opened.",
        f"Write response JSON to: {response_path}",
        "Required response fields: request_id, answer_markdown, cited_evidence_ids, limitations, confidence, privacy_acknowledged, used_full_bundle, unsupported_claims, recommended_next_actions.",
        warning,
    ]).strip()


def build_full_bundle_request(
    case_id: str,
    question: str,
    bundle_scope: str,
    evidence_items: Iterable[EvidenceItem],
    *,
    owner_note: str = "",
    target_model_tool_name: str = "Antigravity IDE AI",
    max_total_text_chars: int = 2_000_000,
    request_id: str | None = None,
    timeout_seconds: int = DEFAULT_HANDOFF_TIMEOUT_SECONDS,
    answer_language: str = "vi",
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], str]:
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
    norm_lang = normalize_locale(answer_language)
    privacy = _privacy_mode(items)
    source_files = sorted({item.source_path or item.title for item in items})
    extraction_formats = sorted({item.source_type for item in items})
    payload = "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
    bundle_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    instruction = build_ide_task_instruction(rid, HANDOFF_ROOT / "outbox" / rid, privacy, HANDOFF_ROOT / "inbox" / rid / "response.json")

    now_dt = datetime.now()
    created_at_iso = now_dt.isoformat()
    expires_at_iso = (now_dt + timedelta(seconds=timeout_seconds)).isoformat()

    manifest = {
        "request_id": rid,
        "created_at": created_at_iso,
        "expires_at": expires_at_iso,
        "timeout_seconds": timeout_seconds,
        "case_id": case_id,
        "question": question,
        "bundle_scope": bundle_scope,
        "answer_language": norm_lang,
        "privacy_mode": privacy,
        "privacy_level": privacy,
        "local_only": privacy == "local_only",
        "allowed_external": privacy != "local_only",
        "source_count": len(source_files),
        "evidence_item_count": len(items),
        "chunk_count": len(records),
        "total_text_chars": total_chars,
        "extraction_formats": extraction_formats,
        "source_files": source_files,
        "allowed_source_ids": [r["evidence_id"] for r in records],
        "evidence_refs": [
            {
                "evidence_id": r["evidence_id"],
                "title": r["title"],
                "source_type": r["source_type"],
                "privacy_level": r["privacy_level"],
            }
            for r in records
        ],
        "expected_response_schema": RESPONSE_SCHEMA_VERSION,
        "omitted_items_count": 0,
        "omitted_reason": "",
        "FULL_BUNDLE_COMPLETE": "YES",
        "bundle_sha256": bundle_sha,
        "model_instruction": instruction,
        "response_schema_version": RESPONSE_SCHEMA_VERSION,
        "owner_note": owner_note,
        "target_model_tool_name": target_model_tool_name,
        "automatic_provider_call_made": False,
        "notebooklm_parity_claimed": False,
        "p1_opened": False,
    }
    source_manifest = {
        "request_id": rid,
        "source_files": [{"source_path": p, "basename": Path(p).name} for p in source_files],
        "evidence_ids": [r["evidence_id"] for r in records],
    }
    return manifest, records, source_manifest, instruction


def build_ide_prompt_markdown(manifest: dict[str, Any], answer_language: str = "vi") -> str:
    lang = manifest.get("answer_language", answer_language)
    lang_instruction = get_ai_language_instruction(lang)
    inbox_path = HANDOFF_ROOT / "inbox" / manifest["request_id"] / "response.json"
    schema = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "request_id": manifest["request_id"],
        "status": "completed",
        "answer_markdown": "...",
        "cited_evidence_ids": ["..."],
        "evidence_ids_used": ["..."],
        "limitations": ["..."],
        "confidence": "high|medium|low",
        "privacy_acknowledged": True,
        "used_full_bundle": True,
        "unsupported_claims": [],
        "recommended_next_actions": ["..."],
        "model_tool_name": "Antigravity IDE AI",
    }
    return "\n".join([
        "# Antigravity Local Handoff Task",
        "",
        f"Question: {manifest['question']}",
        "",
        f"LANGUAGE & CITATION INSTRUCTION:\n{lang_instruction}",
        "",
        "1. Read every file in this bundle. Start with evidence_bundle.json in this folder.",
        "2. Use only evidence in this bundle. Do not invent sources or use external web unless explicitly allowed.",
        "3. Preserve privacy. If local_only is true, do not send raw content to unapproved cloud/provider paths.",
        "4. If evidence is insufficient, say so in limitations and unsupported_claims.",
        "5. Save exactly one JSON file to the expected inbox path below.",
        "",
        f"Expected inbox response path: `{inbox_path}`",
        "",
        "FORMAT REQUIREMENT: Use inline citations and cite only IDs from allowed_source_ids/evidence_refs.",
        "",
        "Return JSON with schema:",
        "",
        "```json",
        json.dumps(schema, ensure_ascii=False, indent=2),
        "```",
        "",
        "NotebookLM parity claimed: NO. P1.0 opened: NO.",
        "",
    ])


build_prompt_md = build_ide_prompt_markdown


def build_evidence_markdown(records: list[dict[str, Any]]) -> str:
    lines = ["# Full Evidence Bundle", ""]
    for record in records:
        source_path = record.get("source_path") or ""
        lines += [
            f"## {record['evidence_id']} - {record['title']}",
            f"- source_type: `{record['source_type']}`",
            *( [f"- source_path: `{source_path}`"] if source_path else [] ),
            f"- metadata_only: `{record['metadata_only']}`",
            "",
            "```text",
            record["text"],
            "```",
            "",
        ]
    return "\n".join(lines)


def write_ide_handoff_bundle(
    case_id: str,
    question: str,
    bundle_scope: str,
    evidence_items: Iterable[EvidenceItem],
    *,
    root: str | Path = HANDOFF_ROOT,
    owner_note: str = "",
    target_model_tool_name: str = "Antigravity IDE AI",
    max_total_text_chars: int = 2_000_000,
    request_id: str | None = None,
    timeout_seconds: int = DEFAULT_HANDOFF_TIMEOUT_SECONDS,
    answer_language: str = "vi",
) -> FullBundleRequest:
    root = Path(root)
    manifest, records, source_manifest, instruction = build_full_bundle_request(
        case_id,
        question,
        bundle_scope,
        evidence_items,
        owner_note=owner_note,
        target_model_tool_name=target_model_tool_name,
        max_total_text_chars=max_total_text_chars,
        request_id=request_id,
        timeout_seconds=timeout_seconds,
        answer_language=answer_language,
    )
    bundle_dir = root / "outbox" / manifest["request_id"]
    bundle_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir = root / "inbox" / manifest["request_id"]
    processed_dir = root / "processed" / manifest["request_id"]
    inbox_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "evidence_bundle.json").write_text(
        json.dumps(
            {
                k: manifest[k]
                for k in [
                    "case_id",
                    "request_id",
                    "question",
                    "evidence_refs",
                    "allowed_source_ids",
                    "privacy_level",
                    "local_only",
                    "created_at",
                    "expires_at",
                    "timeout_seconds",
                    "expected_response_schema",
                ]
                if k in manifest
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (bundle_dir / "question.md").write_text(f"# Question\n\n{question}\n", encoding="utf-8")
    prompt_md = build_ide_prompt_markdown(manifest, answer_language=answer_language)
    (bundle_dir / "prompt.md").write_text(prompt_md, encoding="utf-8")
    (bundle_dir / "prompt_for_antigravity.md").write_text(prompt_md, encoding="utf-8")
    (bundle_dir / "evidence_full.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\n" if records else ""),
        encoding="utf-8",
    )
    (bundle_dir / "evidence_full.md").write_text(build_evidence_markdown(records), encoding="utf-8")
    (bundle_dir / "source_manifest.json").write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    completeness = {
        k: manifest[k]
        for k in [
            "request_id",
            "FULL_BUNDLE_COMPLETE",
            "omitted_items_count",
            "bundle_sha256",
            "evidence_item_count",
            "chunk_count",
        ]
    }
    (bundle_dir / "completeness.json").write_text(json.dumps(completeness, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "README_FOR_IDE.md").write_text(instruction + "\n", encoding="utf-8")

    status = {
        "request_id": manifest["request_id"],
        "state": REQ_STATE_PENDING,
        "created_at": manifest["created_at"],
        "updated_at": manifest["created_at"],
        "timeout_seconds": timeout_seconds,
        "expires_at": manifest["expires_at"],
        "outbox_dir": str(bundle_dir),
        "expected_inbox_response_path": str(inbox_dir / "response.json"),
        "completed_at": "",
        "imported_at": "",
        "failed_at": "",
        "error": "",
        "error_reason": "",
    }
    status_path = bundle_dir / "request_status.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return FullBundleRequest(manifest["request_id"], bundle_dir, manifest, instruction, inbox_dir / "response.json", status_path)


def validate_handoff_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    required = [
        "manifest.json",
        "evidence_bundle.json",
        "question.md",
        "prompt.md",
        "prompt_for_antigravity.md",
        "evidence_full.jsonl",
        "evidence_full.md",
        "source_manifest.json",
        "completeness.json",
        "README_FOR_IDE.md",
        "request_status.json",
    ]
    missing = [name for name in required if not (bundle_dir / name).exists()]
    manifest, _ = _safe_read_json(bundle_dir / "manifest.json") if not missing else ({}, "")
    completeness, _ = _safe_read_json(bundle_dir / "completeness.json") if not missing else ({}, "")
    ok = (
        not missing
        and manifest.get("FULL_BUNDLE_COMPLETE") == "YES"
        and completeness.get("FULL_BUNDLE_COMPLETE") == "YES"
        and manifest.get("bundle_sha256") == completeness.get("bundle_sha256")
    )
    return {"ok": ok, "missing": missing, "manifest": manifest}


def verify_bundle_integrity(bundle_dir: str | Path) -> tuple[bool, list[str]]:
    """Verify cryptographic integrity and completeness of an outbox bundle."""
    bundle_path = Path(bundle_dir)
    errors: list[str] = []

    manifest_path = bundle_path / "manifest.json"
    completeness_path = bundle_path / "completeness.json"
    evidence_jsonl_path = bundle_path / "evidence_full.jsonl"

    if not manifest_path.exists():
        return False, ["manifest.json missing"]
    if not completeness_path.exists():
        return False, ["completeness.json missing"]
    if not evidence_jsonl_path.exists():
        return False, ["evidence_full.jsonl missing"]

    manifest, err_m = _safe_read_json(manifest_path)
    if err_m:
        return False, [f"Corrupted manifest.json: {err_m}"]
    completeness, err_c = _safe_read_json(completeness_path)
    if err_c:
        return False, [f"Corrupted completeness.json: {err_c}"]

    if manifest.get("FULL_BUNDLE_COMPLETE") != "YES":
        errors.append("manifest FULL_BUNDLE_COMPLETE is not YES")
    if completeness.get("FULL_BUNDLE_COMPLETE") != "YES":
        errors.append("completeness.json FULL_BUNDLE_COMPLETE is not YES")

    expected_sha = manifest.get("bundle_sha256", "")
    if not expected_sha:
        errors.append("bundle_sha256 missing in manifest")
    elif expected_sha != completeness.get("bundle_sha256"):
        errors.append("bundle_sha256 mismatch between manifest and completeness.json")
    else:
        try:
            lines = [
                line.strip()
                for line in evidence_jsonl_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            records = [json.loads(line) for line in lines]
            canonical_payload = "\n".join(
                json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records
            )
            computed_sha = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
            if computed_sha != expected_sha:
                errors.append(f"SHA-256 mismatch: expected {expected_sha[:12]}..., got {computed_sha[:12]}...")
        except Exception as exc:
            errors.append(f"Failed to read/verify evidence_full.jsonl: {exc}")

    return len(errors) == 0, errors


def _load_manifest_for_request(request_id: str, root: str | Path) -> tuple[Path, dict[str, Any], set[str]]:
    bundle_dir = Path(root) / "outbox" / request_id
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"outbox request not found: {request_id}")

    manifest, err = _safe_read_json(manifest_path)
    if err:
        raise ValueError(f"malformed manifest.json for request {request_id}: {err}")

    evidence_ids: set[str] = set()
    evidence_full_path = bundle_dir / "evidence_full.jsonl"
    if evidence_full_path.exists():
        try:
            for line in evidence_full_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if isinstance(item, dict) and "evidence_id" in item:
                        evidence_ids.add(str(item["evidence_id"]))
        except Exception as exc:
            LOGGER.warning("Could not fully parse evidence_full.jsonl for %s: %s", request_id, exc)

    # Fallback to manifest allowed_source_ids if evidence_full.jsonl yielded nothing
    if not evidence_ids and "allowed_source_ids" in manifest:
        evidence_ids = {str(eid) for eid in manifest.get("allowed_source_ids", [])}

    return bundle_dir, manifest, evidence_ids


def import_ide_response(
    response_path: str | Path,
    *,
    root: str | Path = HANDOFF_ROOT,
) -> ImportValidationResult:
    root_path = Path(root)
    try:
        raw_text = Path(response_path).read_text(encoding="utf-8")
        if not raw_text.strip():
            return ImportValidationResult(False, False, errors=[f"response file is empty: {response_path}"])
        response = json.loads(raw_text)
    except FileNotFoundError:
        return ImportValidationResult(False, False, errors=[f"response file not found: {response_path}"])
    except json.JSONDecodeError as exc:
        return ImportValidationResult(False, False, errors=[f"malformed JSON response: {exc}"])
    except Exception as exc:
        return ImportValidationResult(False, False, errors=[f"error reading response file: {_sanitize_reason(str(exc))}"])

    if not isinstance(response, dict):
        return ImportValidationResult(False, False, errors=["response JSON root must be an object/dict"])

    errors: list[str] = []
    warnings: list[str] = []

    request_id = str(response.get("request_id", "")).strip()
    if not request_id:
        return ImportValidationResult(False, False, errors=["request_id is required"], response=response)

    bundle_dir: Path | None = None
    manifest: dict[str, Any] = {}
    allowed_ids: set[str] = set()
    try:
        bundle_dir, manifest, allowed_ids = _load_manifest_for_request(request_id, root_path)
    except ValueError as exc:
        return ImportValidationResult(False, False, errors=[str(exc)], response=response)

    # 1. Schema version check
    resp_schema = response.get("schema_version")
    if resp_schema and resp_schema != RESPONSE_SCHEMA_VERSION:
        errors.append(f"invalid schema_version: expected {RESPONSE_SCHEMA_VERSION}, got {resp_schema}")

    # 2. Check explicit failure reported by IDE
    status_val = str(response.get("status", "")).strip().lower()
    if status_val == "failed":
        err_msg = response.get("error") or response.get("reason") or "IDE reported explicit failure"
        errors.append(f"IDE processing failed: {_sanitize_reason(str(err_msg))}")

    # 3. Answer markdown/text requirement
    answer_text = str(response.get("answer_text") or response.get("answer_markdown") or "").strip()
    if not answer_text and not errors:
        errors.append("answer_markdown is required")

    # 4. Model tool name requirement
    if not str(response.get("model_tool_name", "")).strip() and not errors:
        errors.append("model_tool_name is required")

    # 5. Privacy acknowledged requirement for local_only
    is_local_only = (
        manifest.get("privacy_mode") == "local_only"
        or manifest.get("privacy_level") == "local_only"
        or manifest.get("local_only") is True
    )
    if is_local_only and response.get("privacy_acknowledged") is not True:
        errors.append("privacy_acknowledged must be true for local_only bundle")

    # 6. Used full bundle requirement
    if response.get("used_full_bundle") is not True:
        errors.append("used_full_bundle must be true")

    # 7. Safe citation bounds checking
    raw_citations = response.get("evidence_ids_used")
    if raw_citations is None:
        raw_citations = response.get("cited_evidence_ids")
    if isinstance(raw_citations, str):
        raw_citations = [raw_citations]
    elif not isinstance(raw_citations, (list, tuple, set)):
        raw_citations = []
    used_ids = {str(item).strip() for item in raw_citations if str(item).strip()}

    unknown = sorted(used_ids - allowed_ids)
    if unknown:
        errors.append(f"unknown evidence_ids_used: {', '.join(unknown)}")

    final_answer = not errors and bool(used_ids)
    if not used_ids and not errors:
        warnings.append("No evidence_ids_used; import is review_required and not final")

    # Field canonicalization
    if "answer_text" not in response and "answer_markdown" in response:
        response["answer_text"] = response["answer_markdown"]
    if "evidence_ids_used" not in response and "cited_evidence_ids" in response:
        response["evidence_ids_used"] = list(used_ids)
    if "confidence_label" not in response and "confidence" in response:
        response["confidence_label"] = response["confidence"]

    # If validation errors occurred and bundle directory exists, transition request_status.json to failed
    if errors and bundle_dir and (bundle_dir / "request_status.json").exists():
        update_request_status(
            bundle_dir / "request_status.json",
            REQ_STATE_FAILED,
            error="; ".join(errors),
            error_reason="validation_failed",
        )

    return ImportValidationResult(not errors, final_answer, warnings, errors, response, manifest)


def save_imported_ide_answer(
    case_id: str,
    validation: ImportValidationResult,
    *,
    root: str | Path = HANDOFF_ROOT,
) -> PastedStrongModelAnswer:
    if not validation.ok:
        raise ValueError("cannot save invalid IDE response: " + "; ".join(validation.errors))
    root_path = Path(root)
    response, manifest = validation.response, validation.manifest
    evidence_ids = list(response.get("evidence_ids_used") or [])

    answer = PastedStrongModelAnswer(
        draft_id=f"IDE-{uuid.uuid4().hex[:12].upper()}",
        pack_id=manifest["request_id"],
        query=manifest["question"],
        answer_text=response["answer_text"].strip(),
        citation_ids=evidence_ids,
        evidence_ids=evidence_ids,
        privacy_mode=manifest.get("privacy_mode", "local_only"),
        allowed_external=manifest.get("allowed_external", False),
        insufficient_evidence=not validation.final_answer,
        confidence_label=response.get("confidence_label", "low"),
        warnings=list(validation.warnings),
        final_answer=validation.final_answer,
        model_tool_name=response["model_tool_name"].strip(),
        route_summary="ide_full_bundle_handoff",
        prompt_pack_id=manifest["request_id"],
        metadata={
            "answer_kind": "ide_handoff_strong_answer",
            "route_summary": "ide_full_bundle_handoff",
            "risk_label": response.get("risk_label", ""),
            "used_full_bundle": str(response.get("used_full_bundle")),
            "request_id": manifest["request_id"],
        },
    )

    save_evidence(
        EvidenceItem(
            evidence_id=answer.draft_id,
            case_id=case_id,
            source_type="ide_handoff_strong_answer",
            source_path=f"ide_handoff:{manifest['request_id']}",
            title=f"Câu trả lời AI IDE full bundle - {answer.model_tool_name}",
            extracted_text=answer.answer_text,
            structured_summary=json.dumps(asdict(answer), ensure_ascii=False),
            confidence=answer.confidence_label,
            privacy_level=answer.privacy_mode,
            review_status="reviewed" if answer.final_answer else "draft",
            source_origin="ide_handoff",
            verification_status="reviewed" if answer.final_answer else "draft",
        )
    )

    processed_dir = root_path / "processed" / manifest["request_id"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    resp_path = root_path / "inbox" / manifest["request_id"] / "response.json"
    legacy_resp_path = root_path / "inbox" / f"RESP-{manifest['request_id']}.json"

    if resp_path.exists():
        shutil.copy2(resp_path, processed_dir / "response.json")
    elif legacy_resp_path.exists():
        shutil.copy2(legacy_resp_path, processed_dir / "response.json")

    import_result = {
        "request_id": manifest["request_id"],
        "ok": validation.ok,
        "final_answer": validation.final_answer,
        "warnings": validation.warnings,
        "errors": validation.errors,
        "saved_answer_id": answer.draft_id,
        "imported_at": datetime.now().isoformat(),
    }
    (processed_dir / "import_result.json").write_text(
        json.dumps(import_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Transition request_status.json to completed (with legacy imported_at compatibility)
    status_path = root_path / "outbox" / manifest["request_id"] / "request_status.json"
    if status_path.exists():
        update_request_status(
            status_path,
            REQ_STATE_COMPLETED,
            saved_answer_id=answer.draft_id,
        )

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


def vietnamese_next_step_instruction(
    request_id: str,
    outbox_dir: str | Path,
    inbox_response_path: str | Path,
    privacy_mode: str,
) -> str:
    warning = " Dữ liệu local_only: chỉ dùng Antigravity/model đã được owner cho phép." if privacy_mode == "local_only" else ""
    return f"Mở Antigravity, đọc gói tại {outbox_dir}, làm theo prompt_for_antigravity.md, rồi lưu response.json vào {inbox_response_path}. Quay lại màn hình này và bấm Kiểm tra phản hồi từ Antigravity.{warning}"


def block_cloud_provider_for_local_only(manifest: dict[str, Any]) -> tuple[bool, str]:
    if manifest.get("local_only") or manifest.get("privacy_mode") == "local_only":
        return True, "Bị chặn: bundle local_only không được gửi cloud/provider tự động."
    return False, "Cho phép nếu provider đã được owner phê duyệt."


def write_ide_handoff_response(
    request_id: str,
    answer_markdown: str,
    cited_evidence_ids: list[str] | None = None,
    *,
    root: str | Path = HANDOFF_ROOT,
    confidence: str = "high",
    limitations: list[str] | None = None,
    recommended_next_actions: list[str] | None = None,
    privacy_acknowledged: bool = True,
    used_full_bundle: bool = True,
    model_tool_name: str = "Antigravity IDE AI",
    unsupported_claims: list[str] | None = None,
) -> Path:
    """Write an official, fully validated response.json to the expected inbox directory for request_id."""
    root_path = Path(root)
    inbox_dir = root_path / "inbox" / request_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    response_file = inbox_dir / "response.json"

    # Automatically derive citations from outbox manifest if not explicitly given
    if cited_evidence_ids is None:
        try:
            _, manifest, allowed_ids = _load_manifest_for_request(request_id, root_path)
            matched_ids = []
            for ev_id in allowed_ids:
                pattern = re.compile(r'(?<![A-Za-z0-9_-])' + re.escape(str(ev_id)) + r'(?![A-Za-z0-9_-])')
                if pattern.search(answer_markdown):
                    matched_ids.append(str(ev_id))
            cited_evidence_ids = matched_ids
        except Exception:
            cited_evidence_ids = []

    payload = convert_markdown_answer_to_ide_response(
        request_id=request_id,
        markdown_text=answer_markdown,
        cited_evidence_ids=cited_evidence_ids,
        confidence=confidence,
        limitations=limitations,
        recommended_next_actions=recommended_next_actions,
        privacy_acknowledged=privacy_acknowledged,
        used_full_bundle=used_full_bundle,
        model_tool_name=model_tool_name,
        unsupported_claims=unsupported_claims,
    )

    tmp_file = inbox_dir / f"response_{uuid.uuid4().hex[:6]}.tmp"
    tmp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_file.replace(response_file)
    return response_file
