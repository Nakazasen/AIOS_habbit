# Vé LSU-QUALITY-RAG-HOME — Đo lane RAG bộ 50 câu LSU trên máy nhà, CPU-only

**Máy thực hiện:** NHÀ h410asrock (thợ OMP).
**Role gợi ý:** DEFAULT (đo + báo cáo, không sửa logic).
**Lệnh user (23:41 06/10):** "Máy nhà đo nhưng không dùng VGA."

## Bối cảnh

Vé `LSU-QUALITY-PC0575` (máy công ty) đo 2 lane trên bộ 50 câu LSU:
- Lane C-Agent: XONG 50/50 (108,2/150, GPA 2,16; khớp staging 38 câu GPA 2,78 / không khớp 12 câu GPA 0,21).
- Lane RAG: mới 33/50 thì máy công ty hết pin/tắt (im từ 22:38), chưa biết khi nào bật lại.

User lệnh: máy nhà đo thay lane RAG — **nhưng CPU-ONLY, cấm dùng GPU/VGA**, để số liệu cùng
mặt bằng điều kiện với máy công ty (CPU-only). Chạy **trọn 50 câu** (không nối 17 câu lẻ)
để lane có một bộ số tự nhất quán; kết quả PC0575 (33 câu) dùng đối chiếu chéo sau.

## Điều kiện đo (khóa cứng)

1. **CPU-only tuyệt đối:** ép backend nhúng chạy CPU (vd `CUDA_VISIBLE_DEVICES=""` /
   chọn `CPUExecutionProvider`), KHÔNG để fallback lặng lẽ sang GPU. Đầu mỗi phiên đo +
   trong báo cáo phải có bằng chứng device thực tế đang dùng = CPU (log provider/dòng cấu hình).
2. **Index chỉ-đọc:** dùng index production hiện hành của máy nhà, KHÔNG ghi/nhúng lại.
   Ghi SHA256/md5 của file index vào báo cáo để đối chiếu với index PC0575
   (md5 giữa chừng PC0575 ghi: `a7c7c2325949c05d3396ab5371e42e64` — lệch thì DỪNG, báo ngay).
3. **Cùng bộ câu + cùng rubric:** bộ 50 câu lấy từ `docs/phieu-viec/ket-qua/lsu-quality-set.md`
   (JSON hoá như PC0575 đã làm), rubric `chinh_xac` 2.0 + `trich_dan` 1.0, thang 0–3/câu.
   Giữ nguyên cấu hình matcher hiện hành (kể cả ngưỡng `MIN_MATCH_SCORE=3.0`) — vé này ĐO,
   không sửa matcher; ghi nhận riêng số câu bị matcher loại như một phát hiện.
4. **Checkpoint từng câu + resume:** kết quả ghi dồn theo câu, mất điện/mất phiên chạy tiếp
   từ câu chưa đo. Không đo lại câu đã có kết quả trong cùng vé.

## Nhịp heartbeat (BẮT BUỘC)

- Mỗi **15 phút** append một dòng `` `ghi_chu`: <giờ> +07 — RAG x/50, <ghi chú ngắn> `` vào
  `trang-thai.md` mailbox này. Cấm im lặng quá 15 phút không mốc.

## Báo cáo

`docs/phieu-viec/ket-qua/lsu-quality-rag-home.md`:
- Tổng điểm /150, GPA, số câu đạt ≥2, số câu =3, 0 lỗi kỹ thuật hay không.
- Tách theo staging khớp/không khớp như báo cáo lane C-Agent để so trực tiếp.
- Thời gian từng câu (retrieval + tổng hợp) và tổng thời gian lane.
- Bằng chứng CPU-only + SHA index.
- Phát hiện matcher: số câu có cặp hỏi–đáp trong kho nhưng bị ngưỡng loại (nếu gặp).
