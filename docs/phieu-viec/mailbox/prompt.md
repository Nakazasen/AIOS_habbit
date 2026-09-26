# Ticket E2 — Fix khâu tổng hợp theo E1 + chạy lại B1–B5 (B4 loại)

Ngày viết: 2026-09-26 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- E1 (`069460a5`, ĐẠT — Muse review 2026-09-26): nguyên nhân B1/B3 rớt dữ kiện đã rõ:
  1. `synthesize_evidence` mặc định tối đa 5 claim; `_compose_grounded_claims` đi theo
     thứ tự pack → 5 `document_summary` chèn đầu chiếm hết ngân sách trước khi tới
     chunk thân (file `src/aios_habit/rag_v2/synthesis.py`).
  2. `hybrid_search_with_summary` chèn summary lên đầu với intent `general`
     (dòng 2420–2427 `src/aios_habit/rag_v2/index.py`) dù `retrieval_mode=full`.
  3. `_best_fragment` chấm overlap token cùng ngôn ngữ → câu summary tiếng Việt chung
     thắng câu tiếng Nhật chứa `nvarchar(4000)`.
  4. B5: chunk đáp án lexical hạng 467, vượt cửa sổ 100 ứng viên → không vào
     evidence pack (lỗi thu hồi ứng viên, không phải khâu viết).
- Chi tiết: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`.
- Chế độ tự lái toàn phần (user 2026-09-26): tự quyết mọi quyết định kỹ thuật, không hỏi;
  sai thì revert commit và viết ticket sửa.

## Việc cần làm

1. **Fix claim budget** (`src/aios_habit/rag_v2/synthesis.py`): với câu hỏi tra cứu chi
   tiết (`retrieval_mode=full`), không để 5 summary đầu pack chiếm hết ngân sách claim;
   đảm bảo chunk thân vẫn được chọn; citation giữ trỏ đúng chunk chứa đáp án.
2. **Giảm summary chen đầu** (`src/aios_habit/rag_v2/index.py::hybrid_search_with_summary`):
   với `retrieval_mode=full`, không prepend summary trước chunk thân (hoặc chỉ để
   summary làm bổ sung sau kết quả thân).
3. **B5 — thu hồi khóa định danh chính xác**: quota/nhánh exact-match cho token định danh
   (HOUSE_METHOD, T_IF_PROD_RESULT…) trước khi cắt cửa sổ lexical 100; cân nhắc phân loại
   câu hỏi tra cứu mã/giá trị thành lookup riêng trong `query_planning.py`.
4. Không làm hại đường summary-first/overview: mode `overview` vẫn summary_only như cũ.
5. Test read-only (`index_read_only=True`, `BGE_BACKEND=onnx`, 2 flag summary bật như D3):
   chạy B1/B2/B3/B5 — câu trả lời phải nêu đúng đáp án (B1: 11922/12860/12626;
   B3: nvarchar(4000)/4000 ký tự; B5: HOUSE_METHOD '0'/'1') và citation trỏ đúng chunk.
   B4 **LOẠI** khỏi chấm điểm (ground truth không có trong corpus — quyết định của Muse,
   không bịa đáp án).
6. Chạy pytest liên quan; full suite nếu sửa chạm lõi. Ticket này **không ghi index thật**
   (không ingest, không --apply).

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
  (hostname, SHA code lúc chạy, diff chính, kết quả B1/B2/B3/B5 read-only trước/sau,
  pytest, bàn giao test case).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn báo cáo),
  rồi **DỪNG**.
