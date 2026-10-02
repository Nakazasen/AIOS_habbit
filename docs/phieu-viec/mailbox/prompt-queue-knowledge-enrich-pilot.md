# Vé: KNOWLEDGE-ENRICH-PILOT — làm giàu tri thức theo lô bằng Copilot (thí điểm 5 hiện tượng F CALL)

Lane: [VM] Muse code+test trên VM → [USER] chạy batch Copilot trên máy công ty (Copilot 365 Premium) → [NHÀ] OMP verify trên máy nhà (dữ liệu thật, chỉ đọc DB chính).
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user chốt 2026-10-02)

- Dùng Copilot/LLM làm "đào tạo đi tắt" cho AIOS: Copilot 365 đóng vai chuyên gia vì luồng phỏng vấn chuyên gia chưa vận hành; chuyên gia thật phản hồi sau.
- Copilot 365 Premium không trần hạn mức → khai thác theo lô, càng tự động càng tốt.
- **Không lưu vết LLM nào trong kho.** Nhãn duy nhất: `kiến thức đã được đào tạo bổ sung`. Quản lý phản hồi của chuyên gia thật bằng trạng thái nghiệp vụ riêng (`cho_chuyen_gia_phan_hoi` / `chuyen_gia_da_phan_hoi`), không ghi nguồn LLM.
- AIOS hiện tại dùng Sonnet 4 qua gói C-Agent trả phí của công ty.

## Việc Muse làm trên VM

1. **Form chuẩn Q&A điều tra nhân quả** (schema, có test): mỗi form gồm
   - định danh: `gap_id`, mã lỗi, hiện tượng, model/line/công đoạn;
   - câu hỏi + mục tiêu câu hỏi / khía cạnh cần lấp;
   - câu trả lời;
   - giả thuyết nguyên nhân, cơ chế gây lỗi, nhóm 4M (Man/Machine/Material/Method);
   - bằng chứng cần thu thập, tiêu chí xác nhận/bác bỏ, cách phân biệt với giả thuyết khác;
   - ngưỡng/đơn vị/dung sai, ngoại lệ;
   - đối sách tạm thời / lâu dài, điều kiện tái phát;
   - ca/tài liệu liên quan, chỗ cần chuyên gia phản hồi, độ tự tin.
   - Form dùng chung cho cả 3 việc: Copilot trả lời theo lô, chuyên gia phản hồi, và nạp vào kho.
   - Cấm form chung chung kiểu chỉ có `answer`/`confidence` — trả lời mà thiếu nhân quả/bằng chứng thì từ chối.
2. **Bộ sinh + chấm điểm câu hỏi vàng**: từ knowledge gaps 6 loại (`missing_threshold`, `missing_condition`, `missing_exception`, `missing_example`, `conflict`, `stale_knowledge`) + tập giả thuyết từ ca lỗi → sinh câu hỏi, chấm theo 6 tiêu chí (nặng nhất: khả năng phân biệt giả thuyết nguyên nhân; tiếp: lấp gap quan trọng, yêu cầu bằng chứng đo được, đào Why-Why/4M, tính mới, khả thi), chọn top-K mỗi hiện tượng (≥1 câu phân biệt giả thuyết, ≥1 câu bằng chứng đo được, phủ ≥3 nhánh 4M). Tái dùng guardrail hiện có (chống câu hỏi dẫn dắt, chống trùng Jaccard ≥ 0.85, chống vượt budget).
3. **Script xuất batch**: file JSONL (câu hỏi + ngữ cảnh ca + schema form) + phiếu Markdown đọc được cho người (mỗi hiện tượng một section, mỗi câu kèm form trống đúng schema). Thí điểm: **5 hiện tượng F CALL thật** lấy từ DB lỗi (không tự bịa).
4. **Script nhập batch**: đọc file câu trả lời → validate schema → dedup SHA-256 → ghi vào staging DB riêng (`local_cases/staging_enrichment.sqlite`, tách khỏi DB chính và index production) với nhãn duy nhất `kiến thức đã được đào tạo bổ sung`. Cấm nhập thẳng vào DB chính / luồng trả lời chính khi chưa qua vòng phản hồi chuyên gia. Merge kho thật là vé riêng.
5. **Nối câu hỏi vàng vào interview engine**: bộ câu hỏi từ form trở thành seed questions cho `adaptive_interview_engine` (theo loại gap đã có).
6. **Bộ đo trước/sau**: cùng một bộ câu hỏi về 5 hiện tượng — đo độ phủ tri thức (gap high giảm ≥60%), truy hồi (chunk mới vào top-5 ≥4/5), độ đầy form (≥80%), khả năng phân biệt giả thuyết (≥70% cặp), và thời gian trả lời.
7. Test + `compileall` + `pytest` + `cli audit` PASS theo luật repo; không ghi index production; không đụng ổ D.

## Việc user làm (máy công ty, Copilot 365 Premium)

- **BẮT BUỘC trước khi hỏi:** đặt chế độ **Work IQ** và chế độ suy nghĩ **Think deeper** trên thanh chat Copilot (ảnh user gửi 2026-10-02). Đây là chế độ suy luận sâu + truy cập tri thức công việc, cho đáp án chuyên gia chất lượng cao nhất.
- Chạy batch 5 hiện tượng F CALL: mỗi hiện tượng một lượt chat, paste nguyên phiếu câu hỏi từ file Markdown, nhận đáp án theo đúng schema form, lưu file câu trả lời về.
- Duyệt nhanh đợt đầu: đánh dấu mục nào đạt / mục nào cần sửa (chuyên gia thật phản hồi sau, ghi vào trạng thái nghiệp vụ).

## Việc OMP verify [NHÀ]

- Chạy script xuất/nhập trên dữ liệu thật: staging DB đúng schema, nhãn đúng (`kiến thức đã được đào tạo bổ sung`), DB chính và index production không đổi (đo SHA trước/sau).
- Báo cáo `docs/phieu-viec/ket-qua/knowledge-enrich-pilot.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Form schema có test bao phủ; xuất/nhập batch chạy được trên dữ liệu thật.
- Nhãn duy nhất đúng `kiến thức đã được đào tạo bổ sung`; không có bản chưa qua vòng chuyên gia nào lọt vào luồng trả lời chính.
- Bộ đo trước/sau chạy được; index production `library.sqlite` không đổi.
- Commit riêng trên branch `phieu-viec/rag-fix1`, không đụng `main`.

## Phụ lục: phương án khi không có Copilot (user hỏi 2026-10-02 ~22:00)

- Ở máy không có Copilot 365 (ví dụ máy nhà): được phép dùng **Gemini Web qua cầu nối sẵn có (`127.0.0.1:8585`)** hoặc **Nakazasen Router** để soạn thảo đáp án theo đúng schema/form, thay cho Copilot. File batch xuất ra dùng chung, ai soạn cũng điền cùng một form.
- **Không dùng tài khoản ChatGPT cá nhân cho dữ liệu công ty** khi chưa rõ quy định công ty: Copilot 365 đã được công ty cho phép; ChatGPT cá nhân thì chưa. User có thể gỡ rào này bằng quyết định rõ ràng sau.
- Đính chính cách gọi "auto train": ChatGPT/Gemini **không huấn luyện** trên dữ liệu của mình — chúng chỉ đọc file đính kèm trong phiên/project để soạn thảo. Tri thức thật vẫn nằm trong kho AIOS.
- Rào trung thực giữ nguyên: đáp án do LLM soạn chỉ là **bản thảo**, bắt buộc qua chuyên gia duyệt (trạng thái `cho_chuyen_gia_phan_hoi` → `chuyen_gia_da_phan_hoi`) mới được gắn nhãn `kiến thức đã được đào tạo bổ sung`. Cấm gắn nhãn chuyên gia cho bản thảo chưa duyệt.
