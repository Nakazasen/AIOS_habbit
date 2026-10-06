"""Test ve LSU-ALERT-REALTIME-PC0575: consumer qua cong xu huong SMA(20).

4 nhom: (a) trend >=3 diem lien tiep -> CO canh bao; (b) 1 diem don le ->
KHONG canh bao; (c) feedback store dung file; (d) replay do latency < 5 phut.
"""

from __future__ import annotations

import json
from pathlib import Path

from aios_habit.alert_feedback import (
    alert_feedback_stats,
    get_alert_feedback,
    record_alert_feedback,
)
from aios_habit.production_prediction.jig_chat_wire import (
    day_the_realtime_qua_cong_vao_chat,
)
from aios_habit.production_prediction.rt_consumer import (
    chuyen_lo_thanh_the_da_qua_cong,
)
from aios_habit.production_prediction.rt_replay import do_latency_qua_cong_xu_huong


def _su_kien(jig="J-TREND", metric="m", gia_tri=20.0, loai="canh_bao_drift"):
    return {
        "cursor": 1,
        "thoi_gian": "2026-08-01T00:00:00",
        "loai": loai,
        "jig_id": jig,
        "metric": metric,
        "noi_dung": {"gia_tri": gia_tri, "chi_tiet": "Drift test"},
    }


def test_a_trend_3_diem_lien_tiep_co_canh_bao():
    lich_su = {( "J-TREND", "m"): [10.0] * 20}
    lo = [_su_kien(gia_tri=20.0) for _ in range(3)]
    cac_the, cac_can_bien = chuyen_lo_thanh_the_da_qua_cong(lo, lich_su)
    assert len(cac_the) == 1, "Trend 3 diem lien tiep phai CO canh bao"
    assert cac_can_bien == []
    assert cac_the[0]["ma_jig"] == "J-TREND"


def test_b_mot_diem_don_le_khong_canh_bao():
    lich_su = {("J-TREND", "m"): [10.0] * 20}
    lo = [_su_kien(gia_tri=20.0)]
    cac_the, cac_can_bien = chuyen_lo_thanh_the_da_qua_cong(lo, lich_su)
    assert cac_the == [], "Diem don le KHONG duoc thanh the canh bao"
    assert len(cac_can_bien) == 1
    assert cac_can_bien[0]["trang_thai"] == "Cần biến"
    text = day_the_realtime_qua_cong_vao_chat(lo, lich_su)
    assert "Cần biến" in text
    assert "Cảnh báo realtime" not in text


def test_c_feedback_store_dung_file_khong_vao_kho(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    ok = record_alert_feedback("conv1", "alert1", "J1", "m", "dung", chi_tiet="Chi tiet the")
    assert ok == {"ok": True}
    tep = tmp_path / "alert_feedback.jsonl"
    assert tep.is_file()
    dong = json.loads(tep.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert dong["rating"] == "dung"
    assert dong["alert_id"] == "alert1"
    # Che thi bat buoc ly do.
    thieu = record_alert_feedback("conv1", "alert2", "J1", "m", "sai")
    assert thieu["ok"] is False
    ok2 = record_alert_feedback("conv1", "alert2", "J1", "m", "sai", reason="Bao nham")
    assert ok2 == {"ok": True}
    assert get_alert_feedback("conv1", "alert2")["reason"] == "Bao nham"
    stats = alert_feedback_stats()
    assert stats["total"] == 2
    assert stats["dung"] == 1 and stats["sai"] == 1
    # Khong lot vao kho tri thuc: file nam duoi local_cases, khong import kho.
    assert tep.parent.name == tmp_path.name


def test_d_replay_do_latency_duoi_5_phut():
    chuoi = [10.0] * 20 + [10.0] * 100 + [20.0] * 12
    ket_qua = do_latency_qua_cong_xu_huong(chuoi, jig_id="J-LAT", metric="m")
    assert ket_qua["dat_muc_tieu_5_phut"] is True
    assert ket_qua["latency_giay"] < 300.0
    assert ket_qua["so_diem"] == len(chuoi)
    # Do precision: 1 diem don le khong sinh canh bao.
    don = do_latency_qua_cong_xu_huong([10.0] * 20 + [50.0], jig_id="J-ONE", metric="m")
    assert don["so_canh_bao"] == 0, "Diem don le khong duoc sinh canh bao"
