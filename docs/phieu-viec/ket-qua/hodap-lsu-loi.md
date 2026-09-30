# Vé `hodap-lsu-loi` — Thông luồng hỏi đáp LSU + lỗi trên chat (máy `KDTVN-PC0575`)

- Trạng thái báo cáo: **TẠM — chưa nghiệm thu hỏi đáp.** Vé chuyển `cho-muse` vì OMP không thể tải index Drive qua Chrome trên PC0575; cần Muse/user xử lý quyền tải hoặc chính sách trình duyệt.
- Chưa xác minh file Drive, chưa thay production, chưa chạy bộ 6 câu; đang chờ mở nút thắt ở mục 9.
- Ngày làm: 2026-09-30 (13:35–15:54 +07), máy `KDTVN-PC0575` (OMP). Nhánh: `phieu-viec/rag-fix1`.
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
- Việc còn lại: tải index GPU theo BỔ SUNG 2, xác minh đầy đủ, backup/thay index, để reconcile tự chạy rồi verify **6 câu mẫu** trên app LAN. Hiện đang chờ xử lý blocker đăng nhập/chính sách Chrome tại mục 9; sau khi tải được mới tiếp tục, không nhúng CPU.
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
