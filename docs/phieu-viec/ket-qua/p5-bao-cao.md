# P5 — Deploy máy công ty với model ONNX đúng (KDTVN-PC0575)

- Ngày: 2026-09-30 (giờ máy `KDTVN-PC0575`, +07) · CPU-only, RAM 15,9 GB
- Repo: `D:\Sandbox\AIOS_habbit`, nhánh `phieu-viec/rag-fix1` (HEAD khi nhận vé: `338023e`)
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (`p5-deploy-onnx`; user duyệt P5 toàn bộ 5 chặng 2026-09-29 ~20:16)
- Kết luận: **ĐẠT bước 1–6 của vé.** Cây ONNX đúng đã về đúng chỗ (`sha256:9f81075f…`), env + sidecar đã đặt,
  index production giữ nguyên seal `062ec090…` (không byte nào bị ghi), smoke B1–B5 (B4 loại) **PASS cả 4 câu**
  ở chế độ đọc-only, app đã mở trên LAN `0.0.0.0:8501`. Hai việc cần Muse/user quyết (không tự làm theo vé):
  **(a)** firewall máy công ty chặn inbound — cần rule admin (lệnh ở mục 5.3); **(b)** 171 nguồn tài liệu của
  app chưa có vector trong index — muốn app tự trả lời thì phải "chuẩn bị" (embed) trên máy này (vé **cấm
  embed lại**; chi tiết mục 6).

## 0. Tóm tắt số liệu

| Hạng mục | Giá trị |
|---|---|
| Zip model từ Drive | `bge-m3-onnx-fp32.zip`, 1.326.939.447 byte, SHA-256 `4239479b…bf2f3c` (khớp báo cáo upload) |
| Cây giải nén | `models\bge-m3-onnx-fp32`, 9 file, 2.289.625.694 byte |
| Tree checksum (`sha256_model_tree`) | `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093` — **khớp seal** |
| `resolve_onnx_checksum` | trả đúng chuỗi trên (qua sidecar `models\bge-m3-onnx-fp32.sha256`) |
| Fingerprint backend tái tạo | `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` — khớp 107.331 vector dense trong index |
| Env đặt thêm | `AIOS_BGE_ONNX_MODEL_CHECKSUM` (User scope) = `sha256:9f81075f…` |
| Index production | 2.552.659.968 byte, SHA-256 `062ec090…ef8ca` **trước = sau** (mtime `2026-09-29 11:20:54` không đổi) |
| Backup index | `C:\AIOS_p5\library.sqlite.bak-20260930` (cùng SHA-256) |
| Smoke B1–B5 | **PASS 4/4**, exit 0, tổng 1.816 s (B1 533,8 / B2 343,5 / B3 433,7 / B5 459,8), `index_read_only=true` |
| App LAN | `0.0.0.0:8501` LISTENING (PID 1632), HTTP 200 qua `127.0.0.1` và `192.168.1.41` |

## 1. Chặng 1 — tải zip model từ Drive

- Link dùng (theo bàn giao của vé `onnx-upload-drive`): `https://drive.usercontent.google.com/download?id=1CnTrdYLfv1ZpbZMo8zivSOxuD1cVDIrG&export=download&confirm=t`
  → lưu `C:\temp\bge-m3-onnx-fp32.zip`, tải 36,5 s.
- Kích thước thực nhận: **1.326.939.447 byte** — khớp báo cáo bàn giao.
- SHA-256 zip: **`4239479bbc1e68a6aeeb73de35c9737a0dad8e79f1103a31c953c88718bf2f3c`** — khớp báo cáo.
  - Đo chéo 3 cách độc lập: `sha256sum` (MSYS), `certutil -hashfile` (Windows) và `hashlib.sha256` (Python) —
    cả ba cùng kết quả.
  - Ghi chú công cụ: `sha256sum -c` khi đọc checklist từ pipe báo "FAILED" hai lần dù hash thật đúng
    (quirk MSYS khi parse dòng checklist); đã loại trừ bằng 2 cách đo độc lập còn lại, không phải lỗi file.

## 2. Chặng 2 — giải nén + verify (bước 1–3 của vé)

- Giải nén bằng bsdtar: `tar -xf C:\temp\bge-m3-onnx-fp32.zip -C D:\Sandbox\AIOS_habbit\models`
  (46,9 s) → `models\bge-m3-onnx-fp32` gồm đúng 9 file, tổng **2.289.625.694 byte**
  (`model.onnx_data` 2.266.886.160 B; `sparse_linear.npy`/`sparse_linear_bias.npy` có mặt).
- Verify bằng chính hàm của mã (`scratch\p5_verify_tree.py`, chỉ đọc):

```text
default_onnx_model_dir = D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32
tree_hash             = sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093
tree_match            = True
resolve_onnx_checksum = sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093
declared_match        = True
fingerprint           = 016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb
fingerprint_match     = True
RESULT                = PASS
```

  ⇒ cây khớp seal, và fingerprint backend **trùng** định danh 107.331 vector ONNX trong index
  ⇒ không có tình huống "coi toàn bộ vector là hết hạn ⇒ embed lại" (rủi ro đã cảnh báo ở P3/P4).
- Đặt checksum theo 2 cơ chế cùng giá trị (không lệch nhau):
  - env `AIOS_BGE_ONNX_MODEL_CHECKSUM` = `sha256:9f81075f…` qua `setx` (**User scope**, đã xác nhận lại từ registry);
  - sidecar `models\bge-m3-onnx-fp32.sha256` (cơ chế `resolve_onnx_checksum` khuyến nghị ở P4).
- `/models/` nằm trong `.gitignore` (dòng 111) ⇒ cây 2,29 GB không thể lọt vào commit.

## 3. Chặng 3 — index production (bước 4 của vé)

- File: `local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
  - 2.552.659.968 byte; SHA-256 trước smoke `062ec090…` = **đúng seal P2** (bản copy đã có sẵn từ P2,
    không phải copy lại trong vé này — mtime `2026-09-29 11:20:54` giữ nguyên).
  - SHA-256 **sau** smoke và **sau** lượt test UI: vẫn `062ec090…` — không byte nào bị ghi (đúng lệnh cấm).
- Backup trước khi mở app: `C:\AIOS_p5\library.sqlite.bak-20260930` (2.552.659.968 byte, cùng SHA-256)
  — để nếu app có ghi (do người dùng bấm "chuẩn bị lại") thì vẫn còn bản đối chiếu.

## 4. Chặng 4 — smoke B1–B5 (B4 loại) — **PASS 4/4**

- Lệnh: `scratch\p2_b7_smoke.py` (đọc-only, dùng đúng manifest deploy, `index_read_only=true`,
  `ensure_embeddings_on_open=false`, provider guard phải `None`), chạy với env checksum trỏ cây mới.
- Kết quả (exit 0, tổng **1.816,25 s**):

| Câu | Giây | `must_contain` | Thiếu | `candidate_count` | `filtered_as_stale` | Kết quả |
|---|---:|---|---|---:|---:|---|
| B1 | 533,8 | `11922`, `12860`, `12626` | – | 260 | 0 | **PASS** |
| B2 | 343,5 | `YY2-Z151`, `YY2-Z152` | – | 210 | 0 | **PASS** |
| B3 | 433,7 | `nvarchar`, `4000` | – | 274 | 0 | **PASS** |
| B5 | 459,8 | `HOUSE_METHOD`, `0`, `1` | – | 263 | 0 | **PASS** |

- `provider_guard: create_synthesis_provider() is None` — không gọi AI ngoài; `eligible_chunks` 106.982.
- Nhận xét: chậm hơn lượt P2-B7b (456 s) khoảng 4× vì cây ONNX fp32 đúng nặng hơn và số ứng viên
  mỗi câu tăng (210–274 so với 29–100), trên CPU yếu của máy công ty. Đây là số đo thật, không phải lỗi.
- JSON đầy đủ: `scratch\p2_b7_report.json` (scratch bị git-ignore; số liệu chính đã chép ở trên).

## 5. Chặng 5 — mở LAN cho cả phòng

### 5.1. Cách chạy

Script `scratch\p5_run_lan.ps1` (bản LAN của `scripts/run_workspace_chat.ps1`, giữ nguyên env gốc + thêm
đúng 2 thứ: `--server.address 0.0.0.0`, `--server.headless true`, và checksum ONNX đúng):

```powershell
$env:AIOS_BGE_ONNX_MODEL_CHECKSUM = "sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093"
Start-Process -FilePath "D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe" `
  -ArgumentList @("-m","streamlit","run","src\aios_habit\workspace_chat_app.py",
    "--server.address","0.0.0.0","--server.port","8501","--server.headless","true",
    "--browser.gatherUsageStats","false","--server.fileWatcherType","none","--server.runOnSave","false") `
  -WorkingDirectory "D:\Sandbox\AIOS_habbit" -WindowStyle Hidden
```

- Đang chạy: PID launcher `15864`, tiến trình server PID `1632`
  (`netstat`: `TCP 0.0.0.0:8501 LISTENING 1632`).
- Kiểm tra HTTP: `127.0.0.1:8501` → **200**; `192.168.1.41:8501` → **200**.
- Kiểm tra UI thật (Chromium ẩn, URL LAN): app render màn "Chọn hoặc tạo sổ tài liệu để bắt đầu";
  vào sổ "Điều tra lỗi LSU" thấy đúng trạng thái nguồn; gửi thử 1 câu hỏi → app trả lời bằng thông báo
  "⚠️ Tìm kiếm tài liệu chưa sẵn sàng…" kèm nút "🔄 Thử chuẩn bị lại" (đúng thiết kế fail-closed
  khi nguồn chưa có vector). Suốt lượt này index/ledger **không đổi** (mục 3).

### 5.2. Link LAN

- Trang chọn sổ (an toàn, không tự enqueue gì): `http://192.168.1.41:8501/`
- Vào thẳng sổ đang có nguồn `failed` (an toàn, không tự embed):
  `http://192.168.1.41:8501/?nb=NB-E35A7BEE&conv=CONV-9C730D76`

### 5.3. ⚠ Firewall máy công ty — cần quyền admin (chặn truy cập từ máy khác)

- Hiện trạng: cả 3 profile firewall **ON**, policy `BlockInbound,AllowOutbound`; không có rule nào cho
  `python.exe`/port 8501 (đã kiểm tra rule inbound). Máy không có quyền admin
  (`netsh advfirewall firewall add rule …` → "The requested operation requires elevation"), nên **phiên này
  không thể mở firewall**.
- Lệnh cần chạy bằng quyền admin (IT hoặc user có quyền):

```text
netsh advfirewall firewall add rule name="AIOS Workspace Chat 8501" dir=in action=allow protocol=TCP localport=8501 profile=domain,private
```

- Vì firewall chặn, **chưa xác minh được truy cập từ máy khác** trong phiên này. Cách kiểm: từ máy đồng nghiệp
  mở `http://192.168.1.41:8501/` sau khi rule được thêm.

## 6. Ghi chú & rủi ro (đọc trước khi cho phòng dùng)

1. **App không tự embed khi mở trang** ở trạng thái hiện tại: 171 nguồn đang bật của sổ "Điều tra lỗi LSU"
   có dòng ledger `failed` với mã lỗi `preparation_init_bge_worker_model_verify_failed` — mã không nằm trong
   `_RETRYABLE_PREPARATION_ERRORS` nên `reconcile_and_enqueue…` bỏ qua ở mức ưu tiên thường
   (đã kiểm chứng bằng mtime index/ledger không đổi sau khi mở trang + gửi 1 câu hỏi).
2. **Nút "🔄 Thử chuẩn bị lại" và "chuẩn bị tài liệu" là hành động embed thật** (ghi vector vào index
   production, chạy hàng giờ trên CPU này với ~15M ký tự của 171 nguồn). Vé **cấm embed lại trên PC0575**,
   nên phiên này **không bấm**. Muốn app trả lời được thì cần user/Muse duyệt một vé "chuẩn bị tài liệu"
   riêng (dry-run + backup + theo dõi) — hoặc chấp nhận trạng thái hiện tại.
3. **Sổ "MOM / Opcenter" (CONV-EEA591C6) có 146 nguồn đang bật nhưng CHƯA có dòng ledger** — theo mã
   (`reconcile_and_enqueue…` + `_drain_preparation_queue`), ai mở sổ này thì app sẽ **tự xếp hàng và bắt đầu
   embed** 146 nguồn (~2,4M ký tự, nhiều giờ). Nếu chưa muốn vậy: tạm không mở sổ đó, hoặc yêu cầu OMP tắt
   chọn 146 nguồn trước (thao tác UI/1 lệnh) — chờ Muse/user quyết.
4. Index production đã backup (`C:\AIOS_p5\library.sqlite.bak-20260930`); nếu app có ghi thì luôn còn bản đối chiếu
   và có thể kiểm lại `062ec090…`.
5. Provider AI ngoài: lượt smoke chứng minh `create_synthesis_provider() is None` (không có khóa provider
   trong môi trường chạy). App UI có "Cầu nối AI (Gemini Web)" ở trạng thái chưa kết nối — không đổi gì.

## 7. Phạm vi & tuân thủ

- Không merge `main`, không force-push; không đụng ổ D máy nhà; không sửa mã nguồn sản phẩm (chỉ dùng
  `scratch/`, git-ignored). Không embed, không `--apply`, không ghi index/ledger (đã chứng minh bằng SHA + mtime).
- Không đặt thêm biến env nào khác ngoài `AIOS_BGE_ONNX_MODEL_CHECKSUM` (User scope) theo bước 3 của vé.
- File sinh trong vé: `scratch\p5_verify_tree.py`, `scratch\p5_run_lan.ps1`, `scratch\p2_b7_report.json`
  (git-ignored); báo cáo này; `docs/phieu-viec/mailbox-pc0575/trang-thai.md`.
- Thứ tự commit: xem `trang-thai.md` (mục `commit`).
