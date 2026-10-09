# VÉ: EVAL-NORMALIZE-FIX-HOME (sửa ca oan của thước đo: chuẩn hoá đáp án trước khi khớp thang chấm)

- Mã vé: `EVAL-NORMALIZE-FIX-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/eval-normalize-fix-home.md`
- Bối cảnh: báo cáo thí nghiệm ngữ cảnh tại máy công ty (`docs/phieu-viec/ket-qua/synth-context-topk-pc0575.md`, mục phân tích các câu giảm điểm) đã chỉ ra một nhóm câu mất điểm oan vì thước đo chứ không phải vì đáp án sai. Điển hình câu `Q0652`: mô hình trả lời đúng hoàn toàn nội dung phân biệt hai loại động cơ, nhưng viết số vòng quay trong cặp ký hiệu toán học dạng `$48384$` thay vì `48384`, khiến biểu thức khớp từ khoá của thang chấm không nhận ra và chấm 0 điểm. Đây là lỗi ở khâu so khớp của bộ chấm, làm méo mọi con số đo chất lượng từ trước tới nay.

## Việc phải làm

1. Tìm đúng khâu so khớp đáp án với thang chấm trong mã đo hiện hành. Bổ sung bước chuẩn hoá phía đáp án trước khi khớp: loại bỏ ký hiệu bọc toán học (dấu `$` và các ký hiệu tương tự), chuẩn hoá dấu phân cách nghìn và dấu thập phân trong con số, chuẩn hoá khoảng trắng thừa. Nguyên tắc: chuẩn hoá chỉ được thay đổi hình thức trình bày, không được thay đổi nội dung số học — hai con số khác nhau về giá trị vẫn phải không khớp sau chuẩn hoá.
2. Viết kiểm thử đơn vị cho bước chuẩn hoá, gồm cả ca dương tính (đáp án đúng bị oan vì định dạng thì sau chuẩn hoá phải khớp) và ca âm tính (đáp án sai về giá trị số thì sau chuẩn hoá vẫn không khớp).
3. Kiểm chứng không cần gọi mô hình: chấm lại toàn bộ các tệp dữ kiện đo đã có (ít nhất tệp của lượt sửa trích dẫn gần nhất và tệp của thí nghiệm ngữ cảnh tại máy công ty) bằng bộ chấm sau sửa. Báo cáo: tổng điểm trước và sau ở từng tệp, danh sách các câu đổi điểm kèm lý do đổi (ca oan được gỡ hay thay đổi khác), và xác nhận không có câu nào đổi điểm ngoài nhóm ca oan định dạng.
4. Ghi rõ trong báo cáo: từ nay các con số đo chất lượng phải được hiểu là đã qua chuẩn hoá này; các mốc lịch sử (1,31 tại máy nhà, 0,957 tại máy công ty) là số chưa chuẩn hoá và sẽ được điều phối đối chiếu lại khi cần.

## Rào cứng

- Chỉ sửa khâu chuẩn hoá của bộ chấm: không đổi nội dung thang chấm, không đổi đáp án mẫu, không đổi bộ đề. Không ghi vào chỉ mục production. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần.
