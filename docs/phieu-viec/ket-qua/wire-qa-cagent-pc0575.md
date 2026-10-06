# Báo cáo vé WIRE-QA-CAGENT-PC0575 — Nối 3.392 cặp hỏi-đáp vào lane C-Agent của Workspace Chat

- **Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only), branch `phieu-viec/rag-fix1` (không merge `main`).
- **Ngày:** 2026-10-06. **Người thực hiện:** thợ OMP (mailbox `docs/phieu-viec/mailbox-pc0575/`).
- **Commit chính:** `4294ae0` (implement + test), `647fc36` (vá nhãn lặp + kết quả demo), commit chốt vé cuối cùng đi kèm báo cáo này.

## 1. Cổng mạng (làm TRƯỚC mọi việc khác)

- SSID lúc kiểm: **`vn-kdwireless`** — đúng mạng công ty vào được `kdtvn-ai.cmcts.vn`.
- Probe 1 câu (Q0001) qua **đúng hàm** `call_cagent_prediction` trong `src/aios_habit/cagent_api.py`:
  **ok, 34,14 s** (kỳ vọng 20–45 s) → không cần yêu cầu chuyển mạng, không phải dừng chờ xác nhận.

## 2. Quy tắc context đã chốt (4 ghi nhận review)

| # | Ghi nhận (mức thấp) | Cách chốt trong implement |
|---|---|---|
| 1 | JSONL chỉ có 2 trường `question`/`answer` (không có trường bối cảnh riêng) | Template context dùng đúng **2 mảnh** `Câu hỏi gốc` / `Trả lời gốc`; **KHÔNG bịa dòng "Bối cảnh"** — có test chặn (`assert "Bối cảnh:" not in …`) |
| 2 | Tổng số đúng là **3.392** (không phải 3.393) | Mọi tài liệu/báo cáo trong vé dùng 3.392; test demo không phụ thuộc con số này |
| 3 | Trích nguồn theo trường `source` trong JSONL | Prompt block + nhãn dẫn `mom/batch-01.md`, `dieuchinh/batch-88.md`… — có test chặn dẫn đường dẫn raw (`chatgpt-enrichment-raw`) |
| 4 | Kỳ vọng demo 1 ghi mức tối thiểu | Nghiệm thu dùng "F401 đứt + Q402/Q403 short 3 cực" (không nghiệm thu cứng đủ 4 linh kiện IC401/D304/D211) |

## 3. Mô tả implement (theo spec §1–§3)

### 3.1 Module mới `src/aios_habit/wire_qa_staging.py` (+255 dòng)

- Đọc `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (3.392 dòng, đã có sẵn trên máy) ở chế độ **CHỈ ĐỌC**; cache theo đường dẫn + mtime; ghi đè đường dẫn bằng `AIOS_WIRE_QA_MAPPING_PATH`; thiếu file → trả rỗng (không crash app).
- Chọn **top 1–3 cặp** liên quan (tất định, tie-break theo id):
  - mã lỗi / serial khớp **substring** (C0980, F401, 2ND-1004, 61C999999902…) — trọng số áp đảo;
  - từ khóa dài (bỏ stopword tiếng Việt) khớp token;
  - tín hiệu ý định: câu hỏi dạng "kiểm tra linh kiện / điểm đo" → ưu tiên cặp **liệt kê linh kiện** (F401/Q402/Q403/D304…); câu hỏi dạng "báo hiệu lỗi gì / định nghĩa" → ưu tiên cặp **định nghĩa mã** (`C0980 là …`).
- Render khối prompt đúng spec §1.2 (`--- DỮ LIỆU THAM KHẢO (BẢN THẢO) ---`, 2 mảnh, nguồn theo `source`), khối nhãn đúng spec §4.2:
  `> ⚠️ **Bản thảo — chưa qua chuyên gia duyệt**` + `> *Nguồn dữ liệu tham khảo: Khối <category> — Cặp Q&A #<id>*`.
- `strip_echoed_draft_label()`: cắt khối nhãn do **model tự "nhại"** ở đầu câu trả lời (xem 4.4).

### 3.2 `src/aios_habit/cagent_api.py` (104 dòng đổi)

- Endpoint **giữ nguyên** `DEFAULT_CAGENT_API_URL` — không thêm địa chỉ mới.
- Timeout **60 s** (giữ nguyên `DEFAULT_TIMEOUT_SECONDS`).
- Retry tối đa **1 lần**, backoff cố định **2,5 s**; CHỈ khi lỗi mạng tức thời (`URLError` không phải timeout) hoặc HTTP **5xx**. Không retry: HTTP 4xx, timeout, dữ liệu sai, và **khi người dùng đã hủy** (nhận `cancellation_event`).
- **5 thông báo lỗi tiếng Việt** đúng bảng spec §3.2: quá hạn 60 s / mất kết nối mạng nội bộ / server bận `(HTTP {code})` / dữ liệu rỗng / người dùng hủy. Không lộ traceback, đường dẫn `D:\...`, hay endpoint nội bộ.

### 3.3 `src/aios_habit/antigravity_bridge.py` (nhánh `cagent_api`, +17/-4)

- Ghép khối tham khảo staging + system note vào prompt gửi C-Agent; gắn **nhãn + nguồn cặp Q&A vào ĐẦU** câu trả lời; truyền `cancellation_event` xuống client.
- **Vá lỗi tiềm ẩn `UnboundLocalError`**: biến `candidate_sources` chưa được gán khi `packed_sources` rỗng (`raw_pool = packed_sources if packed_sources else candidate_sources`) — đường "hỏi không có nguồn" từng crash, chặn cả demo lẫn dùng thật.

### 3.4 Feature flag + rào cứng an toàn

- `AIOS_FEATURE_WIRE_QA_CAGENT` (đăng ký trong `feature_flags.py`), **mặc định TẮT** theo quy ước; demo chạy với flag bật.
- **Rào cứng:** 3.392 cặp chỉ ở staging/local — module chỉ đọc JSONL, **không ghi vector DB/BM25 index production**, không tạo/ghi đè case chính thức nào.

## 4. Demo 3 câu (chạy qua UI thật, lane C-Agent)

**Cấu hình demo:** app chạy nền tách tiến trình (WMI detached, pid 26880) với `AIOS_FEATURE_WIRE_QA_CAGENT=1` + ghim lane `AIOS_AI_BACKEND=cagent_api` (UI hiện "Đang dùng: **C-Agent (ghim tay)**"); hội thoại `CONV-82A143C1` (nguồn `SRC-2441B1A3` bật, đã ready); driver Playwright Edge headless bấm Hỏi từng câu, giãn cách 20 s.

| # | Câu hỏi | Thời gian UI (gửi→đáp) | Độ dài đáp án | Nhãn bản thảo | Trace (C-AGENT API) | Kỳ vọng tối thiểu |
|---|---|---|---|---|---|---|
| 1 | Mã lỗi C0980 báo hiệu gì + bước kiểm tra linh kiện | **358 s** | 1.607 ký tự | ✓ | `trc_e7fe827e64c5` | **ĐẠT** — `C0980 là 24V電源断検知` + F401 đứt + Q402/Q403 short 3 cực |
| 2 | ctrlMode = 0 và 1 khác nhau thế nào (Matecon) | **303 s** | 1.708 ký tự | ✓ | `trc_dec717658dd3` | **ĐẠT** — =0 chế độ tự động (kích hoạt truyền thông) / =1 thủ công (chặn) + SLMP |
| 3 | Jig 2ND-1004 Serial 61C999999902 — mấy lần, OK/NG từng màu | **211 s** | 1.566 ký tự | ✓ | `trc_21803e80233f` | **ĐẠT** — 4 lần; Total NG, Black/Magenta/Yellow NG, Cyan OK |

- **Cả 3 trace** có `provider_name = C-AGENT API`, `operational_mode = external_api` → đúng lane vé yêu cầu (không phải lane khác).
- Cặp staging được chèn: Q1 `[Q3401, Q2978, Q2980]`; Q2 `[Q0001, Q0267, Q0070]`; Q3 `[Q0825, Q1175, Q0833]`.
- **Đo trực tiếp lời gọi C-Agent** bằng đúng module + client mà lane dùng (`scratch/wire-cagent/measure_lane.py`): **43,6 s / 18,8 s / 23,3 s** — **đạt < 60 s** của spec §2 (ngưỡng HTTP client).
- **Ghi thẳng chênh lệch:** thời gian UI đầu-cuối 211–358 s **vượt mốc <60 s của spec §2.2** — phần lớn là **retrieval nội bộ chạy trước lượt C-Agent** (2 lượt search/câu + chờ worker sau restart; worker BGE init **353 s** trên index mới 149.800 chunk, các search ấm 0,2–5,2 s). Bản thân lời gọi C-Agent đạt 18,8–43,6 s; cắt thời gian retrieval thuộc phạm vi các vé tốc độ RAG (đã đo riêng ở vé khác).
- **Encoding:** câu 1 đi qua context chứa tiếng Nhật (`24V電源断検知`) + backtick (`đứt cầu chì F401`) — trả về nguyên vẹn; khóa thêm bằng test UTF-8/JSON round-trip.
- **Giãn cách** giữa các lần gọi: 20 s (chống 403 khi gọi dồn dập như cảnh báo review).
- **Lượt thử đầu đi nhầm lane Gemini Web** (hội thoại `CONV-8A782CA8`): bridge Gemini sống trên máy nên auto-lane chọn Gemini (trace `trc_e0d765367406`, `operational_mode=direct`) — không có nhãn/context, đúng phạm vi vé (chỉ lane C-Agent được nối). Bằng chứng giữ nguyên trong store; demo chính thức dùng hội thoại ghim C-Agent.
- **Phát hiện nhãn lặp (đã vá):** câu 2/3 model tự viết lại nhãn ở đầu câu trả lời (do thấy nhãn trong lịch sử hội thoại) → hiện 2 nhãn. Vá 2 lớp: (1) system note cấm model tự gắn nhãn; (2) `strip_echoed_draft_label` cắt khối nhại ở đầu. **Kiểm lại trực tiếp sau vá** (cùng hội thoại có lịch sử, câu 2 lặp lại): 262,6 s, 1.606 ký tự, **`label_count = 1`** (trace `trc_999867388941`) — hết lặp nhãn.

## 5. Kết quả cổng kỹ thuật

- `uv run --no-sync --group dev python -m compileall src tests` → **PASS**.
- Test liên quan (sau bản vá): **109 passed** —
  `test_wire_qa_staging.py` (mới), `test_wire_qa_cagent_lane.py` (mới), `test_cagent_api.py` (+8 ca retry/timeout/hủy/ngữ nghĩa), `test_antigravity_bridge.py`, `test_quality_harness.py`, `test_workspace_chat_cancellation.py`.
- `uv run --no-sync --group dev python -m aios_habit.cli audit` → **`Status: PASS`** (errors rỗng).
- `python -c "import aios_habit.workspace_chat_app"` → **OK**.
- Không merge `main`; mọi commit trên `phieu-viec/rag-fix1`. Heartbeat + checkpoint đăng vào `trang-thai.md` suốt phiên (13:52 → 14:14 → 14:24 → 14:46 → 15:22 → chốt).

## 6. Danh sách file thay đổi (đối chiếu `5a25827..647fc36`, +788/−22)

| File | Thay đổi |
|---|---|
| `src/aios_habit/wire_qa_staging.py` | **MỚI** (+255) — đọc staging, chọn cặp, render prompt + nhãn, cắt nhãn nhại |
| `src/aios_habit/cagent_api.py` | +104/−? — retry 1 lần/backoff 2,5 s, hủy giữa retry, 5 thông báo tiếng Việt |
| `src/aios_habit/antigravity_bridge.py` | +17/−4 — ghép context + nhãn vào lane cagent; vá `UnboundLocalError` |
| `src/aios_habit/feature_flags.py` | +12 — flag `wire_qa_cagent` (mặc định tắt) |
| `tests/test_wire_qa_staging.py` | **MỚI** (+131) — matcher trên dữ liệu thật 3 câu demo, ngưỡng, flag, encoding, nhãn |
| `tests/test_wire_qa_cagent_lane.py` | **MỚI** (+129) — ghép nối lane: prompt, nhãn, cờ tắt, chống nhãn lặp |
| `tests/test_cagent_api.py` | +158 — 8 ca retry 5xx/mạng, không retry 4xx, timeout, hủy, payload rỗng |
| `tests/test_antigravity_bridge.py` | +4/−4 — stub nhận kwarg `cancellation_event` mới |

## 7. Ghi chú & rủi ro tồn dư

1. **Feature flag mặc định TẮT** — muốn dùng thật cần bật `AIOS_FEATURE_WIRE_QA_CAGENT=1`; ngoài ra auto-lane hiện ưu tiên Gemini Web khi bridge sống, muốn chốt C-Agent cho mọi câu cần ghim `AIOS_AI_BACKEND=cagent_api` (hoặc Muse/user quyết đổi chính sách auto-lane — **ngoài phạm vi vé này**).
2. **Hủy giữa lượt gọi** chỉ chặn *retry* (đúng spec §2.2 "không retry khi user hủy"); đang gọi sync thì vẫn chờ call kết thúc (cơ chế hiện tại của app, không đổi trong vé này).
3. **Nhãn nhại của model** đã chặn 2 lớp; nếu model đặt nhãn ở *giữa* câu (không phải đầu) thì hiếm khi còn sót — chấp nhận.
4. **App demo đang chạy nền** pid 26880 (WMI detached) với env demo: `AIOS_FEATURE_WIRE_QA_CAGENT=1`, `AIOS_AI_BACKEND=cagent_api`, worker BGE sống tới 6 h idle. Muốn về mặc định: tắt pid này rồi mở lại bằng `RUN_AIOS_WORKSPACE_CHAT.bat`.
5. Lượt demo đầu (Gemini) + câu 1 của hội thoại cũ `CONV-8A782CA8` giữ làm bằng chứng quá trình, không xóa — đây là dữ liệu `local_only` trên máy, không commit.

## 8. Nguồn tham chiếu

- Spec: `docs/phieu-viec/ket-qua/wire-cagent-spec.md`; review: `docs/phieu-viec/ket-qua/review-wire-cagent-spec.md`.
- Dữ liệu staging: `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (3.392 dòng; không sửa).
- Kết quả thô: `scratch/wire-cagent/demo_results.json` (3 câu UI), `scratch/wire-cagent/lane_timing.json` (đo trực tiếp), `scratch/wire-cagent/verify_result.json` (kiểm bản vá nhãn).
