# VÉ: TEST-STALE-GUARDS-HOME (dọn các test bảo vệ chuỗi mã nguồn đã lạc hậu + phân loại 2 ca lệch hành vi truy xuất)

- Mã vé: `TEST-STALE-GUARDS-HOME`
- Role gợi ý: DEFAULT (OMP — thợ phụ, máy nhà)
- Báo cáo: `docs/phieu-viec/ket-qua/test-stale-guards-home.md`
- Căn cứ: các lượt chạy toàn bộ test gần đây liên tục có một nhóm ca đỏ do test còn khẳng định chuỗi mã nguồn cũ đã bị thay bởi các thay đổi thiết kế có chủ đích của những vé trước (mẫu giống hệt vé `WORKER-TESTS-DIAG-HOME` đã xử lý 3 ca). Nhóm ca đỏ triền miên này che mất tín hiệu hồi quy thật. Vé này dọn đúng nhóm đó và phân loại nốt 2 ca lệch hành vi truy xuất còn treo.

## Việc phải làm

1. **Ba ca bảo vệ chuỗi mã nguồn:** các ca trong nhóm chủ sở hữu lựa chọn nguồn và ca thư viện lớn không chặn chat (theo phân loại ở báo cáo vé `SYNTH-DEEPSEEK-PROTOCOL-HOME` mục 6, tự tái hiện để lấy tên chính xác) đang đòi một dòng mã nguồn cụ thể không còn tồn tại sau thay đổi thiết kế đã được duyệt. Với từng ca: truy commit đã thay dòng đó, xác nhận hành vi mới là chủ đích của vé đó (đọc báo cáo/verdict của vé liên quan trong kho), rồi cập nhật test sang khẳng định HÀNH VI hiện tại (kết quả/quan hệ đầu vào–đầu ra) thay vì khẳng định chuỗi mã nguồn. **Nếu truy ra hành vi mới thực ra là hồi quy ngoài ý muốn thì DỪNG ở chẩn đoán, không sửa test để che hồi quy.**
2. **Hai ca truy xuất tối ưu:** phân loại lệch hành vi ở nhóm test vòng lặp truy xuất (preload/prefilter) sau các thay đổi truy xuất đã có trên nhánh: lỗi ở test (giả định cũ), chủ đích thiết kế, hay hồi quy thật. Nếu là test/chủ đích thì sửa test tương tự mục 1; nếu là hồi quy thật thì chỉ chẩn đoán + đề xuất, không tự đổi hành vi truy xuất.
3. Chạy lại toàn bộ các tệp test đã đụng + các tệp lân cận liên quan, ghi kết quả trước/sau từng ca. Không chạy lại toàn bộ suite trừ khi thay đổi lan rộng (khai rõ nếu có).

## Rào cứng

- Chỉ sửa test; không đổi mã chạy thật trong vé này (trừ khi phát hiện hồi quy thật — khi đó dừng ở chẩn đoán). Không ghi chỉ mục. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần. Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
