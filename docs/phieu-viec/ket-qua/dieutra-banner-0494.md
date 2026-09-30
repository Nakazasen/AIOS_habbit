# Vé `dieutra-banner-0494` — Điều tra banner "0/494 tài liệu" vẫn hiện sau khi xóa/tắt hết nguồn

- Ngày: 2026-09-30 (12:14–12:30 +07), máy `KDTVN-PC0575` (OMP).
- Nhánh: `phieu-viec/rag-fix1`. Vé **chỉ điều tra**: không sửa code, không bấm nút chuẩn bị lại dưới mọi hình thức, không merge `main`.
- Trạng thái: **tái hiện được, không phải rác phiên Streamlit cũ**. Nguyên nhân nằm ở nhánh
  chọn nguồn theo dõi trong `src/aios_habit/workspace_chat_app.py:4657`.

## 0. Kết luận ngắn

1. Banner hiện y như user báo trên **phiên trình duyệt hoàn toàn mới**, vẫn hiện **sau F5**, và vẫn hiện
   **sau khi restart hẳn app** (tiến trình Python mới). Loại trừ giả thuyết "session Streamlit cũ".
2. Ledger chuẩn bị nguồn của runtime đang chạy có **0 row** — **không có** row `pending`/`processing` nào
   thuộc 494 nguồn. Nghĩa là hàng đợi thật đang trống, nhưng giao diện vẫn mời bấm "chạy lại".
3. Đúng như đầu mối trong vé: khi **0 nguồn đang bật**, dòng 4657 đổi nguồn theo dõi sang **toàn bộ**
   nguồn của sổ (494), nên banner hiện "0/494" thay vì ẩn đi; nút "Tiếp tục" khi đó gọi
   `resume_workspace_chat_source_preparation(494 nguồn)` → có nguy cơ enqueue thật cả 494 tài liệu.
4. Con số "0/494" **không sai về mặt dữ liệu**: 494 nguồn này hiện **không có vector nào** trong index
   production của runtime đang chạy (đo được 0/262 `document_id`). Cái sai là **banner vẫn hiện và vẫn
   mời hành động** khi người dùng đã tắt hết nguồn.

## 1. Môi trường điều tra (đo trước khi thao tác)

| Mục | Giá trị |
| --- | --- |
| Máy | `KDTVN-PC0575`, IP LAN `192.168.1.41` |
| App lúc bắt đầu | tiến trình `1632` (cha `15864`), khởi động **09:15:46** cùng ngày |
| Lệnh chạy app | `python -m streamlit run src\aios_habit\workspace_chat_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false` |
| Runtime root | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production` (theo `config/workspace_chat_rag_v2.local.json`, `activation_state: activated`) |
| Ledger | `local_runs/workspace_chat_rag_v2_production/workspace_chat.sqlite` — bảng `source_preparation_ledger` |
| Index vector | `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` (2.552.659.968 byte) |
| Hội thoại đang mở | `CONV-9C730D76` thuộc sổ **"Điều tra lỗi LSU"** (`NB-E35A7BEE`) |

Xác nhận runtime root bằng chính code của app (không suy đoán):

```
uv run --no-sync --group dev python -c "from aios_habit.workspace_chat_rag_v2_adapter import WorkspaceChatRagV2CanaryConfig; c=WorkspaceChatRagV2CanaryConfig.from_env(); print(c.enabled, c.requested_profile, c.runtime_root)"
# → True bge_m3_hybrid D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production
```

`config/workspace_chat_rag_v2.local.json` trỏ `runtime.root` vào đúng thư mục trên, và `.env` **không**
đặt biến ghi đè runtime root. Mọi truy vấn ledger/index dưới đây mở bằng `file:…?mode=ro` (chỉ đọc).

### 1.1 Con số 494 đến từ đâu

- `local_cases/workspace_chat/notebook_sources.jsonl`: sổ `NB-E35A7BEE` có **đúng 494 nguồn**, tất cả
  đều có `content_text` (nên đều được đưa vào diện theo dõi chuẩn bị).
- `local_cases/workspace_chat/temporary_sources.jsonl`: hội thoại `CONV-9C730D76` còn **0 nguồn tạm**.
  (146 nguồn tạm còn lại thuộc hội thoại `CONV-EEA591C6` ở sổ khác, 4 nguồn thuộc `CONV-123`.)
- Cả 494 nguồn trong sổ đều có `origin_temporary_source_id` → chúng được **đẩy từ nguồn tạm lên sổ**,
  rồi bản nguồn tạm bị xóa (đúng mô tả trong vé).
- `conversation_source_selections.jsonl` của `CONV-9C730D76` còn 105 dòng, 15 dòng `enabled: true`
  nhưng **cả 15 đều trỏ tới nguồn tạm đã bị xóa** → số nguồn đang bật tính trên nguồn còn tồn tại = **0**.

## 2. Bước 1 — Refresh trang (F5)

Mở **phiên Chromium mới hoàn toàn** (không dùng tab sẵn có của user) vào `http://localhost:8501`,
mở sổ "Điều tra lỗi LSU", rồi `F5`.

Kết quả trên giao diện (đọc thẳng từ DOM, không phải ảnh):

```
Trong sổ tài liệu: 494 · Nguồn tạm trong cuộc trò chuyện: 0
Nguồn đang bật: 0
Đã chuẩn bị xong 0/494 tài liệu (0%) · Tài liệu sẵn sàng để tìm kiếm: 0/494 · Việc chuẩn bị đang tạm dừng. Bấm "Tiếp tục chuẩn bị" để chạy lại.
▶ Tiếp tục lập chỉ mục đang chờ
⚙️ Quản lý tài liệu · 494 tài liệu · 0 đang bật
```

Mở tiếp mục "Quản lý tài liệu":

```
Nguồn tạm trong cuộc trò chuyện → "Chưa có nguồn nào."
Tài liệu trong sổ → "Trang 1 / 33 (Tổng 494 tài liệu)"; không checkbox nào được tick (15 ô, 0 ô tick)
```

→ **Banner hiện ngay ở lần tải đầu tiên và vẫn hiện sau F5.** Trước và sau F5 chuỗi giao diện không đổi.

## 3. Bước 2 — Restart app

Đã dừng hẳn tiến trình `1632` + `15864`, xác nhận cổng 8501 trống, rồi chạy lại app bằng đúng script LAN
đã dùng ở vé P5 (`scratch/p5_run_lan.ps1`, giữ nguyên env gồm `AIOS_BGE_ONNX_MODEL_CHECKSUM`).

| Mục | Trước restart | Sau restart |
| --- | --- | --- |
| Tiến trình | `1632` (cha `15864`) | `18664` (cha `24812`) |
| Giờ khởi động | 09:15:46 | 12:23:03 |
| Cổng | `0.0.0.0:8501` | `0.0.0.0:8501` |

Mở lại trình duyệt vào app mới, mở sổ "Điều tra lỗi LSU":

```
Trong sổ tài liệu: 494 · Nguồn tạm trong cuộc trò chuyện: 0
Nguồn đang bật: 0
Chưa có nguồn nào.
Đã chuẩn bị xong 0/494 tài liệu (0%) · Tài liệu sẵn sàng để tìm kiếm: 0/494 · Việc chuẩn bị đang tạm dừng. Bấm "Tiếp tục chuẩn bị" để chạy lại.
▶ Tiếp tục lập chỉ mục đang chờ
⚙️ Quản lý tài liệu · 494 tài liệu · 0 đang bật
```

→ **Banner vẫn còn nguyên sau khi restart hẳn app.** Khẳng định: đây **không** phải rác phiên Streamlit cũ.

Kiểm thêm: không có tiến trình `bge`/`worker` nền nào đang chạy → khớp với việc giao diện báo
"đang tạm dừng" (`preparation_state = paused`).

## 4. Bước 3 — Đếm row trong ledger chuẩn bị nguồn

Ledger của runtime đang chạy: `local_runs/workspace_chat_rag_v2_production/workspace_chat.sqlite`
(81.920 byte, mtime `2026-09-30 12:08:39`). Mở chế độ chỉ đọc:

| Chỉ tiêu | Số |
| --- | --- |
| Tổng row trong `source_preparation_ledger` | **0** |
| Row `pending` | **0** |
| Row `processing` | **0** |
| Row `ready` / `failed` | 0 / 0 |
| `page_count` / `freelist_count` | 20 / **16** |

Diễn giải:

- **Không có việc nào đang chờ và không có việc nào đang xử lý** cho 494 nguồn này trong ledger thật.
  Hàng đợi trống hoàn toàn.
- `freelist_count = 16/20` trang: file **không phải DB mới tinh** — đã từng ghi dữ liệu rồi bị xóa.
  Khớp mốc thời gian: `temporary_sources.jsonl` bị ghi lại lúc `12:08:38` và ledger đổi lúc `12:08:39`
  → thao tác xóa nguồn tạm đã gọi `forget_workspace_chat_sources()` → `_delete_ledger_rows()`
  (`workspace_chat_rag_v2_adapter.py:2337`), đúng đường xóa row duy nhất cùng với nhánh "thử lại".
  (Số trang free **không** suy ra được con số row đã xóa, nên không nêu con số đó ra đây.)
- Mở app lại hay F5 **không** làm đổi mtime ledger → không phát sinh row mới khi chỉ xem trang.

## 5. Vì sao giao diện báo "0/494" — đọc code

`src/aios_habit/workspace_chat_app.py`:

- dòng 4650–4653: `enabled_ctx_sources` = các nguồn có `selections_map = True`;
- dòng 4655: chỉ khi `enabled_ctx_sources` khác rỗng mới gọi `schedule_workspace_chat_source_preparation`;
- dòng 4657: `tracked_prep_sources = enabled_ctx_sources if enabled_ctx_sources else ctx_all_sources`
  → **khi 0 nguồn đang bật, banner chuyển sang theo dõi TẤT CẢ nguồn** (494);
- dòng 4679: nút trong banner gọi `resume_workspace_chat_source_preparation(tracked_prep_sources)`;
- `workspace_chat_rag_v2_adapter.py` (`get_workspace_chat_preparation_summary`): nguồn không có row
  ledger và không có "durable coverage" bị đếm vào `pending_count`, `ready_count = 0`; vì
  `ready_count != total` và không có worker đang chạy nên `preparation_state = "paused"`
  → hiện câu "Việc chuẩn bị đang tạm dừng…" kèm nút mời chạy lại.

Hệ quả: `pending` mà banner nói tới là **pending suy diễn từ chỗ thiếu row**, không phải row `pending`
trong ledger (ledger đang 0 row). Vì vậy giao diện vừa báo "đang tạm dừng" vừa mời "Tiếp tục lập chỉ mục
đang chờ" dù không có việc nào trong hàng đợi.

### 5.1 Rủi ro nút "Tiếp tục" (không bấm, chỉ đọc code)

`resume_workspace_chat_source_preparation()` (`workspace_chat_rag_v2_adapter.py:2290`) giữ nguyên danh
sách nguồn nhận vào rồi gọi thẳng `schedule_workspace_chat_source_preparation()` →
`reconcile_and_enqueue_workspace_chat_sources()`. Với `tracked_prep_sources` = 494 nguồn, một cú bấm sẽ
**đẩy cả 494 tài liệu vào hàng đợi** để tách văn bản và nhúng vector trên máy chỉ có CPU.

**Đã KHÔNG bấm** nút "Tiếp tục lập chỉ mục đang chờ", cũng không bấm "Thử chuẩn bị lại" / "Bật tất cả" /
"Xóa nguồn" trong suốt vé này.

## 6. Bước 4 — 494 nguồn này có vector trong index chưa?

Để trả lời "0/494" là sai số hiển thị hay phản ánh dữ liệu thật, đã đối chiếu index production
(chỉ đọc). `document_id` của một nguồn được tính bằng `sha256(content_text)` (24 ký tự đầu, tiền tố
`wsc-`) theo `_document_id()` trong adapter, nên 494 nguồn gộp thành **262 `document_id` duy nhất**
(nhiều nguồn trùng nội dung).

| Chỉ tiêu | Số |
| --- | --- |
| `document_id` suy ra từ 494 nguồn | **262** |
| Trong đó có mặt trong `chunks` của index production | **0** |
| Tổng chunk / tổng `document_id` của index | 133.144 / 496 |

Đối chiếu thêm với ledger của runtime root **cũ** (`local_runs/workspace_chat_rag_v2_canary/workspace_chat.sqlite`):

| Chỉ tiêu | Số |
| --- | --- |
| Tổng row ledger root cũ | 1.148 |
| Row thuộc 262 `document_id` trên | 430 |
| Trong đó `failed` / `ready` | **406** / 24 |
| Lỗi phổ biến nhất | `source_text_unavailable` (391 row) |

→ 494 nguồn này **chưa từng được nhúng vector thành công** ở runtime đang chạy, và ở root cũ cũng gần
như toàn bộ ở trạng thái lỗi. Nói cách khác: "0/494" là con số **đúng về mặt dữ liệu**; cái sai nằm ở
chỗ banner **vẫn hiện và vẫn mời hành động** khi người dùng đã tắt hết nguồn, đồng thời con số 494 bị
lấy từ **toàn bộ nguồn của sổ** chứ không phải từ phần đang bật.

## 7. Ảnh chụp màn hình

Ảnh lưu trong `scratch/` (thư mục đã bị git-ignore, **không commit** để tránh lộ dữ liệu vận hành):

| Tệp | Nội dung |
| --- | --- |
| `scratch/banner0494-00-chon-so.png` | Màn hình chọn sổ trước khi mở |
| `scratch/banner0494-01-mo-so.png` | Sau khi mở sổ "Điều tra lỗi LSU", banner đã hiện |
| `scratch/banner0494-02-banner-quanly.png` | Banner + mục "Quản lý tài liệu" mở ra |
| `scratch/banner0494-03-sau-F5.png` | Sau khi F5 |
| `scratch/banner0494-04-sau-restart.png` | **Sau khi restart app** — banner vẫn còn |

Ảnh `banner0494-04` đã được mở kiểm lại bằng mắt: thấy rõ dòng "Đã chuẩn bị xong 0/494 tài liệu (0%)",
khung cảnh báo vàng "…Việc chuẩn bị đang tạm dừng. Bấm 'Tiếp tục chuẩn bị' để chạy lại.",
nút "Tiếp tục lập chỉ mục đang chờ" và dòng "⚙️ Quản lý tài liệu · 494 tài liệu · 0 đang bật".

## 8. Việc đã KHÔNG làm (theo đúng lệnh cấm của vé)

- Không sửa một dòng code nào; không đổi cấu hình runtime, không đụng manifest deploy.
- Không bấm "Tiếp tục chuẩn bị" / "Tiếp tục lập chỉ mục đang chờ" / "Thử chuẩn bị lại" / "Bật tất cả".
- Không xóa nguồn, không xóa sổ, không chạy embed.
- Không merge `main`; mọi thay đổi chỉ là file trạng thái + báo cáo trên nhánh `phieu-viec/rag-fix1`.
- Ngoài vé: app đã được **restart** (vé yêu cầu) — app mới đang chạy bình thường trên `0.0.0.0:8501`.

## 9. Đề xuất hướng xử lý (chờ Muse/user quyết, vé này không sửa)

1. **Ẩn banner khi không còn nguồn nào đang bật**: chỉ theo dõi `enabled_ctx_sources`; khi rỗng thì không
   hiện banner và không hiện nút "Tiếp tục" — tránh vừa gây hiểu sai vừa tạo đường enqueue 494 tài liệu.
2. Nếu vẫn muốn cho người dùng thấy tình trạng "chưa nhúng" của cả sổ, hiển thị ở dạng **thông tin tĩnh**
   trong "Quản lý tài liệu", **không** kèm nút hành động, và ghi rõ số đang bật so với tổng.
3. Cân nhắc chặn ở tầng dưới: `resume_workspace_chat_source_preparation` từ chối khi danh sách nguồn
   vượt một ngưỡng an toàn trên máy CPU-only, hoặc xếp theo lô nhỏ có xác nhận.
