# Vé: KNOWLEDGE-DIGEST-PROVIDER-SWITCH — đổi provider cho batch tóm tắt (cầu nối Gemini chết từ 02:03)

Lane: [NHÀ] OMP chạy trên máy nhà h410asrock.
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

- Cầu nối Gemini Web (`127.0.0.1:8585`) trả HTTP 405/502 từ **02:03** (~5 giờ), batch tóm tắt kẹt ở checkpoint 180/889. Vé R1 chỉ resume khi cầu nối khỏe — hiện vẫn chết.
- Nakazasen Router hiện **KHÔNG dùng được**: khóa cloud lỗi `unknown_error` (OMP đã thử tối 2/10 trong vé LLM-ENABLE-DO-NHA-R1, phải né sang cầu nối theo thứ tự vé).
- User quyết 2026-10-03 ~07:15 +07: **đổi đường khác, chạy tiếp ngay**.

## Thứ tự thử (rẻ trước, đắt sau)

1. **Probe cầu nối Gemini (30 giây, rẻ nhất):** `GET http://127.0.0.1:8585/health` → `direct_ready`? + 1 câu tóm tắt thử đúng schema. Nếu sống → resume R1 như cũ, đóng vé này (ghi rõ trong báo cáo là cầu nối tự hồi).
2. **Chẩn đoán + sửa khóa cloud của Router:** mở log/config xem lỗi `unknown_error` tối 2/10 nằm ở đâu (env/key/account); thử refresh/nhập lại key; probe 1 câu tóm tắt qua `RouterSynthesisProvider`. Ghi rõ nguyên nhân gốc vào báo cáo (key hết hạn? sai env? account bị khóa?).
3. **Đổi batch sang provider sống:** sửa config/env của `C:/tmp/knowledge-digest-home/run_digest_home.py` sang provider vừa probe OK; **resume từ checkpoint hiện tại, không làm lại từ đầu**; giữ nguyên rào trung thực và nhãn bản thảo.
4. Nếu sau 1 giờ chẩn đoán cả hai đường đều chết: ghi đúng tình trạng vào `ghi_chu`, đặt mailbox `cho-muse`, báo lại — không fake số, không quay vòng gọi lỗi liên tục.

## Rào trung thực (giữ nguyên từ vé gốc)

- Sổ tay là **bản thảo do LLM soạn** — dòng đầu file: "Bản thảo — chưa qua chuyên gia duyệt".
- Không gắn nhãn `kiến thức đã được đào tạo bổ sung`; không nhập sổ tay vào kho tri thức; không nhập vào luồng trả lời chính của app.
- DB chính và index production **chỉ đọc** (đo SHA trước/sau: `C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`).
- Cấm quá 45 phút không ghi log tiến độ.

## Tiêu chí ĐẠT

- Batch chạy tiếp được trên provider mới (hoặc cầu nối đã hồi): sổ tay phủ 100% document đã đếm (889 mục), manifest SHA-256 hợp lệ.
- Probe hỏi đáp so sánh lane sổ tay vs RAG như vé gốc (số liệu cụ thể từng câu).
- SHA index production không đổi; không bản thảo nào lọt vào kho/luồng trả lời chính.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
