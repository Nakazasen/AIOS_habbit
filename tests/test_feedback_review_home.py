"""Tests for FEEDBACK-REVIEW-HOME: SMA(20) trend alerts + periodic review."""

import pytest

from aios_habit import feedback_loop_home as loop
from aios_habit import feedback_review_home as review


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    loop.set_feedback_loop_override(True)
    yield
    loop.clear_feedback_loop_override()


def _rec(question, rating, day, device="may-aaa", topic="dieu_tra_loi"):
    return {
        "conversation_id": "c",
        "message_id": "m-%s-%s" % (day, question[:8]),
        "question": question,
        "answer_excerpt": "tra loi",
        "rating": rating,
        "reason": "Ly do che" if rating == "chua_huu_ich" else "",
        "device_id": device,
        "topic": topic,
        "created_at": "2026-09-%02dT08:00:00+07:00" % day,
    }


def _seed_stable_then_spike(question, spike_days=3, base_days=20):
    records = []
    for day in range(1, base_days + 1):
        for i in range(4):
            records.append(_rec(question, "huu_ich", day, device="may-%d" % (i % 3)))
        records.append(_rec(question, "chua_huu_ich", day, device="may-aaa"))
    for day in range(base_days + 1, base_days + spike_days + 1):
        for i in range(5):
            records.append(_rec(question, "chua_huu_ich", day, device="may-%d" % (i % 3)))
    return records


def test_sma_20_of_0_to_19_is_9_5():
    assert review.sma(list(range(20)), 20) == 9.5


def test_sigma_flat_series_is_zero():
    assert review.sigma([0.2] * 20, 20) == 0.0
    assert review.sigma([], 20) == 0.0


def test_short_series_marked_preliminary():
    summary = review.sma_sigma([0.5, 0.7], 20)
    assert summary["so_bo"] is True
    assert summary["diem_da_dung"] == 2
    assert summary["sma"] == pytest.approx(0.6)


def test_single_spike_does_not_alert():
    values = [0.2] * 20 + [1.0]
    details = review.detect_anomalies(values, window=20, k=2.0)
    flags = [row["bat_thuong"] for row in details]
    assert flags[-1] is True
    assert review.has_trend_alert(flags) is False


def test_three_consecutive_spikes_alert():
    values = [0.2] * 20 + [1.0, 1.0, 1.0]
    details = review.detect_anomalies(values, window=20, k=2.0)
    flags = [row["bat_thuong"] for row in details]
    assert flags[-3:] == [True, True, True]
    assert review.has_trend_alert(flags) is True


def test_three_in_last_five_alerts_without_consecutive_run():
    assert review.has_trend_alert([True, False, True, False, True]) is True
    assert review.has_trend_alert([True, False, False, False, False]) is False
    assert review.has_trend_alert([]) is False


def test_daily_rates_group_by_question_and_topic():
    records = [
        _rec("Loi JAM4709 ket giay?", "chua_huu_ich", 1),
        _rec("Loi JAM4709 ket giay?", "huu_ich", 1),
        _rec("Log jig LSU?", "huu_ich", 2, topic="lsu"),
    ]
    daily = review.build_daily_rates(records)
    key = loop.question_key("Loi JAM4709 ket giay?")
    assert daily["theo_cau"][key][0]["ti_le_che"] == 0.5
    assert daily["theo_chu_de"]["lsu"][0]["ti_le_che"] == 0.0


def test_review_disabled_when_flag_off(tmp_path):
    loop.set_feedback_loop_override(False)
    result = review.run_periodic_review([], output_path=str(tmp_path / "r.md"))
    assert result["ok"] is False
    assert result["tat_co"] is True
    assert not (tmp_path / "r.md").exists()


def test_review_trend_end_to_end_with_report(tmp_path):
    bad_q = "Loi JAM4709 ket giay la gi?"
    ok_q = "He thong MOM Opcenter la gi?"
    records = _seed_stable_then_spike(bad_q, spike_days=3)
    records += [_rec(ok_q, "huu_ich", day, topic="mom") for day in range(1, 24)]
    # One single bad day for a third question must not alert.
    records += [_rec("Cau on dinh?", "huu_ich", day) for day in range(1, 23)]
    records += [_rec("Cau on dinh?", "chua_huu_ich", 23, device="may-bbb")]
    out = tmp_path / "review.md"
    result = review.run_periodic_review(records, output_path=str(out))
    assert result["ok"] is True
    alerted = [row["khoa_cau_hoi"] for row in result["canh_bao_cau"]]
    assert loop.question_key(bad_q)[:120] in alerted
    assert loop.question_key("Cau on dinh?")[:120] not in alerted
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "Bang xep hang" in body
    assert "Canh bao xu huong" in body
    assert "De xuat" in body
    assert result["de_xuat"], "expected prioritized proposals"

def test_short_series_report_notes_preliminary(tmp_path):
    records = [_rec("Cau ngan?", "huu_ich", 5), _rec("Cau ngan?", "chua_huu_ich", 6)]
    out = tmp_path / "ngan.md"
    result = review.run_periodic_review(records, output_path=str(out))
    assert result["ok"] is True
    body = out.read_text(encoding="utf-8")
    assert "Chuoi du lieu" in body
    assert "so bo" in body
    assert result["canh_bao_cau"] == []

def test_cli_flag_off_exits_zero_without_file(tmp_path):
    loop.set_feedback_loop_override(False)
    out = tmp_path / "tat.md"
    assert review.main(["--dau-ra", str(out)]) == 0
    assert not out.exists()


def test_cli_main_writes_report(tmp_path, monkeypatch, capsys):
    records = _seed_stable_then_spike("Loi ket giay?", spike_days=3)
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    from aios_habit import answer_feedback

    for record in records[:30]:
        answer_feedback.record_feedback(
            record["conversation_id"],
            record["message_id"],
            record["question"],
            record["answer_excerpt"],
            record["rating"],
            reason=record["reason"] or "Ly do",
            device_id=record["device_id"],
            topic=record["topic"],
        )
    out = tmp_path / "cli.md"
    code = review.main(["--cua-so", "20", "--k", "2.0", "--dau-ra", str(out)])
    assert code == 0
    assert out.exists()
    assert "Da ghi bao cao" in capsys.readouterr().out
