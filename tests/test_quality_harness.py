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
    # Thousand separators stripped (dot and comma)
    assert norm("48.384 vòng/phút") == "48384 vòng/phút"
    assert norm("40.042") == "40042"
    assert norm("48,384 vòng/phút") == "48384 vòng/phút"
    assert norm("40,042") == "40042"
    assert norm("3.153 record") == "3153 record"
    assert norm("3,153 record") == "3153 record"
    # Decimals with comma converted to dot
    assert norm("-0,81 dot") == "-0.81 dot"
    assert norm("1,93") == "1.93"
    assert norm("49,49%") == "49.49%"
    assert norm("43,9%") == "43.9%"
    # Preserve real decimals and dates
    assert norm("0.002") == "0.002"
    assert norm("0,506") == "0.506"
    assert norm("1.15 mm") == "1.15 mm"
    assert norm("1.24") == "1.24"
    assert norm("2019.01.18") == "2019.01.18"


def test_normalize_math_delimiters_and_spacing():
    norm = harness.normalize_text_for_eval
    # Math dollar delimiters removed
    assert norm("$48384$ vòng/phút") == "48384 vòng/phút"
    assert norm("$$40042$$ vòng/phút") == "40042 vòng/phút"
    assert norm("$48.384$ vòng/phút") == "48384 vòng/phút"
    assert norm("$48384$") == "48384"
    assert norm("\\(48384\\)") == "48384"
    assert norm("\\[48384\\]") == "48384"
    assert norm("`48384`") == "48384"
    assert norm("`0`") == "0"
    # Spacing normalized between number and unit/word
    assert norm("48384vòng/phút") == "48384 vòng/phút"
    assert norm("70dot") == "70 dot"
    assert norm("1.15mm") == "1.15 mm"
    assert norm("40µm") == "40 µm"


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


def test_score_one_positive_cases_recovers_falsely_penalized_formats():
    """Positive test cases: correct answers penalized only due to formatting are recovered."""
    rubric = [harness.RubricCriterion(name="chinh_xac", max_score=2.0)]
    q_speed = harness.QualityQuestion(
        qid="Q0652",
        question="Hai loại Motor Polygon được tài liệu phân biệt như thế nào?",
        expected_keywords=["48.384 vòng/phút", "40.042 vòng/phút"],
    )

    # 1. LaTeX math dollar format ($48384$ and $40042$ like in PC0575)
    ans_latex = harness.LaneAnswer(
        text="Đời cao có tốc độ quay $48384$ vòng/phút, đời thấp có tốc độ quay $40042$ vòng/phút."
    )
    row_latex = harness.score_one(q_speed, ans_latex, rubric)
    assert row_latex.scores["chinh_xac"] == 2.0
    assert row_latex.total == 2.0

    # 2. Unspaced unit format (48384vòng/phút and 40042vòng/phút)
    ans_unspaced = harness.LaneAnswer(
        text="Đời cao có tốc độ quay: 48384vòng/phút; đời thấp có tốc độ quay: 40042vòng/phút."
    )
    row_unspaced = harness.score_one(q_speed, ans_unspaced, rubric)
    assert row_unspaced.scores["chinh_xac"] == 2.0
    assert row_unspaced.total == 2.0

    # 3. English comma thousand separator (48,384 and 40,042)
    ans_comma = harness.LaneAnswer(
        text="Đời cao đạt 48,384 vòng/phút, đời thấp đạt 40,042 vòng/phút."
    )
    row_comma = harness.score_one(q_speed, ans_comma, rubric)
    assert row_comma.scores["chinh_xac"] == 2.0
    assert row_comma.total == 2.0

    # 4. Decimal point vs comma normalization (43.9% vs 43,9% in Q0671)
    q_rate = harness.QualityQuestion(
        qid="Q0671",
        question="Tỷ lệ NG?",
        expected_keywords=["43,9%"],
    )
    ans_rate = harness.LaneAnswer(text="Tỷ lệ phát sinh lỗi là 43.9%.")
    row_rate = harness.score_one(q_rate, ans_rate, rubric)
    assert row_rate.scores["chinh_xac"] == 2.0

    # 5. Connected unit normalization (70dot vs 70 dot in Q0699)
    q_dot = harness.QualityQuestion(
        qid="Q0699",
        question="Ngưỡng sai lệch?",
        expected_keywords=["70 dot"],
    )
    ans_dot = harness.LaneAnswer(text="Sai lệch vượt quá 70dot sẽ báo NG.")
    row_dot = harness.score_one(q_dot, ans_dot, rubric)
    assert row_dot.scores["chinh_xac"] == 2.0


def test_score_one_negative_cases_rejects_arithmetically_different_values():
    """Negative test cases: arithmetically incorrect values must remain rejected after normalization."""
    rubric = [harness.RubricCriterion(name="chinh_xac", max_score=2.0)]
    q_speed = harness.QualityQuestion(
        qid="Q0652",
        question="Hai loại Motor Polygon được tài liệu phân biệt như thế nào?",
        expected_keywords=["48.384 vòng/phút", "40.042 vòng/phút"],
    )

    # Completely wrong numbers wrapped in math delimiters ($12000$ and $15000$)
    ans_wrong_math = harness.LaneAnswer(text="Tốc độ là $12000$ vòng/phút và $15000$ vòng/phút.")
    row_wrong_math = harness.score_one(q_speed, ans_wrong_math, rubric)
    assert row_wrong_math.scores["chinh_xac"] == 0.0
    assert row_wrong_math.total == 0.0

    # Slightly off numbers ($48385$ and $40043$)
    ans_off_by_one = harness.LaneAnswer(text="Tốc độ là 48385 vòng/phút và 40043 vòng/phút.")
    row_off_by_one = harness.score_one(q_speed, ans_off_by_one, rubric)
    assert row_off_by_one.scores["chinh_xac"] == 0.0
    assert row_off_by_one.total == 0.0

    # Decimal tolerance mismatch (0.003 vs 0.002)
    q_tol = harness.QualityQuestion(
        qid="Q0685",
        question="Dung sai đo?",
        expected_keywords=["0.002", "0.015"],
    )
    ans_tol_wrong = harness.LaneAnswer(text="Dung sai là 0.003 và 0.018.")
    row_tol_wrong = harness.score_one(q_tol, ans_tol_wrong, rubric)
    assert row_tol_wrong.scores["chinh_xac"] == 0.0

    # Temperature wrong (25 - 30 độ C vs 0–15°C)
    q_temp = harness.QualityQuestion(
        qid="Q_temp",
        question="Nhiệt độ bảo quản?",
        expected_keywords=["0–15°C"],
    )
    ans_temp_wrong = harness.LaneAnswer(text="Bảo quản ở nhiệt độ phòng 25 - 30 độ C.")
    row_temp_wrong = harness.score_one(q_temp, ans_temp_wrong, rubric)
    assert row_temp_wrong.scores["chinh_xac"] == 0.0
    assert row_temp_wrong.total == 0.0


def test_eval_fixtures_loadable_and_reproducible():
    from pathlib import Path
    fixtures_dir = Path(__file__).parent / "fixtures" / "eval"
    q_file = fixtures_dir / "lsu_quality_50_questions.json"
    r_file = fixtures_dir / "lsu_quality_rubric.json"
    assert q_file.is_file(), "lsu_quality_50_questions.json must exist in fixtures/eval"
    assert r_file.is_file(), "lsu_quality_rubric.json must exist in fixtures/eval"

    questions = harness.load_questions(q_file)
    assert len(questions) == 50, "Evaluation fixture must contain exactly 50 questions"

    q_map = {q.qid: q for q in questions}
    # Verify the 4 normalized questions from RUBRIC-NORMALIZE ticket
    assert q_map["Q0630"].expected_keywords == ["quét ngang", "quay drum"]
    assert q_map["Q0635"].expected_keywords == ["quang lượng tâm", "vùng biên", "nhạt màu"]
    assert q_map["Q0674"].expected_keywords == ["không bất thường", "không thay đổi"]
    assert q_map["Q0708"].expected_keywords == ["1.15", "1.24"]

    rubric = harness.load_rubric(r_file)
    assert len(rubric) == 2
    r_names = {r.name: r.max_score for r in rubric}
    assert r_names == {"chinh_xac": 2.0, "trich_dan": 1.0}

