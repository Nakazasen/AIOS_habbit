# VÉ: WATCHER-ESCALATE-FIX-HOME (sửa 3 lỗi của watcher hộp thư tại máy nhà: ghi đè file trạng thái, bám tên vé cũ khi leo thang, chèn BOM)

- Mã vé: `WATCHER-ESCALATE-FIX-HOME`
- Thợ: agy máy nhà (việc farm — xếp hàng chờ sau `DATA-INGEST-MISSING5-HOME`; điều phối phát hành chính thức kèm verdict của vé đó).
- Bối cảnh (đã đối soát xong tại máy tối 10/10/2026): bản stash ở clone kho điều phối chứa một bản sửa file `hop-thu/mailbox-opencode/trang-thai.md` do WATCHER TỰ SINH lúc 22:51 — user đã đọc diff và chốt KHÔNG gộp (bản đó là sản phẩm lỗi). Ba lỗi cụ thể của watcher hộp thư opencode (bản tại `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox-opencode-dieu-phoi.ps1`):
  1. Khi leo thang, watcher GHI ĐÈ toàn bộ file trạng thái thay vì chèn thêm dòng: đổi trạng thái MỌI khối vé thành `cho-muse` (kể cả vé đang `moi` và các vé đã xong), thay vì chỉ ghi vào khối vé hiện hành.
  2. Watcher xoá ~15 dòng `ghi_chu` lịch sử thật của thợ và thay bằng dòng leo thang lặp lại mang tên vé CŨ `INDEX-PROD-HOME` — watcher bám tên vé đã đóng từ lâu thay vì đọc tên vé hiện hành từ file.
  3. Watcher chèn ký tự BOM vào đầu file khi ghi.
- Họ hàng đã biết: watcher hộp thư agy từng có cùng họ lỗi ngày 10/10 ~17:37 (252 dòng `cho-muse` trùng lặp đóng vào các khối vé LỊCH SỬ của `docs/phieu-viec/mailbox-agy/trang-thai.md`). Vé này xử lý cả hai nếu hai watcher dùng chung logic leo thang; nếu không dùng chung, sửa bản opencode trước và báo rõ bản agy cần vé riêng hay xử lý luôn được trong vé này.

## Việc phải làm

1. Sửa logic leo thang của watcher (bản opencode trước, bản agy nếu chung mã):
   - Leo thang CHỈ được chèn thêm dòng vào khối vé HIỆN HÀNH (khối đầu file / vé đang mở); tuyệt đối không sửa trạng thái hay nội dung của các khối vé khác, không xoá bất kỳ dòng `ghi_chu` nào.
   - Tên vé dùng khi leo thang phải đọc từ chính file trạng thái/prompt hiện hành tại thời điểm leo thang; cấm dùng tên vé lưu cũ.
   - Ghi file giữ nguyên định dạng mã hoá hiện có của file (không tự thêm BOM).
   - Mọi bộ đếm leo thang phải có trần và có đường lùi: lỗi ghi/đẩy phụ không được phép biến thành ghi đè file.
2. Dọn dấu vết giả do lỗi này gây ra (chỉ khi chắc chắn là dấu giả): các dòng leo thang trùng lặp trong file trạng thái hộp thư agy (252 dòng của sự cố 17:37) — giữ lại đúng một dòng đại diện kèm ghi chú của điều phối, phần còn lại xoá; file trạng thái hộp thư opencode ở kho điều phối hiện là bản remote đúng (không có dấu giả trên kho — dấu giả chỉ nằm trong stash, KHÔNG đụng vào stash đó).
3. Kiểm chứng: chạy thử leo thang trên BẢN SAO của file trạng thái (không chạy trên file thật đang chạy vé) — diff sau leo thang chỉ được phép thêm đúng dòng leo thang vào khối hiện hành, không đổi bất kỳ ký tự nào khác; trình diff đó trong báo cáo.

## Ràng buộc

- Không khởi động lại watcher đang chạy giữa chừng nếu việc đó làm gián đoạn vé đang chạy (AUDIT-RT-WIRE của opencode, DATA-INGEST của agy); nếu cần nạp lại, ghi rõ thời điểm an toàn trong báo cáo và để điều phối quyết.
- Không đụng vào stash ở clone kho điều phối (bằng chứng sự cố, user chốt giữ nguyên).
- Báo cáo tại `docs/phieu-viec/ket-qua/watcher-escalate-fix-home.md`: tệp đã sửa + diff kiểm chứng trên bản sao + kết luận hai watcher có chung logic hay không.
