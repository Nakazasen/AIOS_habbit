# DRAFT — Bộ 10 câu kiểm thử thật G2 (query dưới default ONNX)

Trạng thái: **DRAFT** — chạy trên máy nhà sau khi G2 code xong (gate fingerprint
+ 3 fix retrieval của OMP đã commit). Backend: default ONNX, không đặt
`BGE_BACKEND`. Máy nhà có GPU thì backend tự chọn CUDA, nhưng mỗi câu đều phải
pass cả khi **tắt GPU** (CPU-only).

Ngày viết: 2026-09-28 (Muse).

## Luật chấm chung cho cả 10 câu

- [ ] Không trả XML thô.
- [ ] Giữ nguyên mã lỗi / con số / tên file / trích dẫn nguồn.
- [ ] Ghi latency, timeout, và trường hợp abstain (không bịa khi không tìm thấy).
- [ ] Phân loại lỗi thuộc retrieval hay synthesis nếu câu trả lời sai/thiếu.
- [ ] UI hiển thị đủ: source / document / chunk / vector / index.
- [ ] Mỗi câu chạy 2 lần: GPU bật (nếu có) và GPU tắt — kết quả phải tương đương.

## 5 câu LSU (dữ liệu: AI_LSU_du_doan_loi.xlsx, AI cảnh báo lỗi LSU.pptx)

**L1.** "Điểm danh các bước trong sheet 'các bước Bước 1–5' của file
AI_LSU_du_doan_loi.xlsx."
→ Kiểm tra: liệt kê đúng thứ tự bước, trích dẫn tên sheet + tên file.

**L2.** "Theo phân tích nguyên nhân 4M, nhóm nguyên nhân nào chiếm tỷ trọng
lớn nhất?"
→ Kiểm tra: synthesis giữ đúng số liệu 4M, không bịa tỷ trọng.

**L3.** "Slide nào trong AI cảnh báo lỗi LSU.pptx nói về dự đoán lỗi? Tóm tắt
nội dung."
→ Kiểm tra: đúng số slide (7 slide), trích dẫn tiêu đề slide.

**L4.** "Trong sheet LÀM DATA, cột nào dùng để dự đoán lỗi?"
→ Kiểm tra: tên cột chính xác từng ký tự (case nhạy cảm với mã cột).

**L5.** Câu abstain chủ động: "Dự đoán lỗi LSU cho line Z tháng 13/2026."
→ Kiểm tra: phải abstain (line Z / tháng 13 không tồn tại), không bịa số liệu.
Ghi rõ timeout và lý do abstain.

## 5 câu case lỗi / bảng mã (dữ liệu: glossary F4 + file điều tra lỗi)

**E1.** "Mã lỗi C0030 thuộc họ nào, nghĩa là gì?"
→ Kiểm tra: họ C_CALL, tên tiếng Việt + tiếng Nhật đầy đủ (glossary F4).

**E2.** "Mã F10X (có wildcard X) áp dụng cho những mã con nào?"
→ Kiểm tra: giữ nguyên wildcard X, không tự "đoán" mã con cụ thể.

**E3.** "JAM 6000 là lỗi gì, xảy ra ở unit nào?"
→ Kiểm tra: DF搬入不良JAM — giữ nguyên tên tiếng Nhật, unit DF.

**E4.** "Lỗi SCT điều chỉnh tự động mã 03 có điểm gì đặc biệt?"
→ Kiểm tra: trùng ErrNo=03 giữ cả 2 qua code_sub (glossary F4).

**E5.** Test bảng mã: hỏi về file có tên từng bị mã hóa `#UXXXX`
(đã fix về tiếng Việt khi giải nén Dieu-tra-loi).
→ Kiểm tra: tên file hiển thị đúng tiếng Việt, không còn `#UXXXX`,
không vỡ font ở trích dẫn.

## Nghiệm thu

Bảng 10 dòng: câu hỏi | latency GPU | latency CPU | đạt/không |
retrieval/synthesis/abstain | ghi chú. 10/10 đạt (cả 2 chế độ GPU) mới đóng G2.
