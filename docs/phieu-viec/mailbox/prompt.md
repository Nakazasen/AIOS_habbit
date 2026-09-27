# Vé V1.4 — tải zip Drive (đường mới) rồi chạy nốt 10 test F4 trên Windows

Ngày viết: 2026-09-28 (Muse). Chế độ: Muse ra vé → OMP thực hiện độc lập trên Windows (luật "không vừa đá vừa thổi còi").
Branch: `phieu-viec/rag-fix1`. Không đụng `main`. Hostname: `h410asrock` (Win 10 Pro).

## Verdict Vé V1.3: CHƯA ĐẠT về số liệu — nhưng báo cáo TRUNG THỰC, không phải lỗi code

- OMP chạy đúng bước 6 của vé: 3 lần tải zip thất bại (gdown bản cũ không có `--fuzzy`; gdown trực tiếp bị chặn sign-in vì file Drive ở chế độ restricted; cookie Chrome bị Windows chặn; trình duyệt điều khiển chưa kết nối) → dừng đúng quy định, không bịa dữ liệu, không ghi index, không ghi ổ D.
- Đối chiếu diff độc lập `fb97f6a...885569a`: chỉ sửa `docs/phieu-viec/mailbox/trang-thai.md` (+4/-4), không đụng code, không đụng `main`. Báo cáo trung thực, verdict độc lập giữ nguyên.
- Gốc rễ của block: file zip trên Drive ở chế độ restricted → mọi cách tải ẩn danh đều chết. Vé này sửa đúng chỗ đó.

## Đường tải mới (Muse đã mở — OMP chỉ việc tải, KHÔNG đổi quyền share)

- 2026-09-28 ~04:35 +07: Muse đã bật **tạm** quyền "anyone with link → reader" (tắt discover công khai) cho file zip `1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP`. Muse đã xác minh ẩn danh: link dưới trả về được (đi qua trang xác nhận virus-scan của Drive — gdown tự xử lý).
- Link tải trực tiếp: `https://drive.google.com/uc?export=download&id=1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP`
- OMP **không** thay đổi quyền share của file dưới mọi hình thức. Muse thu hồi quyền ngay sau khi OMP báo tải xong (poll kế tiếp).

## 4 file nguồn (giữ nguyên từ Vé V1.3 — đã xác minh byte trên VM ngày 27/09)

Sau giải nén, 4 file nằm trong cây `dieu_tra_loi/Điều chỉnh/`:

| File (GIỮ NGUYÊN tên, kể cả ký tự Nhật) | Kích thước (byte) | sha256 |
|---|---|---|
| `Bang ma loi/02XC_自己診断表示一覧表-Iris2020 VN.xls` | 1.278.976 | `031bbe3e447de2f2d5367a8f10fb875df7a3b7ecd5a9d3330860d15b38b20cc4` |
| `UWCAシステムエラー(FXXX)概要.xls` | 303.104 | `81c43cd46496d8f0069f7f40806ff6d6a3e9e5d14af26a5cf2d477709b94a458` |
| `SCT自動調整エラーコード一覧_140221.xls` | 294.400 | `6fe738d0d7ef00a45f881f9deb2354798aec0f840a2ce60948544164801f7749` |
| `Bang ma loi/02XC_機能定義書_JAM一覧 (1).xls` | 782.336 | `6c40012e780dbf83caaaeef5d50e9fbfdc5c387136c5b262a84edf2159088195` |

## Cách làm

1. Nâng cấp gdown trước (bản trên máy cũ, thiếu `--fuzzy`): `pip install -U gdown`.
2. Tải zip (~858 MB) bằng link trực tiếp ở trên, lưu vào `C:/tmp/aios-data-v14.zip`:
   `gdown "https://drive.google.com/uc?id=1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP" -O C:/tmp/aios-data-v14.zip`
3. Giải nén RA Ổ C vào thư mục tạm mới `C:\tmp\aios-data-v14` (không bao giờ ghi ổ D). Nếu tên tiếng Nhật bung sai ký tự, giải nén lại bằng 7-Zip chế độ UTF-8 cho đến khi tên khớp y hệt bảng trên.
4. Đối chiếu 4 file: kích thước + sha256 PHẢI khớp bảng. **Lệch bất kỳ file nào → dừng, báo nguyên vẹn, không dùng file đó** (fail-closed, cấm bịa).
5. Đặt biến môi trường `AIOS_DATA_DIR` trỏ tới thư mục CHA của `dieu_tra_loi` (ví dụ `C:\tmp\aios-data-v14`), sao cho tồn tại `AIOS_DATA_DIR\dieu_tra_loi\Điều chỉnh\...` đúng cấu trúc zip.
6. Dùng lại môi trường Python 3.11.14 + pytest 8.4.2 của Vé V1 (venv trên C, TMP/TEMP trên C):
   - `pytest tests/test_rag_v2_ingest_manifest.py -q` → kỳ vọng 6/6.
   - `pytest tests/test_error_cases_f1.py tests/test_error_cases_f4.py -q` → kỳ vọng 26/26.
7. Nếu KHÔNG tải được zip sau 3 lần thử (tối đa): dừng, ghi rõ "không tải được nguồn" trong báo cáo — chờ Muse lo đường khác. Không thử lần 4.

## Cấm kỵ (fail-closed)

- CHỈ đọc + chạy test. Cấm ghi index, cấm embed/apply/ingest thật.
- Cấm vĩnh viễn GHI ổ D (chỉ tải và giải nén trên C).
- Không `git pull` tạo merge — `git fetch` + checkout commit rõ ràng. Không đụng `main`.
- Không sửa code/test để "cho qua" — fail thì báo nguyên vẹn kèm traceback.
- Không đưa 4 file xls vào Git (báo cáo chỉ ghi đường dẫn + sha256).
- Không thay đổi quyền share của file Drive (Muse quản, sẽ thu hồi).

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_V1_4_F4-windows.md` gồm:
1. Commit checkout + ngày giờ, OS, Python.
2. Cách tải zip (công cụ nào, gdown phiên bản mấy), 4 dòng đối chiếu kích thước + sha256 (khớp/lệch từng file).
3. Kết quả từng suite (6/6 manifest; 26/26 error_cases) với log tóm tắt; khác biệt nào so với kết quả trên VM (VM: F4 11/11 pass trên Linux).

Tiêu chí ĐẠT: 26/26 error_cases + 6/6 manifest pass 100% trên Windows, 4 sha256 khớp, không ghi index, mọi thao tác trên branch riêng (không đụng main).

## Sau vé này

Vé V1.4 đạt → Muse phát hành Vé P1 "đóng dấu kho thử thành kho thật". Không tự mở P1 trước verdict.
