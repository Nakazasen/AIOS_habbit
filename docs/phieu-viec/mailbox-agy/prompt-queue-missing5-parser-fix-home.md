# VÉ: MISSING5-PARSER-FIX-HOME (sửa bộ trích xuất PPTX bỏ sót ghi chú diễn giả + bộ chia mảnh CSV hàng rộng, nạp lại 2 tệp)

- Mã vé: `MISSING5-PARSER-FIX-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/missing5-parser-fix-home.md`
- Điều kiện bốc: sau khi `WATCHER-ESCALATE-FIX-HOME` khép.

## Căn cứ (đã kiểm chứng độc lập bởi điều phối qua vé chẩn đoán MISSING5-RETRIEVAL-DIAG-HOME)

1. Câu `Q0620`: số liệu đích (25,42% → 49,49%, BOWSKEW 4 BEAM, tháng 03/2026) nằm trong ghi chú diễn giả của slide 1 (phần `notesSlides`), bộ trích xuất PPTX hiện hành chỉ đọc phần thân slide nên dữ liệu chưa từng vào chỉ mục.
2. Câu `Q0824`: các dòng của `2026_08_UnitTest.csv` dài ~5.000 ký tự; bộ chia mảnh cắt lát ~1.000 ký tự không kèm tiêu đề cột nên mã serial và các cột phán định `Judge:*` bị tách sang các mảnh khác nhau, không mảnh nào tự trả lời được.

## Việc phải làm

1. Sửa bộ trích xuất PPTX: đưa nội dung ghi chú diễn giả vào văn bản của slide tương ứng. Có kiểm thử đơn vị: trích xuất tệp mẫu phải chứa chuỗi số liệu trong ghi chú; không đổi hành vi với slide không có ghi chú.
2. Sửa bộ chia mảnh cho CSV hàng rộng: mỗi mảnh con phải giữ được liên kết tiêu đề–dòng (lặp lại tiền tố tiêu đề cột hoặc cơ chế tương đương), sao cho một mảnh chứa serial phải chứa luôn các cột phán định của chính dòng đó. Có kiểm thử đơn vị trên dòng dài ~5.000 ký tự. Không đổi hành vi với CSV hàng ngắn.
3. Nạp lại đúng 2 tệp (`AI cảnh báo lỗi LSU.pptx`, `2026_08_UnitTest.csv`) theo quy trình chuẩn: sao lưu trước + toàn vẹn, chạy thử không ghi, nạp qua kho thử có điểm kiểm, hợp nhất; các mảnh mới phải có đủ vector như quy chuẩn (100% mảnh có thể truy hồi). Ghi rõ số mảnh/vector trước–sau.
4. Đo lại đúng 2 câu `Q0620`, `Q0824` bằng đường đo hiện hành và nộp tệp rows; nghiệm thu giao diện 2 câu này trong phiên mới (ảnh chứa trọn thân đáp án). Không đổi ngưỡng cổng, không đổi bộ đề/thang chấm, không sửa hàm chấm để che artefact.

## Ràng buộc

- Chỉ ghi chỉ mục ở bước nạp lại 2 tệp; ngoài ra không đụng production. Giữ bản sao lưu trước nạp cho tới verdict.
- Mốc tiến độ tối thiểu 15 phút/lần kèm điểm kiểm. Mọi con số phải truy được về tệp dữ kiện đã commit.
