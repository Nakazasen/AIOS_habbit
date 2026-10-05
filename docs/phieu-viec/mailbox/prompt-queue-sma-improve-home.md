# Vé SMA-IMPROVE-HOME — Cải tiến cổng SMA(20) theo kết quả đo thật (Bước 2)

**Máy thực hiện:** NHÀ h410asrock (thợ OMP).
**Role gợi ý:** DEFAULT (code + test).
**Nguồn yêu cầu:** `docs/phieu-viec/ket-qua/sma-gate-realdata-home.md` §4–§5
(vé `SMA-GATE-REALDATA-HOME`, verdict ĐẠT 2026-10-06).

## Bối cảnh

Đo trên log JIG thật (132 dòng) phát hiện 2 điểm cần sửa trong `trend_alerts.py`:
1. Nhánh `nen_phang_nhung_lech` (sigma==0): cảm biến trả giá trị làm tròn đứng yên
   (vd 24.3°C suốt 20 dòng) → sigma=0 → lệch 0.1°C cũng bị gắn bất thường
   (58/62 điểm Nhiệt độ, 9/12 điểm Độ ẩm là giả do hiện tượng này).
2. k=3.0 cố định: hơi chặt với TaktTime (phân phối lệch phải, sigma ~35s).

## Việc cần làm

1. **Deadband cho `nen_phang_nhung_lech`:** chỉ gắn bất thường khi
   `|residual| >= nguong_toi_thieu_theo_chi_so`
   (gợi ý: nhiệt độ 0.5°C, độ ẩm 2.0%, TaktTime 10.0s — cấu hình qua `thresholds.yaml`,
   không hardcode; đo lại trên dữ liệu thật để chốt số).
2. **k linh hoạt theo nhóm chỉ số:** nhóm môi trường (nhiệt độ, độ ẩm) mặc định k=3.0;
   nhóm chu kỳ máy (TaktTime) mặc định k=2.0–2.5. Cấu hình qua `thresholds.yaml`.
3. Test: bổ sung test cho deadband (sigma=0 + residual nhỏ → không bất thường;
   residual lớn → bất thường) + test k theo nhóm. Chạy lại toàn bộ test trend cũ phải xanh.
4. Chạy lại script `scripts/analyze_sma_gate_realdata.py` (nếu còn) hoặc đo tương đương:
   xác nhận số điểm bất thường giả do `nen_phang_nhung_lech` giảm mạnh, 21/21 vi phạm
   đơn điểm vẫn bị chặn đúng.

## Rào cứng

- 1 file 1 đứa: chỉ sửa `trend_alerts.py` (+ test của nó). Không đụng UI
  (vé `SMA-WARMUP-LABEL-HOME` của agy làm phần nhãn warmup song song).
- Không đổi hợp đồng hàm (`danh_gia_xu_huong_sma`, `gate_canh_bao_theo_xu_huong`).
- Python 3.11. Không merge `main`. Không ghi index.

## Báo cáo

`docs/phieu-viec/ket-qua/sma-improve-home.md` — bảng trước/sau số điểm bất thường giả,
giá trị deadband đã chốt, kết quả test.
