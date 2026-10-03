"""Vong lap tu cai thien tu feedback goi y (UX-INTERVIEW-FEEDBACK, item 3).

Feedback "sai" / "mot_phan" cua chuyen gia duoc luu thanh BAI HOC co truy vet:
tinh huong -> loi -> cach sua. Khi gap tinh huong tuong tu, he thong nhan
dien bang fingerprint/tu khoa (don gian, khong embedding) de khong lap lai
loi cu.

Metric do duoc: ti le lap lai loi sau feedback theo thoi gian — ky vong GIAM
DAN. Ham `repetition_rates()` + `metric_trend()` tinh metric nay tren du
lieu mau hay du lieu that; test chung minh metric chay duoc.

Luu JSONL tai `local_cases/` (feedback store cuc bo) — KHONG BAO GIO ghi vao
kho tri thuc chinh. Thu muc local_cases ghi de duoc qua bien moi truong
AIOS_LOCAL_CASES_DIR (dung cho test).

Tuong thich Python 3.11.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

LESSONS_FILE_NAME = "improvement_lessons.jsonl"
METRICS_FILE_NAME = "improvement_metrics.jsonl"

MAX_SITUATION_CHARS = 2000
MAX_TEXT_CHARS = 4000

# Simple Vietnamese stopwords for keyword fingerprinting (function words only;
# domain terms like "board", "sensor", "F100" are intentionally kept).
_STOPWORDS = frozenset(
    {
        "là", "la", "của", "cua", "và", "va", "các", "cac", "những", "nhung",
        "một", "mot", "như", "nhu", "với", "voi", "cho", "để", "de", "trong",
        "trên", "tren", "dưới", "duoi", "khi", "nếu", "neu", "thì", "thi",
        "đã", "da", "đang", "dang", "sẽ", "se", "có", "co", "không", "khong",
        "rất", "rat", "này", "nay", "đó", "do", "kia", "ấy", "ay", "bị", "bi",
        "được", "duoc", "cần", "can", "nên", "nen", "phải", "phai", "hay",
        "hoặc", "hoac", "nhưng", "nhung", "mà", "ma", "ở", "o", "từ", "tu",
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are",
        "was", "were", "it", "this", "that",
    }
)

_WORD_RE = re.compile(r"[0-9a-zà-ỹ]+", re.IGNORECASE)

# Similarity gate: two situations are "similar" when their keyword sets
# overlap enough. Tunable; 0.3 is deliberately conservative to avoid noise.
DEFAULT_SIMILARITY_THRESHOLD = 0.3


class ImprovementError(ValueError):
    """Raised when a lesson or metric event cannot be recorded."""


def _local_cases_dir() -> Path:
    base = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    return Path(base) if base else Path.cwd() / "local_cases"


def lessons_file() -> Path:
    return _local_cases_dir() / LESSONS_FILE_NAME


def metrics_file() -> Path:
    return _local_cases_dir() / METRICS_FILE_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def situation_keywords(text: str) -> Set[str]:
    """Extract significant keywords from a situation description.

    Lowercase, keep unicode word chars (Vietnamese intact), drop stopwords,
    drop single chars and pure numbers. No embedding, fully deterministic.
    """
    words = _WORD_RE.findall(str(text or "").lower())
    return {
        w
        for w in words
        if len(w) >= 2 and w not in _STOPWORDS and not w.isdigit()
    }


def situation_fingerprint(text: str) -> str:
    """Stable fingerprint of a situation: sha256 of sorted keywords."""
    keywords = sorted(situation_keywords(text))
    return hashlib.sha256("|".join(keywords).encode("utf-8")).hexdigest()


def keyword_jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity of two keyword sets (0.0–1.0)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class Lesson:
    """One traceable lesson: situation -> mistake -> correction.

    Built from a "sai"/"mot_phan" suggestion feedback record; never written
    to the knowledge store (lives in local_cases only).
    """

    lesson_id: str
    situation_text: str
    situation_fingerprint: str
    keywords: Tuple[str, ...]
    loi: str  # what was wrong (expert's reason)
    nguyen_nhan: str  # the true cause (expert's ground truth)
    cach_sua: str  # corrected content (expert's rewrite)
    source_suggestion_id: str = ""
    source_verdict: str = ""
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict:
        return {
            "lesson_id": self.lesson_id,
            "situation_text": self.situation_text,
            "situation_fingerprint": self.situation_fingerprint,
            "keywords": list(self.keywords),
            "loi": self.loi,
            "nguyen_nhan": self.nguyen_nhan,
            "cach_sua": self.cach_sua,
            "source_suggestion_id": self.source_suggestion_id,
            "source_verdict": self.source_verdict,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: Dict) -> "Lesson":
        return Lesson(
            lesson_id=str(data.get("lesson_id", "")),
            situation_text=str(data.get("situation_text", "")),
            situation_fingerprint=str(data.get("situation_fingerprint", "")),
            keywords=tuple(str(k) for k in (data.get("keywords") or [])),
            loi=str(data.get("loi", "")),
            nguyen_nhan=str(data.get("nguyen_nhan", "")),
            cach_sua=str(data.get("cach_sua", "")),
            source_suggestion_id=str(data.get("source_suggestion_id", "")),
            source_verdict=str(data.get("source_verdict", "")),
            created_at=str(data.get("created_at", "")),
        )


def lesson_from_suggestion_feedback(feedback: Dict, situation_text: str = "") -> Lesson:
    """Build a Lesson from a "sai"/"mot_phan" suggestion feedback record.

    `feedback` is a record from suggestion_feedback.record_feedback with the
    three mandatory fields (reason/true_cause/correction or the Vietnamese
    keys). `situation_text` defaults to the suggestion content + context.
    """
    verdict = str(feedback.get("verdict") or feedback.get("rating") or "").strip()
    if verdict not in ("sai", "mot_phan"):
        raise ImprovementError(
            "Chỉ feedback 'sai' / 'một phần' mới tạo được bài học (nhận: '%s')."
            % verdict
        )
    situation = str(
        situation_text
        or feedback.get("situation_text")
        or "%s || %s"
        % (
            feedback.get("content", feedback.get("suggestion_text", "")),
            feedback.get("context", ""),
        )
    ).strip()[:MAX_SITUATION_CHARS]
    if not situation:
        raise ImprovementError("Không xác định được tình huống để tạo bài học.")
    loi = str(feedback.get("reason") or feedback.get("ly_do") or "").strip()
    nguyen_nhan = str(
        feedback.get("true_cause") or feedback.get("nguyen_nhan_that") or ""
    ).strip()
    cach_sua = str(
        feedback.get("correction") or feedback.get("noi_dung_nan_lai") or ""
    ).strip()
    missing = []
    if not loi:
        missing.append("lý do")
    if not nguyen_nhan:
        missing.append("nguyên nhân thật")
    if not cach_sua:
        missing.append("nội dung nắn lại")
    if missing:
        raise ImprovementError(
            "Feedback thiếu trường bắt buộc để tạo bài học: %s." % ", ".join(missing)
        )
    keywords = situation_keywords(situation)
    return Lesson(
        lesson_id="LES-%s" % uuid.uuid4().hex[:8].upper(),
        situation_text=situation,
        situation_fingerprint=situation_fingerprint(situation),
        keywords=tuple(sorted(keywords)),
        loi=loi[:MAX_TEXT_CHARS],
        nguyen_nhan=nguyen_nhan[:MAX_TEXT_CHARS],
        cach_sua=cach_sua[:MAX_TEXT_CHARS],
        source_suggestion_id=str(
            feedback.get("suggestion_id", feedback.get("feedback_key", ""))
        ),
        source_verdict=verdict,
    )


class LessonStore:
    """Append-only JSONL store of lessons in local_cases (never the KB)."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else lessons_file()

    def add(self, lesson: Lesson) -> Lesson:
        if not lesson.lesson_id:
            raise ImprovementError("Bài học thiếu lesson_id.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(lesson.to_dict(), ensure_ascii=False) + "\n")
        return lesson

    def all(self) -> List[Lesson]:
        if not self.path.exists():
            return []
        lessons: List[Lesson] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    lessons.append(Lesson.from_dict(json.loads(line)))
                except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                    continue
        return lessons

    def find_similar(
        self,
        situation_text: str,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> List[Tuple[Lesson, float]]:
        """Find lessons whose situation is similar (keyword Jaccard).

        Returns (lesson, score) sorted by score desc. Exact fingerprint
        matches score 1.0 and always pass the threshold.
        """
        query_fp = situation_fingerprint(situation_text)
        query_kw = situation_keywords(situation_text)
        hits: List[Tuple[Lesson, float]] = []
        for lesson in self.all():
            if lesson.situation_fingerprint == query_fp:
                hits.append((lesson, 1.0))
                continue
            score = keyword_jaccard(query_kw, set(lesson.keywords))
            if score >= threshold:
                hits.append((lesson, round(score, 3)))
        hits.sort(key=lambda item: item[1], reverse=True)
        return hits


def consult_lessons(
    situation_text: str,
    store: Optional[LessonStore] = None,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> List[Dict]:
    """Before answering a similar situation: return known lessons so the
    old mistake is not repeated. UI-agnostic; the chat UI shows these as
    "bài học đã rút ra" next to the answer box."""
    store = store or LessonStore()
    return [
        {
            "lesson_id": lesson.lesson_id,
            "do_tuong_dong": score,
            "tinh_huong": lesson.situation_text[:300],
            "loi_truoc_day": lesson.loi[:300],
            "nguyen_nhan_that": lesson.nguyen_nhan[:300],
            "cach_sua": lesson.cach_sua[:500],
        }
        for lesson, score in store.find_similar(situation_text, threshold)
    ]


# ---------------------------------------------------------------------------
# Metric: error-repetition rate over time (must trend DOWN)
# ---------------------------------------------------------------------------

def record_repetition_event(
    suggestion_id: str,
    verdict: str,
    repeated: bool,
    period: str = "",
    path: Optional[Path] = None,
) -> Dict:
    """Record one feedback event for the metric.

    `repeated` = True when this "sai"/"mot_phan" feedback hits a situation
    already covered by an older lesson (i.e. the mistake was repeated
    despite the lesson). `period` groups events (default: today, YYYY-MM-DD).
    """
    period = str(period or "").strip() or datetime.now().strftime("%Y-%m-%d")
    event = {
        "suggestion_id": str(suggestion_id or ""),
        "verdict": str(verdict or ""),
        "repeated": bool(repeated),
        "period": period,
        "created_at": _now_iso(),
    }
    target = Path(path) if path else metrics_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def _read_events(path: Optional[Path] = None) -> List[Dict]:
    target = Path(path) if path else metrics_file()
    if not target.exists():
        return []
    events: List[Dict] = []
    with target.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
    return events


def repetition_rates(
    events: Optional[Sequence[Dict]] = None, path: Optional[Path] = None
) -> List[Dict]:
    """Aggregate repetition rate per period, sorted by period ascending.

    Returns [{"ky": period, "tong": n, "lap_lai": k, "ti_le": k/n}].
    Only "sai"/"mot_phan" feedback counts as an opportunity to repeat.
    """
    rows = list(events) if events is not None else _read_events(path)
    buckets: Dict[str, Dict[str, int]] = {}
    for event in rows:
        if str(event.get("verdict", "")) not in ("sai", "mot_phan"):
            continue
        period = str(event.get("period", ""))
        bucket = buckets.setdefault(period, {"tong": 0, "lap_lai": 0})
        bucket["tong"] += 1
        if event.get("repeated"):
            bucket["lap_lai"] += 1
    result = []
    for period in sorted(buckets):
        bucket = buckets[period]
        total = bucket["tong"]
        result.append(
            {
                "ky": period,
                "tong": total,
                "lap_lai": bucket["lap_lai"],
                "ti_le": round(bucket["lap_lai"] / total, 3) if total else 0.0,
            }
        )
    return result


def metric_trend(rates: Sequence[Dict]) -> str:
    """Direction of the repetition-rate metric: "giam_dan" (improving),
    "khong_giam" (flat or worsening), or "khong_du_du_lieu" (< 2 periods).

    Compares the mean rate of the second half of periods against the first
    half — a simple, explainable trend check, no statistics machinery.
    """
    values = [float(r.get("ti_le", 0.0)) for r in rates]
    if len(values) < 2:
        return "khong_du_du_lieu"
    mid = len(values) // 2
    first = sum(values[:mid]) / len(values[:mid])
    second = sum(values[mid:]) / len(values[mid:])
    if second < first:
        return "giam_dan"
    return "khong_giam"


def improvement_overview(
    store: Optional[LessonStore] = None, path: Optional[Path] = None
) -> Dict:
    """One-call review-loop summary for the UI/report: lesson count,
    per-period repetition rates, and the trend direction."""
    store = store or LessonStore()
    rates = repetition_rates(path=path)
    return {
        "so_bai_hoc": len(store.all()),
        "ti_le_lap_lai_theo_ky": rates,
        "xu_huong": metric_trend(rates),
    }
