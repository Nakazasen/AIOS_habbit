# Báo cáo Vé MERGE-HOME lần 2 — gộp 2 gói delta (262b + DC) vào kho app máy nhà (kho C)

Máy: `h410asrock` (máy nhà). Nhánh: `phieu-viec/rag-fix1`. Thời điểm thực hiện: 2026-10-01 08:13–08:5x +07.
Vé: `docs/phieu-viec/mailbox/prompt.md` (bản phát hành lại lần 2 — kho app đã sang ổ C sau verdict ĐẠT `move-index-c`).
Bản lần 1 của báo cáo này (commit `561014b`) ghi lại việc DỪNG ở Pha 0 vì kho app còn trên ổ D; bản này **ghi đè** bằng kết quả chạy đầy đủ.
Không đụng `main`, không force-push, không ghi/xóa gì trên ổ D.

## 1. Kết luận

**ĐẠT toàn bộ yêu cầu của vé**: đã gộp 2 gói delta vào kho C bằng 1 transaction (không ghi đè, không skip gì),
verify độc lập đạt, backup đầy đủ, app restart đọc lại kho C và hỏi thử trên nội dung mới đạt (retrieval trúng 100%,
câu trả lời grounded có trích dẫn). Hai phát sinh phải nói rõ:

1. **FTS bị nhân đôi rồi được sửa**: DB đích có trigger `chunks_fts_insert` (tự đồng bộ FTS khi chèn chunk
   `retrievable=1`); merge script lại chèn FTS tường minh → 13.121 chunk mới có 2 bản FTS. Đã xóa đúng 13.121 bản
   trùng (giữ 1), `chunks_fts integrity-check` = `ok`, không còn bản trùng. Không ảnh hưởng dữ liệu chunk/vector.
2. **Mảnh merge mang `source_fingerprint = NULL`** (đặc tính của gói delta — export không kèm fingerprint nguồn):
   đường hỏi đáp hội thoại của app có cổng "coverage" đòi fingerprint khớp với tệp nguồn đã materialize, nên
   **các mảnh mới chỉ được dùng trực tiếp bởi đường truy vấn đọc (như smoke dưới đây)**; khi người dùng thêm
   các tài liệu này vào sổ, cơ chế "chuẩn bị nguồn" sẽ chạy lại phần nhúng cho tài liệu đó (xem mục 8 — đề xuất).
   Đây là thông tin cho Muse/user quyết định vé sau, không chặn tiêu chí ĐẠT của vé này.

## 2. Cổng gate

- Watcher tự mở OMP **LAUNCH 1/4** cho vé lúc `2026-10-01T08:13:10` (log watcher máy nhà).
- **Điều kiện mở thoả** nên nhận vé bình thường (không dùng nhánh "4 lần watcher"/`cho-muse`):
  app resolve đúng kho **C**, 2 gói delta còn đủ trên ổ C đúng kích thước, app đang chạy health `ok`.

## 3. Pha 0 — xác minh tươi (chỉ đọc, không ghi gì)

1. **App đang đọc kho nào** (chạy bằng code app, chỉ đọc):
   `runtime_root = C:\AIOS_workspace_chat_rag_v2_production`; `deployment manifest: ACTIVATED -> C`;
   index resolve `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` — tồn tại.
2. **SHA-256 2 gói delta khớp ghim**:

| Gói | Kích thước | SHA-256 đo trong vé | Ghim |
| --- | ---: | --- | --- |
| `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` | 20.867.536 B | `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85` | khớp |
| `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` | 74.065.213 B | `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3` | khớp |

3. **Baseline kho C** (app còn chạy, mtime ổn định trong lúc băm): **2.576.191.488 B**,
   SHA-256 `aa7eac3b56dc02be14c0ae8da918e2520e9fb02eb8c44b0cd1d1cd2a97686f0c`.
   Ổ C trống **9.120.370.688 B (~8,49 GiB)** — đủ cho 1 backup ~2,6 GB + tăng trưởng ~0,3 GB.
4. **Cấu trúc + dry-run trùng ID** (chỉ đọc): schema 3 DB (2 delta + kho C) khớp nhau
   (`chunks` / `chunk_embeddings` / `chunk_sparse_embeddings` / `chunk_multivector_embeddings` / FTS5).
   `quick_check=ok` cả 2 delta; fingerprint vector 100% `016c5255…` trên cả 2 gói (dense + sparse).
   **0 trùng** `chunk_id`/`document_id` giữa từng delta và kho C (kiểm theo cả 4 bảng); **cả 5 ID "SKIP-PC0575"
   đều CHƯA có trong kho C** (`0/5`) → theo đúng vé: nhập hết (không skip ID nào trên máy nhà).

## 4. Pha 1 — merge

### 4.1. Dừng app + baseline chốt + backup

- Dừng đúng cây tiến trình app: `cmd 15708` → `streamlit 12180` → `python 15920` → `python 13188` (cổng 8501)
  → `bge_subprocess_worker 16564` → `4312` (`taskkill /PID 15708 /T /F`); xác nhận cổng 8501 hết listen, health lỗi kết nối.
- Baseline chốt (app đã dừng, mtime/size ổn định): **2.576.191.488 B**, SHA-256 `aa7eac3b…6f0c` (trùng số Pha 0).
- **Backup**: `C:\AIOS_backup_library_c_2026-10-01_merge-home\library.sqlite.bak-20261001-merge-home`
  — SHA-256 **`aa7eac3b56dc02be14c0ae8da918e2520e9fb02eb8c44b0cd1d1cd2a97686f0c`** (khớp baseline),
  `integrity_check` = `ok`, `quick_check` = `ok` (134.197 chunk). Ổ C còn 6,54 GB sau backup.

### 4.2. Dry-run (chỉ đọc)

| Gói | Tài liệu | Chunk | Dense/Sparse/FTS | ID sẽ nhập | ID skip | Trùng chunk_id |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 262b | 19 | 2.883 | 2.883 / 2.883 / 2.883 | 19 doc | 0 | 0 |
| DC | 329 | 12.720 | 10.238 / 10.238 / 10.238 (2.482 mảnh cha `retrievable=0`) | 329 doc | 0 | 0 |

Tổng: **348 tài liệu / 15.603 chunk**; danh sách đầy đủ 348 `document_id` in trong log dry-run
(`C:\tmp\merge-home\pha1_dryrun.txt`, máy nhà).

### 4.3. Apply — 1 transaction, không ghi đè

- `BEGIN IMMEDIATE`; kiểm trùng lại bên trong transaction (chunk_id trên 4 bảng + document_id): 0;
  chèn `chunks` → `chunk_embeddings`/`chunk_sparse_embeddings` (vector giữ nguyên byte), `chunks_fts` được
  trigger đồng bộ; `chunk_multivector_embeddings` = 0 dòng; `COMMIT` một lần (59,2 giây).
- Đã chèn: **262b 2.883 chunk + 2.883 dense + 2.883 sparse**; **DC 12.720 chunk + 10.238 dense + 10.238 sparse**;
  kiểm tra trong transaction: số chunk theo từng gói = đúng dry-run.

### 4.4. Verify sau merge (chỉ đọc) + sửa FTS

| Số đo | Trước merge | Sau merge |
| --- | ---: | ---: |
| `chunks` | 134.197 | **149.800** |
| `chunk_embeddings` (dense) | 108.550 | **121.671** |
| `chunk_sparse_embeddings` | 108.550 | **121.671** |
| `chunks_fts` | 108.210 | **121.331** |
| số `document_id` | 541 | **889** |

- `PRAGMA integrity_check` = `ok`; `foreign_key_check` = 0 dòng; `chunks_fts` integrity-check = `ok`.
- FTS sau sửa = **121.331** = đúng số dense mang fingerprint `016c5255…` (bằng nhau); 0 bản trùng.
- Theo từng delta (đếm theo `chunk_id` của delta trong kho C):
  262b `2.883/2.883/2.883/2.883` (chunks/dense/sparse/fts); DC `12.720/10.238/10.238/10.238` — khớp tuyệt đối.
- **Mọi tài liệu mới đều đủ retrievable + dense + sparse** (0 tài liệu thiếu).
- **SHA-256 kho sau merge**: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` (2.942.201.856 B).

## 5. Pha 2 — restart app + hỏi đáp thử

### 5.1. Restart

- Khởi động lại bằng `RUN_AIOS_WORKSPACE_CHAT.bat` lúc 08:34; `http://localhost:8501/_stcore/health` = `ok`
  (streamlit PID 11692).
- App đọc kho C: manifest `runtime.root = C:\AIOS_workspace_chat_rag_v2_production` (resolve lại bằng code app = đường C);
  layout C có file khóa người ghi `.aios-library-writer.lock`; UI mở được thật trong Chrome
  (aria: “Hỏi tài liệu”, “Sổ tài liệu của tôi”, “Cầu nối sẵn sàng (Trực tiếp)”).

### 5.2. Cách hỏi thử (mức tương đương P1 — đã được Muse chấp nhận ở vé `move-index-c`)

Vì app trả lời theo **phạm vi nguồn của từng sổ** (các tài liệu mới chưa nằm trong sổ nào; thêm nguồn là thay đổi
dữ liệu người dùng — ngoài phạm vi vé) nên hỏi thử chạy **đúng stack retrieval của app** trên kho C, chỉ đọc:
manifest → `_pipeline_config(bge_m3_hybrid, read_only=True)` → BGE-M3 ONNX fp32 (75,2 s nạp model) →
`LocalChunkIndex(read_only)` + `search_with_summary` (lexical + dense + sparse) + `synthesize_evidence` cục bộ,
**scope theo `document_id` của tài liệu vừa merge**. Đã hỏi 5 câu (3 LSU + 2 Điều chỉnh); round 1 hỏi tự nhiên,
round 2 chỉnh lại 2 câu để lấy câu trả lời grounded.

### 5.3. Kết quả

| Câu | Nội dung hỏi | Retrieval | Synthesis |
| --- | --- | --- | --- |
| LSU-1 | “Trong cuộc họp chất lượng Iris LSU Beam径NG多発 lần thứ 2, KDTVN và Nhật Bản đã trao đổi và yêu cầu gì?” | 6 kết quả, **đúng 2 tài liệu họp** (会議2回目 + 3回目), `stale=0` | **grounded=true**, 4 trích dẫn |
| LSU-2 / LSU-2b | “Vì sao khi đường kính BEAM lớn thì ảnh SCANNER CHECK PATTERN 600dpi xuất hiện đai đen?” | 3 kết quả, **đúng tài liệu đào tạo LSU 2019** | round 1 abstain (bảo thủ); **LSU-2b grounded=true**, 3 trích dẫn |
| DC-1 / DC-1b | “Báo cáo 8D KDTVN về lỗi 文字顯示異常 trên Iris2024: hiện tượng và kết quả phân tích?” | 3 kết quả, **đúng báo cáo 8D** (`20260310 KDTVN IRIS2024 文字顯示異常03.30 (1).pdf`) | round 1 abstain; **DC-1b grounded=true**, 3 trích dẫn |

- Tổng: **12 kết quả vòng 1 + 6 kết quả vòng 2 — 0 kết quả nằm ngoài tài liệu vừa merge**, `stale=0` mọi câu
  (nghĩa là mảnh mới được search bình thường, không bị loại).
- Tóm tắt câu trả lời (từ bằng chứng trích dẫn):
  - **LSU-1**: sau họp chất lượng lần 2 có nhiều nội dung thực hiện theo biên bản; phía KDC bổ sung nội dung
    thực hiện mới; chuẩn bị tổ chức họp chất lượng lần 3 để phân chia công việc; danh sách trao đổi ngày
    26/06/2026 giữa các bên liên quan KDTVN/KDC (nội dung gốc nằm trong tài liệu .msg của kho, không dán vào Git).
  - **LSU-2b**: ảnh chuẩn khi đường kính BEAM 60 μm (pitch 42 μm, khoảng cách BEAM đều); khi đường kính BEAM
    ~100 μm thì khoảng cách giữa các BEAM chỉ còn ~20 μm → khoảng cách quá hẹp nên ảnh bị chèn ép, và tại vị
    trí đường kính BEAM lớn xuất hiện **đai đen**.
  - **DC-1b**: 8D 解析報告書 (SUNVIEW) cho model `302XC45060 SVF101000ANN`, khách KDTVN, hiện tượng
    `文字顯示異常`, Report No. `S260017-3` (mở 2026/03/10, phát hành 2026/03/30); kiểm tra 2 PCS 客退品:
    đèn lên nhưng **畫面顯示亂訊及色異不良 → NG** (2025.11.15 và 2025.11.17); đã kiểm FPC/IC/FOG/COG (D4).
- Hạn chế ghi nhận: (a) tự động hóa UI Streamlit không thao tác được widget (giới hạn đã biết từ vé trước);
  do đó không gửi câu hỏi qua UI được; (b) synthesis cục bộ **bảo thủ** với nội dung CJK/XML slide — 2 câu round 1
  đúng bằng chứng nhưng bị abstain, chỉnh câu hỏi (round 2) thì grounded; (c) các tài liệu mới chưa thuộc sổ nào
  nên câu hỏi UI thông thường sẽ không thấy chúng (xem mục 1.2 và 8).

## 6. Bất biến của vé

| Điều kiện | Kết quả |
| --- | --- |
| Không ghi/xóa ổ D | Vé này không thao tác nào lên ổ D; bản D sau vé: index `2.552.659.968 B`, mtime `28/09 05:55`, SHA ghim `062ec090…4ef8ca` không đổi |
| Không xóa bản D / bản backup | Bản D còn nguyên; backup mới nằm trên C |
| Không dùng kho PC0575 / staging vé khác | Chỉ đọc đúng 2 file delta của vé (staging 262b/DC) và kho C |
| Không merge `main`, không force-push | Chỉ commit trên `phieu-viec/rag-fix1` |
| An toàn dữ liệu | Không commit dữ liệu local; script/công cụ đặt ngoài Git (`C:\tmp\merge-home\`), script smoke trong `scratch/` (git-ignore) |
| Rollback | (1) trỏ `library.sqlite` về backup `library.sqlite.bak-20261001-merge-home` (SHA `aa7eac3b…6f0c`); (2) hoặc trỏ `runtime.root` về bản D cũ (bản D nguyên vẹn). Không xóa gì của merge nếu muốn giữ |

## 7. Cổng tài liệu + commit

- `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS` (chạy trước khi push báo cáo).
- Vé không đổi mã nguồn sản phẩm (chỉ docs + scripts một lần chạy ngoài Git) nên không chạy full pytest;
  các script merge/verify chạy bằng `uv run --no-sync python` (Python 3.11.14).
- Chuỗi commit vé (branch `phieu-viec/rag-fix1`): `0658b12` nhận vé (`dang-lam`) → `f97db2e` mốc Pha 0
  → `0db9732` mốc Pha 1a → `796fac9` mốc Pha 1b (merge + fix FTS) → `2eee686` mốc Pha 2a → (commit này) báo cáo + trạng thái.

## 8. Đề xuất / ghi chú cho vé sau

1. **`source_fingerprint = NULL` của mảnh merge**: nếu muốn người dùng hỏi–đáp hội thoại dùng ngay dữ liệu mới
   mà không phải nhúng lại, cần vé riêng "gắn fingerprint nguồn cho mảnh merge" (giá trị = SHA-256 của tệp
   nguồn đã materialize, tức bản `.txt` sau `strip()`). Việc này cần nguồn văn bản gốc khớp `document_id`
   (`wsc-…` = SHA-256 24 ký tự đầu của text đã strip) — bàn với Muse trước khi làm; **không tự làm trong vé này**.
2. **Cho vé merge trên PC0575** (`prompt-queue-merge-gpu262b.md`): production PC0575 cũng có trigger
   `chunks_fts_insert` → **không chèn `chunks_fts` tường minh** khi merge (để trigger tự đồng bộ), nếu không sẽ
   bị nhân đôi FTS như vé này; nhớ đo baseline tươi + backup + `integrity_check` trước khi merge.
3. Gói 262b có 5 ID "SKIP-PC0575" — trên máy nhà **không ID nào tồn tại** nên đã nhập cả 5; khi merge trên
   PC0575 cần đối chiếu lại đúng 5 ID đó theo vé PC0575.
4. Kho C là **nguồn thay đổi**: app chạy nền tự "chuẩn bị nguồn" có thể tăng thêm chunk; số đo trong báo cáo này
   là ảnh chụp tại 08:27–08:41 (sau merge, app đang chạy).

## 9. File phụ trợ (máy nhà, không commit)

- `C:\tmp\merge-home\gate_check.py`, `pha0_full.py`, `pha0_hashes.py`, `pha1_backup.py`
- `C:\tmp\merge-home\merge_delta.py` (dry-run mặc định; `--apply` mới ghi; tự nhận trigger FTS)
- `C:\tmp\merge-home\fix_fts_dup.py`, `C:\tmp\merge-home\pha1_verify.py`
- `scratch/merge_home_smoke.py`, `scratch/merge_home_smoke2.py` (git-ignore, không commit)
- Log: `C:\tmp\merge-home\pha0_out.txt`, `pha0_hashes.txt`, `pha1_backup.txt`, `pha1_dryrun.txt`,
  `pha1_apply.txt`, `pha1_verify2.txt`, `pha2_smoke.txt`, `pha2_smoke2.txt`
