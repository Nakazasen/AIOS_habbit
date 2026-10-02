"""Causal Q&A form schema for the golden-question knowledge-enrichment pilot.

Implements the contract from docs/phieu-viec/thiet-ke-bo-sinh-cau-hoi-vang.md
section 3.1: GoldenQuestion (one golden question in a batch) and GoldenAnswer
(the causal investigation form a batch respondent fills in).

Business rules enforced here:
- Vague forms are REJECTED: an "answered" answer must carry causality
  (hypotheses, causal mechanism, 4M branches) and evidence
  (evidence to collect, confirm criteria).
- The single enrichment label is system-assigned:
  "kien thuc da duoc dao tao bo sung" is expressed in Vietnamese below as
  ENRICHMENT_LABEL. Nobody filling the form may change it.
- No LLM-source field is ever stored (no answered_by / model_name / provenance).
- Expert-feedback lifecycle is a business state, not a source label:
  "cho_chuyen_gia_phan_hoi" (pending) / "chuyen_gia_da_phan_hoi" (reviewed).
  Only expert-confirmed entries may ever merge to the real store; the merge
  itself is a separate future ticket and is NOT implemented here.

Python 3.11 compatible: no PEP 701 multiline f-strings, no `type` statements.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Tuple

# The single allowed enrichment label, system-assigned at import time.
ENRICHMENT_LABEL = "kiến thức đã được đào tạo bổ sung"

# Expert-feedback business states (NOT a source label).
REVIEWER_STATUS_PENDING = "cho_chuyen_gia_phan_hoi"
REVIEWER_STATUS_REVIEWED = "chuyen_gia_da_phan_hoi"
ALLOWED_REVIEWER_STATUSES = (REVIEWER_STATUS_PENDING, REVIEWER_STATUS_REVIEWED)

# Answer states allowed in a batch (skipped is not used in batch answering).
ANSWER_STATE_ANSWERED = "answered"
ANSWER_STATE_UNCERTAIN = "uncertain"
ANSWER_STATE_UNKNOWN = "unknown"
ALLOWED_BATCH_ANSWER_STATES = (
    ANSWER_STATE_ANSWERED,
    ANSWER_STATE_UNCERTAIN,
    ANSWER_STATE_UNKNOWN,
)

# 4M branches.
M4_BRANCHES = ("Man", "Machine", "Material", "Method")

# Closed vocabulary for GoldenQuestion.loai_cau_hoi (pilot scope: do not invent
# new kinds at runtime).
LOAI_PHENOMENON = "phenomenon"
LOAI_TIMELINE = "timeline"
LOAI_BEFORE_AFTER = "before_after"
LOAI_M4_MAN = "m4_man"
LOAI_M4_MACHINE = "m4_machine"
LOAI_M4_MATERIAL = "m4_material"
LOAI_M4_METHOD = "m4_method"
LOAI_CAUSAL_MECHANISM = "causal_mechanism"
LOAI_EVIDENCE_CONFIRM = "evidence_confirm"
LOAI_EVIDENCE_REFUTE = "evidence_refute"
LOAI_DISCRIMINATOR = "discriminator"
LOAI_EXCEPTION = "exception"
LOAI_TEMP_COUNTERMEASURE = "temp_countermeasure"
LOAI_PERM_COUNTERMEASURE = "perm_countermeasure"
LOAI_RECURRENCE = "recurrence"
LOAI_RELATED_CASE = "related_case"

ALLOWED_LOAI_CAU_HOI = (
    LOAI_PHENOMENON,
    LOAI_TIMELINE,
    LOAI_BEFORE_AFTER,
    LOAI_M4_MAN,
    LOAI_M4_MACHINE,
    LOAI_M4_MATERIAL,
    LOAI_M4_METHOD,
    LOAI_CAUSAL_MECHANISM,
    LOAI_EVIDENCE_CONFIRM,
    LOAI_EVIDENCE_REFUTE,
    LOAI_DISCRIMINATOR,
    LOAI_EXCEPTION,
    LOAI_TEMP_COUNTERMEASURE,
    LOAI_PERM_COUNTERMEASURE,
    LOAI_RECURRENCE,
    LOAI_RELATED_CASE,
)

# Scorer component keys; every scored question must expose all six.
SCORE_COMPONENTS = ("D", "G", "E", "W", "N", "F")

# Fields that would leak an LLM source into the store. Rejected on sight.
FORBIDDEN_SOURCE_FIELDS = frozenset(
    {
        "answered_by",
        "answer_by",
        "model_name",
        "llm_source",
        "llm_model",
        "source_model",
        "ai_provider",
        "generated_by",
        "provenance",
        "copilot",
        "chatgpt",
        "gemini",
    }
)


class GoldenSchemaError(ValueError):
    """Validation failure of a golden question or golden answer form."""


def _require_non_empty_str(data: Dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoldenSchemaError("Trường '%s' bắt buộc phải là chuỗi khác rỗng." % key)
    return value.strip()


def _require_non_empty_list(data: Dict[str, Any], key: str) -> List[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise GoldenSchemaError("Trường '%s' bắt buộc phải là danh sách khác rỗng." % key)
    return value


def _reject_forbidden_source_fields(data: Dict[str, Any]) -> None:
    found = sorted(set(data.keys()) & set(FORBIDDEN_SOURCE_FIELDS))
    if found:
        raise GoldenSchemaError(
            "Cấm lưu vết nguồn LLM trong kho (trường không cho phép: %s)." % ", ".join(found)
        )


@dataclass(frozen=True)
class GoldenQuestion:
    """One golden question inside an exported batch."""

    question_id: str
    text: str
    target_gap_id: str
    target_case_ids: Tuple[str, ...]
    loai_cau_hoi: str
    muc_tieu: str
    gia_thuyet_lien_quan: Tuple[str, ...] = ()
    expected_evidence: Tuple[str, ...] = ()
    diem: float = 0.0
    diem_thanh_phan: Dict[str, float] = field(default_factory=dict)
    # Extra traceability (not part of the strict contract).
    discriminant_pairs: Tuple[Tuple[str, str], ...] = ()
    m4_branch: str = ""
    why_level: int = 0
    batch_id: str = ""

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise GoldenSchemaError("Mã câu hỏi (question_id) không được để trống.")
        if len(self.text.strip()) < 10:
            raise GoldenSchemaError("Nội dung câu hỏi quá ngắn, cần mô tả rõ ràng.")
        if not self.target_gap_id.strip():
            raise GoldenSchemaError("Câu hỏi vàng bắt buộc phải nối về một gap_id.")
        if not self.target_case_ids:
            raise GoldenSchemaError("Câu hỏi vàng bắt buộc phải gắn ít nhất 1 ca lỗi thật.")
        if self.loai_cau_hoi not in ALLOWED_LOAI_CAU_HOI:
            raise GoldenSchemaError(
                "loai_cau_hoi '%s' không thuộc bộ từ vựng khép kín của pilot." % self.loai_cau_hoi
            )
        if not self.muc_tieu.strip():
            raise GoldenSchemaError("Câu hỏi vàng bắt buộc phải ghi mục tiêu (muc_tieu).")
        if not (0.0 <= self.diem <= 100.0):
            raise GoldenSchemaError("Điểm câu hỏi (diem) phải nằm trong [0, 100].")
        unknown_keys = set(self.diem_thanh_phan.keys()) - set(SCORE_COMPONENTS)
        if unknown_keys:
            raise GoldenSchemaError("Điểm thành phần có khóa lạ: %s." % sorted(unknown_keys))
        for key, value in self.diem_thanh_phan.items():
            if not (0.0 <= value <= 1.0):
                raise GoldenSchemaError("Điểm thành phần '%s' phải nằm trong [0, 1]." % key)
        if self.diem > 0 and set(self.diem_thanh_phan.keys()) != set(SCORE_COMPONENTS):
            raise GoldenSchemaError(
                "Câu hỏi đã chấm điểm bắt buộc phải có đủ 6 điểm thành phần D/G/E/W/N/F."
            )
        if self.m4_branch and self.m4_branch not in M4_BRANCHES:
            raise GoldenSchemaError("Nhánh 4M '%s' không hợp lệ." % self.m4_branch)
        if self.why_level < 0:
            raise GoldenSchemaError("why_level không được âm.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "text": self.text,
            "target_gap_id": self.target_gap_id,
            "target_case_ids": list(self.target_case_ids),
            "loai_cau_hoi": self.loai_cau_hoi,
            "muc_tieu": self.muc_tieu,
            "gia_thuyet_lien_quan": list(self.gia_thuyet_lien_quan),
            "expected_evidence": list(self.expected_evidence),
            "diem": self.diem,
            "diem_thanh_phan": dict(self.diem_thanh_phan),
            "discriminant_pairs": [list(p) for p in self.discriminant_pairs],
            "m4_branch": self.m4_branch,
            "why_level": self.why_level,
            "batch_id": self.batch_id,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GoldenQuestion":
        if not isinstance(data, dict):
            raise GoldenSchemaError("Câu hỏi vàng phải là một object JSON.")
        pairs = tuple(
            (str(p[0]), str(p[1]))
            for p in (data.get("discriminant_pairs") or [])
            if isinstance(p, (list, tuple)) and len(p) == 2
        )
        return GoldenQuestion(
            question_id=_require_non_empty_str(data, "question_id"),
            text=_require_non_empty_str(data, "text"),
            target_gap_id=_require_non_empty_str(data, "target_gap_id"),
            target_case_ids=tuple(str(x) for x in _require_non_empty_list(data, "target_case_ids")),
            loai_cau_hoi=_require_non_empty_str(data, "loai_cau_hoi"),
            muc_tieu=_require_non_empty_str(data, "muc_tieu"),
            gia_thuyet_lien_quan=tuple(str(x) for x in (data.get("gia_thuyet_lien_quan") or [])),
            expected_evidence=tuple(str(x) for x in (data.get("expected_evidence") or [])),
            diem=float(data.get("diem", 0.0)),
            diem_thanh_phan=dict(data.get("diem_thanh_phan") or {}),
            discriminant_pairs=pairs,
            m4_branch=str(data.get("m4_branch") or ""),
            why_level=int(data.get("why_level") or 0),
            batch_id=str(data.get("batch_id") or ""),
        )

    def with_score(self, diem: float, diem_thanh_phan: Dict[str, float]) -> "GoldenQuestion":
        """Return a scored copy (dataclass is frozen)."""
        return replace(self, diem=diem, diem_thanh_phan=dict(diem_thanh_phan))


@dataclass(frozen=True)
class GoldenAnswer:
    """Causal investigation form filled per golden question (batch answering)."""

    answer_id: str
    question_id: str
    gap_id: str
    case_ids: Tuple[str, ...]
    error_code: str
    error_group: str
    phenomenon: str
    answer_text: str
    answer_state: str
    confidence: float
    reviewer_status: str = REVIEWER_STATUS_PENDING
    model_line_station: str = ""
    occurrence_time: str = ""
    hypotheses: Tuple[str, ...] = ()
    causal_mechanism: str = ""
    m4_branches: Tuple[str, ...] = ()
    evidence_to_collect: Tuple[str, ...] = ()
    confirm_criteria: str = ""
    refute_criteria: str = ""
    discriminate_notes: str = ""
    question_loai: str = ""
    thresholds: Tuple[Dict[str, Any], ...] = ()
    exceptions: Tuple[str, ...] = ()
    temp_countermeasure: str = ""
    perm_countermeasure: str = ""
    recurrence_condition: str = ""
    related_cases: Tuple[str, ...] = ()
    related_docs: Tuple[str, ...] = ()
    needs_expert_review: Tuple[str, ...] = ()
    answered_at: str = ""
    enrichment_label: str = ENRICHMENT_LABEL

    def __post_init__(self) -> None:
        if not self.answer_id.strip():
            raise GoldenSchemaError("Mã đáp án (answer_id) không được để trống.")
        if not self.question_id.strip():
            raise GoldenSchemaError("Đáp án bắt buộc phải nối về một question_id.")
        if not self.gap_id.strip():
            raise GoldenSchemaError("Đáp án bắt buộc phải nối về một gap_id.")
        if not self.case_ids:
            raise GoldenSchemaError("Đáp án bắt buộc phải gắn ít nhất 1 ca lỗi thật.")
        if not self.error_code.strip():
            raise GoldenSchemaError("Mã lỗi (error_code) bắt buộc; nhóm không có mã thì ghi 'UNKNOWN'.")
        if not self.error_group.strip():
            raise GoldenSchemaError("Nhóm lỗi (error_group) bắt buộc.")
        if not self.phenomenon.strip():
            raise GoldenSchemaError("Hiện tượng (phenomenon) bắt buộc.")
        if len(self.answer_text.strip()) < 20:
            raise GoldenSchemaError(
                "Nội dung trả lời (answer_text) phải có ít nhất 20 ký tự, không chấp nhận câu trả lời qua loa."
            )
        if self.answer_state not in ALLOWED_BATCH_ANSWER_STATES:
            raise GoldenSchemaError(
                "answer_state '%s' không dùng trong batch (chỉ answered/uncertain/unknown)."
                % self.answer_state
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise GoldenSchemaError("confidence phải nằm trong [0.0, 1.0].")
        if self.reviewer_status not in ALLOWED_REVIEWER_STATUSES:
            raise GoldenSchemaError("reviewer_status '%s' không hợp lệ." % self.reviewer_status)
        if self.enrichment_label != ENRICHMENT_LABEL:
            raise GoldenSchemaError(
                "Nhãn làm giàu tri thức do hệ thống tự gắn, người điền không được sửa."
            )
        for branch in self.m4_branches:
            if branch not in M4_BRANCHES:
                raise GoldenSchemaError("Nhánh 4M '%s' không hợp lệ." % branch)
        for item in self.thresholds:
            if not isinstance(item, dict):
                raise GoldenSchemaError("Mỗi ngưỡng (thresholds) phải là một object.")
            for key in ("name", "value", "unit"):
                if key not in item or not str(item[key]).strip():
                    raise GoldenSchemaError("Ngưỡng thiếu trường bắt buộc '%s'." % key)
        # Vague-form rejection: an "answered" form must carry causality + evidence.
        if self.answer_state == ANSWER_STATE_ANSWERED:
            missing = []
            if not self.hypotheses:
                missing.append("hypotheses (giả thuyết nguyên nhân)")
            if not self.causal_mechanism.strip():
                missing.append("causal_mechanism (cơ chế gây lỗi)")
            if not self.m4_branches:
                missing.append("m4_branches (nhóm 4M)")
            if not self.evidence_to_collect:
                missing.append("evidence_to_collect (bằng chứng cần thu thập)")
            if not self.confirm_criteria.strip():
                missing.append("confirm_criteria (tiêu chí xác nhận)")
            if missing:
                raise GoldenSchemaError(
                    "Đáp án 'answered' mà thiếu nhân quả/bằng chứng thì bị từ chối "
                    "(thiếu: %s). Hãy điền đủ hoặc chuyển answer_state sang "
                    "uncertain/unknown và ghi needs_expert_review." % "; ".join(missing)
                )
            if self.question_loai == LOAI_DISCRIMINATOR and not self.discriminate_notes.strip():
                raise GoldenSchemaError(
                    "Câu loại 'discriminator' bắt buộc phải ghi discriminate_notes "
                    "(cách phân biệt với giả thuyết khác)."
                )
        # Expert-feedback routing: uncertain/unknown or low confidence must name
        # the fields that need a real expert's review.
        if self.answer_state != ANSWER_STATE_ANSWERED or self.confidence < 0.7:
            if not self.needs_expert_review:
                raise GoldenSchemaError(
                    "Đáp án chưa chắc chắn (state=%s, confidence=%.2f) bắt buộc phải liệt kê "
                    "needs_expert_review." % (self.answer_state, self.confidence)
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "question_id": self.question_id,
            "gap_id": self.gap_id,
            "case_ids": list(self.case_ids),
            "error_code": self.error_code,
            "error_group": self.error_group,
            "phenomenon": self.phenomenon,
            "model_line_station": self.model_line_station,
            "occurrence_time": self.occurrence_time,
            "answer_text": self.answer_text,
            "answer_state": self.answer_state,
            "hypotheses": list(self.hypotheses),
            "causal_mechanism": self.causal_mechanism,
            "m4_branches": list(self.m4_branches),
            "evidence_to_collect": list(self.evidence_to_collect),
            "confirm_criteria": self.confirm_criteria,
            "refute_criteria": self.refute_criteria,
            "discriminate_notes": self.discriminate_notes,
            "question_loai": self.question_loai,
            "thresholds": [dict(t) for t in self.thresholds],
            "exceptions": list(self.exceptions),
            "temp_countermeasure": self.temp_countermeasure,
            "perm_countermeasure": self.perm_countermeasure,
            "recurrence_condition": self.recurrence_condition,
            "related_cases": list(self.related_cases),
            "related_docs": list(self.related_docs),
            "needs_expert_review": list(self.needs_expert_review),
            "confidence": self.confidence,
            "reviewer_status": self.reviewer_status,
            "answered_at": self.answered_at,
            "enrichment_label": self.enrichment_label,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GoldenAnswer":
        if not isinstance(data, dict):
            raise GoldenSchemaError("Đáp án phải là một object JSON.")
        _reject_forbidden_source_fields(data)
        label = data.get("enrichment_label", ENRICHMENT_LABEL)
        return GoldenAnswer(
            answer_id=_require_non_empty_str(data, "answer_id"),
            question_id=_require_non_empty_str(data, "question_id"),
            gap_id=_require_non_empty_str(data, "gap_id"),
            case_ids=tuple(str(x) for x in _require_non_empty_list(data, "case_ids")),
            error_code=_require_non_empty_str(data, "error_code"),
            error_group=_require_non_empty_str(data, "error_group"),
            phenomenon=_require_non_empty_str(data, "phenomenon"),
            model_line_station=str(data.get("model_line_station") or ""),
            occurrence_time=str(data.get("occurrence_time") or ""),
            answer_text=_require_non_empty_str(data, "answer_text"),
            answer_state=_require_non_empty_str(data, "answer_state"),
            hypotheses=tuple(str(x) for x in (data.get("hypotheses") or [])),
            causal_mechanism=str(data.get("causal_mechanism") or ""),
            m4_branches=tuple(str(x) for x in (data.get("m4_branches") or [])),
            evidence_to_collect=tuple(str(x) for x in (data.get("evidence_to_collect") or [])),
            confirm_criteria=str(data.get("confirm_criteria") or ""),
            refute_criteria=str(data.get("refute_criteria") or ""),
            discriminate_notes=str(data.get("discriminate_notes") or ""),
            question_loai=str(data.get("question_loai") or ""),
            thresholds=tuple(dict(t) for t in (data.get("thresholds") or [])),
            exceptions=tuple(str(x) for x in (data.get("exceptions") or [])),
            temp_countermeasure=str(data.get("temp_countermeasure") or ""),
            perm_countermeasure=str(data.get("perm_countermeasure") or ""),
            recurrence_condition=str(data.get("recurrence_condition") or ""),
            related_cases=tuple(str(x) for x in (data.get("related_cases") or [])),
            related_docs=tuple(str(x) for x in (data.get("related_docs") or [])),
            needs_expert_review=tuple(str(x) for x in (data.get("needs_expert_review") or [])),
            confidence=float(data.get("confidence", 0.0)),
            reviewer_status=str(data.get("reviewer_status") or REVIEWER_STATUS_PENDING),
            answered_at=str(data.get("answered_at") or ""),
            enrichment_label=str(label),
        )


def answer_form_json_schema() -> Dict[str, Any]:
    """JSON-schema-style description of the GoldenAnswer form (embedded in exports)."""
    required = [
        "answer_id",
        "question_id",
        "gap_id",
        "case_ids",
        "error_code",
        "error_group",
        "phenomenon",
        "answer_text",
        "answer_state",
        "confidence",
    ]
    conditional = [
        "hypotheses",
        "causal_mechanism",
        "m4_branches",
        "evidence_to_collect",
        "confirm_criteria",
    ]
    return {
        "type": "object",
        "required": required,
        "conditionally_required_when_answered": conditional,
        "forbidden_fields": sorted(FORBIDDEN_SOURCE_FIELDS),
        "enrichment_label": ENRICHMENT_LABEL,
        "reviewer_statuses": list(ALLOWED_REVIEWER_STATUSES),
        "note": (
            "Đáp án 'answered' mà thiếu nhân quả (giả thuyết, cơ chế, 4M) hoặc "
            "bằng chứng (cần thu thập gì, tiêu chí xác nhận) thì bị từ chối. "
            "Không ghi bất kỳ trường nguồn LLM nào. reviewer_status mặc định "
            "'cho_chuyen_gia_phan_hoi'; chỉ chuyên gia thật mới được chuyển sang "
            "'chuyen_gia_da_phan_hoi'."
        ),
    }


def parse_answer_line(line: str) -> GoldenAnswer:
    """Parse one JSONL answer line into a validated GoldenAnswer."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise GoldenSchemaError("Dòng JSON không hợp lệ: %s" % exc)
    return GoldenAnswer.from_dict(data)


def parse_question_line(line: str) -> GoldenQuestion:
    """Parse one JSONL question line (the 'question' object) into a GoldenQuestion."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise GoldenSchemaError("Dòng JSON không hợp lệ: %s" % exc)
    if isinstance(data, dict) and "question" in data:
        data = data["question"]
    return GoldenQuestion.from_dict(data)
