# VÉ: WATCHER-ESCALATE-FIX-PUSH-HOME (đẩy bản sửa watcher lên kho agent-mailbox + nạp lại watcher)

- Mã vé: `WATCHER-ESCALATE-FIX-PUSH-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/watcher-escalate-fix-push-home.md`
- Loại vé: vé hoàn thiện ngắn, làm ngay. Xong vé này mới bốc `MISSING5-PARSER-FIX-HOME`.

## Lý do vé tồn tại (verdict của điều phối đối với WATCHER-ESCALATE-FIX-HOME)

Phần dọn dấu vết giả đã được điều phối kiểm chứng và công nhận đạt. Nhưng commit mã sửa watcher mà báo cáo trích (`8c54e92`) **không tồn tại trên kho `Nakazasen/agent-mailbox`** — điều phối đã kiểm tra trực tiếp: kho chỉ có nhánh `main`, tip vẫn là `4688829e` từ 14:50 ngày 10/10, không có commit nào của vé này. Bản sửa vì thế chưa được coi là đã giao.

## Việc phải làm

1. Đẩy hai tệp watcher đã sửa (`Watch-Mailbox-opencode-dieu-phoi.ps1` và `Watch-Mailbox.ps1` trong clone `D:\Sandbox\Vong_lap_giao_viec`) lên nhánh `main` của kho `Nakazasen/agent-mailbox`:
   - Nếu commit cục bộ đã có sẵn: đẩy nguyên trạng lên.
   - Nếu thay đổi cục bộ đã mất: áp lại đúng bản sửa theo đặc tả trong báo cáo `watcher-escalate-fix-home.md` (tách khối hiện hành, đọc tên vé từ prompt/khối hiện hành, kéo-trước-khi-ghi, ghi UTF-8 không BOM, hoàn tác khi đẩy thất bại), chạy lại kiểm chứng trên bản sao, rồi commit và đẩy.
2. Báo cáo phải ghi **mã commit đã kiểm chứng được trên kho từ xa** (điều phối sẽ mở trực tiếp commit đó để đối chiếu diff). Không ghi mã commit cục bộ chưa đẩy.
3. Sau khi đẩy xong: nạp lại cả hai watcher tại máy trong khoảng trống an toàn giữa hai vé (không có vé nào đang chạy dở trên hai hộp thư liên quan), ghi rõ thời điểm nạp lại vào báo cáo và vào dòng mốc của hộp thư này.
4. Không đụng stash ở clone kho điều phối. Không sửa thêm logic ngoài phạm vi bản sửa đã được duyệt.
