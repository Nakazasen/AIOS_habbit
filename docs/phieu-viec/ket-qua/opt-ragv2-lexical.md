# Báo cáo vé OPT-RAGV2-LEXICAL — OMP verify trên PC0575 (CPU-only, index production)

- Trạng thái: **verify xong, chờ Muse duyệt** (`xong-cho-duyet`). Kết luận: **ĐẠT các tiêu chí nghiệm thu đo được** (chi tiết mục 7); mốc stretch **<60s/câu CHƯA đạt** (báo rõ, không tô hồng).
- Ngày: 2026-10-02 (10:11–11:04 +07). Người làm: OMP trên `KDTVN-PC0575`. Nhánh: `phieu-viec/rag-fix1`, mã đo = đỉnh `47299a0` (chứa Phase A `4a796ac`, B1 `be4845c6`, B2 `1f30092`; không sửa thêm mã nguồn khi verify).
- Ràng buộc giữ nguyên: **chỉ verify, không sửa mã**; index production mở **read-only**; không ghi index, không merge `main`, không force-push. Index production nguyên vẹn trước/sau: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` — `2.842.415.104 B`, mtime `2026-10-01 15:46:42` (không đổi suốt phiên). App LAN `localhost:8501/_stcore/health` = `ok` trước/sau.

## 0. Cổng gate (vòng khép kín)

- Watcher công ty (`D:\Sandbox\agent-mailbox\`, `AUTO_LAUNCH`) tự mở OMP `LAUNCH 1/4` lúc **09:43:07** cho vé này (`launchStallCount=1`).
- **Điều kiện mở ĐÃ TỚI** ngay khi nhận: mã Muse đã nằm trong nhánh + verdict PYLOOPS ĐẠT → OMP nhận vé (`ab3afbb`, 09:45) → **không dùng nhánh "4 lần watcher"/`cho-muse`, không no-op**.

## 1. Phương pháp đo

- Probe in-process chỉ-đọc: `scratch/opt_ragv2_lexical_phase_a_probe.py` (Phase A) + `scratch/opt_ragv2_lexical_verify_probe.py` (6 câu) — dựng `RagV2DevPipeline` trên **đúng index production**, 19/33 nguồn `ready` của hội thoại `CONV-9C730D76` / sổ `NB-E35A7BEE`, preload dense+sparse tại init như worker thật, chạy 6 câu L1–L3/E1–E3 qua `RagV2DevPipeline.query` (không gọi LLM: `synthesis_provider=None`).
- **Mốc so sánh (baseline)**: `scratch/opt_ragv2_verify_new.json` — vòng 2 cache ấm của vé PYLOOPS (đúng định nghĩa baseline trong vé).
- Hai lượt đo:
  - `v2off` = `AIOS_RAGV2_LEXICAL_V2=0` (mặc định; chỉ có Phase A + B1).
  - `v2on` = `AIOS_RAGV2_LEXICAL_V2=1` (B2 bật, mọi sub-toggle mặc định; `CJK_PREFILTER=1` như baseline).
- Điều kiện máy: probe chạy tuần tự, không chạy song song; page cache biến động giữa các lượt (xem mục 8) — mọi so sánh đọc kèm cột từng kênh.

## 2. Phase A — probe an toàn TEMP vs `data_version` (PC0575, SQLite 3.50.4)

| Kiểm | Kết quả | Bằng chứng |
|---|---|---|
| Ghi bảng TEMP xảy ra thật | **PASS** | câu non-CJK: `total_changes` +200 dòng |
| `data_version` main không nhảy khi ghi TEMP | **PASS** | `1 → 1` (connection worker) và `1 → 1` (connection quan sát thứ hai) |
| Token cache `(data_version, write_seq)` không đổi | **PASS** | `(1, 0) → (1, 0)` |
| Đối chứng âm (probe không "PASS giả") | **PASS** | connection khác ghi bảng main → `data_version 1 → 2` |
| `write_seq` không bị TEMP chạm | **PASS** | giữ `0` sau các lượt TEMP |

⇒ Giả định an toàn ghi trong comment code (`4a796ac`) **đúng trên máy này**: ghi TEMP không làm token đổi; write thật cùng connection vẫn bắt qua `write_seq` (test đơn vị phủ).

## 3. Phase A — mốc cache trong 6 câu thật (bỏ nạp lại ma trận giữa query)

Token `(1, 0)` giữ nguyên sau **cả 6 câu** ở cả hai lượt; dense/sparse không nạp lại giữa query:

| Câu | baseline dense/sparse | `v2off` dense/sparse | `v2on` dense/sparse |
|---|---:|---:|---:|
| L1 | 100,4 / 99,7s | 10,1 / 0,4s | 6,5 / 0,5s |
| L2 | 112,3 / 110,9s | 1,5 / 0,5s | 1,0 / 0,4s |
| L3 | 103,3 / 113,8s | 1,6 / 0,5s | 1,5 / 0,3s |
| E1 | 0,5 / 0,3s | 0,8 / 0,5s | 0,6 / 0,4s |
| E2 | 116,5 / 157,4s | 1,4 / 0,5s | 1,1 / 0,4s |
| E3 | 103,9 / 62,4s | 1,7 / 0,4s | 2,1 / 0,6s |

- L1 `v2off` 10,1s là chi phí lượt đầu sau preload (khởi động numpy/ma trận con), các câu sau ~1–2s — vẫn **dưới xa mốc 100–260s** mà baseline phải chịu ngay trong câu hỏi.
- Tổng câu (giây): L1 266,2→93,6→**61,7**; L2 301,3→144,2→**131,4**; L3 296,8→146,0→**134,8**; E1 454,6→225,3→**129,6**; E2 405,0→61,5→**55,4**; E3 302,9→129,3→145,7 (xem mục 8 về nhiễu).

## 4. Phase B — parity top-15 (tiêu chí 2)

So từng vị trí với baseline `opt_ragv2_verify_new.json` (script `scratch/opt_ragv2_lexical_compare.py`):

| Câu | `v2off` vs baseline | `v2on` vs baseline |
|---|---|---|
| L1–L3, E2, E3 | **trùng 100% từng vị trí** | **trùng 100% từng vị trí** |
| **E1 (CJK)** | **15/15 trùng khít thứ tự** | **15/15 trùng khít thứ tự** |

⇒ **PASS 6/6 câu ở cả hai chế độ, E1 đủ 15/15 đúng thứ tự baseline** — không có ca nào phải cân nhắc nhánh "hạ kill-switch vì E1 lệch" (tiêu chí 4).

## 5. Phase B — tách chặng lexical (B1) và tác dụng B2

B1 lần đầu tách được số thật trên production (giây):

| Câu | `v2off`: eligibility / fts_match / khác | `v2on`: eligibility / fts_match / khác |
|---|---|---|
| L1 | 57,3 / 19,4 / temp 0,02 + score 0,06 | 31,5 / 19,4 / temp 0,02 + score 0,07 |
| L2 | 89,4 / 46,8 / score 0,07 | 75,4 / 50,4 / score 0,09 |
| L3 | 92,5 / 45,6 / score 0,08 | 76,0 / 52,0 / score 0,09 |
| E1 | 26,9 / like 28,5 / score 0,49 (951 dòng) | 3,1 / like 6,9 / score 0,50 |
| E2 | 6,2 / 49,3 / score 0,09 | 3,0 / 47,2 / score 0,11 |
| E3 | 78,1 / 44,9 / score 0,08 | 90,1 / 49,1 / score 0,11 |

- **Bảng tạm không phải nút thắt**: xây 2.878 dòng chỉ **17–36ms** (giả định "DELETE + INSERT ~120k dòng" trong bối cảnh vé không đúng với cấu hình 19 nguồn — eligibility rộng 2.878/120.452 dòng). Nút thắt thật: **quét eligibility 120.452 dòng** (I/O) + **`chunks_fts MATCH` bm25 19–52s**.
- B2 giúp rõ nhất ở **CJK (E1)**: lexical tóm tắt 56,3→10,6s (like prefilter 28,5→6,9s; eligibility 26,9→3,1s) — nhờ đường `_candidate_rows_v2` đọc id hẹp. L1 −32s, L2 −13s, L3 −11s, E2 −6s. E3 +16s nằm trong dải nhiễu I/O (mục 8).
- `python_score_ms` chỉ 0,06–0,50s ⇒ vòng Python không phải nút thắt; `score_candidate_calls` 100 (non-CJK) / 951 (E1).

## 6. Test + cổng nền

- `compileall src tests` EXIT=0; `check_docs.py` = `DOCUMENTATION_CONTRACT=PASS`; `python -m aios_habit.cli audit` = `"status": "PASS"`; `import aios_habit.workspace_chat_app` OK (Python 3.11.15).
- Test đích: `tests/test_rag_v2_lexical_phase_a.py` + `tests/test_rag_v2_lexical_phase_b.py` + `tests/test_rag_v2_index.py` = **71 passed** (21,1s).
- **Full suite** (`uv run --no-sync --group dev pytest -q`, toàn bộ): **3.641 passed, 37 skipped, 19 failed, 19 error** (10:44).
  - 19 error: thiếu file dữ liệu VM (`/home/hatch/workspace/aios_data/...`) — thuần môi trường, không chạm mã.
  - 19 failed: đối chứng trên **cây nền (HEAD trừ đúng mã LEXICAL)** chạy lại đúng 19 test đó: **19 failed, cùng thông báo, cùng nguyên nhân** (model checksum chưa duyệt, mạng/DNS, LLM server không chạy, rapidocr thiếu, UI copy lệch, privacy-config cục bộ) ⇒ **không regression mới vì vé này**.
  - Ghi chú môi trường: `.venv` thiếu 3 gói tuỳ chọn khiến bộ test không collect được — đã cài **chỉ vào venv** (không đụng repo): `xlrd`, `python-docx`, `python-pptx` (+`xlsxwriter`).

## 7. Kết luận theo tiêu chí nghiệm thu

1. **Phase A — ĐẠT**: test mới đỗ (5/5 trong 71 passed); câu ấm không còn `load_ms` 100+s ở dense/sparse (mục 3); probe an toàn PASS trên PC0575 (mục 2).
2. **Phase B — ĐẠT parity + có giảm đo được**: top-15 khớp baseline **100% cả 6 câu ở cả `v2off` và `v2on`** (E1 đủ 15/15, đúng thứ tự); lexical giảm có số đo (B1, mục 5). **Stretch <60s/câu CHƯA đạt** — chỉ E2 55,4s; L1 61,7s; còn lại 129–146s do quét eligibility + FTS MATCH I/O-bound (trần đĩa ~4,8MB/s đã đo ở vé PYLOOPS).
3. **Full suite — ĐẠT "không regression mới"**: đối chứng nền khớp 19/19 ca fail, 19 error thuần môi trường (mục 6).
4. **E1 (Nhật/Hàn) — ĐẠT**: top-15 khớp baseline đúng thứ tự ở cả hai chế độ ⇒ không phải hạ kill-switch vì lý do E1.

## 8. Rủi ro, hạn chế, đề xuất (ngoài phạm vi đã đo)

- **Nhiễu I/O của máy**: preload cùng khối lượng đo được 262,6s+225,7s (`v2off`) vs 152,6s+159,5s (`v2on`) — biên độ ±40%; các mục eligibility/fts vì thế cũng dao động ±10–20s (E3 "+16s" nằm trong dải này). Kết luận chính (parity + giảm tổng) không phụ thuộc phần nhiễu.
- **E1 có 2 lượt search** do `should_retry_thin_results` (lượt 1 mỏng) — summary B1 chỉ giữ kênh của lượt cuối; tổng thời gian E1 phản ánh cả 2 lượt (như ghi chú vé PYLOOPS mục 8.2).
- **`chunks_fts MATCH` / `CJK_TRIGRAM` chưa đo trên production**: đường `CJK_TRIGRAM` cần bảng `chunks_fts_trigram` **ghi vào index production** — theo QUY-UOC phải dry-run + backup + user duyệt rõ ràng; phiên này không ghi index nên chỉ dựa vào test đơn vị (parity + fallback im lặng khi thiếu bảng). Đề xuất vé riêng nếu Muse muốn đo thật.
- **Đề xuất kill-switch**: số đo ủng hộ **bật `AIOS_RAGV2_LEXICAL_V2=1`** (parity 100%, tổng 6 câu giảm ~142s, E1 giảm mạnh). Lưu ý chéo từ bench máy nhà (vé J3): `SCORE_CACHE` trên index nhà làm CJK chậm hơn ~1,0–1,4s; phiên này chưa A/B riêng từng sub-toggle trên production — Muse cân nhắc khi chốt default. Quyết định default thuộc Muse/user (feature flag, mặc định hiện tại vẫn tắt).
- **Hạn chế đo**: probe in-process không chạy LLM nên không in nhãn citation thật; bằng chứng "citation/trace không thoái lui" dựa trên **tập chunk_id + thứ tự + candidates trùng khít baseline** (nhãn citation sinh từ metadata của chính chunk đó); điểm RRF từng vị trí được test đơn vị `test_rag_v2_lexical_phase_b.py` khẳng định trùng trên dữ liệu tổng hợp.

## 9. Bằng chứng

- Báo cáo này + commit `trang-thai.md` (`xong-cho-duyet`).
- Scratch (git-ignore): `opt_ragv2_lexical_phase_a_probe.py`, `opt_ragv2_lexical_verify_probe.py`, `opt_ragv2_lexical_compare.py`, `opt_ragv2_lexical_v2off.json`, `opt_ragv2_lexical_v2on.json`, `full_suite_lexical.log`, `lexical_failed_nodes.txt`, `run_baseline_subset.sh`.
- Baseline dùng để so: `scratch/opt_ragv2_verify_new.json` (vé PYLOOPS, vòng 2).
- Cây nền đối chứng full suite: HEAD trừ `src/aios_habit/rag_v2/index.py` + `tests/test_rag_v2_index.py` + 2 file test LEXICAL (hoàn tác từ `543c4c5`; đã khôi phục nguyên trạng, `git status` sạch ngoài `uv.lock` sửa sẵn từ trước).
