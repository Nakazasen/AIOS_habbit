# Vé: KNOWLEDGE-DIGEST-HOME — sổ tay tri thức toàn kho cho LLM context dài (vòng hỏi đáp cải thiện)

Lane: [VM] Muse code pipeline + probe (test trên sample) → [NHÀ] OMP chạy full trên DB thật qua cầu nối Gemini Web.
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user quyết 2026-10-03 ~00:45 +07)

- RAG hiện tại chậm, trả lời ít trúng, đặc biệt kém với câu hỏi có tính chất tổng quan / cơ bản / rộng.
- User ủy quyền: đưa toàn bộ kho tri thức lên LLM ngoài để có vòng hỏi đáp cải thiện ngay trong 2 ngày cuối tuần ở nhà; chuyên gia duyệt tính sau.
- Nói thẳng kỹ thuật: không LLM nào nhét vừa ~148k chunk / ~3GB vào một prompt. Đường làm được: **nén toàn bộ kho thành một "sổ tay tri thức" Markdown có cấu trúc** (mỗi document một mục: chủ đề, ý chính, số liệu/thông số then chốt, điều kiện–ngưỡng–ngoại lệ, liên quan tài liệu nào), rồi nạp sổ tay vào context dài của Gemini để hỏi đáp trực tiếp, không qua retrieval chunk.
- Provider: **cầu nối Gemini Web sẵn có** (`127.0.0.1:8585`, đã chứng minh ở vé R1) — không cần tài khoản/key mới. ChatGPT/Grok để dành vé sau nếu cần đối chứng.
- Vòng hỏi đáp này chạy **song song** với RAG, không thay thế: sổ tay phục vụ câu hỏi tổng quan/bao quát; RAG giữ cho câu hỏi cần trích dẫn chính xác từng chunk.

## Rào trung thực (giữ nguyên)

- Sổ tay là **bản thảo do LLM soạn** — file sổ tay ghi rõ dòng đầu: "Bản thảo — chưa qua chuyên gia duyệt".
- Không gắn nhãn `kiến thức đã được đào tạo bổ sung`; không nhập sổ tay vào kho tri thức; không nhập vào luồng trả lời chính của app.
- Không lưu vết LLM nào trong kho (không ghi nguồn LLM vào DB).

## Việc Muse làm trên VM

1. Pipeline `knowledge_digest.py`:
   - đọc chunk theo từng document từ index (**chỉ đọc**, không ghi);
   - mỗi document một lượt tóm tắt có cấu trúc qua LLM (prompt nhắc định dạng đặt trong code, không sửa mã sản phẩm);
   - gom các mục theo chủ đề (tái dùng phân loại sẵn có: 4M / loại lỗi / line–công đoạn);
   - xuất sổ tay Markdown duy nhất + manifest SHA-256;
   - chạy batch có **checkpoint/resume** (ghi tiến độ mỗi 25 document).
2. Probe `digest_qa.py`: nạp sổ tay vào context LLM → hỏi → ghi đáp án + thời gian + số token dùng.
3. Bộ benchmark 10–15 câu hỏi tổng quan/cơ bản/rộng + rubric chấm độ bao quát đơn giản (đủ ý chính / thiếu ý / sai).
4. Test trên sample document (không cần DB thật trên VM); `compileall` + `pytest` + `cli audit` PASS; Python 3.11.

## Việc OMP làm [NHÀ]

0. Đếm thực tế số document trong collection `tri_thuc`, ghi con số vào báo cáo (cấm hardcode số lượng).
1. Pull code pipeline, chạy full trên DB thật: mỗi document một lượt tóm tắt qua cầu nối Gemini Web (công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` đặt trong tiến trình gọi). Batch qua đêm, checkpoint mỗi 25 doc, **cấm quá 45 phút không ghi log tiến độ**. Nếu cầu nối quá chậm hoặc lỗi nhiều: báo trung thực số đã xong + kế hoạch resume, không fake số.
2. Gom thành sổ tay Markdown duy nhất + manifest SHA-256. Kiểm tra bao phủ: số mục trong sổ tay phải bằng số document đã đếm ở bước 0.
3. Chạy probe hỏi đáp trên bộ benchmark: ghi đáp án + thời gian từng câu; chạy cùng bộ câu qua lane RAG hiện tại để so sánh (thời gian + độ bao quát theo rubric).
4. DB chính và index production **chỉ đọc** (đo SHA trước/sau).
5. Báo cáo `docs/phieu-viec/ket-qua/knowledge-digest-home.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Sổ tay bao phủ 100% document đã đếm; manifest SHA-256 hợp lệ.
- Probe trên câu hỏi tổng quan: lane sổ tay **nhanh hơn** RAG và **bao quát hơn** theo rubric (báo cáo ghi số liệu cụ thể từng câu, không nói chung chung).
- SHA index production không đổi; không bản thảo nào lọt vào kho/luồng trả lời chính.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
