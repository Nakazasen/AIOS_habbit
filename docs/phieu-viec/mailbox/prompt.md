# LLM-ENABLE-DO-NHA — [NHÀ] bật đường AI ngoài viết đáp án + đo lại 6 câu

## Bối cảnh

- Chủ sở hữu đã gỡ khóa gửi bằng chứng ra AI ngoài: `00_governance/DATA_POLICY.md` (2026-09-29), xác nhận lại 2026-10-02, áp dụng cả máy nhà và máy công ty. Nhãn `local_only`/`confidential` chỉ còn là phân loại nội bộ.
- Code đã có công tắc: commit `1b6200b` + `f9a0dbb` (nhánh `phieu-viec/rag-fix1`). Không đặt biến môi trường thì hành vi y như cũ (fail-closed, đáp án viết bằng lane tổng hợp cục bộ).
- Lượt `hodap-home` trước đó: đáp án viết bằng lane cục bộ (`synthesize_evidence`), chưa hề gọi LLM. Vé này bật AI ngoài rồi đo lại đúng bộ câu đó để so sánh.

## Việc cần làm

1. Pull tip `phieu-viec/rag-fix1`; ghi lại SHA tip đang chạy trong báo cáo.
2. Khởi chạy app với biến môi trường `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` đặt trong môi trường của TIẾN TRÌNH app/worker (không chỉ ở terminal gõ lệnh). Đấu 1 đường AI sẵn có tại nhà: ưu tiên Nakazasen Router; nếu không được thì Cầu nối Gemini Web. Cấu hình provider lấy từ biến môi trường / mục Nguồn AI trong app. TUYỆT ĐỐI không in khóa bí mật ra báo cáo hay log.
3. Kiểm chứng nhanh 1 câu bất kỳ: đáp án phải có bằng chứng provider ngoài thật sự được gọi (tên provider/model trong trace hoặc tóm tắt tuyến, không phải local fallback). Nếu đường AI lỗi: ghi đúng lỗi gốc, giữ fallback cục bộ chạy, không bịa kết quả.
4. Đo đủ 6 câu NGUYÊN VĂN như báo cáo `hodap-home` (L1–L3, E1–E3; lấy đúng văn bản câu hỏi trong `docs/phieu-viec/ket-qua/hodap-home.md`). Mỗi câu ghi: thời gian khởi tạo (chỉ câu đầu), thời gian tìm kiếm, thời gian viết đáp án (phần LLM), thời gian tổng; provider + model thật đã gọi; toàn văn đáp án; trích dẫn có khớp nguồn không; trace hợp lệ không.
5. Đối chứng chất lượng từng câu với đáp án lượt `hodap-home` (lane cục bộ): câu nào hay hơn / kém hơn, có chi tiết nào ngoài bằng chứng không.
6. Đo thêm 1 câu khi TẮT biến môi trường (restart app không có biến) để chứng minh fail-closed còn nguyên: đáp án phải quay về lane cục bộ.
7. Index chỉ đọc: SHA-256 của `library.sqlite` trước và sau phải khớp nhau; không ghi index dưới bất kỳ hình thức nào.

## Báo cáo

- Ghi vào `docs/phieu-viec/ket-qua/llm-enable-do-nha.md`; cập nhật `docs/phieu-viec/mailbox/trang-thai.md` → `xong-cho-duyet`.
- Điều kiện nào không đạt thì ghi rõ điều kiện đó kèm bằng chứng. Không fake PASS.
