# Báo cáo Vé MERGE-HOME — DỪNG ở Pha 0 theo Cấm: kho app nằm trên ổ D

Máy: `h410asrock` (máy nhà). Nhánh: `phieu-viec/rag-fix1`. Thời điểm khảo sát: 2026-10-01 07:15–07:19 +07.
Commit nhận vé: `f6a0714`. Không đụng `main`, không force-push, không merge.

## Kết luận

**DỪNG Ở PHA 0 theo đúng mục Cấm của vé: kho app máy nhà nằm trên ổ D → mailbox chuyển `cho-muse`.**
Không chạy Pha 1 (dry-run/backup/merge), không chạy Pha 2 (chuyển app + hỏi thử), không ghi dữ liệu
nào lên ổ D, không tạo backup, không đụng app đang chạy. Tiêu chí ĐẠT của vé (báo cáo có số ID nhập/skip
+ kết quả hỏi đáp thử) **chưa thể hoàn thành ở thời điểm này** — cần Muse/quyết định người dùng trước.

## Cổng gate (theo yêu cầu watcher)

- Watcher tự mở OMP **LAUNCH 1/4** cho vé `merge-home` lúc `2026-10-01T07:09:47` (ghi trong
  `D:\Sandbox\Vong_lap_giao_viec\watcher.log`; `launchStallCount=1` trong `watcher_state.json`).
- Chưa đủ 4 lần nên **không dùng nhánh "4 lần watcher"/`cho-muse` vì kẹt**; điều kiện mở vé đã thoả
  (vé đúng lane [NHÀ]; 2 gói delta đang trên ổ C đúng tên và kích thước) → OMP nhận vé bình thường.
- Trạng thái `cho-muse` ở cuối lượt này là do **điều kiện dừng của chính vé** (kho app trên ổ D),
  không phải do watcher kẹt. Watcher đã gặp `cho-muse` sẽ im lặng chờ Muse (cron ~3 phút).

## Pha 0.1 — Kho app `localhost:8501` đang đọc

**Đường dẫn `library.sqlite`:**

```text
D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite
```

- Kích thước: **2.552.659.968 byte**; mtime `2026-09-28 05:55:03 +07`; SHA-256 toàn tệp:
  `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` — **khớp ghim P1.3**
  (đúng bản đã đóng dấu; chưa bị sửa kể từ lần chép đóng dấu).
- Bằng chứng phân giải (chạy bằng code app, chỉ đọc, `-B`/`PYTHONDONTWRITEBYTECODE=1`, cwd = repo):

```text
enabled: True
DEFAULT_COLLECTION_ID: tri_thuc
runtime_root: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production
requested_profile: bge_m3_hybrid
library: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite
exists: True
size: 2552659968 mtime: 1790549703.25
collection: tri_thuc | storage_root: ''
deployment manifest: ACTIVATED -> D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production
```

- Chuỗi quyết định: manifest `config/workspace_chat_rag_v2.local.json` (`activation_state=activated`,
  mtime 2026-08-30) đè biến môi trường `AIOS_WORKSPACE_RAG_V2_RUNTIME_ROOT` (trỏ `..._canary`) —
  giống kết quả P1.2. Bản ghi collection `tri_thuc` có `storage_root` rỗng → đi theo nhánh
  `<profile_root>/collections/tri_thuc/library.sqlite`.
- Bản copy C vẫn nguyên: `C:\AIOS_p1_4\tri_thuc\library.sqlite` — 2.552.659.968 byte,
  SHA-256 **`062ec090…4ef8ca` trùng khít bản D**, mtime `2026-09-28 22:47:02 +07` (bản sao
  byte-đối-byte, chỉ đọc; vé này cũng không ghi vào nó).

## Pha 0.2 — Hai gói delta

### SHA-256 so với ghim trong vé

| Gói | Kích thước | SHA-256 thực đo | Khớp ghim |
| --- | ---: | --- | --- |
| `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` | 20.867.536 B | `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85` | **Đúng** |
| `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` | 74.065.213 B | `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3` | **Đúng** |

### Trong ZIP (CRC đạt toàn bộ, `testzip()` trả `None`)

| Gói | Member | Kích thước | SHA-256 |
| --- | --- | ---: | --- |
| 262b | `gpu-262b-delta-20261001.sqlite` | 57.020.416 B | `b4b6f0bf059f544b606cfb7c33b315d72a5dc9c3a9b9a3591dc4cbfc47cf944a` |
| 262b | `gpu-262b-manifest-20261001.json` | 2.505 B | `bc9302740f9a691e61fb8f4c19c287a7697969c840db04c3ce6a5fcb02aa8be7` |
| DC | `gpu-dc-delta-20261001.sqlite` | 228.937.728 B | `a0ca1345b62a5d95867bb62f5790a40b3bd5f46704002323731c68822ad1cec3` |
| DC | `gpu-dc-manifest-20261001.json` | 45.466 B | `67b279ba087abd3ad9e8215316d175dbf408eac2169459feabbc3a0ff78a1f9d` |

Hash khớp 3 chiều (member trong ZIP = file SQLite cạnh ZIP trên ổ C = trường `delta_sha256` trong
manifest). Không cần giải nén để dùng bản cạnh ZIP.

### Bản chất file: full DB hay diff?

**Là SQLite standalone đúng schema collection `tri_thuc` (không phải diff, không phải bản sao đầy
đủ của kho đích).** Mỗi gói chứa **chỉ các tài liệu mới** của gói đó, kèm dense + sparse + FTS;
khi merge sẽ **chèn thêm dòng theo `document_id`**, bỏ qua mọi ID đã tồn tại (chính sách trong
manifest, không ghi đè).

| Đo trên bản SQLite cạnh ZIP | Gói 262b | Gói DC |
| --- | ---: | ---: |
| `PRAGMA quick_check` | `ok` | `ok` |
| `chunks` | 2.883 | 12.720 |
| `chunk_embeddings` (dense, `retrievable=1`) | 2.883 | 10.238 |
| `chunk_sparse_embeddings` | 2.883 | 10.238 |
| `chunks_fts` | 2.883 | 10.238 |
| tài liệu (`merge_document_ids`) | 19 | 329 (skip 0) |
| mảnh cha `retrievable=0` (giữ ngữ cảnh) | 0 | 2.482 |

### Fingerprint vector

Toàn bộ dòng dense và sparse của **cả 2 gói** mang đúng một giá trị fingerprint:
`016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` (khớp tiền tố `016c5255…`
ghi trong vé) — 2.883/2.883 dense + 2.883/2.883 sparse (262b); 10.238/10.238 + 10.238/10.238 (DC).
Trùng fingerprint model đã xác minh trên kho đích (bản copy C byte-đối-byte của kho D — P1.4).

### Base của từng gói (nguồn dựng)

- **262b**: export lọc 19 tài liệu phi-CSV từ GPU-262 (`source_export_sha256` =
  `0d1907c3…5ed2` trong manifest); staging `C:\AIOS_staging_262b`; backup pre-embed
  `library.sqlite.bak-20261001-gpu262b-preembed`; manifest ghi 5 ID "đã có trong production PC0575"
  (`wsc-154101d384acc2d01009025d`, `wsc-9e3e7cbc01ed57332c1384eb`, `wsc-58589483c646877fdb341f46`,
  `wsc-a1a89391eee709a956a46130`, `wsc-cc7d383bb6f7b9127bcaef00`) để vé merge SKIP. **Chưa đối chiếu
  5 ID này với kho máy nhà vì vé dừng trước Pha 1.1.**
- **DC**: export `export_dc.jsonl` (16.048.605 B, SHA `1d300c3a…0526`, link Drive trong manifest);
  staging `C:\AIOS_staging_dc`; backup pre-embed `1a2a9aac…a74af4d1`; `production_reference` đối
  chiếu bản copy `C:\AIOS_p1_4` (496 tài liệu): **không ID nào trùng, merge toàn bộ 329**.

## Pha 0.3 — Dung lượng ổ C

- Trống tại thời điểm đo (07:17 +07): **9.492.525.056 byte (~8,84 GiB)**.
- Đủ cho 1 bản backup kho (2.552.659.968 B) + phần tăng khi merge (~0,3 GB ước lượng theo kích
  thước 2 gói delta) — nhưng **không dùng vì vé dừng ở Pha 0**.

## Pha 0.4 — Điều kiện dừng của vé: **ĐÃ KÍCH HOẠT**

Mục Cấm của vé ghi: *"KHÔNG ghi bất kỳ thứ gì lên ổ D (ổ hỏng vật lý). Nếu Pha 0 phát hiện kho app
đang nằm trên ổ D → DỪNG ngay ở Pha 0, mailbox `cho-muse`, báo rõ."*

- **Kho app đang dùng nằm trên ổ D** (mục Pha 0.1) → điều kiện dừng được kích hoạt.
- Hệ quả: Pha 1 bắt buộc phải ghi lên kho (backup + chèn dòng) — tại chỗ là ổ D, bị Cấm; chuyển kho
  sang C và cập nhật manifest là **việc của vé riêng** (đã ghi chú sẵn trong báo cáo P1.3: *"việc
  di chuyển sang C và cập nhật manifest cần vé riêng"*). Pha 2 (trỏ app sang kho đã merge) cũng
  phụ thuộc bước này. Vì vậy vé dừng trước mọi thao tác ghi.

## Đã KHÔNG làm (đúng Cấm)

- Không merge, không chạy dry-run Pha 1, không tạo backup, không chèn dòng nào vào bất kỳ kho nào.
- Không ghi dữ liệu nào lên ổ D bởi lượt này (mọi thao tác dữ liệu chỉ đọc; chỉ commit/push git trên
  repo D như quy ước mailbox; script chạy `-B`, tạm đặt trên C).
- Không đụng app đang chạy (PID 3440, khởi động 06:14:36 hôm nay), không restart, không đổi config.
- Không dùng kho production PC0575, không dùng staging của vé khác ngoài 2 gói delta này (chỉ đọc).
- Không merge `main`, không force-push.

## Đề xuất cho Muse/người dùng (chưa thực hiện)

1. **Vé "chuyển kho production sang C + cập nhật manifest"** (đã được nêu từ P1.3): khi đó merge-home
   có thể chạy hoàn toàn trên C. Bản copy C hiện có (`C:\AIOS_p1_4\tri_thuc\library.sqlite`) là bản
   byte-đối-byte của kho D (cùng SHA `062ec090…`) — có thể dùng làm điểm xuất phát, nhưng đây là
   quyết định của Muse/user, không tự làm.
2. Nhắc lại 2 rủi ro đã ghi ở các vé trước (ngoài phạm vi vé này): đường hỏi–đáp của app có thể mở
   sổ `workspace_chat.sqlite` dưới runtime root (trên D) khi lập lịch nguồn (P1.3 mục 6), và worker
   BGE có thể tự dựng provider cloud từ biến môi trường máy (P1.4 mục 1.3).

## Cổng kiểm tra

- `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- Không sửa mã nguồn nên không chạy `compileall`/`pytest` (tránh cả việc ghi cache bytecode).
- Báo cáo này + cập nhật `trang-thai.md` là các commit duy nhất của lượt này (docs-only).

## File phụ trợ

- Script khảo sát (chỉ đọc, đặt trên C — không commit): `C:\tmp\merge-home\probe_merge_home.py`.
- Log watcher: `D:\Sandbox\Vong_lap_giao_viec\watcher.log` (dòng LAUNCH 1/4 lúc 07:09:47).
