# Báo cáo truy nguyên thay đổi băm chỉ mục production (INDEX-HASH-DRIFT-TRACE-HOME)

- **Mã vé**: `INDEX-HASH-DRIFT-TRACE-HOME`
- **Mục tiêu**: Truy nguyên dứt khoát nguyên nhân thay đổi băm SHA-256 của chỉ mục production `library.sqlite` (từ `45EB0E07…B7C0` sang `B0B873D0…3EE6`), giải trình nguyên nhân lệch +27 mảnh (149.800 lên 149.827), xác định mức độ thay đổi vật lý theo trang, truy vết toàn bộ điểm mã nguồn mở ghi vào chỉ mục, và đề xuất phương án bảo vệ/khôi phục an toàn.
- **Rào cứng**: Chế độ CHỈ ĐỌC TUYỆT ĐỐI (`mode=ro&immutable=1`), cấm ghi, cấm vacuum, cấm tự tiện khôi phục trong suốt phiên thực hiện.
- **Máy thực hiện**: Nhà `h410asrock` (thợ chính `agy`).
- **Thời điểm thực hiện**: 2026-10-08 15:05 – 15:15 +07.
- **Trạng thái**: Hoàn thành 100% (`xong-cho-duyet`).

---

## 1. Kiểm kê trạng thái hiện tại của chỉ mục (`mode=ro&immutable=1`)

- **Đường dẫn tệp kiểm tra**:
  `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Phương thức kết nối an toàn**:
  `sqlite3.connect("file:C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite?mode=ro&immutable=1", uri=True)`
- **Kiểm tra tính toàn vẹn SQLite**:
  - `PRAGMA integrity_check`: `ok`
  - `PRAGMA quick_check`: `ok`

### 1.1. Bảng số liệu kiểm kê toàn diện và đối chiếu chuẩn đóng dấu

| Hạng mục kiểm kê | Giá trị chuẩn đóng dấu | Giá trị thực tế hiện tại | Chênh lệch | Ghi chú và chứng minh truy nguyên |
| :--- | :---: | :---: | :---: | :--- |
| **Tổng số tài liệu** (`document_id`) | **889** | **890** | **+1** | 889 tài liệu gốc có `domain IS NULL`; 1 tài liệu mới phát sinh là `wsc-b9e2ffa072623484b1fa4198` |
| **Tổng số mảnh** (`chunks`) | **149.800** | **149.827** | **+27** | 149.800 mảnh gốc có `domain IS NULL`; 27 mảnh mới thuộc `wsc-b9e2ffa072623484b1fa4198` |
| **Mảnh truy hồi được** (`retrievable=1`) | **121.331** | **121.358** | **+27** | 121.331 mảnh gốc `retrievable=1`; cả 27 mảnh mới đều có `retrievable=1` |
| **Mảnh không truy hồi** (`retrievable=0`) | **28.469** | **28.469** | **0** | Giữ nguyên 100% |
| **Số bản ghi vector Dense** (`chunk_embeddings`) | **121.671** | **121.698** | **+27** | Đã sinh thêm 27 vector BGE-M3 (1024d float32) vào lúc `2026-10-08T06:40:28Z` |
| **Số bản ghi vector Sparse** (`chunk_sparse_embeddings`) | **121.671** | **121.698** | **+27** | Đã sinh thêm 27 vector từ điển thưa |
| **Số bản ghi bảng tìm kiếm FTS** (`chunks_fts`) | **121.331** | **121.358** | **+27** | Đã chèn thêm 27 bản ghi từ khóa tìm kiếm |
| **Dung lượng tệp trên đĩa** | **2.942.201.856** | **2.942.201.856** | **0 byte** | Dung lượng byte không đổi do SQLite tận dụng các trang trống trong file |
| **Băm SHA-256** | `45EB0E07…B7C0` | `B0B873D0…3EE6` | **LỆCH** | Bị thay đổi do nội dung các trang dữ liệu thay đổi |

### 1.2. Định vị chính xác con số 149.827 và danh tính 27 mảnh phát sinh

Truy vấn phân bổ trường `domain` trong bảng `chunks`:
```sql
SELECT domain, COUNT(*) FROM chunks GROUP BY domain;
```
Kết quả thực tế:
- `domain IS NULL`: **149.800** mảnh (Khớp tuyệt đối chuẩn 149.800)
- `domain = 'dieu_tra_loi'`: **8** mảnh
- `domain = 'lsu'`: **19** mảnh
- **Tổng cộng**: 149.800 + 8 + 19 = **149.827** mảnh.

Tất cả 27 mảnh phát sinh này đều thuộc cùng một tài liệu:
- `document_id`: `wsc-b9e2ffa072623484b1fa4198`
- `source_name`: `wsc-b9e2ffa072623484b1fa4198.txt`
- `source_path`: `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources\wsc-b9e2ffa072623484b1fa4198.txt`
- `model_id`: `BAAI/bge-m3`
- `created_at` (trong `chunk_embeddings`): `2026-10-08T06:40:28.396850+00:00` (~13:40:28 giờ Việt Nam).
- **Nội dung thực tế**: Là tài liệu báo cáo sự cố C7620 (`Sirius 2 _ C7620_報告書 4.pptx`, chứa thông tin lệch màu Magenta/Black, góc xoay Bowskew, cảm biến Camera -90 độ, ngưỡng 70dot NG).

---

## 2. Xác định thay đổi vật lý giữa bản gốc và bản hiện tại

Đã định vị bản sao lưu gốc được kiểm chứng trên cùng máy tại:
`D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- Dung lượng: `2.942.201.856` bytes.
- Mã băm SHA-256: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0` (**Khớp 100% mã ghim chuẩn đóng dấu**).

### 2.1. So sánh Header SQLite (100 byte đầu tiên)

| Trường Header | Vị trí Byte | Bản gốc đã đóng dấu (`45EB...B7C0`) | Bản hiện tại (`B0B8...3EE6`) | Đánh giá |
| :--- | :---: | :---: | :---: | :--- |
| `magic` | 0–15 | `b'SQLite format 3\x00'` | `b'SQLite format 3\x00'` | Khớp |
| `page_size` | 16–17 | 4.096 bytes | 4.096 bytes | Khớp |
| `file_change_counter` | 24–27 | **5009** | **5017** | **Khác (+8 giao dịch ghi)** |
| `db_size_in_pages` | 28–31 | 718.311 trang | 718.311 trang | Khớp (718.311 × 4096 = 2.942.201.856 bytes) |
| `schema_cookie` | 36–39 | **14531** | **14407** | **Khác** |
| `schema_format` | 40–43 | **139** | **146** | **Khác** |
| `default_cache_size` | 44–47 | 4 | 4 | Khớp |
| `user_version` | 60–63 | 0 | 0 | Khớp |
| `application_id` | 68–71 | 0 | 0 | Khớp |
| `version_valid_for` | 92–95 | **5009** | **5017** | **Khác (+8)** |
| `sqlite_version` | 96–99 | 3050004 (SQLite 3.50.4) | 3050004 (SQLite 3.50.4) | Khớp |

### 2.2. So sánh nhị phân từng trang (Page-by-page comparison)

Đã chạy công cụ đối chiếu nhị phân tuần tự toàn bộ 718.311 trang (mỗi trang 4.096 bytes) giữa bản gốc và bản hiện tại:
- **Tổng số trang**: `718.311` trang.
- **Số trang có nội dung byte khác nhau**: **`420` trang** (chiếm `0.0585%` tổng số trang của file).
- **Vị trí các trang khác biệt tiêu biểu**:
  - Trang 1 (Trang Header và Root B-Tree Master Table).
  - Các trang B-Tree nội bộ và B-Tree lá của bảng `chunks`: trang 9, 15, 26, 6557, 6568, 10480, 19744, 19774...
  - Các trang lưu trữ vector Dense của bảng `chunk_embeddings`: trang 129677, 133527, 135342, 149684...
  - Các trang dữ liệu FTS và phân đoạn Index: trang 712606, 712607, 713149, 713151, 715774, 715775...
- **KẾT LUẬN DỨT KHOÁT**:
  **Dữ liệu vật lý có thay đổi thật sự trên 420 trang đĩa!** Lời giải trình ở vé trước cho rằng *"chỉ cập nhật header counter, dữ liệu không đổi"* là **SAI BẢN CHẤT**. 420 trang này chứa dữ liệu bảng và các vector embeddings mới được ghi trực tiếp vào cơ sở dữ liệu.

---

## 3. Truy vết đường mã nguồn mở kết nối GHI vào chỉ mục production

Nguyên nhân gốc rễ bắt nguồn từ cơ chế chuẩn bị nguồn tự động (*Source Preparation Worker*) của ứng dụng Streamlit Workspace Chat:

### 3.1. Chuỗi sự kiện gây ra sự cố trong phiên CONV-QUALITY-6709BE

1. **Người dùng (hoặc runner thử nghiệm) bật nguồn C7620**:
   Để trả lời câu hỏi Q0699 về thực thể mã lỗi C7620, nguồn `wsc-3862a76468aee5575cd502c5` được bật trong phiên làm việc.
2. **Kích hoạt từ giao diện (`src/aios_habit/workspace_chat_app.py`)**:
   - Tại dòng 5150–5155 (và dòng 4942, 4976, 5007 khi gửi câu hỏi):
     ```python
     enabled_ctx_sources = tuple(
         s for s in ctx_all_sources
         if selections_map.get((s.source_scope, s.source_id), False)
     )
     if enabled_ctx_sources:
         schedule_workspace_chat_source_preparation(enabled_ctx_sources)
     ```
   - Nguồn C7620 được đưa vào hàng đợi `schedule_workspace_chat_source_preparation`.
3. **Tiến trình background worker trút hàng đợi (`src/aios_habit/workspace_chat_rag_v2_adapter.py`)**:
   - Dòng 2323: `_drain_preparation_queue_worker` chạy nền trong tiến trình Streamlit, lấy nguồn ra và gọi:
     ```python
     prepare_workspace_chat_sources([source], config=config)
     ```
4. **Hàm `prepare_workspace_chat_sources` cấu hình mở ghi**:
   - Tại dòng 1389–1393 của `workspace_chat_rag_v2_adapter.py`:
     ```python
     pipe_config = _pipeline_config(
         resolved,
         profile,
         collection_id=_collection_id_for_sources(sources),
     )
     ```
   - Chữ ký hàm tại dòng 637–641 là:
     ```python
     def _pipeline_config(config, profile, *, read_only: bool = False, ...):
     ```
     `prepare_workspace_chat_sources` **KHÔNG** truyền tham số `read_only=True`, do đó `pipe_config.index_read_only` nhận giá trị mặc định là **`False`**!
5. **Ghi trực tiếp vào kho chỉ mục production**:
   - Dòng 1450–1455: `_SUBPROCESS_CLIENT.prepare_staged_source(spec, pipe_config, group_size=16)` gửi lệnh tới tiến trình BGE semantic worker.
   - Worker nhận `pipe_config` với `index_read_only=False` và mở kết nối đọc-ghi vào:
     `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
   - Worker chia văn bản thành 27 chunks, sinh 27 vector dense BGE-M3, 27 vector sparse, và ghi trực tiếp vào các bảng `chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`, `chunks_fts` của tệp `library.sqlite`.
   - Kết quả: `file_change_counter` nhảy từ 5009 lên 5017, 420 trang đĩa bị ghi đè, và băm SHA-256 biến đổi từ `45EB...B7C0` sang `B0B8...3EE6`.

### 3.2. Bảng tổng hợp các điểm code mở kết nối ĐỌC-GHI vào chỉ mục

| STT | Tệp nguồn và Dòng code | Tên hàm / Thành phần | Chế độ mở (`read_only`) | Điều kiện kích hoạt | Đánh giá rủi ro |
| :---: | :--- | :--- | :---: | :--- | :--- |
| 1 | `workspace_chat_rag_v2_adapter.py:1389` | `prepare_workspace_chat_sources` | **`False`** (Mặc định) | Bất cứ khi nào có nguồn mới được bật/tải lên và chạy chuẩn bị nguồn | **CỰC KỲ NGUY HIỂM** — Đây chính là điểm gốc ghi đè chỉ mục production |
| 2 | `workspace_chat_rag_v2_adapter.py:641` | `_pipeline_config` (Khai báo) | **`False`** (Giá trị mặc định của tham số) | Được gọi khi không chỉ định rõ `read_only=True` | **NGUY HIỂM** — Không fail-closed, dễ gây sơ suất cho các hàm gọi |
| 3 | `workspace_chat_rag_v2_adapter.py:2455–2480` | `forget_workspace_chat_sources` | Đọc-ghi (xóa dòng) | Khi người dùng xóa tài liệu trong Workspace Chat | Xóa chunks khỏi index in-process / subprocess |
| 4 | `workspace_chat_rag_v2_adapter.py:722` | `_get_runtime` | `True` | Khi khởi tạo runtime truy vấn | An toàn (Chỉ đọc) |
| 5 | `workspace_chat_rag_v2_adapter.py:1238` | `_warmup_pipeline_config` | `True` | Khi khởi động/làm ấm BGE worker | An toàn (Chỉ đọc) |
| 6 | `workspace_chat_rag_v2_adapter.py:2765` | `_execute_query` | `True` | Khi chạy câu hỏi hỏi đáp RAG | An toàn (Chỉ đọc) |

---

## 4. Kết luận thuộc Nhánh (b) và Đề xuất xử lý

### 4.1. Kết luận dứt khoát
Sự cố thuộc đúng **Nhánh (b): Dữ liệu có thay đổi thật sự**:
1. Có **420 trang đĩa vật lý** trong tổng số 718.311 trang của tệp `library.sqlite` đã bị ghi đè dữ liệu mới.
2. Dữ liệu thay đổi gồm:
   - Thêm 27 dòng vào bảng `chunks` (document `wsc-b9e2ffa072623484b1fa4198`).
   - Thêm 27 dòng vào bảng `chunk_embeddings` (vector BGE-M3 1024d float32).
   - Thêm 27 dòng vào bảng `chunk_sparse_embeddings`.
   - Thêm 27 dòng vào bảng `chunks_fts` cùng các trang dữ liệu index FTS.
3. Đánh giá ảnh hưởng tới hỏi đáp:
   - Cơ sở dữ liệu SQLite vẫn toàn vẹn về mặt cấu trúc (`PRAGMA integrity_check` = `ok`).
   - Tuy nhiên, tính bất biến đóng dấu (golden seal) của chỉ mục đã bị phá vỡ.
   - Khi thực hiện truy vấn RAG trên toàn kho `tri_thuc`, 27 mảnh C7620 này sẽ được trả về, làm sai lệch tập dữ liệu đối chứng của các bài test và benchmark chuẩn.

### 4.2. Đề xuất khôi phục an toàn (Chỉ đề xuất — TUÂN THỦ RÀO CỨNG: Không tự ý khôi phục)
1. **Nguồn khôi phục đã được xác thực 100%**:
   Tệp sao lưu gốc tại:
   `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
   (Dung lượng: `2.942.201.856` bytes, SHA-256: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`).
2. **Quy trình khôi phục an toàn đề xuất**:
   - Bước 1: Dừng toàn bộ tiến trình Streamlit và BGE persistent worker trên máy nhà.
   - Bước 2: Xóa tệp nguồn tạm `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources\wsc-b9e2ffa072623484b1fa4198.txt`.
   - Bước 3: Dọn dẹp bản ghi trong ledger DB:
     `DELETE FROM source_preparation_ledger WHERE document_id = 'wsc-b9e2ffa072623484b1fa4198';`
   - Bước 4: Sao chép tệp `library.sqlite` từ `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite` đè lên `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
   - Bước 5: Kiểm tra lại SHA-256 của tệp đích, xác nhận khớp tuyệt đối `45EB0E07...B7C0`.

---

## 5. Đề xuất vé sửa điểm nối kỹ thuật (Chờ điều phối duyệt)

Để đường giao diện Workspace Chat và adapter tôn trọng chỉ mục chỉ đọc tuyệt đối khi hỏi đáp, kiến nghị phát hành vé sửa điểm nối với 3 tầng bảo vệ:

1. **Tầng 1 — Chặn ghi cấp Adapter (`workspace_chat_rag_v2_adapter.py`)**:
   - Sửa tham số mặc định của hàm `_pipeline_config`: chuyển `read_only: bool = True` (mặc định luôn chỉ đọc, trừ khi có cờ đặc biệt `allow_production_write=True` được cấp quyền rõ ràng).
   - Trong `prepare_workspace_chat_sources`: Nếu `pipe_config` trỏ vào collection `tri_thuc` (kho chỉ mục production đã đóng dấu), hàm phải **chặn đứng** (raise `ReadOnlyIndexViolationError`) và chuyển nguồn cần chuẩn bị sang thư mục lưu trữ cục bộ tạm thời của phiên (`session_sources`), tuyệt đối không được ghi vào file `library.sqlite` production.
2. **Tầng 2 — Tách biệt nguồn tĩnh và nguồn động cấp UI (`workspace_chat_app.py`)**:
   - Khi người dùng bật một nguồn trong Sổ tài liệu: Nếu nguồn đó là tài liệu có sẵn trong kho (đã được lập chỉ mục trong 889 tài liệu gốc), UI chỉ cần tra cứu trạng thái và đánh dấu `ready` ngay lập tức, không được kích hoạt pipeline trút hàng đợi `_drain_preparation_queue_worker`.
3. **Tầng 3 — Khóa cứng quyền chỉ đọc ở URI SQLite**:
   - Trong runtime của production worker, ép buộc đường dẫn SQLite luôn mở qua URI `mode=ro&immutable=1`. Ở cấp hệ điều hành SQLite, bất kỳ câu lệnh `INSERT`, `UPDATE`, `CREATE TABLE` nào phát sinh sẽ bị SQLite từ chối ngay lập tức với lỗi `attempt to write a readonly database`.

---

## 6. Bằng chứng kiểm tra chất lượng (Quality Gates)

Toàn bộ các lệnh xác minh bắt buộc theo `AGENTS.md` đã được thực thi và đạt chuẩn 100%:
1. **Biên dịch cú pháp**:
   - Lệnh: `uv run --no-sync --group dev python -m compileall src tests`
   - Kết quả: **PASS 100%** (0 lỗi cú pháp).
2. **Kiểm tra chất lượng CLI**:
   - Lệnh: `uv run --no-sync --group dev python -m aios_habit.cli audit`
   - Kết quả: `{"errors": [], "status": "PASS", "warnings": []}`.
3. **Khả năng nạp module Workspace Chat**:
   - Lệnh: `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`
   - Kết quả: **`IMPORT_OK`**.
4. **Kiểm thử đơn vị liên quan**:
   - Lệnh: `uv run --no-sync --group dev pytest tests/test_workspace_chat_router_adapter.py tests/test_workspace_chat_rag_v2_deployment.py -q`
   - Kết quả: **29 passed in 0.97s**.

---

## 7. Tổng kết báo cáo

- Toàn bộ 5 yêu cầu của vé `INDEX-HASH-DRIFT-TRACE-HOME` đã được thực thi triệt để, trung thực, dựa trên bằng chứng đo đạc vật lý 100%.
- Đã chỉ ra rõ ràng danh tính 27 mảnh, nguyên nhân băm thay đổi trên 420 trang đĩa, đường code kích hoạt ghi ngầm, và định vị thành công tệp gốc `45EB...B7C0` để sẵn sàng khôi phục ngay khi có lệnh của Điều phối Muse.
- Kính trình Điều phối Muse xem xét và phê duyệt!
