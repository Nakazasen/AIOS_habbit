# Phục Hồi Nguồn và OCR Tập Ngữ Liệu Cho RAG v2 (RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY)

Status: `DONE`

## Kết Quả (Outcome)

Phục hồi toàn bộ các nguồn ngữ liệu MOM/WMS trong phạm vi thông qua trích xuất cục bộ có giới hạn hoặc OCR mà không cần xử lý qua cloud hoặc loại trừ của chủ sở hữu.

## Phạm Vi Đã Chuyển Giao (Delivered Scope)

- Bổ sung OCR Tesseract cục bộ với độ tin cậy, số lượng mẫu, tiền xử lý, lượt thử, engine, ngôn ngữ, trang và nguồn gốc cổng chất lượng.
- Bổ sung các bước thử grayscale/autocontrast/upscale tất định và PSM nhận biết bố cục trong khi vẫn duy trì ngưỡng độ tin cậy sử dụng được `35.0`.
- Bổ sung cơ chế dự phòng OCR cấp trang cho các tệp PDF quét hoặc hỗn hợp trong khi vẫn bảo toàn quyền ưu tiên văn bản gốc (native-text) và chốt an toàn 3 trang.
- Bảo toàn nguồn gốc OCR xuyên suốt quá trình trích xuất, đăng ký, metadata của chunk và lập chỉ mục cục bộ.
- Thêm hạch toán mẫu số toàn bộ tệp nghiêm ngặt và hỗ trợ định đoạt của chủ sở hữu đã được xác thực.
- Thêm công cụ dòng lệnh CLI kiểm toán ngữ liệu cục bộ tất định và schema định đoạt mẫu.

## Bằng Chứng Ngữ Liệu Cuối Cùng (Final Corpus Evidence)

Lệnh kiểm toán nghiêm ngặt:

```powershell
.\.venv\Scripts\python.exe scripts\audit_mom_corpus.py "D:\Sandbox\MOM_WMS_QLLSSX\tailieugoc" --output "local_cases\mom_pilot\corpus_audit_ocr_v2.json"
```

Kết quả:

- `70/70` nguồn sử dụng được (`100.0%`).
- `51` tệp sử dụng trực tiếp và `19` tệp sử dụng qua OCR.
- Toàn bộ `17` nguồn PNG đều được phục hồi thành công.
- Sinh ra `670` chunk, bao gồm `38` chunk OCR (`20` từ PNG và `18` từ PDF).
- `0` tệp chưa được giải quyết, `0` nguồn không hỗ trợ không xác định, và `0` ngoại lệ loại trừ của chủ sở hữu.
- `strict_passed: true`, `privacy_level: local_only`, và `cloud_ocr_used: false`.
- Báo cáo runtime giữ nguyên trạng thái bị gitignore dưới `local_cases/mom_pilot/corpus_audit_ocr_v2.json`.

Hai bản ghi cảnh báo trang PDF là các thông báo an toàn cấp trang rõ ràng bên trong các tài liệu vốn dĩ sử dụng được; chúng không tạo ra các định đoạt nguồn chưa giải quyết.

## Kiểm Chứng (Verification)

- Bộ kiểm thử PDF / OCR / trích xuất tập trung: `49 passed`.
- Hồi quy toàn bộ repository: `1108 passed`.
- Hợp đồng tài liệu: `DOCUMENTATION_CONTRACT=PASS`.
- `python -m compileall -q src tests`: PASS.
- Kiểm toán ứng dụng: `PASS`, không có lỗi hay cảnh báo.
- Import Workspace Chat: PASS; chỉ có các cảnh báo thiếu ngữ cảnh của Streamlit như kỳ vọng.
- `git diff --check`: PASS.

## Ràng Buộc Bảo Mật (Privacy Constraints)

OCR, ảnh tạm thời, văn bản trích xuất và chỉ mục luôn nằm cục bộ dưới các thư mục runtime bị gitignore. Log và bằng chứng được commit chỉ chứa các số lượng / trạng thái tổng hợp, tuyệt đối không chứa văn bản tài liệu trích xuất riêng tư.

## Hoàn Tác (Rollback)

Vô hiệu hóa adapter OCR và tái xây dựng chỉ mục cục bộ từ các nguồn chuẩn tắc. Các tệp nguồn gốc không bao giờ bị chỉnh sửa; các artifact kiểm toán trước đó có thể được giữ lại để so sánh đối chiếu.

