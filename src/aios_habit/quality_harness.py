"""Quality harness for answer lanes (ticket BUILD-QUALITY-HARNESS-PC0575).

Runs a list of questions through one lane (``cagent`` or ``rag``) via the
existing lane interfaces, scores each answer against a rubric, and exports
a CSV + JSON score table.

Only this module + its test may be created by this ticket. Lane code and UI
are never touched; lane callables are imported lazily at call time.

Compatible with Python 3.11. Standard library only.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Sequence

VALID_LANES = ("cagent", "rag")

# File extensions / markers treated as a source citation.
_CITATION_RE = re.compile(
    r"(\.pptx|\.xlsx|\.csv|\.pdf|\.docx|\.md\b|nguồn file|nguon file|nguồn:|http[s]?://|\[[^\]]+\])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QualityQuestion:
    """One question to measure."""

    qid: str
    question: str
    expected_keywords: List[str] = field(default_factory=list)
    requires_citation: bool = False


@dataclass(frozen=True)
class RubricCriterion:
    """One scoring criterion."""

    name: str
    max_score: float = 1.0
    description: str = ""


@dataclass(frozen=True)
class LaneAnswer:
    """Raw answer returned by a lane."""

    text: str = ""
    has_citation: bool = False


@dataclass(frozen=True)
class ScoredRow:
    """Scored result for one question."""

    qid: str
    question: str
    lane: str
    answer_text: str
    has_citation: bool
    scores: Dict[str, float]
    total: float


# Type of an injected lane: question text -> LaneAnswer.
LaneFn = Callable[[str], LaneAnswer]


def detect_citation(text: str) -> bool:
    """Return True when the answer carries a source citation marker."""
    return bool(_CITATION_RE.search(text or ""))


def _fold(text: str) -> str:
    return " ".join((text or "").lower().split())


def score_one(
    question: QualityQuestion,
    answer: LaneAnswer,
    rubric: Sequence[RubricCriterion],
) -> ScoredRow:
    """Score one answer against the rubric (pure, deterministic)."""
    text = (answer.text or "").strip()
    folded = _fold(text)
    has_citation = bool(answer.has_citation) or detect_citation(text)
    scores: Dict[str, float] = {}
    for criterion in rubric:
        lowered = criterion.name.lower()
        maximum = float(criterion.max_score)
        if "trich_dan" in lowered or "citation" in lowered or "nguon" in lowered:
            scores[criterion.name] = maximum if has_citation else 0.0
            continue
        keywords = [k for k in (question.expected_keywords or []) if k.strip()]
        if not text:
            scores[criterion.name] = 0.0
        elif not keywords:
            scores[criterion.name] = maximum if len(text) >= 20 else 0.0
        else:
            hits = sum(1 for kw in keywords if _fold(kw) in folded)
            ratio = hits / len(keywords)
            scores[criterion.name] = round(maximum * ratio, 2)
    total = round(sum(scores.values()), 2)
    return ScoredRow(
        qid=question.qid,
        question=question.question,
        lane="",
        answer_text=text,
        has_citation=has_citation,
        scores=scores,
        total=total,
    )


def _cagent_adapter(question: str) -> LaneAnswer:
    """Call the existing C-Agent interface (no lane code modified)."""
    from aios_habit.cagent_api import CAgentWorkspaceProviderClient

    client = CAgentWorkspaceProviderClient()
    try:
        text = client.generate(
            system_prompt="Trả lời ngắn gọn, kèm tên tài liệu nguồn khi có.",
            user_prompt=question,
        )
    except Exception:
        return LaneAnswer(text="", has_citation=False)
    return LaneAnswer(text=text or "", has_citation=detect_citation(text or ""))


def _rag_adapter(question: str) -> LaneAnswer:
    """Call the existing RAG-side helper without modifying lane code.

    Tries the local draft-fallback decision chain as the read-only RAG
    entry point; when no index/evidence is available it returns an empty
    answer so the harness scores it 0 instead of inventing a score.
    """
    try:
        from aios_habit.answer_draft_fallback import is_rag_usable
    except Exception:
        return LaneAnswer(text="", has_citation=False)
    # No live RAG index is wired into the harness by design (needs user
    # approval + backup per repo rules). Report unusable so scoring is 0.
    usable = is_rag_usable(rag_ok=False, answer_text="")
    if not usable:
        return LaneAnswer(text="", has_citation=False)
    return LaneAnswer(text="", has_citation=False)


def default_lane_fn(lane: str) -> LaneFn:
    """Return the built-in adapter for a lane name."""
    if lane == "cagent":
        return _cagent_adapter
    if lane == "rag":
        return _rag_adapter
    raise ValueError("Lane lạ: %r (chọn 'cagent' hoặc 'rag')." % (lane,))


def evaluate_questions(
    questions: Sequence[QualityQuestion],
    rubric: Sequence[RubricCriterion],
    lane: str,
    lane_fn: LaneFn | None = None,
) -> List[ScoredRow]:
    """Run every question through one lane and score each answer."""
    if lane not in VALID_LANES:
        raise ValueError("Lane lạ: %r (chọn 'cagent' hoặc 'rag')." % (lane,))
    if not rubric:
        raise ValueError("Rubric rỗng, cần ít nhất 1 tiêu chí.")
    runner = lane_fn or default_lane_fn(lane)
    rows: List[ScoredRow] = []
    for item in questions:
        answer = runner(item.question)
        scored = score_one(item, answer, rubric)
        rows.append(
            ScoredRow(
                qid=scored.qid,
                question=scored.question,
                lane=lane,
                answer_text=scored.answer_text,
                has_citation=scored.has_citation,
                scores=scored.scores,
                total=scored.total,
            )
        )
    return rows


def row_to_dict(row: ScoredRow) -> Dict:
    """Convert one scored row to a plain dict (for JSON export)."""
    return {
        "id": row.qid,
        "question": row.question,
        "lane": row.lane,
        "answer_text": row.answer_text,
        "has_citation": bool(row.has_citation),
        "scores": dict(row.scores),
        "total": float(row.total),
    }


def rows_to_csv_text(rows: Sequence[ScoredRow], criteria: Sequence[str]) -> str:
    """Render rows as CSV text (header + one line per question)."""
    import io

    header = ["id", "question", "lane", "total", "has_citation"] + list(criteria) + ["answer_preview"]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        preview = (row.answer_text or "").replace("\n", " ").strip()[:200]
        writer.writerow(
            [
                row.qid,
                row.question,
                row.lane,
                row.total,
                "có" if row.has_citation else "không",
            ]
            + [row.scores.get(name, 0.0) for name in criteria]
            + [preview]
        )
    return buf.getvalue()


def write_csv(rows: Sequence[ScoredRow], criteria: Sequence[str], path: str | Path) -> Path:
    """Write the score table to CSV (operational data: keep under local_cases/)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rows_to_csv_text(rows, criteria), encoding="utf-8")
    return out


def write_json(rows: Sequence[ScoredRow], path: str | Path) -> Path:
    """Write the score table to JSON (operational data: keep under local_cases/)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [row_to_dict(r) for r in rows]
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_questions(path: str | Path) -> List[QualityQuestion]:
    """Load questions from JSON (list of {id, question, expected_keywords, requires_citation})."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("questions", [])
    out: List[QualityQuestion] = []
    for entry in items:
        out.append(
            QualityQuestion(
                qid=str(entry.get("id", "")),
                question=str(entry.get("question", "")),
                expected_keywords=list(entry.get("expected_keywords", []) or []),
                requires_citation=bool(entry.get("requires_citation", False)),
            )
        )
    return out


def load_rubric(path: str | Path) -> List[RubricCriterion]:
    """Load rubric from JSON (list of {name, max_score, description})."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("criteria", [])
    out: List[RubricCriterion] = []
    for entry in items:
        out.append(
            RubricCriterion(
                name=str(entry.get("name", "")),
                max_score=float(entry.get("max_score", 1.0)),
                description=str(entry.get("description", "")),
            )
        )
    return out


def run_harness(
    questions_path: str | Path,
    rubric_path: str | Path,
    lane: str,
    output_dir: str | Path,
    lane_fn: LaneFn | None = None,
) -> List[ScoredRow]:
    """Full run: load inputs, evaluate one lane, write CSV + JSON, return rows."""
    questions = load_questions(questions_path)
    rubric = load_rubric(rubric_path)
    rows = evaluate_questions(questions, rubric, lane, lane_fn=lane_fn)
    criteria = [c.name for c in rubric]
    base = Path(output_dir)
    write_csv(rows, criteria, base / ("diem-" + lane + ".csv"))
    write_json(rows, base / ("diem-" + lane + ".json"))
    return rows
