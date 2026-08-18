# ADR-0003: Chỉ Mục Từ Vựng SQLite Cục Bộ Cho Nền Tảng RAG V2 (Local SQLite Lexical Index)

Status: `ACCEPTED`
Owner role: Project owner / RAG architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing retrieval storage, ranking or adding a vector service

## Bối cảnh (Context)

RAG v2 cần khả năng truy xuất mang tính generic, có thể kiểm tra trực tiếp mà không cần mặc định đám mây hoặc thêm phụ thuộc bắt buộc vào cơ sở dữ liệu vector. Nền tảng hiện tại triển khai một kho lưu trữ chunk SQLite cục bộ với thuật toán chấm điểm từ vựng (lexical) tất định.

## Các phương án đã xem xét (Options Considered)

1. Cơ sở dữ liệu Vector/Cloud làm chỉ mục ban đầu.
2. Chỉ mục từ vựng SQLite cục bộ (Local SQLite lexical index).
3. Tái sử dụng chỉ mục MOM cũ (vốn chứa hard-code miền cụ thể) làm lõi generic.

## Quyết định (Decision)

Sử dụng chỉ mục từ vựng SQLite cục bộ cho nền tảng generic hiện tại. Chỉ mục lưu trữ văn bản chunk và metadata tại đường dẫn do caller chỉ định. Hiện tại đây chưa phải là triển khai FTS/BM25 đầy đủ; roadmap ghi nhận chính xác hành vi từ vựng tất định và các giới hạn xếp hạng song ngữ.

## Hệ quả (Consequences)

- Chỉ mục có thể kiểm tra trực tiếp và nằm hoàn toàn cục bộ nhưng khả năng xếp hạng bị giới hạn có chủ đích.
- Nhận diện OCR ảnh PNG và truy xuất ngữ nghĩa/vector hiện chưa phải là cam kết bảo đảm.
- Caller tự quản lý vòng đời đường dẫn chỉ mục, quyết định sao lưu và dữ liệu đầu vào để tái tạo (rebuild).

## Tác động Bảo mật & Quyền riêng tư (Security and Privacy Impact)

Không có tài liệu nguồn nào bị gửi tới provider chỉ vì được lập chỉ mục. Cơ sở dữ liệu cục bộ vẫn có thể chứa tài liệu nhạy cảm và phải được bảo vệ/loại trừ khỏi Git dưới dạng dữ liệu runtime.

## Di chuyển & Hoàn tác (Migration and Rollback)

Lược đồ chỉ mục được tạo có tính idempotent cho bảng chunk hiện tại. Nếu chỉ mục bị hỏng hoặc không tương thích, hãy lưu lại bằng chứng phù hợp và xây dựng lại từ dữ liệu nguồn/chunk an toàn sẵn có; tuyệt đối không tuyên bố tái tạo không mất dữ liệu nếu thiếu dữ liệu đầu vào đó.

## Bằng chứng Liên kết (Evidence)

- [Thiết kế RAG v2 (RAG v2 design)](../rag_v2/RAG_V2_DESIGN.md)
- [Khả năng tương thích dữ liệu lưu trữ (Persisted-data compatibility)](../contracts/PERSISTED_DATA_COMPATIBILITY.md)
- [Sao lưu và phục hồi (Backup and restore)](../operations/BACKUP_RESTORE.md)

