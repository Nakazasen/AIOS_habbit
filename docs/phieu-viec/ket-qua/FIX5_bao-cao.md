# FIX 5 — Provenance cho document_summary

Ngày: 2026-09-25
Nhánh: `phieu-viec/rag-fix1`

## 1. Tóm tắt thay đổi

Cả ba thay đổi đều nằm sau `AIOS_RAG_V2_SUMMARY_PROVENANCE`, mặc định tắt. Tắt flag thì hành vi cũ y hệt.

- `src/aios_habit/rag_v2/summary_provenance.py`: cờ `AIOS_RAG_V2_SUMMARY_PROVENANCE`, hàm `with_body_provenance` dùng chung, hàm `plan_summary_provenance` (dry-run) và `apply_summary_provenance` (chỉ ghi khi bật cờ).
- `src/aios_habit/rag_v2/chunking.py`: `chunk_elements` gọi `_summary_gate_open` thay cho `len(usable_elements) >= 3`; khi bật cờ, summary mới được chép `source_fingerprint` và `privacy_labels` từ chunk thân. Nội dung summary không đổi.
- `scripts/backfill_summary_provenance.py`: lệnh bảo trì, mặc định dry-run, chỉ ghi khi có `--apply` và cờ bật.

Không đổi schema. Không đụng `detect_retrieval_mode`, `BGE_BACKEND`, đường hybrid full. Không viết tay summary.

Quy tắc cho ca mơ hồ: chunk thân cùng `document_id` mà có nhiều hơn một fingerprint, hoặc nhiều hơn một bộ nhãn privacy, thì bỏ qua và ghi vào `skipped_ambiguous` với lý do `multiple_body_fingerprints` hoặc `multiple_body_privacy_sets`.

## 2. Bảng test

| Test | Việc kiểm | Kết quả |
| --- | --- | --- |
| `test_summary_provenance_flag_off_keeps_null_provenance` | tắt cờ: summary vẫn null/rỗng | pass |
| `test_summary_copies_body_provenance_when_flag_is_on` | bật cờ: summary có fingerprint và privacy của chunk thân | pass |
| `test_relaxed_gate_builds_summary_for_one_and_two_elements` | 1 và 2 phần tử: tắt cờ không có summary, bật cờ có | pass |
| `test_summary_text_does_not_change_when_flag_is_on` | nội dung summary giống nhau giữa hai cờ | pass |
| `test_flag_resolver_defaults_off` | cờ mặc định tắt | pass |
| `test_dry_run_reports_without_writing` | dry-run không ghi gì | pass |
| `test_apply_refuses_without_the_flag` | apply từ chối khi cờ tắt | pass |
| `test_apply_fills_only_missing_fields` | chỉ điền trường thiếu, không ghi đè, không đụng text | pass |
| `test_ambiguous_body_provenance_is_skipped` | mơ hồ thì bỏ qua, không ghi | pass |
| `test_summary_without_body_keeps_empty_provenance` | không có chunk thân thì giữ nguyên rỗng | pass |
| `test_ingested_summary_survives_production_privacy_and_fingerprint_filters` | ingest 1 file một đoạn và một file nhiều đoạn, query overview với privacy và fingerprint kỳ vọng | pass |

## 3. Dry-run trên index thật (chỉ đọc)

Index: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`.

- `summary_count`: 10
- `update_count` (số trường sẽ điền): 20
- `skipped_ambiguous_count`: 0
- `skipped_no_body_value_count`: 0

Không ghi gì. `--apply` trên index thật CHƯA chạy, chờ duyệt riêng.

## 4. End-to-end trên bản copy

Đã copy `collections/tri_thuc` sang thư mục tạm, chạy backfill `--apply` trên bản copy, rồi chạy lại 5 câu A của FIX 3, thêm 3 câu held-out mới, trên bản copy.

- `applied_rows_changed`: applied_rows_changed: 20
- Index production không bị sửa: có (so `st_mtime_ns` trước/sau)

| Câu | Giây | Mode | Abstain | Path | Dòng "trả lời ở mức tổng quan" | Toàn văn |
| --- | ---: | --- | --- | --- | --- | --- |
| A1<br>Hệ thống điều khiển và quản lý sản xuất này gồm những thành phần chính nào và chúng phối hợp với nhau ra sao? | 0.116765 | overview | không | summary_only | có | - Một hệ thống điều khiển đưa ra các chỉ dẫn lái xe cho AGV/ACR/CTU, giám sát trạng thái hoạt động của chúng ... [1]<br>- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [2]<br>- Xử lý ngày 17.06.2026: Đối với nhóm 1, in lại EDI(xóa thông tin Lot sản xuất), xóa dữ liệu đã đọc vào trên SQL và MOM, tiến hành nhập kho lại. [3]<br>- == Thông tin về quy trình sản xuất ST-CO- Đến đăng ký Ngày phát sinh/ghi nhận: Áp dụng cho các lỗi ST/CO và thực tích phát sinh trong quá trình sản xuất AMS; file hiện tại chưa ghi ngày cụ thể cho từng bước. [4]<br>- [DOCUMENT ARCHITECTURE & SUMMARY] [5]<br>Ghi chú: trả lời ở mức tổng quan. |
| A2<br>Luồng luân chuyển vật tư từ khi nhập kho tự động đến khi cấp phát ra dây chuyền sản xuất diễn ra qua những bước cơ bản nào? | 0.108742 | overview | không | summary_only | có | - MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [1]<br>- &P ↑ Khi bạn nhập văn bản vào một ô trống, tiêu đề và chân trang sẽ được tự động thêm vào. [2]<br>- Trang tính: Nhập kho Hiện trạng: Tiến hành nhập kho AMS phát sinh 18 thùng bị đẩy ra cổng NG. [3]<br>- == Thông tin về quy trình sản xuất ST-CO- Đến đăng ký Ngày phát sinh/ghi nhận: Áp dụng cho các lỗi ST/CO và thực tích phát sinh trong quá trình sản xuất AMS; file hiện tại chưa ghi ngày cụ thể cho từng bước. [4]<br>- [DOCUMENT ARCHITECTURE & SUMMARY] [5]<br>Ghi chú: trả lời ở mức tổng quan. |
| A3<br>Quy trình xử lý các sự cố và bất thường phát sinh trong quá trình vận hành và sản xuất nói chung được thực hiện như thế nào? | 0.100182 | overview | không | summary_only | có | PRECHECKS:<br>- No grounded evidence retrieved for this section.<br>STEPS:<br>- No grounded evidence retrieved for this section.<br>POSTCHECKS:<br>- No grounded evidence retrieved for this section.<br>LIMITATIONS: provider_synthesis_unavailable<br>Ghi chú: trả lời ở mức tổng quan. |
| A4<br>Việc ghi nhận tiến độ bắt đầu và hoàn thành công đoạn sản xuất của sản phẩm được thực hiện như thế nào từ dây chuyền lên hệ thống? | 0.082044 | overview | không | summary_only | có | - MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [1]<br>- Bộ phận đã tạo raBộ phận Công nghệ Sản xuất Phòng Kỹ thuật Sản xuất số 2, Ban Kỹ thuật Sản xuất 21 Được tạo bởi: Kazuma Tsutsumi Chuỗi tiêu đề Công ty TNHH Giải pháp Tài liệu KYOCERA Văn bản chân trang Bộ điều khiển xử lý vật liệu Phiên bản <0.01> Hướng dẫn sử dụng (Matecon) - Dùng để điều khiển AGV / ACR / CTU - 作成 審査 承認 Confidential © 2022 KYOCERA Document Solutions Inc. [2]<br>- Phân loại lỗi chi tiết: Nhóm 1: Lỗi sai lệch dữ liệu hệ thống (1 thùng - 9702%) Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất Nhóm 2: Lỗi Camera đọc mã QR ngoại quan các mặt (6 thùng) Hiện trạng: Báo các mã lỗi bắt đầu bằng 0201..., nguyên nhân do Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM. [3]<br>- == Thông tin về quy trình sản xuất ST-CO- Đến đăng ký Ngày phát sinh/ghi nhận: Áp dụng cho các lỗi ST/CO và thực tích phát sinh trong quá trình sản xuất AMS; file hiện tại chưa ghi ngày cụ thể cho từng bước. [4]<br>- [DOCUMENT ARCHITECTURE & SUMMARY] [5]<br>Ghi chú: trả lời ở mức tổng quan. |
| A5<br>Quy trình quản lý và chuyển đổi khi có sự thay đổi thiết kế hoặc thay đổi quy trình sản xuất diễn ra ra sao? | 0.075622 | overview | không | summary_only | có | PRECHECKS:<br>- No grounded evidence retrieved for this section.<br>STEPS:<br>- No grounded evidence retrieved for this section.<br>POSTCHECKS:<br>- No grounded evidence retrieved for this section.<br>LIMITATIONS: provider_synthesis_unavailable<br>Ghi chú: trả lời ở mức tổng quan. |
| H1<br>Các thành phần hệ thống gồm những gì và chúng liên kết với nhau thế nào? | 0.075421 | overview | không | summary_only | có | - MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [1]<br>- Một hệ thống điều khiển đưa ra các chỉ dẫn lái xe cho AGV/ACR/CTU, giám sát trạng thái hoạt động của chúng ... [2]<br>- Phân loại lỗi chi tiết: Nhóm 1: Lỗi sai lệch dữ liệu hệ thống (1 thùng - 9702%) Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất Nhóm 2: Lỗi Camera đọc mã QR ngoại quan các mặt (6 thùng) Hiện trạng: Báo các mã lỗi bắt đầu bằng 0201..., nguyên nhân do Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM. [3]<br>- Thông tin về bảng T_IF_PROD_RESULT Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong file hiện tại; lỗi được ghi nhận khi VN liên kết lượng lớn dữ liệu tiêu hao linh kiện. [4]<br>- [DOCUMENT ARCHITECTURE & SUMMARY] [5]<br>Ghi chú: trả lời ở mức tổng quan. |
| H2<br>Vật tư đi từ kho vào chuyền qua những bước nào? | 0.064881 | overview | không | summary_only | có | - &P ↑ Khi bạn nhập văn bản vào một ô trống, tiêu đề và chân trang sẽ được tự động thêm vào. [1]<br>- Xử lý ngày 17.06.2026: Đối với nhóm 1, in lại EDI(xóa thông tin Lot sản xuất), xóa dữ liệu đã đọc vào trên SQL và MOM, tiến hành nhập kho lại. [2]<br>- [DOCUMENT ARCHITECTURE & SUMMARY] [3]<br>- == Thông tin về quy trình sản xuất ST-CO- Đến đăng ký Ngày phát sinh/ghi nhận: Áp dụng cho các lỗi ST/CO và thực tích phát sinh trong quá trình sản xuất AMS; file hiện tại chưa ghi ngày cụ thể cho từng bước. [4]<br>- MES／MOM説明 MESとは ➤製造業の情報管理は、「計画層」「実行層」「制御層」の3つのレイヤーに分けて考えられますが、 MESはこのうち「実行層」に位置しています。計画層で立てられた生産計画を現場で実行可能な形に 変換し、製造現場に指示を送ることで、スムーズな運営を実現します。 [5]<br>Ghi chú: trả lời ở mức tổng quan. |
| H3<br>Khi có lỗi xảy ra thì xử lý theo trình tự nào? | 6.965456 | focused | không | hybrid | không | - Thông tin về bảng T_IF_PROD_RESULT Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong file hiện tại; lỗi được ghi nhận khi VN liên kết lượng lớn dữ liệu tiêu hao linh kiện. [1]<br>- &P ↑ Khi bạn nhập văn bản vào một ô trống, tiêu đề và chân trang sẽ được tự động thêm vào. [2]<br>- Khôi phục lỗi (khởi động lại) Chương này mô tả quy trình khắc phục khi xảy ra lỗi AGV. [3]<br>- t nơi xảy ra lỗi (trước hoặc sau đó đều được chấp nhận) ②Lỗi trong quá trình đảo ngược ・Khôi phục từ địa chỉ ngay trước khi đảo ngược. [4]<br>- Không chỉnh hoặc chạy tiếp theo cảm tính; phải xác định lỗi đang xảy ra ở hệ thống nào. [5]<br>LIMITATIONS: incomplete_query_term_coverage |

Câu held-out là H1–H3, không nằm trong 10 câu FIX 3.

- A1–A5: không còn abstain, không còn `no_document_summaries`, đều có dòng ghi chú tổng quan. `effective_path` là `summary_only`.
- H1 và H2: `summary_only`, có ghi chú tổng quan, không abstain. H3 xếp `focused` và đi đường `hybrid` vì câu chứa từ `trình tự` và dài hơn, nên không vào overview. H3 vẫn trả lời được.
- Không câu nào lẫn XML `xmlns`.
- Chất lượng trích xuất: A3 và A5 chỉ có khung `PRECHECKS/STEPS/POSTCHECKS` trống cộng ghi chú, vì summary của tài liệu liên quan chỉ có 1500 ký tự đầu. Đây là giới hạn của summary tiền tố, không phải lỗi provenance.

## 5. Đề xuất (4) của báo cáo điều tra

Không làm trong FIX này. Phase 2.

## 6. Kết quả `pytest tests/`

`pytest -q tests` trong 548.92 giây: **3137 passed, 3 skipped, 4 failed**. Không có test mới nào đỏ. `tests/test_rag_v2_chunking.py`, `tests/test_rag_v2_summary_provenance.py`, `tests/test_rag_v2_summary_first.py` đều nằm trong số passed.

Bốn lỗi không nằm trong diff của FIX 5, cùng lớp đã ghi ở FIX 2–4: `uv lock --check`, pin checksum model cục bộ, pip không thấy `streamlit>=1.60.0`, và test OCR phụ thuộc thứ tự.

`scripts/check_docs.py`: `DOCUMENTATION_CONTRACT=PASS`.

## 7. Hướng dẫn chạy trên máy khác (mỗi máy chạy độc lập)

Số liệu ở mục 3 (`summary_count` 10, số trường sẽ điền 20, bỏ qua do mơ hồ 0, bỏ qua do thiếu giá trị ở chunk thân 0) chỉ đúng trên máy đã lập báo cáo này (máy công ty, tên máy `KDTVN-PC0575`). Máy khác ingest tập tài liệu khác nhau nên số liệu có thể khác. Khác số là bình thường, không tự cho là lỗi.

Quy tắc bắt buộc khi sang máy khác:

- Luôn chạy thử chỉ đọc trước (mặc định của lệnh, không ghi gì), đối chiếu số liệu với mục 3, ghi lại sự khác biệt và nguyên nhân (tập tài liệu ingest khác nhau).
- Tuyệt đối không chạy ghi thật (`--apply`) khi chưa được duyệt riêng.
- Chỉ ghi thật khi số liệu chạy thử hợp lý (không có ca mơ hồ bất thường), đã sao lưu tệp `library.sqlite` của chính máy đó, và đã bật cờ `AIOS_RAG_V2_SUMMARY_PROVENANCE`.
- Mỗi máy chạy độc lập trên index của chính máy đó. Không chép tệp `sqlite` từ máy này sang máy khác để áp số liệu.
- Khi chạy, ghi tên máy (kết quả lệnh `hostname`) cùng đường dẫn index vào sổ làm việc, để sau này đối chiếu biết số liệu thuộc máy nào.

Lệnh chạy thử chỉ đọc (đường dẫn là tham số, dùng đường dẫn tương đối trong kho, thay bằng index của máy đó):

```
uv run --no-sync --group dev python scripts/backfill_summary_provenance.py local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --json
```

Trước khi ghi thật (khi đã được duyệt): sao chép tệp `library.sqlite` sang chỗ khác, ghi lại giờ sao lưu và tên máy, rồi mới chạy thêm cờ `--apply`.

Kết quả đối chiếu ngày 2026-09-25 trên máy `KDTVN-PC0575`: chạy thử chỉ đọc cho đúng `summary_count` 10, số trường sẽ điền 20, bỏ qua do mơ hồ 0, bỏ qua do thiếu giá trị ở chunk thân 0 — khớp mục 3. Không chạy ghi thật.
