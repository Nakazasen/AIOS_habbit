"""Tests for quality_harness (mock lanes only, no real network)."""

from aios_habit import quality_harness as harness


def _rubric():
    return [
        harness.RubricCriterion(name="chinh_xac", max_score=2.0),
        harness.RubricCriterion(name="day_du", max_score=1.0),
        harness.RubricCriterion(name="trich_dan", max_score=1.0),
    ]


def _question():
    return harness.QualityQuestion(
        qid="Q1",
        question="SIM tape dày bao nhiêu?",
        expected_keywords=["40", "119.h2"],
        requires_citation=True,
    )


def test_full_marks_when_keywords_and_citation_present():
    answer = harness.LaneAnswer(
        text="Dán SIM tape dày 40 µm tại điểm 119.h2. Nguồn file: bao_cao.pptx",
        has_citation=True,
    )
    row = harness.score_one(_question(), answer, _rubric())
    assert row.scores["chinh_xac"] == 2.0
    assert row.scores["day_du"] == 1.0
    assert row.scores["trich_dan"] == 1.0
    assert row.has_citation is True
    assert row.total == 4.0


def test_citation_criterion_zero_without_citation():
    answer = harness.LaneAnswer(text="Dán SIM tape dày 40 µm tại 119.h2.", has_citation=False)
    row = harness.score_one(_question(), answer, _rubric())
    assert row.scores["trich_dan"] == 0.0
    assert row.has_citation is False


def test_empty_answer_scores_zero():
    answer = harness.LaneAnswer(text="", has_citation=False)
    row = harness.score_one(_question(), answer, _rubric())
    assert row.total == 0.0
    assert all(v == 0.0 for v in row.scores.values())


def test_evaluate_routes_to_chosen_lane():
    seen = []

    def fake_lane(question_text: str) -> harness.LaneAnswer:
        seen.append(question_text)
        return harness.LaneAnswer(text="Đáp án giả có 40 và 119.h2. Xem file a.csv")

    questions = [_question()]
    rows = harness.evaluate_questions(questions, _rubric(), "cagent", lane_fn=fake_lane)
    assert len(rows) == 1
    assert rows[0].lane == "cagent"
    assert seen == ["SIM tape dày bao nhiêu?"]
    rows_rag = harness.evaluate_questions(questions, _rubric(), "rag", lane_fn=fake_lane)
    assert rows_rag[0].lane == "rag"


def test_csv_json_roundtrip(tmp_path):
    questions = [_question()]
    rows = harness.evaluate_questions(
        questions,
        _rubric(),
        "rag",
        lane_fn=lambda q: harness.LaneAnswer(text="Đáp án đủ 40, 119.h2. File b.xlsx"),
    )
    criteria = [c.name for c in _rubric()]
    csv_path = harness.write_csv(rows, criteria, tmp_path / "diem-rag.csv")
    json_path = harness.write_json(rows, tmp_path / "diem-rag.json")
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "trich_dan" in csv_text.splitlines()[0]
    assert "Q1" in csv_text
    import json

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload[0]["id"] == "Q1"
    assert payload[0]["has_citation"] is True
    assert payload[0]["scores"]["trich_dan"] == 1.0
