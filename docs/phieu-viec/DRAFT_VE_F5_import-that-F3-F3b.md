# DRAFT — Vé F5: Import thật 15.737 dòng + đo F3/F3b

Trạng thái: **DRAFT** — chưa phát hành. Chỉ phát hành sau khi Vé V1 (verify F1–F4
trên Windows) ĐẠT và mailbox về `moi`. Một lúc một vé.

Ngày viết: 2026-09-28 (Muse).

## Bối cảnh

- Module F1 (`src/aios_habit/error_cases/`, commit `179180a6d75e`) + profile
  `history_29` (commit `52d3e00205d3`) + F4 glossary (commit `3d1dfbfc5865`)
  đã xong trên VM, chờ verify Windows ở Vé V1.
- File thật: `Loi KDTPS.xlsx`, sheet `History KDTPS`, header dòng 4,
  **15.737 dòng** (trinh sát F2, commit `cd8ce51659b5`).
- 925 khóa `(năm, NO)` trùng — import phải dedup, không được nhân dòng.
- F3 (`completeness.py`, commit `ba22f4a06086`): đo độ đầy 10 trường;
  F3b mở khi trường cốt lõi
  (`no_dvd/machine_type/line/investigation/cause/fix`) dưới 90%.
- Dự kiến: F3b **sẽ mở** vì cột AB (`fix`) thực tế chỉ đầy ~56,8%.

## Cấm kỵ

- Import chạy trên **máy nhà** (file thật ở đó). Muse/VM không đụng.
- Không ghi index RAG trong vé này — chỉ SQLite `error_cases`.
- Ô xanh lá `(146,208,80)` không ghi đè (luật F1).

## Cách làm (đúng thứ tự)

1. Backup file SQLite đích trước khi import (ghi rõ đường dẫn + SHA-256).
2. Import 15.737 dòng bằng đúng `HISTORY_29_MAP` + `normalize_history_row`
   (ưu tiên điều tra tiếng Việt cột O, fallback tiếng Nhật cột N).
   Ánh xạ đã chốt: line=E, S=mã linh kiện, V=LKATQT, Y=ngày giải Hold.
3. Dedup khóa rộng `UNIQUE(no_dvd, machine_type, line)` — 925 khóa trùng
   phải gộp, tổng số dòng sau import + số dòng bị gộp phải khớp 15.737.
4. Ghi provenance mỗi batch: file/sha/sheet/row (theo `store.py`).
5. Chạy `completeness.measure(conn)` → báo cáo Markdown 10 trường.
6. Nếu trường cốt lõi < 90% → **mở F3b**, liệt kê trường rớt + số liệu,
   không tự "sửa" dữ liệu cho đạt.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_F5_import-that-F3.md` gồm:
số dòng import/gộp/bỏ qua, SHA-256 file nguồn, 3 commit đã verify (F1/F4/F3),
bảng completeness 10 trường, trạng thái F3b (mở/đóng + bằng chứng).
F3b mở là **kết quả hợp lệ**, không phải fail — cấm làm đẹp số liệu.
