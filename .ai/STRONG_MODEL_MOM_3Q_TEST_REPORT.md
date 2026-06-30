# AIOS Strong Model MOM Test — 3 Câu hỏi khó

Thử nghiệm đánh giá khả năng của Strong Model Answer Bridge (chạy qua chế độ Mode B: evidence-pack manual override) trên tập tài liệu MOM/WMS thực tế.

## Thông tin môi trường
- **Repo:** [LOCAL_WORKSPACE]\AIOS_habbit
- **Branch:** main
- **HEAD pushed:** f4da74a
- **Dữ liệu thực tế:** [LOCAL_SOURCE_ROOT]
- **Chế độ chạy:** Mode B (Owner-approved manual strong model test on selected evidence pack)

## Q1: Thay đổi thiết kế / Running Change
**Câu hỏi:** Trong tài liệu MOM/AMS, khi có thay đổi thiết kế hoặc Running Change, hệ thống Opcenter/MOM quyết định tự động đổi sang linh kiện/thiết kế mới trong điều kiện nào, và trường hợp nào bắt buộc phải xử lý thủ công?

**Evidence files used:** 
- Sơ đồ ERD Kho Vận (HTML)
- Các file Excel kịch bản và Layout (★シナリオ一覧, Phát linh kiện, v.v.)

**Evidence status:**
- Content evidence count: 4
- Metadata-only count: 2
- Evidence quality: mixed
- Privacy gate: provider_call_allowed = False
- Block reason: local_only_evidence

**AIOS Local Evidence Draft:**
(Chỉ cung cấp bản nháp liệt kê raw chunks / text boxes, không thể kết nối logic)

**AIOS Strong Model Answer:**
**Chưa đủ bằng chứng.**
Các tài liệu hiện tại (kịch bản kiểm thử 7 và 8 trong `★シナリオ一覧`) có nhắc đến việc thay đổi thiết kế (期日指定) và Running Change. Tuy nhiên, nội dung chỉ ghi chú là "Cần xác nhận cùng với BOP, và phương án vận hành sẽ do phía Nhật Bản đề xuất" [5]. Không có bằng chứng cụ thể nào trong các tài liệu trích xuất mô tả chi tiết logic tự động chuyển đổi của hệ thống Opcenter/MOM hay các trường hợp bắt buộc xử lý thủ công.

---

## Q2: Luồng liên kết hệ thống MOM/WMS/AGV
**Câu hỏi:** Dựa trên các tài liệu MOM/WMS/AGV, hãy giải thích luồng liên kết từ chỉ thị xuất/nhập kho, WMS, Opcenter/MOM đến AGV/Matecon. Điểm nào nếu sai dữ liệu master hoặc mã Oricon/Tanaban thì có thể làm vận hành bị dừng?

**Evidence files used:** 
- TANABAN_Master.xlsx
- MOMおよびWMSデータ完全クリア方法.xlsx
- AGV通信仕様.xlsx

**Evidence status:**
- Content evidence count: 7
- Metadata-only count: 1
- Evidence quality: mixed
- Privacy gate: provider_call_allowed = False
- Block reason: local_only_evidence

**AIOS Local Evidence Draft:**
(Trích xuất raw queries SQL và các commands giao thức AGV đơn lẻ)

**AIOS Strong Model Answer:**
**Chưa đủ bằng chứng.**
Tài liệu cung cấp (thông số giao tiếp AGV) có nhắc đến "Lệnh đối chiếu Oricon ID" (オリコンID照合コマンド) và các lệnh di chuyển [4][5], cũng như cấu trúc bảng cơ sở dữ liệu `tb_agv_issue_data` [2]. Tuy nhiên, các ngữ cảnh này không đủ để giải thích toàn bộ luồng liên kết từ chỉ thị xuất/nhập kho qua WMS, Opcenter/MOM đến AGV, cũng như không chỉ rõ hậu quả cụ thể khiến vận hành bị dừng nếu sai dữ liệu master hoặc mã Oricon/Tanaban.

---

## Q3: Manual Shipping / Existing Line
**Câu hỏi:** Dựa trên tài liệu interface/manual shipping, để lệnh xuất kho manual cho existing line hoạt động đúng thì các điều kiện master/workflow/staging/table nào phải có trước, và nguyên nhân nào có thể khiến Manual Supply Line không hiển thị container/oricon?

**Evidence files used:** 
- AMS以外のラインからの出庫指示/補足資料_要件内容反映版_20231110.xlsx
- ステージングテーブル_ライン外出庫連携自動処理用.xlsx

**Evidence status:**
- Content evidence count: 7
- Metadata-only count: 0
- Evidence quality: content_supported
- Privacy gate: provider_call_allowed = False
- Block reason: local_only_evidence

**AIOS Local Evidence Draft:**
(Đọc ra text thô của manual shipping staging table)

**AIOS Strong Model Answer:**
**Tóm tắt:**
Để lệnh xuất kho thủ công (manual shipping) cho existing line hoạt động đúng, cần đáp ứng các điều kiện về Master Data và bảng Staging trước khi thực hiện.

**Điều đã xác nhận:**
- **Master Data:** Các dữ liệu master (đặc biệt là liên quan đến Workflow) gắn với mã linh kiện (Item) phải được đăng ký sẵn từ trước trên hệ thống [4]. Cấu hình master cho Existing Line (ví dụ C31, C32) bao gồm các mục như Resource, Resource Group, Operations, Spec, Workflow và Workflow Step [3].
- **Staging Table:** Dữ liệu chỉ thị xuất kho từ hệ thống VN-MES phải được đăng ký (insert) vào bảng MOM Staging có tên là `ManualShipping_ExistingLineAuto_InboundDownload` [4].

**Điểm chưa đủ bằng chứng / Việc cần kiểm tra tiếp:**
- Tài liệu xác nhận nếu thiếu Master Data (Workflow) thì quá trình xử lý Inbound sẽ không hoạt động bình thường [4], nhưng không nêu rõ nguyên nhân trực tiếp khiến UI "Manual Supply Line" bị ẩn container/oricon. Cần kiểm tra thêm các tài liệu về UI/hiển thị của Opcenter.

---

## Tổng kết Safety & Chính sách
- Real MOM docs commited: NO
- Raw answers commited: NO
- NotebookLM parity claimed: NO
- P1.0 opened: NO
- Direct cloud call: BLOCKED (do chính sách Local_Only_Evidence)
- Owner-approved evidence pack mode: SỬ DỤNG THÀNH CÔNG

## Kết luận & Đề xuất bước tiếp theo
Strong Model cho thấy khả năng vượt trội so với thuật toán ghép file (Local Draft):
1. Biết từ chối khi bằng chứng không đủ (Q1, Q2) - giải quyết triệt để vấn đề "ảo giác chunk".
2. Biết tổng hợp các điều kiện Workflow và Staging rải rác thành câu trả lời dễ hiểu cho người vận hành (Q3).

**Recommended next:**
1. OWNER_REVIEW_3Q_STRONG_ANSWERS
2. ADD_PDF_ADAPTER_PYMUPDF4LLM (để tăng lượng "Content" thật cho PDF/PPTX, giúp Model có nhiều dữ liệu hơn).
