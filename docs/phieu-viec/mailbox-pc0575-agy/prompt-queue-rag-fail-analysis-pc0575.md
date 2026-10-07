# VÉ: RAG-FAIL-ANALYSIS-PC0575 (phân tích vì sao lane RAG điểm thấp — phân loại lỗi, xếp ưu tiên sửa)

- Mã vé: `RAG-FAIL-ANALYSIS-PC0575`
- Role OMP gợi ý: PLAN (vé phân tích/chẩn đoán, chỉ đọc — không code)
- Máy: công ty KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/rag-fail-analysis-pc0575.md`
- Đầu vào bắt buộc đọc trước: `docs/phieu-viec/ket-qua/lsu-quality-pc0575.md` (báo cáo đo 50 câu) + kết quả thô lane RAG trong `local_cases/` / `scratch/lsu-quality/` trên máy.

## Bối cảnh

Vé `LSU-QUALITY-PC0575` (OMP, ĐẠT 09:35 07/10) đo 50 câu LSU thật trên 2 lane:
- Lane C-Agent: **108,2/150 — GPA 2,16** (70% đạt).
- Lane RAG: **46,5/150 — GPA 0,93** (24% đạt); **19/50 câu** trả lời dạng "không đủ dữ kiện";
  chỉ **5/50 câu** nêu tên tệp nguồn thật (16 câu chỉ có nhãn `[n]`); thời gian retrieval
  median 142 s/câu (20–599 s).

Báo cáo đã kết luận hướng: RAG bị chặn chủ yếu bởi (1) retrieval không mang được mảnh
chứa số liệu, (2) trả lời lệch mảnh (≥4 câu), và (3) một phần điểm thấp là **oan do cách
chấm** (lệch định dạng số `48.384` vs `48384`, làm tròn, từ khóa Nhật vs đáp án Việt —
ít nhất 3 câu mất điểm oan đã soi thấy). Nhưng chưa ai phân loại đủ 50 câu để biết
**sửa cái gì trước thì GPA lên nhiều nhất**. Vé này làm việc đó. CHỈ ĐỌC + PHÂN TÍCH,
không sửa code.

## Việc cần làm

1. Lấy đủ 50 đáp án lane RAG + điểm từng câu từ kết quả thô của vé LSU-QUALITY
   (nếu thiếu file thô, dựng lại danh sách từ phụ lục báo cáo — ghi rõ nguồn nào).
2. Phân loại TỪNG câu dưới chuẩn (<2 điểm) vào đúng 1 nhóm gốc:
   - **A — Retrieval trượt**: mảnh chứa số liệu/dữ kiện đúng không hề vào top kết quả.
   - **B — Có mảnh đúng nhưng trả lời sai/lệch**: tổng hợp bỏ qua hoặc diễn giải sai mảnh.
   - **C — Oan do chấm**: đáp án đúng về nội dung nhưng mất điểm vì định dạng/từ khóa
     (kèm bằng chứng đối chiếu đáp án tham chiếu).
   - **D — Thiếu nguồn thật**: câu cần dữ kiện nằm ở file nguồn mà máy CTY không có /
     index không chứa (0/889 file nguồn — xem caveat vé digest).
   - **E — Khác** (ghi rõ).
3. Định lượng: mỗi nhóm chiếm bao nhiêu câu, "ăn" bao nhiêu điểm GPA. Ước tính GPA lane
   RAG nếu chỉ sửa từng nhóm một (để xếp ưu tiên bằng số, không bằng cảm tính).
4. Xếp danh sách việc sửa theo thứ tự ưu tiên (tác động GPA cao → thấp, kèm độ khó áng chừng).
   Đặc biệt trả lời rõ: bao nhiêu trong số GPA 0,93 là **lỗi thật của hệ thống**, bao nhiêu
   là **lỗi của thước đo** (nhóm C)?
5. Ghi báo cáo `rag-fail-analysis-pc0575.md`: bảng phân loại 50 câu + tổng hợp nhóm +
   danh sách ưu tiên. Mọi kết luận phải có bằng chứng (trích đáp án/mảnh liên quan).

## Rào cứng

- CHỈ ĐỌC: không sửa code, không sửa file đo cũ, không ghi index (mở index chỉ-đọc nếu cần soi mảnh).
- KHÔNG đụng `wire_qa_staging.py` (OMP đang vá ở vé MATCHER-FIX-PC0575 — luật 1 file 1 đứa).
- Không nhập kết quả phân tích vào kho tri thức. Không merge `main`. Không secret trong báo cáo.

## Quy ước heartbeat + checkpoint

- Mỗi bước ghi 1 dòng `ghi_chu` mốc bước vào mailbox, tối thiểu 15 phút/lần.
- Phân loại xong nhóm câu nào ghi ngay vào báo cáo nháp (checkpoint) — kẹt giữa chừng người sau đọc tiếp được.

## Tiêu chí nghiệm thu

- ĐẠT = đủ 50 câu được phân loại có bằng chứng + định lượng theo nhóm + danh sách sửa xếp ưu tiên bằng số.
- Báo cáo trả lời được câu hỏi: "GPA 0,93 — bao nhiêu là lỗi thật, bao nhiêu là thước đo oan?"
