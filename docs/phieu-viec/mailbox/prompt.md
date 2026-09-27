# Vé P1 — Đóng dấu kho thử thành kho thật (máy nhà)

Ngày viết: 2026-09-28 (Muse). Chế độ tự lái: Muse ra vé → OMP thực hiện độc lập
trên Windows (luật "không vừa đá vừa thổi còi").
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Máy: `h410asrock` (Win 10 Pro).

## Verdict Vé V1.4: ĐẠT (2026-09-28 ~04:53)

- Tải zip đường mới thành công ngay lần 1 (858.190.286 byte); 4/4 file khớp
  kích thước + sha256 đúng bảng vé; manifest 6/6 + error_cases 26/26 pass trên
  Windows; mọi thao tác trên ổ C; không ghi index, không ghi ổ D.
- Diff độc lập commit `c9148e5`: chỉ thêm báo cáo
  `docs/phieu-viec/ket-qua/VE_V1_4_F4-windows.md` (+61) và sửa
  `docs/phieu-viec/mailbox/trang-thai.md` (+4/-4). Không đụng code, không đụng
  `main`. OMP không sửa code/test để "cho qua".
- Quyền anyone-with-link trên file zip đã được Muse thu hồi sau khi OMP báo tải xong.
- Vé V1 (verify F1–F4 trên Windows) xong → phát hành Vé P1.

## Bối cảnh / tiền điều kiện (từ báo cáo Vé 0.3, commit `9f243ec`)

- Kho canary: `C:\AIOS_habit_index_ve03\library.sqlite` — migration GPU hoàn tất
  99.003/99.003 khối, `pending=0`, ONNX dense và sparse cùng 107.331/107.331,
  `PRAGMA integrity_check=ok`.
- Backup mới nhất trên C:
  `C:\AIOS_habit_index_ve03\library.sqlite.bak-20260927-223834-ve03-retry`
  (integrity_check=ok).
- App production đang đọc kho `workspace_chat_rag_v2_production/workspace_chat.sqlite`.
- **CẤM** app đọc kho đang nhúng dở — chỉ kho đã "đóng dấu" mới được coi là
  kho chạy thật.

## Cách làm (đúng thứ tự)

1. Kiểm toàn vẹn kho canary `C:\AIOS_habit_index_ve03\library.sqlite`:
   - `PRAGMA integrity_check` = `ok`.
   - Đếm vector ONNX dense = 107.331 và sparse = 107.331; `pending` = 0.
   - Fingerprint ONNX
     `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` khớp.
   - Thiếu bất kỳ dấu nào → DỪNG, báo nguyên vẹn, không đi tiếp (fail-closed).
2. Backup kho production HIỆN TẠI (file sibling cạnh nó, `integrity_check=ok`)
   TRƯỚC khi thay — có điểm quay lui dù bước sau đạt hay không.
3. Copy kho canary → `workspace_chat_rag_v2_production/workspace_chat.sqlite`
   (đúng thư mục mà app đang đọc). Copy xong so sha256 + kích thước hai bản —
   phải khớp 100% mới đi tiếp. Nếu không chắc đường dẫn thật của kho production
   trên máy này: ghi rõ vị trí đã tìm vào báo cáo, hỏi lại Muse trong báo cáo,
   KHÔNG tự đoán chỗ khác.
4. App trỏ sang kho mới, chạy thử B1–B5 (B4 loại khỏi chấm điểm theo kế hoạch E):
   đạt, không abstain/timeout bất thường; ghi nhận latency từng câu.
5. Chỉ khi B1–B5 đạt → **đóng dấu**: ghi commit SHA + sha256 file index mới
   + ngày giờ vào báo cáo → từ đây mới coi là "kho chạy thật".

## Cấm kỵ

- Không ghi đè kho production khi chưa đủ dấu toàn vẹn ở bước 1.
- Cấm vĩnh viễn GHI ổ D. Mọi thao tác trên ổ C.
- Không `git pull` tạo merge — `git fetch` + checkout commit rõ ràng. Không đụng `main`.
- Không sửa code/test để "cho qua" — fail thì báo nguyên vẹn kèm số đo.
- Không embed/index lại gì thêm trong vé này — vé này chỉ đóng dấu.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_P1_dong-dau-kho-that.md` gồm:
1. integrity_check, số vector dense/sparse, pending, fingerprint của kho canary.
2. Đường dẫn + sha256 + kích thước của bản backup production và của index mới sau copy (so hai bản).
3. Kết quả B1–B5 + latency từng câu, khác biệt nào so với kỳ vọng.
4. Thời điểm đóng dấu, hostname máy chạy.

Tiêu chí ĐẠT: đủ dấu toàn vẹn bước 1, copy khớp 100%, B1–B5 đạt trên kho mới,
báo cáo đóng dấu đầy đủ.

## Sau vé này

Vé P1 đạt → Muse phát hành Vé P2 "mang sang máy công ty KDTVN-PC0575"
(theo mẫu `docs/phieu-viec/VE_P2_ve-mau-may-cong-ty.md` và tiêu chí G2
`docs/phieu-viec/G2_tieu-chi-nghiem-thu.md`). Không tự mở P2 trước verdict.
