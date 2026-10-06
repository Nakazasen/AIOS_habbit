# Vé LSU-QUALITY-RAG-HOME — Đo lane RAG 50 câu LSU trên máy nhà, CPU-only

- Vé: `LSU-QUALITY-RAG-HOME` (prompt `docs/phieu-viec/mailbox/prompt.md`).
- Máy: nhà `h410asrock`, user `Vinh`. Đo: 2026-10-07 ~01:26–01:30 +07.
- Trạng thái: **XONG 50/50, 0 lỗi kỹ thuật.** Không sửa code, không ghi index, không merge `main`.
- Báo cáo này THAY THẾ bản stub `DỪNG vì md5 lệch` (00:40) theo quyết định của Muse ~00:45:
  **đo tiếp trên index hiện hành của máy nhà, không đồng bộ md5** (nội dung logic khớp 100%,
  SHA-256 gốc khớp ghim, md5 lệch thuần do layout file sau khi PC0575 hợp 4 khối).

## 1. Kết quả tổng (rubric `chinh_xac` 2.0 + `trich_dan` 1.0, thang 0–3/câu)

| Chỉ số | Lane RAG máy nhà | Lane C-Agent PC0575 (đối chiếu) |
|---|---|---|
| Tổng /150 | **37,68** | 108,2 |
| GPA (/3) | **0,75** | 2,16 |
| Câu đạt ≥2 | **3/50 (6%)** | 35/50 (70%) |
| Câu =3 | **3/50 (6%)** | 33/50 (66%) |
| Lỗi kỹ thuật | **0/50** | 0/50 |

## 2. Tách theo staging khớp/không khớp (cùng định nghĩa với lane C-Agent)

Phân loại bằng đúng matcher staging hiện hành (`select_relevant_pairs`,
`MIN_MATCH_SCORE=3.0`, kho 3.392 cặp) — tái lập tại chỗ, khớp số lượng PC0575
(38 khớp / 12 không khớp):

| Nhóm | Số câu | Tổng | GPA | Đạt ≥2 | =3 |
|---|---|---|---|---|---|
| Staging khớp (38 câu) | 38 | 34,68 | **0,91** | 2 | 2 (Q1777, Q0680) |
| Staging không khớp (12 câu) | 12 | 3,00 | **0,25** | 1 | 1 (Q1827) |

- 12 câu không khớp: `Q0703, Q0851, Q1034, Q0685, Q0688, Q0632, Q0635, Q0693, Q0696, Q1827, Q0705, Q0684`.
- Đối chiếu C-Agent PC0575: khớp 38 câu GPA 2,78 (92,1% đạt) / không khớp 12 câu GPA 0,21 (0%).
  Lane RAG thấp hơn hẳn ở cả hai nhóm — nguyên nhân chính ở mục 6 (tổng hợp cloud
  không thành công câu nào, đáp án toàn là trích cục bộ hoặc từ chối trung thực).

## 3. Thời gian lane

- Preload: dense 121.331 chunk / 2,9 s + sparse 121.331 chunk / 12,3 s; khởi tạo pipeline 38,4 s.
- 50 câu: retrieval tổng **235,1 s** (TB 4,7 s/câu) + tổng hợp tổng **10,6 s** + tổng lane **245,8 s**
  (TB **4,92 s/câu**; nhanh nhất Q0696 3,50 s; chậm nhất Q0849 26,26 s — câu duy nhất
  provider chờ lâu 9,36 s trước khi rơi về fallback).
- Chi tiết từng câu (giây: tìm = retrieval, tổng hợp, câu = cả câu; `bc` = số mảnh bằng chứng):

| STT | ID | Điểm | Trích | Tìm | Tổng hợp | Câu | bc | Chế độ |
|---|---|---|---|---|---|---|---|---|
| 1 | Q0699 | 0,0 | không | 3,97 | 0,00 | 3,97 | 0 | provider_not_called |
| 2 | Q0700 | 0,0 | không | 3,81 | 0,00 | 3,81 | 0 | provider_not_called |
| 3 | Q0703 | 0,0 | không | 3,72 | 0,00 | 3,72 | 0 | provider_not_called |
| 4 | Q0708 | 0,0 | không | 4,49 | 0,00 | 4,49 | 0 | provider_not_called |
| 5 | Q0849 | 1,0 | có | 16,91 | 9,36 | 26,26 | 8 | provider_fallback |
| 6 | Q0850 | 1,0 | có | 4,86 | 0,34 | 5,20 | 8 | provider_fallback |
| 7 | Q0851 | 0,0 | không | 3,55 | 0,00 | 3,55 | 0 | provider_not_called |
| 8 | Q1029 | 0,0 | không | 4,33 | 0,00 | 4,33 | 0 | provider_not_called |
| 9 | Q1034 | 0,0 | không | 4,25 | 0,00 | 4,25 | 0 | provider_not_called |
| 10 | Q0620 | 0,0 | không | 4,53 | 0,00 | 4,53 | 0 | provider_not_called |
| 11 | Q0621 | 1,0 | có | 4,20 | 0,01 | 4,22 | 7 | provider_fallback |
| 12 | Q0824 | 0,0 | không | 4,16 | 0,00 | 4,16 | 0 | provider_not_called |
| 13 | Q0689 | 1,0 | có | 4,59 | 0,02 | 4,61 | 8 | provider_fallback |
| 14 | Q0704 | 1,0 | có | 4,89 | 0,02 | 4,92 | 4 | provider_fallback |
| 15 | Q0701 | 1,0 | có | 4,16 | 0,03 | 4,19 | 8 | provider_fallback |
| 16 | Q0718 | 1,0 | có | 5,20 | 0,03 | 5,24 | 8 | provider_fallback |
| 17 | Q0828 | 1,0 | có | 5,23 | 0,05 | 5,28 | 8 | provider_fallback |
| 18 | Q0858 | 1,0 | có | 4,83 | 0,01 | 4,86 | 8 | provider_fallback |
| 19 | Q0685 | 0,0 | không | 3,66 | 0,00 | 3,67 | 0 | provider_not_called |
| 20 | Q0688 | 0,0 | không | 3,56 | 0,00 | 3,56 | 0 | provider_not_called |
| 21 | Q0695 | 1,0 | có | 4,31 | 0,03 | 4,34 | 8 | provider_fallback |
| 22 | Q0632 | 0,0 | không | 4,59 | 0,00 | 4,59 | 8 | provider_not_called |
| 23 | Q0635 | 0,0 | không | 4,52 | 0,00 | 4,52 | 8 | provider_not_called |
| 24 | Q0636 | 1,67 | có | 4,25 | 0,02 | 4,28 | 8 | provider_fallback |
| 25 | Q1798 | 1,0 | có | 4,39 | 0,03 | 4,42 | 8 | provider_fallback |
| 26 | Q0671 | 1,0 | có | 4,62 | 0,02 | 4,64 | 8 | provider_fallback |
| 27 | Q0674 | 1,67 | có | 4,01 | 0,05 | 4,06 | 8 | provider_fallback |
| 28 | Q0677 | 1,0 | có | 5,06 | 0,05 | 5,11 | 8 | provider_fallback |
| 29 | Q0706 | 0,0 | không | 3,53 | 0,00 | 3,55 | 0 | provider_not_called |
| 30 | Q0707 | 1,0 | có | 4,03 | 0,03 | 4,06 | 8 | provider_fallback |
| 31 | Q0693 | 0,0 | không | 4,38 | 0,00 | 4,38 | 0 | provider_not_called |
| 32 | Q0696 | 0,0 | không | 3,50 | 0,00 | 3,50 | 0 | provider_not_called |
| 33 | Q0633 | 1,0 | có | 5,19 | 0,03 | 5,22 | 8 | provider_fallback |
| 34 | Q0787 | 1,0 | có | 5,67 | 0,03 | 5,70 | 8 | provider_fallback |
| 35 | Q1777 | 3,0 | có | 8,20 | 0,05 | 8,25 | 8 | provider_fallback |
| 36 | Q1827 | 3,0 | có | 8,39 | 0,12 | 8,53 | 16 | provider_fallback |
| 37 | Q2157 | 1,0 | có | 3,83 | 0,03 | 3,86 | 8 | provider_fallback |
| 38 | Q0662 | 1,0 | có | 4,20 | 0,03 | 4,25 | 7 | provider_fallback |
| 39 | Q0665 | 1,0 | có | 3,75 | 0,02 | 3,77 | 8 | provider_fallback |
| 40 | Q0668 | 1,0 | có | 3,70 | 0,05 | 3,75 | 8 | provider_fallback |
| 41 | Q0705 | 0,0 | không | 4,06 | 0,00 | 4,06 | 0 | provider_not_called |
| 42 | Q0709 | 0,0 | không | 4,56 | 0,00 | 4,56 | 8 | provider_not_called |
| 43 | Q0843 | 1,0 | có | 3,69 | 0,01 | 3,72 | 8 | provider_fallback |
| 44 | Q0864 | 0,0 | không | 4,19 | 0,00 | 4,19 | 8 | provider_not_called |
| 45 | Q0680 | 3,0 | có | 4,83 | 0,03 | 4,86 | 8 | provider_fallback |
| 46 | Q0684 | 0,0 | không | 4,33 | 0,00 | 4,33 | 0 | provider_not_called |
| 47 | Q0924 | 0,0 | không | 4,45 | 0,00 | 4,45 | 0 | provider_not_called |
| 48 | Q0630 | 1,0 | có | 3,99 | 0,02 | 4,02 | 8 | provider_fallback |
| 49 | Q0652 | 1,67 | có | 4,03 | 0,02 | 4,06 | 8 | provider_fallback |
| 50 | Q0658 | 1,67 | có | 3,94 | 0,02 | 3,95 | 8 | provider_fallback |

## 4. Bằng chứng CPU-only (khóa cứng theo ticket)

- `CUDA_VISIBLE_DEVICES=""`, `AIOS_RETRIEVAL_DEVICE=cpu` (ép từ đầu runner, log
  `pipeline: profile=bge_m3_hybrid device=cpu strict=True`).
- Backend nhúng ghim cứng `providers=["CPUExecutionProvider"]`
  (`src/aios_habit/rag_v2/bge_onnx_backend.py`, hàm `_open_session`) — session ONNX
  không có đường fallback sang GPU. `onnxruntime` trên máy có
  `['AzureExecutionProvider', 'CPUExecutionProvider']` (không có CUDA provider);
  session thực dùng là CPU.
- Adapter mặc định `retrieval_device="cpu"` (`workspace_chat_rag_v2_adapter.py:356,467`).
- Không có cảnh báo fallback device nào trong log đo.

## 5. Index chỉ-đọc + SHA (khóa cứng theo ticket)

- Đường đo: `C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`,
  pipeline mở `read_only=True`, assert tên file + assert đường resolve khớp.
- Trước đo: 2.942.201.856 byte, SHA-256 `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`
  (khớp ghim gốc), md5 `239009676829484049738866329de9f2`.
- Sau đo: SHA khớp trước 100%, md5 khớp, size không đổi → **không ghi index**
  (log: `index sau: ... sha_khop=True md5_khop=True (chi doc: True)`).
- Đếm chỉ-đọc: chunks 149.800 / embeddings 121.671 / FTS 121.331 / 889 document —
  khớp nội dung PC0575; md5 cấp file lệch thuần do layout SQLite sau khi PC0575 hợp
  4 khối (đã có quyết định Muse ~00:45 cho đo tiếp, không đồng bộ md5).

## 6. Phát hiện matcher (ghi nhận riêng, không sửa theo vé)

- Cả 50 câu đều có cặp hỏi–đáp y hệt trong kho staging (tra theo ID), nhưng matcher
  với ngưỡng `MIN_MATCH_SCORE=3.0` chỉ giữ lại 38 câu → **12 câu bị ngưỡng loại**
  (danh sách ở mục 2). Đây là cùng một phát hiện recall mà lane C-Agent PC0575 đã ghi.
- Trong 12 câu bị loại, lane RAG đáp đúng 1 câu =3 (`Q1827` — quy tắc giữ nguyên
  raw value `--`): bằng chứng retrieval toàn kho vẫn tìm được nội dung mà matcher
  staging bỏ sót.

## 7. Phát hiện tổng hợp (trung thực, ngoài dự kiến)

- Tổng hợp qua `RouterSynthesisProvider` (gemini `gemini-2.5-flash`, `max_attempts=1`,
  timeout 120 s). Cầu `127.0.0.1:8585` đã dựng lại `direct_ready` (gọi thử 2,7 s đạt)
  trước khi đo.
- Kết quả: **0/50 câu tổng hợp cloud thành công** — 21 câu gói bằng chứng rỗng
  (`provider_not_called`, đáp án `KHÔNG ĐỦ BẰNG CHỨNG` trung thực, 0 điểm);
  29 câu provider lỗi → rơi về trích cục bộ (`provider_fallback`, trong đó 3 câu
  =3 / 4 câu ≥2 nhờ mảnh retrieval chứa đúng số liệu).
- Hệ quả: số GPA 0,75 này đo **retrieval + trích cục bộ**, không phải retrieval +
  tổng hợp cloud như pilot PC0575 (Q0699: retrieval 198,4 s + tổng hợp 6,1 s, 2,0 điểm).
  So trực tiếp hai lane cần cùng điều kiện tổng hợp — đề nghị vòng sau đo lại khi
  cầu cloud ổn định, hoặc ghi rõ điều kiện này khi trích số.

## 8. Bộ câu + rubric + checkpoint (khóa cứng theo ticket)

- Bộ 50 câu JSON hóa từ `docs/phieu-viec/ket-qua/lsu-quality-set.md`
  (`C:/tmp/lsu-quality-rag-home/cau-hoi-50.json` — ngoài Git): 50/50 có keywords,
  50/50 yêu cầu trích dẫn.
- Quy tắc keywords (khả năng tái lập): lấy các cụm trong cột đáp án tham chiếu được
  bọc `` ` `` (số liệu/mã then chốt), bỏ cụm là tên file nguồn (đó là `trich_dan`);
  câu không có cụm bọc thì lấy cụm số liệu ngắn nhất; 14 câu thêm tay
  (`Q0703, Q0620, Q0621, Q0824, Q0718, Q0688, Q0632, Q0635, Q0636, Q0674, Q0633,
  Q0630, Q0652, Q0658` — xem `trich_50_cau.py`).
- Checkpoint từng câu (`rows.jsonl` ghi dồn, resume từ câu chưa đo; lần này chạy
  một mạch 0→50, không mất điện). Heartbeat mailbox: 00:12 nhận vé, 00:40 dừng,
  00:48/00:58 gate, 01:20 khảo sát, 01:45 bắt đầu đo, 01:50 gate, mốc này chốt.
- Dữ liệu thô ngoài Git: `C:/tmp/lsu-quality-rag-home/` (`rows.jsonl` 50 dòng,
  `ket-qua.json`, `tien-trinh.log`, `cau-hoi-50.json`, `rubric.json`,
  `do_rag_50.py`, `trich_50_cau.py`).

## 9. Rào cứng

- Không sửa code repo (runner + bộ câu nằm ngoài Git). Không ghi index (mục 5).
- Không merge `main` (mọi commit trên `phieu-viec/rag-fix1`).
- Dữ liệu đo là bản thảo (`lsu-quality-set.md` ghi `BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT`).
