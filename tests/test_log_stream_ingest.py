"""Tests cho log_stream_ingest: nap het khong cat, nhan dien dinh dang, resume."""

import pytest

from aios_habit.production_prediction import log_stream_ingest
from aios_habit.production_prediction.log_stream_ingest import (
    _nhan_dien_dinh_dang,
    nap_file_log,
    nap_stream,
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def _ghi_gia(records):
    return {"da_ghi": len(records), "bo_qua_rong": 0, "bi_cat": 0}


def test_nap_stream_khong_cat_50k():
    records = list(range(120_000))
    tien_trinh_calls = []
    ket_qua = nap_stream(
        iter(records),
        ghi_chunk=_ghi_gia,
        chunk=10_000,
        tien_trinh=tien_trinh_calls.append,
    )
    assert ket_qua["da_ghi"] == 120_000
    assert ket_qua["bi_cat"] == 0
    assert ket_qua["dot"] == 12
    assert len(tien_trinh_calls) == 12


def test_nap_stream_rong():
    assert nap_stream(iter([]), ghi_chunk=_ghi_gia)["da_ghi"] == 0


def test_nhan_dien_dinh_dang():
    assert _nhan_dien_dinh_dang(["2026-09-20T08:00:00,UNIT001,JIG-01,bowskew,0.12,mm,OK"]) == "jig_line"


def test_nap_file_log_jig_line(tmp_path):
    tep = tmp_path / "jig.log"
    tep.write_text(
        "\n".join(
            f"2026-09-20T08:00:{i:02d},UNIT{i:03d},JIG-01,bowskew,{0.10 + (i % 5) * 0.01:.2f},mm,OK"
            for i in range(60)
        ),
        encoding="utf-8",
    )
    from aios_habit.production_prediction.log_archive import MAC_DINH_KHO_PATH

    tien_trinh = [c for c in nap_file_log(tep, kho=tmp_path / "kho.sqlite", chunk_dong=25)]
    cuoi = tien_trinh[-1]
    assert cuoi["xong"] is True and cuoi["ok"] is True
    assert cuoi["dinh_dang"] == "jig_line"
    assert cuoi["da_ghi"] == 60
    assert cuoi["dot"] == 3  # 60 dong / chunk 25 -> 3 dot


def test_nap_file_log_resume(tmp_path):
    tep = tmp_path / "jig.log"
    tep.write_text(
        "\n".join(f"2026-09-20T08:00:00,UNIT{i:03d},JIG-01,bowskew,0.12,mm,OK" for i in range(40)),
        encoding="utf-8",
    )
    kho = tmp_path / "kho.sqlite"
    list(nap_file_log(tep, kho=kho, chunk_dong=100))
    # Nap lai: resume bo qua het vi file khong doi.
    lan2 = [c for c in nap_file_log(tep, kho=kho, chunk_dong=100)][-1]
    assert lan2["tiep_tuc_tu_dong"] == 40
    assert lan2["da_ghi"] == 0


def test_nap_file_khong_ton_tai():
    cuoi = [c for c in nap_file_log("/khong/co/file.log")][-1]
    assert cuoi["ok"] is False


def test_chat_action_tach_duong_dan():
    from aios_habit.chat_action_log_stream import _tach_duong_dan

    assert _tach_duong_dan('nạp file log "D:\\logs\\a.csv"') == "D:\\logs\\a.csv"
    assert _tach_duong_dan("đọc file log ./a.log") == "./a.log"
    assert _tach_duong_dan("nạp file log") is None


def test_chat_action_dang_ky():
    from aios_habit.chat_action import BUILTIN_ACTION_MODULES

    assert "aios_habit.chat_action_log_stream" in BUILTIN_ACTION_MODULES
