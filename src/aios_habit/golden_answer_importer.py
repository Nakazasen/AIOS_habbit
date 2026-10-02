"""Batch answer importer: validate -> SHA-256 dedup -> staging only.

Per design doc section 3.4:
1. Integrity: every answer's question_id must exist in the batch manifest.
2. Schema validation: each answer goes through GoldenAnswer validation;
   failures are collected into import_errors.jsonl (the answer is not imported).
3. Dedup: key = sha256(question_id + "|" + normalized answer_text).
4. Labeling: ENRICHMENT_LABEL ("kiến thức đã được đào tạo bổ sung") is
   system-assigned; no LLM-source field is ever stored.
5. Claim mapping: "answered" answers become KnowledgeClaim (status candidate)
   via the existing claim extractor, with conflict detection (conflicted +
   escalate, never auto-resolve).
6. Storage: ONLY local_cases/staging_enrichment.sqlite (separate from the
   production DB and production index). Direct writes to prod are refused.
7. Expert feedback: record_expert_feedback() versions the answer and flips
   reviewer_status to "chuyen_gia_da_phan_hoi" with a responsibility record.
   The importer itself REFUSES input already marked as expert-reviewed.

CLI:
    python -m aios_habit.golden_answer_importer \\
        --answers batch_..._answers.jsonl --manifest batch_..._manifest.json \\
        --staging local_cases/staging_enrichment.sqlite

Python 3.11 compatible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from aios_habit.expert_interview_models import InterviewSession, InterviewTurn
from aios_habit.golden_question_schema import (
    ANSWER_STATE_ANSWERED,
    ENRICHMENT_LABEL,
    FORBIDDEN_SOURCE_FIELDS,
    REVIEWER_STATUS_PENDING,
    REVIEWER_STATUS_REVIEWED,
    GoldenAnswer,
    GoldenSchemaError,
)
from aios_habit.knowledge_claim_extractor import (
    CLAIM_STATUS_CANDIDATE,
    KnowledgeClaim,
    detect_claim_conflicts,
    extract_claim_from_turn,
    mark_conflicting_claims,
)

# Production stores the importer must never write to.
PROD_DB_FILENAMES = frozenset(
    {
        "workspace_chat.sqlite",
        "workspace_chat_rag_v2_production",
        "error_cases_dict.db",
        "production.sqlite",
    }
)

DEFAULT_STAGING_NAME = "staging_enrichment.sqlite"


class GoldenImportError(ValueError):
    """Raised when an import batch cannot proceed."""


class ProductionWriteRefusedError(GoldenImportError):
    """Raised when the staging path looks like a production store."""


def assert_not_production(path: Path, extra_prod_paths: Sequence[Path] = ()) -> None:
    """Refuse any staging path that resolves to a production DB/index."""
    resolved = Path(path).expanduser().resolve()
    name = resolved.name
    lowered = str(resolved).lower()
    if name in PROD_DB_FILENAMES:
        raise ProductionWriteRefusedError(
            "Từ chối ghi vào kho production (%s). Staging phải là file riêng." % name
        )
    if "production" in lowered and DEFAULT_STAGING_NAME not in name:
        raise ProductionWriteRefusedError(
            "Đường dẫn staging trỏ vào vùng production: %s" % resolved
        )
    for prod in extra_prod_paths:
        if resolved == Path(prod).expanduser().resolve():
            raise ProductionWriteRefusedError(
                "Staging trùng đường dẫn production đã khai báo: %s" % prod
            )


def normalize_answer_text(text: str) -> str:
    """Canonical form for dedup: lowercase, collapse whitespace."""
    return " ".join(text.lower().split())


def dedup_key(question_id: str, answer_text: str) -> str:
    raw = question_id.strip() + "|" + normalize_answer_text(answer_text)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def init_staging_db(staging_path: Path) -> sqlite3.Connection:
    """Create the staging schema (answers + claims + expert reviews)."""
    conn = sqlite3.connect(str(staging_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_answers (
            answer_id TEXT PRIMARY KEY,
            question_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            answer_sha TEXT NOT NULL,
            enrichment_label TEXT NOT NULL,
            reviewer_status TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            supersedes_answer_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_claims (
            claim_id TEXT PRIMARY KEY,
            answer_id TEXT NOT NULL,
            statement TEXT NOT NULL,
            scope TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL,
            conflict_claim_ids_json TEXT NOT NULL DEFAULT '[]',
            escalation_id TEXT,
            source_refs_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY (answer_id) REFERENCES staging_answers(answer_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expert_reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_id TEXT NOT NULL,
            answer_version INTEGER NOT NULL,
            reviewer TEXT NOT NULL,
            confidence REAL NOT NULL,
            sources_checked TEXT NOT NULL,
            responsibility_confirmed INTEGER NOT NULL,
            corrections_json TEXT NOT NULL,
            reviewed_at TEXT NOT NULL,
            FOREIGN KEY (answer_id) REFERENCES staging_answers(answer_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_staging_answers_sha ON staging_answers(answer_sha)"
    )
    conn.commit()
    return conn


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_manifest(manifest_path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldenImportError("Không đọc được manifest: %s" % exc)
    for key in ("batch_id", "question_ids"):
        if key not in data:
            raise GoldenImportError("Manifest thiếu trường bắt buộc '%s'." % key)
    return data


def _answer_to_claim(
    answer: GoldenAnswer,
    batch_id: str,
    sequence: int,
    existing_claims: Sequence[KnowledgeClaim],
) -> Tuple[KnowledgeClaim, bool]:
    """Map an 'answered' answer to a KnowledgeClaim (candidate).

    Reuses extract_claim_from_turn with require_confirmed_tokens=True, then
    rebinds provenance to (answer_id, question_id, *case_ids) as the design
    requires. Returns (claim, had_conflict).
    """
    session = InterviewSession(
        session_id="GQB-%s" % batch_id,
        plan_id="GQB-PLAN-%s" % batch_id,
        expert_id="batch-respondent",
        principal_subject_id="batch-respondent",
    )
    turn = InterviewTurn(
        turn_id=answer.answer_id,
        session_id=session.session_id,
        sequence=sequence,
        question_text=answer.question_id,
        answer_text=answer.answer_text,
        question_reason="golden_question_batch",
        answer_confidence=answer.confidence,
        answer_state=answer.answer_state,
    )
    base = extract_claim_from_turn(
        turn, session, answer.error_group, require_confirmed_tokens=True
    )
    claim = KnowledgeClaim(
        claim_id="CLM-GA-%s" % answer.answer_id,
        statement=base.statement,
        scope=base.scope,
        source_refs=(answer.answer_id, answer.question_id) + tuple(answer.case_ids),
        version="1.0",
        validity_conditions=base.validity_conditions,
        confidence=base.confidence,
        uncertainty_note=base.uncertainty_note,
        status=CLAIM_STATUS_CANDIDATE,
    )
    conflicts = detect_claim_conflicts(claim, existing_claims)
    if conflicts.has_conflict:
        claim = mark_conflicting_claims(claim, conflicts.conflicting_claim_ids, conflicts.reason)
        return claim, True
    return claim, False


@dataclass
class ImportReport:
    """Outcome of one import run."""

    batch_id: str
    staging_path: Path
    imported: int = 0
    duplicates_skipped: int = 0
    claims_created: int = 0
    conflicted_claims: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "staging_path": str(self.staging_path),
            "imported": self.imported,
            "duplicates_skipped": self.duplicates_skipped,
            "claims_created": self.claims_created,
            "conflicted_claims": self.conflicted_claims,
            "errors": self.errors,
        }


def import_batch_answers(
    answers_path: Path,
    manifest_path: Path,
    staging_path: Path,
    extra_prod_paths: Sequence[Path] = (),
) -> ImportReport:
    """Validate + dedup + store answers into the staging sqlite (only)."""
    assert_not_production(staging_path, extra_prod_paths)
    manifest = _load_manifest(manifest_path)
    batch_id = str(manifest["batch_id"])
    allowed_questions = set(str(q) for q in manifest["question_ids"])

    answers_file = Path(answers_path)
    if not answers_file.exists():
        raise GoldenImportError("Không tìm thấy file đáp án: %s" % answers_file)

    conn = init_staging_db(staging_path)
    report = ImportReport(batch_id=batch_id, staging_path=staging_path)
    try:
        existing_claims = _load_claims(conn)
        sequence = conn.execute("SELECT COUNT(*) FROM staging_claims").fetchone()[0] + 1

        for line_no, raw_line in enumerate(answers_file.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise GoldenSchemaError("Mỗi dòng phải là một object JSON.")
                forbidden = sorted(set(data.keys()) & set(FORBIDDEN_SOURCE_FIELDS))
                if forbidden:
                    raise GoldenSchemaError(
                        "Cấm lưu vết nguồn LLM (trường: %s)." % ", ".join(forbidden)
                    )
                answer = GoldenAnswer.from_dict(data)
            except (GoldenSchemaError, json.JSONDecodeError, ValueError) as exc:
                report.errors.append({"line": line_no, "reason": str(exc)})
                continue

            if answer.question_id not in allowed_questions:
                report.errors.append(
                    {
                        "line": line_no,
                        "answer_id": answer.answer_id,
                        "reason": "question_id '%s' không có trong manifest batch %s."
                        % (answer.question_id, batch_id),
                    }
                )
                continue

            if answer.reviewer_status == REVIEWER_STATUS_REVIEWED:
                report.errors.append(
                    {
                        "line": line_no,
                        "answer_id": answer.answer_id,
                        "reason": "Importer không được gắn trạng thái 'chuyen_gia_da_phan_hoi'; "
                        "chỉ luồng chuyên gia phản hồi mới được phép.",
                    }
                )
                continue

            # Force system label (importer owns it, never the respondent).
            if answer.enrichment_label != ENRICHMENT_LABEL:
                report.errors.append(
                    {
                        "line": line_no,
                        "answer_id": answer.answer_id,
                        "reason": "Nhãn làm giàu tri thức sai, hệ thống sẽ tự gắn lại.",
                    }
                )
                continue

            key = dedup_key(answer.question_id, answer.answer_text)
            dup = conn.execute(
                "SELECT answer_id FROM staging_answers WHERE answer_sha = ?", (key,)
            ).fetchone()
            if dup:
                report.duplicates_skipped += 1
                continue

            created_at = _utc_now_iso()
            try:
                conn.execute(
                    """
                    INSERT INTO staging_answers
                    (answer_id, question_id, batch_id, payload_json, answer_sha,
                     enrichment_label, reviewer_status, version, supersedes_answer_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        answer.answer_id,
                        answer.question_id,
                        batch_id,
                        json.dumps(answer.to_dict(), ensure_ascii=False),
                        key,
                        ENRICHMENT_LABEL,
                        REVIEWER_STATUS_PENDING,
                        data.get("supersedes_answer_id"),
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError:
                report.errors.append(
                    {
                        "line": line_no,
                        "answer_id": answer.answer_id,
                        "reason": "answer_id đã tồn tại trong staging với nội dung khác; "
                        "hãy dùng answer_id mới hoặc ghi supersedes_answer_id.",
                    }
                )
                continue
            report.imported += 1

            if answer.answer_state == ANSWER_STATE_ANSWERED:
                claim, had_conflict = _answer_to_claim(answer, batch_id, sequence, existing_claims)
                sequence += 1
                conn.execute(
                    """
                    INSERT INTO staging_claims
                    (claim_id, answer_id, statement, scope, confidence, status,
                     conflict_claim_ids_json, escalation_id, source_refs_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claim.claim_id,
                        answer.answer_id,
                        claim.statement,
                        claim.scope,
                        claim.confidence,
                        claim.status,
                        json.dumps(list(claim.conflict_claim_ids), ensure_ascii=False),
                        claim.escalation_id,
                        json.dumps(list(claim.source_refs), ensure_ascii=False),
                        created_at,
                    ),
                )
                existing_claims.append(claim)
                report.claims_created += 1
                if had_conflict:
                    report.conflicted_claims += 1
        conn.commit()
    finally:
        conn.close()

    if report.errors:
        errors_path = staging_path.parent / "import_errors.jsonl"
        with errors_path.open("w", encoding="utf-8") as handle:
            for item in report.errors:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return report


def _load_claims(conn: sqlite3.Connection) -> List[KnowledgeClaim]:
    claims: List[KnowledgeClaim] = []
    for row in conn.execute(
        "SELECT claim_id, statement, scope, confidence, status, "
        "conflict_claim_ids_json, escalation_id, source_refs_json FROM staging_claims"
    ):
        claims.append(
            KnowledgeClaim(
                claim_id=row[0],
                statement=row[1],
                scope=row[2],
                source_refs=tuple(json.loads(row[7] or "[]")),
                confidence=float(row[3]),
                status=row[4],
                conflict_claim_ids=tuple(json.loads(row[5] or "[]")),
                escalation_id=row[6],
            )
        )
    return claims


def record_expert_feedback(
    staging_path: Path,
    answer_id: str,
    *,
    reviewer: str,
    confidence: float,
    sources_checked: str,
    responsibility_confirmed: bool,
    corrections: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply a real expert's review: version+1, status -> chuyen_gia_da_phan_hoi.

    Mirrors the responsibility pattern of submit_artifact_approval (reviewer,
    confidence, checked sources, explicit responsibility confirmation).
    Drafts can never be marked reviewed through the importer itself.
    """
    if not reviewer.strip():
        raise GoldenImportError("Phản hồi chuyên gia bắt buộc phải ghi người duyệt.")
    if not (0.0 <= confidence <= 1.0):
        raise GoldenImportError("confidence phải nằm trong [0.0, 1.0].")
    if not responsibility_confirmed:
        raise GoldenImportError(
            "Chuyên gia phải xác nhận trách nhiệm thì trạng thái mới được chuyển."
        )
    corrections = corrections or {}

    conn = init_staging_db(staging_path)
    try:
        row = conn.execute(
            "SELECT payload_json, version, reviewer_status FROM staging_answers WHERE answer_id = ?",
            (answer_id,),
        ).fetchone()
        if not row:
            raise GoldenImportError("Không tìm thấy đáp án %s trong staging." % answer_id)
        payload = json.loads(row[0])
        if row[2] == REVIEWER_STATUS_REVIEWED:
            raise GoldenImportError("Đáp án %s đã được chuyên gia phản hồi trước đó." % answer_id)

        for fname, value in corrections.items():
            if fname in ("answer_id", "question_id", "enrichment_label"):
                raise GoldenImportError("Không được sửa trường định danh/nhãn: %s." % fname)
            payload[fname] = value
        # Re-validate after corrections; reviewer_status flips only here.
        payload["reviewer_status"] = REVIEWER_STATUS_REVIEWED
        answer = GoldenAnswer.from_dict(payload)

        new_version = int(row[1]) + 1
        reviewed_at = _utc_now_iso()
        conn.execute(
            "UPDATE staging_answers SET payload_json = ?, reviewer_status = ?, version = ? "
            "WHERE answer_id = ?",
            (json.dumps(answer.to_dict(), ensure_ascii=False), REVIEWER_STATUS_REVIEWED,
             new_version, answer_id),
        )
        conn.execute(
            """
            INSERT INTO expert_reviews
            (answer_id, answer_version, reviewer, confidence, sources_checked,
             responsibility_confirmed, corrections_json, reviewed_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                answer_id,
                new_version,
                reviewer.strip(),
                confidence,
                sources_checked.strip(),
                json.dumps(corrections, ensure_ascii=False),
                reviewed_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "answer_id": answer_id,
        "new_version": new_version,
        "reviewer_status": REVIEWER_STATUS_REVIEWED,
        "reviewed_at": reviewed_at,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Nhập đáp án batch vào staging (chỉ staging, cấm ghi production)."
    )
    parser.add_argument("--answers", required=True, help="File JSONL đáp án.")
    parser.add_argument("--manifest", required=True, help="Manifest batch đã xuất.")
    parser.add_argument("--staging", required=True, help="File staging sqlite.")
    parser.add_argument("--prod-db", action="append", default=[],
                        help="Đường dẫn production cần chặn (lặp lại được).")
    args = parser.parse_args(argv)

    try:
        report = import_batch_answers(
            Path(args.answers),
            Path(args.manifest),
            Path(args.staging),
            [Path(p) for p in args.prod_db],
        )
    except GoldenImportError as exc:
        print("Lỗi nhập batch: %s" % exc, file=sys.stderr)
        return 1

    print("Nhập batch %s vào %s:" % (report.batch_id, report.staging_path))
    print("  Đáp án đã nhập: %d" % report.imported)
    print("  Trùng lặp bỏ qua: %d" % report.duplicates_skipped)
    print("  Claim đã tạo: %d (xung đột: %d)" % (report.claims_created, report.conflicted_claims))
    if report.errors:
        print("  Lỗi: %d (xem import_errors.jsonl cạnh file staging)" % len(report.errors))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
