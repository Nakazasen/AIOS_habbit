# VÉ: RUBRIC-NORMALIZE-PC0575 (chuẩn hoá thước đo chấm + chấm lại offline)

- Mã vé: `RUBRIC-NORMALIZE-PC0575`
- Máy: CÔNG TY KDTVN-PC0575 (thợ agy), CPU-only.
- Role gợi ý: DEFAULT (code nhỏ + chấm lại offline).
- Nguồn: báo cáo `docs/phieu-viec/ket-qua/rag-fail-analysis-pc0575.md` §5 Ưu tiên 1 (tác động +0,360 GPA, rủi ro 0).

## Bối cảnh

Phân tích lane RAG (GPA 0,93) cho thấy 10/50 câu bị **thước đo chấm oan** (nhóm C, mất 18,0 điểm): đáp án đúng nội dung nhưng bộ chấm tự động không nhận vì khác định dạng số/đơn vị, cộng thêm vài từ khóa trong bộ đề bị lỗi. Vé này sửa THƯỚC ĐO và chấm lại từ đáp án đã lưu — đây là đính chính phép đo, không phải cải thiện hệ thống; báo cáo phải ghi rõ điều đó.

## Việc phải làm

1. **Hàm chuẩn hoá khi chấm** — thêm `normalize_text_for_eval` trong `aios_habit.quality_harness` (kèm test):
   - Bỏ dấu chấm phân cách hàng nghìn: `48.384` → `48384`.
   - Đổi dấu phẩy thập phân sang dấu chấm: `-0,81` → `-0.81`.
   - Đồng nhất đơn vị: `3 giây` = `3 s`; `0 - 15 độ C` = `0–15°C`.
   - Áp chuẩn hoá cho CẢ đáp án lẫn từ khóa trước khi so khớp.
2. **Sửa từ khóa lỗi trong bộ đề** (theo đúng danh sách báo cáo §5):
   - `Q0630`: thay `['DRUM.', 'DRUM.', 'LSU_2019.01.18_K.']` bằng khái niệm cốt lõi (quét ngang, quay drum).
   - `Q0635`: bổ sung từ khóa nội dung (quang lượng tâm, vùng biên, nhạt màu).
   - `Q0674`: bổ sung từ khóa tiếng Việt (`không bất thường`, `không thay đổi`).
   - `Q0708`: chấp nhận thêm `1.15` và `1.24`.
   - Mọi thay đổi từ khóa phải liệt kê trước/sau trong báo cáo — cấm sửa thêm ngoài danh sách khi chưa có bằng chứng lỗi tương tự.
3. **Chấm lại offline** từ file đáp án đã lưu của lane RAG (`rag_progress.json` trên máy): không gọi lại RAG, không gọi mạng. Xuất bảng từng câu: điểm cũ → điểm mới, câu nào đổi và vì chuẩn hoá nào.
4. Nếu trên máy còn file đáp án đã lưu của lane C-Agent: chấm lại bằng thước mới, báo cáo riêng (trước/sau), không trộn với lane RAG.

## Nghiệm thu

- Test hàm chuẩn hoá xanh (ca: nghìn, thập phân phẩy, đơn vị, ca không đổi điểm khi đáp án sai thật).
- Tổng mới lane RAG đối chiếu kỳ vọng ~1,29 GPA; lệch thì giải thích bằng bảng từng câu.
- Ghi cứng trong báo cáo: "điểm tăng do sửa thước đo, không phải hệ thống trả lời tốt hơn".

## Rào cứng

- Không merge `main`. Không ghi index. Python 3.11. Không đụng `wire_qa_staging.py` (OMP đang vá ở vé MATCHER-FIX) và không đụng `rag_v2/synthesis.py`.
- Heartbeat tối thiểu 15 phút nếu việc kéo dài.

## Báo cáo

`docs/phieu-viec/ket-qua/rubric-normalize-pc0575.md` — danh sách thay đổi thước đo/từ khóa, bảng điểm từng câu trước/sau, tổng kết 2 lane (nếu chấm lại được cả C-Agent).
