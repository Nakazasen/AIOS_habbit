# Vận Hành Nạp Dữ Liệu RAG v2 Tự Động (Automated RAG v2 Ingestion Operations)

## Trải Nghiệm Người Dùng (User Experience)

Người dùng thêm tài liệu hoặc chọn một thư mục đồng bộ. Quá trình nạp dữ liệu (ingestion) chạy dưới nền và chỉ mục (index) hiện đang hoạt động vẫn luôn sẵn sàng phục vụ các câu hỏi. Chỉ mục mới chỉ được kích hoạt sau khi đã vượt qua các bước kiểm tra định danh, checksum, tính toàn vẹn SQLite và kiểm tra triển khai.

| Trạng thái nội bộ | Văn bản hiển thị cho người dùng |
| --- | --- |
| `QUEUED`, `EXTRACTING` | Đang chuẩn bị |
| `EMBEDDING`, `VERIFYING`, `DEPLOYING` | Đang xử lý |
| `WAITING_FOR_CAPACITY` | Đang chờ GPU |
| `READY` | Sẵn sàng |
| `FAILED` | Có file cần xem lại |

## Hợp Đồng Độ Tin Cậy (Reliability Contract)

- Các yêu cầu gửi trùng lặp sẽ trả về cùng một tiến trình xử lý (job) logic.
- Các worker sử dụng cơ chế thuê (lease); một lease hết hạn có thể được thu hồi sau khi worker bị crash.
- Các điểm kiểm tra (checkpoint) là bất biến và được xác thực mã băm trước khi tiếp tục (resume).
- Các lỗi về mạng hoặc dung lượng GPU không ảnh hưởng đến chỉ mục đang hoạt động.
- Dữ liệu `local_only` tuyệt đối không được định tuyến đến worker từ xa.
- Quá trình tải lên và tải gói bundle tiếp tục từ các offset byte đã được xác nhận.
- Các bundle bắt buộc phải vượt qua kiểm tra định danh, SHA-256 và tính toàn vẹn của SQLite.
- Quá trình triển khai sử dụng các con trỏ nguyên tử `candidate`, `active`, và `previous`.

## Lựa Chọn Worker (Worker Selection)

Thứ tự ưu tiên: CUDA cục bộ, CUDA được quản lý, worker từ xa đủ điều kiện, sau đó là CPU cục bộ được điều tiết tốc độ. Chính sách CUDA sử dụng FP16 và batch size theo dung lượng VRAM. Lỗi tràn bộ nhớ (out-of-memory) sẽ giảm một nửa kích thước batch cho đến khi còn 1 item; sau đó bộ lập lịch sẽ chọn worker khác hoặc chờ dung lượng.

Các phiên Colab hoặc Kaggle miễn phí chỉ là worker mang tính cơ hội, không phải là control plane, vì các phiên và hạn ngạch có thể biến mất bất kỳ lúc nào mà không báo trước.

## An Ninh và Quyền Riêng Tư (Security and Privacy)

- Lưu giữ các service token trong kho lưu trữ bí mật của hệ điều hành và truy cập chúng thông qua callback token.
- Tuyệt đối không ghi log token, API key, nội dung nguồn hoặc chi tiết ngoại lệ thô.
- Cloud worker chỉ chấp nhận các job có mức bảo mật `cloud_safe` và `public`.
- Áp dụng chính sách lưu giữ nguồn và artifact sau khi đã chuyển giao được xác thực.

## Các Kịch Bản Phục Hồi Khẩn Cấp (Recovery Drills)

1. Tắt đột ngột (kill) một worker sau một checkpoint; worker thay thế tiếp tục chạy mà không làm thay đổi các checkpoint đã commit.
2. Ngắt quãng quá trình tải lên và tải xuống; truyền tải tiếp tục tại offset đã được xác nhận.
3. Giả mạo gói bundle; bước xác thực sẽ từ chối bundle đó.
4. Mô phỏng lỗi CUDA OOM; kích thước batch giảm dần và phương án dự phòng vẫn sẵn sàng.
5. Dừng máy đột ngột trong khi triển khai; một bundle active hoặc previous còn nguyên vẹn vẫn được duy trì.
6. Đặt câu hỏi đồng thời trong khi nạp dữ liệu; việc truy xuất từ chỉ mục active vẫn luôn khả dụng.

## Các Lệnh Kiểm Chứng (Validation Commands)

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_rag_v2_ingestion_jobs.py tests\test_rag_v2_index_bundle.py tests\test_rag_v2_ingestion_workers.py tests\test_rag_v2_remote_ingestion_client.py tests\test_rag_v2_ingestion_service.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall src tests
.\.venv\Scripts\python.exe scripts\check_docs.py
git diff --check
```

