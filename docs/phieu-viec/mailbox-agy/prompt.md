# VÉ: SYNTH-CLAIMBUDGET-DIAG-HOME (điều tra ngân sách luận điểm — nút thắt validated của mọi model)

- Mã vé: `SYNTH-CLAIMBUDGET-DIAG-HOME`
- Role gợi ý: PLAN/DEFAULT
- Máy: nhà h410asrock (agy — thợ chính, chỉ đọc + đo lại có kiểm soát, CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-claimbudget-diag-home.md`
- Căn cứ: qua 4 lượt đo trên cùng bộ 50 câu (pool free, từng model free, DeepSeek trả phí), tỉ lệ qua kiểm định trích dẫn (validated) luôn rất thấp (0–3/50) bất kể năng lực model — trong khi đáp án mẫu cho thấy có ca model trả lời ĐÚNG và giàu dữ kiện nhưng bị bộ kiểm định đánh trượt vì `provider_answer_claim_budget_exceeded` (số dòng luận điểm vượt ngân sách cho phép so với số đoạn bằng chứng). Giả thuyết cần kiểm chứng: ngân sách luận điểm (claim budget) của bộ kiểm định đang là nút thắt chính của validated — nếu đúng, đây là đòn bẩy chất lượng lớn nhất còn lại của đường tổng hợp, lớn hơn việc đổi model.

## Việc phải làm

1. **Đếm phân rã từ các file kết quả thô đã có** (các lượt đo pool/DeepSeek trên máy nhà): trong các câu bị fallback dù provider có sinh đáp án, bao nhiêu ca do `claim_budget_exceeded`, bao nhiêu do lý do khác (liệt kê đủ các mã lý do + số ca). Nộp bảng phân rã.
2. **Đọc cơ chế claim budget trong code:** ngân sách được tính thế nào (theo số đoạn bằng chứng? theo ký tự?), ngưỡng hiện tại, và nó bảo vệ khỏi rủi ro gì (luận điểm không có bằng chứng chống lưng). Nêu rõ đánh đổi nếu nới.
3. **Đo thử có kiểm soát (nếu mục 1 xác nhận claim budget là nhóm lớn nhất):** chạy lại đúng bộ 50 câu với MỘT biến thể ngân sách (nới theo hệ số rõ ràng, cấu hình tạm thời, khôi phục sau khi đo) trên cùng model chính hiện tại (Ling 3.1 free) — so sánh validated/GPA/fallback trước–sau. Nếu nới ngân sách làm validated tăng nhưng xuất hiện luận điểm không bằng chứng (đọc tay 5 đáp án mẫu bị thay đổi), phải khai rõ.
4. Kết luận + đề xuất dứt khoát: giữ nguyên / nới lên mức cụ thể / thiết kế lại cách tính ngân sách — kèm số đo. Vé này CHỈ chẩn đoán + đo thử tạm thời, KHÔNG áp thay đổi vĩnh viễn vào cấu hình chính.

## Rào cứng

- Không ghi chỉ mục (kiểm băm trước/sau các lượt đo). Không merge `main`. Cấu hình tạm phải khôi phục nguyên trạng sau đo và xác nhận trong báo cáo.
- Trần chi phí: lượt đo dùng model free; nếu cần đo biến thể trên DeepSeek thì trần $0,20. Không in bất kỳ ký tự nào của key.
- Mốc tiến độ tối thiểu 15 phút/lần. Mọi con số phải tái lập được từ file kết quả đính kèm (nộp file rows của lượt đo mới vào kho).

## DỮ KIỆN BỔ SUNG TỪ AUDIT ROWS (điều phối bổ sung 23:28 08/10)

- Lượt đo DeepSeek: **38/50 câu có số lần gọi provider = 0** (10 câu gọi 1 lần, 2 câu gọi 2 lần) — trong khi 43 câu ghi chế độ fallback. Tức là phần lớn ca fallback xảy ra ở tầng QUYẾT ĐỊNH KHÔNG GỌI provider (cổng độ phủ bằng chứng/coverage gate), trước cả khi model sinh đáp án — vé này phải phân rã cả hai tầng: (a) vì sao không được gọi (mã lý do từng câu), (b) trong số câu ĐÃ gọi mà vẫn trượt kiểm định thì claim budget chiếm bao nhiêu. Không kết luận nút thắt chỉ là claim budget khi chưa có bảng phân rã hai tầng này.
- Cả 3 câu validated của lượt DeepSeek đều mang cờ không-trích-dẫn trong file thô — kiểm tra thêm cờ này có phản ánh đúng đáp án thật không khi làm phân rã.
