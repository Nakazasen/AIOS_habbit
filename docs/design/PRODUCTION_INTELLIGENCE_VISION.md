# Tầm Nhìn Trí Tuệ Sản Xuất (Production Intelligence Vision)

Status: `PLANNED — future design reference; no delivery gate opened`

Owner role: Project owner / product architect  
Last reviewed: 2026-08-08  
Review cadence: Before opening any production-traceability, alerting, prediction, or prevention Gate Card

## Mục đích (Purpose)

AIOS WorkLens có thể phát triển từ hệ thống trí tuệ công việc ưu tiên cục bộ (local-first) thành **năng lực hỗ trợ ra quyết định chất lượng sản xuất ưu tiên cục bộ (local-first production-quality decision-support)**. Nó sẽ hỗ trợ con người điều tra và ngăn ngừa các vấn đề chất lượng sản xuất thông qua việc duy trì một chuỗi truy xuất nguồn gốc có thể kiểm toán từ lô linh kiện (component lot) đến kết quả sản xuất quan sát được.

Đây là định hướng thiết kế trong tương lai, không phải là tuyên bố rằng AIOS hiện tại đã dự đoán được lỗi sản xuất. Tài liệu này không mở Giai đoạn 9 (Phase 9), P1.0, thay đổi phụ thuộc hay bất kỳ hành vi runtime nào.

## Kết quả Kim chỉ nam (North-star Outcome)

Khi một lô sản xuất mới được đánh giá, người dùng được ủy quyền cuối cùng sẽ có thể nhận được một kết quả có giới hạn, có bằng chứng xác thực như:

```text
Rủi ro: trung bình, không phải là quyết định xuất hàng/chặn hàng.
Lý do: các lô tương tự trong lịch sử, số đo thực nghiệm, điều kiện dây chuyền và kết quả trên jig kiểm tra.
Bằng chứng: các bản ghi liên kết về lô, Unit, kiểm thử, lỗi hỏng và hồ sơ điều tra sự vụ.
Độ không chắc chắn: những thông tin còn thiếu, xung đột hoặc chưa được xác nhận.
Gợi ý kiểm tra tiếp theo: một bước ngăn chặn cách ly hoặc xác minh đã được con người phê duyệt.
```

Hệ thống tuyệt đối không bao giờ được tự ý quyết định một lô hàng là tốt/xấu, tự ý chặn sản xuất, tự ý xuất hàng, hoặc tuyên bố một nguyên nhân gốc rễ đã được xác nhận khi chưa có sự kiểm soát từ con người và bằng chứng bắt buộc.

## Chuỗi Truy xuất Nguồn gốc (Traceability Chain)

Chuỗi tối thiểu mong muốn là:

```text
Nhà cung cấp / Linh kiện / Lô linh kiện (Supplier / Component / Lot)
              ↓
Kiểm tra đầu vào và các phép đo thô (Incoming inspection & raw measurements)
              ↓
Mối quan hệ BOM và số serial của Unit
              ↓
Lượt chạy quy trình: chuyền, công đoạn, máy, ca, thời gian, điều kiện kiểm soát
              ↓
Bước kiểm tra/Jig, số đo thô, đạt/không đạt (pass/fail), mã lỗi
              ↓
Lỗi hỏng, sửa chữa, xử lý và kết quả chất lượng cuối cùng
              ↓
Điều tra sự vụ: nguyên nhân nghi ngờ, nguyên nhân xác nhận, cảnh báo giả, kết quả ngăn chặn
```

Mỗi liên kết cần định danh ổn định, dấu thời gian, con trỏ nguồn, phân loại và nguồn gốc (provenance). Các liên kết bị thiếu phải hiển thị rõ ràng là đang thiếu — không được tự tiện suy đoán từ các tên tương tự hoặc giả định của mô hình LLM.

## Các Giai đoạn Trưởng thành của Sản phẩm (Product Maturity Stages)

### Giai đoạn 0 — Trí tuệ tài liệu đáng tin cậy (Tiền đề tiên quyết hiện tại)

- Đọc hiểu tài liệu cục bộ, bảng biểu, log hệ thống và báo cáo.
- Truy xuất bằng chứng và cung cấp trích dẫn nguồn (citations).
- Từ chối trả lời (abstain) khi chưa có đủ bằng chứng.
- Đo lường chất lượng câu trả lời mà không làm suy yếu quyền riêng tư hoặc nguồn gốc dữ liệu.

Đây là trọng tâm chất lượng RAG v2 hiện tại. Nó bắt buộc phải trưởng thành trước khi đưa ra các tuyên bố về trí tuệ sản xuất.

### Giai đoạn 1 — Truy xuất nguồn gốc và điều tra lịch sử

- Nạp các bản ghi sản xuất cục bộ có cấu trúc với schema đã được công bố.
- Trả lời các câu hỏi truy xuất nguồn gốc, ví dụ: những lô nào được dùng chung bởi các Unit bị lỗi jig kiểm tra cụ thể?
- Liên kết các bản ghi vận hành với hướng dẫn công việc áp dụng, ghi chú sửa chữa và báo cáo điều tra sự vụ.
- Hiển thị chuỗi liên kết và bản ghi nguồn, bao gồm cả các lỗ hổng thiếu dữ liệu và các bản ghi mâu thuẫn.

Giai đoạn này nghiêm cấm đưa ra bất kỳ tuyên bố nào về dự báo.

### Giai đoạn 2 — Cảnh báo minh bạch

- Đánh giá các quy tắc đã được review và tín hiệu kiểm soát thống kê cục bộ.
- Đánh dấu tỷ lệ phế phẩm bất thường, số đo kiểm thử, sự dịch chuyển hiệu suất (yield) hoặc liên kết lô.
- Giải thích rõ ràng quy tắc/tín hiệu cụ thể, cửa sổ thời gian so sánh và các bản ghi hỗ trợ.
- Yêu cầu người vận hành xác nhận, điều tra, bác bỏ hoặc gắn nhãn cảnh báo.

Cảnh báo chỉ là gợi ý để điều tra sự vụ. Chúng không phải là cơ chế kiểm soát sản xuất tự động.

### Giai đoạn 3 — Dự đoán rủi ro có sự đánh giá của con người

- Huấn luyện/đánh giá mô hình cục bộ có phiên bản CHỈ trên tập dữ liệu được quản trị với kết quả đã biết và có kiểm soát rò rỉ dữ liệu.
- Trả về mức rủi ro, độ chuẩn hóa/độ không chắc chắn (uncertainty), các yếu tố ảnh hưởng và bằng chứng lịch sử tương đương.
- Lưu giữ phiên bản dự đoán, feature schema, định danh tập dữ liệu và quyết định review.
- Bắt buộc có con người đánh giá trước bất kỳ hệ quả vận hành nào.

Dự đoán tuyệt đối không được biểu diễn như bằng chứng xác thực nguyên nhân.

### Giai đoạn 4 — Hỗ trợ phòng ngừa dựa trên bằng chứng

- Đề xuất các hành động ngăn ngừa, kiểm tra, lấy mẫu hoặc leo thang đã được kiểm chứng.
- Giải thích những trường hợp lịch sử nào hỗ trợ cho khuyến nghị và những điểm nào bằng chứng vẫn chưa chắc chắn.
- Ghi lại quyết định của con người và kết quả thực tế sau đó để hệ thống học hỏi từ thực tiễn đã kiểm chứng thay vì sao chép văn phong trò chuyện.

## Hợp đồng Dữ liệu & Học tập (Data and Learning Contract)

### Các Bản ghi Quản trị Tối thiểu

| Bản ghi | Ví dụ bắt buộc |
|---|---|
| Linh kiện và Lô | `part_id`, `supplier_id`, `lot_id`, thời gian tiếp nhận/kiểm tra |
| Quan hệ Unit / BOM | `unit_serial`, thời gian lắp ráp, `lot_id` linh kiện, số lượng/vị trí khi có sẵn |
| Lượt chạy quy trình | chuyền, công đoạn, máy, ca, định danh người thao tác (khi được phép), điều kiện kiểm soát |
| Jig / Kiểm thử | test ID/phiên bản, bước, giá trị thô/đơn vị, giới hạn/phiên bản, đạt/không đạt, mã lỗi, dấu thời gian |
| Kết quả chất lượng | mã lỗi, sửa chữa/làm lại, xử lý cuối cùng, mẫu số tính yield |
| Điều tra sự vụ | nguyên nhân nghi ngờ vs nguyên nhân xác nhận, ID bằng chứng, quyết định chủ sở hữu, ngăn chặn và hiệu quả |

### Quy tắc Chất lượng Dữ liệu

- Bảo toàn các phép đo thô và đơn vị của chúng; không bao giờ chỉ giữ lại nhãn làm tròn.
- Giữ lại giới hạn/phiên bản test, bản sửa đổi jig/firmware/quy trình và thời gian để không nhầm lẫn thay đổi kỹ thuật với biến động vật liệu hoặc nhà cung cấp.
- Sử dụng ID ổn định và bản ghi ánh xạ rõ ràng; tên gọi đơn thuần không thể dùng làm khóa kết nối (join).
- Gắn dấu thời gian cho mọi sự kiện và phân biệt rõ thời gian xảy ra sự kiện với thời gian dữ liệu cập bến.
- Giữ mã băm nguồn/con trỏ và phân loại bảo mật cục bộ cho mỗi lần nạp dữ liệu.
- Tách biệt rõ ràng sự thật (facts), giả thuyết (hypotheses), nguyên nhân đã xác nhận (confirmed causes) và khuyến nghị (recommendations).
- Ghi nhận các trường chưa rõ/thiếu; không âm thầm thay thế chúng bằng giá trị mặc định.

### Các Nhãn Học tập (Learning Labels)

Hệ thống chỉ có thể học từ các nhãn kết quả phân biệt tối thiểu:

- `suspected`: manh mối cần điều tra;
- `confirmed`: nguyên nhân/kết quả đã được con người đánh giá kèm bằng chứng lưu giữ;
- `false_alarm`: tín hiệu đã điều tra và không được xác nhận;
- `unknown`: không đủ bằng chứng để phân loại;
- `effective` / `ineffective`: kết quả đã đánh giá của hành động ngăn ngừa hoặc khắc phục.

Quá trình huấn luyện/đánh giá bắt buộc phải ngăn chặn rò rỉ kết quả (outcome leakage) — ví dụ: mã sửa chữa cuối cùng không được dùng để dự đoán rủi ro tại thời điểm tiếp nhận lô hàng. Việc phân chia dữ liệu (train/test splits) phải tôn trọng dòng thời gian và nhóm lô/nhà cung cấp/Unit liên quan.

## Ranh giới An toàn, Quyền riêng tư & Vận hành

1. **Thẩm quyền của con người (Human authority):** Kết quả đầu ra chỉ hỗ trợ quyết định của con người được ủy quyền; tuyệt đối không tự động chặn, tự động xuất hàng, tự động làm lại hoặc thay đổi thông số quy trình.
2. **Ưu tiên bằng chứng (Evidence first):** Mọi cảnh báo, dự đoán và khuyến nghị đều phải xác định rõ bằng chứng, phiên bản quy tắc/mô hình và độ không chắc chắn đã biết.
3. **Ưu tiên cục bộ (Local first):** Dữ liệu sản xuất luôn là `local_only` trừ khi có chính sách và sự đồng ý tường minh cho phép một tuyến gửi ra ngoài hẹp hơn.
4. **Không nhúng cứng mã miền vào lõi RAG v2:** Schema, quy tắc và adapter đặc thù sản xuất phải nằm ngoài các hợp đồng RAG/bằng chứng generic.
5. **Hiển thị xung đột minh bạch:** Các giới hạn, ngày tháng, phiên bản test hoặc kết quả mâu thuẫn nhau phải được hiển thị dưới dạng xung đột cần xem xét, không được âm thầm gộp lại.
6. **Khả năng hoàn tác (Rollback):** Dữ liệu nạp, quy tắc, mô hình và khuyến nghị phải có phiên bản, có thể vô hiệu hóa và có đường dẫn khôi phục rõ ràng.
7. **Không tuyên bố quá mức về quan hệ nhân quả:** Tương quan (correlation), độ tương đồng và điểm rủi ro hoàn toàn khác biệt với nguyên nhân gốc rễ đã được xác nhận.

## Định hướng Kiến trúc

Năng lực tương lai là phần mở rộng phân tầng, không phải là sự thay thế cho RAG v2:

```text
Nạp dữ liệu sản xuất có cấu trúc và tài liệu nguồn
       ↓
Bản ghi truy xuất nguồn gốc + liên kết xuất xứ (provenance)
       ↓
Bộ máy cảnh báo quy tắc/thống kê và, sau này, các mô hình rủi ro có quản trị
       ↓
Lựa chọn bằng chứng, giải thích có trích dẫn và Workspace Chat
       ↓
Con người xem xét, lưu bản ghi quyết định và phản hồi kết quả đã kiểm chứng
```

RAG v2 tiếp tục chịu trách nhiệm truy xuất bằng chứng tài liệu và giải thích kết quả bằng Tiếng Việt rõ ràng. Việc truy xuất nguồn gốc có cấu trúc, cảnh báo và dự đoán phải có thể kiểm toán độc lập; mô hình LLM không phải là máy tính ghi nhận ngưỡng, mẫu số tính yield hay quyết định phát hành sản xuất.

## Thực hành Chọn lọc Lấy Cảm hứng từ Semantica

Các công việc tương lai có thể tiếp thu các khái niệm này dưới dạng các triển khai cục bộ gọn nhẹ:

- Quan hệ có định kiểu (typed relations) giữa lô, Unit, kiểm thử, lỗi và hành động;
- Xuất xứ/nguồn gốc (provenance/lineage) gắn liền với sự thật và quyết định;
- Trạng thái xung đột tường minh thay vì ép buộc gộp dữ liệu;
- Hiệu lực theo thời gian của phép đo, giới hạn và bản sửa đổi quy trình;
- Duyệt đồ thị (graph traversal) chỉ như một kênh truy xuất ứng viên bổ sung;
- Bản ghi quyết định liên kết một khuyến nghị với quyết định của con người và kết quả thực tế.

AIOS tuyệt đối không áp dụng toàn bộ framework Semantica theo mặc định, nhằm tránh tạo ra một runtime cồng kềnh, chồng chéo và nguồn chân lý thứ hai tiềm ẩn khi chưa chứng minh được lợi ích vận hành cụ thể.

## Bằng chứng Mở Gate (Gate-opening Evidence)

Không có Gate Card triển khai nào cho Giai đoạn 1–4 được phép mở nếu thiếu các bằng chứng liên quan:

| Giai đoạn | Bằng chứng tối thiểu trước khi mở triển khai |
|---|---|
| 1: Truy xuất nguồn gốc | Từ điển dữ liệu được chủ sở hữu phê duyệt; bản ghi mẫu với các khóa join ổn định; phân loại bảo mật; bộ câu hỏi truy vấn nghiệm thu; kế hoạch hoàn tác nạp dữ liệu |
| 2: Cảnh báo | Định nghĩa đường cơ sở/cửa sổ kiểm soát; các ngưỡng đã review; quy trình xác nhận cảnh báo; kế hoạch đo lường dương tính giả; công tắc tắt an toàn |
| 3: Dự đoán | Đủ kết quả xác nhận/tiêu cực; đánh giá chống rò rỉ dữ liệu theo thời gian/nhóm; giao thức đánh giá đóng băng; đánh giá độ chuẩn hóa và sai lệch; sự phê duyệt của chủ sở hữu cho việc ra quyết định |
| 4: Phòng ngừa | Thư viện hành động khắc phục đã review; bằng chứng về tính hiệu quả; quy trình con người phê duyệt; chính sách hoàn tác/leo thang; cơ chế thu thập kết quả sau hành động |

Mỗi gate tiềm năng bắt buộc phải xác định các thước đo thành công, chi phí cảnh báo giả, rủi ro bỏ sót phát hiện, ranh giới quyền riêng tư và kế hoạch kiểm chứng toàn diện. Điểm trung bình tốt không thể bù đắp cho việc rò rỉ dữ liệu, thiếu nguồn gốc xuất xứ, hành động tự động chưa được xem xét hoặc vi phạm quyền riêng tư.

## Quan hệ với Roadmap Hiện tại

- Nguồn trạng thái canonical hiện tại vẫn là [ROADMAP.md](../../ROADMAP.md).
- Gate chất lượng câu trả lời RAG v2 đang hoạt động không thay đổi và phải được giữ đóng băng trong suốt quá trình đánh giá mù.
- Tầm nhìn này chi tiết hóa định vị dài hạn của **Giai đoạn 9 — Nền tảng Truy xuất Nguồn gốc Sản xuất**; đây không phải là kế hoạch triển khai của Giai đoạn 9.
- Mọi kế hoạch trong tương lai bắt buộc phải bắt đầu bằng một bản đặc tả (spec) và Gate Card chuyên dụng thay vì coi tầm nhìn này như phạm vi mã nguồn đã được phê duyệt trước.
