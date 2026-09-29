# Báo cáo Vé E2 vòng 4 — chạy lại B1–B5

- Ngày chạy: 2026-09-29, máy `h410asrock`.
- Nhánh: `phieu-viec/rag-fix1`.
- Mã sửa được kiểm tra: `ada3ed532c00fcf02f52ed41658d0d81203fa43a` (`e2v3_fix_commit`).
- Không sửa mã nguồn. Chỉ mục được truy vấn là bản sao trên C, mở `mode=ro`.

## Kết luận

**B1–B5 chạy xong không lỗi; B1/B2/B3/B5 đạt kiểm tra nội dung.** B4 đã chạy nhưng bị loại khỏi chấm.

- **Kết luận tổng thể: CHƯA ĐẠT về khả năng truy nguyên sự cố quyền riêng tư vòng 3.** Nhật ký phiên xác nhận 19 tệp đã được đọc nhưng không lưu tên các tệp; không thể lập danh sách chính xác hoặc loại trừ khả năng nội dung đã rời máy trong sự cố cũ. Đây là thiếu hụt bằng chứng của sự cố vòng 3, không phải lỗi kết quả B1–B5 vòng 4. Đã dừng tìm kiếm bên ngoài, không gọi lại công cụ gây sự cố. Chuyển `xong-cho-duyet` để Muse xem xét.

## Điều tra sự cố công cụ vòng 3

- Nhật ký phiên cục bộ ghi lần gọi `functions.find` lúc `2026-09-29 20:45:34 +07`, phạm vi `local_runs/workspace_chat_rag_v2_production/`; mục đích là tìm đường dẫn chỉ mục đang vận hành `library.sqlite`.
- Kết quả được ghi trong log: `listed 76`, `judged 0`, `read 19 files (24.1KB)`, `27 requests`, `0 tokens`; log sử dụng ghi các yêu cầu OpenRouter bị từ chối HTTP `402`.
- Bản ghi lưu lại không có tên hoặc đường dẫn của 19 tệp. Tìm trong nhật ký phiên và kho log OMP cục bộ chỉ thấy cùng bản ghi tóm tắt; không có dữ liệu đủ để khôi phục danh sách. Không suy đoán tên tệp.
- Vì vậy không thể chứng minh nội dung nào đã hoặc chưa được gửi trước khi máy chủ trả `402`. Vòng 4 không gọi `functions.find`, không dùng dịch vụ AI/provider hoặc công cụ tìm kiếm ngoài. Các thao tác `git pull`/`git push` chỉ dùng làm kênh mailbox theo yêu cầu; không đẩy câu trả lời hay dữ liệu nguồn thô.

## Điều tra lỗi worker và độ trễ vòng 3

- Cấu hình vòng 3 khởi tạo worker ONNX trên CPU thành công trong `35,163s`; warmup (khởi động nóng) mất `125,34s`. Tệp stderr của worker chỉ có một dòng khởi tạo, không có traceback hay dòng gọi provider.
- Độ trễ vòng 3: B1 `142,987s`, B2 `326,818s`, B3 `58,664s`, B4 `73,660s`, B5 `70,136s`. Chỉ B2 có `recovered_after_worker_restart=true`.
- So với vòng 2, thời gian khởi tạo worker gần tương đương (`35,163s` so với `32,28s`), nhưng warmup (khởi động nóng) tăng từ `13,76s` lên `125,34s`; B1 tăng từ `12,680s` lên `142,987s`, B2 từ `13,310s` lên `326,818s`.
- Log vòng 3 chỉ ghi `BGE worker query failed/crashed: SemanticBackendError`. Mã `bge_subprocess_client.py` chỉ ghi loại ngoại lệ rồi đổi sang `bge_subprocess_worker_crashed`; `_send_request()` có thể phát sinh timeout, EOF, không có phản hồi hoặc lỗi tiến trình, nhưng log không giữ nguyên nhân cụ thể. Không có số đo bộ nhớ, tải CPU hoặc mã thoát worker để phân biệt môi trường với mô hình hoặc mã nguồn. Vì vậy không quy nguyên nhân cho một giả thuyết cụ thể và không sửa mã tổng hợp.
- Lượt vòng 4 lặp lại được, cùng tuyến ONNX CPU, nhưng không tái hiện lỗi. Điều đó cho thấy lỗi không tái hiện ở lượt này; không đủ để xác định nguyên nhân gốc vòng 3.

## Tiền kiểm vòng 4

- Cổng Phase B mở: `e2v3_fix_commit` nằm trong lịch sử HEAD.
- Sáu khóa cloud vẫn hiện diện trong môi trường; giá trị không được đọc/ghi vào báo cáo. `create_synthesis_provider()` trả `none`.
- Cấu hình: `index_read_only=true`, `ensure_embeddings_on_open=false`, `enable_network=false`, `enable_provider_synthesis=false`; bộ nhớ đệm xác minh model còn tươi.
- Bản sao chỉ mục C SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`, khớp giá trị đã ghim. Tập nguồn giữ đúng 74 tài liệu và 1.064 đoạn truy hồi được. Tiền kiểm kết thúc với `blocking=[]`.

## Kết quả B1–B5

| Ca | Thời gian | Lỗi / grounded (có bằng chứng) / abstained (từ chối) / provider_used (dùng nhà cung cấp) | Kết quả chấm |
|---|---:|---|---|
| B1 | `26,771s` | Không lỗi / `true` / `false` / `false` | ĐẠT — đủ `11922`, `12860`, `12626`. |
| B2 | `10,623s` | Không lỗi / `true` / `false` / `false` | ĐẠT — đủ `YY2-Z151.exe` và `YY2-Z152.exe`. |
| B3 | `10,741s` | Không lỗi / `true` / `false` / `false` | ĐẠT — có `nvarchar(4000)`. |
| B4 | `12,863s` | Không lỗi / `true` / `false` / `false` | Đã chạy; loại khỏi chấm theo vé. |
| B5 | `10,748s` | Không lỗi / `true` / `false` / `false` | ĐẠT — một cửa sổ `HOUSE_METHOD` có `'0'`, `'1'`, `倉庫`/`格納` và `検査`; kiểm tra cục bộ xác nhận `'0'` gắn với cất kho, `'1'` gắn với kiểm tra. |

Cả năm câu đi theo đường truy xuất `hybrid`; không câu nào cần khởi động lại worker. Bộ chấm cục bộ cho B1/B2/B3/B5 ghi `DAT=true`. `grounded=true` nghĩa là có bằng chứng; `abstained=false` nghĩa là không từ chối trả lời; `provider_used=false` nghĩa là không dùng nhà cung cấp. B5 không chấm bằng chuỗi `'1'` đơn lẻ: cửa sổ gắn với `HOUSE_METHOD` có đủ cả mã và nghĩa; không có `'1'` nằm ngoài cửa sổ `HOUSE_METHOD`.

## Toàn vẹn dữ liệu và nơi lưu kết quả

- Ảnh chụp cây kho trước/sau lượt: mỗi ảnh 114.055 tệp; sai khác 0 thêm, 0 xóa, 0 đổi (`clean=true`).
- Chỉ mục đang vận hành trên D trước/sau có cùng SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`, kích thước `2.552.659.968` byte và mtime (thời gian sửa) không đổi (`1790549703247790600` ns). Không ghi vào chỉ mục D.
- Câu trả lời nguyên văn, JSON thô và stderr chỉ nằm tại `C:/AIOS_p1_4/out/e2v4/` (`ve_e2v3_answers.txt`, `ve_e2v3_raw.jsonl`, `ve_e2v3_report.json`, `ve_e2v3_worker_stderr.log`). Tiền kiểm và ảnh chụp cũng nằm tại thư mục này. Không đưa nội dung câu trả lời hoặc bằng chứng nguồn thô vào Git; báo cáo này chỉ chứa số liệu tối thiểu, mã kiểm tra và giới hạn bằng chứng.
- Tệp stderr của worker vòng 4 có 1 dòng, 0 dòng gọi provider. Không dùng `functions.find` hoặc dịch vụ AI/provider trong lượt kiểm chứng; tuyến chạy đặt mạng và tổng hợp qua provider tắt.

## Giới hạn và bước tiếp theo

- Không thể hoàn thành danh sách chính xác 19 tệp của sự cố vòng 3 vì nhật ký phiên không ghi danh sách đó. Không gửi yêu cầu nào ra ngoài để thử khôi phục.
- Các tiêu chí chạy, thời gian, nội dung B1/B2/B3/B5 và toàn vẹn chỉ mục vòng 4 đều đạt. Tiêu chí kiểm toán sự cố quyền riêng tư lịch sử vẫn chưa xác nhận; cần Muse xem xét log và quyết định cách xử lý bằng chứng thiếu.
- Trạng thái mailbox: `xong-cho-duyet`. Không sửa mã tổng hợp (`synthesis.py`), không ghi vào chỉ mục D, không chạy `--apply`, `vacuum` hoặc `embed`, không đụng `main`.
