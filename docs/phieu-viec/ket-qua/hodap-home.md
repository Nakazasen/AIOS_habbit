# Báo cáo vé hodap-home — hỏi đáp 6 câu L1–L3/E1–E3 trên index máy nhà

Máy: `h410asrock` (máy nhà). Nhánh: `phieu-viec/rag-fix1`. Thời điểm: phiên 2026-10-01 23:30 +07 → 2026-10-02 00:05 +07; 6 câu chạy liên tiếp 23:48–23:58 (giờ máy, +07). Vé: `docs/phieu-viec/mailbox/prompt.md` (bản phát hành `prompt-queue-hodap-home.md`). Không đụng `main`, không force-push, **không ghi index**, không ghi ổ D.

## 1. Kết luận

**ĐẠT đủ 3 tiêu chí vé.** Chạy đúng 6 câu L1–L3/E1–E3 (nguyên văn từ vé `hodap-lsu-loi-rerun`) trên index máy nhà bằng **đúng stack truy xuất của app**, chỉ đọc: **6/6 câu có trả lời**, đều `grounded`, không abstain, trace **`valid`** với 5–9 nhãn trích dẫn; báo cáo đủ thời gian, top kết quả, citation/trace từng câu; định danh index rõ ràng (mục 3). Tổng thời gian 6 câu **≈ 486 giây** (≈ 8,1 phút). Index **không đổi một byte** sau khi xong (mục 7).

Hạn chế đã ghi rõ ở mục 6 (đáp án từ lane tổng hợp cục bộ xác định nên còn mảnh rời/nhiễu; vài chunk trong index cũ còn XML thô; câu E1 bị cổng phủ từ khóa cắt còn 6 kết quả). Theo đúng ràng buộc vé: **không so trực tiếp số đo với PC0575** (khác index, khác máy).

## 2. Cổng gate

- Watcher tự mở OMP **`LAUNCH 1/4`** lúc `2026-10-01 23:30:55` (`launchStallCount=1`, log `D:\Sandbox\Vong_lap_giao_viec\watcher.log`).
- **Điều kiện mở ĐÃ TỚI**: J1-RT đã có verdict ĐẠT (~23:30) và vé đúng lane [NHÀ] → nhận vé bình thường, **không** dùng nhánh "4 lần watcher"/`cho-muse`, không quay no-op.

## 3. Định danh index máy nhà

| Thuộc tính | Giá trị |
| --- | --- |
| Đường dẫn (app resolve, chỉ đọc) | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` |
| Manifest | `config/workspace_chat_rag_v2.local.json` — `activation_state=activated`, `runtime.root` = `C:\AIOS_workspace_chat_rag_v2_production`, profile `bge_m3_hybrid` |
| Dung lượng | **2.942.201.856 B** (2,74 GiB) |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` (khớp **đúng** số sau merge của báo cáo `merge-home`) |
| mtime | 2026-10-01 08:27:27 (kích thước/mtime ổn định trong lúc băm) |
| Toàn vẹn | `PRAGMA quick_check` = `ok` |
| chunks | 149.800 (trong đó **121.331 `retrievable=1`**) |
| document | **889** `document_id` |
| vector | dense **121.671** · sparse **121.671** · FTS **121.331** · multivector **0** |
| fingerprint vector | `016c5255…6274fb` × **121.331** (dense + sparse) — phủ đúng phần retrievable; 340 hàng còn lại mang fingerprint cũ `ce7fb53f…c8e43c` (đúng bằng chênh dense − retrievable: mảnh cha không retrievable) |

**Delta đã merge (kiểm trực tiếp theo `document_id` của 2 gói delta):**

| Gói | Tài liệu | Chunk | Có trong kho C | `source_fingerprint` |
| --- | ---: | ---: | ---: | --- |
| `gpu-262b-delta-20261001` | 19 | 2.883 | **2.883/2.883** (2.883 retrievable) | toàn bộ `NULL` |
| `gpu-dc-delta-20261001` | 329 | 12.720 | **12.720/12.720** (10.238 retrievable + 2.482 mảnh cha) | toàn bộ `NULL` |
| **Tổng** | **348** | **15.603** | **đủ 100%**, không thiếu tài liệu nào | — |

Ngoài 2 gói trên, kho còn 347 tài liệu / 347 chunk `source_fingerprint=NULL` từ các lần nạp trước (tổng cộng 695 tài liệu / 15.950 chunk NULL). Ghi chú: đây là **index máy nhà**, khác production PC0575 — kết quả dưới đây **chỉ để tham khảo và phục vụ hỏi đáp tại nhà**.

## 4. Phương pháp chạy (chỉ đọc, đúng stack app)

Chuỗi chạy mỗi câu (không sửa mã, không ghi index):

1. `WorkspaceChatRagV2CanaryConfig.from_env()` → manifest → `_pipeline_config("bge_m3_hybrid", read_only=True, collection_id="tri_thuc")` → `RagV2DevPipeline` (BGE-M3 ONNX fp32, `device=cpu` như app đang chạy).
2. `LocalChunkIndex.search_with_summary(coerce_query_plan(question), limit=15)` — phạm vi **toàn kho `tri_thuc`** (không lọc `document_id`), `per_document_limit=3`, `expected_source_fingerprints={}` → mảnh merge (fingerprint nguồn `NULL`) vẫn được dùng, `stale=0`.
3. `build_evidence_pack(max_items=15)` → `synthesize_evidence(answer_shape=<intent>)` — **lane tổng hợp cục bộ xác định** của app (cùng lane đã dùng ở smoke `move-index-c`/`merge-home` được Muse chấp nhận; không gọi provider ngoài).
4. `build_evidence_trace_from_citations(query, answer_text, evidence_items)` — đúng hàm app dùng để gắn trace → `valid` / `insufficient_evidence`.
5. Env theo **đúng launcher app máy nhà** (`RUN_AIOS_WORKSPACE_CHAT.bat`): `AIOS_RAG_V2_NUMPY_DENSE=1`, `AIOS_BGE_QUERY_TIMEOUT=1200`.

**Vì sao không chạy qua UI hội thoại:** kho nhà chỉ có sổ `mom_opcenter` (MOM/Opcenter) — 6 câu LSU/lỗi **không thuộc sổ nào**; thêm nguồn vào sổ sẽ kích hoạt "chuẩn bị nguồn" (ghi index) — trái ràng buộc vé "chỉ đọc, không ghi index". Mảnh merge còn `source_fingerprint=NULL` nên đường hội thoại phải prepare lại mới dùng trực tiếp (đã ghi nhận ở báo cáo `merge-home` mục 8) — vé này không làm việc đó.

**Đáp án trong báo cáo là bản tóm tắt** (viết bởi OMP, dựa trên các mảnh đã trích); **bản nguyên văn từng câu nằm ngoài Git** tại `C:\tmp\hodap-home\qa-<1..6>.json` — theo luật an toàn dữ liệu (tài liệu nội bộ nhãn `local_only`, không dán nguyên văn vào Git).

## 5. Kết quả 6 câu

### 5.1. Bảng tổng hợp

| Câu | Câu hỏi | Thời gian init / tìm / **tổng** (s) | Trả về / top | grounded | mode | citation | trace |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | LSU là gì và gồm những bộ phận quang học chính nào? | 30.92 / 39.6 / **70.56** | 15/15 | có | `answer` | [6] [2] [13] [1] [8] | `trc_8c5a59cc1559` — **valid**, cited 6 |
| L2 | Hiện tượng đai đen trong hình ảnh liên quan thế nào tới đường kính BEAM? | 31.53 / 49.24 / **80.81** | 15/15 | có | `answer` | [5] [2] [12] [11] [3] | `trc_d9f8365992f6` — **valid**, cited 9 |
| L3 | Đường kính BEAM bao nhiêu là đạt, và khi nào gây lỗi hình ảnh? | 30.43 / 48.12 / **78.6** | 15/15 | có | `answer_with_limits` | [2] [1] [10] [13] [8] | `trc_0d9d9ddb8319` — **valid**, cited 7 |
| E1 | Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý? | 27.67 / 69.73 / **97.42** | 6/6 | có | `answer_with_limits` | [3] [4] [5] [1] [2] | `trc_0ccbe1ba8c52` — **valid**, cited 5 |
| E2 | Dán SIM vào LD BLOCK ASSY có tác dụng gì khi xử lý lỗi beam? | 27.94 / 52.0 / **79.98** | 13/13 | có | `answer` | [7] [12] [2] [4] [6] | `trc_14e2c2ae7753` — **valid**, cited 7 |
| E3 | Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)? | 30.12 / 48.43 / **78.6** | 15/15 | có | `answer_with_limits` | [2] [8] [5] [7] [11] | `trc_462719f3265c` — **valid**, cited 6 |

`Trả về / top` = số kết quả engine trả về (trừ khi bị cổng phủ từ khóa cắt) trên số mảnh ghi trong báo cáo. Mọi câu: `candidate_count=100`, `stale=0`, không abstain.

### 5.2. Chi tiết từng câu

#### L1 — LSU là gì và gồm những bộ phận quang học chính nào?

- Thời gian: init **30.92s** · tìm **39.6s** · tổng hợp **0.04s** · **tổng 70.56s** (lúc hỏi: 2026-10-01 23:49:13).
- Truy xuất: trả **15** kết quả, candidate 100, `stale=0`, lý do thiếu: không có.
- Đáp án (lane cục bộ, tóm tắt): Các mảnh trích nói về trạng thái chuẩn/đường kính BEAM và các dạng lệch (đường kính BEAM nghiêng, trục quang nghiêng, phần vai to ra rồi thu gọn), bộ phận quang học nêu tên gồm **Lens CYLINDRICAL, POLYGON, Lens F**, LD mirror và nguồn laser; cách xác nhận trục quang bằng **JIG BEAM**, đo đường kính BEAM tại LINE, và cảnh báo các trạng thái lệch có thể gây lỗi hình ảnh (đai đen). Lane cục bộ **không** tóm ra định nghĩa “LSU là khối quét laser…” trọn vẹn; phần định nghĩa nằm ở chương 2 của tài liệu đào tạo (mảnh hạng 7) và bị nối rời.
- Citation: [6] [2] [13] [1] [8] · mode `answer` · trace `trc_8c5a59cc1559` — **`valid`**, cited **6**.
- Top kết quả (rank · điểm · tài liệu · `document_id`):

| # | Điểm | Tài liệu | `document_id` |
| ---: | ---: | --- | --- |
| 1 | 19.5 | Iris2020_Cコール自己診断.xlsx | `wsc-0603d773386b44af8c901ddf` |
| 2 | 16.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 3 | 14.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 4 | 12.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 5 | 11.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 6 | 7.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 7 | 7.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 8 | 7.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 9 | 7.0 | wsc-f131b2b0169443cf4e1dc576.txt | `wsc-f131b2b0169443cf4e1dc576` |
| 10 | 6.0 | wsc-1e085174af345d01afbf88d6.txt | `wsc-1e085174af345d01afbf88d6` |
| 11 | 6.0 | wsc-c0cfb5bb4e58b93f4ac06c76.txt | `wsc-c0cfb5bb4e58b93f4ac06c76` |
| 12 | 6.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |
| 13 | 6.0 | wsc-e84bb328ced276d4ec291a7b.txt | `wsc-e84bb328ced276d4ec291a7b` |
| 14 | 6.0 | wsc-73aa999fa4cdbafd7e6fdce8.txt | `wsc-73aa999fa4cdbafd7e6fdce8` |
| 15 | 5.0 | Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx | `wsc-154101d384acc2d01009025d` |

#### L2 — Hiện tượng đai đen trong hình ảnh liên quan thế nào tới đường kính BEAM?

- Thời gian: init **31.53s** · tìm **49.24s** · tổng hợp **0.04s** · **tổng 80.81s** (lúc hỏi: 2026-10-01 23:51:31).
- Truy xuất: trả **15** kết quả, candidate 100, `stale=0`, lý do thiếu: không có.
- Đáp án (lane cục bộ, tóm tắt): Quan hệ đúng như tài liệu: khi đường kính BEAM lớn bất thường (≈100 µm so chuẩn 60 µm) thì khoảng cách giữa các BEAM co còn ≈20 µm → hình bị chèn ép, xuất hiện **đai đen**; nguyên nhân chính do **Lens CYLINDRICAL / POLYGON / Lens F** và vị trí **LD mirror**; hướng xác nhận: đo nghiêng LD mirror bằng 3D và **kẹp SIM** để xem xu hướng đường kính Beam. Có 1 mảnh lệch chủ đề (kiểm tra hình ảnh quá khứ 6thA3S).
- Citation: [5] [2] [12] [11] [3] · mode `answer` · trace `trc_d9f8365992f6` — **`valid`**, cited **9**.
- Top kết quả (rank · điểm · tài liệu · `document_id`):

| # | Điểm | Tài liệu | `document_id` |
| ---: | ---: | --- | --- |
| 1 | 34.0 | Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx | `wsc-154101d384acc2d01009025d` |
| 2 | 26.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 3 | 24.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 4 | 24.5 | Iris2020_Cコール自己診断.xlsx | `wsc-0603d773386b44af8c901ddf` |
| 5 | 22.0 | Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx | `wsc-154101d384acc2d01009025d` |
| 6 | 21.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 7 | 21.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 8 | 20.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 9 | 19.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 10 | 16.0 | Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx | `wsc-154101d384acc2d01009025d` |
| 11 | 14.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 12 | 14.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |
| 13 | 14.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 14 | 14.0 | Iris2020_Cコール自己診断.xlsx | `wsc-6227ecdc7e605c80494c74d7` |
| 15 | 13.0 | Maintenance mode 3.xlsx | `wsc-c7aee12699dcc44affb708de` |

#### L3 — Đường kính BEAM bao nhiêu là đạt, và khi nào gây lỗi hình ảnh?

- Thời gian: init **30.43s** · tìm **48.12s** · tổng hợp **0.04s** · **tổng 78.6s** (lúc hỏi: 2026-10-01 23:53:16).
- Truy xuất: trả **15** kết quả, candidate 100, `stale=0`, lý do thiếu: `incomplete_query_term_coverage`.
- Đáp án (lane cục bộ, tóm tắt): Đường kính BEAM đạt chuẩn **60 µm** (khoảng cách đều nhau); khi lên **100 µm** → khoảng cách còn **20 µm** → đai đen. Có thêm mảnh: nếu sai lệch sẽ yêu cầu đổi JIG để dịch độ sâu phán định thêm 1 mm; 1 ca JIG BEAM 4 phát sinh NG tỉ lệ 42/280 = 15% kèm đối sách tạm thời (điều chỉnh trên các JIG còn lại). Mảnh hạng 1 còn XML pptx thô và hạng 2/3 là các đoạn trạng thái lệch.
- Citation: [2] [1] [10] [13] [8] · mode `answer_with_limits` · trace `trc_0d9d9ddb8319` — **`valid`**, cited **7**.
- Top kết quả (rank · điểm · tài liệu · `document_id`):

| # | Điểm | Tài liệu | `document_id` |
| ---: | ---: | --- | --- |
| 1 | 28.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 2 | 27.0 | Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx | `wsc-154101d384acc2d01009025d` |
| 3 | 23.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 4 | 23.0 | wsc-2d528c22ed8a8466fba9c9bd.txt | `wsc-2d528c22ed8a8466fba9c9bd` |
| 5 | 23.0 | wsc-5035a3d752d88cc0e20eb4c3.txt | `wsc-5035a3d752d88cc0e20eb4c3` |
| 6 | 21.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 7 | 21.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 8 | 20.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 9 | 19.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 10 | 18.0 | Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx | `wsc-154101d384acc2d01009025d` |
| 11 | 16.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 12 | 14.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 13 | 14.0 | wsc-2d528c22ed8a8466fba9c9bd.txt | `wsc-2d528c22ed8a8466fba9c9bd` |
| 14 | 14.0 | wsc-5035a3d752d88cc0e20eb4c3.txt | `wsc-5035a3d752d88cc0e20eb4c3` |
| 15 | 13.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |

#### E1 — Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý?

- Thời gian: init **27.67s** · tìm **69.73s** · tổng hợp **0.02s** · **tổng 97.42s** (lúc hỏi: 2026-10-01 23:55:06).
- Truy xuất: trả **6** kết quả, candidate 100, `stale=0`, lý do thiếu: `incomplete_query_term_coverage`.
- Đáp án (lane cục bộ, tóm tắt): Trả lời **mỏng hơn các câu khác** do cổng phủ từ khóa cắt còn 6 kết quả: mảnh chính từ `Loi KDTPS.xlsx` — cross-check nghi do LSU → liên lạc KTCT + QCLSU, kiểm tra MOTOR POLYGON và **PWB APC** đều không phải nguyên nhân, mất hiện trạng sau khi tháo/lắp lại LSU; 1 mảnh tiếng Nhật nêu nguyên nhân **ポリゴンモーター不良** (motor polygon lỗi) từ cross-check; 1 mảnh là dòng công thức Excel (`=AVERAGE(...)`) — nhiễu; 1 mảnh “đang điều tra nguyên nhân”. Chưa tụ được mô tả trọn vẹn “Beam径 NG là gì”.
- Citation: [3] [4] [5] [1] [2] · mode `answer_with_limits` · trace `trc_0ccbe1ba8c52` — **`valid`**, cited **5**.
- Top kết quả (rank · điểm · tài liệu · `document_id`):

| # | Điểm | Tài liệu | `document_id` |
| ---: | ---: | --- | --- |
| 1 | 36.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 2 | 34.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 3 | 33.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 4 | 22.0 | wsc-2d528c22ed8a8466fba9c9bd.txt | `wsc-2d528c22ed8a8466fba9c9bd` |
| 5 | 22.0 | wsc-5035a3d752d88cc0e20eb4c3.txt | `wsc-5035a3d752d88cc0e20eb4c3` |
| 6 | 20.0 | sirius2_beam径確認_240202.xlsx | `wsc-c292106969b26cfd6269485b` |

#### E2 — Dán SIM vào LD BLOCK ASSY có tác dụng gì khi xử lý lỗi beam?

- Thời gian: init **27.94s** · tìm **52.0s** · tổng hợp **0.03s** · **tổng 79.98s** (lúc hỏi: 2026-10-01 23:56:40).
- Truy xuất: trả **13** kết quả, candidate 100, `stale=0`, lý do thiếu: không có.
- Đáp án (lane cục bộ, tóm tắt): Tác dụng của thao tác với MOUNT LD BLOCK ASSY: dùng **2 MOUNT LD BLOCK ASSY đã điều chỉnh OK trên JIG BEAM 6** để **unit test** trên 5 JIG BEAM còn lại; **kẹp LD mirror bằng SIM** để xác nhận đường kính Beam có đổi xu hướng không (1 máy NG ASSY). 1 mảnh lệch chủ đề (Shaft Feed/PICK UP 500 ASSY).
- Citation: [7] [12] [2] [4] [6] · mode `answer` · trace `trc_14e2c2ae7753` — **`valid`**, cited **7**.
- Top kết quả (rank · điểm · tài liệu · `document_id`):

| # | Điểm | Tài liệu | `document_id` |
| ---: | ---: | --- | --- |
| 1 | 28.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 2 | 24.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 3 | 24.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 4 | 20.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 5 | 18.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 6 | 18.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |
| 7 | 13.0 | RE_ Iris LSU Beam径NG多発　異常品質会議5回目.msg | `wsc-bd829b64ef52a3d76ff1747c` |
| 8 | 8.5 | Iris2020_Cコール自己診断.xlsx | `wsc-0603d773386b44af8c901ddf` |
| 9 | 8.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |
| 10 | 8.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 11 | 7.0 | RE__Iris_LSU_Beam径NG多発_異常品質会議3回目.msg | `wsc-e0c617eb98b847bd3b20be64` |
| 12 | 7.0 | RE__Iris_LSU_Beam径NG多発_異常品質会議2回目.msg | `wsc-9e3e7cbc01ed57332c1384eb` |
| 13 | 5.0 | RE__Iris_LSU_Beam径NG多発_異常品質会議5回目.msg | `wsc-61d4aa19758ed232210b4508` |

#### E3 — Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)?

- Thời gian: init **30.12s** · tìm **48.43s** · tổng hợp **0.04s** · **tổng 78.6s** (lúc hỏi: 2026-10-01 23:58:16).
- Truy xuất: trả **15** kết quả, candidate 100, `stale=0`, lý do thiếu: `incomplete_query_term_coverage`.
- Đáp án (lane cục bộ, tóm tắt): Hạng mục kiểm tra khi beam diameter NG: cross-check **MOUNT LD BLOCK ASSY** với FRAME và **PWB APC** trên JIG LSU / HONTAI; kiểm tra MOUNT LD BLOCK trên **JIG BEAM** — lệch trục X 3908 µm (setup 5550–5850 µm), **MIRROR LD A có vết sửa chữa**, LOG JIG chỉ 1 lần điều chỉnh; kiểm UNIT ISU bằng đồ gá, giá trị số/hình sóng không đổi; **đổi trục quang bằng JIG BEAM**. 1 mảnh nhiễu (CCD_SW).
- Citation: [2] [8] [5] [7] [11] · mode `answer_with_limits` · trace `trc_462719f3265c` — **`valid`**, cited **6**.
- Top kết quả (rank · điểm · tài liệu · `document_id`):

| # | Điểm | Tài liệu | `document_id` |
| ---: | ---: | --- | --- |
| 1 | 39.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 2 | 37.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 3 | 28.5 | Loi KDTPS.xlsx | `wsc-4fc7eb76bdc2e05c08b3f0f6` |
| 4 | 26.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 5 | 24.0 | KTD-2026-07-0680-Iris2024-C33-ISU-Điều chỉnh độ quang trục NG.xlsx | `wsc-bcf92b614c3fd337677a85f8` |
| 6 | 22.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 7 | 21.5 | KTD-2026-07-0680-Iris2024-C33-ISU-Điều chỉnh độ quang trục NG.xlsx | `wsc-26c5000f2fe11a6c8c8dd3db` |
| 8 | 20.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 9 | 19.0 | KTD-2026-07-0680-Iris2024-C33-ISU-Điều chỉnh độ quang trục NG.xlsx | `wsc-bcf92b614c3fd337677a85f8` |
| 10 | 18.5 | KTD-2026-07-0680-Iris2024-C33-ISU-Điều chỉnh độ quang trục NG.xlsx | `wsc-26c5000f2fe11a6c8c8dd3db` |
| 11 | 18.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |
| 12 | 17.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |
| 13 | 16.0 | Tài liệu đào tạo LSU_2019.01.18_K.pptx | `wsc-cfe180f30fae3c031ffd5951` |
| 14 | 12.0 | RE_ Iris LSU Beam径NG多発　異常品質会議3回目.msg | `wsc-5bb2e1327274e578dd2c71f4` |
| 15 | 11.0 | RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg | `wsc-75d716e930e8ddf3fc591e5a` |

## 6. Ghi nhận chất lượng & hạn chế

1. **XML thô trong index cũ:** mảnh của `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` vẫn còn thẻ `<p:sld …>` (extractor đã được vá ở vé E3 nhưng index hiện có chưa được trích lại) → các câu L2/L3 dính XML trong đáp án/ngữ cảnh.
2. **Cổng phủ từ khóa:** câu E1 bị `incomplete_query_term_coverage` cắt còn **6/15** kết quả (từ khóa lai “Beam径” hụt phủ); L3/E3 cũng mang lý do này nhưng vẫn trả 15. Đây là dữ liệu cho vé tối ưu, không phải lỗi chặn.
3. **Lane tổng hợp cục bộ nối mảnh rời** nên đáp án có đoạn nhiễu/lệch chủ đề (ví dụ E1 có dòng `=AVERAGE(...)`; E3 có `CCD_SW`; L1 có “Yêu cầu tắt nguồn điện”). Đáp án đọc hiểu trọn vẹn cần lane LLM hội thoại; trên máy nhà lane hội thoại chạy theo nguồn của sổ nên **chưa phủ tài liệu merge** (xem mục 4).
4. **Tốc độ:** 70–97 s/câu (init ~28–32 s + tìm 40–70 s) — nhanh hơn định tính so với các lần đo CPU-only trước đây (không so số trực tiếp), nhưng nếu tính cả khởi tạo thì mục tiêu “tra cứu dưới 1 phút” chưa đạt; ghi nhận để Muse quyết định.
5. **Không so trực tiếp PC0575** theo đúng vé (khác index, khác máy); 6 câu hỏi lấy nguyên văn từ vé `hodap-lsu-loi-rerun` (mục 14/16 báo cáo `hodap-lsu-loi.md`).

## 7. Bất biến của vé

| Điều kiện | Kết quả |
| --- | --- |
| Không ghi index | SHA-256 / dung lượng / mtime **trùng khít** trước và sau 6 câu: `45eb0e07…65b7c0` · 2.942.201.856 B · 08:27:27; `quick_check=ok` |
| Không ghi ổ D | Toàn bộ script/kết quả/log ở `C:\tmp\hodap-home\`; repo chỉ nhận file báo cáo + `trang-thai.md` |
| Không đụng `main`, không force-push | Chỉ commit trên `phieu-viec/rag-fix1` |
| App LAN vẫn phục vụ | `http://localhost:8501/_stcore/health` = `ok` (đo đầu và cuối phiên) |
| An toàn dữ liệu | Không dán nguyên văn nội dung tài liệu nội bộ (`local_only`) vào Git; bản nguyên văn ở `C:\tmp\hodap-home\` (ngoài Git) |

## 8. File phụ trợ (máy nhà, ngoài Git)

- `C:\tmp\hodap-home\probe.py` — probe chỉ đọc (identity + ask).
- Kết quả: `qa-1.json` … `qa-6.json`, `qa.jsonl`; log: `ask-1.log` … `ask-6.log`.
- Ảnh chụp index lúc đo: SHA `45eb0e07…` (mục 3).

## 9. Trạng thái vé

- Chuỗi commit: `11827a8` nhận vé (`dang-lam`) → `fcd1ef1` mốc 1 định danh index → `5bcc028` L1 → `4bdfdf6` L2 → `555eb15` L3 → `57467aa` E1 → `527614c` E2 → (commit này) báo cáo + `xong-cho-duyet`.
- `trang-thai.md` chuyển `xong-cho-duyet`, chờ Muse đối chứng độc lập.
