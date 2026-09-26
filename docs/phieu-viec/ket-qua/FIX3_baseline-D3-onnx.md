# Mức chuẩn D3 — ONNX fp32 trên toàn bộ tập tài liệu (chỉ đọc)

Ngày chạy: 2026-09-26 16:26 +07. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.

- Mã nguồn tại lúc chạy: `7da79aeb16e5b202b6528758358988cadec562a0`.
- Mã lượt PyTorch tham chiếu: `484ac76e72fefb0d1e3b37f2a18102d7d2e38646`.
- Index: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`.
- Mô hình: BGE-M3 ONNX fp32, phiên bản `5617a9f61b028005a4858fdac845db406aefb181`, chạy CPU; dấu vân tay `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`, SHA-256 mô hình `9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
- Cấu hình: `BGE_BACKEND=onnx`, `AIOS_RAG_V2_SUMMARY_FIRST=1`, `AIOS_RAG_V2_SUMMARY_PROVENANCE=1`; `index_read_only=True`, `ensure_embeddings_on_open=False`; mỗi câu có giới hạn 180 giây. Giá trị `onnx_int8` trong trường trạng thái sẵn sàng là tên nội bộ cũ; thư mục mô hình và dấu vân tay là bản ONNX fp32.

## Kết quả

Tiến trình ONNX khởi tạo thành công trong **27,21 giây** theo trạng thái sẵn sàng (27,46 giây theo đồng hồ phía gọi), dưới ngưỡng dừng 300 giây. Chạy đủ 6/6 câu; không câu nào quá thời gian chờ hoặc từ chối trả lời. Cả sáu câu đi theo đường `hybrid`; B1–B5 dùng chế độ `full`, H3 dùng chế độ `focused`.

| Câu | Chế độ | Thời gian ONNX (giây) | Thời gian PyTorch `484ac76` (giây) | Chênh lệch ONNX − PyTorch (giây) | Đối chiếu đáp án |
| --- | --- | ---: | ---: | ---: | --- |
| B1 | `full` | 2,165 | 101,61 | −99,445 | **Sai trong câu trả lời**: không nêu `11922`, `12860`, `12626`; cả ba mã có trong bằng chứng được truy xuất. |
| B2 | `full` | 0,996 | 2,25 | −1,254 | Có đủ hai tên tệp theo bộ đáp án; câu trả lời không phân định tên nào dành cho ACR hay CTU. |
| B3 | `full` | 1,095 | 3,64 | −2,545 | **Sai trong câu trả lời**: không nêu giới hạn `nvarchar(4000)` / 4.000 ký tự; bằng chứng có đoạn nguồn ghi rõ giới hạn. |
| B4 | `full` | 0,983 | 2,19 | −1,207 | Chạy theo yêu cầu nhưng **không tính đúng/sai**: đáp án chuẩn đã xác nhận là không có trong tài liệu hiện có. Câu trả lời cũng không nêu 14 ký tự hoặc tiền tố `Y3`. |
| B5 | `full` | 0,957 | 1,81 | −0,853 | **Sai**: không nêu `HOUSE_METHOD`, không nêu `'0'` = đưa vào kho và `'1'` = kiểm tra. |
| H3 | `focused` | 0,483 | 1,18 | −0,697 | Báo cáo lượt tham chiếu không có bộ dữ kiện chuẩn độc lập; không chấm đúng/sai. Câu trả lời ONNX không đưa ra trình tự xử lý lỗi, tương tự câu trả lời PyTorch. |

Đối chiếu B1–B5 dùng cùng câu hỏi và bộ dữ kiện tham chiếu của lượt PyTorch: B1 `11922` / `12860` / `12626`; B2 `YY2-Z151.exe` / `YY2-Z152.exe`; B3 `nvarchar(4000)` / 4.000 ký tự; B4 như ghi chú loại trừ; B5 `'0'` / `'1'` cùng ý nghĩa. B4 không được tính vào tỷ lệ đúng/sai. H3 là câu giữ lại để kiểm tra; `FIX2_onnx-worker-verify.md` chỉ ghi nhận câu trả lời có xuất hiện, không cung cấp đáp án chuẩn để chấm.

Thời gian ONNX đều thấp hơn số PyTorch trong lượt tham chiếu. Mức tăng tốc theo từng câu lần lượt là B1 **46,93×**, B2 **2,26×**, B3 **3,32×**, B4 **2,23×**, B5 **1,89×**, H3 **2,44×**. Đây là so sánh với thời gian PyTorch đã ghi ở commit `484ac76`, không phải lượt PyTorch chạy lại trên index mới.

## Bằng chứng và nhiễu XML

- B1 và B3: đoạn bằng chứng có dữ kiện tham chiếu, nhưng câu trả lời tổng hợp không nhắc lại dữ kiện. Đây là thiếu sót ở câu trả lời, không phải không tìm thấy đoạn.
- B2: câu trả lời có cả hai tên tệp; đoạn trích đặt chúng dưới nhãn Matecon CTU nên không chứng minh phép gán riêng cho từng loại xe.
- B4: 2 đoạn bằng chứng có XML slide (`<p:sld`, `xmlns`); câu trả lời không chứa XML. B1, B2, B3, B5 và H3 không có XML trong bằng chứng/câu trả lời. Chỉ ghi nhận, không dọn XML trong D3.
- B5: có từ `検査` trong bằng chứng nhưng ở nội dung khác, không phải định nghĩa giá trị của `HOUSE_METHOD`; không tính là bằng chứng cho đáp án.

## Xác nhận chỉ đọc

| Chỉ số | Trước | Sau |
| --- | ---: | ---: |
| Kích thước index (byte) | 29.851.648 | 29.851.648 |
| Tài liệu | 74 | 74 |
| Chunk | 1.272 | 1.272 |
| Chunk truy xuất được | 1.064 | 1.064 |
| Vector ONNX dense | 1.064 | 1.064 |
| Vector ONNX sparse | 1.064 | 1.064 |
| `integrity_check` | `ok` | `ok` |

Ảnh chụp chỉ số trước/sau giống hệt; truy vấn không ghi vector, không nạp tài liệu và không chạy `--apply`. Nhật ký JSONL đầy đủ được giữ ngoài Git tại `C:/Users/Admin/AppData/Local/Temp/fix3_baseline_d3_onnx.jsonl`.

Nguồn đối chiếu: `docs/phieu-viec/ket-qua/FIX3_ingest-D2-apply.md`, `docs/phieu-viec/ket-qua/FIX3_dieu-tra-B-sai.md`, `docs/phieu-viec/ket-qua/FIX2_onnx-worker-verify.md`, `docs/phieu-viec/ket-qua/FIX3_nghiem-thu-lan3.md`.
