# Vé MOVE-INDEX-C — Chuyển kho production app sang ổ C + cập nhật manifest (vé tiền đề cho merge-home)

## Bối cảnh
Vé merge-home DỪNG ở Pha 0 theo đúng mục Cấm của vé: kho app `localhost:8501`
đang đọc nằm trên ổ D (cấm ghi):
`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
(2.552.659.968 byte, SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`
khớp ghim P1.3 — xem báo cáo `docs/phieu-viec/ket-qua/merge-home.md`, commit `561014b`).
Bản copy trên ổ C đã có từ P1.4: `C:\AIOS_p1_4\tri_thuc\library.sqlite`
(SHA `062ec090…4ef8ca` trùng byte-đối-byte với bản D theo báo cáo merge-home —
vé này VERIFY LẠI độc lập, không tin báo cáo cũ).
Manifest/config hiện tại: `config/workspace_chat_rag_v2.local.json`
(`activation_state=activated`); deployment manifest đang trỏ
`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production`.
Muse quyết định (chế độ tự lái, xử lý cờ `cho-muse` trong SLA): làm vé tiền đề
này TRƯỚC, rồi phát hành lại merge-home để gộp 2 gói delta trên ổ C.

## Việc cần làm
### Pha 0 — Xác minh chỉ đọc (không ghi gì)
1. Đo SHA-256 toàn tệp: bản C `C:\AIOS_p1_4\tri_thuc\library.sqlite` và bản D
   (đường dẫn trên). Cả hai phải bằng
   `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`.
   Lệch bất kỳ đâu → DỪNG, mailbox `cho-muse`, báo rõ.
2. `PRAGMA integrity_check` trên bản C phải `ok`.
3. Đọc manifest/config, xác định CHÍNH XÁC file nào + key nào đang trỏ app tới
   đường dẫn D. Ghi đường dẫn D cũ vào báo cáo (để rollback).
4. Kiểm tra dung lượng trống ổ C (sau vé này kho chính nằm trên C; merge-home
   sau đó cần ~2,6 GB cho 1 bản backup + ~0,3 GB tăng trưởng).

### Pha 1 — Chuyển kho sang C (không xóa gì trên D)
1. Nếu Pha 0 chứng minh bản C đã byte-identical với bản D → dùng luôn, KHÔNG
   copy lại. Nếu chưa → copy D→C (chỉ đọc D), đo SHA lại cho tới khi khớp.
2. Cập nhật manifest/config: trỏ app sang bản C. Báo cáo ghi rõ: file nào,
   key nào, giá trị cũ (D) → giá trị mới (C).
3. Reload/restart app theo đúng quy trình của máy (không đổi gì khác).
4. Verify app đang đọc kho C: lấy đường dẫn index đã resolve từ app đang chạy
   (log/health/config) + smoke đọc — app health ok và 1 câu hỏi thử có citation
   (hoặc mức smoke tương đương P1 "app đọc thử đạt").
5. Verify ổ D nguyên vẹn sau vé: đo lại SHA bản D, vẫn
   `062ec090…4ef8ca`; không có thao tác ghi/xóa nào lên D trong lượt này.

## Cấm
- KHÔNG ghi/xóa bất kỳ thứ gì trên ổ D (chỉ đọc: đo SHA, integrity_check).
- KHÔNG xóa bản D sau khi chuyển — giữ nguyên làm fallback rollback.
  Dọn D (nếu muốn) là quyết định của user, vé riêng sau.
- KHÔNG merge delta trong vé này (việc của merge-home, chạy sau vé này ĐẠT).
- KHÔNG đụng `main`, không force-push; commit riêng trên `phieu-viec/rag-fix1`.

## Tiêu chí ĐẠT — báo cáo `docs/phieu-viec/ket-qua/move-index-c.md`
1. SHA-256 bản C = SHA-256 bản D = `062ec090…4ef8ca` (số đo TRONG vé này).
2. `integrity_check=ok` trên bản C.
3. App đang chạy đọc kho trên C (đường dẫn resolve + smoke đọc đạt);
   manifest/config đã cập nhật (ghi rõ file/key/cũ/mới trong báo cáo).
4. SHA bản D sau vé vẫn `062ec090…4ef8ca`; không thao tác ghi nào lên D.
5. Báo cáo ghi đường rollback: trỏ lại đường dẫn D cũ là xong (bản D nguyên vẹn).

Xong → `trang-thai.md` = `xong-cho-duyet`, đính kèm đường dẫn báo cáo.
