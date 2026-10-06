# Vé WIRE-QA-CAGENT-PC0575 — Nối 3.392 cặp hỏi-đáp vào lane C-Agent của Workspace Chat

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** sau `RESTORE-INDEX-SPLIT-PC0575` (index chính 889 doc / 149.800 chunk đã vào vị trí).
**Role gợi ý:** DEFAULT (tích hợp lane + kiểm thử đầu-cuối).

## Bối cảnh

- 3.392 cặp hỏi-đáp (MOM 608 / LSU 1.790 / điều-tra-lỗi 994) đã review chéo: ID duy nhất, 0 rỗng, 6 trường đúng tên (vé REVIEW-WIRE-QA-MAPPING, verdict Muse ĐẠT 2026-10-05).
- Spec kỹ thuật nối C-Agent đã có: `docs/phieu-viec/ket-qua/wire-cagent-spec.md` (agy lập 05/10; opencode review 05/10: **OK để nối**, 4 ghi nhận mức thấp — đọc kỹ trước khi implement, chốt trong vé này).
- Endpoint C-Agent **SỐNG trên mạng công ty** (vé CAGENT-HEALTH-RETRY-PC0575, verdict Muse ĐẠT 06/10 ~13:33: 3/3 câu Q0001/Q0609/Q2409 thành công, **20,0–44,7 s/câu**, timeout 150 s/câu). **KT_CHETAO KHÔNG vào được `kdtvn-ai.cmcts.vn`** (vé CAGENT-HEALTH chạy sai mạng — kết luận CHẾT vô giá trị; user đính chính 06/10 ~12:56: KT_CHETAO chỉ tải Drive).

## Cổng mạng (bắt buộc — làm TRƯỚC mọi việc khác)

1. Kiểm tra SSID hiện tại (`netsh wlan show interfaces`): phải là mạng công ty vào được `kdtvn-ai.cmcts.vn` (hiện tại: `vn-kdwireless`).
2. Probe 1 câu qua đúng hàm `call_cagent_prediction` trong `src/aios_habit/cagent_api.py` (tái dùng Q0001 đã đo — kỳ vọng ~20–45 s).
3. Nếu probe rớt (timeout/DNS/403): ghi vào `trang-thai.md` dòng `ghi_chu` **"YÊU CẦU CHUYỂN MẠNG vn-kdwireless: vé WIRE cần gọi endpoint kdtvn-ai.cmcts.vn (KT_CHETAO không vào được)"** rồi **DỪNG CHỜ** xác nhận của điều phối viên (Muse) trong cùng file, kiểm tra lại mỗi 3 phút — **không implement tiếp trước xác nhận** (đúng pattern rào mạng vé RESTORE-INDEX-SPLIT).

## Việc cần làm

1. Đọc spec `wire-cagent-spec.md` + báo cáo review `review-wire-cagent-spec.md`, chốt 4 ghi nhận thấp trong implement:
   - #1: JSONL chỉ có 2 trường `question`/`answer` (không có trường bối cảnh riêng) → **quy tắc chốt: template context dùng đúng 2 mảnh `{câu hỏi gốc}` / `{trả lời gốc}`, KHÔNG bịa trường "Bối cảnh"**.
   - #2: tổng số đúng là **3.392** (không phải 3.393) — mọi tài liệu/báo cáo trong vé dùng số này.
   - #3: trích dẫn `source` theo trường `source` trong JSONL (đường dẫn fixed), không dẫn đường dẫn raw.
   - #4: kỳ vọng demo 1 (C0980) ghi mức **tối thiểu "F401 đứt + Q402/Q403 short 3 cực"** — không nghiệm thu cứng cả 4 linh kiện (tránh trượt oan).
2. Nguồn dữ liệu staging: file `wire-qa-mapping.jsonl` (3.392 dòng, 6 trường `id/question/answer/source/category/batch`). Kiểm tra tồn tại trên máy công ty; nếu chưa có: tải từ Drive ngăn `digest/` trong thư mục `index-split-r5-backup` (ID + SHA trong báo cáo `upload-digest-drive-home.md`) bằng đúng pattern đã chứng minh (`drive.usercontent.google.com/download`, đối chiếu SHA-256, **không bịa ID**).
3. Implement lane C-Agent trong Workspace Chat theo spec §1–§3:
   - Endpoint giữ nguyên `DEFAULT_CAGENT_API_URL` trong `cagent_api.py` — **không thêm địa chỉ mới**.
   - Payload `{"question": "<system_prompt>\n\n<user_prompt>"}` theo template spec §1.2 (đã chốt 2 mảnh ở bước 1).
   - Timeout 60 s; retry tối đa **1 lần** (chỉ khi mất kết nối đột ngột hoặc HTTP 5xx); backoff 2–3 s; **không retry** với HTTP 4xx hoặc khi user hủy.
   - Thông báo lỗi **100% tiếng Việt** theo bảng spec §3.2 — **cấm traceback thô, cấm lộ đường dẫn `D:\...` hay endpoint nội bộ**.
4. Nhãn bản thảo (rào cứng spec §4): mọi câu trả lời dùng context 3.392 cặp phải hiển thị `⚠️ Bản thảo — chưa qua chuyên gia duyệt` + nguồn cặp Q&A (đầu bong bóng tin nhắn hoặc footer).
5. Rào cứng an toàn: 3.392 cặp **CHỈ ở staging/local** — cấm nạp vào vector DB production / BM25 index chính của AIOS; cấm tự tạo/ghi đè case chính thức khi chưa có phê duyệt thủ công của kỹ sư.
6. Encoding: test 1 câu chứa tiếng Nhật + backtick (vd Q3401) để khóa encoding UTF-8/JSON ngay từ đầu (ghi nhận review).
7. Rate limit: giãn cách giữa các lần gọi, **không gọi dồn dập** (từng bị 403 ngày 02/10 khi chạy hàng loạt).
8. Quy ước chuẩn 06/10: heartbeat mốc bước tối thiểu **15 phút/lần** + checkpoint/resume bắt buộc (vé dài).
9. Code tương thích Python 3.11. Không merge `main`. Mọi commit trên `phieu-viec/rag-fix1`.

## Nghiệm thu (3 câu demo theo spec §5 — chạy qua lane đã nối)

| # | Câu hỏi | Nguồn | Kỳ vọng tối thiểu |
|---|---|---|---|
| 1 | Mã lỗi C0980 báo hiệu gì + bước kiểm tra linh kiện | Q3401/Q3317 (điều-tra-lỗi) | định nghĩa `24V電源断検知` + F401 đứt + Q402/Q403 short 3 cực |
| 2 | `ctrlMode = 0` và `1` khác nhau thế nào (Matecon) | Q0001 (MOM) | =0 chế độ tự động / =1 thủ công + giao thức SLMP |
| 3 | Jig 2ND-1004 Serial 61C999999902: xuất hiện mấy lần, OK/NG từng màu | Q0825 (LSU) | xuất hiện **4 lần**; Total NG; Black/Magenta/Yellow NG, Cyan OK |

- Mỗi câu: **<60 s**, có nhãn bản thảo, ghi thời gian + độ dài đáp án vào báo cáo.
- Cổng kỹ thuật: `compileall src tests` PASS; test liên quan (`test_cagent_api.py` + `test_quality_harness.py`) PASS; `cli audit` PASS; `import workspace_chat_app` OK.
- Phạm vi vé này là **tích hợp lane + demo 3 câu** (không phải gọi hết 3.392 câu qua endpoint trong vé này).

## Báo cáo

`docs/phieu-viec/ket-qua/wire-qa-cagent-pc0575.md` — đủ: kết quả cổng mạng + probe; quy tắc context đã chốt (4 ghi nhận); mô tả implement (file/hàm đổi); bảng 3 câu demo (thời gian, độ dài đáp án, đạt kỳ vọng tối thiểu hay không); kết quả cổng kỹ thuật; danh sách file thay đổi.
