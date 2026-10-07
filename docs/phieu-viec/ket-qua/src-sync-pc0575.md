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

## 7. Kết quả hướng A + mẫu B theo chốt 11:47 (thợ làm 11:53 → 12:15)

- Cách đếm sửa cho đúng (rút kinh nghiệm từ lần chạy đầu): mỗi mã có thêm 1 mảnh tóm tắt (`file_type=document_summary`, vân tay trống) nên phải trừ ra; chỉ xét mảnh nội dung.
- Hướng A (toàn bộ nhóm 1 mảnh, có kiểm hash từng tệp, chỉ mục mở chỉ-đọc):
  - 541 mã txt = 40 một-mảnh nội dung + 500 nhiều-mảnh + 1 chỉ-có-tóm-tắt.
  - Dựng được 29/40 một-mảnh (băm SHA-256 nội dung mảnh bằng đúng vân tay mới ghi, kiểm lại sau ghi); 11 mã một-mảnh không khớp cả 3 biến thể (thường/chuẩn hóa/đã xén) nên KHÔNG ghi (đúng rào).
  - Đĩa hiện có 29 tệp (canary 16 + `C:/AIOS_workspace…` 13), đúng đường dẫn tuyệt đối trong chỉ mục (không dùng ánh xạ).
  - Probe mức cổng (mô phỏng `_is_stale`): 29 qua / 0 rớt; 11 mã chưa ghi vẫn thiếu tệp (đúng như dự kiến).
  - Chỉ mục MD5 trước/sau bước này đều `492c065f8f741ad5c73a900fa6bcdf3e` (không đổi trong bước; thành thật ghi nhận khác mã Pha 0 `A7C7…` dù cùng cỡ 2853646336 B, tệp sửa lúc 11:36 — cần điều phối xác minh, thợ không sửa chỉ mục).
- Mẫu B (5 mã nhiều-mảnh: 2 xlsx/txt 2 mảnh + 3 txt/pdf 3 mảnh):
  - Thử 9 công thức nối (nội dung thường/chuẩn hóa/đã xén × nối rỗng/xuống dòng/hai xuống dòng, xếp theo mã mảnh): 0/5 khớp — chưa rút được công thức nối.
  - Đối chiếu 5/5 với `text_export.jsonl` và 2 gói delta: không có mã nào trong đó.
  - Tệp gốc trên Drive cho 5 mã này chưa tải (cần bản đồ tên tệp gốc ↔ mã; tên gợi ý `KTD-…xlsx`, `302XC…pdf` nằm trong nhóm MOM/LSU).
  - KHÔNG ghi tệp nào cho nhóm nhiều-mảnh (đúng rào chỉ-ghi-khi-khớp).
- Kết luận thợ: A đạt một phần (29/541 có mặt đúng từng byte, qua cổng); B mẫu 0/5 — xin điều phối chốt tiếp (bản đồ Drive cho 500 mã nhiều-mảnh, hoặc cho chạy toàn bộ B khi có nguồn, hoặc quay lại C nếu B bất khả thi). Probe RAG đầy đủ `strict_semantic=True` chưa chạy (máy đang mạng `KT_CHETAO` để tải; chạy đo cần về mạng công ty + runtime app).

## 8. Kiểm chứng chỉ mục + bản đồ hướng B đúng nghĩa (lệnh 12:22, thợ làm 12:45 → 13:00, chỉ-đọc)

- Kiểm chứng chặn trước mọi việc khác trên chỉ mục (mở `mode=ro`, không ghi):
  - `PRAGMA quick_check` = `ok`.
  - Đếm trực tiếp: 889 mã tài liệu riêng biệt / 889 đường dẫn riêng biệt / 149.800 mảnh — khớp mốc chuẩn.
  - Phân loại mảnh: 385 mảnh tóm tắt (`document_summary`, vân tay trống) + 149.415 mảnh nội dung.
  - Nhóm nội dung có vân tay: 540 mã có vân tay đầy đủ + 348 mã `gpu-…` trống vân tay + 1 mã chỉ-có-tóm-tắt (tổng 889). Khớp phát hiện mục 5.
  - Vân tay logic mới (thay MD5 thô, vì byte SQLite đổi khi tiến trình chạy/chốt sổ):
    - Công thức nội dung (khuyên dùng): SHA-256 trên danh sách sắp xếp `mã | vân tay nội dung | số mảnh nội dung` = `87a3626a85bc32c81ec899c0b5c47d59f6208afd73c80cc94c0a4f2f1df6de3c`.
    - Công thức tổng (để đối chiếu): SHA-256 trên `mã | vân tay nội dung | tổng mảnh` = `fce85b60b783d0a59545f87042ac2b1b63212bbd8d9dd9948df647b9dbdcf`.
  - Ghi nhận thay đổi byte 11:36: cùng cỡ 2.853.646.336 B, không thợ nào ghi chỉ mục trong bước này, probe 29/29 khớp vân tay — dấu hiệu nội dung nguyên vẹn, chờ điều phối xác minh thêm.
  - Rào giữ: không ghi/sửa chỉ mục, không đụng `wire_qa_staging.py`, không đụng `src/rag_v2*` local.
- Hướng B đúng nghĩa (bản đồ tệp gốc ↔ mã từ siêu dữ liệu chỉ mục, chưa tải Drive):
  - Cách đọc: mỗi mã có `source_path` là đường dẫn `.txt` vật liệu hóa tuyệt đối + `source_name` là tên tệp gốc + `metadata_json.extractor` là bộ chuyển đổi (ví dụ `ExcelDocumentConverterAdapter`).
  - Ví dụ thật (nhóm nhiều-mảnh, đọc chỉ-đọc): `wsc-9c82b1ca2e1898a8d9d03e8b` (61.760 mảnh) ↔ `61C1065D8513_B4_Bow_Skew.xlsm`; `wsc-4fc7eb76bdc2e05c08b3f0f6` (39.870 mảnh) ↔ `Loi KDTPS.xlsx`.
  - Cơ chế đúng của chương trình (đọc mã `HEAD`): tệp gốc → trích văn bản (`source.text`) → ghi `{mã}.txt` (`_materialize_sources`) → băm SHA-256 toàn tệp (`_file_fingerprint`) → tách mảnh theo phần tử. Vì vậy nối tay các mảnh không bao giờ khớp — phải tải gốc + chạy đúng bộ chuyển đổi rồi đối chiếu vân tay.
  - Bước tiếp theo cần cổng mạng `ngoai` + `DRIVE=OK`: tải 5 tệp gốc mẫu từ Drive `AIOS_Data` (nhóm MOM/LSU), chạy bộ chuyển đổi của chương trình, đối chiếu từng tệp; báo mẫu trước khi mở rộng. Nếu mẫu đúng-nghĩa vẫn 0/5 thì dừng báo điều phối (không tự chốt C).

## 9. Mẫu B 5 mã + rà Drive (thợ làm 13:05 → 13:15, chỉ-đọc + liệt kê Drive)

- Cổng mạng lúc làm: `MANG=KT_CHETAO`, `DRIVE=OK` (chạy lại `Chuyen-Mang.ps1`, ra được Drive). Đĩa C trống 68,21 GB, D trống 20,73 GB — đủ chỗ tải mẫu.
- Chọn 5 mã nhóm `.txt` 2–3 mảnh nội dung, có vân tay, tên gốc thật (đọc chỉ-đọc `mode=ro`, khóa `metadata.metadata.extractor`):
  - `wsc-3d9aa320fd815c22934dd257` (3 mảnh) ↔ `KTD-2026-01-0067-Iris2020-C34-A1-C4701.xlsx` ↔ `ExcelDocumentConverterAdapter`.
  - `wsc-8a3bd0d172fd52cb192c6be7` (3 mảnh) ↔ `Barcode_List.xlsx` ↔ `ExcelDocumentConverterAdapter`.
  - `wsc-6d6398a3ab79894c5425393f` (3 mảnh) ↔ `302XC47210-01.pdf` ↔ `PDFDocumentConverterAdapter+pymupdf_fallback`.
  - `wsc-b124bf7cf16c2ffe0bd1518a` (2 mảnh) ↔ `PA0893D_circuit.pdf` ↔ `PDFDocumentConverterAdapter+pymupdf_fallback`.
  - `wsc-c3e7ff49251ad8ff24cf613e` (3 mảnh) ↔ `KTD-2025-11-1181-Iris2024-C35-A5-Màn hình không sáng.xlsx` ↔ `ExcelDocumentConverterAdapter`.
- Bối cảnh: nhóm `.txt` 2–3 mảnh có vân tay có 36 mã; chỉ 13 mã có tên gốc thật, 23 mã tên `wsc-*.txt` (mất tên gốc, chưa tải được nếu không có bản đồ khác).
- Rà Drive `AIOS_Data` (`1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`, liệt kê `embeddedfolderview` qua `KT_CHETAO`, chưa tải gì):
  - Gốc 11 mục khớp Pha 1 (3 thư mục + 8 tệp).
  - `MOM_Opcenter_WMS` 44 mục, `Tài liệu của tất cả dòng máy` 8 mục (3 thư mục LSU + 5 tệp lẻ), `Iris LSU` 11 mục, `6thA3 LSU` 1 mục, `Sirius LSU` 7 mục — **không thấy 5 tên gốc mẫu** ở các mức đã liệt kê.
  - Suy đoán trung thực: 5 tệp KTD/PDF mẫu nằm sâu hơn (thư mục cháu chưa duyệt hết) hoặc trong gói `Điều chỉnh-20260905T053942Z-1-001.zip` ở gốc — cần duyệt tiếp ở nhịp sau, không tải bừa cả gói lớn.
- Rào giữ: chỉ đọc chỉ mục (`mode=ro`), không ghi tệp nào, không sửa chỉ mục, không đụng `wire_qa_staging.py`, không đụng `src/rag_v2*` local (WIP của agy giữ nguyên).

## 10. Rà sâu tầng 3 (thợ làm 13:14 → 13:16, chỉ liệt kê Drive, chưa tải gì)

- Cách làm: liệt kê `embeddedfolderview` từng thư mục con qua mạng `KT_CHETAO` (`DRIVE=OK`), đối chiếu đúng tên 5 tệp mẫu mục 9.
- Kết quả tầng 2: `MOM_Opcenter_WMS` 44 mục (5 thư mục con + 37 tệp, toàn tài liệu MOM/WMS/PLM — không có tên mẫu); `Tài liệu của tất cả dòng máy` 8 mục (3 thư mục LSU + 5 tệp lẻ LSU — không có tên mẫu); `Iris LSU` 11 mục, `Sirius LSU` 7 mục, `6thA3 LSU` 1 mục (`Lỗi JIG BEAM`) — không có tên mẫu.
- Kết quả tầng 3: `Iris/log` 5 tệp csv, `Iris/thử nghiệm TAPE` 2 mục, `Sirius/NG BOW_SKEW_RC9` 1 mục, `Sirius/Sirius2_linearity` 13 mục (6 thư mục con + 7 tệp xlsm/xlsx/png), `Sirius/ảnh hưởng độ dạt tia` 5 mục, `6thA3/Lỗi JIG BEAM` 9 thư mục con (ngày `2021.03.xx`) — **không thấy 5 tên mẫu** ở tầng này.
- Tổng đã rà khoảng 120 tên qua 3 tầng: **0/5 tên mẫu**. Không tải bừa gói `Điều chỉnh-...zip` ở gốc (chưa rõ dung lượng, để nhịp sau quyết).
- Rào giữ: chỉ liệt kê Drive + đọc chỉ mục cũ, không ghi tệp nào, không sửa chỉ mục, không đụng `src/rag_v2*` local.

## 11. Cổng mạng mở lại + đo dung lượng gói Điều-chỉnh (thợ làm 14:59 → 15:02, chỉ đọc header, chưa tải)

- Cổng mạng: `Chuyen-Mang.ps1 -Mang ngoai` OK (`MANG=KT_CHETAO`, `DRIVE=OK`, exit 0), wifi `KT_CHETAO` 86% 5GHz, `curl drive.google.com` HTTP 302 ~0,4s — cổng Pha 2 MỞ thật (khác các nhịp trước FAIL ở `vn-kdwireless`).
- Liệt kê lại gốc `AIOS_Data` qua `embeddedfolderview`: đủ 11 mục như Pha 1 (3 thư mục + 8 tệp), gói `Điều chỉnh-20260905T053942Z-1-001.zip` ID `1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP`.
- Đo dung lượng KHÔNG tải (lệnh `curl --range 0-0` lấy `Content-Range`): `bytes 0-0/858190286` = 858.190.286 B ≈ 818,4 MB ≈ 0,799 GB — **dưới ngưỡng 1 GB nên được tải thẳng theo vé** (không cần báo trước mới tải).
- Đĩa C lúc đo: trống ~73,8 GB (73.858.588.672 B) — đủ chỗ cho gói 0,8 GB + giải nén.
- Rào giữ: chỉ đọc header + liệt kê, chưa tải byte nào, không ghi tệp/index, không đụng `wire_qa_staging.py`, không đụng `src/rag_v2*` local.

## 12. Tải gói Điều-chỉnh + đối chiếu 5 mẫu bằng bộ chuyển đổi của chương trình (thợ làm 15:02 → 15:15)

- Tải: `drive.usercontent.google.com/download?id=1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP` về `local_runs/src_sync/Dieu-chinh-20260905T053942Z-1-001.zip` (ngoài Git), đủ 858.190.286 B khớp `Content-Range`, tốc độ ~37 MB/s (~21 giây).
- Giải nén chỉ-đọc: gói có 2.201 mục trong thư mục `Điều chỉnh/`.
- Đối chiếu tên 5 mẫu mục 9 với tên trong gói: **4/5 có mặt** — `KTD-2026-01-0067…C4701.xlsx` (Lịch sử lỗi/C Call), `302XC47210-01.pdf` (Sơ đồ điện/Led), `PA0893D_circuit.pdf` (Sơ đồ điện/Tranfer Assy), `KTD-2025-11-1181…Màn hình không sáng.xlsx` (Lịch sử lỗi/C Call); **vắng `Barcode_List.xlsx`** (0 hit trong gói; rà gốc MOM 44+ mục cũng không thấy — cần nhịp sau tìm tiếp hoặc xin bản khác).
- Tách 4 tệp ra `local_runs/src_sync/goc_mau/` (ngoài Git, chỉ để đối chiếu, chưa đặt vào `materialized_sources`).
- Chạy đúng bộ chuyển đổi tải file hiện tại của chương trình (`ingest_and_extract_bytes` trong `src/aios_habit/workspace_chat_source_ingest.py`): băm SHA-256 văn bản đã xén so với vân tay chỉ mục — **0/4 khớp** (xlsx KTD-…C4701 900 ký tự `88b5de…` vs `f9023c…`; pdf 302XC 2.248 ký tự `69155f…` vs `983402…`; pdf PA0893D 1.080 ký tự `0a4be7…` vs `6fabc8…`; xlsx KTD-…1181 1.258 ký tự `651c50…` vs `c45516…`).
- Ý nghĩa trung thực: tệp gốc cùng tên trong gói Điều-chỉnh KHÔNG cho ra đúng từng byte bản vật liệu hóa trong chỉ mục khi chạy bộ chuyển đổi hiện tại — có thể khác phiên bản tệp, khác bộ chuyển đổi lúc dựng chỉ mục, hoặc đường nối văn bản khác. Vì vậy **chưa ghi tệp nào vào `materialized_sources`** (đúng rào chỉ-ghi-khi-khớp).
- Kiểm chứng chỉ mục trước/sau: chỉ mở `mode=ro`, không ghi/sửa chỉ mục (md5 logic sẽ đo ở nhịp probe sau).
- Đề xuất xin Muse chốt: (a) tìm `Barcode_List.xlsx` ở nguồn khác; (b) thử đường chuyển đổi `rag_v2` (`ExcelDocumentConverterAdapter`/`PDFDocumentConverterAdapter` qua `registry`) thay vì đường tải file, hoặc xin 4 tệp đúng phiên bản từ máy dựng chỉ mục; (c) nếu vẫn lệch thì báo phương án C (chế độ index-only) — thợ KHÔNG tự chốt.
- Rào giữ: không ghi `materialized_sources`, không sửa chỉ mục, không đụng `wire_qa_staging.py`, không đụng `src/rag_v2*` local, không merge `main`, không secret.

## 13. Bản kê dứt điểm nhóm 511 theo chốt Muse 15:22 (thợ làm 15:42 → 15:50, chỉ-đọc)

- Chốt áp dụng: DỪNG hẳn đường săn tệp gốc trên Drive cho nhóm 511 (mẫu mục 12 0/4 bằng chính bộ chuyển đổi của chương trình = tệp trong gói Điều-chỉnh khác phiên bản lúc nạp chỉ mục, không truy `Barcode_List` nữa). Nguồn byte đáng tin duy nhất cho nhóm 511 = các tệp `.txt` vật liệu hoá trên máy nhà giữ chỉ mục — vé đóng gói riêng sẽ làm sau.
- Cách lập: đọc chỉ mục chỉ-đọc (`mode=ro&immutable=1`, `PRAGMA query_only=ON`, không ghi/sửa gì), nhóm theo mã tài liệu, lọc 541 đường dẫn `.txt` có vân tay (540 mã), trừ 29 mã một-mảnh đã khôi phục đúng hash ở mục 7 (đĩa còn nguyên: canary 16 + `C:/AIOS…` 13, đã kiểm lại ở nhịp này).
- Kết quả: **511 mã** = **500 mã nhiều-mảnh** + **11 mã một-mảnh lệch** (40 một-mảnh − 29 đã ghi). File checklist đầy đủ: `docs/phieu-viec/ket-qua/ban-ke-511.csv` (511 dòng + header, cột `document_id, source_path, source_fingerprint, n_content, nhom`).
- Mẫu 11 mã một-mảnh lệch (để vé đóng gói đối chiếu nhanh): `wsc-1696cf072`, `wsc-575eb6de7`, `wsc-6d14cd1be`, `wsc-72286b0d4`, `wsc-8782bf3e4`, `wsc-8ce71e2a1`, `wsc-a36e39c1d`, `wsc-c3ac0ce86`, `wsc-d28ff291f`, `wsc-fa75c3428`, `wsc-ffa5990a7` — mỗi mã 1 mảnh nội dung, có vân tay kỳ vọng trong CSV, đích là đường dẫn tuyệt đối trong cột `source_path` (2 gốc: `local_runs/workspace_chat_rag_v2_canary/materialized_sources` và `C:/AIOS_workspace_chat_rag_v2_production/materialized_sources`).
- Nhóm 500 mã nhiều-mảnh: số mảnh nội dung từ 2 đến 61.760 (phân bố đã đo ở mục 7–8), vân tay kỳ vọng + đường dẫn đích trong CSV. Vé đóng gói máy nhà chỉ cần: chép đúng byte tệp `.txt` vào đúng `source_path`, băm SHA-256 khớp `source_fingerprint` mới ghi.
- Phần máy công ty của vé khép ở đây: 29 tệp khôi phục + kiểm chứng chỉ mục ĐẠT (mục 8: `quick_check=ok`, 889/149.800, vân tay logic nội dung `87a3626a…`) + bản đồ bằng chứng đầy đủ (mục 8–12) + bản kê 511 này. Nhóm 511 và nhóm 349 (`gpu-…` + 1 trống vân tay) chuyển vé riêng.
- Giữ nguyên toàn bộ tệp đã tải ở `local_runs/src_sync` (gói Điều-chỉnh 858MB + 3 tệp delta + 4 gốc mẫu), không xóa.
- Rào giữ: chỉ đọc chỉ mục, không ghi/sửa index, không ghi `materialized_sources`, không đụng `wire_qa_staging.py`, không đụng `src/rag_v2*` local (WIP agy), không merge `main`, không secret.
