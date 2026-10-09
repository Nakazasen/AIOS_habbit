# VÉ: TEST-SUITE-CONFIRM-HOME (chạy lại toàn bộ bộ kiểm thử tại đầu nhánh hiện tại để xác nhận tín hiệu sạch còn đứng vững)

- Mã vé: `TEST-SUITE-CONFIRM-HOME`
- Role gợi ý: DEFAULT (opencode — thợ phụ tạm thời, máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/test-suite-confirm-home.md`
- Bối cảnh: vé `TEST-SUITE-HYGIENE-HOME` vừa đưa toàn bộ bộ kiểm thử về 0 ca hỏng / 0 lỗi tại thời điểm chốt của vé đó. Sau đó nhánh đã nhận thêm các thay đổi thật (sửa bộ phân loại dạng câu hỏi và nhiều commit tài liệu trong sáng 09/10). Vé này là một lượt kiểm chứng độc lập tại đầu nhánh hiện tại: tín hiệu sạch còn đứng vững hay đã xuất hiện ca đỏ mới — để mọi ca đỏ từ nay đều được coi là hồi quy thật và xử lý ngay.

## Việc phải làm

1. Ghi rõ mã commit đầu nhánh tại thời điểm chạy.
2. Chạy toàn bộ bộ kiểm thử một lượt duy nhất theo đúng cổng của repo, ghi kết quả tổng: số đạt, số hỏng, số bỏ qua, số lỗi, và thời gian chạy.
3. Nếu có bất kỳ ca hỏng hay lỗi nào: liệt kê đầy đủ tên ca và thông báo lỗi gốc, kèm phân loại sơ bộ (giống các ca môi trường đã biết hay ca mới chưa từng thấy). **Không sửa mã, không sửa kiểm thử trong vé này** — chỉ chạy, ghi và phân loại; phần xử lý do điều phối quyết định sau.
4. Đối chiếu số bỏ qua với mốc của vé dọn dẹp (66 ca bỏ qua có điều kiện): nếu số bỏ qua thay đổi, giải thích được theo điều kiện máy hay không.

## Rào cứng

- Chỉ chạy và báo cáo: không sửa mã nguồn, không sửa kiểm thử, không ghi chỉ mục (băm chỉ mục trước/sau phải khớp nếu có đọc tới). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần trong lúc lượt chạy dài đang diễn ra (ghi mốc bắt đầu, mốc giữa nếu cần, mốc kết thúc kèm kết quả).
