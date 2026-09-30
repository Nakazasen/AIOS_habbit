# Vé `deploy-fix-banner-0494` — Pull fix + restart app (máy `KDTVN-PC0575`)

- Ngày: 2026-09-30 (12:44–12:52 +07), máy `KDTVN-PC0575` (OMP).
- Nhánh: `phieu-viec/rag-fix1`. Vé này **chỉ deploy + kiểm chứng**: không sửa code, không merge `main`.
- Kết quả: **ĐẠT**. Fix `e5d37fc` đã có trên máy, app đã được restart bằng đúng script LAN của vé P5,
  banner "0/494 tài liệu" **không còn hiện** khi 0 nguồn đang bật, app vẫn phục vụ LAN bình thường.

## 0. Kết luận ngắn

1. `git pull origin phieu-viec/rag-fix1` chạy sạch (fast-forward `8611f9a..7e9181e`). Fix `e5d37fc`
   **đã có mặt** trên máy: `git merge-base --is-ancestor e5d37fc HEAD` → đúng.
2. App cũ (PID `24812`/`18664`, khởi động **12:23:03**) đang chạy **code trước fix** → đã dừng hẳn và
   restart bằng `scratch/p5_run_lan.ps1` (giữ nguyên env `AIOS_BGE_ONNX_MODEL_CHECKSUM`).
3. Trên app mới, mở sổ "Điều tra lỗi LSU" (494 tài liệu, **0 nguồn đang bật**): banner
   "Đã chuẩn bị xong 0/494 tài liệu (0%) … Bấm 'Tiếp tục chuẩn bị' để chạy lại" **không còn hiện**,
   nút "Tiếp tục lập chỉ mục đang chờ" **không còn tồn tại**. Kiểm chứng trên **phiên trình duyệt
   hoàn toàn mới** và **sau F5** — kết quả giống nhau.
4. Ledger chuẩn bị nguồn **không đổi** (`12:08:39`, 0 row, 0 pending, 0 processing) → không có thao tác
   nào vô tình enqueue nguồn.
5. App mới vẫn phục vụ LAN: `0.0.0.0:8501` LISTENING (PID `21016`), HTTP 200 trên cả `localhost` và
   `192.168.1.41`.

## 1. Bước 1 — Pull nhánh

```
$ git pull origin phieu-viec/rag-fix1
From https://github.com/Nakazasen/AIOS_habbit
 * branch            phieu-viec/rag-fix1 -> FETCH_HEAD
   8611f9a..7e9181e  phieu-viec/rag-fix1 -> origin/phieu-viec/rag-fix1
Updating 8611f9a..7e9181e
Fast-forward
 docs/phieu-viec/mailbox-pc0575/prompt.md     | 31 +++++++++++-----------------
 docs/phieu-viec/mailbox-pc0575/trang-thai.md | 12 +++++------
 src/aios_habit/workspace_chat_app.py         |  6 +++++-
 tests/test_large_library_nonblocking_chat.py |  7 ++++++--
```

**Lưu ý về mốc `e5d37fc` trong prompt:** prompt yêu cầu `git log --oneline -1` ra `e5d37fc`, nhưng
Muse đã push thêm commit phát vé lên trên, nên **HEAD thực tế là `7e9181e`** (commit "phat hanh ve
deploy-fix-banner-0494"). Fix vẫn nằm nguyên trong lịch sử:

| Kiểm tra | Kết quả |
| --- | --- |
| `git log --oneline -1` | `7e9181e` mailbox(pc0575): phat hanh ve deploy-fix-banner-0494 |
| `git log --oneline -2` (dòng 2) | `e5d37fc` fix(workspace-chat): banner chi theo doi nguon dang bat… |
| `git merge-base --is-ancestor e5d37fc HEAD` | **đúng** — `e5d37fc` là tổ tiên của HEAD |
| Giờ commit của fix | 2026-09-30 12:35:01 +07 |

**Code trên đĩa đúng bản đã sửa** (`src/aios_habit/workspace_chat_app.py`, mtime `12:44:26`):

```
4661:                tracked_prep_sources = enabled_ctx_sources
```

Dòng fallback cũ `enabled_ctx_sources if enabled_ctx_sources else ctx_all_sources` **không còn** trên đĩa.

## 2. Bước 2 — Restart app bằng script LAN của vé P5

App đang chạy lúc bắt đầu **là code trước fix** — đây là lý do restart là bắt buộc:

| Mục | Trước restart | Sau restart |
| --- | --- | --- |
| Tiến trình | `24812` (cha `18664`) | `21016` (cha `7924`) |
| Giờ khởi động | **12:23:03** (trước khi pull fix lúc 12:44) | **12:47:03** |
| Cổng | `0.0.0.0:8501` | `0.0.0.0:8501` |
| HTTP `localhost:8501` | (có client LAN đang kết nối) | **200** |
| HTTP `192.168.1.41:8501` | — | **200** |
| `/_stcore/health` | — | `ok` |

Lệnh chạy: `powershell -NoProfile -ExecutionPolicy Bypass -File scratch\p5_run_lan.ps1` → `PID=7924`.
Script giữ nguyên env gồm `AIOS_BGE_ONNX_MODEL_CHECKSUM=sha256:9f81075f…`, `PYTHONPATH=src`,
`OMP_NUM_THREADS=1`, `STREAMLIT_SERVER_FILE_WATCHER_TYPE=none`. Cả hai tiến trình cũ (`24812`, `18664`)
xác nhận đã chết trước khi app mới lên.

## 3. Bước 3 — Verify banner trên giao diện (0 nguồn đang bật)

Điều kiện tái hiện giữ nguyên như vé điều tra: sổ **"Điều tra lỗi LSU"**, **494 tài liệu trong sổ**,
**0 nguồn đang bật**.

### 3.1 Chuỗi giao diện trên app mới

Đọc thẳng từ DOM (không phải đọc ảnh):

```
📚 Thư viện nguồn
Trong sổ tài liệu: 494 · Nguồn tạm trong cuộc trò chuyện: 0
Nguồn đang bật: 0
Nguồn đang dùng: Các nguồn được bật sẽ được dùng khi trả lời.
...
➕ Thêm tài liệu/ảnh để AI tham khảo
⚙️ Quản lý tài liệu · 494 tài liệu · 0 đang bật
📌 Kết quả & bằng chứng
```

So với **trước fix** (vé `dieutra-banner-0494`), khối giữa hai mục cuối từng là:

```
Đã chuẩn bị xong 0/494 tài liệu (0%)
[khung cảnh báo vàng] Đã chuẩn bị xong 0/494 tài liệu (0%) · Tài liệu sẵn sàng để tìm kiếm: 0/494 ·
                      Việc chuẩn bị đang tạm dừng. Bấm "Tiếp tục chuẩn bị" để chạy lại.
▶ Tiếp tục lập chỉ mục đang chờ
```

### 3.2 Kiểm tra sự vắng mặt (assertion, không phải cảm nhận)

| Chuỗi phải VẮNG MẶT | Phiên thường | Sau F5 | Phiên mới hoàn toàn |
| --- | --- | --- | --- |
| `0/494` | vắng | vắng | vắng |
| `Đã chuẩn bị xong` | vắng | vắng | vắng |
| `Tài liệu sẵn sàng để tìm kiếm` | vắng | — | — |
| `Việc chuẩn bị đang tạm dừng` | vắng | — | — |
| `Tiếp tục chuẩn bị` | vắng | vắng | vắng |
| `Tiếp tục lập chỉ mục` | vắng | vắng | vắng |
| `Thử chuẩn bị lại` | vắng | — | vắng |
| `Bật tất cả` | vắng | — | vắng |

Liệt kê **toàn bộ 19 nút** đang có trên trang — không có nút nào thuộc nhóm cấm:

```
⬅️ Quay lại danh sách sổ · ➕ Tạo cuộc trò chuyện mới · 👉 💬 Cuộc trò chuyện 25/08 18:01 ·
🧠 Nén ngữ cảnh hội thoại · 🔄 Kết nối lại & làm mới · Sổ bài học · chevron_left ·
Chuyển đổi giữa chế độ đọc rộng và đối chiếu 2 cột · 🕸️ Xem đồ thị bằng chứng ·
➕ Đính kèm · ⬆️ Hỏi · ⇣ Xuống câu trả lời mới nhất · 🔗 Link to heading (×n) …
```

### 3.3 Đo khoảng cách phần tử — chứng minh "chỗ trống"

Đo offset trong vùng cuộn chính (`[data-testid="stMain"]`):

| Phần tử | offset (px) |
| --- | --- |
| `➕ Thêm tài liệu/ảnh để AI tham khảo` | 2508 |
| `⚙️ Quản lý tài liệu · 494 tài liệu · 0 đang bật` | 2564 |

Hai mục **cách nhau 56 px** — tức đúng khoảng của một expander, **không còn khe nào cho banner và nút
"Tiếp tục" từng nằm ở giữa** (trước fix, banner + nút chiếm khoảng 200 px tại vị trí này).

### 3.4 Xác nhận không đụng hàng đợi

Ledger `local_runs/workspace_chat_rag_v2_production/workspace_chat.sqlite` (mở `mode=ro`):

| Chỉ tiêu | Trước vé | Sau verify |
| --- | --- | --- |
| mtime | `2026-09-30 12:08:39` | `2026-09-30 12:08:39` (**không đổi**) |
| Tổng row | 0 | 0 |
| `pending` / `processing` | 0 / 0 | 0 / 0 |

→ Mở sổ, F5, mở phiên mới **không** enqueue gì và **không** tạo row mới.

## 4. Bước 4 — App vẫn phục vụ LAN

```
LAN 192.168.1.41:8501 -> HTTP 200
localhost:8501        -> HTTP 200
  TCP    0.0.0.0:8501   0.0.0.0:0   LISTENING   21016
```

App mới (PID `21016`) listen `0.0.0.0:8501` — đúng cấu hình LAN của vé P5/P5b, không đổi gì về mạng.

## 5. Ảnh chụp màn hình

Ảnh lưu trong `scratch/` (thư mục git-ignore, **không commit** để tránh lộ dữ liệu vận hành):

| Tệp | Nội dung |
| --- | --- |
| `scratch/deploy-fix-banner-0494-01-sau-restart.png` | App mới, đáy vùng cuộn: "Thêm tài liệu/ảnh để AI tham khảo" → thẳng "Quản lý tài liệu · 494 tài liệu · 0 đang bật", **không còn banner** |
| `scratch/deploy-fix-banner-0494-04-dau-trang.png` | App mới, đầu vùng cuộn: hội thoại sổ "Điều tra lỗi LSU", không có cảnh báo chuẩn bị |
| `scratch/deploy-fix-banner-0494-05-thu-vien-nguon.png` | Sidebar: "📚 Thư viện nguồn · Trong sổ tài liệu: 494 · Nguồn đang bật: 0", không banner |
| `scratch/deploy-fix-banner-0494-06-phien-moi.png` | **Phiên trình duyệt mới hoàn toàn** mở lại sổ — sạch banner |
| `scratch/banner0494-04-sau-restart.png` | (ảnh cũ, vé điều tra) **Trước fix** — banner "0/494" + nút "Tiếp tục lập chỉ mục" còn nguyên |

Đối chiếu cặp ảnh `banner0494-04-sau-restart.png` (trước) và
`deploy-fix-banner-0494-01-sau-restart.png` (sau): cùng sổ, cùng điều kiện 494/0, cùng vùng giao diện —
khác duy nhất ở chỗ banner + nút "Tiếp tục" đã biến mất.

## 6. Việc đã KHÔNG làm (theo đúng lệnh cấm của vé)

- Không bấm "Thử chuẩn bị lại" / "Tiếp tục chuẩn bị" / "Tiếp tục lập chỉ mục đang chờ" / "Bật tất cả".
- Không sửa một dòng code nào (thay đổi duy nhất ngoài file trạng thái là **không có**).
- Không merge `main`.
- Không đụng ổ D máy nhà — toàn bộ thao tác trên `D:\Sandbox\AIOS_habbit` của `KDTVN-PC0575`.
- Không xóa nguồn, không xóa sổ, không chạy embed.
