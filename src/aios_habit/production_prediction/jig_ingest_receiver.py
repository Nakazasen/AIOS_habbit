"""Đầu tiếp nhận dữ liệu đẩy lên phía ứng dụng cho tool JIG (DESKTOP-STEP4-PERIODIC-REPORT-INGEST-HOME).

Quy chuẩn và tính năng:
- Điểm nhận nội bộ nhận lô bản ghi log từ tool JIG (batch ingestion).
- Ghi vào kho log và chạy cổng cảnh báo xu hướng SMA(20).
- Tách biệt tuyệt đối dữ liệu mô phỏng gắn mác SIMULATED_* sinh từ log thật (không trộn vào dữ liệu sản xuất).
- Tái sử dụng logic cổng cảnh báo trong `trend_alerts.py`, không viết lại logic SMA.
- Tương thích Python 3.11, đầy đủ type hints và error handling.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from aios_habit.production_prediction.log_archive import (
    DongKhoLog,
    MAC_DINH_KHO_PATH,
    MAC_DINH_KHO_MO_PHONG_PATH,
    doc_kho,
    ghi_ban_ghi,
    lich_su_theo_jig,
)
from aios_habit.production_prediction.stream_api import (
    NGUON_THAT,
    StreamBuffer,
    StreamRecord,
    parse_stream_record,
)
from aios_habit.production_prediction.trend_alerts import (
    WINDOW_DEFAULT,
    K_DEFAULT,
    danh_gia_xu_huong_sma,
)

VIETNAM_TZ = timezone(timedelta(hours=7))


@dataclass
class DanhGiaCongThongSo:
    """Kết quả đánh giá cổng cảnh báo cho một thông số trong lô tiếp nhận."""

    jig_id: str
    metric: str
    so_diem_moi: int
    gia_tri_cuoi: Optional[float]
    sma: Optional[float]
    muc_lech: str
    so_diem_lien_tiep: int
    trang_thai: str  # "Vi phạm" | "Cận biên" | "Đạt"
    canh_bao: bool
    chi_tiet: str
    la_mo_phong: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jig_id": self.jig_id,
            "metric": self.metric,
            "so_diem_moi": self.so_diem_moi,
            "gia_tri_cuoi": self.gia_tri_cuoi,
            "sma": self.sma,
            "muc_lech": self.muc_lech,
            "so_diem_lien_tiep": self.so_diem_lien_tiep,
            "trang_thai": self.trang_thai,
            "canh_bao": self.canh_bao,
            "chi_tiet": self.chi_tiet,
            "la_mo_phong": self.la_mo_phong,
        }


@dataclass
class KetQuaTiepNhanLo:
    """Kết quả phản hồi của đầu tiếp nhận dữ liệu JIG."""

    thanh_cong: bool
    trang_thai: str
    tong_so_nhan: int
    da_ghi_kho: int
    bo_qua_rong: int
    la_mo_phong: bool
    nguon: str
    kho_luu_tru: str
    danh_sach_danh_gia_cong: List[DanhGiaCongThongSo] = field(default_factory=list)
    so_canh_bao_vi_pham: int = 0
    so_can_bien: int = 0
    so_dat_chuan: int = 0
    thong_diep: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thanh_cong": self.thanh_cong,
            "trang_thai": self.trang_thai,
            "tong_so_nhan": self.tong_so_nhan,
            "da_ghi_kho": self.da_ghi_kho,
            "bo_qua_rong": self.bo_qua_rong,
            "la_mo_phong": self.la_mo_phong,
            "nguon": self.nguon,
            "kho_luu_tru": self.kho_luu_tru,
            "so_canh_bao_vi_pham": self.so_canh_bao_vi_pham,
            "so_can_bien": self.so_can_bien,
            "so_dat_chuan": self.so_dat_chuan,
            "thong_diep": self.thong_diep,
            "danh_sach_danh_gia_cong": [d.to_dict() for d in self.danh_sach_danh_gia_cong],
        }


class JigIngestReceiver:
    """Đầu tiếp nhận dữ liệu phía ứng dụng cho tool JIG."""

    def __init__(
        self,
        kho_that: Union[str, Path] = MAC_DINH_KHO_PATH,
        kho_mo_phong: Union[str, Path] = MAC_DINH_KHO_MO_PHONG_PATH,
        window: int = WINDOW_DEFAULT,
        stream_buffer: Optional[StreamBuffer] = None,
    ) -> None:
        self.kho_that = Path(kho_that)
        self.kho_mo_phong = Path(kho_mo_phong)
        self.window = window
        self.stream_buffer = stream_buffer

    def tiep_nhan_lo(
        self,
        records: Union[Sequence[Dict[str, Any]], str],
        *,
        nguon_mac_dinh: str = NGUON_THAT,
    ) -> KetQuaTiepNhanLo:
        """Tiếp nhận lô bản ghi log, ghi kho và chạy cổng cảnh báo xu hướng SMA(20).

        Tách biệt hoàn toàn:
        - Nếu bản ghi mang nhãn `nguon="that"`: ghi vào `kho_that` (kho sản xuất).
        - Nếu bản ghi mang nhãn `nguon="SIMULATED_*"`: ghi vào `kho_mo_phong` (kho mô phỏng).
        """
        # 1. Chuẩn hoá dữ liệu đầu vào
        parsed_records: List[Dict[str, Any]] = []
        if isinstance(records, str):
            text = records.strip()
            if not text:
                return KetQuaTiepNhanLo(
                    thanh_cong=False,
                    trang_thai="Lỗi dữ liệu",
                    tong_so_nhan=0,
                    da_ghi_kho=0,
                    bo_qua_rong=0,
                    la_mo_phong=False,
                    nguon=nguon_mac_dinh,
                    kho_luu_tru="",
                    thong_diep="Dữ liệu gửi lên rỗng.",
                )
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    parsed_records = [d for d in data if isinstance(d, dict)]
                elif isinstance(data, dict):
                    parsed_records = [data]
            except json.JSONDecodeError:
                # NDJSON (từng dòng một JSON)
                for line in text.splitlines():
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                parsed_records.append(obj)
                        except json.JSONDecodeError:
                            continue
        else:
            parsed_records = [dict(r) for r in records if isinstance(r, dict)]

        if not parsed_records:
            return KetQuaTiepNhanLo(
                thanh_cong=False,
                trang_thai="Lỗi dữ liệu",
                tong_so_nhan=0,
                da_ghi_kho=0,
                bo_qua_rong=0,
                la_mo_phong=False,
                nguon=nguon_mac_dinh,
                kho_luu_tru="",
                thong_diep="Không có bản ghi hợp lệ nào trong lô.",
            )

        # 2. Phân loại nguồn bản ghi & kiểm tra tính hợp lệ
        validated_records: List[Dict[str, Any]] = []
        la_toan_bo_mo_phong = True
        nguon_chinh = nguon_mac_dinh

        for item in parsed_records:
            unit_serial = str(item.get("unit_serial", "") or "").strip()
            jig_id = str(item.get("jig_id", "") or "JIG-UNKNOWN").strip()
            metric = str(item.get("metric_name", "") or item.get("metric", "") or "").strip()
            raw_val = item.get("value")

            if not unit_serial or not metric:
                continue

            value = None
            if raw_val is not None and str(raw_val).strip() not in ("", "-", "None", "null"):
                try:
                    value = float(str(raw_val).replace(",", "."))
                except (ValueError, TypeError):
                    value = None

            nguon_item = str(item.get("nguon", nguon_mac_dinh) or nguon_mac_dinh).strip()
            if not nguon_item.startswith("SIMULATED_") and nguon_item != NGUON_THAT:
                nguon_item = NGUON_THAT

            if not nguon_item.startswith("SIMULATED_"):
                la_toan_bo_mo_phong = False

            ts = item.get("ts") or item.get("timestamp") or datetime.now(VIETNAM_TZ).isoformat()
            target_label = str(item.get("target_label", "") or item.get("status", "OK")).strip()
            unit = str(item.get("unit", "") or "").strip()
            tep = str(item.get("tep", "") or jig_id).strip()

            validated_records.append({
                "unit_serial": unit_serial,
                "jig_id": jig_id,
                "metric_name": metric,
                "value": value,
                "unit": unit,
                "target_label": target_label,
                "ts": str(ts),
                "tep": tep,
                "nguon": nguon_item,
            })
            nguon_chinh = nguon_item

        if not validated_records:
            return KetQuaTiepNhanLo(
                thanh_cong=False,
                trang_thai="Lỗi dữ liệu",
                tong_so_nhan=len(parsed_records),
                da_ghi_kho=0,
                bo_qua_rong=len(parsed_records),
                la_mo_phong=la_toan_bo_mo_phong,
                nguon=nguon_chinh,
                kho_luu_tru="",
                thong_diep="Toàn bộ bản ghi thiếu trường bắt buộc (unit_serial hoặc metric).",
            )

        # 3. Ghi vào kho log tương ứng (Tách biệt sản xuất vs mô phỏng)
        # Nhóm theo tính chất mô phỏng
        records_that = [r for r in validated_records if not r["nguon"].startswith("SIMULATED_")]
        records_sim = [r for r in validated_records if r["nguon"].startswith("SIMULATED_")]

        tong_da_ghi = 0
        bo_qua_rong = 0

        target_kho_path = self.kho_mo_phong if (records_sim and not records_that) else self.kho_that

        if records_that:
            # Ghi vào kho sản xuất thật
            res_that = self._ghi_danh_sach(records_that, self.kho_that)
            tong_da_ghi += res_that["da_ghi"]
            bo_qua_rong += res_that["bo_qua_rong"]

        if records_sim:
            # Ghi vào kho mô phỏng tách biệt
            res_sim = self._ghi_danh_sach(records_sim, self.kho_mo_phong)
            tong_da_ghi += res_sim["da_ghi"]
            bo_qua_rong += res_sim["bo_qua_rong"]

        # Nếu có StreamBuffer SQLite, cũng ghi đồng bộ
        if self.stream_buffer is not None:
            for r in validated_records:
                try:
                    s_rec = StreamRecord(
                        timestamp=r["ts"],
                        unit_serial=r["unit_serial"],
                        jig_id=r["jig_id"],
                        metric=r["metric_name"],
                        value=r["value"],
                        unit=r["unit"],
                        status=r["target_label"],
                        nguon=r["nguon"],
                    )
                    self.stream_buffer.append_idempotent(s_rec)
                except Exception:
                    pass

        # 4. Chạy cổng cảnh báo SMA(20) cho các chuỗi thông số trong lô
        ket_qua_cong = self._chay_cong_canh_bao_cho_lo(validated_records)

        so_vi_pham = sum(1 for k in ket_qua_cong if k.canh_bao)
        so_can_bien = sum(1 for k in ket_qua_cong if not k.canh_bao and k.trang_thai == "Cận biên")
        so_dat = sum(1 for k in ket_qua_cong if k.trang_thai == "Đạt")

        thong_diep = (
            f"Đã tiếp nhận {tong_da_ghi}/{len(validated_records)} bản ghi vào kho "
            f"({'MÔ PHỎNG (Tách biệt)' if la_toan_bo_mo_phong else 'SẢN XUẤT'}). "
            f"Cổng SMA(20): {so_vi_pham} vi phạm, {so_can_bien} cận biên, {so_dat} đạt chuẩn."
        )

        return KetQuaTiepNhanLo(
            thanh_cong=True,
            trang_thai="Đã tiếp nhận thành công",
            tong_so_nhan=len(parsed_records),
            da_ghi_kho=tong_da_ghi,
            bo_qua_rong=bo_qua_rong,
            la_mo_phong=la_toan_bo_mo_phong,
            nguon=nguon_chinh,
            kho_luu_tru=str(target_kho_path),
            danh_sach_danh_gia_cong=ket_qua_cong,
            so_canh_bao_vi_pham=so_vi_pham,
            so_can_bien=so_can_bien,
            so_dat_chuan=so_dat,
            thong_diep=thong_diep,
        )

    def _ghi_danh_sach(self, records: List[Dict[str, Any]], kho_path: Path) -> Dict[str, int]:
        """Ghi danh sách bản ghi dạng dict vào kho JSONL."""
        luc = datetime.now(VIETNAM_TZ).replace(microsecond=0)
        moc = luc.isoformat()
        dong_kho: List[DongKhoLog] = []
        bo_qua_rong = 0

        for r in records:
            if r.get("value") is None:
                bo_qua_rong += 1
                continue
            dong_kho.append(
                DongKhoLog(
                    ts=r.get("ts"),
                    ghi_luc=moc,
                    nguon=r.get("nguon", NGUON_THAT),
                    tep=r.get("tep", r.get("jig_id", "")),
                    unit_serial=r.get("unit_serial", ""),
                    jig_id=r.get("jig_id", ""),
                    metric_name=r.get("metric_name", ""),
                    value=float(r["value"]),
                    unit=r.get("unit", ""),
                    target_label=r.get("target_label", "OK"),
                )
            )

        if not dong_kho:
            return {"da_ghi": 0, "bo_qua_rong": bo_qua_rong}

        kho_path.mkdir(parents=True, exist_ok=True)
        # Ghi vào tệp tháng
        file_path = kho_path / f"{luc.strftime('%Y-%m')}.jsonl"
        with file_path.open("a", encoding="utf-8") as f:
            for d in dong_kho:
                f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")

        return {"da_ghi": len(dong_kho), "bo_qua_rong": bo_qua_rong}

    def _chay_cong_canh_bao_cho_lo(
        self, records: List[Dict[str, Any]]
    ) -> List[DanhGiaCongThongSo]:
        """Đánh giá cổng SMA(20) tức thì cho từng (jig_id, metric) trong lô."""
        # Gom các giá trị mới theo (jig_id, metric, is_simulated)
        nhom_moi: Dict[Tuple[str, str, bool], List[float]] = defaultdict(list)
        for r in records:
            val = r.get("value")
            if val is not None:
                is_sim = str(r.get("nguon", "")).startswith("SIMULATED_")
                nhom_moi[(r["jig_id"], r["metric_name"], is_sim)].append(float(val))

        ket_qua_cong: List[DanhGiaCongThongSo] = []

        for (jig_id, metric, is_sim), vals_moi in nhom_moi.items():
            # Lấy chuỗi lịch sử từ kho tương ứng
            target_kho = self.kho_mo_phong if is_sim else self.kho_that
            lich_su = lich_su_theo_jig(
                target_kho,
                jig_id=jig_id,
                metric_name=metric,
                limit=100,
                chi_mo_phong=is_sim,
                chi_that=not is_sim,
            )

            # Chuỗi đánh giá = lịch sử + giá trị mới trong lô
            chuoi_toan_bo = lich_su + vals_moi

            # Chạy cổng SMA(20)
            eval_res = danh_gia_xu_huong_sma(
                chuoi_toan_bo,
                window=self.window,
                k=K_DEFAULT,
            )

            so_lien_tiep = int(eval_res.get("so_diem_lien_tiep", 0) or eval_res.get("consecutive", 0))
            trang_thai = str(eval_res.get("trang_thai", "Đạt"))
            canh_bao = bool(eval_res.get("canh_bao", False))

            # Bảo đảm nguyên tắc chống báo ảo:
            # Nếu chỉ có 1 điểm đơn lẻ -> "Cận biên", canh_bao = False
            if canh_bao and so_lien_tiep < 3:
                trang_thai = "Cận biên"
                canh_bao = False

            ket_qua_cong.append(
                DanhGiaCongThongSo(
                    jig_id=jig_id,
                    metric=metric,
                    so_diem_moi=len(vals_moi),
                    gia_tri_cuoi=vals_moi[-1] if vals_moi else None,
                    sma=eval_res.get("sma"),
                    muc_lech=str(eval_res.get("muc_lech") or "—"),
                    so_diem_lien_tiep=so_lien_tiep,
                    trang_thai=trang_thai,
                    canh_bao=canh_bao,
                    chi_tiet=str(eval_res.get("chi_tiet") or ""),
                    la_mo_phong=is_sim,
                )
            )

        return ket_qua_cong


def tiep_nhan_lo_ban_ghi_jig(
    records: Union[Sequence[Dict[str, Any]], str],
    *,
    kho_that: Union[str, Path] = MAC_DINH_KHO_PATH,
    kho_mo_phong: Union[str, Path] = MAC_DINH_KHO_MO_PHONG_PATH,
    nguon_mac_dinh: str = NGUON_THAT,
) -> KetQuaTiepNhanLo:
    """Tiện ích độc lập tiếp nhận một lô bản ghi log JIG và trả về kết quả."""
    receiver = JigIngestReceiver(kho_that=kho_that, kho_mo_phong=kho_mo_phong)
    return receiver.tiep_nhan_lo(records, nguon_mac_dinh=nguon_mac_dinh)


def sinh_du_lieu_mo_phong_tu_log_that(
    csv_that_path: Union[str, Path],
    *,
    metric_name: str = "TaktTime",
    kich_ban: str = "binh_thuong",
    tag_mo_phong: str = "SIMULATED_JIG_BEAM",
) -> List[Dict[str, Any]]:
    """Trích xuất từ tệp log JIG thật (2026_08_Master.csv) và sinh dữ liệu mô phỏng.

    Các kịch bản kiểm chứng:
    1. 'binh_thuong': 40 điểm ổn định quanh giá trị nền thật (Đạt chuẩn).
    2. 'don_le': 40 điểm nền + 1 điểm dị biệt bất thường đơn lẻ (Cận biên, không cảnh báo).
    3. 'xu_huong_troi': 40 điểm nền + 4 điểm dị biệt bất thường liên tiếp (Vi phạm, kích hoạt cảnh báo).
    """
    path = Path(csv_that_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp log thật: {path}")

    # Đọc tệp log thật bằng csv.reader
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise ValueError(f"Tệp log {path.name} không có dòng tiêu đề.")

        # Tìm cột Date, Time, S/N, metric
        col_map = {name.strip().upper(): i for i, name in enumerate(header)}
        idx_date = col_map.get("DATE")
        idx_time = col_map.get("TIME")
        idx_sn = col_map.get("SERIAL NUMBER") or col_map.get("S/N") or col_map.get("SERIAL")
        idx_val = col_map.get(metric_name.upper())

        if idx_val is None:
            # Fallback lấy cột đầu tiên có giá trị số
            idx_val = 5

        row_idx = 0
        base_vals: List[float] = []
        for row in reader:
            if not row or len(row) <= idx_val:
                continue
            v_str = row[idx_val].strip().replace(",", ".")
            try:
                val = float(v_str)
                base_vals.append(val)
                row_idx += 1
            except (ValueError, TypeError):
                continue
            if row_idx >= 45:
                break

    if not base_vals:
        base_vals = [140.0] * 40

    mean_base = sum(base_vals[:30]) / max(1, len(base_vals[:30]))

    # Sinh chuỗi theo kịch bản
    generated_values: List[float] = []
    if kich_ban == "binh_thuong":
        # 40 điểm nền bình thường
        generated_values = (base_vals[:40] if len(base_vals) >= 40 else base_vals * 2)[:40]
    elif kich_ban == "don_le":
        # 40 điểm nền + 1 điểm dị biệt
        nen = (base_vals[:40] if len(base_vals) >= 40 else base_vals * 2)[:40]
        diem_di_biet = mean_base * 2.5 + 50.0
        generated_values = nen + [diem_di_biet]
    elif kich_ban == "xu_huong_troi":
        # 40 điểm nền + 4 điểm xấu liên tiếp
        nen = (base_vals[:40] if len(base_vals) >= 40 else base_vals * 2)[:40]
        diem_xau = [mean_base * 2.0 + 30.0 + i * 5.0 for i in range(4)]
        generated_values = nen + diem_xau
    else:
        generated_values = base_vals[:40]

    # Đóng gói thành các bản ghi mô phỏng gắn mác SIMULATED_*
    mock_records: List[Dict[str, Any]] = []
    base_time = datetime(2026, 10, 15, 8, 0, 0)
    for i, val in enumerate(generated_values):
        t_cur = base_time + timedelta(minutes=i * 2)
        mock_records.append({
            "unit_serial": f"SIM-UNIT-{i:04d}",
            "jig_id": "2ND-1002_JIG_BEAM",
            "metric_name": metric_name,
            "value": round(val, 3),
            "unit": "s" if "takt" in metric_name.lower() else "mm",
            "status": "OK" if i < 40 else ("NG" if kich_ban == "xu_huong_troi" else "OK"),
            "timestamp": t_cur.isoformat(),
            "nguon": tag_mo_phong,
            "tep": "SIMULATED_2026_08_Master.csv",
        })

    return mock_records
