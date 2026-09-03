# Kế hoạch triển khai: Trợ lý công việc khép kín từ vụ việc đến phòng ngừa lỗi

**Mã tính năng**: `008-evidence-case-loop`

**Ngày cập nhật**: 04/09/2026

**Trạng thái**: Đã duyệt cách triển khai theo các đợt vận hành nhỏ

**Đặc tả**: [spec.md](spec.md)

## 1. Kết quả cần đạt

Giữ nguyên tầm nhìn đầy đủ của US1–US11 nhưng đưa sản phẩm vào dùng theo từng lát cắt có giá trị:

```text
Nguồn và hồ sơ ổn định
        ↓
Một vụ C-call hoặc Jam thật được điều tra đến cùng
        ↓
Bài học đã duyệt được tìm lại
        ↓
LSU được đánh giá bằng dữ liệu thật và chế độ thử nghiệm bóng
        ↓
Chỉ mở cảnh báo, NAS nhiều người, Drum/DLP hoặc Agent lập trình khi đủ điều kiện
```

AI chỉ gom bằng chứng, chỉ ra phần thiếu và tạo bản nháp. Con người xác nhận kết luận, duyệt bài học, phát hành tài liệu và quyết định mọi hành động vận hành.

## 2. Hiện trạng làm điểm xuất phát

- Gate 1A và US1 đã có nền code: migration, role/scope, activity, danh sách/chi tiết case, trạng thái, kết luận và tham chiếu bằng chứng.
- Chuẩn bị nguồn tăng dần đã có code/test nhưng còn thiếu smoke trình duyệt với tài liệu thật.
- Phần nền chưa được gọi là hoàn tất cho tới khi kiểm chứng lại trên cây code hiện tại.
- Parser Jam/C-call/LSU và `line_events.sqlite` đã có; chưa có một pilot line thật khép kín.
- Chưa có vòng chuyên gia trong sản phẩm, bài học được promotion rồi dùng lại, model LSU, shadow hoặc cảnh báo vận hành.
- Gate A NAS vẫn `PARTIAL`; dữ liệu thật và đường dẫn cục bộ không được commit.

Không làm lại phần nền đã có. Đợt đầu tiên là kiểm chứng và sửa đúng lỗi quan sát được, sau đó mở một pilot thực tế.

## 3. Phương án đã chọn

### Phương án A — Triển khai liên tục cả 14 gate

Ưu điểm: mọi ý tưởng đều có task ngay.

Nhược điểm: 81 task tương lai cùng hoạt động, phụ thuộc giả, khó biết khi nào sản phẩm dùng được và dễ xây hạ tầng trước dữ liệu.

Kết luận: không chọn.

### Phương án B — Cắt còn một trình quản lý hồ sơ

Ưu điểm: nhanh và ít code.

Nhược điểm: mất vòng bằng chứng → xác nhận → bài học → phòng ngừa, không còn đúng mục tiêu WorkLens.

Kết luận: không chọn.

### Phương án C — Giữ đặc tả đầy đủ, giao theo đợt nhỏ

Ưu điểm: bảo toàn tầm nhìn, mỗi đợt có giá trị sử dụng và có thể dừng an toàn; chỉ xây kho/model/UI khi đầu vào đã có.

Nhược điểm: trạng thái cần được cập nhật đều và mỗi đợt phải có bằng chứng vận hành riêng.

Kết luận: chọn phương án này.

## 4. Nguyên tắc kiến trúc tối thiểu

1. Workspace Chat vẫn là giao diện chính; không khôi phục Case Cockpit hoặc Studio.
2. `library.sqlite`, `line_events.sqlite` và `workspace_cases.sqlite` giữ ranh giới hiện có, liên kết bằng ID/digest.
3. Chưa tạo `production_prediction.sqlite` cho tới khi Data Gate LSU/Iris đạt.
4. Dùng SQLite và tìm kiếm từ khóa trước; chỉ thêm embedding hoặc thư viện máy học khi phép đo chứng minh cần thiết.
5. Giữ activity hash-chain đang có cho hồ sơ; không nhân rộng chuỗi băm sang mọi bảng nếu chưa có yêu cầu kiểm toán thật.
6. Mặc định người điều tra cũng là chuyên gia đúng công đoạn. Chỉ thêm người thứ hai khi cần theo dõi riêng hoặc phân xử.
7. Pilot artifact chỉ gồm báo cáo điều tra và SOP. Chưa xây danh mục năng lực tổng quát.
8. Mọi giao diện, cảnh báo và lỗi người dùng thấy phải bằng tiếng Việt và không lộ tên engine/model nội bộ.

## 5. Các đợt triển khai

### Đợt 0 — Khóa phần nền để dùng cá nhân

**Phạm vi**

- Đối soát code hiện có với Gate 1A, US1, đặc tả 005 và 007.
- Chạy test tập trung cho chuẩn bị nguồn, lưu/mở case, migration và quyền.
- Smoke trình duyệt: tiến độ lập chỉ mục, trạng thái chưa sẵn sàng, danh sách/chi tiết case, kết luận và đọc lại sau restart.
- Chỉ sửa lỗi thật quan sát được; không viết lại kiến trúc.

**Điều kiện hoàn tất**

- Người dùng hiểu rõ khi thư viện chưa sẵn sàng và thấy tiến độ phần trăm.
- Case tạo từ câu trả lời có thể mở lại, cập nhật trạng thái/kết luận và đọc sau restart.
- Kiểm thử tập trung đạt; bộ kiểm thử toàn bộ, audit, import và kiểm tra tài liệu được ghi đúng kết quả.

### Đợt 1 — Một pilot điều tra line thật

**Phạm vi**

- Chọn đúng một loại sự việc đầu tiên: C-call hoặc Jam.
- Tạo timeline từ log với timezone Việt Nam; event ban đầu luôn là `suspected` và không có fallback giả.
- Gắn SOP, mã lỗi và mapping có phiên bản vào case bằng locator/digest, không sao chép dữ liệu thô.
- Người điều tra kiêm chuyên gia có thể xác nhận/bác bỏ manh mối; người theo dõi công đoạn thứ hai là tùy chọn.
- Tạo bản nháp báo cáo điều tra và SOP từ bằng chứng; người có thẩm quyền duyệt trước khi phát hành.

**Không làm trong đợt này**

- Hàng chờ nhiều người, ma trận quyền quản trị đầy đủ hoặc phân xử phức tạp.
- Capability registry tổng quát cho mọi loại file.
- Model dự đoán, cảnh báo hoặc điều khiển máy.

**Điều kiện hoàn tất**

- Một case thật được phép đi từ mở hồ sơ → timeline → xác nhận → kết luận → báo cáo được duyệt.
- Báo cáo vẫn mô tả đây là hỗ trợ điều tra, không phải chẩn đoán tự động.

### Đợt 2 — Dùng lại bài học đã duyệt

**Điều kiện vào**: có ít nhất một case thật đã kết luận và một phản hồi xác nhận có provenance.

**Phạm vi**

- Tạo ứng viên bài học từ case đã xác nhận.
- Trợ lý/trưởng/phó phòng duyệt promotion hoặc thu hồi.
- Tìm kiếm chính xác/từ khóa bằng SQLite; kết quả luôn dẫn về case, review và evidence gốc.
- Chỉ thêm hàng chờ chuyên gia nhiều người nếu pilot chứng minh có bàn giao thật.

**Điều kiện hoàn tất**

- Bài học chưa duyệt/đã thu hồi không xuất hiện như sự thật.
- Một case mới tìm lại được bài học đã duyệt mà không thay đổi `library.sqlite`.

### Đợt 3 — Thử nghiệm dự đoán LSU nhẹ

**Điều kiện vào**

- Có data dictionary, khóa join, đơn vị, timezone, phiên bản JIG/quy trình, outcome OK/NG và người xác nhận nhãn.
- Đã kiểm tra rò rỉ tương lai, chất lượng nhãn và khả năng phát lại lịch sử.

**Phạm vi**

- Tạo kho dự đoán cục bộ và snapshot có version sau khi Data Gate đạt.
- So sánh không cảnh báo, rule/EWMA/CUSUM và tối đa một model bảng đơn giản chạy CPU.
- Chia dữ liệu theo thời gian/nhóm máy; báo false alarm, missed detection, lead time và độ ổn định.
- Chạy phát lại lịch sử hoặc shadow thủ công trước. Chưa cần scheduler.

**Điều kiện hoàn tất**

- Có báo cáo tái lập được, model/dataset/threshold có version và rollback.
- Mỗi tín hiệu có feature snapshot; không phát cảnh báo vận hành và không điều khiển máy.

### Đợt 4 — Mở rộng có điều kiện

Mỗi nhánh dưới đây là một quyết định riêng, không chặn nhau:

| Nhánh | Chỉ mở khi |
|---|---|
| Cảnh báo trong Workspace Chat | Shadow LSU đạt ngưỡng do chủ sở hữu duyệt, có kill switch và quy trình phản hồi |
| NAS nhiều người | Có môi trường thật để thử một writer–nhiều reader, backup/restore và bàn giao liên ca |
| Drum hoặc DLP | LSU chứng minh hợp đồng lõi có giá trị; mỗi miền có Data Gate và threshold riêng |
| Agent lập trình | Có nhu cầu nghiệp vụ riêng, workspace cách ly, allowlist và người duyệt rõ ràng |
| Artifact khác báo cáo/SOP | Có ít nhất ba loại đầu ra thật cần cùng một cơ chế dùng lại |

## 6. Ánh xạ 14 gate cũ vào kế hoạch mới

| Gate cũ | Cách xử lý |
|---|---|
| 1A | Đợt 0: kiểm toán phần nền đã có, không xây lại |
| 2 | Đợt 0: smoke case UI và vòng đời |
| 3 | Đợt 1: xác nhận tối thiểu cùng người; hàng chờ nhiều người để sau khi có nhu cầu |
| 4 | Đợt 2: promotion thủ công và tìm kiếm SQLite |
| 5 | Đợt 1: đưa lên trước để tạo giá trị vận hành đầu tiên |
| 6 | Đợt 1: chỉ báo cáo điều tra và SOP |
| 7 | Đợt 4: tách thành nhánh Agent lập trình riêng |
| 8 | Đợt 3: chỉ Data Gate LSU/Iris |
| 9 | Đợt 3: baseline thống kê và một model CPU đơn giản |
| 10 | Đợt 3: phát lại lịch sử hoặc shadow thủ công trước |
| 11 | Đợt 4: chỉ sau bằng chứng shadow |
| 12 | Đợt 4: Drum/DLP sau LSU và có gate riêng |
| 13 | Đợt 4: tách NAS, pilot tổ chức và mở rộng miền thành ba việc độc lập |
| 14 | Đóng ở cuối từng đợt nhỏ, không chờ toàn bộ tầm nhìn |

## 7. Ngân sách kỹ thuật cho máy i5, RAM 16 GB, không GPU

- Một worker lập chỉ mục tại một thời điểm; có thể dừng và tiếp tục.
- SQLite/FTS và xử lý theo lô nhỏ là mặc định.
- Không chạy LLM lớn cục bộ, AutoML, deep learning, nhiều model song song hoặc quét tham số lớn.
- Embedding/rerank chỉ chạy khi cần và phải hiển thị rõ trạng thái sẵn sàng cho người dùng.
- Dữ liệu prediction ưu tiên phép biến đổi tất định và model bảng nhẹ trên CPU.

## 8. Chiến lược kiểm thử

- Mỗi task: chạy test tập trung cho module vừa đổi và `git diff --check`.
- Mỗi story: chạy luồng restart/readback, privacy, quyền và thông báo tiếng Việt liên quan.
- Trước hợp nhất, phát hành hoặc đánh dấu hoàn tất một đợt: chạy compile, toàn bộ pytest, CLI audit, import Workspace Chat và kiểm tra tài liệu.
- Thiếu môi trường/dữ liệu thật phải ghi `PARTIAL` hoặc `BLOCKED`; không thay bằng fixture để tuyên bố vận hành.
- Người kiểm toán không dùng chính kết luận của lượt triển khai làm bằng chứng duy nhất.

## 9. Rủi ro và cách dừng an toàn

| Rủi ro | Cách kiểm soát |
|---|---|
| Tài liệu trạng thái lệch code | `ROADMAP.md` là nguồn trạng thái duy nhất; tasks chỉ chứa đợt đang làm |
| Xây quá sớm | Mọi đợt có điều kiện vào; chưa đạt thì không tạo schema/dependency/UI tương ứng |
| Mất dữ liệu | Migration có backup/readback; không xóa dữ liệu/cột cũ chỉ để làm sạch |
| Lộ dữ liệu nhà máy | Chỉ lưu locator/digest đã làm sạch; `local_only` không rời máy và không commit |
| Người dùng hiểu nhầm AI | UI ghi rõ nháp, manh mối, chưa xác nhận và người duyệt |
| Máy yếu bị nghẽn | Một worker, lô nhỏ, model nhẹ và thao tác có thể tiếp tục |

## 10. Kiểm tra Hiến chương

- Bằng chứng đi trước tuyên bố: đạt ở mức kế hoạch.
- Ưu tiên cục bộ và an toàn dữ liệu: đạt ở mức kế hoạch.
- Workspace Chat là giao diện chính: giữ nguyên.
- Không fake PASS: có điều kiện đóng và trạng thái `PARTIAL`/`BLOCKED` rõ ràng.
- Không over-engineer: kho prediction, hàng chờ nhiều người, registry tổng quát và adapter mới đều chưa được kích hoạt trước nhu cầu.
- Không có ngoại lệ Hiến chương được đề xuất.
