# Hợp đồng rà soát thiết kế công đoạn phiên bản 1

`aios_process_design_review_v1` là đầu ra US2. Hệ thống **tự so, tự lưu bản nháp, hiện «Đã xong»**. Không sửa SOP/JIG/tiêu chuẩn/giới hạn sản xuất chính thức. Không có bước người dùng duyệt từng nhận xét.

## 1. Hai vai trò nguồn

Người dùng chọn tài liệu. Hệ thống gán vai trò:

| Vai trò | Nghĩa | Cách gán |
|---|---|---|
| `guideline` | Luật / Guideline thiết kế công đoạn / tiêu chuẩn / quy chuẩn | Người dùng gắn nhãn; nếu không gắn: tiêu đề hoặc loại tài liệu chứa `guideline`, `tiêu chuẩn`, `quy chuẩn`, `standard`, `quy định` (không phân biệt hoa thường, không hardcode tên nhà máy) |
| `design` | Bản thiết kế / SOP nháp / hướng dẫn công đoạn đang xét | Phần còn lại trong nguồn đã chọn |
| `context` | MOM, báo cáo lỗi, số liệu, bản vẽ bổ sung | Không dùng làm luật; chỉ dẫn chứng |

Nếu không tách được luật và thiết kế: mọi nguồn là `context`, mỗi kiểm tra mang `evidence_status=insufficient`, và thẻ kết quả nói rõ «Chưa tách được tài liệu luật và bản thiết kế — hãy chọn thêm Guideline». Vẫn lưu bản nháp, không chặn im lặng.

## 2. Payload

| Trường | Bắt buộc | Quy tắc |
|---|---|---|
| `schema_version` | có | `aios_process_design_review_v1` |
| `artifact_id` | có | |
| `work_id` | có | |
| `title_vi` | có | |
| `status` | có | `verified_draft` khi verifier đạt |
| `guideline_refs` | có | nguồn vai trò `guideline` |
| `design_refs` | có | nguồn vai trò `design` |
| `context_refs` | có | nguồn còn lại |
| `as_is_vi` | có | hiện trạng theo tài liệu, có nguồn |
| `checks` | có | mảng mục 3 |
| `impacts_vi` | có | |
| `proposals` | có | mảng đề xuất, `evidence_status=proposal` |
| `expert_questions_vi` | có | câu cần người am hiểu công đoạn xác nhận; không chặn «Đã xong» |
| `diagrams` | không | Mermaid hiện tại / đề xuất; locator bản nháp |
| `created_at` | có | |
| `artifact_digest` | có | |

## 3. Một mục `checks`

| Trường | Quy tắc |
|---|---|
| `check_id` | ổn định trong artifact |
| `guideline_locator` | chỗ luật; null nếu không có guideline |
| `design_locator` | chỗ bản thiết kế; null nếu không có |
| `verdict` | `pass` / `violate` / `insufficient` |
| `statement_vi` | một câu đời thường |
| `source_refs` | bắt buộc với `pass` và `violate` |
| `evidence_status` | `supported` / `conflicting` / `insufficient` / `proposal` |

- `pass`: thiết kế khớp luật, có hai locator.
- `violate`: thiết kế lệch luật, giữ cả hai nguồn, không tự «sửa giúp» file gốc.
- `insufficient`: thiếu trang, scan kém, không tìm thấy điều luật tương ứng.
- `conflicting`: hai guideline hoặc hai bản thiết kế trái nhau; không tự chọn bên đúng.

## 4. Việc không làm

- Không ghi đè SOP/JIG/tiêu chuẩn trong thư viện chính thức.
- Không đổi thông số vận hành thật.
- Không biến bản nháp thành tài liệu đã phê duyệt.
- Không dự đoán lỗi line.
- Không bắt người dùng tick từng `check` trước khi hiện «Đã xong».

## 5. Fixture nghiệm thu

Bộ giả lập có: một Guideline, một bản thiết kế lệch giới hạn, một bước thiếu điểm kiểm tra, một chỗ không đủ bằng chứng, một tài liệu phiên bản cũ. Kỳ vọng: đủ `violate` / `insufficient` / mâu thuẫn phiên bản, mỗi mục có nguồn hoặc nhãn rõ, artifact vẫn `verified_draft`.
