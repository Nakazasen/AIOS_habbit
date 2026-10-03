"""Tests for the persistent one-line notebook status."""

import json

from aios_habit.notebook_readiness import (
    NotebookReadiness,
    NotebookReadinessStore,
    dong_trang_thai_so,
    dong_trang_thai_tu_snapshot,
)


def test_dong_trang_thai_ro_rang():
    dong = dong_trang_thai_so("Lỗi JIG", 12)
    assert dong == "Sổ Lỗi JIG — sẵn sàng, 12 tài liệu"
    assert "%" not in dong


def test_dong_chua_san_sang():
    dong = dong_trang_thai_so("Lỗi JIG", 0, san_sang=False)
    assert "chưa sẵn sàng" in dong
    assert "đang nạp tài liệu" in dong


def test_dong_co_ten_thu_vien():
    dong = dong_trang_thai_so("Sổ A", 3, ten_thu_vien="Kho chung")
    assert "Kho chung" in dong


def test_store_luu_ben_vung(tmp_path):
    store = NotebookReadinessStore(tmp_path)
    snap = store.cap_nhat("NB-1", san_sang=True, so_tai_lieu=5, ten_thu_vien="Kho")
    assert snap.notebook_id == "NB-1"
    # A new store instance on the same dir sees the snapshot (persistent).
    store2 = NotebookReadinessStore(tmp_path)
    doc = store2.lay("NB-1")
    assert doc is not None
    assert doc.so_tai_lieu == 5
    assert doc.san_sang is True
    dong = dong_trang_thai_tu_snapshot(doc, "Sổ test")
    assert dong == "Sổ Sổ test — sẵn sàng, 5 tài liệu (thư viện: Kho)"


def test_store_khong_co_snapshot():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        store = NotebookReadinessStore(d)
        assert store.lay("NB-KHONG-CO") is None
        dong = dong_trang_thai_tu_snapshot(None, "Sổ trống")
        assert "chưa có thông tin trạng thái" in dong


def test_store_xoa(tmp_path):
    store = NotebookReadinessStore(tmp_path)
    store.cap_nhat("NB-9", san_sang=True, so_tai_lieu=1)
    assert store.xoa("NB-9") is True
    assert store.lay("NB-9") is None
    assert store.xoa("NB-9") is False


def test_snapshot_file_la_json_hop_le(tmp_path):
    store = NotebookReadinessStore(tmp_path)
    store.cap_nhat("NB-2", san_sang=False, so_tai_lieu=0)
    raw = json.loads((tmp_path / "notebook_readiness.json").read_text(encoding="utf-8"))
    assert raw["NB-2"]["san_sang"] is False
    snap = NotebookReadiness.from_dict(raw["NB-2"])
    assert snap.notebook_id == "NB-2"
