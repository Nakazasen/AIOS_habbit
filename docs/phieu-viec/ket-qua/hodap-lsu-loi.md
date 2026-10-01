# Vé `hodap-lsu-loi` — Thông luồng hỏi đáp LSU + lỗi trên chat (máy `KDTVN-PC0575`)

- Trạng thái báo cáo: **TẠM — chưa nghiệm thu hỏi đáp.** Bước 6 dừng theo cổng BỔ SUNG 5.1: nhúng câu hỏi riêng mất 0,205–0,272 giây, nhưng truy vấn retrieval L1 không trả kết quả trong giới hạn chẩn đoán 60 giây; mục 14 ghi số đo và lý do chuyển `cho-muse`. Không chạy LLM hoặc sáu câu để tránh vượt cổng.
- Trước đó: `cho-muse` (lần 3) vì BỔ SUNG 5.3 **nhánh B**: worker BGE không hỏng (log init sạch) nhưng truy vấn retrieval vượt bức tường 30 s **nằm trong code** (`bge_subprocess_client.py:31`, `…adapter.py:2688`) và một phần lớn thời gian bị ăn bởi query dense quét toàn bảng `chunk_embeddings` (`…adapter.py:956-963`, đo 71,9 s/tài liệu 15 chunk) → tổng 211,2 s/câu rồi lỗi "Tìm kiếm tài liệu chưa sẵn sàng". Số đo đầy đủ + file/dòng cần sửa: **mục 11**.
- Trước đó: `cho-muse` (lần 2) vì Bước 2 xác minh file Drive **KHÔNG ĐẠT gate số document** (496 < 501) và file Drive **không chứa vector của bất kỳ nguồn nào trong sổ LSU** (0/262) → nếu thay index sẽ làm app mất 5 tài liệu đang ready. Chi tiết mục 10.
- Chưa thay production, chưa chạy đủ sáu câu; truy vấn retrieval sau bản sửa vẫn quá chậm nên đã dừng theo BỔ SUNG 5.1 và chuyển `cho-muse` ở mục 14.
- Ngày làm: 2026-09-30 (13:35–15:54 +07, tiếp 16:33–18:45 +07) và 2026-10-01 (08:46–09:16 +07), máy `KDTVN-PC0575` (OMP). Nhánh: `phieu-viec/rag-fix1`.
- Phạm vi: chỉ đọc chẩn đoán + bật nguồn + chuẩn bị nền + dừng nhúng theo lệnh. **Không sửa code,
  không merge `main`, không xóa nguồn/tài liệu.**

## 0. Kết luận ngắn (tạm)

1. Nguyên nhân gốc đúng như chẩn đoán: hội thoại `CONV-9C730D76` (sổ "Điều tra lỗi LSU") có **0 nguồn
   đang bật** (15 lựa chọn cũ trỏ nguồn tạm đã xóa) và 494 tài liệu của sổ **chưa có vector** trong
   index production đang chạy → app chặn ở cổng tìm kiếm: "⚠️ Tìm kiếm tài liệu chưa sẵn sàng."
2. Đã bật 35/494 nguồn (nhóm không-CSV: 24 xlsx + 8 pptx + 3 msg) và chạy chuẩn bị nền đúng thiết kế
   của app; **9 dòng `ready` trong ledger** (banner UI ghi "10/35 nguồn ready" vì có 3 nguồn trùng chung
   1 tài liệu), gồm `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` và biên bản họp lỗi `Beam径NG多発` kỳ 2.
3. Máy CPU-only nhúng thật chỉ **0,31–0,35 chunk/s** → 494 nguồn ≈ 68 giờ (bất khả thi) và 19 tài liệu
   đã bật ≈ 2 giờ. Theo bổ sung khẩn: **đã dừng hẳn worker nhúng CPU**, 25 nguồn còn lại được park ở
   trạng thái không tự chạy lại.
4. **`collection_id` của sổ "Điều tra lỗi LSU" = `tri_thuc`** (thông tin Muse yêu cầu). Chi tiết ở mục 5.
- Việc còn lại: Muse xử lý nút thắt trong truy vấn retrieval (mục 14); sau khi có hướng sửa và cổng tìm kiếm đạt mới chạy sáu câu L1–L3/E1–E3 trên UI LAN. Không thay index, không tự tăng timeout và không nhúng CPU.
- Không chuyển `xong-cho-duyet` cho tới khi hoàn thành toàn bộ các bước trên.

## 1. Pha 1 — Chẩn đoán (chỉ đọc)

### 1.1 Luồng user dùng

Sổ **"Điều tra lỗi LSU"** = notebook `NB-E35A7BEE` (494 tài liệu trong sổ) → hội thoại duy nhất
**`CONV-9C730D76`** ("Cuộc trò chuyện 25/08 18:01"), hội thoại này có 35 nguồn đang bật sau Pha 2.
Trả lời chỉ dùng **nguồn đang bật → lọc `document_id` đã `ready` → LLM**.

### 1.2 Tái hiện lỗi (trước khi sửa)

Trên app LAN đang chạy, hỏi "LSU là gì?" → app trả:

```
⚠️ Tìm kiếm tài liệu chưa sẵn sàng. Vui lòng thử lại sau khi các nguồn hoàn tất chuẩn bị.
Nguồn đang bật: 35
ℹ️ AIOS đang chuẩn bị 33 tài liệu ở chế độ nền. Vui lòng đợi trong giây lát để bắt đầu hỏi đáp.
```

(Ảnh: `scratch/hodap-00-hien-trang.png` — thư mục `scratch/` git-ignore, không commit.)

### 1.3 Số đo index production (đầu phiên này)

| Chỉ tiêu | Giá trị |
| --- | --- |
| Đường dẫn index | `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` |
| Tổng chunk / chunk có embedding | 133.144 / 107.671 (đầu phiên) → 133.503 / 107.987 (14:26) |
| Số `document_id` trong index | 496 |
| `document_id` của 494 nguồn sổ có vector trong index | **0/262** (khớp vé `dieutra-banner-0494`) |
| Ledger chuẩn bị nguồn | trống → sau Pha 2 có 35 dòng |

### 1.4 Tốc độ nhúng thật (ONNX fp32, CPU)

- Đo sống trong phiên này (2 mốc liên tiếp): 312 chunk trong ~16,9 phút → **0,31 chunk/s**; tài liệu nhỏ
  17 chunk trong 49 giây → **0,35 chunk/s** (khớp số Pha 1: 0,32 chunk/s = 3,1 s/chunk).
- Suy ra: 19 tài liệu đã bật (≈ 1.993 chunk theo `content_text`) ≈ **1,7–2 giờ**; cả 494 nguồn ≈ **68 giờ**.

## 2. Pha 2 — Việc đã làm trước bổ sung khẩn

1. **Bật 35/494 nguồn** cho hội thoại `CONV-9C730D76` bằng API store của app (`scratch/hodap_enable_sources.py`
   của phiên trước): 24 xlsx + 8 pptx + 3 msg; **bỏ 459 CSV log** (nhúng sẽ mất ~66 giờ).
2. **Chuẩn bị nền**: worker `bge_subprocess_worker` (ONNX fp32, PID 2764) chạy trong app LAN, không chặn UI;
   ledger `source_preparation_ledger` theo dõi từng nguồn.
3. **Đẩy 5 nguồn trọng tâm lên ưu tiên `interactive`** (`scratch/hodap_promote_priority.py`, dry-run + apply):
   tài liệu đào tạo LSU + 3 biên bản họp lỗi `Beam径NG多発`. Mục đích: kiểm chứng sớm đúng 2 nhóm tri thức
   user cần (LSU + lỗi).
4. **Kết quả tới lúc dừng: 9 nguồn `ready` trên 5 tài liệu duy nhất**:

| Tài liệu (`document_id`) | Nguồn ready | Ghi chú |
| --- | --- | --- |
| `wsc-154101d384acc2d01009025d` | `SRC-6618270A`, `SRC-8A0501D5` | `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` (tri thức LSU) |
| `wsc-9e3e7cbc01ed57332c1384eb` | `SRC-28DACBC8` | biên bản họp lỗi `Beam径NG多発` kỳ 2 (`local_only`) |
| `wsc-a1a89391eee709a956a46130` | `SRC-4D52CBBA`, `SRC-F303840C` | `tổng_hợp_dữ_liệu_dán_tape.xlsx` (312 chunk) |
| `wsc-58589483c646877fdb341f46` | `SRC-41D0A83F`, `SRC-638E2C36` | `Dữ_liệu_tổng_hợp.xlsx` |
| `wsc-cc7d383bb6f7b9127bcaef00` | `SRC-B9269C50`, `SRC-86285084` | `dữ_liệu_tổng_hợp_CaV2__1240_.xlsx` |

5. **Sự cố và cách chữa**: nguồn `SRC-8A0501D5` từng `failed` với lý do
   `preparation_batch_001_document_9983dcbf05d5_bge_worker_staged_commit_invalid_res…`
   (phản hồi commit của worker không hợp lệ — lỗi **tạm thời** đúng lúc worker khởi động lại, không phải
   lỗi dữ liệu). Bấm nút **"🔄 Thử chuẩn bị lại"** của app → nguồn tự chữa thành `ready`; đường
   `_durable_semantic_coverage_ready` xác nhận lại vector trong index (không nhúng lại từ đầu).

## 3. Bổ sung khẩn — DỪNG nhúng CPU (2026-09-30 14:40 +07)

1. **Dừng worker**: `Stop-Process` PID `2764` (worker) + `17368` (launcher). Kiểm chứng: 0 tiến trình
   `bge_subprocess_worker` còn sống.
2. **Park hàng đợi để không tự nhúng lại**: `scratch/hodap_pause_prep.py` (dry-run + apply) chuyển
   24 nguồn `pending` + 1 nguồn `processing` → `failed` với lý do
   `paused_shared_index_from_home_machine`, đồng thời hạ ưu tiên `interactive` → `normal`.
   Lý do chọn cách này: lý do này **không** nằm trong `_RETRYABLE_PREPARATION_ERRORS` nên
   `reconcile_and_enqueue_workspace_chat_sources` sẽ **bỏ qua** các dòng đó (không xếp lại hàng đợi,
   không khởi động lại drain).
3. **Kiểm chứng không tự chạy lại**: F5 app (rerun đầy đủ) rồi đo 40 giây → ledger đứng yên
   (`9 ready / 25 parked`, 0 `processing`), không sinh worker mới.
4. Trạng thái cuối: app vẫn phục vụ LAN — `10.170.157.79:8501` → **HTTP 200**, `localhost:8501` → **HTTP 200**,
   `/_stcore/health` → `ok`; tiến trình `0.0.0.0:8501` LISTENING (PID 21016). Lưu ý vận hành:
   **không bấm "🔄 Thử chuẩn bị lại"** cho tới khi index dùng chung được copy sang, vì bấm sẽ nhúng lại
   bằng CPU. Trong phiên này có 1 dòng `processing` bị ngắt bởi lệnh dừng nên mang lý do crash
   (`…_bge_worker_prepare_stdout_eof`); đã chuẩn hoá lại thành `paused_shared_index_from_home_machine`
   cho đồng nhất (lý do này không nằm trong `_RETRYABLE_PREPARATION_ERRORS` nên reconcile bỏ qua).
   Trạng thái cuối cùng: **25 dòng `failed` (parked, lý do `paused_shared_index_from_home_machine`) /
   9 dòng `ready` / 0 `processing`**.

## 4. Kiểm chứng hỏi đáp: CHƯA chạy (đúng lệnh hoãn)

- `[INFERENCE]` Theo mã nguồn `_semantic_readiness`: chỉ cần **≥1 nguồn `ready`** là cổng tìm kiếm mở
  (không còn chặn "Tìm kiếm tài liệu chưa sẵn sàng"). Hiện có 9 dòng `ready` (5 tài liệu) nên cổng đã mở
  trong phạm vi 5 tài liệu đó. **Chưa xác nhận bằng câu hỏi thật trong phiên này** — bước verify 6 câu hỏi
  được hoãn theo bổ sung khẩn cho tới khi index dùng chung từ máy nhà được copy sang (để kết quả phản ánh
  đủ 494 tài liệu, không phải 5 tài liệu tạm).
- Thử nghiệm sớm bằng trình duyệt tự động trong phiên này **không gửi được câu hỏi** (ô soạn câu hỏi nằm
  trong rail bị thu gọn, sau khi mở rail thì thao tác điền/gửi tự động không đăng ký được với Streamlit).
  Không dùng kết quả này làm bằng chứng ĐẠT hay KHÔNG ĐẠT; bước verify sẽ do người/phiên sau thực hiện trên UI.


## 5. Thông tin cho vé index máy nhà

| Mục | Giá trị |
| --- | --- |
| `collection_id` của sổ "Điều tra lỗi LSU" | **`tri_thuc`** (bản ghi `NB-E35A7BEE` không có trường `collection_id` → dùng mặc định `DEFAULT_COLLECTION_ID = "tri_thuc"`) |
| Thư viện tương ứng | `tri_thuc` — tên hiển thị "Tri thức" (`local_cases/workspace_chat/collections.jsonl`) |
| `requested_profile` | `bge_m3_hybrid` (`AIOS_WORKSPACE_RAG_V2_PROFILE`) |
| Runtime root | `local_runs/workspace_chat_rag_v2_production` (mặc định, không override) |
| Đường dẫn index trên máy công ty | `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` |
| `model_id` / `model_revision` | `BAAI/bge-m3` / `5617a9f61b028005a4858fdac845db406aefb181` |
| `model_fingerprint` đang được E-chain chấp nhận | `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` (runtime `onnxruntime-int8`, `float32-le`, dim 1024) |
| Bản PyTorch cũ còn trong index | fingerprint `ce7fb53f797f0973e2cbf51d6a6ffef4de9a32b659b979f45663c6c360c8e43c` (340 dòng, dead weight vô hại — xem vé `stale-check`) |

### 5.1 Điều kiện để index copy sang được chấp nhận (cổng fail-closed)

Đọc từ mã (`_document_id`, `_durable_semantic_coverage_ready`, `_expected_backend_fingerprint`) — **quan trọng
cho vé máy nhà**, vì nếu lệch thì máy công ty sẽ coi là "chưa chuẩn bị" và **nhúng lại bằng CPU**:

| Điều kiện | Giá trị máy công ty đang chấp nhận |
| --- | --- |
| `document_id` mỗi nguồn | `wsc-<sha256(content_text đã strip)[:24]>` — **theo nội dung văn bản**, không theo tên file/đường dẫn (text rỗng mới rơi về `scope:source_id`) |
| `model_id` / `model_revision` của vector | `BAAI/bge-m3` / `5617a9f61b028005a4858fdac845db406aefb181` |
| `model_fingerprint` của vector | `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` (backend ONNX fp32 — nhãn runtime `onnxruntime-int8` theo tên lớp di sản) |
| Yêu cầu khác | mỗi `document_id` phải có ≥1 chunk `retrievable=1`, đủ cả dense **và** sparse embedding mang đúng fingerprint trên; thiếu là fail-closed |
| Hệ quả | Nếu máy nhà nhúng bằng backend khác (PyTorch/GPU, int8 khác cấu hình) thì fingerprint khác → index copy **không** được nhận, app sẽ xếp hàng nhúng lại (CPU) |

Sau khi copy: mở lại app (hoặc để app tự rerun) → `reconcile_and_enqueue_workspace_chat_sources` gọi
`_durable_semantic_coverage_ready` cho từng nguồn đang bật, thấy vector đúng fingerprint thì **tự tạo dòng
`ready`** (đè lên dòng đang park) — **không nhúng lại**. Đây là đường phục hồi dự kiến của vé.

## 6. Việc còn lại (sau khi index dùng chung được copy sang)

1. Copy index vào đúng đường dẫn ở mục 5 (hoặc theo hướng dẫn của vé máy nhà), mở app lại/để app
   reconcile: các nguồn có vector sẵn sẽ tự thành `ready` qua `_durable_semantic_coverage_ready`
   (không nhúng lại).
2. Chạy bộ 6 câu hỏi mẫu trên UI LAN (đúng hội thoại `CONV-9C730D76`, ghi lại đáp án + nguồn trích dẫn):

| # | Nhóm | Câu hỏi dự kiến |
| --- | --- | --- |
| L1 | LSU | "LSU là gì và gồm những bộ phận quang học chính nào?" |
| L2 | LSU | "Hiện tượng đai đen trong hình ảnh liên quan thế nào tới đường kính BEAM?" |
| L3 | LSU | "Đường kính BEAM bao nhiêu là đạt, và khi nào gây lỗi hình ảnh?" |
| E1 | Lỗi | "Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý?" |
| E2 | Lỗi | "Dán SIM vào LD BLOCK ASSY có tác dụng gì khi xử lý lỗi beam?" |
| E3 | Lỗi | "Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)?" |

3. Cập nhật báo cáo này (bỏ chữ "TẠM") + `trang-thai.md` → `xong-cho-duyet`.
4. Kiểm app vẫn phục vụ LAN sau khi xong (HTTP 200 trên `localhost` và IP LAN).

### 6.1 Kiểm cổng lúc 15:08 +07 (vé `dang-lam`, chờ index dùng chung)

- Kết luận: **điều kiện mở chưa tới** — chưa có bản index dùng chung nào được copy sang máy này.
- Bằng chứng (phiên watcher tự mở, chỉ đọc):
  - `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`:
    `mtime` **2026-09-30 14:37:14** (đúng mốc dừng nhúng CPU), 2.565.955.584 byte, **133.880 chunk** —
    không đổi kể từ 14:37.
  - Quét file >50 MB sửa trong 14 giờ ở `D:\`, `D:\Sandbox`, `D:\tmp`, `C:\temp`, `~/Downloads`:
    không có file mới nào (không có zip/bản copy index).
  - Ledger (`workspace_chat.sqlite`, mở `mode=ro`): **9 `ready` / 25 `failed` (lý do
    `paused_shared_index_from_home_machine`) / 0 `processing`**; không có tiến trình `bge_subprocess_worker`.
  - App LAN vẫn phục vụ: `127.0.0.1:8501` và `10.170.157.79:8501` → HTTP 200, `/_stcore/health` → `ok`
    (PID 21016, `0.0.0.0:8501`).
- Cổng gate của watcher: `launchStallCount = 1/4` (lần tự mở 15:01:47 vẫn cùng `sig` với mốc 14:59) →
  **chưa đủ 4 lần nên không đặt `cho-muse`**; phiên này chỉ thêm 1 dòng tiến độ, **không sửa** 4 trường
  watcher parse để bộ đếm chạy tiếp (1/4 → 4/4). Đủ 4/4 watcher tự ghi `cho-muse` + commit + push rồi ngừng mở lại.
- Không thực hiện trong phiên này (giữ đúng lệnh hoãn): không nhúng CPU, không bấm "Thử chuẩn bị lại",
  không chạy 6 câu hỏi mẫu.

## 7. Đã KHÔNG làm (theo lệnh cấm của vé)

- Không merge `main`; không force-push (có 1 lần `git pull --rebase` + push thường khi remote nhận commit mới).
- Không xóa nguồn/tài liệu/sổ nào. Thao tác ghi duy nhất ngoài file trạng thái: **bật nguồn** cho hội thoại
  (35/494), cập nhật `priority` rồi park hàng đợi chuẩn bị — đều là trạng thái vận hành của app, không xóa dữ liệu.
- Không sửa một dòng code nào; không đụng ổ D máy nhà (chỉ `D:\Sandbox\AIOS_habbit` của `KDTVN-PC0575`).
- Không đưa nội dung tài liệu `local_only` vào báo cáo/commit (chỉ nêu tên tài liệu).

## 8. Rủi ro / đề xuất

1. **Đề xuất (không tự làm)**: sau khi index dùng chung ổn định, 459 CSV log của sổ chỉ nên nạp nếu thật
   cần — nhúng chúng trên máy CPU sẽ tốn ~66 giờ; nên để máy nhà (GPU) xử lý một lần rồi copy.
2. 15 lựa chọn nguồn cũ trong `conversation_source_selections.jsonl` còn trỏ nguồn tạm đã xóa — vô hại
   nhưng gây nhiễu khi đọc file; đề xuất dọn bằng thao tác của app khi có thời điểm phù hợp (chưa làm).
## 9. BỔ SUNG 2 — Bị chặn khi tải Drive (15:54 +07)

- Không tải được file. Tải ẩn danh từ `drive.usercontent.google.com` chuyển `302` sang đăng nhập Google; thử qua profile tạm và profile Chrome thật nối bằng junction cũng hiển thị trang đăng nhập. Không có file tải xong trong `scratch/drive_index_check/`.
- Relay OMP không kết nối: CDP trả lỗi `Loading of unpacked extensions is disabled by the administrator.` Chính sách Chrome hiện tại chặn cài/nạp extension relay nên OMP không điều khiển được phiên Google của user.
- Đã khôi phục Chrome user chạy bình thường. Không ghi cookie/token vào repo; dữ liệu cookie/profile tạm do phiên này tạo đã xóa.
- **Không đụng production**: `library.sqlite` vẫn 2.565.955.584 byte, `mtime` 2026-09-30 14:37:14; không dừng app, không nhúng CPU, không bấm chuẩn bị lại, không chạy 6 câu hỏi.
- BỔ SUNG 2.1 (15:58 +07): đo production hiện tại được **501 `document_id` riêng biệt** trong `chunks`; prompt ghi tham chiếu file Drive là **496 document**. Mốc tham chiếu này thấp hơn production nên **chưa đủ điều kiện thay index**. File Drive chưa tải được nên số thật của file chưa kiểm chứng; cần bản đúng có ≥501 document hoặc Muse làm rõ chênh lệch trước khi tiếp tục.
- App vẫn phục vụ: `localhost:8501` và IP hiện tại `192.168.1.41:8501` → HTTP 200; `/_stcore/health` → `ok`. Không có tiến trình `bge_subprocess_worker`.
- Bước tiếp theo cần Muse/user mở cách tải hợp lệ ngay trên PC0575 và giải quyết gate số document: cho phép relay extension theo chính sách quản trị hoặc tải trực tiếp từ Chrome đã đăng nhập vào `scratch/drive_index_check/library.sqlite`; file phải có ≥501 document (hoặc Muse xác nhận số tham chiếu/cách đếm). Sau khi đủ hai điều kiện mới tiếp tục xác minh Bước 2; không đổi file production trước khi mọi gate đạt.

## 10. BƯỚC 2 — Xác minh file Drive tải tay: GATE KHÔNG ĐẠT → `cho-muse` (2026-09-30 16:35–17:10 +07)

### 10.1 Số đo thực tế (chỉ đọc)

| Chỉ tiêu | File Drive `scratch/drive_index_check/library.sqlite` | Production `…/collections/tri_thuc/library.sqlite` |
| --- | --- | --- |
| Dung lượng | 2.552.659.968 byte (mtime 2026-09-30 16:17) | 2.565.955.584 byte (mtime 2026-09-30 14:37) |
| SHA-256 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` **khớp ghim tham chiếu** | `5260c0430013981672b4e82cf3e967886b5a1d543ad3cad08e6016ca1b0b512b` |
| `PRAGMA integrity_check` | `ok` | `ok` |
| Document / chunk | **496** / 133.144 | **501** / 133.880 |
| Chunk `retrievable=1` | 107.331 | 108.007 |
| Dense khớp fingerprint `016c5255…` | 107.331 | 108.007 |
| Sparse khớp fingerprint `016c5255…` | 107.331 | 108.007 |
| Document có ≥1 chunk retrievable | 496/496 | 501/501 |
| Fingerprint app PC0575 yêu cầu | `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` (đo bằng chính hàm `_expected_backend_fingerprint` của app) → **khớp** | — |

- File Drive qua được mọi cổng kỹ thuật (SHA ghim, integrity, schema, fingerprint dense+sparse) **trừ cổng số document**.
- Cả hai index đều còn 340 dòng fingerprint PyTorch cũ `ce7fb53f…` (dead weight vô hại, đã biết từ vé `stale-check`).

### 10.2 Gate số document: KHÔNG ĐẠT

- Đo được: Drive **496** < production **501** → theo BỔ SUNG 2.1/2.2 (GHI CHÚ MỞ KẸT mục "Kẹt 2"), **dừng, không thay index, đặt `cho-muse`**.
- 5 `document_id` của production thiếu trong bản Drive (so theo tập ID, đúng 5 ID đã được nhúng CPU chiều nay trên PC0575):

| `document_id` thiếu trong bản Drive | Tên nguồn trong sổ | Chunk trong production |
| --- | --- | --- |
| `wsc-154101d384acc2d01009025d` | `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` | 52 |
| `wsc-58589483c646877fdb341f46` | `Dữ_liệu_tổng_hợp.xlsx` | 54 |
| `wsc-9e3e7cbc01ed57332c1384eb` | `RE__Iris_LSU_Beam径NG多発_異常品質会議2回目.msg` | 45 |
| `wsc-a1a89391eee709a956a46130` | `tổng_hợp_dữ_liệu_dán_tape.xlsx` | 312 |
| `wsc-cc7d383bb6f7b9127bcaef00` | `dữ_liệu_tổng_hợp_CaV2__1240_.xlsx` | 213 |

(Tổng 676 chunk mới = 108.007 − 107.331, khớp đúng 5 tài liệu trên.)

### 10.3 Bằng chứng bổ sung (quyết định): bản Drive KHÔNG phủ nguồn sổ LSU

Đo độ phủ thật theo đúng danh tính `document_id` của app (`wsc-<sha256(text)[:24]>`), chỉ đọc:

| Tập nguồn | Số nguồn | Số `document_id` | Production: có/ready | **Drive: có/ready** |
| --- | --- | --- | --- | --- |
| Cả sổ "Điều tra lỗi LSU" (`NB-E35A7BEE`) | 494 | 262 | 5 / 5 | **0 / 0** |
| Nhóm đang **bật** cho hội thoại `CONV-9C730D76` | 35 | 19 | 5 / 5 | **0 / 0** |

- Nội dung file Drive trùng corpus cũ đã biết: cùng danh sách tên nguồn + số chunk với production (chỉ khác 5 tài liệu nhúng chiều nay), gồm `Loi KDTPS.xlsx` (39.870 chunk), các bản vẽ `【Iris2020】全体配線図…`, và các bản `.msg` phiên bản trích xuất cũ (ví dụ `RE_ Iris LSU Beam径NG多発　異常品質会議2回目.msg` 47 chunk — **khác** `document_id` với nguồn cùng tên trong sổ). SHA `062ec090…` này chính là bản ghim P1.3 đã gặp ở vé `don-o-c`/`stale-check`.
- Kết luận đo được: file Drive **không phải** index đã nhúng cho bộ nguồn sổ LSU. Nếu thay, app mất 5 tài liệu đang `ready` (676 chunk LSU/lỗi) và **tụt về 0 tài liệu ready** → cổng "Tìm kiếm tài liệu chưa sẵn sàng" sẽ chặn lại như Pha 1. Vì vậy kể cả khi Muse miễn cổng số document, **thay index là bước đi ngược** với tiêu chí ĐẠT của vé.
- Giả thuyết khớp với số đo: máy nhà chưa từng nhúng bộ nguồn của sổ này (index máy nhà = corpus điều tra lỗi cũ), hoặc dữ liệu được nhập/trích xuất khác đường nên `document_id` không giao nhau.

### 10.4 Đã KHÔNG làm trong phiên này

- Không thay/bổ sung file production; không tạo backup (không cần vì chưa ghi); production vẫn 2.565.955.584 byte, `mtime` 2026-09-30 14:37, SHA `5260c043…`.
- Không bấm "🔄 Thử chuẩn bị lại"; không nhúng CPU; không sinh `bge_subprocess_worker` (kiểm tra: 0 tiến trình worker).
- Không sửa code, không đụng ổ D ngoài thư mục app, không merge `main`, không force-push.
- Không xóa file Drive trong `scratch/` (giữ làm bằng chứng; `scratch/` git-ignore).

### 10.5 Trạng thái app sau phiên (đo lúc 17:0x +07)

- `127.0.0.1:8501` → HTTP 200; `/_stcore/health` → `ok`; tiến trình `0.0.0.0:8501` LISTENING (PID 21016).
- Ledger (`mode=ro`): **9 `ready` / 25 `failed` (lý do `paused_shared_index_from_home_machine`) / 0 `processing`** — không đổi so với 15:58.
- 0 tiến trình `bge_subprocess_worker`.

### 10.6 Đề xuất để Muse/user quyết (OMP không tự quyết)

1. **Nếu mục tiêu vẫn là hỏi đáp đủ 494 nguồn sổ LSU:** máy nhà (GPU) phải nhúng đúng bộ nguồn của sổ (262 `document_id`) từ chính dữ liệu đã nhập trên máy công ty, rồi copy index sang PC0575 — lúc đó số document sẽ ≥ 501 và cổng phủ sẽ đạt. Cần Muse xác nhận dữ liệu nhập của sổ trên máy nhà (danh sách nguồn + text trích xuất) khớp máy công ty trước khi tốn công nhúng.
2. **Nếu chấp nhận phạm vi tạm:** giữ nguyên production hiện tại (5 tài liệu đã ready: LSU pptx + biên bản lỗi kỳ 2 + 3 xlsx dữ liệu) và cho phép chạy **6 câu hỏi mẫu** để nghiệm thu phần đã có (câu trả lời chỉ dựa trong 5 tài liệu đó). Đây là đường duy nhất hiện có thể thu được bằng chứng ĐẠT cho tiêu chí "trả lời có căn cứ".
3. Nhánh còn lại (nhúng tiếp bằng CPU trên PC0575) vẫn bị cấm theo BỔ SUNG KHẨN.

### 10.7 Trạng thái vé

- `trang-thai.md` → `cho-muse`; dừng, **không quay no-op**; hiện không còn việc OMP được phép làm tiếp trên vé này cho tới khi Muse/user trả lời mục 10.6.
- Bộ đếm kẹt "watcher tự mở 4 lần" không áp dụng: phiên này là việc thật (Bước 2) và đã kết luận bằng gate của vé.

## 11. BỔ SUNG 5 + 5.1 — Dừng thí nghiệm 600s, chẩn đoán "worker hỏng hay chậm", đo thật 3 chặng (2026-09-30 18:23–18:45 +07)

### 11.1 Đã dừng thí nghiệm 600s (theo BỔ SUNG 5.1)

- Kiểm tiến trình lúc 18:23 +07: **0** tiến trình đo (script `scratch/hodap_query_timing.py` không còn chạy) và **0** `bge_subprocess_worker` → không còn gì để kill; thí nghiệm đã tự dừng trước đó, phiên này không chờ thêm giây nào.
- Không có tiến trình nền nào của phiên trước còn sót (kiểm bằng `Get-CimInstance Win32_Process` lọc `bge|hodap`).

### 11.2 Chẩn đoán bằng log (BỔ SUNG 5.2)

- Log worker (`…/collections/tri_thuc/logs/bge_worker.stderr.log`, chỉ đọc). **Nguyên văn** dòng mới nhất:
  `bge_worker_stage backend=onnx init_ms=17860.928` (lần spawn 18:07) và `bge_worker_stage backend=onnx init_ms=18783.22` (lần spawn 18:41:49).
- Kết luận từ log: worker **khởi động được**, backend ONNX, nạp model + mở index xong trong ~18–19 s; **không có traceback** nào trong log ⇒ worker không tự chết.
- Lưu ý về bằng chứng: client mở log bằng chế độ ghi đè (`bge_subprocess_client.py:202`, `stderr_path.open("w")`) nên log của lần spawn lúc 17:24–17:27 (câu L1 của user) **đã bị ghi đè**; chỉ còn log của các lần spawn sau.
- Nguyên văn lỗi phía app, đo lại trực tiếp bằng probe chỉ đọc (`scratch/hodap_probe5e.py`, câu L1, 18:36–18:40):

```
aios_habit.rag_v2.semantic.SemanticBackendError: bge_worker_query_timeout   (bge_subprocess_client.py:612)
The above exception was the direct cause of the following exception:
aios_habit.rag_v2.semantic.SemanticBackendError: bge_subprocess_worker_crashed   (bge_subprocess_client.py:497)
→ Workspace Chat BGE-M3 retrieval unavailable: semanticbackenderror
→ canary: {"backend": "unavailable", "fallback_reason": "semanticbackenderror"}
```

### 11.3 Số đo thật theo 3 chặng (BỔ SUNG 5.1) — câu L1, đường app, chỉ đọc

| Chặng | Việc đo | Số đo thực tế (PC0575) |
| --- | --- | --- |
| 0 (chuẩn bị, trước mọi chặng) | `load_notebook_sources` (494 nguồn) | 2,1 s (cache ấm) – 13,8 s (nguội) |
| 0 | quét trạng thái `get_workspace_chat_source_preparation_status` (35 nguồn bật) | **27,0 s – 67,7 s mỗi lần**; đường app gọi **4–5 lần mỗi câu** = **152,3 s** (4 lần trong `retrieve_workspace_chat_evidence`) |
| 1 (nhúng câu hỏi — BGE worker) + 2 (search index) | `initialize_worker` (nguội) rồi `query_ready` | init **19,4–27,1 s**; query **dừng ở bức tường 30 s** (`bge_worker_query_timeout`, đo 31,6 s) ⇒ **không có kết quả search** |
| 3 (LLM sinh đáp án) | không chạy | không tới được vì chặng 1+2 lỗi |
| Tổng | `retrieve_workspace_chat_evidence` (L1) | **211,2 s** rồi trả `quality_search_unavailable` → UI hiện "⚠️ Tìm kiếm tài liệu chưa sẵn sàng" |

- Đo bổ sung (chỉ đọc, SQLite `mode=ro`), **cùng một file index production**:
  - `SELECT COUNT(*) FROM chunks WHERE document_id=? AND retrievable=1` → 0,00 s (dùng `idx_chunks_retrievable`).
  - Query dense của cổng phủ (`_durable_semantic_coverage_ready`): **71,9 s cho một tài liệu chỉ 15 chunk**. `EXPLAIN QUERY PLAN`: `SEARCH e USING INDEX idx_chunk_embeddings_model (model_fingerprint=?)` → quét **toàn bộ 108.347 dòng** `chunk_embeddings` (BLOB dense ~4 KB/dòng) rồi dò `chunks` từng dòng (đọc cả BLOB text của 133.880 chunk).
  - Query sparse cùng chức năng (cùng file, cùng tài liệu): 0,01 s (plan đúng: đi từ `chunks` theo `document_id` trước).
- Tài liệu kích hoạt chi phí trên: nguồn **`SRC-CCD87663`** (`Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx`, `document_id = wsc-154101d384acc2d01009025d`, 22 chunk / 15 retrievable) — nguồn này **không có dòng ledger** nên mỗi lần quét trạng thái đều rơi vào đường "kiểm tra phủ vector" đắt đỏ trên. Chi phí **không phụ thuộc kích thước tài liệu** mà phụ thuộc bảng embeddings bị quét toàn bộ.

### 11.4 Kết luận nguyên nhân gốc (đo được, không đoán)

1. **Worker không hỏng** — nó khởi động và nạp model bình thường (11.2).
2. **Nút thắt là tầng index/SQLite trên máy này**: (a) query dense trong cổng phủ vector bị plan thành **quét toàn bảng embeddings** → 27–72 s mỗi lần gọi, mà đường app gọi 4–5 lần mỗi câu; (b) chính truy vấn retrieval trong worker cũng **vượt 30 s** trên index này (probe nới cap 240 s không trả về trong ~11 phút ở trạng thái máy hiện tại; đã dừng theo lệnh "không chờ"), trong khi lần duy nhất app trả lời được hôm nay (L3, 18:09) chỉ mất 10 s — theo mã, đó là **đường trả lời trực tiếp bằng văn bản nguồn** (`antigravity_bridge.py:1274` trích chunk từ `packed_sources` khi không có `evidence_items`), không phải đường retrieval BGE.
3. Cổng thời gian cứng 30 s không có đường chỉnh bằng env ⇒ theo BỔ SUNG 5.3 là **nhánh B** và phải dừng, không tự sửa code.
4. Hệ quả mục tiêu: **211 s/câu** (đo được) ≫ mục tiêu "tra cứu < 1 phút" (Bước 1 lộ trình `docs/dich-den-du-an.md`) → bị đe dọa rõ ràng trên máy CPU-only (ghi theo BỔ SUNG 5.4).

### 11.5 Đúng file/dòng cần sửa (Muse gửi qua commit; OMP không tự sửa)

| # | Vị trí | Vấn đề | Hướng sửa đề xuất |
| --- | --- | --- | --- |
| 1 | `src/aios_habit/workspace_chat_rag_v2_adapter.py:956-963` | Query dense `COUNT(DISTINCT …)` của `_durable_semantic_coverage_ready` bị plan thành quét toàn bảng `chunk_embeddings` (đo 71,9 s cho 15 chunk) | Ép plan đi từ `chunks` theo `document_id` trước (như query sparse cùng hàm, dòng 965-973) hoặc `EXISTS … LIMIT 1` / bỏ `COUNT(DISTINCT)` vì chỉ cần biết "đủ hay không"; cân nhắc thêm index `(chunk_id, model_fingerprint, model_revision)` cho `chunk_embeddings` |
| 2 | `src/aios_habit/rag_v2/bge_subprocess_client.py:31` (+ mặc định ở dòng 422/449/515) | `_QUERY_TIMEOUT_SECONDS = 30.0` cứng, không có env ghi đè (chỉ `AIOS_BGE_PREPARE_TIMEOUT` cho pha prepare) | Cho timeout truy vấn đọc từ env/config có mặc định an toàn; đây là chỗ chặn hỏi đáp hiện tại |
| 3 | `src/aios_habit/workspace_chat_rag_v2_adapter.py:2688` | `timeout_s=(config.deep_timeout_ms/1000.0 if rerank_requested else 30.0)` — nhánh thường vẫn là literal 30,0 | Dùng cùng một nguồn cấu hình timeout cho cả nhánh thường (đo được ~211 s/câu khi máy nguội; nếu chỉ nới timeout thì vẫn rất chậm, xem #1) |
| 4 | Gọi lặp cổng phủ: adapter `3013`, `3039`, `2665`; app `786`, `838`, `851`, `3467`, `4149` | Cùng một câu hỏi quét trạng thái 4–5 lần (mỗi lần 27–72 s) | Cache theo lượt (một lần mỗi câu) hoặc gộp 3 lần gọi trong `retrieve_workspace_chat_evidence` |
| 5 | Ghi chú dữ liệu: nguồn `SRC-CCD87663` không có dòng ledger nên luôn rơi vào đường đắt (#1) | Có thể seed/backfill ledger cho nguồn đã có vector đúng (app đã có `_upsert_ledger_row` trong `reconcile_*`) | — |

### 11.6 Đã KHÔNG làm trong phiên này

- Không sửa một dòng code nào; không ghi index; **không nhúng CPU**; không bấm "🔄 Thử chuẩn bị lại"; không xóa nguồn/tài liệu nào; không merge `main`; không force-push.
- Không chạy 6 câu hỏi mẫu: chặng 1+2 chưa qua được bức tường 30 s nên không thể thu bằng chứng hỏi đáp (đúng thứ tự "sau fix" của BỔ SUNG 5.5). Bước 8/9 (xuất 262 nguồn cho vé GPU) **chưa chạy**, vẫn treo chờ quyết định của Muse/user vì BỔ SUNG 4 xếp sau Bước 6.
- Ghi chú thêm về chất lượng câu trả lời (để Muse tính khi ra vé tối ưu): câu trả lời duy nhất hôm nay (L3, đường trực tiếp bằng văn bản nguồn) bị chính app đánh dấu `insufficient_evidence` — "No valid citations found in answer text from enabled sources" — nên **tiêu chí ĐẠT (có nguồn trích dẫn) chưa đạt kể cả khi app trả lời được**.

### 11.7 Trạng thái app sau phiên (đo lúc 18:23–18:44 +07)

- `127.0.0.1:8501` → HTTP 200; `/_stcore/health` → `ok`; LAN IP hiện tại `10.170.157.79`.
- Ledger: **9 `ready` / 25 `failed` (`paused_shared_index_from_home_machine`) / 0 `processing`** (không đổi).
- Production index **không đụng**: 2.565.955.584 byte, SHA `5260c043…` (đọc lại lúc 18:2x).
- Các tiến trình đo của phiên này đều đã được dừng; còn **0** `bge_subprocess_worker`.

### 11.8 Trạng thái vé

- `trang-thai.md` → **`cho-muse`** theo đúng BỔ SUNG 5.3 (nhánh B, timeout nằm trong code) — dừng, không quay no-op, chờ Muse gửi bản sửa qua commit rồi OMP `git pull` + restart app + chạy lại 6 câu.

## 12. BỔ SUNG 6 — Bước 8/9: phân nhóm 262 nguồn + xuất `text_export.jsonl` (2026-09-30 19:22–19:35 +07)

### 12.1 Bước 8 — phân nhóm 262 `document_id` (chỉ đọc)

Script: `scratch/hodap_step8_groups.py` → `scratch/hodap-step8-groups.json`. Không ghi index, không nhúng.

- Sổ `NB-E35A7BEE`: **494 nguồn → 262 `document_id`** (khớp con số của vé).
- **Nhóm A = 5** (đã có vector dense + sparse đủ trong production):
  | `document_id` | Tài liệu | chunk retrievable |
  |---|---|---|
  | `wsc-154101d384acc2d01009025d` | `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx` | 15 |
  | `wsc-58589483c646877fdb341f46` | `Dữ_liệu_tổng_hợp.xlsx` | 11 |
  | `wsc-9e3e7cbc01ed57332c1384eb` | biên bản lỗi kỳ 2 (.msg) | 345 |
  | `wsc-a1a89391eee709a956a46130` | `tổng_hợp_dữ_liệu_dán_tape.xlsx` | 274 |
  | `wsc-cc7d383bb6f7b9127bcaef00` | `dữ_liệu_tổng_hợp_CaV2__1240_.xlsx` | 31 |
- **Nhóm B = 257** (chưa có vector; tất cả còn `content_text` đã trích xuất sẵn; chỉ 9/257 còn file gốc `.xlsx` trên đĩa — 248 nguồn không còn file gốc).
- **Nhóm C = 0** → không có nguồn mất text; theo BỔ SUNG 6 không phải dừng.

### 12.2 Cách xuất — dùng ĐÚNG đường text mà app đưa cho worker (chứng minh bằng code)

- `document_id` của app = `wsc-sha256(content_text.strip())[:24]` (`workspace_chat_rag_v2_adapter.py:740-750`, ghép từ `content_text` tại `:2153`) → script dùng đúng công thức này; `text.strip()` ghi ra `.txt` giống `_materialize_sources` (`:2452-2495`) rồi chạy `ConverterRegistry.convert_document` + `StructureAwareChunker.chunk_elements` — đúng chuỗi mà worker nhúng thật (`bge_subprocess_worker.py:190-207`).
- Vì vậy text trong JSONL là **đúng loại text app sẽ đưa vào BGE** cho từng nguồn, không trích xuất lại kiểu khác.
- Giới hạn cần biết cho vé máy nhà: `content_text` bị app cắt ở `WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES = 200 KiB/nguồn` (`workspace_chat_models.py:19`, `:166`) — export phản ánh đúng phần text app đang có.

### 12.3 Bước 9 — kết quả file export

| Chỉ số | Giá trị |
|---|---|
| Đường dẫn | `D:\Sandbox\AIOS_habbit\scratch\export_262\text_export.jsonl` |
| `document_id` xuất được | **262 / 262** (coverage 100%) |
| Tổng chunk | **52.979** |
| Dung lượng | **81.531.448 byte** (77,8 MiB) |
| SHA-256 file | `95aecf07297bfdf2e4f7462fd477fa052a89aa3eaaa462c53cbce40d341bb505` |
| Lỗi | `failed: []` (0 nguồn lỗi) |

Format mỗi dòng: `{"document_id","source_name","chunk_index","text"}`.

Kiểm tra sau xuất (chỉ đọc, độc lập với script xuất):
- 52.979 dòng; 262 `document_id` đúng bằng tập của sổ; 0 dòng lạ id; 0 text rỗng; mỗi nguồn 1–568 chunk; chunk dài nhất 6.000 ký tự.
- Nhóm A đối chiếu ngược với production: text khớp **100%** (2 nguồn kiểm: 15/15 và 11/11 chunk giống hệt theo thứ tự `rowid`).

### 12.4 Đã KHÔNG làm (đúng lệnh cấm)

- Không nhúng CPU, không ghi index, không bấm "🔄 Thử chuẩn bị lại", không đụng production, không xóa nguồn/tài liệu nào.
- **Không upload Drive tối nay** (theo BỔ SUNG 6.3) — user copy bằng USB.
- Không set env timeout / không chạy 6 câu hỏi tối nay (dời sang mai theo BỔ SUNG 6.1).
- File nằm trong `scratch/` (đã bị `.gitignore` che) → không commit vào git; user copy trực tiếp.

### 12.5 Trạng thái vé

- Giữ `dang-lam`, **tạm dừng qua đêm**: mai tiếp **Bước 6** (set env `AIOS_BGE_QUERY_TIMEOUT` sau khi đo cold/warm + restart app + chạy 6 câu L1–L3/E1–E3 trên UI LAN, hội thoại `CONV-9C730D76`) rồi **Bước 7** (báo cáo bỏ chữ "TẠM" + `xong-cho-duyet`).
- App LAN vẫn phục vụ bình thường; không bấm gì thêm.

## 13. Mốc 5–6 — nhận bản sửa `5cb5c94`, restart app, probe câu L1 (2026-09-30 18:5x–19:05 +07)

- **Mốc 5 (18:5x):** `git pull` → HEAD `72a6f85` đã chứa bản sửa của Muse `5cb5c94` (query dense/sparse đi từ `chunks` theo `document_id` bằng `CROSS JOIN`; timeout đọc từ env `AIOS_BGE_QUERY_TIMEOUT`; cache cổng phủ 60 s). Chưa chạy gì trong bước này.
- **Mốc 6 (19:00):** restart app lúc 18:55:54 với code mới (PID `21176`), `/_stcore/health` = `ok`, bind `0.0.0.0:8501`; **8 test mới `tests/test_hodap_worker_timeout_fix.py` pass trên chính PC0575**; 98 test adapter/fingerprint pass (Muse chạy trên VM; OMP chỉ chạy nhóm test của bản sửa).
- Probe chỉ đọc câu L1 (`scratch/hodap_probe6.py`):
  - `_durable_semantic_coverage_ready`: **5 lần gọi tổng 0,02 s** (trước fix 27–72 s/lần) → fix #1 và #3 đã diệt đúng chỗ chậm nhất.
  - Nhưng `worker.query_ready` **32,5 s > 30 s** ở query đầu (worker vừa init 20,2 s) → vẫn chạm `bge_worker_query_timeout`.
- Theo BỔ SUNG 6.1: **không set env / không đổi timeout / không chạy 6 câu tối nay** — dời sang mai (đo cold/warm rồi đặt `AIOS_BGE_QUERY_TIMEOUT` = số đo + margin, restart, rồi chạy L1–L3/E1–E3).

## 14. Bước 6 tiếp tục — truy vấn retrieval vượt cổng thời gian, dừng chờ Muse (2026-10-01 08:59–09:13 +07)

- Trước khi kiểm tra: `localhost:8501` không kết nối; không có tiến trình Workspace Chat hoặc BGE worker. Runtime production dùng Python 3.11.15, ONNX trên CPU; index `tri_thuc` giữ nguyên. Probe thấy **35 nguồn bật, 10 nguồn `ready`, 5 tài liệu**.
- **Khởi động worker lạnh:** probe chỉ đọc `scratch/hodap_query_time.py` đo worker khởi tạo trong **15,5 giây** (`init_ms=15516.271`, `reused=False`); log nguyên văn: `bge_worker_stage backend=onnx init_ms=15053.44`.
- **Chặng 1 — nhúng câu hỏi:** đo riêng bằng cùng backend ONNX CPU, không đọc/trả nội dung nguồn: khởi tạo model **10,396 giây**; nhúng L1 **0,205 giây**, nhúng L2 **0,272 giây**. Mỗi câu cho vector dày 1024 chiều; vector thưa có lần lượt 14 và 16 mục.
- **Truy vấn retrieval L1 (gồm nhúng + tìm kiếm):** không có kết quả trong **60 giây**; tổng thời gian tới lúc client báo lỗi là **61,6 giây**, lỗi `bge_subprocess_worker_crashed`. Probe giới hạn lời gọi ở 60 giây; dòng “cap 240s” của script cũ chỉ in giới hạn nội bộ cũ, không phải giới hạn thực tế của lượt này. Log worker chỉ có dòng init nêu trên, không có traceback hay số đo tách riêng truy vấn.
- **Kết luận:** thời gian nhúng đo riêng dưới 0,3 giây, còn truy vấn retrieval không xong trong 60 giây. `[INFERENCE]` phần còn lại của chặng retrieval, nhiều khả năng là tìm kiếm/index, là nút thắt; log hiện có chưa tách chính xác thời gian SQL/search nên không khẳng định chi tiết hơn. Theo BỔ SUNG 5.1, chặng tìm kiếm phải ở mức mili giây đến vài giây; vì vậy **dừng tại đây và chuyển `cho-muse`**, không nới timeout để che chậm.
- **Không gọi chặng 3 (LLM), không chạy sáu câu hỏi, không ghi đáp án/citation:** retrieval chưa trả evidence; không bịa câu trả lời hoặc nguồn. Biến `AIOS_BGE_QUERY_TIMEOUT` chưa được đặt, không tăng timeout. Không nhúng CPU, không ghi index, không đổi nguồn hay ledger.
- **Khôi phục dịch vụ LAN:** khởi động app bằng `RUN_AIOS_WORKSPACE_CHAT.bat`; listener `0.0.0.0:8501`, `localhost` và IP LAN `10.170.157.180` đều trả HTTP 200, `/_stcore/health` trả `ok`. Sau khởi động không thấy `bge_subprocess_worker`; app tiếp tục phục vụ dù vé đang chờ Muse.
- Trạng thái: `cho-muse`; chờ Muse xử lý/đưa hướng cho truy vấn search chậm. Chỉ tiếp tục sáu câu sau khi có truy vấn retrieval hoàn tất trong cổng thời gian.
