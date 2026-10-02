# Vé: KNOWLEDGE-DIGEST-HOME-R1 — resume batch tóm tắt từ checkpoint (92/889) sau khi cầu nối hết HTTP 405

Lane: [NHÀ] OMP resume trên máy nhà qua cầu nối Gemini Web.
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh

- Vé KNOWLEDGE-DIGEST-HOME bị dừng giữa chừng: batch tóm tắt dừng ở **92/889** document vì cầu nối Gemini Web trả **HTTP 405 từ 02:03** (sidecar đổi thành 502 sau khi làm mới BL thất bại). Muse verdict **CHƯA ĐẠT** (báo cáo `56838d9`).
- Checkpoint giữ nguyên 92 mục tại `C:/tmp/knowledge-digest-home/` — resume, không làm lại từ đầu.
- Lỗi 405 là rào ngoài (phía cầu nối/Google), không phải lỗi code vé.

## Cổng kiểm tra cầu nối trước khi resume (bắt buộc)

1. `GET http://127.0.0.1:8585/health` phải trả `direct_ready`.
2. Chạy 1 lượt tóm tắt thử trên 1 document (ngoài batch): phải trả JSON đúng schema trong <60 giây.
3. Nếu health chưa đạt: chờ và thử lại theo backoff (5, 15, 30, 60 phút); **không quay vòng gọi lỗi liên tục**. Nếu sau 2 giờ vẫn 405/502: ghi đúng tình trạng vào `ghi_chu` của mailbox, dừng phiên này (watcher sẽ mở lại vé ở lần tới khi cầu nối khỏe), không fake số.

## Việc OMP làm [NHÀ]

1. Khi cầu nối khỏe: chạy lại `C:/tmp/knowledge-digest-home/run_digest_home.py`. Checkpoint giữ 92 mục. **Cấm quá 45 phút không ghi log tiến độ** (ghi mốc số mục đã xong).
2. Khi `done=889`: script xuất `so_tay_tri_thuc.md` + manifest SHA-256. Kiểm tra bao phủ: số mục trong sổ tay = 889 (số document đã đếm).
3. Chạy probe hỏi đáp trên bộ benchmark 10–15 câu hỏi tổng quan (từ vé gốc): nạp sổ tay vào context Gemini Web → ghi đáp án + thời gian từng câu; chạy cùng bộ câu qua lane RAG hiện tại (chỉ đọc) → so sánh thời gian + độ bao quát theo rubric (đủ ý chính / thiếu ý / sai), ghi số liệu cụ thể từng câu, không nói chung chung.
4. DB chính và index production **chỉ đọc** (đo SHA trước/sau: `C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`).
5. Báo cáo cập nhật vào `docs/phieu-viec/ket-qua/knowledge-digest-home.md` + đặt mailbox `xong-cho-duyet`.

## Rào trung thực (giữ nguyên)

- Sổ tay là **bản thảo do LLM soạn** — dòng đầu file: "Bản thảo — chưa qua chuyên gia duyệt".
- Không gắn nhãn `kiến thức đã được đào tạo bổ sung`; không nhập sổ tay vào kho tri thức; không nhập vào luồng trả lời chính của app.
- Không lưu vết LLM nào trong kho (không ghi nguồn LLM vào DB).
- Báo trung thực số đã xong + kế hoạch resume; không fake số.

## Tiêu chí ĐẠT

- Sổ tay bao phủ 100% document đã đếm (889 mục); manifest SHA-256 hợp lệ.
- Probe trên câu hỏi tổng quan: lane sổ tay **nhanh hơn** RAG và **bao quát hơn** theo rubric (báo cáo ghi số liệu cụ thể từng câu).
- SHA index production không đổi; không bản thảo nào lọt vào kho/luồng trả lời chính.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
