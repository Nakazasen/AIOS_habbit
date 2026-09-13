# Hợp đồng báo cáo lỗi kỹ thuật xưởng phiên bản 1

`aios_factory_error_report_v1` là đầu ra US1 **cho người viết mã**. Người dùng không thấy tên schema. Họ chọn log, Excel, ảnh hiện trạng hoặc mô tả, nói việc; hệ thống **tự tạo file báo cáo, tự lưu, hiện «Đã xong»**. Không duyệt. «Hoàn tác» luôn có. Đó là file dùng được.

Không dùng schema [agent-error-report-v1.md](agent-error-report-v1.md) (đó là khi Agent gãy).

## 1. Khi nào chạy

- Người dùng chọn ít nhất một nguồn (hồ sơ, file nạp, log, bảng) và chọn việc «Tạo báo cáo lỗi» hoặc nói tương đương.
- Không có watcher line 24/7. Không tự lấy SCADA nếu chưa có file trong nguồn đã chọn.
- Không dự đoán lỗi tương lai. Chỉ mô tả và tổng hợp những gì nguồn đang có.

## 2. Payload

| Trường | Bắt buộc | Quy tắc |
|---|---|---|
| `schema_version` | có | `aios_factory_error_report_v1` |
| `artifact_id` | có | không chứa path tuyệt đối |
| `work_id` | có | khớp `AgentWorkItem` |
| `title_vi` | có | tiếng Việt đời thường |
| `status` | có | sau verifier thành công: `completed` (hiện «Đã xong») |
| `phenomenon_vi` | có | hiện tượng quan sát được từ nguồn |
| `impact_vi` | có | phạm vi ảnh hưởng; thiếu thì ghi chưa đủ bằng chứng |
| `evidence` | có | mảng `source_refs` + vị trí đọc lại được |
| `analysis_vi` | có | chỉ dựa evidence |
| `hypotheses` | có | mảng; mỗi phần tử `statement_vi` + `evidence_status=proposal` |
| `uncertainties_vi` | có | phần chưa chắc; không được để trống nếu thiếu số |
| `next_actions_vi` | có | 1–5 việc kỹ sư có thể làm tiếp |
| `visuals` | có | mảng `VisualArtifact`; rỗng khi không đủ số |
| `created_at` | có | ISO 8601 UTC |
| `artifact_digest` | có | SHA-256, không gồm chính field này |

## 3. Biểu đồ và bảng

- Chỉ tạo biểu đồ khi có trục, đơn vị, phạm vi thời gian/lô và `data_digest` từ file nguồn.
- Mỗi visual bắt buộc: `source_refs`, `source_columns`, `units`, `filters`, `aggregation`, `data_digest`.
- Thiếu số liệu: không vẽ; dùng bảng hoặc `uncertainties_vi`. Cấm biểu đồ trang trí.
- Dùng lại `document_extractors`, metadata chart Excel, Mermaid/visual map hiện có. Không thêm thư viện biểu đồ mới.

## 4. Hành vi không cần người duyệt

- Verifier đạt → lưu file báo cáo → hiện thẻ «Đã xong» + «Mở kết quả» + «Hoàn tác».
- Không nút «Duyệt», «Phê duyệt», «Xác nhận từng mục».
- «Cần bạn bổ sung» chỉ khi **chưa có nguồn** hoặc file không đọc được; không dùng để xin quyền.
- Không gửi `local_only` ra Gemini Web / Router. C-AGENT chỉ khi người dùng đã chọn đúng cầu nối đó.

## 5. Fixture nghiệm thu

- Đủ log + bảng số: có báo cáo Markdown/cấu trúc, ít nhất một visual có provenance, mọi số truy ngược được.
- Thiếu số: vẫn có báo cáo; `visuals` rỗng hoặc chỉ bảng; có cảnh báo tiếng Việt.
- Không dùng dữ liệu nhà máy thật.
