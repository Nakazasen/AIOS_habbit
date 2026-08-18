# Kiểm Toán Kế Thừa Nvidia (Nvidia Inheritance Audit)

## Trạng Thái (Status)
KEEP_AS_REFERENCE / PAUSE đối với runtime nặng. Không sao chép mã nguồn nào.

## Tài Liệu Đã Đọc (Read Materials)
- `README.md`
- `package.json`
- Cấu trúc cấp cao nhất

## Cấu Trúc Thư Mục (Folder Structure)
- `tools`, `tests`, `skills`, `flowkit`, `docs`, `proof`, `node_modules`, `.nvidia-agent`

## Điểm Đầu Vào (Entrypoints)
- `npm start` / `tools/nvidia-server.mjs`
- Các tập lệnh CLI và agent trong `tools`
- Electron desktop qua `electron-main.js`

## Kiểm Thử / Tập Lệnh (Tests / Scripts)
`package.json` liệt kê nhiều bài kiểm thử: điều tuyến provider, kiểm tra trước cầu nối, kiểm thử khói trình duyệt, các chỉnh sửa đang chờ xử lý, thao tác tệp, độ tin cậy, xung đột cổng.

## Các Tính Năng Đã Quan Sát (Features Observed)
- Trừu tượng hóa provider và gọi công cụ (tool calling).
- Các mô hình công cụ / MCP server.
- Các công việc lệnh (command jobs) và các chỉnh sửa đang chờ xử lý.
- Bộ kiểm thử khói trình duyệt và bằng chứng UI.
- Vỏ ứng dụng desktop Electron.

## Các Module / Khái Niệm Tái Sử Dụng Được (Reusable Modules / Concepts)
- Trừu tượng hóa provider có thể cung cấp thông tin cho Agent Bridge tương lai.
- Kiểm thử khói trình duyệt có thể giúp xác thực giao diện người dùng WorkLens sau này.
- An toàn cho công việc lệnh có thể định hướng việc thực thi hành động trong tương lai.

## Module Bị Bỏ / Chưa Rõ Ràng (Dead / Unclear Modules)
Không có module nào bị tuyên bố là đã chết. Vỏ runtime/IDE/Electron nằm ngoài phạm vi của v0.1 và có thể TẠM DỪNG (PAUSED).

## Rủi Ro (Risks)
- Chứa `.env`, `node_modules`, log và trạng thái runtime; tuyệt đối không sao chép dữ liệu.
- Độ phức tạp cao và các vấn đề về provider có thể làm chệch hướng Case Cockpit.
- Bản sắc sản phẩm khác với WorkLens.

## Ứng Viên Thu Hoạch (Harvest Candidates)
| Ứng viên (Candidate) | Trạng thái (Status) | Độ khớp vòng lặp (Loop Fit) | Kiểm thử (Tests) | Khả năng chuyển đổi (Portability) | Độ phức tạp (Complexity) |
|---|---|---|---|---|---|
| Trừu tượng hóa provider | NEEDS_AUDIT | Agent Bridge | Có | Thấp-Trung bình | Cao |
| Bộ kiểm thử khói trình duyệt | NEEDS_AUDIT | Xác thực | Có | Trung bình | Trung bình |
| Mô hình công việc lệnh | NEEDS_AUDIT | Hành động | Có | Trung bình | Cao |
| Vỏ Electron | PAUSE | Chỉ phân phối | Chưa rõ | Thấp | Cao |

## Khuyến Nghị (Recommendation)
Không chuyển đổi runtime. Giữ các gói prompt làm cầu nối v0.1. Xem xét lại sau khi thử nghiệm.

