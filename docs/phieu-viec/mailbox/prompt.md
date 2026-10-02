# LLM-ENABLE-DO-NHA-R1 — [NHÀ] Cứu trợ vé đường AI ngoài (bản rescue sau escalate cho-muse 23:04)

> Vé gốc `LLM-ENABLE-DO-NHA` bị kẹt: từ 22:32 (commit mốc 0 kiểm công gate đạt RELAUNCH 3/4 bridge Gemini) đến 23:04 không có commit tiến triển nào, file báo cáo chưa tồn tại → watcher escalate `cho-muse`. Bản rescue này giữ nguyên mục tiêu vé gốc, làm rõ từng bước chẩn đoán và bắt buộc checkpoint.

## Quy tắc session (quyết định kỹ thuật của Muse)
- **Session handover:** nếu vẫn còn session OMP cũ (PID 10792, từ 21:39) đang sống thì nó DỪNG NGAY khi session mới nhận vé này. Chỉ một OMP chạy cho mailbox này tại một thời điểm — cấm hai session cùng làm song song.
- **Checkpoint bắt buộc:** mỗi phase xong phải commit checkpoint ngay (kể cả chỉ là script/probe chưa hoàn chỉnh) và ghi một dòng `ghi_chu` có timestamp vào `trang-thai.md` để watcher thấy tiến triển. Cấm để quá 45 phút không có commit khi đang làm việc kéo dài (đây chính là nguyên nhân lần kẹt trước).
- Index chỉ đọc: SHA-256 `library.sqlite` trước/sau phải khớp. Không ghi index.

## Phase 0 — kiểm lại công gate (đã đạt mốc 0 lúc 22:32, kiểm lại cho chắc)
1. Pull tip `phieu-viec/rag-fix1`; ghi SHA tip vào báo cáo.
2. Khởi chạy app với `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` đặt TRONG môi trường tiến trình app/worker (không chỉ terminal gõ lệnh) + `AIOS_LOCAL_AI_ENDPOINT` trỏ đúng cầu nối. Ưu tiên Nakazasen Router; không được thì Cầu nối Gemini Web (mốc 0 đã xác nhận `direct_ready`).
3. Chạy 1 câu bất kỳ: đáp án phải có bằng chứng provider ngoài thật sự được gọi (tên provider/model trong trace hoặc tóm tắt tuyến). Nếu rơi về local fallback → dừng, ghi đúng lỗi gốc (cấu hình endpoint, key, hay wiring synthesis), không bịa kết quả. → **commit checkpoint Phase 0.**

## Phase 1 — đấu script probe vào lane tổng hợp
- Hoàn thiện script probe: gọi lane tổng hợp RAG v2 với công tắc cloud bật, đảm bảo `synthesize_with_provider`/`RouterSynthesisProvider` thực sự đi qua provider ngoài (theo vá `1b6200b` + `f9a0dbb`).
- Chạy thử 1 câu qua script, xác minh trace có provider ngoài. → **commit checkpoint Phase 1.**

## Phase 2 — đo đủ 6 câu
- 6 câu NGUYÊN VĂN như `docs/phieu-viec/ket-qua/hodap-home.md` (L1–L3, E1–E3). Mỗi câu ghi: thời gian khởi tạo (câu đầu), tìm kiếm, viết đáp án (phần LLM), tổng; provider + model thật; toàn văn đáp án; trích dẫn khớp nguồn không; trace hợp lệ không.
- Đối chứng chất lượng từng câu với đáp án lượt `hodap-home` (lane cục bộ): hay hơn/kém hơn, chi tiết ngoài bằng chứng. → **commit checkpoint Phase 2.**

## Phase 3 — báo cáo
- Ghi `docs/phieu-viec/ket-qua/llm-enable-do-nha.md`; cập nhật `trang-thai.md` → `xong-cho-duyet`.
- Điều kiện nào không đạt ghi rõ kèm bằng chứng. Không fake PASS. TUYỆT ĐỐI không in khóa bí mật ra báo cáo hay log.
