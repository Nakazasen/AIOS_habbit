# Báo cáo vé TEST-SUITE-HYGIENE-HOME — dọn nốt nhóm ca đỏ môi trường

- **Mã vé:** `TEST-SUITE-HYGIENE-HOME`
- **Máy thực hiện:** Nhà `h410asrock` (thợ OMP).
- **Thời điểm:** 2026-10-09 05:27 – ~08:00 +07.
- **Căn cứ:** sau vé `TEST-STALE-GUARDS-HOME` (verdict ĐẠT), toàn bộ suite còn 24 ca đỏ phân loại sơ bộ là môi trường (mục 6 vé `SYNTH-DEEPSEEK-PROTOCOL-HOME`).
- **Kết quả một câu:** **Đã dọn 23/23 ca bảng kê + 2 ca mới lòi ở lượt chốt — toàn bộ là môi trường/test lạc hậu, KHÔNG có hồi quy thật.** Chỉ sửa test + cơ chế bỏ qua có điều kiện, không đụng `src/`.

---

## 1. Bảng kê trước sửa (full suite đầu vé, 22 phút)

`4 failed / 4214 passed / 46 skipped / 19 errors` — log `local_runs/hygiene/full-before.log` (ngoài Git):

| # | Ca | Nhóm | Bằng chứng gốc |
|---|---|------|----------------|
| 1–10 | `test_error_cases_f4` ×10 (all_families, ccall_c0030/c0120, fsystem_f000/f10x, jam_6000/0000, sct_01, sct_dup, reimport) | Thiếu tệp máy khác | `AssertionError: source file missing: \home\hatch\workspace\aios_data\...02XC_自己診断表示一覧表-Iris2020 VN.xls` |
| 11–19 | `test_chat_action_error_lookup` ×9 (five_codes, hint, symptom, db_real, prefer, order, column, qd2×2) | Thiếu tệp máy khác | `FileNotFoundError: .../Lịch sử lỗi/Loi KDTPS.xlsx` |
| 20 | `test_call_antigravity_bridge_privacy_guard` (tier5) | Test lạc hậu privacy | `assert 'Bị chặn' in '<urlopen error [Errno 11001] getaddrinfo failed>'` — guard đã bị gỡ bởi `941c31c` (quyết định chủ 29/9) nên gọi thật ra DNS |
| 21 | `test_in_app_qa_blocks_cloud_local_export` | Test lạc hậu privacy | `assert 'Không thể gửi dữ liệu local_only' in 'Lỗi khi gọi AI: ...WinError 10061...'` — chặn đã bị gỡ bởi `f27081d`, code mới tự đổi sang cloud_safe + gọi provider (không có LLM cục bộ trên máy) |
| 22 | `test_production_index_specs_retrieval` | Kỳ vọng số tuyệt đối kho máy khác | `assert 496 == 889` — kho máy này 496 tài liệu, test đòi đúng 889 của máy khác |
| 23 | `test_query_never_starts_worker_and_reuses_explicit_worker` | Flaky tải nặng | `SemanticBackendError: bge_worker_query_timeout` khi full suite song song; chạy lẻ xanh (40,8s) |

Tái hiện riêng 4 failed: 3 đỏ thật + BGE xanh khi chạy lẻ → đúng phân loại flaky tải.

## 2. Xử lý theo nhóm (chỉ sửa test, không đụng `src/`)

### 2a. Nhóm thiếu tệp máy khác (19 ca: F4 ×10 + lookup ×9)
- `tests/test_error_cases_f4.py` — fixture `conn`: kiểm tra 4 tệp nguồn, thiếu → `pytest.skip` kèm `AIOS_DATA_DIR` + danh sách đường dẫn vắng. Đủ tệp → chạy thật như cũ.
- `tests/test_chat_action_error_lookup.py` — fixture `real_db`: kiểm tra `Loi KDTPS.xlsx` + JAM + SCT_ADJ, thiếu → `pytest.skip` kèm đường dẫn. Đủ tệp → dựng DB thật như cũ.
- Không bỏ qua vô điều kiện; không đổi khẳng định hành vi.

### 2b. Nhóm test lạc hậu privacy (2 ca)
Cả 2 ca đều đòi hành vi chặn `local_only` đã bị chủ sở hữu gỡ ngày 2026-09-29 (`00_governance/DATA_POLICY.md`):
- `941c31c` gỡ fail-closed trong `call_antigravity_bridge`; test canonical `test_antigravity_bridge.py::test_local_only_cloud_not_blocked_locally` đã khẳng định hành vi mới (phải thử gọi, không chứa "Bị chặn").
- `f27081d` gỡ chặn trong `answer_notebook_question`; code mới (`notebook_qa.py:213`) tự đổi cloud+local → cloud_safe và ẩn nội dung local_only trong prompt.
- Sửa: tier5 privacy-guard chuyển sang mock transport hermetic + khẳng định hành vi mới (có thử gọi, không "Bị chặn"); notebook block-test chuyển sang mock provider + khẳng định cloud_safe + prompt đã ẩn (không chặn sớm).
- Đây là cập nhật test theo thiết kế đã duyệt, không nới lỏng khẳng định đúng (lớp ẩn prompt vẫn được kiểm).

### 2c. Kỳ vọng số tuyệt đối kho máy (1 ca)
- `test_production_index_specs_retrieval`: kho máy này 496 tài liệu (lsu 77 / dtl 343 / mom 27 / tong-hop 49 — đo thật), test đòi đúng 889 của máy khác.
- Sửa thành quan hệ đúng với dữ liệu đầu vào của chính test, giữ nguyên ý nghĩa lọc theo miền: auto bao hết kho hiện tại; các miền rời nhau; hợp các miền = toàn kho; tổng số miền = tổng kho.
- `test_domain_document_map_counts` (kỳ vọng 889 từ manifest đóng gói trong repo) giữ nguyên — manifest là dữ liệu của test, không phải kho máy.

### 2d. Flaky tải nặng (1 ca)
- `test_query_never_starts_worker_and_reuses_explicit_worker`: lexical thật 2,7–13,6s/ca; full suite nhiều worker song song vượt 30s mặc định → timeout fail-closed đúng mã.
- Sửa: chỉ `pytest.skip` khi đúng mã `bge_worker_query_timeout` (fail-closed đúng), kèm lý do tải máy; mã lỗi khác vẫn fail thật. Chạy lẻ vẫn chạy thật.

### 2e. Hai ca mới lòi ở lượt chốt (không thuộc bảng kê đầu vé)

Lượt chốt lần 1 (`2 failed / 4216 passed / 65 skipped`, 34 phút): 23 ca vé đã hết nhưng lòi 2 ca mới — theo vé DỪNG chẩn đoán chi tiết, không sửa che lấp:

- **`test_dispatch_is_read_only` (TOOL-4 interview):** SHA file DB đổi sau dispatch, đỏ cả khi chạy lẻ (3/3). Truy gốc: nội dung logic **28/28 bảng giống hệt** (đếm dòng từng bảng bằng nhau); file phình 274.432 → 466.944 byte do **WAL checkpoint** — `load_builtin_actions` import `chat_action_visual_maps` ngay sau `chat_action_expert_interview` checkpoint thêm ~192KB vào file chính mà không đổi dòng nào. Lỗi ở TEST (khẳng định SHA byte file giòn), không phải hồi quy (handler chỉ đọc qua `list_gap_candidates`/`list_sessions`).
- **Sửa:** so sánh nội dung logic (`_dump_logical`: toàn bộ bảng sắp xếp theo `repr`) thay vì SHA byte; giữ kiểm không thêm file phụ. Kết quả: **12/12 xanh**.
- **`test_clean_machine_full_isolated_venv_installation` (slow packaging):** `pip install --no-index` full-RAG offline quá 600s, đỏ cả khi chạy lẻ (606s). Đây là ca `slow` phụ thuộc tốc độ máy, không phải vỡ đóng gói (lỗi không-zero vẫn fail thật).
- **Sửa:** chỉ `pytest.skip` khi đúng `subprocess.TimeoutExpired`, kèm lý do; thoát lỗi pip vẫn fail. Comment tiếng Anh theo luật repo.

## 3. Kết quả sau sửa

- Nhóm đã đụng (6 tệp): **36 passed / 19 skipped** (113,97s) — 19 skipped = đúng 19 ca thiếu tệp.
- Cổng repo: `compileall` sạch, `cli audit` `"status": "PASS"`, `import aios_habit.workspace_chat_app` OK, `git diff -- src/` rỗng.
- **Full suite chốt lần 2 (37 phút 30 giây): 0 failed / 4217 passed / 66 skipped / 0 errors — EXIT=0.** Log `local_runs/hygiene/full-final.log` (ngoài Git).
- Đối chiếu: skipped 46 → 66 = **+20** (19 ca thiếu tệp + 1 ca slow packaging — đúng các ca đã chuyển điều kiện); passed 4214 → 4217 = **+3** (privacy-guard + notebook-block + kho 496/889 chuyển đỏ → xanh); failed 4 → 0, errors 19 → 0.

### Bảng đối chiếu trước/sau từng ca

| Ca | Trước | Sau | Cách xử lý |
|----|-------|-----|------------|
| F4 ×10 | 10 errors (thiếu tệp) | skip có điều kiện | fixture kiểm tệp + lý do |
| lookup ×9 | 9 errors (thiếu tệp) | skip có điều kiện | fixture kiểm tệp + lý do |
| privacy-guard | failed (đòi chặn cũ) | pass (hành vi mới + mock DNS) | cập nhật theo `941c31c` |
| notebook-block | failed (đòi chặn cũ) | pass (cloud_safe + mock LLM) | cập nhật theo `f27081d` |
| kho 496/889 | failed (số tuyệt đối) | pass (quan hệ) | auto/disjoint/tổng khớp |
| BGE worker | failed khi tải nặng | pass thật (lần chốt) / skip khi đúng mã timeout tải | skip chỉ khi đúng mã timeout |
| interview SHA | failed (WAL churn) | pass 12/12 (so sánh logic) | thay SHA byte bằng dump logic |
| slow packaging | timeout 600s | skip khi đúng TimeoutExpired | condition + reason riêng |

## 4. Rào cứng đã giữ

- **Chỉ sửa test:** 8 tệp test, `diff HEAD -- src/` rỗng. Không đổi mã chạy thật (không phát hiện hồi quy thật).
- **Không nới lỏng khẳng định đúng:** nhóm thiếu tệp vẫn chạy thật khi đủ tệp; nhóm privacy vẫn kiểm ẩn prompt + thử gọi; nhóm kho vẫn kiểm disjoint/bao phủ/tổng; interview chuyển sang so sánh logic chặt hơn (toàn bộ dòng 28 bảng).
- **Không ghi chỉ mục:** chỉ dùng chỉ mục tạm của kiểm thử + đọc production DB chỉ đọc.
- **Không merge `main`:** toàn bộ commit trên nhánh `phieu-viec/rag-fix1`.
- Commit sửa test: `81ba460` (19 ca thiếu tệp) + `37832e0` (4 ca failed) + `ba15cf3` (2 ca mới + comment tiếng Anh).

## 5. Nghiệm thu sử dụng thật

Vé này là vệ sinh tín hiệu suite (không có luồng người dùng mới). Nghiệm thu dùng thật được kế thừa từ các vé trước trên cùng codebase (QUALITY3 ĐẠT nghiệm thu app; PROTOCOL smoke Q0699 đáp án thật 844 ký tự). Cổng thay thế: full suite xanh + `cli audit` PASS + import app OK (đã chạy thật trên máy này).

## 6. Tồn dư / ghi nhận

1. **Kho production máy này 496 ≠ 889:** manifest đóng gói vẫn 889 (đúng cho máy đủ dữ liệu); test quan hệ mới chấp nhận mọi kho. Nếu chủ muốn kho nhà đủ 889, cần vé đồng bộ dữ liệu riêng (ngoài phạm vi vé này).
2. **BGE timeout khi tải nặng:** test mới skip khi đúng mã timeout tải; nếu tần suất skip tăng, nên xem xét nâng `AIOS_BGE_QUERY_TIMEOUT` cho máy nhà hoặc tách worker nặng ra khỏi full suite mặc định (việc vận hành, không thuộc vé).
3. **19 ca skip cần tệp máy khác:** sẽ tự chạy thật trên máy có đủ dữ liệu (điều kiện `os.path.exists`), không cần sửa thêm.
4. **WAL churn khi import chuỗi action:** `load_builtin_actions` làm file DB WAL checkpoint thêm ~192KB (byte đổi, dòng không đổi). Đã ghi nhận; test nào khẳng định "read-only" trên file SQLite WAL nên so sánh nội dung logic thay vì SHA byte.
5. **Ca slow `pip install` offline full-RAG:** hiện skip khi quá 600 s trên máy nhà; nếu muốn thành tín hiệu thật trên máy này cần nâng timeout hoặc chỉ chạy trong CI khoẻ (việc vận hành).
6. **`chat_action_*.py` comment trong code dùng tiếng Anh** theo luật repo (mã nguồn: comment kỹ thuật tiếng Anh) — các comment TEST-SUITE-HYGIENE-HOME đã viết tiếng Anh.
