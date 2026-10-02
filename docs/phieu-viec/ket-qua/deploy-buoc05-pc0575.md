# Vé `DEPLOY-BUOC05-PC0575` — Deploy tính năng Bước 0–5 lên KDTVN-PC0575 + verify chạy thật CPU-only

- Trạng thái: **Verify deploy xong trên PC0575, chờ Muse duyệt.** Kết luận: **6/6 tính năng B0–B5 mở được và chạy được trên app thật (CPU-only, dữ liệu thật)**; B1-FEAT **1,6 s/câu** (3 mã đo, < 1 phút); index production `library.sqlite` **không đổi**; **1 phát hiện ưu tiên action (B3) cần Muse quyết** (mục 5.1); phần **LAN treo theo chỉ đạo 12:07 +07 của user/Muse** (mục 5.2).
- Máy: `KDTVN-PC0575` — Windows build `10.0.26200` x64, CPU-only, Wi-Fi mạng domain `km.local` (`10.170.157.164/24`); Python `3.11.15` (`.venv` repo).
- Nhánh: `phieu-viec/rag-fix1`. **SHA code deploy: `52cd29e2`** (`git diff 52cd29e2..HEAD -- src tests` = rỗng — các commit sau chỉ đụng `docs/phieu-viec/mailbox-pc0575/`). Commit phiên: `f004df2` (nhận vé) → `8367795` (Bước 1–2) → `cf93adb` (Bước 3) → `f0e95a5` (mốc B0–B3, sau rebase lên `be6b421` của Muse) → (báo cáo này) → (mốc `xong-cho-duyet` theo sau). Muse: `be6b421` (chỉ đạo ưu tiên tốc độ + vé `OPT-RAGV2-SPEED-APP-PC0575`).
- Ràng buộc giữ nguyên: **không đụng `main`, không force-push, không ghi index production RAG**; DB ca lỗi là bản copy tải từ Drive (ngoài repo); dữ liệu thật không vào Git.

## 0. Cổng gate (vòng khép kín)

- Watcher PC0575 (`D:\Sandbox\agent-mailbox\`) tự mở OMP **`LAUNCH 1/4` lúc 11:30:21** (`launchStallCount=1`) khi thấy vé `moi`; điều kiện mở **đã tới**: (a) `OPT-RAGV2-PYLOOPS` ĐẠT trên PC0575 2026-10-02 09:26 +07, (b) `B5` ĐẠT máy nhà 2026-10-01 ~17:50 +07 → **nhận vé (`dang-lam`, commit `f004df2`)** — không dùng nhánh “4 lần watcher”/`cho-muse`, không quay no-op.
- Giữa phiên, Muse đẩy `be6b421` (12:08 +07) kèm chỉ đạo mới của user: **ưu tiên số 1 là tốc độ trả lời; hoãn LAN/tường lửa** (ghi nhận treo, không chặn). Báo cáo này tuân thủ: mọi mốc tiến độ push đúng quy ước; phần LAN chỉ ghi nhận trạng thái (mục 5.2), không tiếp tục xử lý.

## 1. Bước 1 — SHA code deploy

- `git pull` fast-forward `ac10d7d..52cd29e2` (11:31). SHA code deploy ghi vào `trang-thai.md`: **`52cd29e2`**.
- Kiểm lại cuối phiên: `git diff 52cd29e2..f0e95a5 --stat -- src tests` **rỗng** (code không đổi trong toàn bộ phiên verify).

## 2. Bước 2 — DB ca lỗi thật (đúng cách máy nhà đã làm)

| Kiểm | Kết quả |
|---|---|
| Nguồn | Drive `AIOS_Data`, file ID `1ooa5RBApWuOW0L4Ubm5KOEkQwFn6ZEGy` (`upload-errordb-drive.md`, upload đã verify ẩn danh 01/10) |
| Tải | `curl.exe -q -L` ẩn danh → `C:/tmp/b0-dict/error_cases_dict.db`, HTTP 200 |
| Dung lượng | `54.480.896` byte |
| SHA-256 | `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` — **khớp ghim `6bd41a8c…2369`** |
| Toàn vẹn | `PRAGMA integrity_check` = `ok`; bảng `error_cases` = **15.707 ca** |
| Trỏ app | `AIOS_ERROR_CASES_DB=C:\tmp\b0-dict\error_cases_dict.db` (máy này **không** có `C:/tmp/buoc0-deploy/error_cases_deploy.db`; env được ưu tiên trước default theo `resolve_db_path`) |

- **Không tự bịa DB**; không insert ca giả (2 ca thử B5 gắn tiền tố `SIMULATED_` đã xoá ngay — mục 4.6).

## 3. Bước 3 — Restart app CPU-only + health + LAN

- **Đối chiếu env “như hiện tại” bằng bằng chứng**: viết công cụ `scratch/read_proc_env.py` đọc trực tiếp environment block của tiến trình app cũ (PID 22216, 107 biến) qua PEB, lưu `scratch/app_env_pid22216.json`. Khác biệt duy nhất theo hướng app có thêm là các biến do `RUN_AIOS_WORKSPACE_CHAT.bat` tự set (numpy dense/timeout/streamlit/PYTHONPATH) — không có biến nào của app cũ bị thiếu khi restart.
- **Restart 11:47:54** bằng `RUN_AIOS_WORKSPACE_CHAT.bat` (kịch bản `scratch/pc0575_deploy_restart.ps1`, log `scratch/app_lan_deploy_buoc05_20261002.log`), env thêm:
  - `AIOS_ERROR_CASES_DB=C:\tmp\b0-dict\error_cases_dict.db` (theo Bước 2);
  - `AIOS_FEATURE_CHAT_ACTION=1` — **bắt buộc để B0–B5 “mở được”** trên app (framework chat action fail-closed); **mặc định trong repo vẫn TẮT/không đổi**, đây chỉ là env phiên chạy máy này. Kiểm bằng cách đọc env tiến trình mới: `AIOS_ERROR_CASES_DB` + `AIOS_FEATURE_CHAT_ACTION=1` có mặt.
- **Health/LAN (local)**:

| Kiểm | Kết quả |
|---|---|
| `/_stcore/health` localhost | `ok` |
| `/_stcore/health` qua IP LAN `10.170.157.164:8501` | `ok` |
| Listener | `0.0.0.0:8501` + `[::]:8501` (PID app mới `13664`) |
| LAN từ thiết bị khác | **Chặn bởi Windows Firewall của máy** — Block rules theo chương trình `…cpython-3.11.15…python.exe` áp profile **Domain** (`{350DF9F6…}` TCP + `{9B31A0F1…}` UDP) và **Public** (`{C91566E5…}`/`{768186E8…}`); **0 rule Allow** cho port 8501/python/cmd (ActiveStore); thử `netsh advfirewall firewall add rule … profile=domain,private,public` → `The requested operation requires elevation` (không có quyền admin). |

- ℹ️ Theo chỉ đạo 12:07: **hoãn LAN** — ghi thành **việc treo**: khi cần mở cho người dùng, người có admin chạy lệnh thêm rule (kèm `profile=domain` — khác P5b vì mạng hiện tại là domain) + cân nhắc xử lý 2 rule Block.

## 4. Bước 4 — Verify B0–B5 với dữ liệu thật (trên app thật, qua ô chat UI)

Mức verify: **điều khiển Chromium thật** vào app LAN (local), gõ lệnh thật trong ô chat (“Câu hỏi gửi AI”), gửi bằng Ctrl+Enter — đúng entry `workspace_chat_app` → `chat_action.handle_chat_text` mà người dùng công ty sẽ dùng. Thời gian đo = từ lúc gửi đến khi bong bóng trả lời hiện.

### 4.1 B0-FORM — ĐẠT

| Việc | Kết quả |
|---|---|
| Mở form (`nhập báo cáo lỗi`) | Bong bóng “Nhập báo cáo lỗi (form Bước 0)” render **đủ 13 nhãn** (12 trường; “Ngày phát sinh”/“Ngày đóng” tách riêng), **5 trường bắt buộc có dấu `*`**: Công đoạn, Error code, Hiện tượng, Nguyên nhân, Đối sách |
| Validate thiếu cả 5 | “Chưa ghi được” + đúng **5 lỗi**: Công đoạn · Error code · Hiện tượng · Nguyên nhân · Đối sách |
| Validate thiếu 1 (Đối sách) | Điền đủ 11 trường còn lại → báo **đúng 1 lỗi**: “Thiếu trường bắt buộc: Đối sách.” — không ghi DB |
| Ràng buộc không ghi DB | SHA DB không đổi sau 2 lượt bị chặn |

### 4.2 B1-FEAT — ĐẠT (số giây/câu)

| Mã thật | Kết quả | Thời gian (UI) |
|---|---|---|
| `F000` | Top-5 ca + từ điển (F_SYSTEM) + mỗi thẻ đủ **Hiện tượng/Nguyên nhân/Đối sách/Nguồn gốc** (`Loi KDTPS.xlsx › History KDTPS › dòng N`) | **1,6 s** |
| `C4701` | Top-5 ca + từ điển (C_CALL, tên “Bất thường thiết bị VIDEO_ASIC”) | **1,6 s** |
| `C7620` | Top-5 ca + từ điển (“Lỗi thời gian đăng ký màu”) | **1,6 s** |

- “Tìm thấy 5 ca lỗi liên quan đến <mã> trong **15.707 ca lịch sử**”; **không hỏi ngược** (không rơi về luồng RAG). Xa dưới ngưỡng < 1 phút.

### 4.3 B2 — ĐẠT (log ghi nhận)

- Sau tra cứu `F000`: gõ `đánh giá đúng` → “Đã ghi nhận đánh giá: **đúng** cho 2023/384, 2024/3848, 2023/183, 2023/375, 2023/501”; gõ `đánh giá một phần` → ghi thêm bản ghi mới (mới nhất thắng).
- DB sau phiên: `suggestion_calls` 3 → **8**, `suggestion_ratings` 3 → **5** (2 đánh giá mới gắn đúng call của hội thoại test; các dòng còn lại là log tra cứu của B1). Đây là **hành vi thiết kế** (vòng phản hồi ghi log khi dùng app).

### 4.4 B3 — ĐẠT có điều kiện (kèm phát hiện ưu tiên action, mục 5.1)

- **Hiện tượng thật** (lấy từ dữ liệu thật, chuỗi nguyên văn đã dùng ở vé B3 máy nhà): `Stopper Paperがスムーズに動かない`.
- Demo qua UI bằng phrasing **`lập cây điều tra 4M: Stopper Paperがスムーズに動かない`** → **1,5 s**:
  - Cây **4M đủ 4 nhánh** (Con người/Máy móc/Vật liệu/Phương pháp), mỗi nhánh câu hỏi cụ thể + mục “Thu thập:”;
  - **Chuỗi Why-Why 5 tầng**;
  - **Xuất file đúng format báo cáo công ty**: `local_runs/dieu_tra/20261002-122701-stopper-paper.md` + `.docx` — kiểm `python-docx`: bảng **13 dòng** `Item／項目`/`Details／詳細`, có tiêu đề 調査報告書, hiện tượng vào “Contents of defect”, kế hoạch vào “Investigation content and results” (kèm “Cây điều tra 4M” + “Why-Why”).
- ❌ **Phrasing chuẩn của vé (`gợi ý hướng điều tra cho hiện tượng …`) bị action tra cứu cướp** — không vào được B3 bằng câu chuẩn (chi tiết + repro ở mục 5.1).

### 4.5 B4 — ĐẠT (script E2E read-only trên DB thật)

- `scratch/pc0575_b4_e2e.py` → `C:/tmp/deploy-buoc05/b4/b4_results.json`; DB mở `mode=ro`.
- **Biểu đồ xu hướng chạy được**: `fetch_records` đủ **15.707 ca**, `occurred_at` 2023-01-05 → 2026-08-27, **41 kỳ tháng**; PNG `chart_model_Virgo.png` **1920×1080/66.239 B**, mở lại bằng Pillow OK, **6.874 pixel đỏ** (vòng khoanh điểm vượt ngưỡng của engine JIG).
- **Cảnh báo bắn đúng theo ngưỡng**: ô kiểm tra `2026-07 · Model=Virgo` = **147/651 = 22,5806%** (engine khớp **tính tay từng chữ số**); ngưỡng `21,6%` → bắn **đúng ô** (“22.6% vượt ngưỡng 21.6% trong kỳ 2026-07”); ngưỡng `23,6%` → **không bắn ô đó**. Cảnh báo sớm “tăng liên tục 3 kỳ”: model 3 · line 5 · công đoạn 26 · máy 21 (khớp máy nhà).
- **Báo cáo định kỳ sinh được file**: `C:/tmp/deploy-buoc05/b4/report/bao_cao_xu_huong_2026-10-02_1235.md` (**464.921 B**, đủ 4 mục Model/Line/Công đoạn/Máy, có “Bảng tỉ lệ phát sinh”) + 8 chart; **mail stub**: lần 1 `da_gui` (bắt đúng 1 thư, subject “...55 cảnh báo”), lần 2 cùng cooldown `khong_gui`, lần 3 không người nhận `khong_gui` nhưng **file vẫn sinh**.
- Ghi chú: máy này **không có** file ngưỡng local `local_cases/nguong_xu_huong_loi.json` (máy nhà có) nên báo cáo mặc định chỉ có cảnh báo sớm (**55**), không có dòng “vượt ngưỡng”; phần bắn-theo-ngưỡng đã kiểm riêng bằng ngưỡng truyền tay như trên.

### 4.6 B5 — ĐẠT (nhập mới + phân loại + cảnh báo tái phát), đã dọn ca thử

- **Ca 1** (mã thật `C6950`, gắn tiền tố `SIMULATED_` ở “Tên lỗi”): → phiếu **`FORM-20261002-0001`**, “Đủ 12 trường chuẩn đã lưu vào DB Bước 0”, thẻ **Phân loại tự động**: nhóm “Khác” (độ tin cậy 35% → có dòng “AI chưa chắc chắn — người nhập kiểm tra lại”), công đoạn/bộ phận gợi ý; **“Đã đối chiếu lịch sử: tìm thấy 5 ca tương tự.”**
- **Ca 2** (cùng mã, khác Model/Line để không trùng dedup): → `FORM-20261002-0002` + **⚠️ Cảnh báo tái phát**: *“mã C6950 đã phát sinh **2 lần** trong **168 giờ** qua. Đề xuất đối sách: …(đối sách lấy từ phiếu FORM-20261002-0001)”* — đúng cơ chế form (nguồn đối sách = trường `investigation` của phiếu trước, khớp cách máy nhà).
- **Dọn ngay sau khi xong** (`scratch/pc0575_b5_cleanup.py`): xoá đúng 2 ca `SIMULATED_` + batch `FORM-nhap-lieu` do chúng tạo → **15.709 → 15.707 ca**, `integrity_check=ok`, “còn ca đích: 0”.

## 5. Phát hiện (đề Muse quyết)

### 5.1 ⚠️ Ưu tiên action bị đảo — B3 không vào được bằng câu chuẩn của vé

- **Hiện tượng:** câu `gợi ý hướng điều tra cho hiện tượng LCD画面にF000表示` (đúng phrasing vé B3) → trả lời **“Tra cứu lỗi tương tự”** (action `tra_cuu_loi_tuong_tu`), không phải `goi_y_huong_dieu_tra`.
- **Repro (tái hiện được, không cần DB):**
  ```
  python -c "import sys; sys.path.insert(0,'src'); from aios_habit.chat_action import load_builtin_actions, match_action, ChatActionRequest; load_builtin_actions(); m=match_action(ChatActionRequest(question='gợi ý hướng điều tra cho hiện tượng LCD画面にF000表示')); print(m.name)"
  → tra_cuu_loi_tuong_tu   (kỳ vọng: goi_y_huong_dieu_tra)
  ```
  Kiểm thêm 3 câu khác (kể cả **không có mã lỗi**) đều ra `tra_cuu_loi_tuong_tu`.
- **Nguyên nhân (đã khoanh vùng):**
  - Thứ tự đăng ký thực tế khác thiết kế: `… nhap_bao_cao_loi → tra_cuu_loi_tuong_tu → lap_bao_cao_dieu_tra → goi_y_huong_dieu_tra …` — tức **lookup đứng trước dieu_tra**, trái chú thích ngay trong `chat_action.py` (“tra_cuu_loi_tuong_tu stays last … lowest match priority”).
  - Do **import side-effect**: `chat_action_bao_cao_dieu_tra.py` (commit `b330020`, report agent) có `from .chat_action_error_lookup import …` ở cấp module (dòng 58) → khi `load_builtin_actions` import module này (trước `dieu_tra` trong `BUILTIN_ACTION_MODULES`), module lookup được nạp và **tự đăng ký** trước.
  - Điều kiện khớp của lookup lại rất rộng: super().matches theo hint có cả **`hien tuong`, `trieu chung`, `ket giay`, `jam`**, cộng fallback `_CODE_RE` (`[CFJ]\d{3,4}`) — nên mọi câu B3 chứa “hiện tượng” hoặc chứa mã lỗi (rất phổ biến trong dữ liệu thật) đều bị cướp.
- **Ảnh hưởng deploy:** người dùng nhập hiện tượng kèm mã lỗi sẽ nhận kết quả tra cứu thay vì cây điều tra; B3 chỉ tiếp cận được bằng phrasing khác (`lập cây điều tra 4M: …`) khi chuỗi không chứa mã. Đây là lỗi phía **ưu tiên/đăng ký action**, không phải lỗi nội dung B3.
- **Đề xuất (Muse code trên VM):** đảm bảo lookup đăng ký **cuối cùng** (bỏ import side-effect — chuyển import vào trong hàm, hoặc thêm cơ chế priority tường minh cho `ChatAction`); sau vá, chạy lại repro trên + test “canonical B3 phrasing”.
- Demo B3 trong vé này đã thực hiện bằng phrasing thay thế (mục 4.4) để chứng minh năng lực B3 chạy tốt khi tới được action.

### 5.2 LAN từ thiết bị khác — **treo theo chỉ đạo 12:07**

- Trạng thái máy: app chạy local + LAN-local OK (`10.170.157.164:8501` = `ok`), nhưng máy khác trong mạng bị **Windows Firewall chặn inbound** (Block rules Domain/Public cho `cpython-3.11.15\python.exe`; không có rule Allow; phiên này không có admin — `netsh … add rule` trả `requires elevation`).
- Việc cần khi mở lại: người/IT có admin thêm rule Allow `localport=8501 profile=domain,private,public` (+ xử lý 2 rule Block nếu muốn chắc), rồi thử từ điện thoại cùng Wi-Fi. **Không tiếp tục trong vé này** theo chỉ đạo ưu tiên tốc độ.

### 5.3 Ghi nhận nhỏ (không chặn)

- PNG chart B4 của máy này **66.239 B / 6.874 px đỏ** so máy nhà **65.597 B / 6.989 px đỏ** — cùng dữ liệu/cùng engine; khác nhẹ do nội dung stamp/hiển thị trên hình (không ảnh hưởng tiêu chí). Muốn byte-exact cần chốt lại phần stamp — ngoài phạm vi.
- Thông điệp tái phát gọi “Đề xuất đối sách” nhưng nguồn thật là trường `investigation` của phiếu trước (đúng code; vé B5 máy nhà cũng ghi nhận cách này).

## 6. An toàn dữ liệu — ĐẠT

| Hạng mục | Trước | Sau | Kết luận |
|---|---|---|---|
| Index production `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` | SHA `e54c7745b86cb360d903c5e211827126b6c8d69606c8809bcdd7f90737c47fe7`; mtime 2026-10-01 15:46:42; 2.842.415.104 B | **y nguyên** (SHA + mtime + size) | **Không đổi** ✔ |
| DB deploy `C:/tmp/b0-dict/error_cases_dict.db` | SHA `6bd41a8c…2369` (lúc tải, 15.707 ca) | `be9dfef3…968a`, 15.707 ca, `integrity=ok` | Thay đổi **đúng thiết kế** (B2 ghi log đánh giá/tra cứu; B5 nhập rồi dọn 2 ca `SIMULATED_`); số ca trở về 15.707 |
| `git status` | — | chỉ `M uv.lock` (có sẵn từ đầu phiên, không commit) + file watcher untracked | Sạch theo quy ước |

- Không ghi index/vector; không đụng ổ D dữ liệu; file sinh: `local_runs/dieu_tra/` (gitignored), `C:/tmp/deploy-buoc05/b4/`, `scratch/` (gitignored).

## 7. Cổng nền nhanh (code không đổi từ `52cd29e2`)

- `compileall src tests` **PASS**; `aios_habit.cli audit` → `{"status": "PASS", "errors": [], "warnings": []}`; `import aios_habit.workspace_chat_app` **OK**; health app `ok` (đầu–cuối).
- Không chạy lại full `pytest` (code không đổi so vé `OPT-RAGV2-LEXICAL` đã chạy 3.641 đạt trên chính máy này); vé này là vé deploy/verify.

## 8. Bằng chứng thô

- Công cụ/kịch bản (gitignored): `scratch/read_proc_env.py` (đọc env tiến trình qua PEB), `scratch/pc0575_deploy_restart.ps1` (restart + env DB/cờ), `scratch/pc0575_b4_e2e.py`, `scratch/pc0575_b5_cleanup.py`, log app `scratch/app_lan_deploy_buoc05_20261002.log`.
- Kết quả: `C:/tmp/deploy-buoc05/b4/{b4_results.json, chart_model_Virgo.png, report/bao_cao_xu_huong_2026-10-02_1235.md, report/chart_*.png}`; file B3 `local_runs/dieu_tra/20261002-122701-stopper-paper.{md,docx}`.
- Bằng chứng UI: điều khiển Chromium thật, ảnh chụp màn hình phiên; nhật ký hội thoại “Cuộc trò chuyện 02/10 11:51” trong sổ “Điều tra lỗi LSU” (hội thoại test do phiên này tạo, giữ lại làm bằng chứng).
- Mốc `trang-thai.md`: nhận vé `f004df2` → B1–2 `8367795` → B3 `cf93adb` → B0–B3 `f0e95a5` → báo cáo này + `xong-cho-duyet`.

## 9. Kết luận & đề xuất cho Muse

1. **ĐẠT tiêu chí deploy**: 6/6 tính năng B0–B5 mở được và chạy được trên PC0575 CPU-only với dữ liệu thật; **B1-FEAT 1,6 s/câu** (3 mã, < 1 phút); index production không đổi; không merge `main`.
2. **Chờ Muse quyết mục 5.1** (ưu tiên action B3 — đề xuất vá đăng ký lookup cuối cùng). Phần LAN: treo theo chỉ đạo, có sẵn bằng chứng + lệnh cho IT khi cần.
3. Theo `hang-cho` + chỉ đạo 12:07: vé tiếp theo của PC0575 là **`OPT-RAGV2-SPEED-APP-PC0575`** (đo tốc độ hỏi đáp app thật + hồ sơ nút thắt).
