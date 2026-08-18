# Mô Hình Dữ Liệu: Chuẩn Bị Giai Đoạn A Có Khả Năng Tiếp Tục (Data Model: Resumable Stage A Preparation)

## Điểm Kiểm Tra Chuẩn Bị (Preparation checkpoint)

| Trường (Field) | Ý nghĩa (Meaning) | Xác thực (Validation) |
|---|---|---|
| `schema_version` | Phiên bản định dạng checkpoint | số nguyên được hỗ trợ chính xác |
| `status` | `building`, `failed`, hoặc `ready` | `ready` chỉ được ghi sau khi hoàn tất toàn bộ chuẩn bị |
| `identity` | Định danh giai đoạn định địa chỉ theo nội dung đóng băng | yêu cầu khớp chính xác tuyệt đối để tiếp tục |
| `completed_document_ids` | Danh sách có thứ tự các ID tài liệu đã commit mờ (opaque) | tập con của các ID tài liệu hiện thực hóa hiện tại, không trùng lặp |
| `total_sources` | Số lượng nguồn có chứa văn bản | bằng với số lượng nguồn staging hiện tại |
| `last_error` | Danh mục lỗi an toàn | không chứa chi tiết ngoại lệ thô |
| `updated_at` | Thời gian cập nhật checkpoint UTC | ghi nguyên tử (atomically) |

## Chuyển Đổi Trạng Thái (State Transitions)

```text
missing -> building -> ready
                  -> failed -> building (chỉ khi đúng định danh chính xác)
```

Một checkpoint ở trạng thái `failed` không bao giờ đủ điều kiện làm manifest staging. Một định danh bị thay đổi sẽ bị từ chối thay vì chuyển đổi trạng thái.

