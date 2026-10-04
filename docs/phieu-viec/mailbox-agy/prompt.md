# Vé: SCAN-O-D — kiểm kê và quét các thao tác trên ổ D

Lane: [NHÀ] thợ agy chạy trên máy nhà h410asrock (ổ D). Chỉ đọc/kiểm kê, KHÔNG xóa, KHÔNG di chuyển file. Không merge `main`.
Role gợi ý: SMOL (việc đọc/liệt kê nhanh).

## Bối cảnh

Backlog master còn mục "quét sạch thao tác ổ D" chưa có vé: cần biết trên ổ D đang có những gì liên quan dự án (kho index, backup, file tạm, model), chỗ nào trùng lặp, chỗ nào có thể dọn — nhưng quyết định xóa/dọn là của user (luật tự lái: Muse không gật thay việc xóa backup).

## Việc agy làm [NHÀ]

1. Liệt kê cây thư mục cấp 1–2 của ổ D, dung lượng từng nhánh lớn (>1GB).
2. Kiểm kê các mục liên quan AIOS: file `*.sqlite` (kho index — ghi rõ đường dẫn + SHA-256 + dung lượng), thư mục backup, file zip/tar, thư mục model, file log lớn.
3. Đối chiếu với danh mục đã biết (kho production máy nhà SHA `45eb0e07…b7c0`, staging GPU-262 giữ nguyên theo lệnh user) — đánh dấu mục nào lạ/chưa từng ghi nhận.
4. Đề xuất danh sách dọn (theo thứ tự an toàn: rác tmp → venv trùng → worktree cũ → backup cũ sau kiểm toàn vẹn) — CHỈ ĐỀ XUẤT, không thực hiện.
5. Tuyệt đối không mở/sửa file dữ liệu công ty ngoài việc đọc metadata (tên, size, SHA).

## Tiêu chí ĐẠT

- Báo cáo `docs/phieu-viec/ket-qua/scan-o-d.md` gồm: cây thư mục + dung lượng, bảng kiểm kê sqlite (đường dẫn/SHA/size), danh sách đề xuất dọn có thứ tự — rồi `xong-cho-duyet`.
- Không có file nào bị xóa/sửa/di chuyển trong quá trình quét.

## Tiêu chí CHƯA ĐẠT

- Thiếu SHA của bất kỳ file sqlite nào, hoặc có thao tác ghi/xóa lên ổ D.
