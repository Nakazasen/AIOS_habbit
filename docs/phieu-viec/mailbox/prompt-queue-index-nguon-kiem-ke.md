# Vé: INDEX-NGUON-KIEM-KE — kiểm kê document trong index production theo thư mục nguồn (chỉ đọc)

Lane: [NHÀ] OMP chạy trên máy nhà. TUYỆT ĐỐI chỉ đọc: mở SQLite bằng `mode=ro`, không ingest, không embed, không sửa/ghi bất kỳ file index nào. Không merge `main`.

## Bối cảnh

User hỏi: dữ liệu 3 nguồn (thư mục LSU trên Drive, file zip "Điều chỉnh"/Điều-tra-lỗi, thư mục MOM) có đang bị trộn chung trong một index production không. Điều tra trên VM cho thấy:

- Index production là MỘT file duy nhất: `C:\AIOS_habit_index_ve03\library.sqlite` (collection `tri_thuc`), ~107k chunk / 889 document.
- Schema chunk có `source_path`/`source_name`/`document_id` nhưng KHÔNG có trường `domain`; retrieval không lọc theo lĩnh vực kiến thức.
- Tài liệu MOM đã xác nhận nằm trong index này (báo cáo `MOM_INGEST_KHAO_SAT.md`, `MOM_INGEST_BO_SUNG.md`).
- Log LSU và `Loi KDTPS.xlsx` nằm trong DB `error_cases` riêng, không phải index RAG — nhưng chưa rõ các file còn lại của 2 nguồn kia.

Cần con số chính xác từ index thật để thiết kế việc tách thành 3 khối.

## Việc OMP làm

1. Mở `C:\AIOS_habit_index_ve03\library.sqlite` ở chế độ chỉ đọc (`mode=ro`). Ghi lại SHA-256 (hoặc kích thước + mtime) của file TRƯỚC và SAU để chứng minh không bị sửa.
2. Truy vấn bảng `chunks`: đếm số document phân biệt (`document_id`) và số chunk, NHÓM THEO thư mục nguồn (lấy từ `source_path`, gom theo thư mục gốc cấp 1–2, ví dụ `D:\Sandbox\MOM_QLLSSX_WMS\...`, thư mục LSU, thư mục Điều-tra-lỗi...).
3. Liệt kê mọi collection khác ngoài `tri_thuc` nếu có (đường dẫn `collections/<id>/`).
4. Xuất bảng: thư mục nguồn → số document → số chunk. Không cần trích nội dung chunk.

## Tiêu chí ĐẠT

- Bảng kiểm kê đầy đủ 889 document (hoặc tổng số thực tế tại thời điểm chạy, ghi rõ), khớp tổng chunk với `PRAGMA` đếm độc lập.
- SHA/kích thước/mtime file index trước = sau (chứng minh chỉ đọc).
- Báo cáo `docs/phieu-viec/ket-qua/index-nguon-kiem-ke.md` + `xong-cho-duyet`.

## Không làm

- Không ingest/embed/sửa index. Không chạy bất kỳ lệnh ghi nào vào `C:\AIOS_habit_index_ve03\`.
