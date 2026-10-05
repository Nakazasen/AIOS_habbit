# Báo cáo triển khai nhãn tích lũy dữ liệu nền (Warmup Label) trên thẻ kiểm tra

- Mã vé: `SMA-WARMUP-LABEL-HOME`
- Máy thực thi: máy nhà `h410asrock` (Windows 10 Pro x64, Python 3.11.14 `.venv`)
- Nhánh: `phieu-viec/rag-fix1`
- Trạng thái: **Hoàn thành 100%**, sẵn sàng nghiệm thu.
- Nguồn yêu cầu: [`docs/phieu-viec/ket-qua/sma-gate-realdata-home.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/sma-gate-realdata-home.md) §5.2 mục 3 ("Cơ chế khởi động mềm / Warmup window").

---

## 1. Bối cảnh & Mục tiêu

Cổng cảnh báo xu hướng SMA(20) cần tối thiểu 20 điểm nền để kết luận xu hướng. Khi tiếp nhận các lô đo ngắn hoặc các lần kiểm tra đầu ca (chuỗi dữ liệu $N < 20$ điểm), người vận hành dễ băn khoăn vì sao chưa thấy xuất hiện các cảnh báo xu hướng.

Vé này bổ sung nhãn giải thích rõ ràng và minh bạch ngay trên thẻ kiểm tra log tức thì (instant card):
1. Khi chuỗi dữ liệu có $N < 20$ điểm: hiển thị thêm dòng thông điệp:
   `"Đang tích lũy dữ liệu nền (N/20 điểm) — chưa đủ cơ sở kết luận xu hướng."`
2. Khi $N \ge 20$ điểm: ẩn hoàn toàn dòng này để giữ giao diện thẻ ngắn gọn, sạch sẽ.
3. Đáp ứng kiểm thử mọi mốc: $N = 0$, $N = 5$, $N = 20$, $N = 25$.
4. Tuân thủ nghiêm ngặt các rào cứng của kiến trúc:
   - **Rào cứng 1 file 1 đứa**: Tuyệt đối không chạm vào `src/aios_habit/production_prediction/trend_alerts.py` (đang dành cho vé song song `SMA-IMPROVE-HOME` của OMP).
   - **Chuỗi nhãn chuẩn hóa i18n**: Nhãn được khai báo tập trung trong `src/aios_habit/i18n.py` với key parity 100% qua 3 ngôn ngữ (`vi`, `ja`, `zh-CN`).
   - Môi trường chuẩn Python 3.11, không merge `main`.

---

## 2. Các tệp đã sửa đổi & Giải pháp kỹ thuật

| STT | Tệp sửa đổi | Vai trò kỹ thuật |
|:---:|---|---|
| 1 | [`src/aios_habit/production_prediction/jig_alert_cards.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_alert_cards.py) | Bổ sung hàm `tao_nhan_warmup()`, `trich_so_diem_nen()`, mở rộng tham số `so_diem: Optional[int] = None` trong `build_instant_log_card()`, gắn các trường `nhan_warmup` và `so_diem` vào cấu trúc thẻ dict. |
| 2 | [`src/aios_habit/production_prediction/jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_chat_wire.py) | Cập nhật `format_instant_card_text()` tự động bổ sung dòng nhãn warmup vào tin nhắn chat text; truyền `so_diem = len(history) + 1` tại cả 3 nhánh tiếp nhận log JIG (dòng depth, dòng rộng Iris, dòng đơn chuẩn). |
| 3 | [`src/aios_habit/i18n.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/i18n.py) | Khai báo key `jig_instant_card_warmup` cho đủ 3 ngôn ngữ tiếng Việt, tiếng Nhật, tiếng Trung (Giản thể). |
| 4 | [`src/aios_habit/workspace_chat_ui.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_ui.py) | Cập nhật `render_jig_instant_log_card()` hiển thị `st.caption(t("jig_instant_card_warmup", ...))` qua i18n. |
| 5 | [`tests/test_jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_jig_chat_wire.py) | Thêm 3 test case mới kiểm tra toàn diện các mức $N=0$, $N=5$, $N=20$, $N=25$, routing end-to-end `decide_jig_action`, và key parity i18n. |

---

## 3. Bằng chứng Text Render mẫu thực tế

Dưới đây là kết quả render thực tế từ hàm `format_instant_card_text()` của module `jig_chat_wire.py`:

### 3.1. Khi $N = 0$ điểm (Khởi tạo chưa có điểm nền nào)
```text
Kết luận: Cần kiểm tra — 2ND-1002_001 — TaktTime (Cận biên)
Giá trị: 28.5 s | JIG: 2ND-1002
Điểm đo nằm trong giới hạn kiểm soát.
Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].
Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi
Đang tích lũy dữ liệu nền (0/20 điểm) — chưa đủ cơ sở kết luận xu hướng.
```
> Nhận xét: Hiển thị rõ ràng dòng `"Đang tích lũy dữ liệu nền (0/20 điểm) — chưa đủ cơ sở kết luận xu hướng."`.

### 3.2. Khi $N = 5$ điểm (Chuỗi đo ngắn, đang tích lũy)
```text
Kết luận: Cần kiểm tra — 2ND-1002_001 — TaktTime (Cận biên)
Giá trị: 28.5 s | JIG: 2ND-1002
Điểm đo nằm trong giới hạn kiểm soát.
Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].
Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi
Đang tích lũy dữ liệu nền (5/20 điểm) — chưa đủ cơ sở kết luận xu hướng.
```
> Nhận xét: Hiển thị đúng số điểm tích lũy thực tế $5/20$, người dùng hiểu ngay hệ thống đang trong giai đoạn warmup.

### 3.3. Khi $N = 20$ điểm (Đã đủ 20 điểm nền)
```text
Kết luận: Cần kiểm tra — 2ND-1002_001 — TaktTime (Cận biên)
Giá trị: 28.5 s | JIG: 2ND-1002
Điểm đo nằm trong giới hạn kiểm soát.
Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].
Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi
```
> Nhận xét: Dòng nhãn warmup tự động biến mất, giao diện thẻ được thu gọn, hoàn toàn không bị rác màn hình.

---

## 4. Kết quả kiểm thử tự động (Unit Test & Contract Test)

Chạy kiểm thử với `pytest -v tests/test_jig_chat_wire.py`:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0 -- D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Sandbox\AIOS_habbit
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 17 items

tests/test_jig_chat_wire.py::test_dong_log_jig_duoc_xu_ly_khong_qua_rag PASSED [  5%]
tests/test_jig_chat_wire.py::test_cau_hoi_thuong_khong_bi_chan PASSED    [ 11%]
tests/test_jig_chat_wire.py::test_lenh_xem_cai_dat_hien_bang PASSED      [ 17%]
tests/test_jig_chat_wire.py::test_lenh_them_email_va_doi_nguong PASSED   [ 23%]
tests/test_jig_chat_wire.py::test_lenh_truc_ban_doi_persona PASSED       [ 29%]
tests/test_jig_chat_wire.py::test_di_lich_su_ewma_cho_danh_gia_xu_huong PASSED [ 35%]
tests/test_jig_chat_wire.py::test_xu_huong_lien_tiep_thi_canh_bao PASSED [ 41%]
tests/test_jig_chat_wire.py::test_dau_noi_app_luu_tin_nhan_va_cau_hinh PASSED [ 47%]
tests/test_jig_chat_wire.py::test_dau_noi_app_bo_qua_cau_thuong PASSED   [ 52%]
tests/test_jig_chat_wire.py::test_the_kiem_tra_log_mo_dau_bang_ket_luan_mot_cau PASSED [ 58%]
tests/test_jig_chat_wire.py::test_tra_loi_bieu_do_kem_bang_so_van_ban PASSED [ 64%]
tests/test_jig_chat_wire.py::test_ung_dung_co_nut_tam_dung_tiep_tuc_luong_truc_tiep PASSED [ 70%]
tests/test_jig_chat_wire.py::test_xu_huong_xau_kem_phan_doan_va_de_xuat PASSED [ 76%]
tests/test_jig_chat_wire.py::test_khong_co_xu_huong_thi_khong_phan_doan PASSED [ 82%]
tests/test_jig_chat_wire.py::test_sma_warmup_label_cac_muc_n PASSED      [ 88%]
tests/test_jig_chat_wire.py::test_sma_warmup_label_decide_jig_action_routing PASSED [ 94%]
tests/test_jig_chat_wire.py::test_sma_warmup_label_i18n_key_parity PASSED [100%]

============================= 17 passed in 0.58s ==============================
```

- Kiểm thử tương thích các module liên quan:
  - `tests/test_i18n.py`: **14/14 PASSED** (100% key parity).
  - `tests/test_omnibar_jig_log_ingest.py`: **8/8 PASSED**.

---

## 5. Bằng chứng cổng chất lượng bắt buộc (Quality Gates)

1. **Python 3.11 Runtime**:
   - `python --version`: `Python 3.11.14`
2. **Biên dịch mã nguồn (Bytecode Compilation)**:
   - Lệnh: `uv run --no-sync --group dev python -m compileall src tests`
   - Kết quả: **PASS 100%**, mã thoát 0, không có lỗi cú pháp.
3. **Audit kiểm tra vi phạm**:
   - Lệnh: `uv run --no-sync --group dev python -m aios_habit.cli audit`
   - Kết quả:
     ```json
     {
       "errors": [],
       "status": "PASS",
       "warnings": []
     }
     ```
4. **Kiểm tra nạp ứng dụng**:
   - Lệnh: `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`
   - Kết quả: **`IMPORT_OK`**.

---

## 6. Kết luận & Đề xuất

Vé `SMA-WARMUP-LABEL-HOME` đã giải quyết triệt để vấn đề phản hồi trực quan khi chuỗi dữ liệu chưa đủ 20 điểm nền theo SMA(20). Code được tổ chức gọn gàng, cách ly hoàn toàn với file `trend_alerts.py`, tương thích đa ngôn ngữ qua i18n, các test case xanh 100% và toàn bộ cổng chất lượng bắt buộc đều đạt tiêu chuẩn. Kính trình Muse nghiệm thu.
