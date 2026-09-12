# Đặc tả: Tăng tỉ lệ tìm đúng trên nguồn đã sẵn, không hardcode

**Nhánh tính năng**: `012-ready-hybrid-recall`

**Created**: 2026-09-12

**Status**: Implemented — test tập trung 144 passed; chưa tuyên bố ngang NotebookLM

**Input**: Người dùng xác nhận chênh lệch đáp án với NotebookLM là thật (kiến thức nghiệp vụ). Cần nâng tỉ lệ đúng mà **không** gắn cứng ID câu hỏi, tên file, hay từ khóa ngữ liệu (WMS/MOM/ORICON/RevUp…).

## User Scenarios & Testing

### User Story 1 - Câu Latin không bị cắt 3 nguồn khi kho đa số CJK (Priority: P1)

Người hỏi bằng tiếng Việt/Anh. Kho tài liệu đã sẵn (ready) phần lớn là tiếng Nhật/Trung. Hệ thống **không** chọn 3 file theo từ khóa Latin trùng tiêu đề, rồi bỏ tài liệu đúng viết bằng chữ CJK.

**Why this priority**: So sánh 10 câu cho thấy Gemini viết đúng khi có bằng chứng; sai chủ yếu vì **không tìm ra tài liệu**. Cắt 3 nguồn theo từ vựng Latin là nguyên nhân generic.

**Independent Test**: Sáu nguồn ready; câu Latin; bốn nguồn CJK không trùng token Latin; hai nguồn Latin trùng từ khóa. Truy xuất phải giữ nguồn CJK, không chỉ 2 nguồn Latin.

**Acceptance Scenarios**:

1. **Given** đa số nguồn ready là chữ CJK và câu hỏi là Latin, **When** truy xuất trên nguồn đã ready, **Then** không cắt còn 3 theo lexical title.
2. **Given** câu hẹp đặt tên hệ thống trên kho nhỏ không có đa số CJK, **When** truy xuất, **Then** vẫn được phép hẹp (hành vi Matecon/manual hiện có).
3. **Given** chuẩn bị nguồn chưa ready, **When** chọn phạm vi nhúng, **Then** vẫn giới hạn 3 — không nhúng cả sổ vì một câu.

---

### User Story 2 - Ưu tiên kênh ngữ nghĩa khi lệch hệ chữ (Priority: P2)

Khi câu hỏi và đa số tên/nguồn trong index khác hệ chữ (Latin vs CJK), kênh từ vựng không được át kênh dense/sparse.

**Why this priority**: Hybrid RRF trọng lexical = 1 làm đoạn CJK trượt dù embedding đa ngữ đã gần.

**Independent Test**: Cùng một truy vấn Latin, cấu hình xếp hạng khi lệch chữ phải có trọng số lexical thấp hơn dense.

**Acceptance Scenarios**:

1. **Given** câu Latin và đa số `source_name` CJK, **When** hybrid fuse, **Then** trọng số dense > lexical.
2. **Given** câu và kho cùng hệ chữ, **When** hybrid fuse, **Then** trọng số mặc định không đổi.

---

### User Story 3 - Kết quả mỏng thì tìm lại, không bịa (Priority: P3)

Nếu sau lần tìm đầu chỉ còn ≤1 tài liệu trong khi index còn nhiều tài liệu được phép, hệ thống tìm lại với cửa sổ rộng hơn và ưu tiên dense. Không bịa đoạn.

**Why this priority**: Câu quy trình từng chỉ ra 1 đoạn lạc đề; Gemini chịu đúng — cần thêm cơ hội tìm, không hardcode tên quy trình.

**Independent Test**: Index nhiều tài liệu; lần 1 trả 1 doc; lần 2 phải gọi lại với hạn mức cao hơn hoặc đánh dấu đã mở rộng.

**Acceptance Scenarios**:

1. **Given** kết quả ≤1 document_id và index còn ≥5 tài liệu được phép, **When** hoàn tất hybrid, **Then** có lần tìm bổ sung.
2. **Given** lần 2 vẫn thiếu, **When** tổng hợp, **Then** vẫn được chịu / ghi thiếu bằng chứng — không bịa.

---

### Edge Cases

- Kho hỗn hợp không có đa số hệ chữ: giữ cắt 3 như cũ.
- Câu nhiều vế (Goal 002): vẫn tìm mọi nguồn ready.
- Không gửi chữ tài liệu `local_only` lên cloud chỉ để dịch câu hỏi.

## Requirements

### Functional Requirements

- **FR-001**: Truy xuất trên nguồn **đã ready** MUST không cắt lexical còn 3 khi câu hỏi và đa số nguồn khác hệ chữ (Latin vs CJK).
- **FR-002**: Chuẩn bị nguồn chưa ready MUST giữ giới hạn 3.
- **FR-003**: Hybrid ranking MUST giảm trọng số lexical khi lệch hệ chữ; không được đặt trọng số kênh ≤ 0.
- **FR-004**: Kết quả mỏng (≤1 tài liệu, index còn nhiều) MUST mở cửa sổ tìm lại một lần.
- **FR-005**: Cấm gắn ID BQ, tên file ngữ liệu, hay từ khóa nghiệp vụ vào planner/ranking.
- **FR-006**: Câu hẹp trên kho nhỏ cùng hệ chữ MUST giữ hành vi hẹp hiện có.

### Key Entities

- **Script family**: `latin` | `cjk` | `mixed` — đếm ký tự, không suy chủ đề.
- **Ready retrieval window**: tập nguồn đã nhúng được phép đưa vào hybrid.
- **Hybrid ranking config**: trọng số lexical/dense/sparse > 0.

## Success Criteria

- **SC-001**: Fixture lệch chữ: truy xuất giữ ≥1 nguồn CJK không trùng token Latin của câu hỏi.
- **SC-002**: Câu hẹp kho nhỏ (2 nguồn, không đa số CJK) vẫn chọn đúng nguồn trùng từ khóa như hiện tại.
- **SC-003**: Không có chuỗi BQ01–BQ10 / tên file nhà máy trong mã ranking/planner mới.
- **SC-004**: Test tập trung của lát này đạt; không tuyên bố ngang NotebookLM.

## Assumptions

- BGE-M3 Hybrid đã là nền; không đổi model, không rebuild index.
- Người dùng đã cho phép triển khai sau khi lập phương án (“rồi code đi”).
- Gemini chỉ chau chuốt; không thay thế việc tìm.
