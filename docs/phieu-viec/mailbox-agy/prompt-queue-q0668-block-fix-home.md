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
