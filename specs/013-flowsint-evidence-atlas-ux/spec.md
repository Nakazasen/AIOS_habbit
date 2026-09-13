# Feature Specification: 013-flowsint-evidence-atlas-ux

**Feature Branch**: `013-flowsint-evidence-atlas-ux`  
**Created**: 2026-09-13  
**Status**: Draft  
**Input**: Tái cấu trúc UX Đồ thị bằng chứng (Evidence Graph) và Atlas chi tiết theo phong cách đồ thị điều tra chuyên nghiệp Flowsint (bố cục 3 cột: Thực thể - Canvas Pill nền tối - Thanh kiểm tra chi tiết), loại bỏ dump text trên node và sửa triệt để lỗi rò rỉ thẻ SVG `<tspan>`.

---

## Bối cảnh & Vấn đề Cốt lõi

Hiện tại, tính năng trực quan hóa bằng chứng (`Evidence Graph` và `Evidence Atlas`) trong AIOS WorkLens đang gặp 3 khuyết điểm lớn về mặt UX/UI:
1. **Node bị nhồi nhét cả đoạn văn bản (Dump text)**: Các hộp "Trích dẫn [k]" và "Nguồn tài liệu" nhồi nhét nguyên cả đoạn trích dẫn dài (`[DOCUMENT ARCHITECTURE & SUMMARY] ## INTRODUCTION...`) trực tiếp vào khung vẽ của node khiến kích thước hộp phình to, chữ bị cắt vụn giữa chừng (`truncate`), làm đồ thị rối rắm và khó theo dõi.
2. **Thiếu bảng kiểm tra chi tiết (Inspector Panel) độc lập**: Người dùng buộc phải căng mắt đọc nội dung trích dẫn ngay trên mặt node nhỏ hẹp. Khi chuyển sang phong cách Flowsint, node trên canvas chỉ hiển thị nhãn ngắn dạng viên thuốc (`pill`), toàn bộ văn bản đầy đủ, độ tin cậy và siêu dữ liệu được đưa sang thanh kiểm tra bên phải khi click.
3. **Lỗi hiển thị SVG markup thô trên Atlas (`<tspan>` leak)**: Khi người dùng bấm "Mở Atlas chi tiết", hàm `_polish_evidence_atlas_html` trong `excaliflow_adapter.py` đã bắt regex nhãn node nhưng không bóc tách (strip) các thẻ `<tspan>` đã được sinh từ tầng dưới, dẫn đến việc escape lần hai và in thẳng mã nguồn HTML/SVG (`<tspan x="84" dy="0">...`) lên màn hình người dùng.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sửa triệt để lỗi rò rỉ SVG Markup (`<tspan>`) trên Atlas (Priority: P1)
Người dùng khi nhấn nút "Mở Atlas chi tiết" sẽ nhìn thấy sơ đồ tri thức hiển thị chữ tiếng Việt và tiếng Nhật sạch sẽ, sắc nét; tuyệt đối không còn xuất hiện bất kỳ chuỗi markup kỹ thuật nào như `<tspan x="84" dy="0">`.

**Why this priority**: Lỗi hiển thị thẻ SVG thô làm hỏng trải nghiệm người dùng, vi phạm trực tiếp Quy tắc Hiển thị và Chính sách Ngôn ngữ của hệ thống. Đây là lỗi bề mặt nghiêm trọng cần xử lý ngay lập tức.

**Independent Test**: Mở bất kỳ câu trả lời nào có bằng chứng, bấm "Mở Atlas chi tiết", kiểm tra toàn bộ nhãn node trên canvas SVG xem có xuất hiện ký tự `<tspan>` hay không. 

**Acceptance Scenarios**:
1. **Given** một `EvidenceTrace` hợp lệ với các trích dẫn tiếng Việt/CJK, **When** hệ thống gọi `render_evidence_atlas_html()`, **Then** đầu ra SVG không chứa bất kỳ thẻ `<tspan>` nào bị escape thành chuỗi hiển thị thô (`&lt;tspan` hoặc `<tspan` bên trong text node).
2. **Given** nhãn đầu vào chứa các thẻ định dạng HTML/SVG, **When** qua bộ chuẩn hóa `_polish_evidence_atlas_html`, **Then** hệ thống thực hiện `strip_tags` lấy `textContent` thuần túy trước khi chia dòng và đóng gói thẻ SVG.

---

### User Story 2 - Bố cục 3 Cột Phong Cách Flowsint cho Đồ Thị Bằng Chứng (Priority: P1)
Người dùng mở xem "Đồ thị bằng chứng" sẽ thấy giao diện 3 cột trực quan, hiện đại và tinh gọn:
- **Cột trái (Danh sách Thực thể & Bộ lọc)**: Liệt kê phân tầng: Câu hỏi, Câu trả lời, Trích dẫn `[1]`...`[n]`, và các Tệp nguồn; kèm bộ lọc trạng thái và ô tìm kiếm nhanh.
- **Cột giữa (Khung vẽ Canvas Nền Tối)**: Nền tối chuẩn màu `#0f172a`, các node được thiết kế dạng **viên thuốc (pill)** nhỏ gọn:
  * `question`: Tối đa 60 ký tự, biểu tượng ❓.
  * `answer`: "Câu trả lời" + 1 dòng đầu tiên, biểu tượng 💡.
  * `citation`: Chỉ hiện mã định danh gọn gàng `[1]`, `[2]`, biểu tượng 🏷️.
  * `source`: Chỉ hiện tên tệp tài liệu ngắn gọn (ví dụ `MOMデータ連携説明.pdf`), biểu tượng 📄.
  * Các cạnh nối mỏng, thanh thoát, định hướng rõ ràng từ `question -> answer -> citations -> sources`.
- **Cột phải (Bảng Kiểm tra Chi tiết - Inspector Panel)**: Khi bấm vào bất kỳ node nào trên canvas hoặc danh sách bên trái, cột phải sẽ hiển thị toàn bộ nội dung chi tiết: Tiêu đề đầy đủ, trích đoạn nguyên vẹn không bị cắt ngắn (full snippet), đường dẫn tệp (source_path), mã trích dẫn, phần trăm độ tin cậy và nút thao tác.

**Why this priority**: Giải quyết triệt để vấn đề "đồ thị xấu quắc, chữ bị cắt giữa chừng, chẳng hiểu gì". Biến đồ thị từ dạng card cồng kềnh thành công cụ điều tra phân tích bằng chứng chuyên nghiệp.

**Independent Test**: Kiểm tra với một trace có 24 node và 23 cạnh. Trên canvas, toàn bộ 24 node đều hiển thị gọn gàng, không bị tràn màn hình; khi click vào node `[1]`, thanh inspector bên phải mở ra trọn vẹn văn bản của trích dẫn 1.

**Acceptance Scenarios**:
1. **Given** câu trả lời RAG có nhiều trích dẫn dài, **When** người dùng xem đồ thị bằng chứng, **Then** các node trên canvas hiển thị dưới dạng pill ngắn gọn, không nhồi nhét đoạn văn bản dài vào node.
2. **Given** người dùng click vào node trích dẫn `[k]`, **When** sự kiện chọn diễn ra, **Then** thanh kiểm tra bên phải lập tức hiển thị nội dung nguyên bản không bị cắt xén kèm thông tin tệp nguồn.

---

### User Story 3 - Tương tác Tô Sáng Tuyến Bằng Chứng (Cross-Highlighting) (Priority: P2)
Khi người dùng chọn một trích dẫn `[k]` hoặc một tệp nguồn, toàn bộ tuyến liên kết liên quan (`Câu trả lời -> Trích dẫn [k] -> Tệp nguồn`) sẽ được tô sáng (highlight), các liên kết và node không liên quan sẽ mờ đi để người dùng tập trung theo dõi nguồn gốc bằng chứng.

**Why this priority**: Tăng tính kết nối logic trong việc kiểm chứng thông tin, giúp người dùng trả lời ngay câu hỏi: "Ý này trong câu trả lời được rút ra từ trang/tệp nào?".

**Independent Test**: Click vào `[3]` -> Đường nối giữa `Answer -> [3] -> File nguồn` chuyển sang màu sáng nổi bật, các trích dẫn khác mờ xuống độ trong suốt 0.3.

**Acceptance Scenarios**:
1. **Given** đồ thị đang hiển thị nhiều trích dẫn, **When** người dùng click hoặc hover vào một trích dẫn, **Then** tuyến bằng chứng tương ứng được làm nổi bật rõ rệt.

---

### User Story 4 - Đảm bảo Tính Tương thích & An Toàn Ngoại Tuyến (Priority: P1)
Giữ vững 100% cam kết kiến trúc của dự án AIOS WorkLens:
- Không thay đổi cấu trúc dữ liệu schema `rag-trace/v1` và logic lọc 4 loại node chuẩn Commit C (`question`, `answer`, `citation`, `source`).
- 100% chạy offline tại chỗ (Pure in-process, zero cloud egress, không tải tài nguyên từ CDN ngoài).
- Bảo toàn bộ đệm SHA-256 `VIEWER_CACHE` chống tính toán lại lặp đi lặp lại.
- Bộ font đa ngôn ngữ CJK & tiếng Việt hiển thị hoàn hảo trên mọi hệ điều hành.

**Acceptance Scenarios**:
1. **Given** môi trường ngắt hoàn toàn kết nối Internet, **When** hiển thị đồ thị và Atlas, **Then** toàn bộ thành phần UI render bình thường không có lỗi tài nguyên.

---

## Ràng Buộc & Điều Không Làm (Non-Goals)
- **KHÔNG** tích hợp Neo4j hay kéo mã nguồn nặng Docker của Flowsint vào dự án (chỉ học hỏi và tái hiện trải nghiệm UX/UI đỉnh cao của Flowsint).
- **KHÔNG** làm thay đổi schema `rag-trace/v1`.
- **KHÔNG** hiển thị mặc định toàn bộ knowledge graph khổng lồ gây quá tải; giữ mặc định là đồ thị bằng chứng của phiên câu trả lời hiện tại (`subgraph of 1 answer`).
