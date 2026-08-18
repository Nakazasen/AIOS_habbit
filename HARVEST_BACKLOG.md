# Danh sách Hạng mục Thu hoạch Kế thừa (Harvest Backlog)

Tất cả các ứng viên từ repository cũ đều bắt đầu ở trạng thái `NEEDS_AUDIT`. Không có mục nào ở trạng thái SẴN SÀNG (READY) cho đến khi bằng chứng, bài kiểm thử, độ phức tạp và mức độ phù hợp với vòng lặp WorkLens được xác minh đầy đủ.

| Ứng viên (Candidate) | Repo Nguồn | Trạng thái | Độ khớp Vòng lặp | Kiểm thử Đã biết | Rủi ro Phức tạp | Ghi chú |
|---|---|---|---|---|---|---|
| Script trạng thái runtime quản trị | ABW_NVIDIA_FUSION_CONTROL | NEEDS_AUDIT | Quản trị hỗ trợ an toàn Hành động/Bài học | Chưa rõ | Trung bình | Có thể trở thành checklist audit WorkLens, không port trực tiếp. |
| Mẫu kiến trúc cầu nối (Bridge pattern) | ABW_NVIDIA_FUSION_CONTROL | NEEDS_AUDIT | Cầu nối Agent sau Gói Prompt | Chưa rõ | Trung bình | Bọc khái niệm trước; không sao chép mã nguồn. |
| Bố cục tri thức `.brain` | skill-Anti-brain-wiki_note | NEEDS_AUDIT | Bộ nhớ học nghề và tái sử dụng | Có khả năng | Trung bình | Cần đơn giản hóa cho kết quả sự vụ. |
| Quy trình nạp/truy vấn Wiki | skill-Anti-brain-wiki_note | NEEDS_AUDIT | Bằng chứng → Bài học | Có khả năng | Cao | Không sao chép toàn bộ diện tích quy trình ABW. |
| Kỷ luật audit/đánh giá/chống thành công giả | skill-Anti-brain-wiki_note | NEEDS_AUDIT | Quản trị xuyên suốt vòng lặp | Có khả năng | Thấp-Trung bình | Ứng viên tốt nhất để áp dụng vào chính sách. |
| Trừu tượng hóa nhà cung cấp (Provider) | Nvidia | NEEDS_AUDIT | Cầu nối Agent | Có, theo package scripts | Cao | Để sau; các gói prompt hiện tại là đủ. |
| Trình quản lý tác vụ lệnh (Command job) | Nvidia | NEEDS_AUDIT | Thực thi hành động | Có, theo package scripts | Cao | Nguy hiểm nếu triển khai sớm. |
| Khung kiểm thử giao diện / trình duyệt | Nvidia | NEEDS_AUDIT | Xác thực kiểm chứng | Có | Trung bình | Hữu ích cho các kiểm tra smoke UI trong tương lai. |
| Vỏ ứng dụng Desktop Electron | Nvidia | NEEDS_AUDIT | Phân phối ứng dụng | Chưa rõ | Cao | TẠM DỪNG (PAUSE) cho đến khi thử nghiệm pilot chứng minh nhu cầu. |

