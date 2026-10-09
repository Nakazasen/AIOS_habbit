# VÉ: CONFIG-GOLIVE-AUDIT-HOME (rà toàn bộ cấu hình chạy thật của máy nhà theo các quyết định đã chốt + sửa lệch)

- Mã vé: `CONFIG-GOLIVE-AUDIT-HOME`
- Role gợi ý: SMOL/TINY (OMP — thợ phụ, máy nhà; việc rà soát nhanh)
- Báo cáo: `docs/phieu-viec/ket-qua/config-golive-audit-home.md`
- Căn cứ: nhiều quyết định cấu hình đã chốt rải rác qua các vé gần đây cần được đối chiếu một lượt trên chính tệp cấu hình thật của máy nhà trước khi coi là sẵn sàng dùng thật: (1) chuỗi tổng hợp 3 tầng đã chốt (model chính miễn phí, dự phòng nhanh miễn phí, dự phòng chất lượng có phí) đã áp ở vé cấu hình tầng; (2) công tắc mở cổng tổng hợp cho sổ ở giao diện đang bật theo quyết định của chủ sở hữu; (3) vé sửa giao thức DeepSeek ghi nhận tồn dư: thời gian chờ nhà cung cấp mặc định 30 giây có thể cắt mất lượt thử lại (vốn kéo dài 20–50 giây) khi chạy qua giao diện thật, dù cơ chế thử lại đã đúng. Vé này rà một lượt, sửa đúng điểm lệch, và chứng minh bằng một lượt dùng thật.

## Việc phải làm

1. **Bảng đối chiếu cấu hình:** đọc tệp `.env` thật của máy nhà (chỉ ghi tên biến và giá trị cấu hình không nhạy cảm; tuyệt đối không in bất kỳ phần nào của khoá truy cập — chỉ ghi biến khoá "có mặt/không có mặt"), đối chiếu từng biến liên quan tới: chuỗi model tổng hợp và thứ tự dự phòng, công tắc cho phép nhà cung cấp ngoài, địa phương dữ liệu, thời gian chờ nhà cung cấp, giới hạn token, các biến truy hồi liên quan tới ngữ cảnh tổng hợp. Nộp bảng: tên biến — giá trị hiện tại — giá trị theo quyết định đã chốt — khớp/lệch.
2. **Sửa đúng điểm lệch về thời gian chờ:** đặt thời gian chờ nhà cung cấp ở mức đủ cho lượt thử lại hoàn thành (căn cứ số đo thật của vé sửa giao thức: lượt thử lại 20–50 giây; chọn mức có dư địa hợp lý nhưng không vô hạn) trong `.env` máy nhà. Các điểm lệch khác (nếu phát hiện): chỉ sửa khi lệch khỏi quyết định đã chốt và ghi rõ căn cứ; không tự ý đổi model hay thứ tự chuỗi.
3. **Chứng minh bằng dùng thật:** khởi động lại ứng dụng, hỏi 1 câu LSU qua giao diện ở chế độ chỉ-CPU, bảo đảm đáp án trọn vẹn ra được và tệp nguồn gốc phục vụ ghi nhận đúng model; ghi thời gian toàn trình. Nếu câu hỏi tự nhiên đi qua lượt thử lại thì ghi nhận; không ép tạo tình huống giả.

## Rào cứng

- Không in ký tự nào của khoá truy cập trong báo cáo/log/commit (chỉ "có mặt/không có mặt"). Không commit tệp `.env`. Không ghi chỉ mục (băm trước/sau khớp). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần. Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
