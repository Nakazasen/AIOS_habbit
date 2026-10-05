"""Test bo chuyen doi log JIG BEAM (ve RT-JIGBEAM-ADAPTER-HOME).

Du lieu that: ``2026_08_Master.csv`` (677 cot, 132 dong, JIG BEAM) tren may
nha. Test du lieu that tu bo qua neu may khong co file (giong test_j1_rt).
Test tong hop bang file gia lap nho luon chay de khoa hanh vi.
"""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

import pytest

from aios_habit.production_prediction.jigbeam_log_adapter import (
    FLAG_ENV_KEY,
    doc_log_jigbeam,
    la_log_jigbeam,
    phat_lai_csv_jigbeam,
)
from aios_habit.production_prediction.rt_replay import (
    NHAN_MO_PHONG,
    gui_lo_len_server,
    phat_lai_csv_tu_dong,
)
from aios_habit.production_prediction.stream_api import (
    STREAM_PATH,
    StreamBuffer,
    StreamListener,
    parse_stream_record,
)

DU_LIEU_THAT_WIN = Path(
    r"C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log"
    r"\2ND-1002_JIG BEAM\2026_08_Master.csv"
)
DU_LIEU_THAT_LINUX = Path(
    "/home/hatch/workspace/aios_data/lsu/Iris LSU/thu nghiem 6pcs do thong so va log"
    "/2ND-1002_JIG BEAM/2026_08_Master.csv"
)


def _duong_dan_that() -> Path | None:
    if DU_LIEU_THAT_WIN.is_file():
        return DU_LIEU_THAT_WIN
    if DU_LIEU_THAT_LINUX.is_file():
        return DU_LIEU_THAT_LINUX
    return None


co_du_lieu_that = pytest.mark.skipif(
    _duong_dan_that() is None, reason="Thieu file JIG BEAM that tren may nay"
)


def _tep_jigbeam_gia(tmp_path: Path) -> Path:
    tep = tmp_path / "jigbeam_gia.csv"
    with tep.open("w", encoding="utf-8", newline="") as f:
        viet = csv.writer(f)
        viet.writerow([
            "DATE", "TIME", "JigNumber", "S/N", "LD Lot No", "TotalJudge",
            "Black_Judge", "Mode", "TaktTime", "XyPosX_B", "XyPosY_B",
        ] + ["CotPhu%d" % i for i in range(12)])
        viet.writerow([
            "2026/08/01", "6:03:59", "#1", "SN001", "L1", "OK",
            "OK", "Master", "145", "5644", "3319",
        ] + ["1"] * 12)
        viet.writerow([
            "2026/08/01", "6:05:39", "#1", "SN002", "L1", "NG",
            "NG", "Master", "89", "5650", "3320",
        ] + ["2"] * 12)
        viet.writerow([
            "2026/08/01", "6:07:34", "#1", "SN003", "L1", "OK",
            "OK", "Master", "103", "5655", "3321",
        ] + ["3"] * 12)
    return tep


def test_nhan_dien_tieu_de_jigbeam(tmp_path):
    tep = _tep_jigbeam_gia(tmp_path)
    with tep.open("r", encoding="utf-8", newline="") as f:
        tieu_de = next(csv.reader(f))
    assert la_log_jigbeam(tieu_de) is True
    assert la_log_jigbeam(["DATE", "TIME", "S/N"]) is False


def test_doc_file_gia_du_3_dong(tmp_path):
    ket_qua = doc_log_jigbeam(_tep_jigbeam_gia(tmp_path))
    assert ket_qua.thieu_cot == []
    assert ket_qua.so_dong == 3
    hop_le = ket_qua.ban_ghi_hop_le()
    assert len(hop_le) > 0
    takttime = [b for b in hop_le if b.metric_name == "TAKTTIME"]
    assert len(takttime) == 3
    assert sorted(b.value for b in takttime) == [89.0, 103.0, 145.0]


def test_phat_lai_mac_dinh_moi_dong_1_ban_tin(tmp_path):
    cac_ban_tin = list(phat_lai_csv_jigbeam(_tep_jigbeam_gia(tmp_path)))
    assert len(cac_ban_tin) == 3
    assert all(b["nguon"] == NHAN_MO_PHONG for b in cac_ban_tin)
    assert all(b["metric"] == "TAKTTIME" for b in cac_ban_tin)
    moc = [b["timestamp"] for b in cac_ban_tin]
    assert moc == sorted(moc)


def test_tu_dong_tat_co_thi_tu_choi_jigbeam(tmp_path, monkeypatch):
    monkeypatch.delenv(FLAG_ENV_KEY, raising=False)
    with pytest.raises(ValueError, match="AIOS_FEATURE_JIGBEAM_ADAPTER"):
        list(phat_lai_csv_tu_dong(_tep_jigbeam_gia(tmp_path)))


def test_tu_dong_bat_co_thi_doc_duoc_jigbeam(tmp_path, monkeypatch):
    monkeypatch.setenv(FLAG_ENV_KEY, "1")
    cac_ban_tin = list(phat_lai_csv_tu_dong(_tep_jigbeam_gia(tmp_path)))
    assert len(cac_ban_tin) == 3


def test_e2e_gui_file_gia_qua_http(tmp_path):
    cac_ban_tin = list(phat_lai_csv_jigbeam(_tep_jigbeam_gia(tmp_path)))
    for b in cac_ban_tin:
        parse_stream_record(b)
    bo_dem = StreamBuffer(tmp_path / "jigbeam.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18821, buffer=bo_dem)
    lang_nghe.start()
    try:
        ket_qua = gui_lo_len_server(cac_ban_tin, "http://127.0.0.1:18821", kich_co_lo=50)
        assert ket_qua["tong_ban_tin"] == 3
        with bo_dem._connect() as conn:
            dem = conn.execute("SELECT COUNT(*) FROM jig_stream_logs").fetchone()[0]
        assert dem == 3
        # Gui lai dung lo: chong trung giu nguyen 3.
        lan2 = []
        for b in cac_ban_tin:
            du_lieu = json.dumps([b]).encode("utf-8")
            yeu_cau = urllib.request.Request(
                "http://127.0.0.1:18821" + STREAM_PATH, data=du_lieu,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(yeu_cau, timeout=5) as tra_loi:
                lan2.append(json.loads(tra_loi.read().decode("utf-8")))
        assert all(t["trung_lap"] == 1 for t in lan2)
        with bo_dem._connect() as conn:
            dem2 = conn.execute("SELECT COUNT(*) FROM jig_stream_logs").fetchone()[0]
        assert dem2 == 3
    finally:
        lang_nghe.stop()


@co_du_lieu_that
def test_file_that_132_dong_qua_duoc():
    duong_dan = _duong_dan_that()
    assert duong_dan is not None
    ket_qua = doc_log_jigbeam(duong_dan)
    assert ket_qua.thieu_cot == []
    assert ket_qua.so_dong == 132
    assert ket_qua.so_cot == 677
    cac_ban_tin = list(phat_lai_csv_jigbeam(duong_dan))
    assert len(cac_ban_tin) == 132
    assert all(b["nguon"] == "SIMULATED_REALTIME" for b in cac_ban_tin)
    moc = [b["timestamp"] for b in cac_ban_tin if b["timestamp"]]
    assert moc == sorted(moc)


@co_du_lieu_that
def test_file_that_e2e_132_qua_http(tmp_path):
    duong_dan = _duong_dan_that()
    assert duong_dan is not None
    cac_ban_tin = list(phat_lai_csv_jigbeam(duong_dan))
    assert len(cac_ban_tin) == 132
    bo_dem = StreamBuffer(tmp_path / "jigbeam_that.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18822, buffer=bo_dem)
    lang_nghe.start()
    try:
        ket_qua = gui_lo_len_server(cac_ban_tin, "http://127.0.0.1:18822", kich_co_lo=50)
        assert ket_qua["tong_ban_tin"] == 132
        with bo_dem._connect() as conn:
            dem = conn.execute("SELECT COUNT(*) FROM jig_stream_logs").fetchone()[0]
        assert dem == 132
    finally:
        lang_nghe.stop()
