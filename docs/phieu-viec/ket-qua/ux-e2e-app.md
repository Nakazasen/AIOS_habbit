# Báo cáo vé UX-E2E-APP — kiểm thử đầu-cuối app thật (máy nhà)

- Ngày: 2026-10-03, khoảng 14:59–15:30 +07.
- Máy: `h410asrock`. Python `3.11.14` (`.venv` của repo).
- Nhánh: `phieu-viec/rag-fix1` (HEAD `2aabcd3` khi nhận vé; không merge `main`, không force-push).
- Mã kiểm: `846713e` `07913b1` `82698a5` `928e242` — đều là tổ tiên của HEAD; OMP chỉ kiểm thử, không sửa code sản phẩm.

## 0. Cổng gate

- Watcher tự mở OMP lần 1/4 lúc 14:58:02 (`launchStallCount=1`). Điều kiện mở ĐÃ TỚI: vé lane [NHÀ], mã UX đã nằm trên nhánh.
- OMP nhận vé `dang-lam` (`232b1aa`), không đặt `cho-muse` ở bước gate.

## 1. Cách chạy app thật

- Mở bản mã hiện tại ở cổng riêng `http://127.0.0.1:8515`, dùng **đúng các biến môi trường của**
  `RUN_AIOS_WORKSPACE_CHAT.bat` (kể cả `AIOS_FEATURE_CHAT_ACTION=1`, `AIOS_RAG_V2_NUMPY_DENSE=1`,
  `AIOS_BGE_QUERY_TIMEOUT=1200`, `AIOS_BGE_INIT_TIMEOUT=300`, `AIOS_RAGV2_WORKER_PERSIST=1`).
- App của người dùng ở cổng `8501` (chạy từ trước) **không bị đụng**, không dùng để nghiệm thu.
- Điều khiển UI thật bằng Chrome headless (CDP cục bộ, profile riêng `C:/tmp/e2e-chrome`):
  gõ tin nhắn thật vào ô chat + `Ctrl+Enter` — đúng phím tắt app tự gắn
  (`workspace_chat_app.py` dòng ~4004–4024).
- Sổ thử `E2EUxApp` (`NB-922E3730`), cuộc trò chuyện `CONV-43CC60EF`.

## 2. Index production

- `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
- Trước: size `2552659968`, mtime `2026-09-28 05:55:03`,
  SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`.
- Sau: **giống hệt cả size/mtime/SHA**. Không ghi index.

## 3. Kết quả từng mục

| Mục | Kết quả | Ghi chú |
|---|---|---|
| a. Câu gộp 2–3 ý định | **FAIL** | Chỉ chạy phần ngưỡng, tách sai thông số, không vẽ biểu đồ — log dưới |
| b. Dán CSV/log thật → phân tích + biểu đồ | **PASS** | Đủ tóm tắt + bảng thống kê + biểu đồ PNG trong câu trả lời |
| c. Lane AI tự chọn / ngắt cầu nối | KHÔNG CHẠY | Luật vé: có mục FAIL → dừng vé |
| d. Thumbs up/down + lý do + file feedback | KHÔNG CHẠY | |
| e. 1 điểm xấu đơn lẻ → thẻ Cận biên, không email | KHÔNG CHẠY | |
| f. 3–4 dòng xấu liên tiếp → Vi phạm + phán đoán + đề xuất | KHÔNG CHẠY | |
| g. Biểu đồ SPC có đường SMA(20) | KHÔNG CHẠY | |
| h. Sidebar cổng LSU + radio | KHÔNG CHẠY | |

### 3.1 Mục (a) — FAIL, log nguyên văn (chạy sạch 1 lần gửi)

- Người dùng: `vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12`
- App trả lời (nguyên văn):

  > Đã lưu quy tắc CB-D0EDE6: cảnh báo khi trên vượt 12. Chưa có dữ liệu cho thông số 'trên'.

- Không có biểu đồ; không có phần bowskew/JIG-01; tên thông số bị tách thành `trên` (rác).
- Định tuyến trên chính máy (cùng mã nguồn): `classify_all_intents(...)` → `[('canh_bao_nguong', {})]`
  — phần "vẽ biểu đồ" không phải ý định của router chat nên bị bỏ khi câu chứa ý định khác.

### 3.2 Mục (b) — PASS, dán CSV log thật

- Dán nguyên tệp log (bản copy cục bộ ngoài repo `C:\tmp\lsu1-deploy\...`, tệp 616 byte,
  không đưa nội dung vào git) → app tự nhận khối `du_lieu_dan`.
- Câu trả lời: `Phân tích dữ liệu vừa dán` + tóm tắt số dòng/cột + bảng thống kê mô tả +
  **biểu đồ PNG 800×420 nhúng data-URI** + preview 10 dòng. Chú thích
  "Biểu đồ từ dữ liệu bạn vừa dán (không phải mô phỏng)".
- Máy không có `matplotlib` → ảnh vẫn hiện (đường Pillow của UX-CHAT-CORE-FIX1).
- Ảnh nghiệm thu: `C:\tmp\e2e-ux\b-csv-analysis.png` (ngoài repo; không commit vì chứa số liệu log thật).

## 4. Kiểm tra phụ để khoanh vùng lỗi (a)

Hai phép kiểm nhỏ, cùng app thật, để Muse sửa đúng chỗ:

1. `vẽ biểu đồ bowskew JIG-01` **một mình** → trả lời hướng dẫn đúng tiếng Việt:
   "Chưa có dữ liệu để vẽ biểu đồ. Vui lòng mở mục Kiểm tra dữ liệu LSU, tải tệp và chờ báo dữ liệu
   hợp lệ trước." → đường vẽ biểu đồ JIG còn sống, không lỗi ảo; nhưng chỉ đọc dữ liệu từ phiên
   LSU gate (`wsc_last_lsu_traces`), không đọc kho log archive.
2. Cặp đã hỗ trợ (dán CSV số + `đặt ngưỡng` đúng tên cột) → **MỘT** câu trả lời gộp đủ 2 phần:
   "Phân tích dữ liệu vừa dán" (bảng + biểu đồ) và "Cảnh báo ngưỡng" (lưu `CB-476B96` đúng thông số
   `nhiet_do_gia_lap`). → Máy gộp nhiều ý vẫn chạy; lỗi (a) nằm ở hai chỗ: (i) router không có ý định
   "vẽ biểu đồ" nên phần này bị bỏ khi câu có ý định khác; (ii) bộ tách ngưỡng nhận "trên" làm tên
   thông số khi câu thiếu tên thông số hợp lệ.

Ghi nhận thêm khi chạy (a)/(b): cạnh ô chat có dòng `Đang dùng: Gemini qua cầu nối (tự động)`,
không có selectbox đổi lane tay trên composer — bằng chứng một phần cho mục (c), chưa phải nghiệm thu
đầy đủ (chưa ngắt cầu nối).

## 5. Kết luận

- **CHƯA ĐẠT**: mục (a) FAIL (log ở 3.1). Theo luật vé, OMP dừng vé và báo `cho-muse`; 6 mục còn lại
  chưa chạy, sẽ chạy trong vé/vòng kế tiếp sau khi Muse sửa.
- Đề xuất cho Muse (phạm vi sửa gợi ý, không tự code):
  1. Thêm ý định "vẽ biểu đồ" vào `chat_intent_router` (hoặc để luồng gộp chạy nhánh chart JIG độc lập)
     để câu gộp chart + ngưỡng ra đủ cả hai phần.
  2. Câu ngưỡng thiếu tên thông số hợp lệ ("đặt ngưỡng trên 12") phải **hỏi lại**, không lưu quy tắc
     với tên rác như `trên`.
  3. Nguồn dữ liệu cho chart JIG hiện chỉ từ phiên LSU gate; nếu muốn vẽ từ kho log archive thì cần nối
     thêm (kèm thông điệp hướng dẫn hiện có vẫn đúng khi chưa có dữ liệu).

## 6. Dọn dẹp / để lại máy

- `local_cases/threshold_rules.json` chỉ chứa 2 quy tắc test (`CB-D0EDE6`, `CB-476B96`) → đã xóa.
- Sổ thử `E2EUxApp` + cuộc trò chuyện `CONV-43CC60EF` còn trong `local_cases/workspace_chat` (như tiền lệ;
  người dùng xóa nếu không cần).
- Không ghi kho log JIG, không ghi `answer_feedback.jsonl`, không ghi index, không đụng `main`.
- App thử cổng `8515` + Chrome headless đã tắt; app người dùng `8501` vẫn nguyên; `git status` sạch.
- Mục (g)/(e)/(f) chưa chạy nên chưa có ảnh chụp tương ứng.

---
Thời gian tham chiếu: nhận vé 14:59; app mở 15:03; mục (b) ~15:16; mục (a) chạy sạch ~15:24; kết thúc ~15:30.
