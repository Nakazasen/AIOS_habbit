# Vé MATCHER-FIX-PC0575 — Vá 2 lỗi bộ ghép cặp staging + đo lại lane C-Agent

**Máy thực hiện:** CÔNG TY KDTVN-PC0575 (thợ OMP), CPU-only.
**Role gợi ý:** DEFAULT (code + đo).
**Nguồn:** báo cáo `docs/phieu-viec/ket-qua/lsu-quality-pc0575.md` §3.2 + §6 mục 1 (ưu tiên 1 — lãi ngay 14/50 câu C-Agent).

## Bối cảnh — 2 lỗi đã tái lập được

File đích: `src/aios_habit/wire_qa_staging.py` (chỉ file này + test của nó; luật 1 file 1 đứa).

1. **Lỗi recall (12/50 câu).** Cả 12 câu đều có cặp trong staging với câu hỏi **y hệt**, nhưng chấm câu hỏi với chính cặp của nó chỉ được 0–2 điểm (token hoá gom cả mạch CJK thành 1 token, token chứa số bị bỏ) → bị ngưỡng `MIN_MATCH_SCORE=3.0` loại. Nhóm câu: Q0703, Q0851, Q1034, Q0685, Q0635, Q0684, Q0688, Q0696, Q1827…
2. **Lỗi ranking (2/50 câu — Q0671, Q0658).** Bonus mã linh kiện (tối đa +8, kích bởi ý định "kiểm tra") nâng 6 cặp nhiễu `dieu-tra-loi` lên 8,0 điểm, lấn át cặp đúng (5,0) → top-3 toàn cặp sai chủ đề → model trả "không đủ dữ kiện" oan.

Hiện trạng: 38/50 câu có ngữ cảnh đúng. Vá xong trần = 50/50.

## Việc phải làm

1. **Vá recall:** thêm điểm thưởng khớp câu hỏi gần đúng — chuẩn hoá khoảng trắng/dấu câu; nếu câu hỏi truy vấn xuất hiện nguyên văn (sau chuẩn hoá) trong `pair.question` ⇒ điểm áp đảo (ví dụ ≥100), không ngưỡng nào loại được.
2. **Vá ranking:** bonus mã linh kiện chỉ cộng khi cặp đã có ≥1 khớp thật (word/code); điểm gốc từ khớp câu hỏi phải luôn lớn hơn mọi bonus.
3. **Rà `MIN_MATCH_SCORE=3.0`** cho câu CJK ngắn (hoặc tách token theo ranh giới Hán/Kana/Latin): làm khi bằng chứng test cho thấy cần; hành vi với câu Latin không đổi.
4. **Test:** unit test tái lập cả 2 lỗi (tự chấm câu CJK với chính cặp của nó; ca bonus nhiễu lấn át) — đỏ trên code cũ, xanh trên code mới; hồi quy test staging liên quan.

## Nghiệm thu (2 tầng)

- **Tầng 1 — mức ghép cặp (không gọi LLM):** chạy matcher trên bộ 50 câu: mục tiêu **50/50 câu có cặp của chính nó trong top-3** (hiện 38/50); liệt kê câu nào còn hụt + lý do.
- **Tầng 2 — đo lại lane C-Agent:** 50 câu trên PC0575 (mạng `vn-kdwireless` cho endpoint C-Agent), cùng rubric 0–3. Đối chiếu GPA **2,16** hiện tại; mục tiêu **≥2,5**. Index chỉ-đọc + md5 trước/sau. Heartbeat 15 phút, checkpoint từng câu.

## Rào cứng

- Không merge `main`. Không ghi index. Python 3.11. Không đụng `rag_v2/synthesis.py` (việc của máy nhà).
- Không nới chuẩn chấm để lấy điểm; không sửa bộ câu hỏi/đáp án tham chiếu.

## Báo cáo

`docs/phieu-viec/ket-qua/matcher-fix-pc0575.md` — diff tóm tắt, test trước/sau, bảng ghép cặp 50 câu, điểm lane C-Agent trước/sau.
