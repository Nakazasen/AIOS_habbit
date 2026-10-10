# BÁO CÁO CHẨN ĐOÁN: MISSING5-RETRIEVAL-DIAG-HOME

- **Mã vé**: `MISSING5-RETRIEVAL-DIAG-HOME`
- **Thợ thực hiện**: `DEFAULT` (agy — thợ chính, máy nhà `h410asrock`)
- **Nhánh thực hiện**: `phieu-viec/rag-fix1`
- **Loại vé**: CHẨN ĐOÁN CHỈ ĐỌC (Không ghi chỉ mục, không sửa mã, không đổi ngưỡng, không đổi bộ đề/thang chấm).
- **Trạng thái**: HOÀN THÀNH TOÀN DIỆN 5 MỤC THEO ĐÚNG HỢP ĐỒNG

---

## Tóm tắt điều hành & Phát hiện cốt lõi

Vé chẩn đoán chỉ đọc `MISSING5-RETRIEVAL-DIAG-HOME` đã truy vết tận gốc nguyên nhân vì sao sau khi nạp 5 tệp dữ liệu nguồn (`2026_08_Error.csv`, `2026_08_Error_BowOverAdjust.csv`, `2026_08_Spec.csv`, `2026_08_UnitTest.csv`, `AI cảnh báo lỗi LSU.pptx`), nhóm 7 câu hỏi đích chỉ đạt **1.0/21 điểm** (trong đó câu `Q0824` đạt 1.0 điểm giả do hàm chấm chuỗi "ng", thực chất cả 7 câu đều bị cổng kiểm chứng chặn ở chế độ `local_extractive_provider_not_called`):

1. **Lỗ hổng vector**: Có **26.907 trên tổng số 27.529 mảnh có thể truy hồi** của 2 tệp lớn (`2026_08_Error_BowOverAdjust.csv` và `2026_08_Spec.csv`) **hoàn toàn KHÔNG có vector dày (dense) và vector thưa (sparse)** (0/26.907). Chỉ có 622 vector được ghi cho 3 tệp nhỏ. Đối chiếu 889 tài liệu cũ cho thấy quy trình chuẩn yêu cầu độ phủ vector đạt **100%** trên số mảnh có thể truy hồi.
2. **Khớp số lượng mảnh**: Con số 31.233 mảnh tổng nạp vào production gồm đúng **27.529 mảnh có thể truy hồi (`retrievable = 1`)** và **3.704 mảnh ngữ cảnh cha (`retrievable = 0`, `representation_role="parent"`)**. Đây là cấu trúc phân cấp chuẩn của `StructureAwareChunker` (27.529 + 3.704 = 31.233), không có mảnh nào bị rơi rụng.
3. **Lỗi bóc tách PPTX (Q0620)**: Số liệu đích `25.42% -> 49.49%` và `2026年3月` nằm trọn vẹn trong **lời thoại ghi chú của diễn giả (Speaker Notes - `ppt/notesSlides/notesSlide1.xml`)**, chứ không nằm trong slide shapes hay bảng biểu. Bộ chuyển đổi PPTX hiện hành chỉ đọc slide shapes nên **dữ liệu đích hoàn toàn không tồn tại trong bất kỳ mảnh nào của production**.
4. **Lỗi chia mảnh CSV hàng dài (Q0824)**: Dòng 5 và 6 của `2026_08_UnitTest.csv` dài hơn 5.000 ký tự (hơn 250 cột). Bộ chia mảnh cắt lát cứng 1.000 ký tự mà không lặp lại tiêu đề cột. Mảnh chứa mã Serial `61C1068E7022` nằm ở đầu dòng (ký tự 0–1000) hoàn toàn không chứa kết quả phán định (`Judge:Black: OK`, `Judge:Cyan: NG`, v.v.), vốn nằm ở cuối dòng (ký tự 4900–5000).
5. **Nghịch lý câu hỏi thống kê toàn tệp CSV (Q0849, Q0850, Q1034, Q0843)**: Cả 4 câu hỏi này đều yêu cầu tổng hợp thống kê toàn tệp (đếm tổng 3.153 bản ghi, phân bố 1.304 Yellow / 1.035 Cyan / 814 Magenta, ngày lỗi nhiều nhất 2026/08/11 với 34 bản ghi, cặp giới hạn phổ biến nhất 370 mA - 520 mA trên 4.399 bản ghi). Cơ chế RAG top-k mảnh văn bản rời rạc (k=8–15) về mặt toán học **không thể tính toán chính xác số liệu thống kê toàn tệp**.
6. **Lệch khối tri thức giữa đường đo và giao diện (Q0668)**: Đường đo chạy trên bộ chỉ mục hợp nhất `tri_thuc` (có 151 mảnh của `3V2ND19040`, truy hồi đạt Hạng 1, điểm 1.5). Trong khi đó, giao diện Streamlit khi chạy thử đã chọn khối `block=lsu`. Trong phân chia khối tri thức, `3V2ND19040` được xếp vào khối `dieu_tra_loi` (151 mảnh) và có **0 mảnh trong khối `lsu`**. Bộ lọc khối `lsu` đã chặn đứng tệp đích, khiến giao diện phải dùng nguồn thay thế và trả về "chưa đủ bằng chứng".

---

## Mục 1 — Kiểm kê chỉ đọc trên Production DB

- **Phương thức mở**: SQLite Read-Only URI (`file:C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite?mode=ro`).
- **Tổng quy mô Production**:
  * Tài liệu (`DISTINCT document_id`): **894**
  * Tổng số mảnh (`chunks`): **181.033**
  * Số mảnh có thể truy hồi (`retrievable = 1`): **148.860**
  * Số mảnh ngữ cảnh cha (`retrievable = 0`): **32.173**
  * Vector dày (`chunk_embeddings`): **122.293**
  * Vector thưa (`chunk_sparse_embeddings`): **122.293**
  * Bảng FTS5: `chunks_fts` đồng bộ 100% với 181.033 mảnh.

### 1.1 Thống kê chi tiết 5 tệp mới nạp

| Tên tệp nguồn | Document ID | Tổng mảnh | Mảnh truy hồi (`ret=1`) | Mảnh cha (`ret=0`) | Vector dày | Vector thưa | Tỷ lệ phủ vector |
|---|---|---|---|---|---|---|---|
| `2026_08_Error.csv` | `wsc-03bf475fc208c02f741d4013` | 597 | 517 | 80 | 517 | 517 | **100.0%** |
| `2026_08_Error_BowOverAdjust.csv` | `wsc-8eb2a5d21b75fa88307223b1` | 25.213 | 22.054 | 3.159 | 0 | 0 | **0.0% (THIẾU 22.054)** |
| `2026_08_Spec.csv` | `wsc-d4df39c14101e40ebad88a91` | 5.303 | 4.853 | 450 | 0 | 0 | **0.0% (THIẾU 4.853)** |
| `2026_08_UnitTest.csv` | `wsc-4bd2e353e19864fe786358c5` | 112 | 97 | 15 | 97 | 97 | **100.0%** |
| `AI cảnh báo lỗi LSU.pptx` | `wsc-f6782ff77c152a5c9a416ad8` | 8 | 8 | 0 | 8 | 8 | **100.0%** |
| **TỔNG CỘNG 5 TỆP MỚI** | — | **31.233** | **27.529** | **3.704** | **622** | **622** | **2.26%** |

*Giải trình con số 3.704 mảnh*: Báo cáo vé trước liệt kê 27.529 mảnh có thể truy hồi; 3.704 mảnh còn lại chính xác là các mảnh ngữ cảnh cha (`retrievable = 0`) được tạo bởi `StructureAwareChunker` nhằm phục vụ việc mở rộng ngữ cảnh khi truy hồi mảnh con.

### 1.2 Đối chiếu với 889 tài liệu cũ trong kho

| Nhóm tài liệu | Số tài liệu | Tổng số mảnh | Mảnh truy hồi (`ret=1`) | Mảnh cha (`ret=0`) | Vector dày | Tỷ lệ phủ vector |
|---|---|---|---|---|---|---|
| Toàn bộ 889 tài liệu cũ | 889 | 149.800 | 121.331 | 28.469 | 121.671 | **100.28%** |
| Mẫu XLSX cũ (sirius2_beam径確認...) | 1 | 3.328 | 3.013 | 315 | 3.013 | **100.0%** |
| Mẫu PPTX cũ (C7620_報告版 4...) | 1 | 27 | 27 | 0 | 27 | **100.0%** |
| Mẫu PDF cũ (DP IF ASSY...) | 1 | 24 | 24 | 0 | 24 | **100.0%** |

**Kết luận Mục 1**: Quy trình nạp chuẩn của hệ thống **BẮT BUỘC 100% các mảnh có thể truy hồi (`retrievable=1`) phải có vector dày và vector thưa**. Việc chỉ nạp 622 vector cho 3 tệp nhỏ và bỏ qua 26.907 mảnh của 2 tệp lớn là vi phạm quy chuẩn nạp, khiến 2 tệp lớn hoàn toàn không thể tham gia vào kênh tìm kiếm vector ngữ nghĩa (dense semantic search).

---

## Mục 2 — Truy vết 8 câu hỏi mục tiêu trên đường đo

Dữ liệu thô được ghi nhận trực tiếp từ `scratch/task2_trace_8_questions_raw.json` khi chạy trên pipeline RAG v2 production (`bge_m3_hybrid` CPU-only, preload cache):

| Mã câu | Tệp nguồn đích | Xuất hiện Top-15 | Thứ hạng Top-15 | Có trong Evidence Pack | Độ phủ từ vựng (`cov / th`) | Điểm ngữ nghĩa (`max / th`) | Cổng từ vựng | Cổng ngữ nghĩa | Chế độ phản hồi | Phân loại nguyên nhân |
|---|---|---|---|---|---|---|---|---|---|---|
| `Q0849` | `2026_08_Error_BowOverAdjust.csv` | **Không** | — | **Không** (0/3) | 0.5000 / 0.60 | 0.0000 / 0.55 | **FAIL** | **FAIL** (missing dense) | `local_extractive_provider_not_called` | **(b) & (d)** |
| `Q0850` | `2026_08_Error_BowOverAdjust.csv` | **Có** | Hạng 13 | **Có** (1/4) | 0.2143 / 0.60 | 0.5378 / 0.55 | **FAIL** | **FAIL** (dưới ngưỡng) | `local_extractive_provider_not_called` | **(b), (c) & (d)** |
| `Q1034` | `2026_08_Error.csv` | **Có** | Hạng 4, 7, 11 | **Có** (3/4) | 0.1250 / 0.60 | 0.0000 / 0.55 | **FAIL** | **FAIL** (missing dense) | `local_extractive_provider_not_called` | **(c) & (d)** |
| `Q0620` | `AI cảnh báo lỗi LSU.pptx` | **Có** | Hạng 2 | **Không** (bị lọc) | 0.1667 / 0.60 | 0.0000 / 0.55 | **FAIL** | **FAIL** (missing dense) | `local_extractive_provider_not_called` | **(a) & (c)** |
| `Q0824` | `2026_08_UnitTest.csv` | **Có** | Hạng 3, 4, 11 | **Có** (3/9) | 0.1379 / 0.60 | 0.5280 / 0.55 | **FAIL** | **FAIL** (dưới ngưỡng) | `local_extractive_provider_not_called` | **(b) & (c)** |
| `Q0828` | `2026_08_UnitTest.csv` | **Không** | — | **Không** (0/5) | 0.5882 / 0.60 | 0.0000 / 0.55 | **FAIL** | **FAIL** (missing dense) | `local_extractive_provider_not_called` | **(b) & (d)** |
| `Q0843` | `2026_08_Spec.csv` | **Không** | — | **Không** (0/8) | 0.4000 / 0.60 | 0.5283 / 0.55 | **FAIL** | **FAIL** (dưới ngưỡng) | `local_extractive_provider_not_called` | **(b) & (d)** |
| `Q0668` | `3V2ND19040...xlsx` | **Có** | **Hạng 1** | **Có** (Hạng 1) | **0.8571 / 0.60** | 0.5201 / 0.55 | **PASS** | **FAIL** (dưới ngưỡng) | `local_citation_first_provider_fallback` | Đạt 1.5 điểm |

### Chi tiết 4 nhóm nguyên nhân phân định:

- **(a) Mảnh đích không có trong chỉ mục**: 
  * Áp dụng cho **`Q0620`**: Số liệu đích `49.49%` và `25.42%` nằm trong `notesSlide1.xml` không được trích xuất vào database. Mảnh duy nhất của Slide 1 trong DB chỉ có chữ tổng quan, không có số.
- **(b) Có mảnh nhưng không có vector/FTS hoặc bị cắt nát không thể truy hồi đúng**:
  * Áp dụng cho **`Q0849`**, **`Q0843`**: 2 tệp lớn có 0 vector, hoàn toàn bị loại khỏi kênh dense.
  * Áp dụng cho **`Q0824`**: Dòng CSV bị cắt lát 1.000 ký tự làm tách rời mã Serial khỏi cột phán định `Judge:Cyan: NG`.
  * Áp dụng cho **`Q0828`**: Từ khóa "Black Skew" không xuất hiện trong văn bản của tệp `2026_08_UnitTest.csv` (FTS match = 0).
- **(c) Truy hồi được nhưng cổng bằng chứng loại**:
  * Áp dụng cho **`Q1034`**, **`Q0850`**, **`Q0824`**: Mảnh tệp đích lọt vào Top-15 và gói bằng chứng, nhưng do độ phủ thuật ngữ truy vấn trong mảnh quá thấp (Q1034: 12.5%, Q0850: 21.4%, Q0824: 13.8%), cổng từ vựng (ngưỡng 0.60) và cổng ngữ nghĩa (ngưỡng 0.55) đều đánh trượt fail-closed -> Mô hình AI không được phép gọi (`local_extractive_provider_not_called`).
- **(d) Bản chất câu hỏi cần tổng hợp toàn tệp, không thể trả lời từ top-k mảnh rời rạc**:
  * Áp dụng cho **`Q0849`**, **`Q0850`**, **`Q1034`**, **`Q0843`**: Câu hỏi hỏi "có bao nhiêu record lỗi", "mỗi màu có bao nhiêu kiện", "ngày nào lỗi nhiều nhất", "cặp giới hạn phổ biến nhất". Đây là các phép toán `COUNT(*)`, `GROUP BY Color`, `GROUP BY Date ORDER BY count DESC`, `GROUP BY Lower, Upper ORDER BY count DESC`. Cơ chế RAG chỉ lấy 8–15 mảnh không thể đọc hết 3.153 hay 22.054 dòng để cộng tổng.

---

## Mục 3 — Truy vết chuyên sâu Q0620 và Q0824

### 3.1 Câu Q0620 (`AI cảnh báo lỗi LSU.pptx`)

- **Giá trị kỳ vọng**: `25.42%`, `49.49%`, `2026年3月`, `BOWSKEW 4 BEAM`.
- **Vị trí thực tế trong tệp nguồn gốc**:
  * Phân tích tệp nén `.pptx`: Dữ liệu số KHÔNG nằm trong các shape hiển thị của Slide 1 (`ppt/slides/slide1.xml`), cũng KHÔNG nằm trong biểu đồ (`ppt/charts/chart2.xml`).
  * Dữ liệu nằm nguyên văn trong **Speaker Notes của Slide 1 (`ppt/notesSlides/notesSlide1.xml`)**:
    > *"Cụ thể, Iris Jig BOWSKEW 4 BEAM luôn đứng cao nhất và tăng từ 25,42% lên 49,49% vào tháng 03/2026. Tiếp theo là Iris Jig BOWSKEW 2 BEAM, đạt 25,04%, và Iris Jig BEAM 4 BEAM, đạt 20,56% trong cùng kỳ."*
- **Lỗi của khâu nạp**: Bộ chuyển đổi PPTX trong `src/aios_habit/rag_v2/adapters.py` (hoặc thư viện trích xuất) chỉ duyệt qua `slide.shapes` trên canvas trình diễn, bỏ qua hoàn toàn phần ghi chú diễn giả (`notesSlide`).
- **Hiện trạng trên Production**: Mảnh Slide 1 duy nhất (`76366631e1929150...`) chỉ chứa:
  > *"Biểu đồ cho thấy các JIG thuộc Iris LSU có tỷ lệ NG cao hơn rõ rệt so với các JIG còn lại... BOWSKEW 4 BEAM là đối tượng trọng tâm."*
  Hoàn toàn không có số liệu tỷ lệ phần trăm nào. Cả đường đo và giao diện đều không thể trả lời đúng vì dữ liệu chưa từng được nạp vào DB.

### 3.2 Câu Q0824 (`2026_08_UnitTest.csv`)

- **Giá trị kỳ vọng**: Serial `61C1068E7022`, ngày 12/8 và 13/8 không đổi pattern: `Total=NG`, `Black=OK`, `Magenta=OK`, `Cyan=NG`, `Yellow=OK`.
- **Vị trí thực tế trong tệp nguồn gốc**:
  * Dòng 5 (2026/08/12 16:14:30) và Dòng 6 (2026/08/13 15:50:26).
  * Mỗi dòng có độ dài **5.019 ký tự** và **4.999 ký tự** với hơn 250 cột số đo chi tiết.
- **Lỗi của khâu chia mảnh**:
  * Bộ chia mảnh cắt thô theo kích thước ký tự (~1.000 ký tự/mảnh) mà không gắn tiêu đề cột (header) vào từng mảnh con.
  * Mã Serial `61C1068E7022` nằm ở ký tự thứ 20 (Mảnh 1, chunk `370961ab2dc...`).
  * Các cột phán định `Judge:Black: OK, Judge:Magenta: OK, Judge:Cyan: NG, Judge:Yellow: OK, TotalJudge: NG` nằm ở tận cùng của dòng (ký tự 4.850–5.000).
  * Hệ quả: Mảnh 1 chứa Serial nhưng không có kết quả phán định. Mảnh cuối chứa kết quả phán định nhưng là chuỗi số và chữ cụt ngủn `...,OK,OK,NG,OK,NG,...` không có Serial và không có tên cột để biết màu nào là OK, màu nào là NG.
- **Bóc tách điểm Artefact của Scorer**:
  * Trong tệp `rows-target8-check.jsonl`, đáp án của Q0824 là mẫu từ chối an toàn:
    > *"KHÔNG ĐỦ BẰNG CHỨNG:\n- Corpus được truy xuất không thiết lập được sự kiện hoặc quan hệ mà câu hỏi yêu cầu...\nLIMITATIONS: evidence_pack_insufficient..."*
  * Scorer chấm điểm chính xác dựa trên danh sách từ khóa kỳ vọng `["NG", "OK"]`. Do từ "KHÔNG" trong tiếng Việt chứa chuỗi con `"ng"` (không phân biệt hoa thường), hàm khớp chuỗi con đã nhận diện chuỗi `"ng"` là đạt từ khóa `"NG"`, cho 1.0 điểm chính xác (1/2 từ khóa), dù `co_trich_dan = False`.
  * **Kết luận**: Điểm 1.0 của Q0824 là điểm giả 100% của bộ chấm, thực chất câu này bị chặn hoàn toàn ở cổng bằng chứng.

---

## Mục 4 — Truy vết đường giao diện cho Q0668

Điều phối đã chỉ ra sự mâu thuẫn giữa báo cáo vé trước (nhắc phiên `CONV-Q0668-68F465F5` thành công) và bằng chứng thực tế đã commit ở `8e8bd3b` (tệp JSON ghi phiên `CONV-Q0668-6AC9BA1F` với đáp án Q0668 kết luận chưa đủ bằng chứng).

### 4.1 Kết quả kiểm tra vật lý các khối chỉ mục

Truy vấn thực tế trên các cơ sở dữ liệu production tại `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\`:

```
tri_thuc:     total chunks = 181.033 | has 3V2ND19040 = 151 | has 2026_08_Error = 25.810
lsu:          total chunks =  71.945 | has 3V2ND19040 =   0 | has 2026_08_Error =      0
dieu_tra_loi: total chunks =  74.439 | has 3V2ND19040 = 151 | has 2026_08_Error =      0
mom:          total chunks =   1.014 | has 3V2ND19040 =   0 | has 2026_08_Error =      0
```

### 4.2 Nguyên nhân gốc rễ khiến giao diện thất bại

1. **Sai lệch phân loại khối tri thức**: 
   * Tệp bản vẽ cơ khí `3V2ND19040-MOUNT_LD_BLOCK__LOT_18.8.2026.xlsx` chứa thông số dung sai của g1 và g2. Khi chia khối theo taxonomy (`src/aios_habit/index_domain.py`), tệp này được xếp vào khối `dieu_tra_loi` (151 mảnh). Trong khối `lsu`, tệp này hoàn toàn **KHÔNG TỒN TẠI (0 mảnh)**.
2. **Kịch bản chạy giao diện ép buộc sai khối**:
   * Trong kịch bản nghiệm thu giao diện `scratch/run_ui_synth_q0668_filter_fix.py` (dòng 213):
     `url_session = f"{BASE_URL}/?nb=mom_opcenter&conv={active_conv_id}&block=lsu"`
   * Việc gán cứng `block=lsu` đã ép buộc giao diện Streamlit chỉ được tìm kiếm trong bộ chỉ mục `collections/lsu/library.sqlite`.
   * Vì tệp `3V2ND19040` không có trong khối `lsu`, bộ truy hồi của giao diện buộc phải lấy các mảnh khác có chứa chuỗi "g1/g2" trong khối LSU (chân tín hiệu vi mạch trong `DP IF ASSY_7PA1153CJF.pdf`, slide báo cáo C7620).
   * Do các nguồn này không có dung sai cơ khí, AI tổng hợp của giao diện đã kết luận trung thực: *"Chưa đủ bằng chứng để xác định nominal và giới hạn của g1 và g2"*.
3. **Mã phiên không có bằng chứng**: Mã phiên `CONV-Q0668-68F465F5` mà báo cáo trước nhắc tới không tồn tại trong kho git; chỉ có phiên `CONV-Q0668-6AC9BA1F` là có tệp dữ kiện và ảnh chụp thực tế.

**Kết luận Mục 4**: Đường đo thành công (đạt 1.5) vì đo trên chỉ mục hợp nhất `tri_thuc`. Đường giao diện thất bại vì kịch bản test đã ép chọn khối `block=lsu`, trong khi tài liệu đích lại nằm ở khối `dieu_tra_loi`.

---

## Mục 5 — Xếp hạng nguyên nhân & Đề xuất phương án sửa

### Bảng xếp hạng nguyên nhân theo mức độ đóng góp

| Hạng | Nhóm nguyên nhân | Các câu bị ảnh hưởng | Tỷ lệ ảnh hưởng điểm đích | Bản chất kỹ thuật |
|---|---|---|---|---|
| **1** | **Bản chất câu hỏi thống kê toàn tệp CSV** | `Q0849`, `Q0850`, `Q1034`, `Q0843` | **57.1%** (4/7 câu) | RAG top-k mảnh rời rạc không thể thực hiện phép tính tổng hợp trên 3.000–25.000 dòng dữ liệu bảng. |
| **2** | **Thiếu 100% vector embedding của 2 tệp lớn** | `Q0849`, `Q0850`, `Q0843` | **42.9%** (3/7 câu) | 26.907 mảnh của `Spec` và `BowOverAdjust` có 0 dense/sparse embeddings, bị loại khỏi kênh semantic. |
| **3** | **Lỗi bóc tách tệp nguồn (Parser & Chunker)** | `Q0620`, `Q0824` | **28.6%** (2/7 câu) | Parser PPTX bỏ qua Speaker Notes (`notesSlides`); Chunker CSV cắt lát 1.000 ký tự làm đứt liên kết Header-Row. |
| **4** | **Lệch khối tri thức / Làn định tuyến giao diện** | `Q0668` (UI) | Tồn đọng Mục 0.2 | Tệp đích nằm ở khối `dieu_tra_loi`, nhưng kịch bản giao diện lại ép chọn `block=lsu`. |

---

### Đề xuất phương án kỹ thuật chi tiết cho các vé tiếp theo (Không tự ý triển khai trong vé này)

#### Phương án 1: Bổ sung làn truy vấn có cấu trúc cho tệp CSV thống kê (Structured CSV Engine)
- **Mục tiêu**: Cứu 4 câu thống kê `Q0849`, `Q0850`, `Q1034`, `Q0843`.
- **Phạm vi**: 
  * Tận dụng hạ tầng DuckDB/SQLite memory có sẵn trong kho (`src/aios_habit/rag_v2/structured_query.py`).
  * Khi bộ phân loại ý định phát hiện câu hỏi thuộc nhóm đếm bản ghi (`COUNT`), phân bố (`GROUP BY`), giá trị cực trị (`MAX/MIN`), tự động định tuyến sang thực thi truy vấn cấu trúc trên tệp CSV nguồn gốc hoặc bảng tóm tắt siêu dữ liệu tệp (Document Metadata Summary Chunk).
- **Rủi ro**: Cần kiểm soát chặt chẽ schema và SQL injection (chỉ cho phép truy vấn SELECT nội bộ trên bảng tạm read-only).
- **Cách kiểm chứng**: Đo lại 4 câu thống kê, kiểm tra số liệu khớp chính xác 100% với đáp án chuẩn.

#### Phương án 2: Hoàn tất nạp bổ sung 26.907 vector cho 2 tệp lớn
- **Mục tiêu**: Đưa 2 tệp `2026_08_Spec.csv` và `2026_08_Error_BowOverAdjust.csv` đạt chuẩn 100% vector như 889 tài liệu cũ.
- **Phạm vi**: 
  * Chạy tiến trình nhúng BGE-M3 ONNX FP32 có checkpoint cho 26.907 mảnh còn lại và cập nhật vào `chunk_embeddings` / `chunk_sparse_embeddings`.
  * Có thể tối ưu tốc độ bằng cách chỉ nhúng các mảnh tiêu biểu hoặc chạy qua đêm trên CPU (khoảng 10–12 giờ máy).
- **Rủi ro**: Tải CPU cao, kích thước database tăng thêm ~100MB.
- **Cách kiểm chứng**: Truy vấn kiểm kê số lượng vector đạt đúng 181.033 / 148.860 (100% retrievable chunks).

#### Phương án 3: Nâng cấp Parser PPTX và Chunker CSV hàng rộng
- **Mục tiêu**: Cứu câu `Q0620` và `Q0824`.
- **Phạm vi**:
  * **PPTX**: Bổ sung hàm đọc `slide.notes_slide.notes_text_frame.text` vào bộ trích xuất PPTX để thu thập toàn bộ nội dung diễn giả vào mảnh văn bản của slide tương ứng.
  * **CSV**: Với các tệp CSV có hàng dài (>1.000 ký tự), thực hiện nén dòng hoặc lặp lại tiêu đề cột (Header Prefix) vào từng mảnh con (ví dụ: `[Header: S/N, Date, Judge:Cyan...] [Row Data...]`), hoặc ưu tiên giữ lại các cột phán định ở cuối dòng.
- **Rủi ro**: Cần nạp lại 2 tệp `AI cảnh báo lỗi LSU.pptx` và `2026_08_UnitTest.csv` vào staging rồi merge vào production.
- **Cách kiểm chứng**: Chạy kiểm thử đơn vị trích xuất dữ liệu, xác nhận `49.49%` và `Judge:Cyan: NG` xuất hiện trong kết quả tìm kiếm FTS và vector.

#### Phương án 4: Chuẩn hóa phân loại khối tri thức và kịch bản giao diện cho Q0668
- **Mục tiêu**: Đóng dứt điểm Mục 0.2 cho `Q0668`.
- **Phạm vi**:
  * Cập nhật quy tắc phân loại trong `src/aios_habit/index_domain.py`: Cho phép các tệp bản vẽ cơ khí LSU như `3V2ND19040` thuộc cả 2 khối `lsu` và `dieu_tra_loi` (hoặc đồng bộ tệp này vào thư mục `collections/lsu/library.sqlite`).
  * Hoặc trong kịch bản test giao diện, cho phép chế độ khối tri thức là `auto` (toàn bộ tri thức) thay vì ép buộc `block=lsu`.
- **Rủi ro**: Không có rủi ro hồi quy.
- **Cách kiểm chứng**: Chạy lại kịch bản Playwright UI trong phiên mới, trích xuất đáp án và ảnh chụp trọn thân chứng minh `3V2ND19040` được trích dẫn và trả về đúng nominal `13.81` và giới hạn `13.93 / 13.76`.

---

## Danh mục tệp dữ kiện thô đính kèm phục vụ kiểm chứng độc lập

1. `docs/phieu-viec/ket-qua/missing5-task1-prod-inventory-raw.json`: Kết quả truy vấn kiểm kê chi tiết toàn bộ bảng, mảnh, vector, FTS và LIKE của 5 tệp mới cùng 889 tài liệu cũ trên production DB.
2. `docs/phieu-viec/ket-qua/missing5-task2-trace-8-questions-raw.json`: Dữ liệu vết truy hồi đầy đủ của 8 câu hỏi mục tiêu (Top-15 hits, điểm số, matched terms, evidence pack, telemetry cổng từ vựng/ngữ nghĩa, mode phản hồi).
3. `docs/phieu-viec/ket-qua/missing5-target8-questions.json`: Bộ 8 câu hỏi mục tiêu trích xuất từ đề thi chuẩn.
4. Các script truy vấn và đối chứng chỉ đọc lưu tại máy: `scratch/task1_prod_inventory.py`, `scratch/task2_trace_8_questions.py`, `scratch/task3_investigate_q0620_q0824.py`.
