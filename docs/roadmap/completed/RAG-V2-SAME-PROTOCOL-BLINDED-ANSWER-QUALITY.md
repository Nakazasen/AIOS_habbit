# Chất Lượng Câu Trả Lời Ẩn Danh Cùng Giao Thức Cho RAG v2 (RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY)

Status: `DOCUMENTED_RESULT_PENDING_CURRENT_VALIDATION — 2026-08-16`

Kết quả Giai đoạn A / Giai đoạn B và báo cáo 12 câu hỏi đã có mặt trong cây làm việc, nhưng thẻ này chưa phải là một tuyên bố phát hành hiện tại cho đến khi diff phạm vi cuối cùng vượt qua cổng chất lượng đầy đủ bắt buộc và được đánh giá / commit. Khám phá kiểm thử hiện tại tìm thấy 1,143 bài kiểm thử; việc thu thập chưa phải là một lượt chạy toàn bộ bộ kiểm thử thành công.

## Mục Tiêu (Goal)

Đánh giá ứng viên sản xuất `bge_m3_hybrid` đã kích hoạt so với tham chiếu NotebookLM bất biến theo cùng giao thức 12 câu hỏi đóng băng, không tinh chỉnh sau khi mở mù hoặc làm suy yếu các kiểm soát quyền riêng tư.

## Điều Kiện Tiên Quyết (Preconditions)

- [RAG-V2-HYBRID-PRODUCTION-ACTIVATION](../completed/RAG-V2-HYBRID-PRODUCTION-ACTIVATION.md): `DONE`.
- [RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY](../completed/RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY.md): `DONE`, kiểm toán ngữ liệu nghiêm ngặt `70/70`.
- Tham chiếu NotebookLM hiện có giữ nguyên trạng thái bất biến và không được thu thập lại trong cổng này.

## Đường Cơ Sở Đóng Băng (Frozen Baseline)

- Điểm số NotebookLM cùng giao thức trước đó: `3.807/5`.
- Điểm số RAG v2 trước đó: `2.898/5`.
- Bộ câu hỏi: chuẩn tắc `BQ01`–`BQ12`; mã băm của nó phải khớp với tham chiếu bất biến.
- Cấu hình truy xuất sản xuất: `bge_m3_hybrid` với định danh triển khai / mô hình đã được phê duyệt.

## Khắc Phục Tính Toàn Vẹn Đo Lường — 2026-07-29

- Chẩn đoán `BQ01/BQ02` ban đầu được giữ lại như bằng chứng nhánh kế thừa lịch sử, nhưng không thể hỗ trợ kết luận chất lượng cho bộ truy xuất sản xuất Workspace Chat đã kích hoạt: nhánh `workspace_chat` đã khai báo của nó đã gọi trực tiếp truy xuất từ vựng cũ.
- Trình chạy khắc phục hiện gọi cùng một adapter Workspace Chat RAG v2 được sử dụng bởi UI, chuẩn bị các nguồn một lần trước vòng lặp câu hỏi và ghi lại backend adapter, cấu hình yêu cầu / hiệu lực và trạng thái dự phòng cho mỗi hàng câu trả lời Workspace.
- Một hàng bị coi là không hợp lệ về mặt kỹ thuật và việc tổng hợp provider bị chặn trừ khi nó chứng minh được `rag_v2_subprocess`, yêu cầu / hiệu lực `bge_m3_hybrid` và không có dự phòng. Một đánh dấu giao thức adapter riêng biệt cũng ngăn các checkpoint cũ được tái sử dụng.
- Chỉ có một chẩn đoán khắc phục `BQ01/BQ02` riêng biệt mới có thể chạy trước khi đánh giá 12 câu hỏi mới được ủy quyền. Tham chiếu NotebookLM bất biến, bộ câu hỏi, định danh ngữ liệu, các artifact trước đó và quy tắc không tinh chỉnh vẫn giữ nguyên không đổi.

## Danh Sách Cho Phép (Allowlist)

- `ROADMAP.md`
- `docs/roadmap/RAG-V2-INTENT-RETRIEVAL-SYNTHESIS-TUNING.md`
- `docs/roadmap/active/RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY.md`
- `docs/rag_v2/SAME_PROTOCOL_ANSWER_QUALITY_PROTOCOL.md`
- `scripts/battle_notebooklm_rag_v2.py`
- `src/aios_habit/workspace_chat_rag_v2_deployment.py`
- Các bài kiểm thử tập trung cho các tệp trên

Bằng chứng runtime thuộc về thư mục `local_runs/` bị gitignore; câu trả lời thô, văn bản bằng chứng và credential tuyệt đối không được commit.

## Ràng Buộc Bảo Mật (Privacy Constraints)

- Các nguồn `local_only` không thể sử dụng tuyến provider trực tiếp hoặc tuyến NotebookLM.
- Tổng hợp trực tiếp yêu cầu phân loại `cloud_safe` hoặc `public` rõ ràng cộng với định danh tham chiếu bất biến.
- Ngữ liệu 70 nguồn hiện tại vẫn là `local_only`; không có việc gắn nhãn lại nào được ngụ ý bởi cổng này.
- Giai đoạn A hoàn toàn không sử dụng provider. Nếu không có tuyến trực tiếp nào được phê duyệt riêng biệt, kết luận là `BLOCKED_PRIVACY_ROUTE`.

## Kỷ Luật Đánh Giá (Evaluation Discipline)

1. Đóng băng định danh ứng viên, mô hình, kiểm toán ngữ liệu, bộ câu hỏi và tham chiếu trước khi sinh câu trả lời.
2. Chỉ một lượt chạy chính duy nhất; chỉ thử lại các lỗi vận chuyển / provider đã khai báo trước mà không làm thay đổi định danh thử nghiệm.
3. Không tinh chỉnh truy xuất, prompt hoặc tổng hợp sau khi xem điểm số mù trong cổng này.
4. Chấm điểm độc lập không nhận bản đồ gán hệ thống.
5. Lỗi provider là lỗi kỹ thuật, không phải là hàng chất lượng.
6. Các cổng bảo mật cứng, trích dẫn và từ chối trả lời không thể bị bù trừ bởi điểm số trung bình cao.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

Tất cả các cổng cứng phải đạt:

- Không có hồi quy bảo mật / gateway;
- Đúng định danh sản xuất đã kích hoạt;
- Kiểm toán ngữ liệu nghiêm ngặt và mã băm ngữ liệu bất biến;
- Định danh câu hỏi / tham chiếu / notebook bất biến;
- Không có trích dẫn bịa đặt;
- Từ chối trả lời chính xác đối với các câu hỏi thiếu bằng chứng;
- Không gắn cứng ID benchmark, tên tệp hoặc mã đặc thù ngành;
- Công bố tổng hợp loại trừ nội dung thô riêng tư.

Chất lượng chỉ đạt khi tiêu chí 8 chiều đóng băng đạt đường cơ sở đã đăng ký trước hoặc đánh giá quy trình quan trọng theo cặp chứng minh không có sự suy giảm chất lượng đáng kể. Độ hoàn chỉnh, hỗ trợ trích dẫn, tính hành động và tổng hợp xuyên nguồn vẫn hiển thị riêng biệt.

## Kiểm Chứng (Verification)

- Kiểm thử benchmark / đánh giá / triển khai tập trung.
- Toàn bộ pytest, compileall, kiểm tra tài liệu, kiểm toán CLI và import gói.
- Kiểm tra khoảng trắng Git.
- Chạy thử Giai đoạn A không có provider với `local_only`; không xây dựng credential hay kết nối mạng.
- Sự ủy quyền của chủ sở hữu trước bất kỳ lần thực thi trực tiếp Giai đoạn B nào.

## Hoàn Tác (Rollback)

Gỡ bỏ các hàm trợ giúp định danh chỉ dành cho đánh giá và khôi phục hợp đồng manifest benchmark trước đó. Không thay đổi triển khai Workspace Chat đã kích hoạt, artifact mô hình, ngữ liệu nguồn hoặc tham chiếu bất biến.

## Các Kết Luận Đóng Cổng (Closure Verdicts)

- `QUALITY_GATE_PASSED`
- `QUALITY_IMPROVED_NOT_PARITY`
- `QUALITY_GATE_FAILED`
- `BLOCKED_PRIVACY_ROUTE`
- `INSUFFICIENT_EVIDENCE`

Một đánh giá thất bại hoặc bị chặn có thể tạo ra một cổng tinh chỉnh được lên kế hoạch riêng biệt; tuyệt đối không tinh chỉnh đánh giá đang hoạt động này ngay tại chỗ. A18 và P1.0 vẫn giữ trạng thái đóng.

