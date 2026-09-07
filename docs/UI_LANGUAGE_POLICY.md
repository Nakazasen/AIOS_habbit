# Chính sách tiếng Việt cho giao diện và thông báo

## Mục đích

AIOS WorkLens phục vụ người dùng không học công nghệ thông tin và không sử dụng tiếng Anh. Người dùng phải hiểu được trạng thái của chương trình và biết cần làm gì tiếp theo mà không phải tra nghĩa thuật ngữ kỹ thuật.

## Phạm vi bắt buộc

Tiếng Việt là ngôn ngữ giao diện duy nhất được hỗ trợ. Quy tắc áp dụng cho mọi nội dung do chương trình tạo hoặc hiển thị cho người dùng và người vận hành:

- Nút, nhãn, menu, ô nhập, hướng dẫn và trợ giúp.
- Trạng thái trống, tiến độ, thông báo thành công và thông báo chờ.
- Cảnh báo, lỗi kiểm tra dữ liệu và hướng dẫn khắc phục.
- Nhật ký vận hành, bảng trạng thái, đầu ra dòng lệnh và báo cáo người dùng đọc.
- Nội dung do AI soạn cho người dùng, trừ đoạn trích nguồn cần giữ nguyên để bảo toàn bằng chứng.

Không dùng câu tiếng Anh hoặc ngôn ngữ khác làm phương án dự phòng. Không hiển thị bộ chọn ngôn ngữ giao diện khác tiếng Việt.

## Quy tắc trình bày

1. Viết bằng câu ngắn, từ thông dụng và nói rõ việc người dùng cần làm tiếp theo.
2. Không bắt người dùng hiểu các từ như RAG, provider, bridge, hash, gate, stack trace hoặc tên model để thao tác hằng ngày.
3. Nếu cần giữ mã thiết bị, mã lỗi, tên tệp, đường dẫn tương đối hoặc hằng kỹ thuật, phải trình bày chúng như định danh và giải thích ý nghĩa bằng tiếng Việt gần đó.
4. Tài liệu nguồn tiếng Nhật, tiếng Trung hoặc ngôn ngữ khác có thể giữ nguyên nội dung gốc để không làm sai bằng chứng; mọi nút điều khiển, chú thích, kết luận và hướng dẫn của chương trình vẫn phải bằng tiếng Việt.
5. Không hiện traceback, đường dẫn hệ thống, khóa bí mật hoặc nội dung `local_only` chưa được làm sạch.

## Xử lý lỗi từ bên ngoài

- Chương trình phải bắt lỗi từ thư viện, hệ điều hành và dịch vụ bên ngoài trước khi lỗi đến giao diện.
- Mỗi lỗi được đổi thành một câu tiếng Việt nói rõ chuyện gì xảy ra và người dùng có thể làm gì.
- Nếu chưa có ánh xạ cụ thể, dùng thông báo an toàn: “Chương trình gặp sự cố khi thực hiện việc này. Hãy thử lại; nếu vẫn lỗi, gửi mã sự cố cho người phụ trách.”
- Có thể lưu mã sự cố để kỹ thuật viên tra cứu, nhưng không hiển thị nguyên văn câu lỗi tiếng Anh cho người dùng.

## Điều kiện nghiệm thu

Một màn hình hoặc luồng công việc chỉ được coi là hoàn tất khi:

1. Kiểm tra toàn bộ trạng thái bình thường, trạng thái trống, chờ, thành công, cảnh báo và lỗi.
2. Cố ý tạo lỗi từ thư viện hoặc dịch vụ bên ngoài và xác nhận không có câu tiếng Anh lọt ra.
3. Nhật ký vận hành và báo cáo mà người dùng đọc đều dùng tiếng Việt dễ hiểu.
4. Người kiểm thử không học công nghệ thông tin có thể nói được chương trình đang làm gì và bước tiếp theo là gì.

Mã nguồn, tên hàm, tên lớp, đường dẫn lập trình và thông tin chẩn đoán chỉ dành cho nhà phát triển không phải câu giao diện, nhưng chúng không được lọt ra màn hình hoặc nhật ký vận hành thông thường.
