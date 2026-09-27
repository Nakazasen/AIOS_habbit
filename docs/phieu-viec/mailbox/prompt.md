# Vé V1.3 — tải 4 file nguồn từ Drive rồi chạy nốt 10 test F4 trên Windows

Ngày viết: 2026-09-28 (Muse). Chế độ: Muse ra vé → OMP thực hiện độc lập trên Windows (luật "không vừa đá vừa thổi còi").
Branch: `phieu-viec/rag-fix1`. Không đụng `main`. Hostname: `h410asrock` (Win 10 Pro).

## Verdict Vé V1.2: CHƯA ĐẠT (không phải lỗi code)

- Vé V1.2 chạy đúng kịch bản "không tìm thấy nguồn thì dừng" (bước 6): quét `C:/Users`, `D:/`, `C:/tmp` — 0/4 file; không dùng file gần giống; 0 bịa dữ liệu; không ghi index, không ghi D.
- Kết quả: manifest 6/6 ✓, F1 15/15 ✓, F4 1/11 + 10 ERROR ở fixture `assert path.exists()` (thiếu nguồn). 0 test FAILED.
- Đã đối chiếu diff độc lập `de11b647...8c10f8c6`: chỉ 2 file báo cáo mới + mailbox, không đụng code, không đụng main. Báo cáo trung thực.
- Gốc rễ: 4 file nguồn xls không còn trên máy nhà. Muse đã đối chiếu bản Drive tải về VM (27/09) — đủ 4 file, đúng tên/kích thước, có sha256 xác minh dưới đây.

## 4 file nguồn (tải từ link Drive user đã cung cấp — nguồn hợp lệ)

Link file zip (user upload ngày 2026-09-27): `https://drive.google.com/file/d/1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP/view?usp=drive_link`
Sau giải nén, 4 file nằm trong cây `dieu_tra_loi/Điều chỉnh/`:

| File (GIỮ NGUYÊN tên, kể cả ký tự Nhật) | Kích thước (byte) | sha256 |
|---|---|---|
| `Bang ma loi/02XC_自己診断表示一覧表-Iris2020 VN.xls` | 1.278.976 | `031bbe3e447de2f2d5367a8f10fb875df7a3b7ecd5a9d3330860d15b38b20cc4` |
| `UWCAシステムエラー(FXXX)概要.xls` | 303.104 | `81c43cd46496d8f0069f7f40806ff6d6a3e9e5d14af26a5cf2d477709b94a458` |
| `SCT自動調整エラーコード一覧_140221.xls` | 294.400 | `6fe738d0d7ef00a45f881f9deb2354798aec0f840a2ce60948544164801f7749` |
| `Bang ma loi/02XC_機能定義書_JAM一覧 (1).xls` | 782.336 | `6c40012e780dbf83caaaeef5d50e9fbfdc5c387136c5b262a84edf2159088195` |

## Cách làm

1. Tải zip từ link Drive trên (thử `gdown`/công cụ tải Drive trước; bị chặn sign-in thì tải bằng trình duyệt khi đã đăng nhập tài khoản user). Zip ~858 MB.
2. Giải nén RA Ổ C (không bao giờ ghi ổ D) vào thư mục tạm mới, ví dụ `C:\tmp\aios-data-v13`. Nếu tên tiếng Nhật bị bung sai ký tự, giải nén lại bằng 7-Zip chế độ UTF-8 cho đến khi tên khớp y hệt bảng trên.
3. Đối chiếu 4 file: kích thước + sha256 PHẢI khớp bảng. **Lệch bất kỳ file nào → dừng, báo nguyên vẹn, không dùng file đó** (fail-closed, cấm bịa).
4. Đặt biến môi trường `AIOS_DATA_DIR` trỏ tới thư mục CHA của `dieu_tra_loi` (ví dụ `C:\tmp\aios-data-v13`), sao cho tồn tại `AIOS_DATA_DIR\dieu_tra_loi\Điều chỉnh\...` đúng cấu trúc zip.
5. Dùng lại môi trường Python 3.11.14 + pytest 8.4.2 của Vé V1 (venv trên C, TMP/TEMP trên C):
   - `pytest tests/test_rag_v2_ingest_manifest.py -q` → kỳ vọng 6/6.
   - `pytest tests/test_error_cases_f1.py tests/test_error_cases_f4.py -q` → kỳ vọng 26/26.
6. Nếu KHÔNG tải được zip sau 3 lần thử (tối đa): dừng, ghi rõ "không tải được nguồn" trong báo cáo — chờ Muse lo đường khác.

## Cấm kỵ (fail-closed)

- CHỈ đọc + chạy test. Cấm ghi index, cấm embed/apply/ingest thật.
- Cấm vĩnh viễn GHI ổ D (chỉ tải và giải nén trên C).
- Không `git pull` tạo merge — `git fetch` + checkout commit rõ ràng. Không đụng `main`.
- Không sửa code/test để "cho qua" — fail thì báo nguyên vẹn kèm traceback.
- Không đưa 4 file xls vào Git (báo cáo chỉ ghi đường dẫn + sha256).

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_V1_3_F4-voi-du-lieu-drive.md` gồm:
1. Commit checkout + ngày giờ, OS, Python.
2. Cách tải zip (công cụ nào), 4 dòng đối chiếu kích thước + sha256 (khớp/lệch từng file).
3. Kết quả từng suite (6/6 manifest; 26/26 error_cases) với log tóm tắt; khác biệt nào so với kết quả trên VM (VM: F4 11/11 pass trên Linux).

Tiêu chí ĐẠT: 26/26 error_cases + 6/6 manifest pass 100% trên Windows, 4 sha256 khớp, không ghi index, mọi thao tác trên branch riêng (không đụng main).

## Sau vé này

Vé V1.3 đạt → Muse phát hành Vé P1 "đóng dấu kho thử thành kho thật". Không tự mở P1 trước verdict.
