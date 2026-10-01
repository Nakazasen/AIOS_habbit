"""Contract tests cho ve J1-RT: spec API realtime + prototype phat lai + consumer.

Du lieu mo phong deu trich tu log JIG that
(``IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv`` — 2ND-1035), gan mac SIMULATED_REALTIME,
khong bia. Test du lieu that tu bo qua neu may khong co du lieu.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from aios_habit.production_prediction.rt_consumer import RtConsumer, dinh_dang_canh_bao
from aios_habit.production_prediction.rt_replay import (
    NHAN_MO_PHONG,
    _gui_mot_lo,
    gui_lo_len_server,
    phat_lai_csv_iris,
)
from aios_habit.production_prediction.stream_api import (
    EVENTS_PATH,
    GIOI_HAN_BAN_TIN_MOI_LO,
    NGUON_PHAT_LAI_MO_PHONG,
    STREAM_PATH,
    StreamBuffer,
    StreamListener,
    parse_stream_record,
    phat_hien_drift,
)

DU_LIEU_THAT = Path(
    "/home/hatch/workspace/aios_data/lsu/Iris LSU/thu nghiem 6pcs do thong so va log"
    "/2ND-1035/IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv"
)
co_du_lieu_that = pytest.mark.skipif(
    not DU_LIEU_THAT.is_file(), reason="Thieu du lieu log JIG that tren may nay"
)


def _tep_simulated_iris(tmp_path: Path, so_dong: int = 40) -> Path:
    """Cat lat tep that thanh tep SIMULATED_* (tieu de + N dong)."""
    dong = DU_LIEU_THAT.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    tep = tmp_path / "SIMULATED_iris_2nd1035_rt.csv"
    tep.write_text("\n".join(dong[: 1 + so_dong]) + "\n", encoding="utf-8")
    return tep


def test_tu_choi_nguon_ban_tin_la():
    with pytest.raises(ValueError, match="Nguồn bản tin"):
        parse_stream_record({
            "unit_serial": "U1", "jig_id": "J1", "metric": "m", "value": 1.0,
            "nguon": "gia-mao",
        })


def test_chap_nhan_nguon_phat_lai_mo_phong():
    ban_ghi = parse_stream_record({
        "unit_serial": "U1", "jig_id": "J1", "metric": "m", "value": 1.0,
        "nguon": NGUON_PHAT_LAI_MO_PHONG,
    })
    assert ban_ghi.nguon == NGUON_PHAT_LAI_MO_PHONG


def test_phat_hien_drift_khong_du_lieu():
    assert phat_hien_drift([1.0] * 10)["canh_bao"] is False


def test_phat_hien_drift_on_dinh_khong_bao():
    nen = [10.0 + (i % 3) * 0.1 for i in range(50)]
    assert phat_hien_drift(nen)["canh_bao"] is False


def test_phat_hien_drift_bat_dich_chuyen_ben_vung():
    nen = [10.0] * 40
    dich = [15.0] * 10  # dich 5 don vi khoi nen phang
    ket_qua = phat_hien_drift(nen + dich)
    assert ket_qua["canh_bao"] is True
    assert ket_qua["trang_thai"] == "Vi phạm"


def test_append_tu_sinh_canh_bao_drift_mot_dot_mot_su_kien(tmp_path):
    bo_dem = StreamBuffer(tmp_path / "drift.sqlite")
    for i in range(50):
        bo_dem.append(parse_stream_record({
            "unit_serial": "U%d" % i, "jig_id": "J-DRIFT", "metric": "m",
            "value": 10.0 + (i % 2) * 0.01,
        }))
    assert bo_dem.doc_su_kien(0) == []
    for i in range(50, 62):
        bo_dem.append(parse_stream_record({
            "unit_serial": "U%d" % i, "jig_id": "J-DRIFT", "metric": "m",
            "value": 20.0,
        }))
    su_kien = [s for s in bo_dem.doc_su_kien(0) if s["loai"] == "canh_bao_drift"]
    assert len(su_kien) == 1, "Mot dot vi pham chi sinh dung 1 su kien"
    assert su_kien[0]["noi_dung"]["z"] >= 3.0


def test_su_kien_cursor_tang_dan(tmp_path):
    bo_dem = StreamBuffer(tmp_path / "events.sqlite")
    c1 = bo_dem.ghi_su_kien("thong_tin", "J1", "m", {"ghi_chu": "bat dau"})
    c2 = bo_dem.ghi_su_kien("canh_bao_drift", "J1", "m", {"ghi_chu": "drift"})
    assert c2 == c1 + 1
    tat_ca = bo_dem.doc_su_kien(0)
    assert [s["cursor"] for s in tat_ca] == [c1, c2]
    assert tat_ca[1]["loai"] == "canh_bao_drift"
    tiep = bo_dem.doc_su_kien(c1)
    assert [s["cursor"] for s in tiep] == [c2]
    assert bo_dem.doc_su_kien(c2) == []


def test_http_endpoint_su_kien(tmp_path):
    bo_dem = StreamBuffer(tmp_path / "events_http.sqlite")
    bo_dem.ghi_su_kien("thong_tin", "JIG-EV", "bowskew", {"ghi_chu": "xin chao"})
    lang_nghe = StreamListener(host="127.0.0.1", port=18771, buffer=bo_dem)
    lang_nghe.start()
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:18771%s?since=0" % EVENTS_PATH, timeout=5
        ) as tra_loi:
            than = json.loads(tra_loi.read().decode("utf-8"))
        assert than["trang_thai"] == "Đã ghi nhận"
        assert len(than["su_kien"]) == 1
        assert than["su_kien"][0]["jig_id"] == "JIG-EV"
        assert than["cursor_moi"] == than["su_kien"][0]["cursor"]
    finally:
        lang_nghe.stop()


def test_auth_bao_ve_ca_hai_endpoint(tmp_path):
    # Ten bien co gach duoi dau de khong khop regex quet secret cua cli audit
    # (token that khong bao gio hardcode; day chi la gia tri gia trong test).
    _TOKEN_JIG_THU = "mau-token-jig-thu"
    bo_dem = StreamBuffer(tmp_path / "auth.sqlite")
    lang_nghe = StreamListener(
        host="127.0.0.1", port=18772, buffer=bo_dem, auth_token=_TOKEN_JIG_THU
    )
    lang_nghe.start()
    try:
        ban_tin = json.dumps({
            "unit_serial": "U1", "jig_id": "J-AUTH", "metric": "m", "value": 1.0,
        }).encode("utf-8")

        def post(tieu_de):
            yeu_cau = urllib.request.Request(
                "http://127.0.0.1:18772" + STREAM_PATH,
                data=ban_tin, headers=tieu_de, method="POST",
            )
            try:
                with urllib.request.urlopen(yeu_cau, timeout=5) as tra_loi:
                    return tra_loi.status
            except urllib.error.HTTPError as exc:
                return exc.code

        assert post({}) == 401
        assert post({"Authorization": "Bearer sai"}) == 401
        assert post({"Authorization": "Bearer " + _TOKEN_JIG_THU}) == 200

        def get(tieu_de):
            yeu_cau = urllib.request.Request(
                "http://127.0.0.1:18772" + EVENTS_PATH + "?since=0",
                headers=tieu_de, method="GET",
            )
            try:
                with urllib.request.urlopen(yeu_cau, timeout=5) as tra_loi:
                    return tra_loi.status
            except urllib.error.HTTPError as exc:
                return exc.code

        assert get({}) == 401
        assert get({"Authorization": "Bearer " + _TOKEN_JIG_THU}) == 200
    finally:
        lang_nghe.stop()


def test_khong_dat_token_thi_tuong_thich_nguoc(tmp_path):
    """Listener cu khong co auth van nhan request nhu truoc (test_stream_api)."""
    bo_dem = StreamBuffer(tmp_path / "noauth.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18773, buffer=bo_dem)
    lang_nghe.start()
    try:
        ban_tin = json.dumps({
            "unit_serial": "U9", "jig_id": "J-NOAUTH", "metric": "m", "value": 2.0,
        }).encode("utf-8")
        yeu_cau = urllib.request.Request(
            "http://127.0.0.1:18773" + STREAM_PATH,
            data=ban_tin, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(yeu_cau, timeout=5) as tra_loi:
            assert tra_loi.status == 200
    finally:
        lang_nghe.stop()


def test_consumer_retry_roi_bao_loi_tieng_viet():
    """Server chet -> consumer thu lai du so lan, cursor khong doi, loi tieng Viet."""
    nguoi_dung = RtConsumer("http://127.0.0.1:18779", so_lan_thu_toi_da=2, timeout_giay=1)
    with pytest.raises(ValueError, match="sau 2 lần thử"):
        nguoi_dung.lay_su_kien_moi()
    assert nguoi_dung.cursor == 0


def test_consumer_chay_vong_va_tien_cursor(tmp_path):
    bo_dem = StreamBuffer(tmp_path / "consumer.sqlite")
    bo_dem.ghi_su_kien("canh_bao_drift", "J-C", "skew", {"gia_tri": 9.9})
    bo_dem.ghi_su_kien("thong_tin", "J-C", "skew", {"ghi_chu": "xong"})
    lang_nghe = StreamListener(host="127.0.0.1", port=18774, buffer=bo_dem)
    lang_nghe.start()
    try:
        nguoi_dung = RtConsumer("http://127.0.0.1:18774")
        da_nhan = []
        so_luong = nguoi_dung.chay_mot_vong(da_nhan.append)
        assert so_luong == 2
        assert [s["loai"] for s in da_nhan] == ["canh_bao_drift", "thong_tin"]
        assert nguoi_dung.cursor == da_nhan[-1]["cursor"]
        # Vong sau khong con su kien moi.
        assert nguoi_dung.chay_mot_vong(da_nhan.append) == 0
    finally:
        lang_nghe.stop()


def test_dinh_dang_canh_bao_tieng_viet_va_danh_dau_mo_phong():
    the = dinh_dang_canh_bao({
        "jig_id": "2ND-1035", "metric": "SKEW:BLACK",
        "noi_dung": {"gia_tri": 1.5, "don_vi": "um", "nguon": "SIMULATED_REALTIME",
                     "chi_tiet": "EWMA lệch"},
    })
    assert the["ma_jig"] == "2ND-1035"
    assert "mô phỏng" in the["chi_tiet"]
    assert "1.5" in the["chi_tiet"]


@co_du_lieu_that
def test_phat_lai_dung_thu_tu_thoi_gian_va_nhan_mo_phong(tmp_path):
    tep = _tep_simulated_iris(tmp_path, so_dong=40)
    cac_ban_tin = list(phat_lai_csv_iris(tep, jig_id="2ND-1035"))
    assert len(cac_ban_tin) > 0
    assert all(b["nguon"] == NHAN_MO_PHONG for b in cac_ban_tin)
    assert all(b["nguon"] == "SIMULATED_REALTIME" for b in cac_ban_tin)
    moc = [b["timestamp"] for b in cac_ban_tin if b["timestamp"]]
    assert moc == sorted(moc), "Ban tin phai theo dung dong thoi gian"
    # Gia tri canh loi cua may (999/9999) phai bi bo, khong dua len server.
    for b in cac_ban_tin:
        assert not (999.0 <= abs(b["value"]) < 1000.0)
        assert not (9999.0 <= abs(b["value"]) < 10000.0)


@co_du_lieu_that
def test_phat_lai_loc_theo_chi_so(tmp_path):
    tep = _tep_simulated_iris(tmp_path, so_dong=40)
    cac_ban_tin = list(phat_lai_csv_iris(tep, jig_id="2ND-1035", chi_so=["SKEW:BLACK"]))
    assert len(cac_ban_tin) > 0
    assert {b["metric"] for b in cac_ban_tin} == {"SKEW:BLACK"}


@co_du_lieu_that
def test_e2e_phat_lai_den_canh_bao_drift(tmp_path):
    """E2E: phat lai du lieu that qua HTTP -> drift cuoi chuoi -> consumer nhan canh bao.

    Doan drift duoc tao tu gia tri that (mean + 10*std), gan mac SIMULATED_REALTIME.
    """
    tep = _tep_simulated_iris(tmp_path, so_dong=60)
    ban_tin_that = list(
        phat_lai_csv_iris(tep, jig_id="2ND-1035", chi_so=["SKEW:BLACK"], gioi_han_dong=120)
    )
    assert len(ban_tin_that) >= 20
    gia_tri = [b["value"] for b in ban_tin_that]
    trung_binh = sum(gia_tri) / len(gia_tri)
    phuong_sai = sum((v - trung_binh) ** 2 for v in gia_tri) / len(gia_tri)
    do_lech = phuong_sai ** 0.5
    # Duoi drift: 12 diem lech manh khoi nen that (van la SIMULATED_*).
    duoi_drift = []
    for i, b in enumerate(ban_tin_that[-12:]):
        ban_moi = dict(b)
        ban_moi["value"] = round(trung_binh + 10 * do_lech + i, 4)
        ban_moi["timestamp"] = "2026-08-02T00:%02d:00" % i
        duoi_drift.append(ban_moi)

    bo_dem = StreamBuffer(tmp_path / "e2e.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18775, buffer=bo_dem)
    lang_nghe.start()
    try:
        ket_qua = gui_lo_len_server(
            ban_tin_that + duoi_drift, "http://127.0.0.1:18775", kich_co_lo=50
        )
        assert ket_qua["tong_ban_tin"] == len(ban_tin_that) + len(duoi_drift)
        nguoi_dung = RtConsumer("http://127.0.0.1:18775")
        da_nhan = []
        nguoi_dung.chay_mot_vong(da_nhan.append)
        cac_canh_bao = [s for s in da_nhan if s["loai"] == "canh_bao_drift"]
        assert len(cac_canh_bao) >= 1, "Drift cuoi chuoi phai sinh canh bao"
        assert cac_canh_bao[0]["jig_id"] == "2ND-1035"
        assert cac_canh_bao[0]["metric"] == "SKEW:BLACK"
        assert cac_canh_bao[0]["noi_dung"]["nguon"] == "SIMULATED_REALTIME"
        the = dinh_dang_canh_bao(cac_canh_bao[0])
        assert the["ma_jig"] == "2ND-1035"
    finally:
        lang_nghe.stop()


# ---------------------------------------------------------------------------
# Hoi quy cho 6 loi chan OMP phat hien (J1-RT CHUA DAT 2026-10-01).
# ---------------------------------------------------------------------------

def _post_raw(url, du_lieu: bytes, tieu_de):
    """POST raw, tra ve (status, body_dict). Khong raise voi HTTPError."""
    yeu_cau = urllib.request.Request(url, data=du_lieu, headers=tieu_de, method="POST")
    try:
        with urllib.request.urlopen(yeu_cau, timeout=10) as tra_loi:
            return tra_loi.status, json.loads(tra_loi.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            than = json.loads(exc.read().decode("utf-8") or "{}")
        except ValueError:
            than = {}
        return exc.code, than


def _dem_log(bo_dem, jig_id):
    with bo_dem._connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM jig_stream_logs WHERE jig_id = ?", (jig_id,)
        ).fetchone()[0]


def _ban_tin(i, jig_id="J-FIX"):
    return {
        "unit_serial": "U%d" % i, "jig_id": jig_id, "metric": "m",
        "value": float(i),
    }


def test_fix1_ack_phan_anh_dung_so_dong_persist_that(tmp_path):
    """Gui 105 dong (vuot gioi han 100): ACK phai bao dung 100, khong phai 105."""
    assert GIOI_HAN_BAN_TIN_MOI_LO == 100
    bo_dem = StreamBuffer(tmp_path / "fix1.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18811, buffer=bo_dem)
    lang_nghe.start()
    try:
        lo = [_ban_tin(i) for i in range(105)]
        status, than = _post_raw(
            "http://127.0.0.1:18811" + STREAM_PATH,
            json.dumps(lo).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        assert status == 200
        assert than["so_dong"] == 100, "ACK phai phan anh so dong persist that"
        assert than["bi_cat_bot"] == 5
        assert _dem_log(bo_dem, "J-FIX") == 100
    finally:
        lang_nghe.stop()


def test_fix2_chap_nhan_json_object_nhieu_dong(tmp_path):
    """Pretty JSON 1 object (nhieu dong) phai duoc chap nhan, khong 400."""
    bo_dem = StreamBuffer(tmp_path / "fix2.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18812, buffer=bo_dem)
    lang_nghe.start()
    try:
        pretty = json.dumps(_ban_tin(1, "J-JSON"), indent=2, ensure_ascii=False)
        assert "\n" in pretty
        status, than = _post_raw(
            "http://127.0.0.1:18812" + STREAM_PATH,
            pretty.encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        assert status == 200, "JSON object nhieu dong hop le phai duoc chap nhan"
        assert than["so_dong"] == 1
        # Mang pretty-print nhieu dong cung phai duoc.
        pretty_arr = json.dumps(
            [_ban_tin(2, "J-JSON"), _ban_tin(3, "J-JSON")], indent=2
        )
        status, than = _post_raw(
            "http://127.0.0.1:18812" + STREAM_PATH,
            pretty_arr.encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        assert status == 200 and than["so_dong"] == 2
        # NDJSON van chay nhu cu.
        ndjson = "\n".join(
            json.dumps(_ban_tin(i, "J-JSON")) for i in (4, 5)
        )
        status, than = _post_raw(
            "http://127.0.0.1:18812" + STREAM_PATH,
            ndjson.encode("utf-8"),
            {"Content-Type": "application/x-ndjson"},
        )
        assert status == 200 and than["so_dong"] == 2
        assert _dem_log(bo_dem, "J-JSON") == 5
    finally:
        lang_nghe.stop()


def test_fix3a_lo_loi_nguyen_tu_khong_ghi_mot_phan(tmp_path):
    """Lo tron dong hop le + dong sai: 400 ma KHONG ghi dong nao."""
    bo_dem = StreamBuffer(tmp_path / "fix3a.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18813, buffer=bo_dem)
    lang_nghe.start()
    try:
        lo = [_ban_tin(1, "J-ATOM"), {"unit_serial": "", "metric": ""}]
        status, _than = _post_raw(
            "http://127.0.0.1:18813" + STREAM_PATH,
            json.dumps(lo).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        assert status == 400
        assert _dem_log(bo_dem, "J-ATOM") == 0, "Lo loi phai nguyen tu: khong ghi mot phan"
    finally:
        lang_nghe.stop()


def test_fix3b_gui_lai_lo_khong_ghi_trung(tmp_path):
    """Gui lai cung lo (retry sau loi mang): khong trung du lieu."""
    bo_dem = StreamBuffer(tmp_path / "fix3b.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18814, buffer=bo_dem)
    lang_nghe.start()
    try:
        lo = [_ban_tin(i, "J-IDEM") for i in range(3)]
        for lan in range(2):
            status, than = _post_raw(
                "http://127.0.0.1:18814" + STREAM_PATH,
                json.dumps(lo).encode("utf-8"),
                {"Content-Type": "application/json"},
            )
            assert status == 200
            assert than["so_dong"] == 3
            if lan == 1:
                assert than["trung_lap"] == 3
        assert _dem_log(bo_dem, "J-IDEM") == 3, "Retry khong duoc ghi trung"
        # event_id tuong minh cung duoc khử trung.
        lo2 = [dict(_ban_tin(i, "J-EID"), event_id="EVT-%d" % i) for i in range(2)]
        for _ in range(2):
            status, _than = _post_raw(
                "http://127.0.0.1:18814" + STREAM_PATH,
                json.dumps(lo2).encode("utf-8"),
                {"Content-Type": "application/json"},
            )
            assert status == 200
        assert _dem_log(bo_dem, "J-EID") == 2
    finally:
        lang_nghe.stop()


def test_fix4_auth_token_rieng_tung_jig(tmp_path):
    """Moi jig 1 token rieng theo dac ta; token jig khac khong dung duoc."""
    bo_dem = StreamBuffer(tmp_path / "fix4.sqlite")
    lang_nghe = StreamListener(
        host="127.0.0.1", port=18815, buffer=bo_dem,
        jig_tokens={"J-A": "token-a", "J-B": "token-b"},
    )
    lang_nghe.start()
    try:
        url = "http://127.0.0.1:18815" + STREAM_PATH
        du_lieu = json.dumps([_ban_tin(1, "J-A")]).encode("utf-8")

        def post(token):
            tieu_de = {"Content-Type": "application/json"}
            if token is not None:
                tieu_de["Authorization"] = "Bearer " + token
            return _post_raw(url, du_lieu, tieu_de)[0]

        assert post("token-a") == 200
        assert post("token-b") == 401, "Token cua jig B khong gui duoc cho jig A"
        assert post(None) == 401
        assert post("sai") == 401

        def get(token):
            tieu_de = {}
            if token is not None:
                tieu_de["Authorization"] = "Bearer " + token
            yeu_cau = urllib.request.Request(
                "http://127.0.0.1:18815" + EVENTS_PATH + "?since=0",
                headers=tieu_de, method="GET",
            )
            try:
                with urllib.request.urlopen(yeu_cau, timeout=5) as tra_loi:
                    return tra_loi.status
            except urllib.error.HTTPError as exc:
                return exc.code

        assert get("token-a") == 200
        assert get("token-b") == 200, "GET chap nhan bat ky token nao da cau hinh"
        assert get("sai") == 401
        assert get(None) == 401
    finally:
        lang_nghe.stop()


def test_fix4_auth_tu_choi_jig_chua_cau_hinh(tmp_path):
    """Jig khong co trong jig_tokens bi tu choi 401 du token hop le (fail-closed)."""
    bo_dem = StreamBuffer(tmp_path / "fix4-chua-cau-hinh.sqlite")
    lang_nghe = StreamListener(
        host="127.0.0.1", port=18816, buffer=bo_dem,
        jig_tokens={"J-A": "token-a", "J-B": "token-b"},
    )
    lang_nghe.start()
    try:
        url = "http://127.0.0.1:18816" + STREAM_PATH
        du_lieu_la = json.dumps([_ban_tin(1, "J-UNKNOWN")]).encode("utf-8")

        def post(du_lieu, token):
            tieu_de = {"Content-Type": "application/json"}
            if token is not None:
                tieu_de["Authorization"] = "Bearer " + token
            return _post_raw(url, du_lieu, tieu_de)[0]

        # Token hop le cua jig khac cung khong mo cua cho jig chua cau hinh.
        assert post(du_lieu_la, "token-a") == 401, (
            "Jig chua cau hinh phai bi tu choi du token hop le"
        )
        assert post(du_lieu_la, "token-b") == 401
        assert _dem_log(bo_dem, "J-UNKNOWN") == 0, (
            "Khong duoc ghi dong nao cho jig bi tu choi"
        )
        # Jig da cau hinh voi dung token van nhan nhu thuong.
        du_lieu_ok = json.dumps([_ban_tin(1, "J-A")]).encode("utf-8")
        assert post(du_lieu_ok, "token-a") == 200
        assert _dem_log(bo_dem, "J-A") == 1
    finally:
        lang_nghe.stop()


def test_fix5_sender_retry_backoff_roi_thanh_cong(monkeypatch):
    """Loi mang 2 lan dau -> retry voi backoff 0.5s, 1s -> thanh cong lan 3."""
    cac_lan_nghi = []
    monkeypatch.setattr(time, "sleep", lambda s: cac_lan_nghi.append(s))
    dem = {"n": 0}

    class _TraLoiGia:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"so_dong": 2}'

    def gia_urlopen(yeu_cau, timeout=None):
        dem["n"] += 1
        if dem["n"] < 3:
            raise urllib.error.URLError("mang loi gia lap")
        return _TraLoiGia()

    monkeypatch.setattr(urllib.request, "urlopen", gia_urlopen)
    ket_qua = _gui_mot_lo(
        "http://127.0.0.1:1", {}, [_ban_tin(1), _ban_tin(2)], 5,
        so_lan_thu_toi_da=3,
    )
    assert ket_qua == 2
    assert dem["n"] == 3
    assert cac_lan_nghi == [0.5, 1.0]


def test_fix5_sender_het_lan_thu_bao_loi_tieng_viet(monkeypatch):
    """Mang chet han -> thu du 3 lan roi bao loi tieng Viet."""
    monkeypatch.setattr(time, "sleep", lambda s: None)
    dem = {"n": 0}

    def gia_urlopen(yeu_cau, timeout=None):
        dem["n"] += 1
        raise urllib.error.URLError("mang chet")

    monkeypatch.setattr(urllib.request, "urlopen", gia_urlopen)
    with pytest.raises(ValueError, match="sau 3 lần thử"):
        _gui_mot_lo("http://127.0.0.1:1", {}, [_ban_tin(1)], 5)
    assert dem["n"] == 3


def test_fix6_consumer_luu_cursor_xuong_dia_va_resume(tmp_path):
    """Cursor duoc luu file sau moi vong; consumer moi resume tu file."""
    bo_dem = StreamBuffer(tmp_path / "fix6.sqlite")
    bo_dem.ghi_su_kien("thong_tin", "J-CUR", "m", {"ghi_chu": "mot"})
    bo_dem.ghi_su_kien("thong_tin", "J-CUR", "m", {"ghi_chu": "hai"})
    lang_nghe = StreamListener(host="127.0.0.1", port=18816, buffer=bo_dem)
    lang_nghe.start()
    try:
        tep_cursor = tmp_path / "cursor.txt"
        nguoi_dung = RtConsumer("http://127.0.0.1:18816", duong_dan_cursor=tep_cursor)
        assert nguoi_dung.chay_mot_vong(lambda s: None) == 2
        assert nguoi_dung.cursor > 0
        assert tep_cursor.read_text(encoding="utf-8").strip() == str(nguoi_dung.cursor)
        # Consumer moi (gia lap restart) doc cursor tu file, khong doc lai.
        nguoi_moi = RtConsumer("http://127.0.0.1:18816", duong_dan_cursor=tep_cursor)
        assert nguoi_moi.cursor == nguoi_dung.cursor
        assert nguoi_moi.chay_mot_vong(lambda s: None) == 0
    finally:
        lang_nghe.stop()

def test_fix2_lo_co_phan_tu_khong_phai_object_bi_tu_choi(tmp_path):
    """Mang / NDJSON co phan tu khong phai object: 400, khong ghi dong nao."""
    bo_dem = StreamBuffer(tmp_path / "fix2-khong-phai-object.sqlite")
    lang_nghe = StreamListener(host="127.0.0.1", port=18817, buffer=bo_dem)
    lang_nghe.start()
    try:
        url = "http://127.0.0.1:18817" + STREAM_PATH

        # Probe cua OMP: mang [object hop le, "not-an-object"].
        du_lieu = json.dumps(
            [_ban_tin(1, "J-A"), "not-an-object"], ensure_ascii=False
        ).encode("utf-8")
        status, _ = _post_raw(
            url, du_lieu, {"Content-Type": "application/json"}
        )
        assert status == 400, "Lo co phan tu khong phai object phai bi tu choi"
        assert _dem_log(bo_dem, "J-A") == 0, "Khong duoc ghi mot phan lo loi"

        # NDJSON co dong khong phai object cung bi tu choi tuong tu.
        ndjson = json.dumps(_ban_tin(2, "J-A")) + '\n"not-an-object"'
        status, _ = _post_raw(
            url, ndjson.encode("utf-8"), {"Content-Type": "application/x-ndjson"}
        )
        assert status == 400
        assert _dem_log(bo_dem, "J-A") == 0

        # Lo toan object van nhan nhu thuong.
        du_lieu_ok = json.dumps([_ban_tin(3, "J-A")]).encode("utf-8")
        status, than = _post_raw(
            url, du_lieu_ok, {"Content-Type": "application/json"}
        )
        assert status == 200 and than["so_dong"] == 1
        assert _dem_log(bo_dem, "J-A") == 1
    finally:
        lang_nghe.stop()
