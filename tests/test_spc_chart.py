"""Contract tests for Monozukuri/SPC chart renderer (US12 T060)."""

from __future__ import annotations

from pathlib import Path

from aios_habit.production_prediction.spc_chart import (
    SpcChartInput,
    render_spc_png,
    render_spc_svg,
)


def _mau_bieu_do() -> SpcChartInput:
    values = [0.10, 0.11, 0.12, 0.13, 0.16, 0.20]
    return SpcChartInput(
        jig_id="JIG-BOWSKEW-4BEAM",
        cong_doan="LSU Iris",
        metric="bowskew",
        unit="mm",
        values=values,
        usl=0.22,
        lsl=0.05,
        ucl=0.20,
        cl=0.12,
        lcl=0.06,
        cpk=1.33,
        sigma=0.02,
        nguoi_phu_trach="Tổ trưởng ca",
        du_bao=[0.21, 0.22],
    )


def test_ve_png_2x_retina_300dpi(tmp_path: Path):
    out = tmp_path / "spc.png"
    result = render_spc_png(_mau_bieu_do(), out, scale=2)
    assert result.exists()
    from PIL import Image

    with Image.open(result) as image:
        assert image.size[0] >= 1500
        dpi = image.info.get("dpi", (0, 0))
        assert abs(dpi[0] - 300) < 0.01 and abs(dpi[1] - 300) < 0.01


def test_ve_svg_vector_co_tem_quan_ly():
    svg = render_spc_svg(_mau_bieu_do())
    assert "<svg" in svg
    assert "JIG-BOWSKEW-4BEAM" in svg
    assert "USL" in svg
    assert "Cpk" in svg


def test_thieu_du_lieu_bao_loi_tieng_viet():
    import pytest

    with pytest.raises(ValueError, match="Thiếu chuỗi giá trị"):
        render_spc_png(SpcChartInput(jig_id="JIG-01"), "khong_co.png")
