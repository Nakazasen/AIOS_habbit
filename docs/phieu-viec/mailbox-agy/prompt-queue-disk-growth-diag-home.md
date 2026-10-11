# VÉ: DISK-GROWTH-DIAG-HOME (chẩn đoán phần dung lượng ổ C: bị tiêu thụ từ sau vòng dọn 2) — CHỈ ĐỌC

- Mã vé: `DISK-GROWTH-DIAG-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/disk-growth-diag-home.md`
- Điều kiện bốc: sau `STRUCTURED-LANE-TEST-FIXTURE-HOME`.

## Bối cảnh

Báo cáo vòng dọn 3 ghi ổ C: trống 7,443 GB tại 14:56 ngày 11/10/2026, trong khi mốc kiểm chứng sau vòng dọn 2 (17:12 ngày 10/10/2026) là 24,742 GB trống — **khoảng 17,3 GB đã bị tiêu thụ trong ~22 giờ** mà không báo cáo nào giải thích được. Các ứng viên đã biết chỉ cộng được một phần nhỏ (đồng bộ chỉ mục khối LSU +0,8 GB; đệm npm 1,14 GB hiện hữu; các tệp tạm đã dọn chỉ ~0,2 GB).

## Việc phải làm (CHỈ ĐỌC — tuyệt đối không xoá/dọn gì ở vé này)

1. Lập bảng các thư mục/tệp tiêu thụ lớn nhất trên ổ C: tại thời điểm đo (top ~30 theo dung lượng, kèm tuổi tệp mới nhất trong từng thư mục) — bao quát ít nhất: cây production, `C:\tmp` và `C:\temp`, hồ sơ người dùng (`.gemini`, AppData), tệp hoán trang/đệm hệ thống (pagefile/hiberfil nếu đọc được kích thước), thư mục của Antigravity và các profile trình duyệt kiểm thử, các bản sao chỉ mục/sao lưu.
2. Đối chiếu với mốc vòng dọn 2 (24,742 GB trống) và mốc vòng dọn 3 (7,443 GB): mục nào phình ra trong khoảng đó, phình bao nhiêu — mục nào không xác định được thời điểm thì ghi rõ "không xác định được", không đoán.
3. Phân loại từng mục lớn: (a) dữ kiện production/sao lưu phải giữ; (b) sản phẩm phụ của các phiên làm việc đã khép, đủ điều kiện vào vòng dọn sau; (c) chưa rõ chủ — kèm đề xuất xử lý cho từng mục (b) và (c).

## Nghiệm thu
- Báo cáo có bảng số liệu đo thật tại máy kèm thời điểm đo; điều phối sẽ đối chiếu tổng các mục phình với con số ~17,3 GB (sai lệch phải giải thích được phần còn lại thuộc đâu hoặc ghi là chưa truy hết).
- Không một thao tác ghi/xoá nào ngoài tệp báo cáo.
