# Mô hình dữ liệu: Vòng khép kín từ Hồ sơ sự vụ – Thẩm định chuyên gia – Bài học thực tế

Toàn bộ các bảng dữ liệu mới trong đợt phát triển này được lưu trữ cục bộ tại tệp cơ sở dữ liệu riêng:
```text
local_cases/workspace_cases.sqlite
```
Đây là ngăn kéo dữ liệu riêng biệt của từng máy tính làm việc, hoàn toàn tách rời khỏi thư viện tri thức chung (`library.sqlite`), không tự tiện đồng bộ dữ liệu chat riêng tư lên mạng nội bộ. Mọi thao tác ghi nhận dữ liệu đều được thực hiện trọn vẹn (hoặc thành công 100% hoặc hủy bỏ hoàn toàn, không lưu dở dang), và toàn bộ lịch sử chỉnh sửa được ghi nối tiếp để phục vụ kiểm toán sau này.

---

## 1. Bảng `CaseRecord` (Hồ sơ sự vụ)
Lưu các mã định danh và dấu vết kiểm toán cho một ca hỏi đáp hoặc một phiên điều tra lỗi kỹ thuật. Nội dung câu hỏi, câu trả lời và đoạn trích nguồn không thuộc bảng này.

| Tên trường kỹ thuật | Tên gọi dễ hiểu | Ý nghĩa thực tế & Ràng buộc an toàn |
|---|---|---|
| `case_id` | **Mã hồ sơ sự vụ** | Mã định danh duy nhất (ví dụ `CASE-A1B2C3D4`), được sinh tự động và không bao giờ thay đổi. |
| `created_at` | **Thời điểm tạo** | Ngày, giờ, phút, giây tạo hồ sơ theo chuẩn quốc tế UTC. |
| `conversation_id` | **Mã phiên hỏi đáp** | Mã tham chiếu đến phiên có câu hỏi; không lưu nội dung câu hỏi. |
| `assistant_message_id` | **Mã câu trả lời** | Mã tham chiếu đến câu trả lời của hệ thống; không lưu nội dung câu trả lời. |
| `trace_id` | **Mã dấu vết bằng chứng** | Mã tham chiếu đến trace đã có tại thời điểm lưu hồ sơ. |
| `status` | **Trạng thái hồ sơ** | Vòng đời của hồ sơ: `draft` (Nháp) $\rightarrow$ `under_review` (Đang chờ chuyên gia thẩm định) $\rightarrow$ `resolved` (Đã xử lý xong) / `rejected` (Bác bỏ) / `archived` (Lưu trữ). |
| `created_by` | **Người tạo hồ sơ** | Tên hoặc tài khoản của kỹ sư bấm lưu hồ sơ trên màn hình chat. |
| `evidence_digest` | **Mã băm tập bằng chứng** | Chuỗi mã băm đại diện cho toàn bộ các tài liệu và dòng log được trích dẫn làm căn cứ. |

---

## 2. Bảng `EvidenceReference` (Căn cứ trích dẫn tài liệu & Log)
Lưu trữ danh sách các đoạn văn bản trong quy trình SOP hoặc các sự kiện trong log máy được dùng làm bằng chứng đối chiếu.

| Tên trường kỹ thuật | Tên gọi dễ hiểu | Ý nghĩa thực tế & Ràng buộc an toàn |
|---|---|---|
| `evidence_ref_id` | **Mã căn cứ trích dẫn** | Mã định danh duy nhất của từng đoạn bằng chứng. |
| `case_id` | **Thuộc hồ sơ sự vụ** | Mã hồ sơ sự vụ cha mà bằng chứng này gắn liền vào (bắt buộc phải tồn tại). |
| `source_type` | **Loại nguồn dữ liệu** | Phân loại nguồn gốc: `library` (Tài liệu quy chuẩn SOP), `line_log` (Log sự kiện máy), `approved_report` (Báo cáo kỹ thuật đã duyệt). |
| `locator` | **Vị trí trong tài liệu** | Vị trí cụ thể của đoạn trích dẫn (ví dụ: Tên tệp SOP, số trang, số dòng log). Tuyệt đối không lưu các đoạn văn bản chứa bí mật công nghệ chưa phân loại. |
| `content_digest` | **Mã băm nội dung trích dẫn** | Mã băm kiểm chứng rằng đoạn văn bản trích dẫn không bị sửa đổi nội dung. |
| `provenance_status` | **Xuất xứ & Độ tin cậy** | Trạng thái nguồn: `suspected` (Nghi vấn / Cần đối chứng), `approved` (Đã được duyệt chính thức), `unknown` (Chưa rõ). Dữ liệu log máy luôn bắt đầu ở mức `suspected`. |
| `privacy_label` | **Nhãn phân loại bảo mật** | Nhãn an toàn dữ liệu: Dữ liệu gắn nhãn `local_only` (Chỉ dùng nội bộ) tuyệt đối không được gửi lên các dịch vụ AI công cộng. |

---

## 3. Bảng `ExpertReview` (Ý kiến thẩm định của Chuyên gia)
Lưu lại nhận xét, đánh giá và chữ ký phê duyệt của kỹ sư trưởng hoặc chuyên gia phụ trách công đoạn.

| Tên trường kỹ thuật | Tên gọi dễ hiểu | Ý nghĩa thực tế & Ràng buộc an toàn |
|---|---|---|
| `review_id` | **Mã thẩm định** | Mã định danh duy nhất của lượt đánh giá. |
| `case_id` | **Thuộc hồ sơ sự vụ** | Hồ sơ sự vụ đang được chuyên gia đọc và đánh giá. |
| `claim_digest` | **Mã nhận định được đánh giá** | Đoạn kết luận cụ thể mà chuyên gia đang thẩm định tính đúng sai. |
| `decision` | **Quyết định thẩm định** | Kết quả đánh giá: `candidate` (Bản ý kiến dự thảo), `confirmed` (Xác nhận đúng 100%), `rejected` (Bác bỏ kết luận), `needs_more_evidence` (Yêu cầu bổ sung thêm tài liệu/log). AI chỉ được phép tạo ở mức `candidate`. |
| `reviewer_id` | **Mã chuyên gia** | Tên hoặc mã nhân viên của chuyên gia bấm duyệt. |
| `reviewer_role` | **Chức danh / Vai trò** | Vị trí chuyên môn (ví dụ: Kỹ sư trưởng công đoạn, Quản lý chất lượng xưởng). |
| `scope` | **Phạm vi thẩm quyền** | Khu vực hoặc dòng máy chuyên gia chịu trách nhiệm (ví dụ: `LSU_Optical_Alignment`). |
| `confidence` | **Mức độ tin cậy** | Đánh giá mức độ chắc chắn của nhận định (ví dụ: `Cao / Tuyệt đối`). |
| `rationale` | **Lý do & Căn cứ phê duyệt** | Giải thích chi tiết tại sao đồng ý hoặc tại sao từ chối (bắt buộc phải nhập, không được để trống). |
| `reviewed_at` | **Thời điểm phê duyệt** | Ngày giờ chính xác khi chuyên gia bấm nút ký duyệt trên màn hình. |

---

## 4. Bảng `LearningRecord` (Bài học kinh nghiệm đúc kết)
Lưu lại tri thức xử lý lỗi đã được chứng minh hiệu quả, dùng để đào tạo hoặc tra cứu cho các ca làm việc tương lai.

| Tên trường kỹ thuật | Tên gọi dễ hiểu | Ý nghĩa thực tế & Ràng buộc an toàn |
|---|---|---|
| `learning_id` | **Mã bài học kinh nghiệm** | Mã định danh duy nhất của bài học. |
| `source_review_id` | **Căn cứ từ thẩm định nào** | Phải bắt nguồn từ một thẩm định đã được chuyên gia bấm `confirmed` (bắt buộc). |
| `case_id`, `evidence_digest` | **Truy vết nguồn gốc** | Liên kết chặt chẽ về đúng hồ sơ sự vụ gốc và tài liệu chứng minh. |
| `promotion_status` | **Trạng thái bài học** | `candidate` (Đề xuất bài học) $\rightarrow$ `promoted` (Đã được Quản lý phê duyệt thành bài học chính thức) $\rightarrow$ `withdrawn` (Thu hồi bài học nếu quy trình nhà máy thay đổi). |
| `promoted_by`, `promoted_at` | **Người duyệt & Thời điểm** | Tên Quản lý chất lượng phê duyệt đưa vào sổ tay và thời gian duyệt. |
| `learning_text` | **Tóm tắt bài học kinh nghiệm** | Văn bản hướng dẫn xử lý ngắn gọn, dễ hiểu, đã làm sạch thông tin nhạy cảm. Bài học này dùng cho con người đọc, không dùng để tự động huấn luyện lại mô hình AI. |

---

## 5. Bảng `LsuReadinessManifest` (Bảng kiểm tra độ sẵn sàng cho Dự đoán lỗi LSU)
Bảng kiểm tra 6 tiêu chí bắt buộc trước khi cho phép chạy thử nghiệm dự đoán lỗi cho cụm máy LSU.

| Tên trường kỹ thuật | Tên gọi dễ hiểu | Ý nghĩa thực tế & Ràng buộc an toàn |
|---|---|---|
| `manifest_id` | **Mã bảng kiểm tra** | Mã định danh duy nhất của đợt đánh giá độ sẵn sàng. |
| `dataset_digest` | **Mã băm dữ liệu đo đạc** | Kiểm tra dữ liệu lịch sử máy quét laser đã được nạp đủ và toàn vẹn chưa. |
| `label_definition` | **Quy chuẩn nhãn lỗi** | Định nghĩa rõ ràng thế nào là lỗi quang học, thế nào là lệch góc Bow/Skew. |
| `data_owner`, `quality_owner` | **Người chịu trách nhiệm** | Tên Kỹ sư phụ trách dữ liệu và Quản lý phụ trách chất lượng ký tên chịu trách nhiệm. |
| `replay_protocol` | **Quy trình thử nghiệm lại** | Kịch bản kiểm tra lại mô hình trên dữ liệu quá khứ để đo độ chính xác. |
| `shadow_reviewer` | **Người giám sát thử nghiệm bóng** | Kỹ sư được phân công theo dõi mô hình chạy ngầm song song với dây chuyền. |
| `status` | **Kết luận độ sẵn sàng** | `blocked` (Bị chặn do còn thiếu điều kiện) $\rightarrow$ `ready_for_shadow` (Đủ điều kiện chạy thử nghiệm bóng song song) $\rightarrow$ `shadow_reviewed` (Đã hoàn tất đánh giá thử nghiệm bóng). **Tuyệt đối không có trạng thái tự động đưa vào sản xuất (`production`)**. |
| `missing_requirements` | **Danh sách các mục còn thiếu** | Ghi rõ cụ thể đang thiếu dữ liệu gì, thiếu chữ ký của ai (nếu bị `blocked`). |

---

## 6. Bảng `ActionProposal` (Dự thảo Quy trình / Báo cáo do AI đề xuất)
Quản lý các văn bản dự thảo báo cáo hoặc quy trình xử lý lỗi do trợ lý AI soạn thảo từ bằng chứng đã được duyệt.

| Tên trường kỹ thuật | Tên gọi dễ hiểu | Ý nghĩa thực tế & Ràng buộc an toàn |
|---|---|---|
| `proposal_id` | **Mã dự thảo đề xuất** | Mã định danh duy nhất của bản dự thảo. |
| `case_id`, `evidence_digest` | **Căn cứ nguồn gốc** | Dự thảo bắt buộc phải sinh ra từ một hồ sơ sự vụ có thật và có bằng chứng đối chứng. |
| `kind` | **Loại dự thảo** | `sop_draft` (Dự thảo Quy trình thao tác chuẩn), `report_draft` (Dự thảo Báo cáo điều tra kỹ thuật), `export_instruction` (Chỉ dẫn xuất văn bản). Tuyệt đối không có lệnh điều khiển máy hay lệnh xóa tệp. |
| `status` | **Trạng thái phê duyệt** | `proposed` (Mới đề xuất) $\rightarrow$ `reviewed` (Đã xem xét) $\rightarrow$ `approved` (Đã được con người bấm duyệt) / `rejected` (Từ chối) / `expired` (Hết hạn). |
| `approver_id`, `approver_role` | **Người duyệt văn bản** | Tên và chức danh của kỹ sư bấm nút duyệt trên màn hình tiếng Việt. |
| `approved_at`, `notes` | **Thời điểm & Ghi chú** | Ngày giờ bấm duyệt và nhận xét của người duyệt. |
| `output_locator` | **Vị trí tệp xuất ra** | Đường dẫn tệp mới được lưu trên đĩa (chỉ tạo tệp mới, không bao giờ ghi đè tệp cũ). |

---

## 7. Mối quan hệ và Nguyên tắc chuyển đổi trạng thái

```text
    [ Hồ sơ sự vụ (CaseRecord) ] ── (Có chứa) ──> [ Căn cứ trích dẫn (EvidenceReference) ]
                 │
                 ├── (Được thẩm định bởi) ──> [ Ý kiến chuyên gia (ExpertReview) ]
                 │                                            │
                 │                                    (Nếu được "Xác nhận đúng")
                 │                                            ↓
                 │                                [ Bài học kinh nghiệm (LearningRecord) ]
                 │
                 └── (Trợ lý AI soạn nháp) ──> [ Dự thảo Đề xuất (ActionProposal) ]
                                                              │
                                                      (Người dùng bấm duyệt)
                                                              ↓
                                                  [ Xuất tệp văn bản mới an toàn ]
```

* **Nguyên tắc bảo vệ kép**: Bất kỳ hành động nâng cấp thành bài học (`promotion`) hay xuất tệp chính thức (`approval`) đều phải kiểm tra lại mã băm của tài liệu gốc trong cùng một lần ghi dữ liệu.
* **Tôn trọng ý kiến đa chiều**: Nếu 2 chuyên gia có ý kiến trái chiều về cùng một nhận định, hệ thống lưu giữ nguyên văn cả 2 ý kiến, không tự ý chọn bên nào đúng cho đến khi Quản lý phân xử.
