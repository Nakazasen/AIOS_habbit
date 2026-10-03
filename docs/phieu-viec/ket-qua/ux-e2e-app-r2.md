# Báo cáo vé `UX-E2E-APP-R2` — verify fix `58d1245` + chạy nốt E2E (c)–(h) trên app thật

- Ngày: 2026-10-03, khoảng 15:30–16:35 +07 (giờ máy). Máy: `h410asrock`, Windows 10 `10.0.18363`, Python `3.11.14` (`.venv` repo).
- Nhánh `phieu-viec/rag-fix1`. Nhận vé ở HEAD `f21542c` (đã chứa fix `58d1245`); **giữa lượt branch tiến thêm 3 commit VM** (`ad14a3e` phiên phỏng vấn trong chat, `d5d3250` tải về theo định dạng, `acb9382` báo cáo Phase A + xếp vé queue) → OMP rebase mailbox lên `acb9382`, **khởi động lại app trên cây mã mới nhất** và chạy lại các mục đã làm; kết quả dưới đây ứng với cây mã cuối của branch tại thời điểm nghiệm thu. Không merge `main`, không force-push; OMP chỉ kiểm thử, không sửa code sản phẩm.
- Index production (`local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`): trước và sau **giống hệt** — size `2.552.659.968`, mtime `2026-09-28 05:55`, SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`.

## 0. Cổng gate và cách chạy

- Gate: `58d1245` là tổ tiên của HEAD → điều kiện mở ĐÃ TỚI ngay lần kiểm đầu; không rơi nhánh 4-lần-watcher, không đặt `cho-muse` ở bước gate (mailbox `ba7b01e`).
- App thật cổng `8515` đúng các biến môi trường của `RUN_AIOS_WORKSPACE_CHAT.bat` (`AIOS_FEATURE_CHAT_ACTION=1`, `AIOS_RAG_V2_NUMPY_DENSE=1`, `AIOS_BGE_QUERY_TIMEOUT=1200`, `AIOS_BGE_INIT_TIMEOUT=300`, `AIOS_RAGV2_WORKER_PERSIST=1`, …); **không đụng app người dùng 8501** (vẫn listen suốt lượt kiểm).
- Điều khiển UI thật bằng Chrome headless cục bộ (profile riêng `C:/tmp/r2-chrome`), gõ tin nhắn thật + `Ctrl+Enter` đúng phím tắt app tự gắn. Sổ thử `E2EUxApp` (`NB-922E3730`).
- Phiên đóng mailbox (16:27 +07) chỉ đối chiếu bằng chứng trên đĩa (`C:/tmp/r2-e2e/`, SHA index, SHA kho log, cổng đang nghe), không chạy lại UI. Các mục bên dưới là của phiên kiểm thử 15:30–16:19.

## 1. Kết quả từng mục — (a) + 3 kiểm riêng + (c)–(h) đều PASS

| Mục | Kết quả | Bằng chứng (rút gọn) |
|---|---|---|
| (a) chạy lại sau fix | **PASS 3/3** | Câu trả lời gộp đủ 2 phần: "Cảnh báo ngưỡng" (hỏi lại tên thông số) + "Vẽ biểu đồ" (thông điệp hướng dẫn, không lỗi); `threshold_rules.json` vẫn KHÔNG tồn tại sau (a) |
| (a) kiểm riêng 1 — "vẽ biểu đồ bowskew JIG-01" | **PASS** | Vẫn ra đúng thông điệp hướng dẫn như vé trước |
| (a) kiểm riêng 2 — "đặt ngưỡng trên 12" | **PASS** | Hỏi lại tên thông số, không lưu quy tắc (file vẫn trống) |
| (a) kiểm riêng 3 — "đặt ngưỡng nhiệt độ 80" | **PASS** | Lưu đúng quy tắc `CB-8F4BE2` (thông số `nhiệt độ`, `> 80`) — đã xóa khi dọn |
| (c) lane AI tự chọn + ngắt cầu nối | **PASS** | Không còn selectbox đổi lane; ngắt cầu nối → lane tự rơi `C-Agent`, sidebar báo "Cầu nối chưa kết nối", app vẫn trả lời bình thường, không lỗi ảo; khôi phục → về lại Gemini |
| (d) thumbs down + lý do + file feedback | **PASS** | Bấm down → hiện ô lý do + nút gửi; `local_cases/answer_feedback.jsonl` có dòng mới — đã xóa khi dọn |
| (e) 1 điểm xấu đơn lẻ | **PASS** | Thẻ `(Cận biên)` + dòng "Xu hướng SMA(20): … một điểm xấu đơn lẻ chưa thành xu hướng … chưa cảnh báo"; không có thẻ đề xuất mail/không tự vẽ đính kèm (`canh_bao=False`) |
| (f) 3–4 dòng xấu liên tiếp | **PASS** | Thẻ `(Vi phạm)` + "Phán đoán nguyên nhân (giả thuyết)" + "Đề xuất điều tra" (đủ 5 mục); xác nhận cả khi dán lần lượt từng dòng |
| (g) biểu đồ SPC có SMA(20) | **PASS** | Biểu đồ xu hướng SVG có nhãn `SMA(20)` (màu tím `#7b1fa2`) + đường nét đứt `stroke-dasharray="10 6"`; ảnh PNG đã chụp |
| (h) cổng LSU mở/đóng đúng điều hướng | **PASS** | Theo UI mới (radio điều hướng đã bỏ ở `928e242`): mở cổng bằng chat, bấm "⬅️ Quay lại Sổ tài liệu" → cổng đóng, về đúng khung chat, không còn chữ "Điều hướng"/radio cũ |

## 2. Log nguyên văn

### 2.1 Mục (a) — câu gộp, chạy sạch trên mã cuối

- Người dùng: `vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12`
- App trả lời (nguyên văn, `MSG-A-5ABFF62D`):

  > **Cảnh báo ngưỡng**
  >
  > Bạn muốn đặt ngưỡng cho thông số nào? Tôi chưa hiểu rõ tên thông số trong câu của bạn — bạn gõ lại ví dụ: đặt ngưỡng nhiệt độ 80
  >
  > ---
  >
  > **Vẽ biểu đồ**
  >
  > Chưa có dữ liệu để vẽ biểu đồ. Vui lòng mở mục Kiểm tra dữ liệu LSU, tải tệp và chờ báo dữ liệu hợp lệ trước.

- `local_cases/threshold_rules.json`: không tồn tại sau câu này (không có quy tắc rác `trên`).

### 2.2 Ba câu kiểm riêng

1. `vẽ biểu đồ bowskew JIG-01` → `MSG-A-BE776BA7`: "Chưa có dữ liệu để vẽ biểu đồ. Vui lòng mở mục Kiểm tra dữ liệu LSU, tải tệp và chờ báo dữ liệu hợp lệ trước."
2. `đặt ngưỡng trên 12` → `MSG-A-2A94D43B`: "Bạn muốn đặt ngưỡng cho thông số nào? …"; file quy tắc vẫn trống.
3. `đặt ngưỡng nhiệt độ 80` → `MSG-A-C8FF69C3`: "Đã lưu quy tắc CB-8F4BE2: cảnh báo khi nhiệt độ vượt 80. Chưa có dữ liệu cho thông số 'nhiệt độ'." — file chứa đúng 1 quy tắc (`nhiệt độ`, `>`, `80.0`).

### 2.3 Mục (c) — lane tự chọn, ngắt cầu nối

- Trước khi ngắt: caption cạnh ô chat `Đang dùng: Gemini qua cầu nối (tự động)`; trong trang chỉ có combobox "Cuộc trò chuyện:" và "Mức độ tìm kiếm" — **không có selectbox chọn lane AI**.
- Ngắt: dừng tiến trình cầu nối Gemini (`python.exe` PID 3516, cổng `8585`). Sau khi nạp lại trang:
  - Sidebar: `⚪ Cầu nối chưa kết nối` (báo trung thực, không phải lỗi ảo).
  - Caption lane: `Đang dùng: C-Agent (tự động)` — hệ thống tự rơi sang lane kế tiếp (probe C-Agent có URL mặc định của máy).
  - Gửi `đặt ngưỡng trên 12` → vẫn trả lời bình thường ("Bạn muốn đặt ngưỡng cho thông số nào? …"); không có traceback/lỗi ảo trên trang.
- Khôi phục: `ensure_antigravity_bridge_running()` → health `direct_ready`; hội thoại mới về lại `Đang dùng: Gemini qua cầu nối (tự động)`, sidebar 🟢.

### 2.4 Mục (d) — thumbs down + lý do

- Bấm nút `thumb_down` dưới câu trả lời mới nhất → hiện ô "Câu trả lời chưa ổn ở điểm nào? (nhập lý do để tụi mình cải thiện)" + nút "Gửi đánh giá".
- Nhập lý do "E2E R2 test: câu trả lời chưa kiểm chứng nguồn dữ liệu" → "Đã ghi nhận. Cảm ơn bạn!"
- `local_cases/answer_feedback.jsonl` (dòng mới, nguyên văn):

  ```json
  {"conversation_id": "CONV-D2E56291", "message_id": "MSG-A-C8FF69C3", "rating": "chua_huu_ich", "reason": "E2E R2 test: câu trả lời chưa kiểm chứng nguồn dữ liệu", "created_at": "2026-10-03T15:53:29+07:00"}
  ```

  (File này trước lượt test không tồn tại — đã xóa khi dọn.)

### 2.5 Mục (e) — 1 điểm xấu đơn lẻ

Chuẩn bị fixture: gieo nền vào kho log (test, đã hoàn nguyên) — nền 40 điểm quanh 0.100–0.102 cho `JIG-E2E-R2/BOW:BLACK:0`, và nền 30 điểm 0.10 + ngưỡng thật `[0, 0.2]` cho `JIG-E2E-R3/SKEW:BLACK`.

- (e-A) Dán 1 dòng `2026-10-03T08:30:00,E2EUNIT,JIG-E2E-R2,BOW:BLACK:0,0.50,mm,OK` → `MSG-A-CE3506FC` (nguyên văn):

  > Kết luận: Cần kiểm tra — E2EUNIT — BOW:BLACK:0 (Cận biên)
  > Giá trị: 0.5 mm | JIG: JIG-E2E-R2
  > Xu hướng đang trôi gần ngưỡng (0.134/0.185), nên theo dõi thêm.
  > Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].
  > Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi
  > Xu hướng SMA(20): Mới có 2 điểm bất thường đơn lẻ trong 5 điểm gần nhất — một điểm xấu đơn lẻ chưa thành xu hướng, theo dõi thêm, chưa cảnh báo.
  > Đã nạp hết 1 giá trị theo 1 đợt (không cắt bỏ).

  `canh_bao=False` → không có thẻ đề xuất mail, không tự vẽ đính kèm cho điểm đơn lẻ.

- (e-B, biến thể có ngưỡng thật) Dán 1 dòng `…,JIG-E2E-R3,SKEW:BLACK,0.19,mm,OK` → `MSG-A-E1F02F60`:

  > Kết luận: Cần kiểm tra — E2EUNIT — SKEW:BLACK (Cận biên)
  > Giá trị: 0.19 mm | JIG: JIG-E2E-R3
  > Giá trị 0.19 đã dùng 90% dải dung sai [0, 0.2] của SKEW:BLACK, chạm mức theo dõi 80%.
  > Đối chiếu giới hạn thật khai báo trong tệp của JIG (nguoi_dung).
  > Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi
  > Xu hướng SMA(20): Mới có 2 điểm bất thường đơn lẻ trong 5 điểm gần nhất — …

### 2.6 Mục (f) — chuỗi 3–4 điểm xấu liên tiếp

- (f-A) Nền 40 điểm 0.10 + 3 điểm xấu `[0.50, 0.52, 0.51]` trong kho; dán thêm 1 dòng `…,JIG-E2E-R4,bowskew,0.53,mm,OK` → `MSG-A-BA0A80EC` (nguyên văn):

  > Kết luận: Nguy cơ — E2EUNIT — bowskew (Vi phạm)
  > Giá trị: 0.53 mm | JIG: JIG-E2E-R4
  > Có xu hướng bất thường: 5 điểm liên tiếp lệch xa SMA(20). Điểm mới nhất 0.530 so với SMA 0.100.
  > Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].
  > Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi
  > Xu hướng SMA(20): Có xu hướng bất thường: 5 điểm liên tiếp lệch xa SMA(20). …
  > Phán đoán nguyên nhân (giả thuyết): Dịch chuyển mức đột ngột rồi ổn định ở mức mới (0.100 → 0.518) — nghi đổi setup, thay đồ gá, đổi lô vật tư hoặc hiệu chuẩn lại.
  > Đề xuất điều tra:
  >   • Kiểm tra biên bản setup/đổi mã hàng tại thời điểm dịch chuyển.
  >   • Xác nhận lại hiệu chuẩn thiết bị đo.
  >   • Đối chiếu log bảo trì / thay đồ gá trong khoảng thời gian dịch chuyển.
  >   • So sánh với ca sản xuất trước và sau để loại trừ yếu tố lô vật tư.
  >   • Ghi lại kết quả điều tra vào bài học để lần sau nhận diện nhanh hơn.

- (f-B) Dán **lần lượt** 3 dòng xấu (`JIG-E2E-R6`, nền 40 điểm): dòng 1 → `(Cận biên)` "… một điểm xấu đơn lẻ …" (`MSG-A-BC261CF1`); dòng 2 → `(Vi phạm)` "3 điểm liên tiếp …" + phán đoán + đề xuất (`MSG-A-E5A62978`); dòng 3 → `(Vi phạm)` "4 điểm liên tiếp …" + phán đoán + đề xuất (`MSG-A-F0BACAC1`).
- Ghi nhận thêm (không chặn): dán 3 dòng **cùng một tin nhắn** bị khung "dữ liệu dán" nhận diện thành bảng → ra "Phân tích dữ liệu vừa dán" (`MSG-A-16DC4AE0`), không ra thẻ JIG. Muốn ra thẻ theo dõi xu hướng thì dán lần lượt hoặc để kho đã có nền — đề xuất Muse cân nhắc nhận diện khối log JIG nhiều dòng trong khung dữ liệu dán.

### 2.7 Mục (g) — biểu đồ SPC có SMA(20)

- Mở cổng LSU bằng chat `mở công cụ nâng cao` → tab "📋 Cổng kiểm tra dữ liệu"; nạp tệp test `IRIS_E2E_G.csv` (25 dòng, ma trận rộng 22 cột) → "Đã đọc 1 tệp (unit_test), lưu 425 giá trị đo vào kho log, bỏ 0 ô canh lỗi."
- Khối "3. Chọn biểu đồ xem trước": `Mã JIG = JIG-E2E-G`, `Chỉ số = SKEW:BLACK`, `Loại = Xu hướng theo thời gian`, `Loại ảnh = SVG` → bấm "📊 Xem biểu đồ".
- Kiểm trong DOM của SVG biểu đồ (nguyên văn cấu trúc):

  ```html
  <text x="934" y="60" fill="#7b1fa2">SMA(20)</text>
  <polyline stroke="#7b1fa2" stroke-dasharray="10 6" points="755.0,293.2 790.0,285.9 …" />
  ```

  → đúng "đường SMA(20) nét đứt tím có nhãn". Ảnh PNG cùng biểu đồ đã chụp (`g-spc-png.webp`).

### 2.8 Mục (h) — cổng LSU mở/đóng

- Theo UI mới, radio điều hướng 3 nhánh đã bị bỏ (commit `928e242`); sidebar **không còn** mục "Hỏi tài liệu"/"Cổng dữ liệu LSU" và trang không còn chữ "Điều hướng".
- Quy trình kiểm đúng UI mới: mở cổng bằng chat `mở công cụ nâng cao` (intent `CONG_CU_NANG_CAO`); bấm "⬅️ Quay lại Sổ tài liệu" → cổng đóng, quay về đúng khung chat (ô nhập hiện lại), không còn trạng thái radio cũ. Cổng tự đóng hoạt động đúng — khớp cách kiểm Case 1 ở `docs/phieu-viec/ket-qua/bao-loi-ao-da-sua.md`.

## 3. Ghi nhận thêm cho Muse (không chặn vé)

1. **Dòng "Gợi ý" tĩnh trong mọi thẻ log**: mọi thẻ (kể cả thẻ `(Đạt)`) đều có dòng `Gợi ý: Gửi email cảnh báo, Lưu vào chuỗi theo dõi` (`jig_alert_cards.build_instant_log_card`). Đây là gợi ý tĩnh, KHÔNG phải đề xuất gửi mail cho điểm đang xét — không có mã duyệt/không tự vẽ đính kèm khi `canh_bao=False`. Nếu muốn chữ trong vé khớp tuyệt đối ("KHÔNG đề xuất gửi email cảnh báo") thì nên ẩn gợi ý email khi không cảnh báo — đề xuất Muse xem có đáng sửa không.
2. **(f) dán 3 dòng cùng một tin nhắn** → khung "Phân tích dữ liệu vừa dán" (bảng + biểu đồ), không ra thẻ JIG (chi tiết ở 2.6).
3. **(h) chữ trong vé đã cũ** so với UI hiện tại (radio đã bỏ từ `928e242`); cách kiểm tương đương đã ghi ở 2.8.

## 4. Dọn dẹp / để lại máy

- `local_cases/jig_log_archive/2026-10.jsonl`: **hoàn nguyên từ backup** (SHA-256 `5268333ac341148e3c70529b0fcb997b2c8ea81e6e1054073c8f9d8278ed687e` khớp bản trước test); `bang_nhap_tep.json` không đổi (SHA `b2899c1d…`).
- Đã xóa 3 tệp test không tồn tại trước lượt này: `local_cases/threshold_rules.json`, `local_cases/answer_feedback.jsonl`, `local_cases/metric_limits.json`.
- Sổ thử `E2EUxApp` + các cuộc trò chuyện test còn trong `local_cases/workspace_chat` (như tiền lệ; người dùng xóa nếu không cần): `CONV-D2E56291`, `CONV-5B401C34`, `CONV-42393826`.
- App thử cổng `8515` đã tắt; Chrome test đã đóng; app người dùng `8501` nguyên vẹn; cầu nối `8585` đã khôi phục (`direct_ready`); `git status` sạch.
- Bằng chứng ngoài repo (`C:/tmp/r2-e2e/`): `conversation-replies.jsonl` (24 tin nhắn), `2026-10.jsonl.bak`, `bang_nhap_tep.json.bak`, `IRIS_E2E_G.csv`, script gieo/mô phỏng, 7 ảnh: `a-merged-reply.webp`, `c-lane-before-cut.webp`, `c-lane-fallback-cagent.webp`, `e-single-bad-point.webp`, `f-trend-alert.webp`, `g-spc-png.webp`, `g-spc-svg.webp`.

## 5. Đối chiếu tiêu chí ĐẠT của vé

- [x] Mục (a) chạy lại **PASS** đúng 3 điểm + 3 kiểm riêng đúng.
- [x] (c)–(h) **PASS**.
- [x] SHA index production không đổi; `git status` sạch; không ghi kho log JIG/`answer_feedback.jsonl` ngoài mục đích test (đã dọn).
- [x] Báo cáo này + `trang-thai.md` = `xong-cho-duyet`.

## 6. Thời gian chạy (giờ máy, gần đúng)

| Mốc | Thời gian |
|---|---|
| Nhận vé + mở app 8515 (bản đầu) | 15:30–15:36 |
| Mục (a) trên bản đầu | ~15:36 |
| Branch tiến 3 commit VM → rebase + khởi động lại app | 15:44–15:47 |
| (a) chạy lại + 3 kiểm riêng (bản cuối) | 15:48–15:52 |
| (d) | ~15:53 |
| (c) — ngắt cầu nối ~15:57, khôi phục ~16:00 | 15:55–16:02 |
| Gieo fixture + (e) + (f) | 16:03–16:14 |
| (g) | 16:12–16:16 |
| (h) | 16:16–16:18 |
| Dọn dẹp + báo cáo | 16:19–16:35 |
