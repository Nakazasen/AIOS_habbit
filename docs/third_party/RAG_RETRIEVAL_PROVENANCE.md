# Nguồn Gốc Bên Thứ Ba Của Truy Xuất RAG (RAG Retrieval Third-Party Provenance)

Tệp này ghi lại các gói được duy trì bên ngoài và các dòng mô hình được sử dụng bởi phòng thí nghiệm truy xuất Cổng H (Gate H) tùy chọn. Bản cài đặt AIOS Habit mặc định không cài đặt hoặc tải các thành phần này.

## FlagEmbedding / BGE-M3

- Kho lưu trữ thượng nguồn (Upstream repository): https://github.com/FlagOpen/FlagEmbedding
- Gói (Package): `FlagEmbedding==1.3.5`
- Giấy phép (License): MIT (xác minh bản phân phối đã cài đặt và thẻ mô hình đã chọn trước khi thăng cấp)
- Tích hợp: API công khai `BGEM3FlagModel` thông qua `src/aios_habit/rag_v2/retrieval_backends.py`
- Hành vi được sử dụng: embedding dày đặc đa ngôn ngữ (dense embeddings) và trọng số từ vựng thưa thớt học được (sparse lexical weights)
- Chính sách tính cục bộ: đường dẫn mô hình đã cấu hình phải tồn tại cục bộ; toàn bộ cây thư mục được kiểm tra đối chiếu với mã băm SHA-256 đã cấu hình trước khi khởi tạo mô hình; quyền truy cập mạng bị vô hiệu hóa trong quá trình khởi tạo và suy luận.
- Khóa mô hình: cấu hình runtime phải cung cấp bản sửa đổi mô hình rõ ràng và checksum cây thư mục. Tuyệt đối không commit trọng số mô hình vào repository này.

## BGE reranker v2 M3

- Dòng mô hình: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Gói runtime: `FlagEmbedding==1.3.5`
- Giấy phép: xác minh thẻ mô hình đã chọn trước khi thăng cấp
- Tích hợp: API công khai `FlagReranker` thông qua `src/aios_habit/rag_v2/retrieval_backends.py`
- Hành vi được sử dụng: chấm điểm tương tác chéo truy vấn - tài liệu (cross-encoder) đa ngôn ngữ
- Chính sách tính cục bộ: các ràng buộc đường dẫn fail-closed, bản sửa đổi, checksum và offline giống hệt như BGE-M3.

## Haystack và RAGFlow

Haystack và RAGFlow đã cung cấp thông tin cho việc đánh giá kiến trúc (các bộ truy xuất riêng biệt, kết hợp xếp hạng, xếp hạng lại và nguồn gốc giai đoạn), nhưng không có mã nguồn nào từ cả hai kho lưu trữ được sao chép trong quá trình triển khai Cổng H hiện tại. Nếu quy tắc dừng kích hoạt và một bản thử nghiệm adapter được thực hiện, hãy ghi lại commit repository, các tệp nguồn, giấy phép và các sửa đổi chính xác ở đây.

## Các Yêu Cầu Xác Thực Trước Khi Thăng Cấp (Verification requirements before promotion)

1. Ghi lại checksum thư mục mô hình cục bộ chính xác trong metadata của lượt chạy thi đấu.
2. Ghi lại phiên bản gói, thiết bị, bản sửa đổi mô hình, số chiều và độ trễ runtime đo được.
3. Chạy với mạng bị vô hiệu hóa sau khi việc tải mô hình được thực hiện bên ngoài benchmark.
4. Xác nhận các tập hợp dense, sparse, kết hợp và xếp hạng lại không bị rỗng đối với các nhánh áp dụng.
5. Giữ nguyên các thông báo của nhà phát triển thượng nguồn nếu mã nguồn trực tiếp từng được sao chép thay vì được gọi qua API công khai.

