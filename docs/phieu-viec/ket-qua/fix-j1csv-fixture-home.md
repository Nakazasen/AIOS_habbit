# Báo cáo kết quả vé FIX-J1CSV-FIXTURE-HOME

- **Mã vé:** `FIX-J1CSV-FIXTURE-HOME`
- **Máy thực thi:** Máy nhà `h410asrock` (thợ agy — Python 3.11.14 `.venv`)
- **Nhánh:** `phieu-viec/rag-fix1`
- **Trạng thái:** **Hoàn thành 100%**, sẵn sàng nghiệm thu.
- **Nguồn gốc:** Phát hiện P0 #2 từ báo cáo [`docs/phieu-viec/ket-qua/audit-buoc2-jig-home.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/audit-buoc2-jig-home.md).

---

## 1. Bối cảnh & Điều kiện cổng gate

1. **Điều kiện mở cổng gate:**
   - Mailbox OMP ([`docs/phieu-viec/mailbox/trang-thai.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/mailbox/trang-thai.md)) đã có dòng verdict Muse **ĐẠT** cho vé `SMA-IMPROVE-HOME` (commit code `3c7f2f3` tại mốc ~23:30 2026-10-06 +07).
   - Điều kiện bắt đầu vé thỏa mãn 100%, cổng gate chính thức mở.

2. **Vấn đề cần giải quyết:**
   - Trước đây, test `test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh` trong [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py) dùng fixture với 1 điểm vi phạm đơn lẻ `99.9` trên nền 20 điểm `10.0`.
   - Cổng gate SMA(20) (từ commit `846713e` và hoàn thiện qua `SMA-IMPROVE-HOME`) chặn đúng các điểm xấu đơn lẻ (`canh_bao = False`), phân loại là "Cận biên" thay vì cảnh báo xu hướng. Do đó, biểu đồ cảnh báo không được kích hoạt tự động vẽ (`ket_qua.chart_png is None`), dẫn đến test bị lệch so với hành vi cổng gate sản phẩm hiện tại.

---

## 2. Chi tiết sửa đổi Fixture (Trước & Sau)

Chỉ chỉnh sửa tệp kiểm thử [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py), tuyệt đối không sửa code sản phẩm hay [`src/aios_habit/production_prediction/trend_alerts.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/trend_alerts.py).

### 2.1. Cập nhật fixture chuỗi 3 điểm xấu liên tiếp
- **Fixture cũ:**
  ```python
  history_provider=lambda jig, chi_so: [10.0] * 20,
  # Dòng log mới: "2026-10-01T10:00:00,U001,JIG-A,BOW_VALUE,99.9,um,OK"
  # -> Chỉ có 1 điểm 99.9 ở vị trí index 20.
  # -> consecutive = 1 < 3 -> canh_bao = False -> không tự động vẽ biểu đồ -> FAIL.
  ```
- **Fixture mới:**
  ```python
  history_provider=lambda jig, chi_so: [10.0] * 20 + [99.9, 99.9],
  # Dòng log mới: "2026-10-01T10:00:00,U001,JIG-A,BOW_VALUE,99.9,um,OK"
  # -> Chuỗi đánh giá gồm 20 điểm nền 10.0 và 3 điểm 99.9 liên tiếp (index 20, 21, 22).
  # -> Cả 3 điểm đều bất thường (nen_phang_nhung_lech, residual = 89.9 > 0).
  # -> consecutive = 3 >= DIEM_LIEN_TIEP_DEFAULT (3) -> canh_bao = True, Vi phạm -> PASS.
  ```

### 2.2. Bổ sung test đối chứng cho hành vi chặn điểm đơn lẻ
Bổ sung hàm kiểm thử mới `test_mot_diem_xau_don_le_bi_cong_gate_sma_chan_khong_tu_dong_ve()`:
```python
def test_mot_diem_xau_don_le_bi_cong_gate_sma_chan_khong_tu_dong_ve():
    """Điểm xấu đơn lẻ bị cổng SMA(20) chặn cảnh báo -> không tự động vẽ biểu đồ."""
    cau_hinh = AlertConfig(bieu_do_dinh_kem=["phan_bo"])
    dong_log = "2026-10-01T10:00:00,U001,JIG-A,BOW_VALUE,99.9,um,OK"
    ket_qua = decide_jig_action(
        dong_log,
        alert_config=cau_hinh,
        history_provider=lambda jig, chi_so: [10.0] * 20,
        chart_rows_provider=lambda: [
            dict(h, jig_id="JIG-A") for h in _hang_ve()
        ],
    )
    assert ket_qua.handled
    assert ket_qua.chart_png is None
    assert "tự động vẽ" not in ket_qua.assistant_text
```
Xác nhận trực tiếp rằng: 1 điểm đơn lẻ `99.9` trên nền 20 điểm `10.0` được cổng SMA(20) chặn cảnh báo đúng theo thiết kế, bảo vệ hệ thống khỏi báo động giả.

---

## 3. Thống kê kiểm thử (Trước & Sau)

| Bộ kiểm thử | Trước khi sửa | Sau khi sửa | Trạng thái |
|---|:---:|:---:|:---:|
| [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py) | 1 failed, 10 passed, 4 skipped | **12 passed, 4 skipped** | **Xanh 100%** (12/12 test chạy được) |
| [`tests/test_trend_alerts.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_trend_alerts.py) | 22 passed | **22 passed** | **Xanh 100%**, không đỏ thêm |
| Hồi quy liên quan (`jig or trend or alert`) | - | **178 passed** (4012 deselected) | **Xanh 100%** |

---

## 4. Xác nhận khớp hành vi cổng gate sau SMA-IMPROVE-HOME

1. **Khớp logic gate:** Cổng SMA(20) trong `trend_alerts.py` đòi hỏi tối thiểu 3 điểm liên tiếp hoặc $\ge 3$ điểm trong cửa sổ nhìn lại 5 điểm để kích hoạt cảnh báo xu hướng. Chuỗi 3 điểm xấu liên tiếp trong fixture mới thỏa mãn chuẩn xác quy tắc này.
2. **Khớp giao diện & tính năng tự động vẽ:** Khi `canh_bao = True`, `decide_jig_action` tự động kích hoạt `_bieu_do_canh_bao_tu_dong` vẽ đúng biểu đồ phân bố đã cấu hình và đính kèm thông điệp hướng dẫn gửi email.
3. **Rào cứng bất biến được bảo đảm:**
   - **Rào 1 file 1 đứa:** Không chạm vào `trend_alerts.py` (file của OMP) hay bất kỳ file UI nào.
   - **Phạm vi thay đổi:** Chỉ sửa đổi duy nhất tệp [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py).
   - **Python version:** Chuẩn Python 3.11, không sử dụng tính năng/cú pháp 3.12+.
   - **Không đụng main:** Toàn bộ công việc thực hiện trên nhánh `phieu-viec/rag-fix1`.

---

## 5. Kết quả cổng kiểm định chất lượng (Quality Gates)

| Cổng kiểm định | Lệnh thực thi | Kết quả | Bằng chứng |
|---|---|:---:|---|
| **Compileall** | `uv run --no-sync --group dev python -m compileall src tests` | **PASS** | Exit code 0, không có lỗi cú pháp |
| **CLI Audit** | `uv run --no-sync --group dev python -m aios_habit.cli audit` | **PASS** | `{"errors": [], "status": "PASS", "warnings": []}` |
| **Import App** | `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` | **PASS** | `IMPORT_OK` |
