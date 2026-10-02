# Vé: KNOWLEDGE-ENRICH-PILOT — làm giàu tri thức theo lô (thí điểm 5 hiện tượng F CALL)

Lane: [VM] Muse code+test (XONG đêm 2026-10-02, commit `cbb54ab`, push remote `63cf68c`) → [NHÀ] OMP tự chạy toàn bộ trên máy nhà: sinh câu hỏi vàng → xuất batch 5 hiện tượng F CALL thật → soạn đáp án qua cầu nối Gemini Web → nhập staging → verify trên dữ liệu thật.
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user chốt 2026-10-02, đính chính lane 2026-10-03)

- Dùng LLM làm "đào tạo đi tắt" cho AIOS: LLM soạn bản thảo vì luồng phỏng vấn chuyên gia chưa vận hành; chuyên gia thật phản hồi sau.
- **Quyết định lane 2026-10-03 (user):** máy nhà KHÔNG có Copilot 365; máy công ty (có Copilot 365 Premium) đang tắt. Vé này chạy lane máy nhà: **soạn đáp án bằng Gemini Web qua cầu nối sẵn có (`127.0.0.1:8585`)** — đúng phương án dự phòng đã chốt trong phụ lục 2026-10-02, và đã được chứng minh chạy được ở vé `LLM-ENABLE-DO-NHA-R1` (6/6 câu, trace valid).
- Nakazasen Router vẫn lỗi khóa cloud (vé R1 đã chứng minh) → không dùng Router ở vé này.
- **Không lưu vết LLM nào trong kho.** Nhãn duy nhất: `kiến thức đã được đào tạo bổ sung`. Quản lý phản hồi của chuyên gia thật bằng trạng thái nghiệp vụ riêng (`cho_chuyen_gia_phan_hoi` / `chuyen_gia_da_phan_hoi`), không ghi nguồn LLM.
- **Không dùng tài khoản ChatGPT cá nhân cho dữ liệu công ty** khi chưa rõ quy định công ty: Copilot 365 đã được công ty cho phép, ChatGPT cá nhân thì chưa. User có thể gỡ rào này bằng quyết định rõ ràng sau.
- Đính chính cách gọi "auto train": Gemini/Copilot **không huấn luyện** trên dữ liệu của mình — chúng chỉ đọc file trong phiên để soạn thảo. Tri thức thật vẫn nằm trong kho AIOS.
- Rào trung thực giữ nguyên: đáp án do LLM soạn chỉ là **bản thảo** (`cho_chuyen_gia_phan_hoi`), bắt buộc qua chuyên gia duyệt mới được gắn nhãn `kiến thức đã được đào tạo bổ sung`. Cấm gắn nhãn chuyên gia cho bản thảo chưa duyệt.

## Việc Muse làm trên VM (ĐÃ XONG)

1. **Form chuẩn Q&A điều tra nhân quả** (schema, có test): mỗi form gồm
   - định danh: `gap_id`, mã lỗi, hiện tượng, model/line/công đoạn;
   - câu hỏi + mục tiêu câu hỏi / khía cạnh cần lấp;
   - câu trả lời;
   - giả thuyết nguyên nhân, cơ chế gây lỗi, nhóm 4M (Man/Machine/Material/Method);
   - bằng chứng cần thu thập, tiêu chí xác nhận/bác bỏ, cách phân biệt với giả thuyết khác;
   - ngưỡng/đơn vị/dung sai, ngoại lệ;
   - đối sách tạm thời / lâu dài, điều kiện tái phát;
   - ca/tài liệu liên quan, chỗ cần chuyên gia phản hồi, độ tự tin.
   - Form dùng chung cho cả 3 việc: LLM soạn thảo theo lô, chuyên gia phản hồi, và nạp vào kho.
   - Cấm form chung chung kiểu chỉ có `answer`/`confidence` — trả lời mà thiếu nhân quả/bằng chứng thì từ chối.
2. **Bộ sinh + chấm điểm câu hỏi vàng**: từ knowledge gaps 6 loại (`missing_threshold`, `missing_condition`, `missing_exception`, `missing_example`, `conflict`, `stale_knowledge`) + tập giả thuyết từ ca lỗi → sinh câu hỏi, chấm theo 6 tiêu chí (nặng nhất: khả năng phân biệt giả thuyết nguyên nhân; tiếp: lấp gap quan trọng, yêu cầu bằng chứng đo được, đào Why-Why/4M, tính mới, khả thi), chọn top-K mỗi hiện tượng (≥1 câu phân biệt giả thuyết, ≥1 câu bằng chứng đo được, phủ ≥3 nhánh 4M). Tái dùng guardrail hiện có (chống câu hỏi dẫn dắt, chống trùng Jaccard ≥ 0.85, chống vượt budget).
3. **Script xuất batch**: file JSONL (câu hỏi + ngữ cảnh ca + schema form) + phiếu Markdown đọc được cho người (mỗi hiện tượng một section, mỗi câu kèm form trống đúng schema). Thí điểm: **5 hiện tượng F CALL thật** lấy từ DB lỗi (không tự bịa).
4. **Script nhập batch**: đọc file câu trả lời → validate schema → dedup SHA-256 → ghi vào staging DB riêng (`local_cases/staging_enrichment.sqlite`, tách khỏi DB chính và index production) với nhãn duy nhất `kiến thức đã được đào tạo bổ sung`. Cấm nhập thẳng vào DB chính / luồng trả lời chính khi chưa qua vòng phản hồi chuyên gia. Merge kho thật là vé riêng.
5. **Nối câu hỏi vàng vào interview engine**: bộ câu hỏi từ form trở thành seed questions cho `adaptive_interview_engine` (theo loại gap đã có).
6. **Bộ đo trước/sau**: cùng một bộ câu hỏi về 5 hiện tượng — đo độ phủ tri thức (gap high giảm ≥60%), truy hồi (chunk mới vào top-5 ≥4/5), độ đầy form (≥80%), khả năng phân biệt giả thuyết (≥70% cặp), và thời gian trả lời.
7. Test + `compileall` + `pytest` + `cli audit` PASS theo luật repo; không ghi index production; không đụng ổ D.

## Việc OMP làm [NHÀ] (toàn bộ, không chờ user)

1. Pull code commit `cbb54ab` (remote `63cf68c`), kiểm tra các module golden question import được trên Python 3.11.
2. Chạy bộ sinh + chấm điểm trên **5 hiện tượng F CALL thật** lấy từ DB lỗi (`C:/tmp/b0-dict/error_cases_dict.db`, không tự bịa): mỗi hiện tượng chọn top-K câu hỏi theo ràng buộc (≥1 câu phân biệt giả thuyết, ≥1 câu bằng chứng đo được, phủ ≥3 nhánh 4M).
3. Chạy script xuất batch: JSONL + phiếu Markdown (mỗi hiện tượng một section, mỗi câu kèm form trống đúng schema) + manifest SHA-256.
4. **Soạn đáp án qua cầu nối Gemini Web** (`127.0.0.1:8585`, model `gemini-web`, công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` đặt trong tiến trình gọi): mỗi hiện tượng một lượt gọi, đưa nguyên phiếu Markdown + yêu cầu trả đúng schema form nhân quả đầy đủ (giả thuyết, cơ chế gây lỗi, 4M, bằng chứng đo được, tiêu chí xác nhận/bác bỏ, đối sách). Prompt nhắc định dạng đặt trong probe, không sửa mã sản phẩm, không nới schema. Bài học vé R1: Gemini hay trả ngắn/thiếu số liệu — prompt phải yêu cầu điền đầy đủ từng trường schema, trường nào không đủ dữ kiện thì ghi rõ "chưa đủ bằng chứng" thay vì bỏ trống.
5. Chạy script nhập batch: validate schema → dedup SHA-256 → ghi vào staging DB riêng `local_cases/staging_enrichment.sqlite` (tách khỏi DB chính và index production). Từ chối đường dẫn production; từ chối đáp án gắn sẵn `chuyen_gia_da_phan_hoi`; cấm field nguồn LLM. Đánh dấu toàn bộ bản thảo là `cho_chuyen_gia_phan_hoi`.
6. Verify: staging DB đúng schema, nhãn duy nhất `kiến thức đã được đào tạo bổ sung`; DB chính và index production không đổi (đo SHA trước/sau); không bản thảo nào lọt vào luồng trả lời chính.
7. Chạy bộ đo trước/sau theo tiêu chí ĐẠT.
8. Báo cáo `docs/phieu-viec/ket-qua/knowledge-enrich-pilot.md` + `xong-cho-duyet`.

## Việc user làm

- **Không có việc tay ở vé này.** Vé chạy độc lập bằng lane máy nhà.

## Tiêu chí ĐẠT

- Form schema có test bao phủ; xuất/nhập batch chạy được trên dữ liệu thật.
- 5 hiện tượng đều là F CALL thật từ DB, không bịa.
- Nhãn duy nhất đúng `kiến thức đã được đào tạo bổ sung`; toàn bộ bản thảo ở trạng thái `cho_chuyen_gia_phan_hoi`; không có bản chưa qua vòng chuyên gia nào lọt vào luồng trả lời chính.
- Bộ đo trước/sau chạy được; index production `library.sqlite` không đổi.
- Commit riêng trên branch `phieu-viec/rag-fix1`, không đụng `main`.

## Phụ lục: Copilot 365 (so sánh chất lượng, vé riêng — không chặn vé này)

- Khi máy công ty bật lại: có thể chạy lại batch 5 hiện tượng qua Copilot 365 Premium (bật **Work IQ** + **Think deeper** trên thanh chat, mỗi hiện tượng một lượt chat, paste nguyên phiếu Markdown, nhận đáp án đúng schema) để so sánh chất lượng bản thảo với lane Gemini Web. File batch xuất ra dùng chung, ai soạn cũng điền cùng một form.
- So sánh chất lượng là vé riêng; vé này ĐẠT độc lập bằng lane máy nhà.
