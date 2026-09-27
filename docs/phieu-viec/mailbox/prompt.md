# Vé P1.1 — Hoàn tất đóng dấu kho thật (sửa đường dẫn production)

Ngày viết: 2026-09-28 (Muse). Chế độ tự lái: Muse ra vé → OMP thực hiện độc lập
trên Windows (luật "không vừa đá vừa thổi còi").
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Máy: `h410asrock` (Win 10 Pro).

## Verdict Vé P1: CHƯA ĐẠT đóng dấu — nhưng KHÔNG phải lỗi OMP

- **Bước 1: ĐẠT.** `C:\AIOS_habit_index_ve03\library.sqlite`: `integrity_check=ok`,
  ONNX dense/sparse 107.331/107.331, fingerprint
  `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` khớp,
  pending=0, 340 vector PyTorch cũ giữ nguyên. (Báo cáo commit `4ec8567`,
  Muse đã review độc lập: số liệu khớp vé 0.3, không bịa.)
- **Bước 2–5: chưa chạy.** Vé P1 ghi sai đường dẫn kho production.
  OMP dừng đúng (fail-closed), không bịa backup, không chép mù sang đường dẫn
  chưa xác nhận — xử lý chuẩn, không trừ điểm.
- **Đính chính từ code (Muse kiểm trên repo):** kho library của một collection =
  `<storage_root>/aios_thu_vien/library.sqlite`
  (`COLLECTION_RUNTIME_DIRNAME = "aios_thu_vien"` trong `workspace_chat_store.py`).
  Đường dẫn `workspace_chat_rag_v2_production/workspace_chat.sqlite` trong vé P1
  là SAI — đó là ledger của profile canary (`_get_ledger_db_path`), chỉ ~16KB,
  không phải kho vector. **Lỗi ở vé của Muse, Muse nhận.**

## Cách làm (đúng thứ tự)

1. Xác định `storage_root` thật của collection `tri_thuc` trên máy h410asrock:
   mở app Streamlit → cài đặt/kho tri thức của collection `tri_thuc`, xem
   storage root; hoặc tìm trong file config nơi app lưu `KnowledgeCollection`
   (`set_collection_storage_root`). Ghi rõ đường dẫn đầy đủ + lấy từ đâu vào
   báo cáo. Nếu không tìm thấy: DỪNG, báo lại, KHÔNG đoán.
   Đường dẫn library production = `<storage_root>\aios_thu_vien\library.sqlite`.
2. Kiểm nhanh kho canary `C:\AIOS_habit_index_ve03\library.sqlite` (mở read-only):
   `integrity_check=ok`, pending=0. (Không cần đếm lại toàn bộ — bước 1 của P1
   đã đạt, đây chỉ là chốt an toàn trước khi copy.)
3. Backup kho production HIỆN TẠI (file sibling cạnh nó, `integrity_check=ok`)
   TRƯỚC khi thay — có điểm quay lui dù bước sau đạt hay không.
4. Copy canary → đè lên library production. Copy xong so sha256 + kích thước
   hai bản — phải khớp 100% mới đi tiếp.
5. App đọc kho mới, chạy thử B1–B5 (B4 loại khỏi chấm điểm theo kế hoạch E):
   đạt, không abstain/timeout bất thường; ghi nhận latency từng câu.
6. Chỉ khi B1–B5 đạt → **đóng dấu**: ghi commit SHA + sha256 file index mới
   + ngày giờ vào báo cáo → từ đây mới coi là "kho chạy thật".

## Cấm kỵ

- Không ghi đè kho production khi bước 2 hoặc 3 chưa đủ dấu.
- Cấm vĩnh viễn GHI ổ D. Mọi thao tác trên ổ C.
- Không `git pull` tạo merge — `git fetch` + checkout commit rõ ràng. Không đụng `main`.
- Không sửa code/test để "cho qua" — fail thì báo nguyên vẹn kèm số đo.
- Không embed/index lại gì thêm trong vé này — vé này chỉ đóng dấu.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_P1_1_dong-dau-kho-that.md` gồm:
1. Đường dẫn production đã xác định + bằng chứng lấy từ đâu (UI app / file config nào).
2. sha256 + kích thước bản backup production và index mới sau copy (so hai bản).
3. Kết quả B1–B5 + latency từng câu, khác biệt nào so với kỳ vọng.
4. Thời điểm đóng dấu, hostname máy chạy.

Tiêu chí ĐẠT: đường dẫn production xác thực được, backup ok, copy khớp 100%,
B1–B5 đạt trên kho mới, báo cáo đóng dấu đầy đủ.

## Sau vé này

Vé P1.1 đạt → Muse phát hành Vé P2 "mang sang máy công ty KDTVN-PC0575"
(theo mẫu `docs/phieu-viec/VE_P2_ve-mau-may-cong-ty.md` và tiêu chí G2
`docs/phieu-viec/G2_tieu-chi-nghiem-thu.md`). Không tự mở P2 trước verdict.
