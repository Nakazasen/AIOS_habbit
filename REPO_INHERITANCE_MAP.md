# Bản đồ Kế thừa Repository (Repository Inheritance Map)

| Repo | Vai trò Hiện tại | Vai trò Tương lai | Giữ lại cái gì | Bọc lại cái gì (Wrap) | Chuyển đổi sau (Port Later) | Tạm dừng cái gì | Chỉ bỏ khi chứng minh vô dụng | Rủi ro | Đường dẫn Bằng chứng |
|---|---|---|---|---|---|---|---|---|---|
| AIOS_habbit | Repo sản phẩm trung tâm gồm CLI, Studio, Case Cockpit | Trung tâm sản phẩm AIOS WorkLens | Case Cockpit, quản trị riêng tư, tests, tài liệu | Các hàm hỗ trợ CLI phía sau UI | Kiến trúc module hóa hơn sau thử nghiệm pilot | Tái cấu trúc quy mô lớn | Chưa bỏ gì | Phình tính năng (feature creep), rò rỉ dữ liệu cục bộ | `[LOCAL_WORKSPACE]\AIOS_habbit` |
| ABW_NVIDIA_FUSION_CONTROL | Repo tài liệu quản trị/kiểm soát kết hợp ABW/NVIDIA | Nguồn tham chiếu quản trị | Quản trị chuẩn mực, kiến trúc cầu nối, khái niệm trạng thái runtime | Ý tưởng checklist quản trị | Nhật ký quyết định và hợp đồng an toàn nếu khớp với WorkLens | Nhận diện thương hiệu provider/runtime | Chưa bỏ gì | Lỗi mã hóa trong tài liệu, quản trị trừu tượng có thể làm chậm sản phẩm | `[LOCAL_WORKSPACE]\ABW_NVIDIA_FUSION_CONTROL` |
| skill-Anti-brain-wiki_note | Gói kỹ năng ABW/wiki/tri thức | Tham chiếu quy trình và quản trị tri thức | Cấu trúc `.brain`, luồng xử lý raw/processed/wiki, kỷ luật audit/đánh giá | Các mẫu quy trình truy vấn/nạp dữ liệu | Các mẫu đóng gói wiki an toàn và luồng tiếp tục | Toàn bộ giao diện quy trình ABW trên UI sản phẩm | Chưa bỏ gì | Diện tích bề mặt lớn; có thể gây phân tâm khỏi Case Cockpit | `[LOCAL_WORKSPACE]\skill-Anti-brain-wiki_note` |
| Nvidia | Vỏ bọc runtime/provider agent đang hoạt động | Chỉ dùng làm tham chiếu cầu nối agent | Trừu tượng hóa provider, gọi công cụ, tác vụ lệnh, mẫu kiểm tra trình duyệt | Khái niệm cầu nối CLI | Cầu nối agent tùy chọn sau khi các gói prompt ổn định | Bản sao Electron/IDE, runtime phụ thuộc nhiều vào provider | Chưa bỏ gì | Chứa `.env`, node_modules, trạng thái runtime lớn; tuyệt đối không sao chép mù quáng | `[LOCAL_WORKSPACE]\Nvidia` |

Không có repository nào bị phân loại là rác. Tất cả các repo ngoài trung tâm đều là nguồn kế thừa tiềm năng chờ đợi đánh giá sâu hơn dựa trên bằng chứng.


