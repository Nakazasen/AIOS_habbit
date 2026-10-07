# Báo cáo vé `SRC-SYNC-PC0575` — nháp Pha 0 (xong điều tra, chờ cổng mạng)

- Vé: `SRC-SYNC-PC0575` — đưa tệp nguồn về máy công ty để RAG chạy đúng thiết kế.
- Máy làm: công ty `KDTVN-PC0575` (mạng công ty `vn-kdwireless` suốt Pha 0).
- Thời gian Pha 0: 2026-10-07 10:05 → 10:25 +07 (giờ máy).
- Trạng thái vé: xong Pha 0, **dừng ở cổng mạng** (chưa tải bất kỳ tệp nào).
- Nhánh làm việc: `phieu-viec/rag-fix1`, không gộp nhánh chính.
- Đầu vào đã đọc trước: mục 2.3 + 2.4 của `docs/phieu-viec/ket-qua/lsu-quality-pc0575.md` và báo cáo `docs/phieu-viec/ket-qua/knowledge-digest-cty.md`.

## 1. Kết quả Pha 0

### 1.1. Index mong đợi tệp nguồn ở đâu, dạng nào

- Tệp chỉ mục (mở chỉ đọc, không ghi): `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` (dung lượng tệp 2.853.646.336 byte).
- Đếm trực tiếp trong bảng khối văn bản: 889 mã tài liệu riêng biệt, 889 đường dẫn nguồn riêng biệt, 149.800 mảnh (trong đó 121.331 mảnh dùng được).
- Hai dạng đường dẫn index đang giữ:
  - 541 đường dẫn dạng bản vật liệu hóa, tên `wsc-*.txt` trong thư mục `materialized_sources` của máy đã dựng chỉ mục.
  - 348 đường dẫn dạng `gpu-262b://...` kèm tên tệp gốc (nhóm `.pptx`, `.xlsx`, `.csv`, `.pdf` và họ bảng tính).
- Tổng số ký tự văn bản trong chỉ mục: 128.208.184 ký tự (ước lượng vài trăm MB khi vật liệu hóa đầy đủ).
- Cách chương trình dùng tệp nguồn (đọc mã, không chạy):
  - Cấu hình thật của chương trình đặt `strict_semantic=True` (tệp `src/aios_habit/workspace_chat_rag_v2_adapter.py`, dòng 671).
  - Mỗi truy vấn, chương trình băm tệp trên đĩa (hàm `_file_fingerprint` trong `src/aios_habit/rag_v2/pipeline.py`, dòng 162); tệp nào không có trên đĩa thì ghi nhận `__source_unavailable__` (cùng tệp, dòng 857–858).
  - Vân tay này đem so với vân tay trong chỉ mục qua hai cổng: cổng lọc mảnh cũ `_is_stale` và cổng kiểm lại sau trộn `_hybrid_result_is_safe` (tệp `src/aios_habit/rag_v2/index.py`, dòng 4639 và 492).
  - Khi đặt `strict_semantic=True` kèm mở chỉ đọc, chương trình kiểm tra bao phủ và chặn bằng lỗi `semantic_index_coverage_incomplete` (tệp `src/aios_habit/rag_v2/pipeline.py`, dòng 888–896).

### 1.2. Ổ đĩa máy công ty có đủ không

- Ổ `C` còn trống 69,61 GB; ổ `D` còn trống 21,1 GB (đo lúc 10:05).
- Nhu cầu ước lượng chỉ vài trăm MB cho bản vật liệu hóa (cộng thêm tệp gốc nếu kéo cả gốc) — đĩa hiện tại **đủ chỗ**.
- Mạng lúc đo: `vn-kdwireless` (mạng công ty), tín hiệu 94% — đúng mạng để chạy chương trình, chưa phải mạng để tải (xem cổng bên dưới).

### 1.3. Tệp nguồn hiện có trên đĩa là 0/889

- Kiểm trực tiếp từng đường dẫn riêng biệt trong chỉ mục: **0/889 đường dẫn tồn tại** trên đĩa máy công ty.
- Thư mục bản vật liệu hóa của bản thử (`local_runs/workspace_chat_rag_v2_canary/materialized_sources`) **không tồn tại**.
- Thư mục bản vật liệu hóa của bản chính (`local_runs/workspace_chat_rag_v2_production/materialized_sources`) chỉ có 2 tệp lạ, không phải 541 tệp chỉ mục cần.
- Kết luận: đúng như vé mô tả, máy công ty đang 0/889 — mọi truy vấn đúng thiết kế đều bị chặn như đã đo ở hai vé trước.

### 1.4. Đối chiếu với thư mục Drive `AIOS_Data`

- Chưa đối chiếu được danh sách thiếu/thừa trong Pha 0 vì cần liệt kê/tải từ Drive, mà vé bắt buộc **qua cổng mạng** trước khi chạm vào Drive.
- Phần này để sau cổng (Pha 2), khi đã có dòng xác nhận chuyển mạng của Muse.

### 1.5. Bằng chứng không ghi chỉ mục

- Mã băm `MD5` của tệp chỉ mục đo sau Pha 0: `A7C7C2325949C05D3396AB5371E42E64` — khớp mã đã ghi ở vé đo chất lượng và vé sổ tay (không đổi, không ghi gì vào chỉ mục).
- Lệnh kiểm tra dùng trong Pha 0 đều mở cơ sở dữ liệu ở chế độ chỉ đọc; chi tiết lệnh nằm ở `scratch/src_sync_ph0_schema.py`, `scratch/src_sync_ph0_prefix.py`, `scratch/src_sync_ph0_size.py` (ngoài Git, không nhập kho).

## 2. Yêu cầu chuyển mạng (cổng Pha 1 — bắt buộc dừng chờ)

- Thợ xin chuyển sang mạng `KT_CHETAO` chỉ để liệt kê và tải thư mục Drive `AIOS_Data` (nhóm `MOM`, `LSU`, `Dieu-tra-loi`).
- Thợ **dừng chờ** dòng xác nhận của Muse với đúng nội dung: đã chuyển mạng `KT_CHETAO`, tiếp tục kéo.
- Tuyệt đối chưa tải bất kỳ tệp nào trước dòng xác nhận đó. Tải xong sẽ về lại mạng công ty mới chạy chương trình và đầu mối (đúng vé).

## 3. Rào đã giữ trong Pha 0

- Không ghi hay sửa chỉ mục (mã băm không đổi như trên).
- Không chạm tệp `wire_qa_staging.py` (đồng nghiệp đang vá ở vé song song).
- Không khởi động lại chương trình của đồng nghiệp, không gộp nhánh chính, không đưa bí mật vào báo cáo hay nhật ký.
