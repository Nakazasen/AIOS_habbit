# Vé: UX-E2E-APP-R2 — verify fix cho-muse + chạy nốt các mục E2E còn lại

Lane: [NHÀ] OMP kiểm thử trên app thật (máy nhà h410asrock). Không merge `main`; không ghi index production; OMP chỉ kiểm thử, không sửa code sản phẩm.

## Bối cảnh

Vé UX-E2E-APP dừng ở mục (a) theo luật vé (FAIL → dừng, báo `cho-muse`), báo cáo `docs/phieu-viec/ket-qua/ux-e2e-app.md`:

- (a) FAIL: "vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12" → app chỉ lưu quy tắc `CB-D0EDE6` với tên thông số rác `trên`, không vẽ biểu đồ (router chat-first không có ý định "vẽ biểu đồ" nên phần chart bị bỏ).
- (b) PASS. (c)–(h) chưa chạy.

Muse đã code fix trên VM (commit `58d1245`, đã push lên nhánh):

1. Router thêm ý định `ve_bieu_do` ("vẽ biểu đồ") → câu gộp chart + ngưỡng chạy ĐỦ cả 2 nhánh, gộp trong một câu trả lời. ("biểu đồ gửi mail" vẫn thuộc lệnh cấu hình, không bị nhầm.)
2. Nhánh chart trong router chạy đúng logic JIG (`_quyet_dinh_ve_bieu_do`), đọc dữ liệu từ phiên LSU gate; ảnh PNG nhúng data-URI trong câu trả lời gộp.
3. Lệnh ngưỡng thiếu tên thông số hợp lệ ("đặt ngưỡng trên 12") → app HỎI LẠI tên thông số, KHÔNG lưu quy tắc rác.

Báo cáo Phase A: `docs/phieu-viec/ket-qua/ux-e2e-app-fixa.md`. Test vé mới: 39/39 pass trên VM.

## Việc OMP làm [NHÀ]

1. Pull nhánh `phieu-viec/rag-fix1` mới nhất. Kiểm cổng: commit `58d1245` phải là tổ tiên của HEAD (chưa tới → đợi pull lại, không tự code thay).
2. Mở app thật cổng riêng (như vé trước: 8515, đúng biến môi trường của `RUN_AIOS_WORKSPACE_CHAT.bat`, không đụng app user 8501). Ghi SHA index production trước/sau.
3. Chạy lại mục (a): gửi đúng câu "vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12". Tiêu chí PASS (đúng kỳ vọng sau fix):
   - Câu trả lời gộp ĐỦ 2 phần có tiêu đề: "Vẽ biểu đồ" + "Cảnh báo ngưỡng".
   - Phần "Vẽ biểu đồ": vì chưa có dữ liệu LSU gate trong phiên thử → thông điệp hướng dẫn tiếng Việt (giống khi chạy câu vẽ biểu đồ một mình), KHÔNG lỗi, KHÔNG im lặng.
   - Phần "Cảnh báo ngưỡng": HỎI LẠI tên thông số (không lưu quy tắc). Kiểm `local_cases/threshold_rules.json` KHÔNG có quy tắc mới tên `trên`.
   - PASS = cả 3 điểm trên đúng. (Không đòi vẽ được biểu đồ thật khi chưa có dữ liệu — đó là việc của mục khác.)
4. Kiểm riêng (không regression):
   - "vẽ biểu đồ bowskew JIG-01" một mình → vẫn ra thông điệp hướng dẫn như vé trước.
   - "đặt ngưỡng trên 12" một mình → hỏi lại tên thông số, không lưu quy tắc.
   - "đặt ngưỡng nhiệt độ 80" → vẫn lưu quy tắc bình thường.
5. Chạy tiếp các mục (c)–(h) của vé gốc còn dang dở, cùng tiêu chí như vé gốc:
   - c. Lane AI tự chọn (không còn selectbox đổi tay); ngắt cầu nối Gemini thử → lane tự rơi về lane khác, app không báo lỗi ảo.
   - d. Dưới một câu trả lời assistant có hàng thumbs up/down; bấm down → bắt nhập lý do → file `local_cases/answer_feedback.jsonl` có dòng mới.
   - e. Dán dòng log JIG có 1 điểm xấu đơn lẻ → thẻ hiện "Cận biên", có dòng "Xu hướng SMA(20)", KHÔNG đề xuất gửi email cảnh báo.
   - f. Dán 3–4 dòng log xấu liên tiếp → thẻ hiện "Vi phạm" + "Phán đoán nguyên nhân (giả thuyết)" + "Đề xuất điều tra".
   - g. Mở biểu đồ SPC → thấy đường SMA(20) nét đứt tím có nhãn.
   - h. Sidebar: mở "Công cụ nâng cao" (LSU gate) rồi bấm "Hỏi tài liệu" → gate tự đóng, radio hiển thị đúng mục đang chọn.
   - Ghi thời gian chạy mỗi kịch bản, chụp màn hình mục (g), (e), (f) nếu được.
6. Dọn dẹp như vé trước (xóa quy tắc test trong `threshold_rules.json`, tắt app thử 8515, `git status` sạch).

## Tiêu chí ĐẠT

- Mục (a) chạy lại PASS theo đúng 3 điểm ở bước 3 + các kiểm riêng ở bước 4 đúng + (c)–(h) PASS.
- SHA index production không đổi; `git status` sạch; không ghi kho log JIG / `answer_feedback.jsonl` ngoài mục đích test (dọn sau test).
- Báo cáo `docs/phieu-viec/ket-qua/ux-e2e-app-r2.md` + đặt `xong-cho-duyet` (ghi đường dẫn báo cáo + commit mailbox).

## Tiêu chí CHƯA ĐẠT

- Bất kỳ mục nào FAIL → ghi rõ log nguyên văn, dừng vé, báo `cho-muse` theo luật.
