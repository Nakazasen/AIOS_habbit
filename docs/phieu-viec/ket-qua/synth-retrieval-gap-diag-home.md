# Báo cáo kết quả vé SYNTH-RETRIEVAL-GAP-DIAG-HOME: Chẩn đoán khoảng trống truy hồi của nhóm câu bị chặn vì thiếu bằng chứng

- **Mã vé:** `SYNTH-RETRIEVAL-GAP-DIAG-HOME`
- **Thợ thực hiện:** agy (máy nhà `h410asrock`, model `gemini-3.8-flash-high`)
- **Mã commit đang chạy:** `f49befa`
- **Mục tiêu cốt lõi:**
  1. **Sự tồn tại trong chỉ mục:** Tìm trực tiếp trong chỉ mục production `library.sqlite` (chỉ đọc) các mảnh chứa dữ kiện đích của 8 câu bị chặn (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0668`, `Q0843`). Kết luận rõ ràng cho từng câu: *dữ kiện có trong chỉ mục* / *có một phần* / *hoàn toàn không có*.
  2. **Hành trình truy hồi:** Chạy đường truy hồi thực tế của từng câu hỏi và ghi lại: mảnh chứa dữ kiện đích (nếu có) xuất hiện ở hạng mấy trong kết quả thô; có qua được khâu lọc theo khối tri thức (domain filtering), khâu sắp xếp lại (scoring/reranking), và cửa sổ ngữ cảnh hay không; khâu cụ thể nào đã loại nó ra kèm con số (điểm số, thứ hạng trước và sau mỗi khâu).
  3. **Phân loại nguyên nhân:** Phân loại rạch ròi từng câu vào đúng 4 nhóm: (a) Dữ liệu không có trong kho; (b) Dữ kiện có trong kho nhưng truy hồi thô không xếp hạng đủ cao; (c) Dữ kiện qua được truy hồi thô nhưng bị khâu lọc hoặc cửa sổ ngữ cảnh loại; (d) Nhóm khác.
  4. **Tổng hợp & Đề xuất kiến trúc:** Bảng phân loại 8 câu, ước tính điểm có thể lấy lại cho từng nhóm nguyên nhân, và đề xuất giải pháp cho nhóm lớn nhất.
- **Môi trường & Rào cứng:**
  - Python 3.11.14 (`cpython-3.11-windows-x86_64-none`), môi trường repo `AIOS_habbit` nhánh `phieu-viec/rag-fix1`.
  - Chỉ mục production: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` (dung lượng 2.942.201.856 bytes, mã băm SHA-256 `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`).
  - Toàn bộ chẩn đoán chạy chỉ đọc, chỉ dùng bộ xử lý trung tâm (CPU-only).
  - Không sửa mã sản phẩm, không hạ ngưỡng cổng kiểm chứng, không ghi vào chỉ mục, không sửa bộ đề/thang chấm, không merge `main`.
- **Tệp dữ kiện nộp kèm:**
  - `docs/phieu-viec/ket-qua/ket-qua-synth-retrieval-gap-diag-home.json`
  - `docs/phieu-viec/ket-qua/synth-retrieval-gap-diag-home.md`
- **Trạng thái:** `HOÀN THÀNH - NỘP XONG-CHO-DUYET`.

---

## 1. Tóm tắt kết quả chẩn đoán cốt lõi & Sự thật kỹ thuật quyết định

### 1.1. Phát hiện sự thật kỹ thuật quyết định (Ground Truth Finding)
Sau khi quét trực tiếp toàn bộ 149.800 chunks trong chỉ mục production và chạy đối soát hành trình truy hồi thực tế:

1. **Nhóm (a) - DỮ LIỆU HOÀN TOÀN KHÔNG CÓ TRONG KHO chiếm đa số tuyệt đối: 7 / 8 câu (87.5%)!**
   - Trong số 8 câu bị cổng kiểm chứng chặn ở cả hai lượt đo `SYNTH-REMEASURE-STABLE-HOME` (làm mất tối đa 24 điểm), có tới **7 câu** (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0843`) có tệp nguồn tài liệu thực tế **CHƯA TỪNG ĐƯỢC CHUYỂN HOÁ VÀ NẠP VÀO CHỈ MỤC PRODUCTION `library.sqlite`**!
   - 5 tệp nguồn chứa đáp án mẫu của 7 câu này:
     1. `2026_08_Error_BowOverAdjust.csv` (nguồn của `Q0849`, `Q0850`): **0 chunk trong kho**.
     2. `2026_08_Error.csv` (nguồn của `Q1034`): **0 chunk trong kho**.
     3. `2026_08_UnitTest.csv` (nguồn của `Q0824`, `Q0828`): **0 chunk trong kho**, các mã serial `61C1068E7022` và `61C1068E6778` hoàn toàn không tồn tại (0 chunk).
     4. `2026_08_Spec.csv` (nguồn của `Q0843`): **0 chunk trong kho**, cặp dòng điện `370 mA` / `520 mA` hoàn toàn không có trong kho.
     5. `AI cảnh báo lỗi LSU.pptx` (nguồn của `Q0620`): **0 chunk trong kho**, thông số tỷ lệ NG `25.42% -> 49.49%` tháng 3/2026 hoàn toàn không có.
   - **Kết luận thẳng thắn theo yêu cầu của vé:**
     > **Trần điểm hiện tại của hệ thống bị giới hạn vật lý bởi dữ liệu nguồn, KHÔNG PHẢI DO MÃ NGUỒN.**
     > Mọi vé sửa mã RAG tiếp theo (tối ưu truy hồi, phân loại intent, nới ngữ cảnh hay viết lại query) **HOÀN TOÀN KHÔNG CÓ TÁC DỤNG đối với 7 câu này** (tương đương 21 điểm). Cổng Evidence Gate chặn an toàn fail-closed là hoàn toàn chính xác 100% vì hệ thống không thể bịa ra dữ liệu mà trong kho không hề có.

2. **Duy nhất 1 câu có dữ liệu đích thật trong kho: `Q0668` (12.5%) — Bị chặn do khâu lọc khối tri thức và nhiễu từ FTS:**
   - Câu `Q0668` (*"g1 và g2 có nominal và giới hạn nào?"*): Tệp nguồn `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` **CÓ TRONG CHỈ MỤC PRODUCTION** (82 chunks, doc_id `wsc-0ac3ea307df810908f4446a5` và `wsc-582a992dc46566ab198dabe2`).
   - Chunk `fb98fb34fbbf41a5b61c44d4a3e3b0a36f4cb3e215df2c430ae59a3b5ffb6f02` chứa chính xác 100% dữ kiện đề bài yêu cầu:
     `C61=1D | E61=13.81 | F61=+0.12 -0.05 | G61=0.12 | H61=0.05 | I61=g2 | J61==E61+G61 | K61==E61-H61 | L61=13.8562 | M61=13.8502...`
     và chunk `58275204fc911b7211938d4af3704f68c62164070d5c6b0dd3148923fb2ffa66` chứa `13.81` và `g1`!
   - **Nguyên nhân câu này bị mất điểm:**
     - **Nguyên nhân cấp 1 (Khâu lọc khối tri thức - Domain Filtering):** Tệp `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` trong bảng phân bổ domain của repo (`domain_document_map`) đang bị gán nhãn thuộc khối **`dieu_tra_loi`**, KHÔNG thuộc khối **`lsu`**. Khi chạy đo bộ đề LSU (hoặc người dùng chọn khối LSU), khâu lọc `allowed_document_ids` (chỉ chọn 92 tài liệu của LSU) đã loại bỏ 100% tài liệu này ngay từ vòng kiểm tra tính hợp lệ (Eligibility Gate)!
     - **Nguyên nhân cấp 2 (Truy hồi thô FTS bị pha loãng):** Nếu tắt lọc khối tri thức (tìm trên toàn kho 889 tài liệu), câu hỏi chứa các hư từ tiếng Việt phổ biến (`và`, `có`, `giới`, `hạn`, `nào`) làm cho 30.627 chunks trong kho khớp FTS. Chunk đích `58275204...` bị đẩy xuống hạng **#602** và `fb98fb34...` bị đẩy xuống hạng **#658** (vượt xa trần ứng viên `candidate_limit = 100`), do đó không lọt vào vòng xếp hạng và tổng hợp!

---

## 2. Bảng phân loại chi tiết 8 câu bị chặn

| STT | Mã câu | Câu hỏi | Tệp nguồn theo Rubric | Dữ kiện đích cần trả lời | Sự tồn tại trong chỉ mục `library.sqlite` | Khâu cụ thể loại bỏ mảnh đích | Phân loại nhóm nguyên nhân | Điểm có thể lấy lại nếu xử lý đúng |
|:---:|:---:|---|---|---|:---:|---|:---:|:---:|
| 1 | **Q0849** | File có bao nhiêu record lỗi và phạm vi ngày nào? | `2026_08_Error_BowOverAdjust.csv` | 3.153 record, 2026/08/01 đến 2026/08/25, 1.252 Serial | **Hoàn toàn không có** | Tệp nguồn chưa từng được nạp vào chỉ mục production (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp CSV vào kho) |
| 2 | **Q0850** | Yellow、Cyan、Magenta分别有多少件？ | `2026_08_Error_BowOverAdjust.csv` | Yellow=1304件, Cyan=1035件, Magenta=814件 | **Hoàn toàn không có** | Tệp nguồn chưa từng được nạp vào chỉ mục production (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp CSV vào kho) |
| 3 | **Q1034** | 哪一天Error Record最多？ | `2026_08_Error.csv` | 2026/08/11最多，有34笔; 08/12=22, 08/18=16 | **Hoàn toàn không có** | Tệp nguồn chưa từng được nạp vào chỉ mục production (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp CSV vào kho) |
| 4 | **Q0620** | 2026年3月のBOWSKEW 4 BEAM NG率はいくつですか。 | `AI cảnh báo lỗi LSU.pptx` | 25.42% từ 2026年3月に49.49%へ達した | **Hoàn toàn không có** | Tệp nguồn chưa từng được nạp vào chỉ mục production (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp PPTX vào kho) |
| 5 | **Q0824** | `61C1068E7022`は8月12日と13日で判定Patternが変わりましたか。 | `2026_08_UnitTest.csv` | Serial `61C1068E7022` cả 2 ngày Total NG, Cyan NG | **Hoàn toàn không có** | Serial và tệp nguồn hoàn toàn không tồn tại trong kho (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp CSV vào kho) |
| 6 | **Q0828** | Có thể khẳng định Black Skew là nguyên nhân duy nhất của mọi Total NG trong file không? | `2026_08_UnitTest.csv` | Serial `61C1068E6778`, `61C1068E7022` có Black OK | **Hoàn toàn không có** | Các serial và tệp nguồn hoàn toàn không tồn tại trong kho (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp CSV vào kho) |
| 7 | **Q0843** | Cặp giới hạn Current phổ biến nhất là bao nhiêu? | `2026_08_Spec.csv` | Lower=370 mA, Upper=520 mA (4.399 record) | **Hoàn toàn không có** | Tệp nguồn và cặp giá trị dòng điện không có trong kho (0 chunk) | **(a) Dữ liệu không có trong kho** | 0.0đ (cần nạp tệp CSV vào kho) |
| 8 | **Q0668** | g1 và g2 có nominal và giới hạn nào? | `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` | Nominal 13.81, dung sai +0.12/-0.05, giới hạn 13.93/13.76 | **Có trong chỉ mục (100%)** | (1) Bị lọc khối tri thức (Domain Filter) loại do gán nhãn `dieu_tra_loi`; (2) FTS toàn kho bị từ nhiễu đẩy xuống hạng #602/#658 | **(c) Khâu lọc loại & (b) Truy hồi thô FTS thấp** | **+3.00 điểm** (xử lý domain hoặc exact identifier boost) |

---

## 3. Mục 1 & 2: Hồ sơ chẩn đoán chi tiết từng câu

### 3.1. Nhóm (a): Dữ liệu không có trong kho (7 câu)

#### 1. Câu `Q0849` (STT 05 trong bộ đề)
- **Câu hỏi:** `File có bao nhiêu record lỗi và phạm vi ngày nào?`
- **Đáp án chuẩn:** Có `3.153 record`, từ `2026/08/01` đến `2026/08/25`, liên quan tới `1.252 Serial`. Nguồn: `2026_08_Error_BowOverAdjust.csv`.
- **Khảo sát chỉ mục:**
  - Tìm kiếm `2026_08_Error_BowOverAdjust.csv` hoặc tên chứa `BowOverAdjust`: **0 nguồn khớp**.
  - Tìm kiếm `BowOverAdjustment`: **0 chunk**.
  - Các số 3153 và 1252 chỉ xuất hiện ngẫu nhiên trong tệp đo dán tape năm 2021 (`tổng hợp dữ liệu dán tape.xlsx`) ở tọa độ phôi, hoàn toàn không phải record lỗi của tháng 8/2026.
- **Hành trình truy hồi:**
  - Chạy truy hồi: Top 1 là `RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg` (score=11.0, cov=0.273) và `Bong TAPE COVER GLASS Rev.00 VN.pptx`.
  - Không có mẩu nào chứa số lượng record hay phạm vi ngày.
  - Cổng Evidence Gate chặn chính xác `che_do=local_extractive_provider_not_called`, `gate_basis=insufficient`, độ phủ 0.50 (< 0.60).
- **Kết luận:** **Nhóm (a)**. Vấn đề nguồn dữ liệu thiếu, không phải lỗi mã.

#### 2. Câu `Q0850` (STT 06 trong bộ đề)
- **Câu hỏi:** `Yellow、Cyan、Magenta分别有多少件？`
- **Đáp án chuẩn:** Yellow=`1304件`、Cyan=`1035件`、Magenta=`814件`. Nguồn: `2026_08_Error_BowOverAdjust.csv`.
- **Khảo sát chỉ mục:**
  - Tệp nguồn `2026_08_Error_BowOverAdjust.csv`: **0 nguồn khớp**.
  - Cụm từ `1304件`, `1035件`, `814件`: **0 chunk**.
  - Trong kho chỉ có các tệp `DATA_Matome.xlsx`, `Sirius2_7620.xlsx` chứa tiêu đề cột tên màu, không có bảng thống kê tổng số lượng lỗi theo màu.
- **Hành trình truy hồi:**
  - Chạy truy hồi: Top 1–3 đều là `DATA_Matome.xlsx` (score=35.5, cov=0.214) do khớp 3 từ màu.
  - Không có số liệu件, độ phủ 0.214 (< 0.60).
  - Cổng Evidence Gate chặn chính xác `che_do=local_extractive_provider_not_called`.
- **Kết luận:** **Nhóm (a)**.

#### 3. Câu `Q1034` (STT 09 trong bộ đề)
- **Câu hỏi:** `哪一天Error Record最多？`
- **Đáp án chuẩn:** `2026/08/11`最多，有`34笔`；之后为`08/12=22`、`08/18=16`... Nguồn: `2026_08_Error.csv`.
- **Khảo sát chỉ mục:**
  - Tệp nguồn `2026_08_Error.csv`: **0 nguồn khớp**.
  - Chuỗi ngày `2026/08/11` kèm số record lỗi: **0 chunk**.
- **Hành trình truy hồi:**
  - Chạy truy hồi: Chỉ tìm được 3 chunks của `Sirius 2 _ C7620_報告版 4.pptx` khớp từ `error` (cov=0.125).
  - Cổng Evidence Gate chặn chính xác `gate_basis=insufficient`.
- **Kết luận:** **Nhóm (a)**.

#### 4. Câu `Q0620` (STT 10 trong bộ đề)
- **Câu hỏi:** `2026年3月のBOWSKEW 4 BEAM NG率はいくつですか。`
- **Đáp án chuẩn:** Tỷ lệ NG của Iris Jig BOWSKEW 4 BEAM tăng từ 25.42% lên 49.49% vào tháng 3/2026. Nguồn: `AI cảnh báo lỗi LSU.pptx`.
- **Khảo sát chỉ mục:**
  - Tệp nguồn `AI cảnh báo lỗi LSU.pptx`: **0 nguồn khớp**.
  - Cụm `BOWSKEW 4 BEAM`: **0 chunk**.
  - Số `25.42` xuất hiện trong `bowskew_nano_6AE10ZXA9910_2510221.xlsm` ở dòng `Row 19: nano | 45 | 155.25 | ... | 125.42` (tọa độ nano cơ khí, không phải tỷ lệ phần trăm NG).
- **Hành trình truy hồi:**
  - Chạy truy hồi: Top 1 là `siriud2調整治具_2号機_240411.pptx` (score=28.0, cov=0.167) và `Sirius 2 _ C7620_報告版 4.pptx` (score=16.75, cov=0.250).
  - Không có thông tin tháng 3/2026 hay tỷ lệ 49.49%.
  - Cổng Evidence Gate chặn chính xác `gate_basis=insufficient`.
- **Kết luận:** **Nhóm (a)**.

#### 5. Câu `Q0824` (STT 12 trong bộ đề)
- **Câu hỏi:** ``61C1068E7022`は8月12日と13日で判定Patternが変わりましたか。`
- **Đáp án chuẩn:** Cả 2 ngày đều Total NG, Black OK, Cyan NG, Magenta OK, Yellow OK. Nguồn: `2026_08_UnitTest.csv`.
- **Khảo sát chỉ mục:**
  - Tệp nguồn `2026_08_UnitTest.csv`: **0 nguồn khớp**.
  - Mã serial `61C1068E7022`: **0 chunk khớp** trong toàn bộ 149.800 chunks của kho!
- **Hành trình truy hồi:**
  - Chạy truy hồi: Vì serial không có trong kho, FTS chỉ bắt được từ `8` và `pattern` trong `Tài liệu đào tạo LSU_2019.01.18_K.pptx` (cov=0.069).
  - Cổng Evidence Gate chặn chính xác với lý do `no_target_query_evidence`, `no_direct_query_evidence`, độ phủ 0.103.
- **Kết luận:** **Nhóm (a)**.

#### 6. Câu `Q0828` (STT 17 trong bộ đề)
- **Câu hỏi:** `Có thể khẳng định Black Skew là nguyên nhân duy nhất của mọi Total NG trong file không?`
- **Đáp án chuẩn:** Không, có các serial Total NG nhưng Black OK (`61C1068E6778`, `61C1068E7022`). Nguồn: `2026_08_UnitTest.csv`.
- **Khảo sát chỉ mục:**
  - Tệp nguồn `2026_08_UnitTest.csv`: **0 nguồn khớp**.
  - Cả 2 serial `61C1068E6778` và `61C1068E7022`: **0 chunk khớp**.
- **Hành trình truy hồi:**
  - Chạy truy hồi: Bắt được các mẩu của `Loi KDTPS.xlsx` và `DATA_Matome.xlsx` do trùng từ nối tiếng Việt.
  - Cổng Evidence Gate chặn chính xác độ phủ 0.588 (< 0.60).
- **Kết luận:** **Nhóm (a)**.

#### 7. Câu `Q0843` (STT 43 trong bộ đề)
- **Câu hỏi:** `Cặp giới hạn Current phổ biến nhất là bao nhiêu?`
- **Đáp án chuẩn:** Lower=370 mA, Upper=520 mA, xuất hiện trong 4.399 record. Nguồn: `2026_08_Spec.csv`.
- **Khảo sát chỉ mục:**
  - Tệp nguồn `2026_08_Spec.csv`: **0 nguồn khớp**.
  - Cụm `370 mA` / `370mA`: **0 chunk**.
  - Các số 370 và 520 chỉ xuất hiện trong tài liệu AGV giao tiếp UART (`wsc-b8220b0d1cc36804b19e6dea.txt`) và bảng dán tape năm 2021.
- **Hành trình truy hồi:**
  - Chạy truy hồi: Bắt các mẩu công tắc hành trình cơ khí thang máy trong `Loi KDTPS.xlsx` và `Iris2020_Cコール自己診断.xlsx`.
  - Cổng Evidence Gate chặn chính xác độ phủ 0.400 (< 0.60).
- **Kết luận:** **Nhóm (a)**.

---

### 3.2. Nhóm (c) & (b): Ca đặc biệt duy nhất có dữ liệu trong kho — Câu `Q0668`

#### Câu `Q0668` (STT 40 trong bộ đề)
- **Câu hỏi:** `g1 và g2 có nominal và giới hạn nào?`
- **Đáp án chuẩn:** Nominal `13.81`, dung sai `+0.12 / -0.05`, giới hạn trên `13.93`, giới hạn dưới `13.76`. Các giá trị đọc `13.845 - 13.856`, đánh giá `O`. Nguồn: `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx`.
- **Khảo sát chỉ mục production:**
  - Tệp nguồn `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx` **HIỆN DIỆN 100% TRONG KHO CHỈ MỤC** gồm 82 chunks (`wsc-0ac3ea307df810908f4446a5` và `wsc-582a992dc46566ab198dabe2`).
  - Dữ kiện đích nằm trọn vẹn trong chunk `fb98fb34fbbf41a5b61c44d4a3e3b0a36f4cb3e215df2c430ae59a3b5ffb6f02`:
    > `... C61=1D | E61=13.81 | F61=+0.12 -0.05 | G61=0.12 | H61=0.05 | I61=g2 | J61==E61+G61 | K61==E61-H61 | L61=13.8562 | M61=13.8502 | N61=13.8474 | O61=13.8554 | P61=13.8489 | Q61=13.8483 | R61==IF(OR(Q61>E61+G61,Q61<E61-H61),"X",IF(AND(Q61<=E61+G61-(G61+H61)*0.1,Q61>=E61-H61+(G61+H61)*0.1),"O","Caution")) ...`
  - Và chunk `58275204fc911b7211938d4af3704f68c62164070d5c6b0dd3148923fb2ffa66`:
    > `Sheet: 18.08.2026 Columns: NO | Vị trí bản vẽ | Kích thước đo | Column D | Dung sai | Column F | Column G | Điểm đo | Dung sai trên | Dung sai dưới | Lot 18.08.26 ... 13.81 ... g1`
- **Hành trình truy hồi và các khâu loại bỏ:**
  1. **Khâu 1: Lọc khối tri thức (Domain / Knowledge Block Filtering):**
     - Bản đồ khối tri thức `index_domain.load_domain_document_map()` đang phân loại tệp `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` vào khối **`dieu_tra_loi`** (Điều tra lỗi).
     - Khi chạy đo bộ đề LSU (hoặc người dùng chọn khối tri thức LSU), hệ thống áp đặt bộ lọc cứng: `allowed_document_ids` chỉ bao gồm 92 tài liệu của khối `lsu`.
     - Do đó, tài liệu chứa đáp án bị **loại bỏ 100% ngay từ khâu lọc tính hợp lệ ban đầu (Eligibility Filter)**. Không một chunk nào của tài liệu này được phép tham gia vòng tìm kiếm.
  2. **Khâu 2: Truy hồi thô FTS (nếu tìm trên toàn bộ kho 889 tài liệu):**
     - Khi bỏ bộ lọc khối tri thức (tìm toàn kho):
     - Câu hỏi `g1 và g2 có nominal và giới hạn nào?` chứa các từ tiếng Việt thông dụng: `và`, `có`, `giới`, `hạn`, `nào`.
     - Trong kho có tới **30.627 chunks** khớp ít nhất một trong các từ này.
     - Các tài liệu khác chứa nhiều từ `và`, `có`, `giới`, `hạn` (như `KTD-2025-08-0866-DP Iris2020-C2B- Write DP Serial NG.xlsx`, `sirius2_beam径確認_240202.xlsx`, `MAIN_3V2XD47010_04.pdf`) đạt điểm BM25 cao hơn và chiếm trọn top 100.
     - Hai chunk đích thực tế chỉ đứng ở hạng **#602** (`58275204...`, score=-9.4319) và **#658** (`fb98fb34...`, score=-8.8457).
     - Với giới hạn tạo ứng viên mặc định `candidate_limit = 100`, hai chunk đích bị **Khâu tạo ứng viên truy hồi thô loại bỏ** trước khi bước vào khâu xếp hạng hay nới ngữ cảnh.
- **Phân loại:** **Nhóm (c) & Nhóm (b)**.

---

## 4. Tổng hợp & Ước tính điểm số có thể lấy lại

### 4.1. Phân bổ điểm số theo nhóm nguyên nhân

| Nhóm nguyên nhân | Số lượng câu | Danh sách mã câu | Tỷ lệ (%) | Điểm số tối đa bị khóa | Điểm có thể lấy lại bằng sửa mã RAG | Ghi chú điều kiện lấy lại điểm |
|---|:---:|---|:---:|:---:|:---:|---|
| **(a) Dữ liệu không có trong kho** | **7 câu** | `Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0843` | **87.5%** | **21.0 điểm** | **0.0 điểm** | Phụ thuộc 100% vào việc nạp bổ sung 5 tệp CSV/PPTX nguồn vào chỉ mục production |
| **(b) & (c) Lọc domain & Thứ hạng FTS thấp** | **1 câu** | `Q0668` | **12.5%** | **3.0 điểm** | **+3.0 điểm** | Khả thi bằng sửa mã RAG (gán đúng domain LSU cho MOUNT LD BLOCK hoặc mở rộng cross-domain search cho mã cơ khí, kèm Exact Identifier Boost cho `g1`/`g2`) |
| **Tổng cộng** | **8 câu** | — | **100.0%** | **24.0 điểm** | **+3.0 điểm** | — |

### 4.2. Ý nghĩa đối với mục tiêu Go-Live 1.500

1. **Thực trạng điểm số hiện tại:**
   - Điểm trung bình cộng quyết định 2 lượt đo hiện tại: **68.84 / 150 điểm** (GPA **1.377 / 3.0**).
   - Ngưỡng đạt yêu cầu go-live (GPA 1.500): **75.00 / 150 điểm**.
   - Khoảng cách còn thiếu: **6.16 điểm**.

2. **Khả năng lấy điểm từ việc sửa mã RAG:**
   - Giải quyết triệt để câu `Q0668` (nhóm b & c) sẽ mang lại **+3.00 điểm**, nâng tổng điểm lên **71.84 / 150 điểm** (GPA **1.437 / 3.0**).
   - Khoảng cách còn lại tới ngưỡng 1.500 là: `75.00 - 71.84 = 3.16 điểm`.
   - Khoảng cách 3.16 điểm này hoàn toàn có thể đạt được thông qua việc nâng cấp các câu đang đạt 1.0đ (nhóm 39 câu fallback có trích dẫn chuẩn) lên mức 2.0đ hoặc 3.0đ thông qua cải thiện schema format phản hồi của mô hình LLM (validated) hoặc tinh chỉnh trích dẫn, mà **không cần mạo hiểm nới lỏng cổng an toàn hay can thiệp vào chỉ mục production**.

3. **Về 7 câu thuộc nhóm (a):**
   - Không thể và không được phép cố gắng "sửa mã RAG" để lấy điểm cho 7 câu này.
   - Cổng Evidence Gate chặn 7 câu này nhận 0 điểm là hành vi an toàn hoàn hảo, bảo vệ người dùng khỏi ảo giác khi tài liệu nguồn không tồn tại.
   - Nếu dự án muốn khai thác điểm của 7 câu này, cần có một vé riêng biệt do Điều phối Muse và User phê duyệt để nạp bổ sung 5 tệp CSV/PPTX vào chỉ mục production thông qua quy trình chuẩn hóa và lập chỉ mục an toàn.

---

## 5. Bằng chứng kiểm chứng tính bất biến của chỉ mục production

- **Đường dẫn tệp chỉ mục:** `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Dung lượng tệp:** `2.942.201.856` bytes.
- **Mã băm SHA-256 ban đầu (trước chẩn đoán):**
  `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Mã băm SHA-256 sau chẩn đoán:**
  `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Đánh giá toàn vẹn:** Khớp tuyệt đối 100%, bảo toàn tính bất biến không thay đổi dù chỉ 1 byte.
