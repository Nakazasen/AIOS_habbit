# Vé APP-RESTORE-DEFAULT-PC0575 — đưa app Workspace Chat về env mặc định sau demo WIRE-QA

- Máy thực hiện: KDTVN-PC0575 (CPU-only). Ngày: 2026-10-06 (+07). Nhánh: `phieu-viec/rag-fix1`. Người làm: OMP.
- Trạng thái: xong-cho-duyet (chờ Muse review).
- Phạm vi: chỉ thao tác process + smoke 1 câu qua UI. **Không sửa code**, không bật/tắt flag của vé khác, không merge `main`. Mọi commit trên `phieu-viec/rag-fix1`.

## 1. Bối cảnh

- Trước phiên, port 8501 do **app demo WIRE-QA** giữ: cây process `streamlit.exe` pid `28028` → python `18636` → python `26880` (báo cáo WIRE-QA §7.5 nói rõ: muốn về mặc định thì tắt pid này rồi mở lại bằng `RUN_AIOS_WORKSPACE_CHAT.bat`).
- Theo quy ước, về dùng thật phải ở **env mặc định** — flag `AIOS_FEATURE_WIRE_QA_CAGENT` TẮT (không set tay), không ghim `AIOS_AI_BACKEND`.

## 2. Cổng gate (theo dặn của user)

- Watcher ghi `LAUNCH [omp] 1/4` lúc **15:29:56** cho phiên này — **chưa tới ngưỡng 4 lần tự mở**; vé mới đã phát hành trong `prompt.md` lúc 15:29 và app demo còn sống → **điều kiện mở CÓ**, làm tiếp (không rơi vào ca phải đặt `cho-muse`).

## 3. Tắt app demo

- `taskkill /PID 28028 /T /F` → kết quả: terminated `26880` (con của `18636`), `18636` (con của `28028`), `28028` (con của `3616`).
- Xác minh sau tắt: `netstat` port **8501 không còn process lắng nghe**; `Get-Process` không còn 3 pid trên.
- Worker BGE bền (`pid 25148`, mở từ 14:46) **không** thuộc cây này nên vẫn sống — giữ ấm cho lần mở lại.

## 4. Mở lại bằng đúng file bat

- Chạy **đúng** `RUN_AIOS_WORKSPACE_CHAT.bat` (không chỉnh env): khởi động tách tiến trình qua WMI như dùng thật; script gọi chỉ thêm phần chuyển log ra file để lấy bằng chứng (`scratch/app-restore/run_default.cmd`).
- Kết quả: tiến trình bat 15:35:29 → `/_stcore/health` = **ok** lúc **15:35:42** (~13 s). Cây app mới: cmd `26572` → `streamlit.exe` `21324` → python `5624`; cmdline đúng tham số của bat (`--browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false`) — không ghim cổng/lane tay như app demo.
- **Env mặc định — bằng chứng:** bat không set `AIOS_AI_BACKEND`/`AIOS_FEATURE_WIRE_QA_CAGENT`; kiểm scope User + Machine cũng không có 2 biến này (chỉ có `AIOS_BGE_ONNX_MODEL_CHECKSUM` — không liên quan chọn lane).
- Worker BGE cũ (`pid 25148`) được app gắn lại (log worker: serve tiếp, không nạp lại) ⇒ app mở nhanh, worker ấm.

## 5. Smoke 1 câu qua UI

- Hội thoại **mới** `CONV-21A250C7` (nguồn `SRC-2441B1A3` bật; chỉ ghi store cục bộ `local_cases/workspace_chat/`, không commit).
- Câu hỏi: “ORICON STATUS là gì?” — bấm **Hỏi lúc 15:40:47,17** → **trả lời lúc 15:43:24,71** = **157,5 s** (1.022 ký tự, tiếng Việt, bám tài liệu).
- Store: user `MSG-6B545707` (15:40:49,96) → assistant `MSG-7A8CED42` (15:43:24,71).
- Trace `trc_46ddad06391c`: `status=valid`, `insufficient_evidence=false`, **`cited_count=2`**; nhãn `[1]`/`[3]` trỏ `ORICON_STATUS_早見表_検証済み版.pdf` (nguồn `SRC-2441B1A3`) ⇒ **có trích dẫn hợp lệ**.
- Lane trả lời: `provider_name=Gemini Web Stream`, `operational_mode=direct` — đúng đường mặc định của app trên máy công ty (KHÔNG phải lane C-Agent của demo) ⇒ xác nhận lại lần nữa: flag demo đã tắt.
- UI xác nhận trực tiếp (ảnh chụp): dòng chọn đường ghi **“Đang dùng: Gemini qua cầu nối (tự động)”**, khung nguồn “Đã chuẩn bị xong 1/1 tài liệu (100%)”, câu trả lời hiển thị đầy đủ trong khung chat. Ảnh: `scratch/app-restore/ui_smoke.png` (local_only, không commit).
- Ghi nhận thẳng: driver đo tự động (Playwright) **crash giữa chừng** sau khi đã bấm Hỏi (không kịp tự ghi kết quả); số đo lấy trực tiếp từ store + trace — app không bị ảnh hưởng, `/_stcore/health` = ok sau đó.

## 6. Trạng thái sau phiên

- App **env mặc định** đang chạy (port 8501, health ok) — đúng trạng thái “dùng thật hằng ngày”.
- Không sửa mã nguồn; không đụng index (kho tri thức vẫn là bản hợp `a7c7c232…` đã đặt ở vé RESTORE-INDEX-SPLIT; smoke chỉ đọc nguồn đã chuẩn bị sẵn).
- Mốc đầy đủ trong `docs/phieu-viec/mailbox-pc0575/trang-thai.md`: nhận vé (commit `807ca8b`), tắt + mở lại (commit `b766178`), smoke (commit kế tiếp).

## 7. Kết luận

- **ĐẠT** câu việc của vé: (1) tắt app demo — port 8501 sạch; (2) mở lại bằng đúng `RUN_AIOS_WORKSPACE_CHAT.bat` — env mặc định, không set tay flag/lane; (3) smoke 1 câu lạnh qua UI trả lời bình thường, **có 2 trích dẫn**, thời gian gửi→đáp 157,5 s đã ghi mốc; (4) `trang-thai.md` cập nhật đủ mốc + timestamp.
- Không có rủi ro tồn dư: không đổi code, không đổi dữ liệu bền ngoài store chat cục bộ.
