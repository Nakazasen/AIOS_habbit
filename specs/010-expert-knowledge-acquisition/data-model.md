# Mô hình dữ liệu: Vòng phỏng vấn và xuất bản tri thức

## 1. Nguyên tắc

- Dữ liệu phỏng vấn thô, dữ liệu điều phối và tri thức xuất bản là ba lớp riêng.
- Chỉ sự kiện có ý nghĩa phục hồi hoặc trách nhiệm mới cần ghi nối; không biến mọi thao tác giao diện thành sổ kiểm toán.
- Tên người dùng là thông tin ghi nhận, không cấp quyền và không được gọi là danh tính xác minh.
- Nội dung AI tạo mặc định là bản nháp.
- Audio và bản chép lời chỉ được lưu trong vùng `local_only`; DB điều phối chỉ giữ chỉ dẫn cục bộ đã làm sạch và mã kiểm tra.
- Mã nội bộ được lưu để chống ghi nhầm phiên bản nhưng không hiển thị ở luồng người dùng thường.

## 2. Quan hệ

```text
LibrarySelection 1─* InterviewSession 1─* InterviewTurn
InterviewSession 1─* TranscriptSegment
InterviewTurn/TranscriptSegment *─* KnowledgeArtifactCandidate
KnowledgeArtifactCandidate 1─* DecisionRecord
KnowledgeArtifactCandidate 1─* PublicationReceipt
RecordedPerson 1─* DecisionRecord
```

`KnowledgeGapCandidate` và các phát biểu tri thức nhỏ có thể được dùng nội bộ để gợi ý và truy nguồn, nhưng không phải cửa chặn hoặc khái niệm bắt người dùng quản lý.

## 3. Thực thể và trường tối thiểu

### 3.1 LibrarySelection

| Trường | Ý nghĩa |
| --- | --- |
| `library_id` | Mã ổn định nội bộ |
| `kind` | `personal` hoặc `shared` |
| `display_name` | Tên dễ hiểu trên giao diện |
| `location_ref` | Tham chiếu vị trí đã làm sạch; không hiện đường dẫn tuyệt đối trong thông báo thường |
| `selected_at` | Thời điểm bắt đầu dùng lựa chọn này |

### 3.2 RecordedPerson

| Trường | Ý nghĩa |
| --- | --- |
| `recorded_name` | Tên người dùng xác nhận để ghi vào lịch sử |
| `os_name_suggestion` | Tên OS chỉ dùng điền sẵn |
| `machine_ref` | Mã máy đã làm sạch để hỗ trợ truy vết |
| `recorded_at` | Thời điểm ghi |

Không có `assurance_level`, hồ sơ quyền, vai trò hoặc phạm vi cấp phép. Tên có thể sửa và không được xem là xác thực.

### 3.3 KnowledgeGapCandidate

| Trường | Ý nghĩa |
| --- | --- |
| `gap_id` | Mã ổn định nội bộ |
| `question`, `topic` | Điều nên làm rõ |
| `evidence_refs` | Nguồn/câu hỏi cho thấy nội dung còn thiếu |
| `reason`, `priority` | Lý do và mức gợi ý |
| `status` | `suggested`, `used`, `dismissed`, `resolved` |

Người dùng có thể bắt đầu phỏng vấn mà không có bản ghi này.

### 3.4 InterviewSession

| Trường | Ý nghĩa |
| --- | --- |
| `session_id` | Mã để tiếp tục phiên |
| `library_id`, `topic`, `gap_id` | Đích và chủ đề; `gap_id` tùy chọn |
| `state` | `active`, `paused`, `completed`, `stopped`, `blocked` |
| `consent_state` | `not_requested`, `declined`, `granted`, `withdrawn` |
| `checkpoint_seq`, `last_turn_digest` | Tiếp tục và chống gửi lặp |
| `started_at`, `updated_at`, `ended_at` | Thời gian |
| `stop_reason` | Lý do kết thúc |

Giới hạn lượt/thời gian là cấu hình an toàn nội bộ, không phải trường người dùng phải quyết định.

### 3.5 InterviewTurn

| Trường | Ý nghĩa |
| --- | --- |
| `turn_id`, `sequence` | Thứ tự ổn định |
| `question_text`, `answer_locator` | Câu hỏi và tham chiếu câu trả lời cục bộ |
| `answer_state` | `answered`, `unknown`, `uncertain`, `skipped`, `corrected` |
| `source_refs` | Chủ đề/lượt trước/nguồn làm căn cứ hỏi tiếp |
| `payload_digest`, `created_at` | Chống gửi lặp và phục hồi |

Không lưu nội dung audio hoặc bản chép lời thô trong `workspace_cases.sqlite`.

### 3.6 TranscriptSegment

| Trường | Ý nghĩa |
| --- | --- |
| `segment_id`, `session_id` | Liên kết phiên |
| `start_ms`, `end_ms` | Mốc thời gian |
| `machine_text`, `corrected_text` | Chỉ tồn tại trong kho `local_only` |
| `critical_tokens` | Mã máy/số/đơn vị cần xác nhận |
| `confirmation_state`, `confirmed_by_name` | Trạng thái người dùng kiểm tra |
| `audio_locator`, `audio_digest` | Chỉ trỏ cục bộ |
| `engine_receipt` | Chi tiết hỗ trợ kỹ thuật, không hiện mặc định |

### 3.7 KnowledgeArtifactCandidate

| Trường | Ý nghĩa |
| --- | --- |
| `artifact_id`, `artifact_type`, `version` | Bản nháp SOP hoặc bài học |
| `title`, `content_locator`, `content_digest` | Nội dung theo phiên bản |
| `source_refs` | Nguồn dùng để tạo nội dung |
| `uncertainty_notes`, `conflict_notes` | Điểm cần người dùng xem lại |
| `status` | `draft`, `confirmed`, `rejected`, `published`, `revoked`, `superseded` |

### 3.8 DecisionRecord

| Trường | Ý nghĩa |
| --- | --- |
| `decision_id` | Mã ghi nối |
| `subject_id`, `subject_digest`, `subject_version` | Đúng nội dung được quyết định |
| `decision` | `confirm`, `reject`, `request_change`, `revoke` |
| `recorded_name`, `machine_ref` | Thông tin người nhận trách nhiệm; không phải xác thực |
| `confidence` | `low`, `medium`, `high` |
| `rationale` | Lý do hoặc căn cứ |
| `checked_source_refs` | Nguồn người dùng cho biết đã kiểm tra |
| `responsibility_acknowledged` | Xác nhận chịu trách nhiệm |
| `created_at` | Thời điểm hệ thống tự ghi |

### 3.9 PublicationReceipt

| Trường | Ý nghĩa |
| --- | --- |
| `publication_id`, `artifact_id`, `artifact_digest` | Liên kết đúng bản nội dung |
| `library_id`, `source_digest` | Đích và nguồn được nạp |
| `decision_id` | Quyết định làm căn cứ |
| `status` | `preparing`, `published`, `failed`, `revoked`, `superseded` |
| `backup_ref`, `index_digest_before`, `index_digest_after` | Phục hồi và đối chiếu |
| `integrity_result`, `retrieval_result`, `rollback_result` | Bằng chứng kỹ thuật |
| `created_at` | Thời điểm |

## 4. Chuyển trạng thái chính

```text
Phiên: active -> paused -> active -> completed
              \-> stopped/blocked

Bản nháp: draft -> confirmed -> published -> superseded/revoked
             \-> rejected/request_change
```

Quyết định chỉ áp dụng khi mã kiểm tra và phiên bản còn khớp. Nếu nội dung thay đổi, người dùng phải xác nhận bản mới. Ghi thư viện dùng khóa ngắn hạn; khóa không mang thông tin quyền.

## 5. Lưu giữ và xóa

Audio và bản chép lời thô chỉ ở vùng `local_only`. Người dùng có thể xóa dữ liệu phỏng vấn cục bộ; xóa dữ liệu thô không được âm thầm xóa tri thức đã xuất bản hoặc lịch sử quyết định. Thu hồi tri thức khỏi kết quả hỏi đáp tạo sự kiện mới và giữ dấu vết cũ. Chính sách tự xóa theo ngày chỉ được bổ sung khi có yêu cầu vận hành cụ thể.

## 6. Chuyển đổi từ mô hình cũ

- Giữ bảng hồ sơ chuyên gia và quyền cũ để đọc dữ liệu lịch sử; Goal 010 không dùng chúng làm điều kiện thao tác mới.
- Chuyển các quyết định cũ sang trạng thái “thông tin trách nhiệm chưa đầy đủ” thay vì tự điền độ tự tin hoặc nguồn đã kiểm tra.
- Không sao chép bản chép lời thô đang nằm sai chỗ sang thư viện. Việc di chuyển/xóa khỏi DB hồ sơ phải có migration, backup và test không mất dữ liệu.
