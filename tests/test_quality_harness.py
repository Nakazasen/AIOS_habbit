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


def test_normalize_text_thousands_and_decimals():
    norm = harness.normalize_text_for_eval
    # Thousand separators stripped
    assert norm("48.384 vòng/phút") == "48384 vòng/phút"
    assert norm("40.042") == "40042"
    assert norm("3.153 record") == "3153 record"
    # Decimals with comma converted to dot
    assert norm("-0,81 dot") == "-0.81 dot"
    assert norm("1,93") == "1.93"
    assert norm("49,49%") == "49.49%"
    # Preserve real decimals and dates
    assert norm("0.002") == "0.002"
    assert norm("1.15 mm") == "1.15 mm"
    assert norm("1.24") == "1.24"
    assert norm("2019.01.18") == "2019.01.18"


def test_normalize_text_units_and_ranges():
    norm = harness.normalize_text_for_eval
    # Time unit
    assert norm("3 giây") == "3 s"
    assert norm("3 giay") == "3 s"
    assert norm("6 giây") == "6 s"
    # Temperature range & unit
    assert norm("0 - 15 độ C") == "0–15°C"
    assert norm("0-15°C") == "0–15°C"
    assert norm("0–15°C") == "0–15°C"


def test_score_one_with_normalized_formats():
    rubric = [harness.RubricCriterion(name="chinh_xac", max_score=2.0)]
    q_speed = harness.QualityQuestion(
        qid="Q_speed",
        question="Tốc độ quay là bao nhiêu?",
        expected_keywords=["48.384 vòng/phút", "40.042 vòng/phút"],
    )
    # Answer writes without thousand separator dot: 48384 and 40042
    ans_correct = harness.LaneAnswer(text="Tốc độ là 48384 vòng/phút và 40042 vòng/phút.")
    row = harness.score_one(q_speed, ans_correct, rubric)
    assert row.scores["chinh_xac"] == 2.0
    assert row.total == 2.0


def test_score_one_does_not_change_when_answer_truly_wrong():
    rubric = [harness.RubricCriterion(name="chinh_xac", max_score=2.0)]
    q_speed = harness.QualityQuestion(
        qid="Q_speed",
        question="Tốc độ quay là bao nhiêu?",
        expected_keywords=["48.384 vòng/phút", "40.042 vòng/phút"],
    )
    # Truly wrong answers score 0.0
    ans_wrong = harness.LaneAnswer(text="Tốc độ là 12000 vòng/phút và 15000 vòng/phút.")
    row_wrong = harness.score_one(q_speed, ans_wrong, rubric)
    assert row_wrong.scores["chinh_xac"] == 0.0
    assert row_wrong.total == 0.0

    q_temp = harness.QualityQuestion(
        qid="Q_temp",
        question="Nhiệt độ bảo quản?",
        expected_keywords=["0–15°C"],
    )
    ans_temp_wrong = harness.LaneAnswer(text="Bảo quản ở nhiệt độ phòng 25 - 30 độ C.")
    row_temp_wrong = harness.score_one(q_temp, ans_temp_wrong, rubric)
    assert row_temp_wrong.scores["chinh_xac"] == 0.0
    assert row_temp_wrong.total == 0.0
