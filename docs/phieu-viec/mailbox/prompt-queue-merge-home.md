# Vé MERGE-HOME — Gộp 2 gói delta vào kho app máy nhà (phát hành lại lần 2)

## Bối cảnh cập nhật (2026-10-01 ~08:20 +07)
Vé `move-index-c` đã ĐẠT (verdict Muse): kho app `localhost:8501` hiện đọc trên **ổ C**:
`C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
(manifest `config/workspace_chat_rag_v2.local.json` → `runtime.root` = `C:\AIOS_workspace_chat_rag_v2_production`,
backup `.bak-20261001-move-index-c`; bản D giữ nguyên = ghim `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` làm fallback).
Bản `C:\AIOS_p1_4\` KHÔNG còn file (đã move vào layout app).

**CẢNH BÁO — kho C là nguồn thay đổi:** app có cơ chế nền "chuẩn bị nguồn" tự nhúng tài liệu
(sau move-index-c tự nhúng +3 tài liệu/+116 chunk, đúng fingerprint `016c5255…`).
Vì vậy trong vé này:
- Đo LẠI SHA-256 + size kho C ngay đầu Pha 1, ghi làm baseline trong báo cáo.
- KHÔNG dùng ghim `062ec090…4ef8ca` để so kho C (ghim cũ chỉ còn đúng cho bản D).
- **DỪNG app trước khi backup + merge**, restart sau khi merge xong (tránh race với worker nền).

Khảo sát chi tiết Pha 0 lần 1 đã có trong `docs/phieu-viec/ket-qua/merge-home.md` (commit `561014b`):
2 gói delta SHA khớp ghim, ZIP CRC đạt, SQLite standalone (không phải diff), fingerprint
`016c5255…` đủ 100% dense+sparse cả 2 gói, `quick_check` ok. Lần này tái kiểm nhanh số đo tươi
(kho C đã đổi), không cần khảo sát lại toàn bộ.

2 gói delta (trên ổ C; đã upload lên Drive qua vé `upload-delta-drive` — link dự phòng):
- `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` — 20.867.536 B, SHA `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85`; Drive: https://drive.google.com/file/d/1TE6mHBAE0CzD5I4pleO-23zVYaspnsVz/view?usp=sharing
- `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` — 74.065.213 B, SHA `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3`; Drive: https://drive.google.com/file/d/1Smteq_Iyjx2uZjh2RlrK1wvASFjXJ3yZ/view?usp=sharing
- 262b: 19 tài liệu/2.883 chunk (14 ID mới + 5 ID SKIP của PC0575); DC: 329 tài liệu/12.720 chunk (10.238 dense+sparse), toàn ID mới.
Fingerprint vector `016c5255…` (tương thích mọi kho cùng model).

## Việc cần làm
### Pha 0 — Xác minh tươi (chỉ đọc)
1. Xác định app (`localhost:8501`) đang đọc kho nào: đường resolve `library.sqlite` phải là bản C trên (bằng code app, chỉ đọc). Nếu quay lại đường D → DỪNG, mailbox `cho-muse`, báo rõ.
2. SHA-256 2 file delta local khớp ghim trên (nếu lệch → lấy lại từ Drive link trên, verify rồi mới tiếp).
3. Đo SHA-256 + size hiện tại của kho C (baseline trước merge) + dung lượng trống ổ C (phải đủ 1 bản backup ~2,6–2,8 GB + ~0,3 GB tăng trưởng).

### Pha 1 — Merge
1. **DỪNG app** trước mọi thao tác ghi.
2. Dry-run: liệt kê ID sẽ thêm từ 2 delta. 5 ID skip của gói 262b (`wsc-154101d384acc2d01009025d`, `wsc-9e3e7cbc01ed57332c1384eb`, `wsc-58589483c646877fdb341f46`, `wsc-a1a89391eee709a956a46130`, `wsc-cc7d383bb6f7b9127bcaef00`): đối chiếu LẠI với kho C hiện tại (kho đã đổi từ lần khảo sát cũ) — có rồi thì skip (tuyệt đối không ghi đè), chưa có thì nhập.
3. Backup kho C hiện tại: copy sang file backup có timestamp trên C; SHA-256 + `PRAGMA integrity_check` phải `ok` trước khi merge.
4. Merge: nhập ID mới từ 2 delta vào kho C. Luật cứng: KHÔNG ghi đè bất kỳ dòng nào đã tồn tại — phát hiện trùng `chunk_id` → DỪNG, mailbox `cho-muse`.
5. Verify sau merge (chỉ đọc): `integrity_check=ok`, fingerprint `016c5255…` trên bảng vector, đếm số ID mới đúng như dry-run.

### Pha 2 — Restart app + hỏi đáp thử
1. Restart app bằng `RUN_AIOS_WORKSPACE_CHAT.bat`; health `ok`; verify app vẫn đọc kho C (đường resolve + lock/info trong layout C).
2. Hỏi thử 2–3 câu về nội dung mới (ít nhất 1 câu LSU, 1 câu Điều chỉnh); ghi câu hỏi + câu trả lời tóm tắt vào báo cáo.

## Cấm
- KHÔNG ghi/xóa bất kỳ thứ gì trên ổ D (chỉ đọc). Bản D là fallback rollback.
- Không dùng kho production của PC0575, không dùng staging của vé khác, không merge `main`, không force-push.
- Fingerprint lệch → DỪNG, `cho-muse`.

## Tiêu chí ĐẠT
Báo cáo `docs/phieu-viec/ket-qua/merge-home.md` (ghi đè bản lần 1 — báo cáo lần 2): đường kho trước/sau, SHA baseline trước merge + SHA sau merge, SHA backup, số ID đã nhập/skip từng gói, kết quả hỏi đáp thử.

Xong → `trang-thai.md` = `xong-cho-duyet`, đính kèm đường dẫn báo cáo.
