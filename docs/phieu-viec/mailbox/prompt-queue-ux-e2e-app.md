# Vé: UX-E2E-APP — kiểm thử đầu-cuối app thật sau loạt UX mới

Lane: [NHÀ] OMP chạy E2E trên app thật (máy nhà h410asrock). Không merge `main`; không ghi index production.

## Bối cảnh

Đêm 2026-10-03 Muse code xong trên VM một loạt tính năng UX (commit `846713e`, `07913b1`, `82698a5`, `928e242` trên nhánh `phieu-viec/rag-fix1`):
multi-intent, dán log/CSV vẽ biểu đồ inline, lane AI tự động, nhãn trung thực dải giới hạn,
feedback câu trả lời trên khung chat, SMA(20) + cảnh báo theo xu hướng, engine sửa docx/pptx/md có backup.
Cần OMP chạy E2E trên app thật để xác nhận chạy được, trước khi coi là xong.

## Việc OMP làm [NHÀ]

1. Pull nhánh `phieu-viec/rag-fix1` mới nhất, chạy app Streamlit thật.
2. Kịch bản E2E (ghi PASS/FAIL từng mục):
   a. Chat 1 câu 2–3 ý định (ví dụ: "vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12") → ra đủ kết quả trong một câu trả lời.
   b. Dán đoạn CSV/log thật → phân tích + biểu đồ hiện ngay trong câu trả lời.
   c. Lane AI tự chọn (không còn selectbox đổi tay); ngắt cầu nối Gemini thử → lane tự rơi về lane khác, app không báo lỗi ảo.
   d. Dưới một câu trả lời assistant có hàng thumbs up/down; bấm down → bắt nhập lý do → file `local_cases/answer_feedback.jsonl` có dòng mới.
   e. Dán dòng log JIG có 1 điểm xấu đơn lẻ → thẻ hiện "Cận biên", có dòng "Xu hướng SMA(20)", KHÔNG đề xuất gửi email cảnh báo.
   f. Dán 3–4 dòng log xấu liên tiếp → thẻ hiện "Vi phạm" + "Phán đoán nguyên nhân (giả thuyết)" + "Đề xuất điều tra".
   g. Mở biểu đồ SPC → thấy đường SMA(20) nét đứt tím có nhãn.
   h. Sidebar: mở "Công cụ nâng cao" (LSU gate) rồi bấm "Hỏi tài liệu" → gate tự đóng, radio hiển thị đúng mục đang chọn.
3. Ghi thời gian chạy mỗi kịch bản, chụp màn hình mục (g), (e), (f) nếu được.

## Tiêu chí ĐẠT

- 8/8 mục PASS trên app thật; mục nào FAIL ghi rõ log và dừng vé, báo `cho-muse`.
- Không ghi index production; SHA index nhà không đổi trước/sau.
- Báo cáo `docs/phieu-viec/ket-qua/ux-e2e-app.md` + `xong-cho-duyet`.

## Tiêu chí CHƯA ĐẠT

- Bất kỳ mục nào FAIL, hoặc app crash/mất kết nối lane mà không tự hồi phục.
