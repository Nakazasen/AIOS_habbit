# VÉ: Q0668-BLOCK-FIX-HOME (khép Mục 0.2: sửa lệch khối tri thức khiến giao diện không thấy tệp đích của Q0668)

- Mã vé: `Q0668-BLOCK-FIX-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/q0668-block-fix-home.md`
- Điều kiện bốc: sau khi `MISSING5-EMBED-COMPLETE-HOME` khép.

## Căn cứ (vé chẩn đoán MISSING5-RETRIEVAL-DIAG-HOME, điều phối đã kiểm chứng)

Đường đo đạt 1,5 cho `Q0668` vì đo trên chỉ mục hợp nhất `tri_thuc` (tệp `3V2ND19040...xlsx` có 151 mảnh, hạng 1). Đường giao diện thất bại vì tệp đích được phân loại chỉ thuộc khối `dieu_tra_loi` (0 mảnh trong khối `lsu`), trong khi kịch bản giao diện ép chọn khối `lsu` → bộ lọc khối chặn đứng tệp đích. Đây là gốc rễ còn lại của Mục 0.2.

## Việc phải làm

1. Chọn và triển khai cách sửa ở tầng phân loại/định tuyến (ví dụ cho phép tệp thuộc đồng thời khối `lsu` và `dieu_tra_loi`, hoặc đồng bộ tệp đích vào khối `lsu`), theo đúng mô hình tài liệu user đã chốt: tài liệu đã index là hỏi đáp được ngay bằng chọn khối tri thức, không hiển thị số liệu mâu thuẫn. Ghi rõ cách đã chọn và lý do; không phá phân loại của các tệp khác (có kiểm thử hồi quy cho `index_domain`).
2. Nếu cách sửa cần ghi chỉ mục: sao lưu trước + toàn vẹn, chỉ ghi đúng phần liên quan, ghi số đo trước/sau.
3. Nghiệm thu giao diện thật: phiên MỚI, chọn khối theo đúng cách người dùng cuối vẫn dùng, hỏi lại `Q0668`; đáp án phải trích đúng tệp đích và có bộ số nominal/giới hạn; ảnh chứa trọn thân đáp án. Đo lại `Q0668` bằng đường đo để xác nhận không thụt lùi.

## Ràng buộc

- Không đổi ngưỡng cổng. Không dùng cách "sửa kịch bản test cho qua" thay cho sửa phân loại/định tuyến thật.
- Mốc tiến độ tối thiểu 15 phút/lần kèm điểm kiểm.

## Bổ sung phạm vi của điều phối (2026-10-11, từ verdict đợt quét B1)

Đợt quét `DESKTOP-KNOWLEDGE-BLOCK-QA-HOME` phát hiện thêm một lệch đồng bộ cùng họ với lệch khối của Q0668, xử lý luôn trong vé này:

- Nhãn chip khối trên giao diện ghi "Tự động (889 tài liệu)" trong khi chỉ mục hợp nhất đang dùng có 894 tài liệu sau đợt nạp missing5.
- Năm tệp nguồn mới nạp (nhóm LSU) chỉ tồn tại trong chỉ mục hợp nhất `tri_thuc`, chưa có trong các bộ sưu tập theo khối — vé chẩn đoán đã đo khối `lsu` có 0 mảnh của các tệp này. Người dùng chọn khối LSU trên giao diện vì thế không bao giờ chạm được dữ liệu mới nạp.

Yêu cầu bổ sung: đồng bộ 5 tệp mới vào đúng bộ sưu tập theo khối của chúng (kèm đủ vector theo quy chuẩn như vé nhúng bổ sung), bảo đảm số đếm tài liệu hiển thị trên chip khối khớp với dữ liệu thật của từng khối sau đồng bộ, và nghiệm thu bằng một câu hỏi giao diện chọn khối LSU có trích đúng một tệp mới. Nếu cách sửa phân loại ở phần chính của vé đã bao phủ việc này thì ghi rõ trong báo cáo, không làm hai lần.
