# Báo cáo vé SMA-IMPROVE-HOME — Cải tiến cổng SMA(20) theo kết quả đo thật

- Mã vé: `SMA-IMPROVE-HOME`
- Máy thực thi: máy nhà `h410asrock` (Windows 10 Pro x64, Python 3.11.14 qua `uv run`)
- Nhánh: `phieu-viec/rag-fix1` (không merge `main`, không ghi index)
- Máy đo lại (bước chốt): `h410asrock`, 2026-10-06 22:2x–22:3x +07, nhánh `phieu-viec/rag-fix1` tại `3c7f2f3`.
- Nguồn yêu cầu: `docs/phieu-viec/ket-qua/sma-gate-realdata-home.md` §4–§5 (verdict ĐẠT 2026-10-06)
- Trạng thái: **Hoàn thành, chờ duyệt** (chốt 2026-10-06 ~23:1x +07; đo lại + cổng repo
  đầy đủ ở bước chốt; `pytest -q` 4109 đạt, 43 ca đỏ ngoài vùng vé đã phân loại).

## 1. Thay đổi code (đúng rào 1-file-1-đứa)

Chỉ sửa `src/aios_habit/production_prediction/trend_alerts.py` (+ test của nó).
Không đổi hợp đồng `danh_gia_xu_huong_sma` / `gate_canh_bao_theo_xu_huong`
(chỉ thêm tham số tùy chọn `nhom_chi_so`, `deadband`; không truyền gì mới
thì hành vi cũ giữ nguyên 100%).

### 1.1. Deadband cho nhánh `nen_phang_nhung_lech`

- Vấn đề: cảm biến trả giá trị làm tròn đứng yên (vd 24.3°C suốt 20 dòng)
  → sigma=0 → lệch 0.1°C cũng bị gắn bất thường, rồi bị mask khỏi baseline
  khiến các điểm sau tiếp tục rơi vào bẫy sigma=0.
- Sửa: nhánh sigma==0 chỉ gắn bất thường khi `|residual| >= deadband_theo_chi_so`.
  Giá trị deadband đã chốt bằng đo thật (mục 2): nhiệt độ **0.5°C**,
  độ ẩm **2.0%**, TaktTime **10.0s**.
- Tham số hóa (không hardcode): `deadband_cho_chi_so(nguong, deadband)` —
  truyền số trực tiếp được ưu tiên cao nhất; truyền mapping thì tra theo
  `NguongChiSo.chi_so`; không truyền thì dùng bảng mặc định theo chỉ số;
  pure SPC (không ngưỡng) thì deadband=0.0 → giữ hành vi cũ.
- Điểm dưới deadband mang lý do mới `nen_phang_duoi_deadband` (báo bình thường)
  nhưng **vẫn mask khỏi baseline** — giữ nguyên động lực baseline đã được
  kiểm chứng 21/21 chặn (phát hiện khi thử nghiệm: bỏ mask làm baseline trôi,
  lọt 1 điểm Độ ẩm dòng 71 thành cảnh báo xu hướng giả; giữ mask thì 21/21).

### 1.2. k linh hoạt theo nhóm chỉ số

- `k_cho_nhom(nhom_chi_so, k)`: `k` truyền trực tiếp luôn thắng (tương thích ngược);
  không truyền `k` thì nhóm chu kỳ máy (`nhom_chi_so="chu_ky"`, vd TaktTime,
  phân phối lệch phải sigma ~35s) dùng **k=2.5**, còn lại dùng **k=3.0**.
- Hằng số: `K_MAC_DINH_NHOM_MOI_TRUONG = 3.0`, `K_MAC_DINH_NHOM_CHU_KY = 2.5`,
  `NHOM_CHU_KY = "chu_ky"`, `NHOM_MOI_TRUONG = "moi_truong"`.
- Ghi chú về `thresholds.yaml`: repo hiện chưa có file này (ngưỡng hiện hành
  là `NguongChiSo`/`metric_limits.json`); deadband + k đã tham số hóa qua
  tham số hàm + hằng số module, sẵn sàng chuyển sang `thresholds.yaml` khi
  file đó được lập (không hardcode giá trị vào logic nhánh).

## 2. Bảng trước/sau trên log JIG thật (132 dòng)

### 2.1. Điểm bất thường giả do `nen_phang_nhung_lech` (pure SMA + deadband theo chỉ số)

| Chỉ số | Trước (flat bất thường) | Sau (flat bất thường) | Sau (dưới deadband, báo bình thường) | Giảm giả |
|---|:---:|:---:|:---:|:---:|
| Nhiệt độ | 58 | **4** | 54 | **-93%** |
| Độ ẩm | 9 | **0** | 7 | **-100%** |
| TaktTime | 0 | 0 | 0 | giữ nguyên |

- Cách đo: `detect_abnormal_sma(values, window=20, k=3.0, nguong=None)` (trước)
  so với `detect_abnormal_sma(values, window=20, k=3.0, nguong=<NguongChiSo>)`
  (sau — truyền ngưỡng để tra deadband theo chỉ số).
- Nhiệt độ còn 4 điểm flat vượt deadband 0.5°C là các lần sụt/nhảy thật
  (vd 19.2°C sáng 10/08, 24.3→26.x), không phải nhiễu lượng tử hóa.
- Độ ẩm 2 điểm flat vượt ngưỡng cũ hóa ra là bước nhảy 33.9↔66% thật
  (chuyển sang `lech_xa_sma`/`vuot_nguong_that` đúng bản chất, không mất).

Chạy lại bước chốt 2026-10-06 ~22:30 +07 (`scripts/analyze_sma_gate_realdata.py`
nguyên vẹn, CSV gốc `2026_08_Master.csv` 132 dòng, kết quả JSON
`local_runs/sma_chot_20261006_22h.json`): gate chặn **21/21 vi phạm đơn điểm**
(ẩm 11 + Takt 8 + nhiệt 2), cảnh báo giả sau gate = 0; flat
`nen_phang_nhung_lech` còn lại: **nhiệt 4** (58→4, -93% — các lần sụt/nhảy thật),
**ẩm 0** (9→0 trong đó 2 điểm flat vượt ngưỡng cũ là bước nhảy 33.9↔66% thật,
được phân loại đúng bản chất, không mất).

| Chỉ số | Vi phạm đơn điểm | Chặn (trước) | Chặn (sau) | Cảnh báo giả sau gate |
|---|:---:|:---:|:---:|:---:|
| Độ ẩm (11) | 11 | 11 | **11** | 0 |
| TaktTime (8) | 8 | 8 | **8** | 0 |
| Nhiệt độ (2) | 2 | 2 | **2** | 0 |
| **Tổng** | **21** | **21** | **21 (100%)** | **0** |

- Khảo sát k=1.0–4.0 chạy lại khớp 100% số cũ (Humidity 12/0 tại k=3.0,
  TaktTime 0 tại k=3.0, Temperature 62 tại k=3.0) — không truyền tham số mới
  thì hành vi cũ giữ nguyên.
- k nhóm chu kỳ (2.5) trên TaktTime thật: 6/6 điểm vượt ngưỡng thật vẫn bắt
  đúng qua `vuot_nguong_that`; pure-SPC 8 đỉnh lệch-phải được tách tốt hơn
  ở k=2.5 (1 điểm) so với k=3.0 (0 điểm) theo bảng khảo sát cũ.

## 3. Test

- Test vé mới (8 test trong `tests/test_trend_alerts.py`):
  residual nhỏ dưới deadband → không bất thường; residual lớn → bất thường
  đúng lý do; pure SPC giữ hành vi cũ; deadband truyền trực tiếp ghi đè;
  `k_cho_nhom` mặc định theo nhóm; k nhóm bắt được đỉnh mà k=3.0 bỏ sót;
  điểm dưới deadband vẫn mask (lý do `nen_phang_duoi_deadband`);
  chuỗi dao động dưới deadband không tạo xu hướng giả.
- Hồi quy: `test_trend_alerts` + `test_trend_response` + `test_b4_trend_notify`
  + `test_trend_analysis` = **62/62 xanh** (chạy lại 2026-10-06 ~22:3x +07,
  đối chứng A/B nhánh B cũ 75/75 ↔ nhánh A mới 83/83 trên cùng 5 file trend).
- Cổng repo (chạy ở bước chốt 2026-10-06 ~22:3x +07, Python 3.11.14): `compileall` sạch
  (exit 0), `cli audit` PASS (`"status": "PASS"`, 0 lỗi/0 cảnh báo),
  `import workspace_chat_app` OK. `pytest -q` toàn bộ: **4109 đạt / 24 lỗi /
  37 bỏ qua / 19 error** (932,7s) — đã phân loại trọn 43 ca đỏ, **không ca nào
  thuộc mã vé**: 19 error thiếu file `D:/home/hatch/...` của VM; 24 lỗi thuộc
  nhóm packaging/privacy-dev/handoff/OCR/mạng/lifecycle/J1CSV + UI-nhãn i18n
  của commit khác (đối chứng A/B module cũ/mới: nhánh B 75/75 ↔ nhánh A 83/83
  trên 5 file trend — ca đỏ có sẵn trước vé, không do vé gây ra).

## 4. Rủi ro còn lại

- Deadband là hằng số module, chưa có `thresholds.yaml` để người vận hành
  chỉnh không cần đụng code — đã tham số hóa sẵn, chuyển sang file cấu hình
  khi vé lập file đó được duyệt.
- `ly_do` mới `nen_phang_duoi_deadband`: chỉ `trend_alerts.py` sinh ra,
  không có consumer nào đọc `ly_do` ngoài test (đã grep toàn repo) nên an toàn.
