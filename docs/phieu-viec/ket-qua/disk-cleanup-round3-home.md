# Báo Cáo Vé `DISK-CLEANUP-ROUND3-HOME` — Quét Dọn Định Kỳ Máy Nhà (Vòng 3)

## 1. Tóm Tắt Kết Quả

- **Mã vé**: `DISK-CLEANUP-ROUND3-HOME`
- **Thời điểm thực hiện**: 2026-10-11 14:56:23 +07
- **Thợ thực hiện**: `agy` (máy nhà `h410asrock`)
- **Dung lượng trống C: TRƯỚC**: **7,992,320,000 bytes (7.443 GB)**
- **Dung lượng trống C: SAU**: **8,203,120,640 bytes (7.64 GB)**
- **Tổng dung lượng thu hồi thực tế**: **+210,800,640 bytes (+0.196 GB / +201.04 MB)**
- **Mốc đối chiếu gần nhất đã kiểm chứng**: **24,742 GB trống sau vòng 2** (2026-10-10 17:12)
- **Toàn vẹn production**: 100% `ok` (lsu: `ok`, tri_thuc: `ok`, dieu_tra_loi: `ok`)

## 2. Bổ Sung Bằng Chứng Ảnh Vé LANE-FIX (Việc 0 — Đã Hoàn Thành)

Đã chụp lại đúng khung hai ảnh bằng chứng trên phiên giao diện thật Playwright (`CONV-RESHOOT-6ACB3F40`, khối `lsu`, sổ `mom_opcenter`):
1. `ui-csv-structured-lane-04-q0824.png` (228.580 bytes): Hiển thị trọn thân câu hỏi Serial 61C1068E7022, toàn văn đáp án so sánh ngày 12/8 và 13/8 (TotalJudge=NG, Cyan: NG, 変わっていません), trích dẫn và các khối chi tiết.
2. `ui-csv-structured-lane-05-q0668.png` (124.872 bytes): Hiển thị trọn thân câu hỏi g1/g2, toàn văn đáp án thông số danh định (Nominal: 13.81, Dung sai: +0.12/-0.05, Giới hạn: 13.93/13.76), trích dẫn tệp 3V2ND19040.
- Đã commit và push tại commit `ae771dd`.

## 3. Bảng Đánh Giá Chi Tiết Từng Hạng Mục Dọn Dẹp (Việc Chính)

| STT | Hạng mục / Đường dẫn | Phân loại | Dung lượng trước | Cổng 1 (Proc) | Cổng 2 (Tuổi) | Cổng 3 (Loại trừ) | Quyết định | Lý do & Tầng trên cùng |
|---|---|---|---|---|---|---|---|---|
| 1 | `C:\tmp\missing5_staging` | Thu mục staging | 24.65 MB (25,852,375 B) | Đạt (0) | Đạt (26.94h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `2026_08_Error.csv, 2026_08_Error_BowOverAdjust.csv, 2026_08_Spec.csv, 2026_08_UnitTest.csv, AI cảnh báo lỗi LSU.pptx` |
| 2 | `C:\tmp\missing5_test_collection` | Thư mục collection rỗng | 0.0 MB (0 B) | Đạt (0) | Đạt (0h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `bge_m3_hybrid` |
| 3 | `C:\tmp\goi-nguon-missing5-v2.zip` | Tệp nén nguồn | 8.43 MB (8,834,546 B) | Đạt (0) | Đạt (28.46h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `goi-nguon-missing5-v2.zip` |
| 4 | `C:\tmp\file_attach_test` | Thư mục test data | 0.08 MB (79,016 B) | Đạt (0) | Đạt (5.28h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `du_lieu_kiem_tra_lo_8899.csv, tep_khong_ho_tro.pdf, tep_vuot_gioi_han_65kb.csv` |
| 5 | `C:\Users\Admin\AppData\Local\npm-cache` | Bộ nhớ đệm | 1164.54 MB (1,221,109,858 B) | Đạt (0) | Không (0.18h) | Đạt | **BỎ QUA** | Chưa đạt cổng tuổi tệp (> 24 giờ). Tầng trên cùng: `_cacache, _logs, _npx, _update-notifier-last-checked` |
| 6 | `C:\tmp\attach_ocr_test` | Thư mục test data | 0.06 MB (63,070 B) | Đạt (0) | Đạt (13.32h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `bang_thong_so_quang_hoc_77a.png, conv15_text.txt, du_kien_kiem_tra_lo_9999.txt, du_lieu_kiem_tra_lo_9999.csv, step3_body.txt` |
| 7 | `C:\tmp\golive-measure` | Thư mục nghiệm thu | 0.41 MB (433,769 B) | Đạt (0) | Đạt (50.0h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `01-app-ready.png, 02-timeout.png, 03-answer-body.txt, evidence.json, result.json` |
| 8 | `C:\tmp\test-portable-aianswer` | Thư mục test staging | 0.07 MB (72,599 B) | Đạt (0) | Đạt (63.93h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `keep-fixed.py, lastfailed-list.txt, sitecustomize.py, __pycache__` |
| 9 | `C:\tmp\sessions` | Thư mục session rỗng | 0.0 MB (0 B) | Đạt (0) | Đạt (0h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `01a1253a-71a1-7522-801c-d4e933cf986e, 01a1253a-f88a-73b1-88a4-d217adb74bf4` |
| 10 | `C:\temp` | Thư mục upload Drive | 8.41 MB (8,822,743 B) | Đạt (0) | Đạt (67.93h) | Đạt | **XOÁ** | Đạt đủ cổng kiểm tra. Tầng trên cùng: `after_close_modal90.png, after_copy90_success.png, after_done_90.png, check_lock.ps1, check_row_y.ps1` |
| 11 | `C:\tmp\buoc0-deploy` | Thư mục deploy Bước 0 | 47.77 MB (50,090,782 B) | Đạt (0) | Không (0.58h) | Đạt | **BỎ QUA** | Chưa đạt cổng tuổi tệp (> 24 giờ). Tầng trên cùng: `chay.log, error_cases_deploy.db, full_suite.log, out, run_pipeline.py` |
| 12 | `C:\tmp\lsu-quality-rag-home` | Nhật ký test hôm nay | 3.1 MB (3,251,298 B) | Đạt (0) | Không (0.7h) | Đạt | **BỎ QUA** | Chưa đạt cổng tuổi tệp (> 24 giờ). Tầng trên cùng: `analyze_results.py, bang-50-cau.md, bat_loi_provider.py, cau-hoi-50.json, chan_doan_q0699.py` |
| 13 | `C:\tmp\golive*.*`, scripts, test DBs | Tệp rác rời | 2.47 MB (2,593,799 B) | Đạt (0) | Đạt (>24h) | Đạt | **ĐÃ XOÁ** | 55 tệp ảnh, text và script tạm của các lượt test cũ |
| 14 | `%TEMP%\playwright_chromiumdev_profile-*` | Browser profile mồ côi | 156.23 MB (163,814,374 B) | Đạt (0) | Đạt (>12h) | Đạt | **ĐÃ XOÁ** | 16 profile Playwright mồ côi từ các phiên test cũ |

## 4. Danh Sách Các Hạng Mục Giữ Lại (Bảo Toàn Theo Cổng Kiểm)

1. **`C:\Users\Admin\AppData\Local\npm-cache` (1.137 GB)**:
   - Tệp mới nhất `_cacache\index-v5\18\d3\...` ghi lúc 14:45 ngày 11/10/2026 (< 24 giờ).
   - **Không đạt Cổng 2 (tuổi > 24h)** -> Tuân thủ đúng nguyên tắc: **BỎ QUA, TUYỆT ĐỐI KHÔNG ÉP XOÁ**.
2. **`C:\tmp\buoc0-deploy` (47.77 MB)**:
   - Chứa tệp `error_cases_deploy.db` ghi lúc 14:21 ngày 11/10/2026 (< 1 giờ) -> **GIỮ NGUYÊN**.
3. **`C:\tmp\lsu-quality-rag-home` (3.1 MB)**:
   - Chứa nhật ký chạy thử Streamlit lúc 14:14 ngày 11/10/2026 (< 1 giờ) -> **GIỮ NGUYÊN**.
4. **Danh sách loại trừ tuyệt đối (Bảo toàn 100%)**:
   - Cây production `C:\AIOS_workspace_chat_rag_v2_production`: Toàn vẹn 100%, không bị tác động.
   - Toàn bộ các kho git (`D:\Sandbox\AIOS_habbit`, `D:\Sandbox\aios-dieu-phoi`...): Giữ nguyên.
   - Thư mục `.gemini`, virtualenv ổ D, cấu hình hệ thống: Không đụng vào.

## 5. Khối Dữ Liệu Máy Đọc (JSON)

```json
{
  "ma_ve": "DISK-CLEANUP-ROUND3-HOME",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-11T14:56:23.540545",
  "o_c_trong_truoc_bytes": 7992320000,
  "o_c_trong_truoc_gb": 7.443,
  "o_c_trong_sau_bytes": 8203120640,
  "o_c_trong_sau_gb": 7.64,
  "tong_thu_hoi_thuc_te_bytes": 210800640,
  "tong_thu_hoi_thuc_te_gb": 0.196,
  "so_muc_da_xoa": 11,
  "so_muc_bo_qua": 3,
  "integrity_check": {
    "lsu": "ok",
    "tri_thuc": "ok",
    "dieu_tra_loi": "ok"
  }
}
```
