# Báo cáo vé `SRC-SYNC-PC0575` — nháp Pha 1 (xong liệt kê Drive, chờ chốt phương án 349 mã trống vân tay)

- Vé: `SRC-SYNC-PC0575` — đưa tệp nguồn về máy công ty để RAG chạy đúng thiết kế.
- Máy làm: công ty `KDTVN-PC0575` (mạng công ty `vn-kdwireless` suốt Pha 0).
- Thời gian Pha 0: 2026-10-07 10:05 → 10:25 +07 (giờ máy).
- Trạng thái vé: xong Pha 1 (cổng mạng mở theo cơ chế mới, đã liệt kê Drive, tuyệt đối chưa tải tệp nào).
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

## 2. Yêu cầu chuyển mạng (cổng Pha 1 — cơ chế MỚI từ 2026-10-07, thay đoạn dừng chờ cũ)

- Thợ TỰ chuyển sang mạng `KT_CHETAO` bằng `D:\Sandbox\agent-mailbox\Chuyen-Mang.ps1 -Mang ngoai`, kiểm kết quả `DRIVE=OK` rồi mới tải — không chờ dòng xác nhận của Muse nữa (quy ước mới trong `docs/phieu-viec/mailbox-pc0575-opencode/QUY-UOC.md`).
- Tải xong chuyển về `-Mang congty` mới chạy chương trình và đầu mối.
- Bằng chứng cổng mở lúc 10:46: `MANG=KT_CHETAO`, `DRIVE=OK` (chạy lại lệnh chuyển mạng, ra được `drive.usercontent.google.com:443`).

## 3. Rào đã giữ trong Pha 0

- Không ghi hay sửa chỉ mục (mã băm không đổi như trên).
- Không chạm tệp `wire_qa_staging.py` (đồng nghiệp đang vá ở vé song song).
- Không khởi động lại chương trình của đồng nghiệp, không gộp nhánh chính, không đưa bí mật vào báo cáo hay nhật ký.

## 4. Pha 1 xong — liệt kê Drive `AIOS_Data` (chỉ đọc, chưa tải tệp nào)

- Cách liệt kê: trang xem thư mục công khai của Drive (`embeddedfolderview`) qua mạng `KT_CHETAO`, không đăng nhập, không tải tệp.
- Gốc `AIOS_Data` (11 mục): 3 thư mục — `Hệ thống MOM_Opcenter_WMS`, `index-split-r5-backup`, `Tài liệu của tất cả dòng máy` — và 8 tệp (`bge-m3-onnx-fp32.zip`, `error_cases_dict.db`, `export_dc.jsonl`, `gpu-262b-delta-20261001.zip`, `gpu-dc-delta-20261001.zip`, `library.sqlite`, `text_export.jsonl`, `Điều chỉnh-20260905T053942Z-1-001.zip`).
- `Hệ thống MOM_Opcenter_WMS`: khoảng 30 tệp nguồn nhóm MOM (bản trình chiếu, bảng tính, bản vẽ, văn bản).
- `Tài liệu của tất cả dòng máy`: 3 thư mục con `6thA3 LSU`, `Iris LSU`, `Sirius LSU` (mỗi thư mục còn thư mục cháu như `log`, `Lỗi JIG BEAM`) + vài tệp lẻ nhóm LSU.
- Ghi chú: tệp `gpu-dc-delta-20261001.zip` và `gpu-262b-delta-20261001.zip` ở gốc có tên gợi ý chứa phần chênh lệch của máy dựng chỉ mục — chưa mở, để dành cho bước tải.

## 5. Phát hiện quyết định khi đọc mã (ảnh hưởng trực tiếp Pha 2)

- Đếm lại trong chỉ mục (chỉ đọc): 889 mã tài liệu — 348 đường dẫn `gpu-dc://…` / `gpu-262b://…`, 541 đường dẫn tệp `.txt` vật liệu hóa (496 ở `local_runs/workspace_chat_rag_v2_canary/materialized_sources`, 45 ở `C:\AIOS_workspace_chat_rag_v2_production\…`).
- Vân tay trong chỉ mục: **cả 348 mã nhóm `gpu-…` đều để trống** (`source_fingerprint` rỗng), thêm 1 mã nhóm vật liệu hóa cũng trống; 540 mã còn lại có vân tay đầy đủ.
- Vì sao quan trọng: mỗi truy vấn, chương trình băm tệp trên đĩa (`_file_fingerprint`, `src/aios_habit/rag_v2/pipeline.py:162`) rồi so với vân tay trong chỉ mục ở 3 cổng (`verify_selected_document_coverage`, `_is_stale`, `_hybrid_result_is_safe`); đường dẫn `gpu-…` không phải tệp trên đĩa nên luôn ra `__source_unavailable__`, khác vân tay rỗng trong chỉ mục — **tải tệp về cũng không qua được cổng với 349 mã này** nếu không có cơ chế ánh xạ trong mã (hiện mã nguồn không có chỗ nào ánh xạ `gpu-…` ra tệp đĩa).
- Hệ quả trung thực cho tiêu chí nghiệm thu: chỉ tải tệp không đủ cho cả 889; tối đa qua được cổng vân tay là 540/889 (nhóm có vân tay, nếu đặt đúng từng byte vào đúng đường dẫn tuyệt đối trong chỉ mục). Muốn đủ 889 phải thêm một trong: cơ chế ánh xạ `gpu-…` (đổi mã, cần duyệt kiến trúc), hoặc dựng lại chỉ mục có vân tay (vé cấm ghi chỉ mục), hoặc chốt chế độ chỉ-dùng-chỉ-mục chính thức.
- Đề xuất bước tiếp theo (chờ Muse chốt, không tự làm bừa): tải đối chiếu `text_export.jsonl` + 2 gói `gpu-dc-delta` trước để xem có sẵn nội dung từng byte của 541 tệp vật liệu hóa không; nếu có thì đặt vào đúng đường dẫn, đo lại probe trên nhóm 540; song song xin quyết định cơ chế cho 349 mã còn lại.

## 6. Kết quả bước 1 theo phương án 11:15 (tải xong, chưa khôi phục được 541)

- Thời gian tải: 2026-10-07 11:22 → 11:30 +07, mạng `KT_CHETAO`, kênh `drive.usercontent.google.com`, ngoài Git (`local_runs/src_sync`).
- Tệp đã tải (mã SHA-256 khớp ghim đã biết):
  - `text_export.jsonl` 81.531.448 B (`95aecf07…`), 52.979 dòng, 262 mã tài liệu.
  - `gpu-dc-delta-20261001.zip` 74.065.213 B (`31afe1e3…`), mở ra 329 mã tài liệu.
  - `gpu-262b-delta-20261001.zip` 20.867.536 B (`5bd7c56d…`), mở ra 19 mã tài liệu.
  - Tổng khoảng 176 MB, dưới ngưỡng 1 GB nên tải thẳng theo phương án.
- Đối chiếu với chỉ mục (mở chỉ đọc):
  - Chỉ mục có 889 mã: 541 đường dẫn `.txt` vật liệu hóa + 348 đường dẫn `gpu-…`.
  - Hai gói delta gộp lại đúng bằng nhóm `gpu-…` (329 + 19 = 348, trùng từng mã).
  - Tệp `text_export.jsonl` giao với nhóm vật liệu hóa = 0/541; giao với nhóm `gpu-…` = 19 mã; còn 243 mã nằm ngoài chỉ mục này.
  - Vậy cả 3 tệp đã tải **không chứa nội dung 541 tệp vật liệu hóa** (0/541).
- Thử dựng lại từ chỉ mục (chỉ đọc, chưa ghi tệp nào):
  - Tệp 1 mảnh: băm SHA-256 của nội dung mảnh bằng đúng vân tay trong chỉ mục (thử 3/3 khớp) — nhóm này dựng lại được.
  - Tệp nhiều mảnh: nối nội dung các mảnh (đã trừ mảnh tóm tắt, xếp theo mã phần tử, thử nối rỗng / xuống dòng / hai xuống dòng, cả nội dung thường và nội dung chuẩn hóa) **không khớp** vân tay (thử 1 mã 5 mảnh và 20 mã ngẫu nhiên, chỉ 1 mã 1 mảnh khớp).
  - Nguyên nhân: mảnh trong chỉ mục tách từ danh sách phần tử tài liệu, không phải cắt chuỗi tệp vật liệu hóa — muốn dựng đúng từng byte phải biết công thức tạo tệp gốc từ phần tử, chưa có.
- Chỉ mục không đổi: mã MD5 sau bước tải vẫn `A7C7C2325949C05D3396AB5371E42E64`, khớp mã Pha 0.
- Rào đã giữ: tuyệt đối chưa ghi tệp nào vào `materialized_sources`, chưa sửa chỉ mục, chưa đụng `wire_qa_staging.py`, chưa khởi động lại chương trình.
- Trở ngại kỹ thuật (không phải câu hỏi 349 đã chốt): bước 1 không khôi phục được 541 tệp từ 3 tệp đã tải vì thiếu nguồn từng byte của nhóm vật liệu hóa.
- Đề xuất hướng mới (chờ điều phối chốt, không tự làm bừa):
  - Hướng A (nhẹ): dựng tệp 1 mảnh trước từ chỉ mục (đã chứng minh khớp), đo probe trên nhóm này để lấy đà.
  - Hướng B (đúng gốc): tải tệp gốc nhóm MOM / LSU từ Drive `AIOS_Data` rồi chạy bộ chuyển đổi của chương trình để tạo lại 541 tệp `.txt` đúng từng byte, sau đó mới đo probe nhóm 540.
  - Hướng C (chốt kiến trúc): công nhận chế độ chỉ-dùng-chỉ-mục cho nhóm vật liệu hóa nếu không lấy được nguồn gốc.
