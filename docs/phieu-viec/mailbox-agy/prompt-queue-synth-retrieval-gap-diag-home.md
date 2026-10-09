# VÉ: SYNTH-RETRIEVAL-GAP-DIAG-HOME (chẩn đoán khoảng trống truy hồi của nhóm câu bị mất điểm vì thiếu bằng chứng)

- Mã vé: `SYNTH-RETRIEVAL-GAP-DIAG-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-retrieval-gap-diag-home.md`
- Bối cảnh: con số chất lượng quyết định sau đo lặp hai lượt là 68,84 trên 150 (điểm trung bình 1,377), ổn định cao giữa hai lượt (lệch đúng 2,0 điểm, không câu nào giảm). Khoảng cách tới ngưỡng go-live 1,5 là khoảng 6,2 điểm mỗi lượt — một khoảng cách cấu trúc, không phải nhiễu đo. Thành phần lớn nhất của khoảng cách này đã được xác định: 8 câu bị cổng kiểm chứng chặn đóng kín nên nhận 0 điểm (7 câu chẩn đoán ngắn `Q0620`, `Q0668`, `Q0824`, `Q0843`, `Q0849`, `Q0850`, `Q1034` và câu `Q0828`). Vé rà cổng đã chứng minh cổng chặn đúng vì bằng chứng truy hồi được thiếu thật. Câu hỏi còn mở — và là câu hỏi quyết định hướng đi tiếp theo — là: dữ liệu trả lời được các câu đó có tồn tại trong chỉ mục hay không, và nếu có thì khâu truy hồi nào làm mất nó.

## Việc phải làm (chỉ chẩn đoán và phân loại — không sửa mã ở vé này)

Với từng câu trong nhóm 8 câu bị chặn, lập hồ sơ chẩn đoán đầy đủ:

1. **Sự tồn tại trong chỉ mục:** tìm trực tiếp trong chỉ mục production (chỉ đọc) các mảnh chứa dữ kiện đích của câu hỏi (mã lỗi, mã báo cáo, con số, tên bảng mà đáp án mẫu yêu cầu). Kết luận một trong ba: dữ kiện có trong chỉ mục / có một phần / hoàn toàn không có.
2. **Hành trình truy hồi:** chạy đường truy hồi của chính câu hỏi đó và ghi lại: mảnh chứa dữ kiện đích (nếu có) xuất hiện ở hạng mấy trong kết quả thô; nó có qua được khâu lọc theo khối tri thức, khâu sắp xếp lại, và cửa sổ ngữ cảnh cuối cùng hay không; khâu cụ thể nào đã loại nó ra, kèm con số (điểm truy hồi, hạng trước và sau mỗi khâu).
3. **Phân loại nguyên nhân** cho từng câu vào đúng một nhóm: (a) dữ liệu không có trong kho — vấn đề nguồn dữ liệu, không phải mã; (b) dữ kiện có trong kho nhưng truy hồi thô không xếp hạng đủ cao; (c) dữ kiện qua được truy hồi thô nhưng bị khâu lọc hoặc cửa sổ ngữ cảnh loại; (d) nhóm khác, mô tả cụ thể.
4. Tổng hợp cuối báo cáo: bảng phân loại 8 câu; ước tính điểm có thể lấy lại được cho từng nhóm nguyên nhân nếu xử lý đúng nhóm đó; đề xuất hướng xử lý cho nhóm lớn nhất, kèm mức độ chắc chắn. Nếu nhóm (a) chiếm đa số thì kết luận phải nói thẳng: trần điểm hiện tại bị giới hạn bởi dữ liệu, các vé sửa mã tiếp theo không có tác dụng cho nhóm này.

## Điều kiện đo và an toàn

- Toàn bộ chẩn đoán chạy chỉ đọc trên chỉ mục production, chỉ dùng bộ xử lý trung tâm. Ghi băm của chỉ mục trước và sau để chứng minh không thay đổi.
- Ghi rõ mã commit đang chạy trong báo cáo.

## Rào cứng

- Vé này CHỈ chẩn đoán: không sửa mã, không hạ ngưỡng cổng kiểm chứng, không ghi vào chỉ mục. Mọi hướng sửa sẽ thành vé riêng sau khi điều phối duyệt báo cáo chẩn đoán.
- Không đổi bộ đề và thang chấm. Không merge `main`.
- Kích thước tệp trong báo cáo phải đo trên bản đã nộp vào kho sau khi commit.
- Mốc tiến độ tối thiểu 15 phút/lần.
