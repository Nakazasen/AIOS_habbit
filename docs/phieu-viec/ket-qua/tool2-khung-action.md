# Vé `TOOL-2` — Khung `chat_action` + tool mẫu nối `daily_next_actions`: báo cáo nghiệm thu

- Trạng thái: **xong — chờ Muse duyệt** (code + test, không ghi index).
- Máy: `h410asrock` — Windows (`win32`, 10.0.18363); Python `3.11.14` (venv repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `e62da78` (nhận vé 03:34) → `c50c39b` (mốc 1: chốt thiết kế) → `e017e73` (code + test) → `2cc61a7` (mốc 2) → báo cáo này. Không merge `main`, không force-push.
- Phạm vi ghi: mã nguồn + test trong repo, 2 tài liệu canonical (`ARCHITECTURE.md`, `PROJECT_HANDOVER.md`), báo cáo này và `docs/phieu-viec/mailbox/trang-thai.md` (đúng quy ước vé). **Không ghi index, không embed, không đụng dữ liệu/index production.**

## 1. Việc đã làm (đúng 4 bước của vé)

1. **Thiết kế khung `chat_action`** — registry + matcher + render giàu (mục 2).
2. **Code khung + 1 tool mẫu** — `src/aios_habit/chat_action.py` (khung), `src/aios_habit/chat_action_next_actions.py` (tool mẫu), hook trong `workspace_chat_app.py`, cờ mới trong `feature_flags.py` (mục 3).
3. **Test** — `tests/test_chat_action.py` (17 bài) + smoke trên app thật (mục 5).
4. **Không thêm nút** — không thêm ô nhập, nút bấm hay màn hình nào; điểm vào duy nhất vẫn là khung chat (đúng luật UI “một khung chat duy nhất, không tạo thêm ô nhập liệu hay nút bấm riêng biệt” ở `specs/008-evidence-case-loop/spec.md` và `specs/015-csv-chart-selector/`).

## 2. Thiết kế khung (bám mẫu `jig_chat_wire` sẵn có)

- **Đăng ký action**: tool gọi `register_action(ChatAction(name, title, hints, handler))` một lần; import xong là action có mặt (registry kiểu dict, thứ tự đăng ký = thứ tự ưu tiên khớp).
- **Khớp theo ngữ cảnh câu hỏi**: `normalize_text()` bỏ dấu tiếng Việt + không phân biệt hoa thường + gộp khoảng trắng; hint viết có dấu hay không dấu đều khớp câu người dùng gõ (`"Tiếp theo nên làm gì?"` và `"tiep theo nen lam gi"` đều khớp).
- **Dữ liệu vào**: `ChatActionRequest` (câu hỏi, locale, mã hội thoại, mã sổ, `workspace_id`, `context` tự do) — chat truyền ngữ cảnh đang mở (sổ, hội thoại) cho tool.
- **Kết quả giàu**: `ChatActionOutcome` gồm các khối `ChatActionBlock`: `markdown` (chữ), `table` (bảng GFM, tự escape `|`/xuống dòng), `chart` (PNG nhúng **data-URI** để ảnh nằm luôn trong bong bóng trả lời và tồn tại theo tin nhắn; có trần `CHART_MAX_BYTES = 400.000` byte, quá trần thì chỉ còn chú thích tiếng Việt thay vì nhúng).
- **Fail-closed**: `dispatch()` bọc cả bước nạp module action lẫn handler trong một ranh giới lỗi → lỗi bất kỳ thì trả `None` để chat chạy tiếp luồng trả lời thường, không lộ traceback; không bao giờ chặn câu hỏi không khớp hint.
- **Cờ tính năng mới**: `AIOS_FEATURE_CHAT_ACTION` (mặc định **TẮT**; bật bằng biến môi trường `AIOS_FEATURE_CHAT_ACTION=1` hoặc override trong test). Hook trong `workspace_chat_app.py` đặt **sau** luồng log JIG (`jig_chat_wire`) và **trước** luồng agent/RAG; chỉ chạy khi cờ bật và người dùng chưa đính kèm ảnh.
- **Nạp action builtin**: `load_builtin_actions()` import các module trong `BUILTIN_ACTION_MODULES` rồi gọi `register()` tường minh (an toàn khi module đã nằm trong `sys.modules` sau `reset_actions`) — TOOL-3/TOOL-4/TOOL-5 chỉ cần thêm module của mình vào danh sách này là xong phần “chui vào chat”.

## 3. Tool mẫu đã chọn

- Tool: `daily_next_actions.suggest_next_actions` — **47 dòng**, đơn giản nhất trong danh sách gợi ý của báo cáo TOOL-1 (`rag_evaluator` 57, `claim_guard` 81, `mom_benchmark` 339). Không chọn nhóm benchmark (để dành TOOL-3) và không đụng nhóm visual (TOOL-5).
- Action đăng ký: `goi_y_viec_tiep_theo` — “Gợi ý việc nên làm tiếp”; hint: `gợi ý việc nên làm`, `việc nên làm tiếp`, `nên làm gì tiếp`, `bước tiếp theo nên làm gì`, `tiếp theo nên làm gì`, `làm gì tiếp theo`.
- Kết quả trả về: một dòng dẫn + **bảng** `# | Việc nên làm tiếp` (mỗi việc một dòng) + chú thích tên sổ (lấy từ ngữ cảnh chat truyền vào, `context["notebook_title"]`).
- Trường hợp chưa mở sổ hoặc tool lỗi: trả về câu tiếng Việt hướng dẫn/thông báo, không lộ lỗi kỹ thuật.

## 4. Tệp đã đổi

| Tệp | Thay đổi |
|---|---|
| `src/aios_habit/chat_action.py` | Mới — khung chat_action (registry, matcher bỏ dấu, block markdown/bảng/biểu đồ, dispatch fail-closed, entry `handle_chat_text`, cờ `chat_action_enabled`) |
| `src/aios_habit/chat_action_next_actions.py` | Mới — tool mẫu đăng ký action “Gợi ý việc nên làm tiếp” nối `daily_next_actions` |
| `src/aios_habit/workspace_chat_app.py` | +30 dòng hook sau `jig_chat_wire`, lưu 2 tin nhắn qua store hiện có, không thêm widget |
| `src/aios_habit/feature_flags.py` | Thêm cờ `chat_action` (state, `to_dict`, `is_enabled`, `_canonical_name`, `snapshot`) |
| `tests/test_chat_action.py` | Mới — 17 bài (khớp/không khớp, dispatch lỗi, render bảng/biểu đồ, tool mẫu, cờ mặc định tắt) |
| `ARCHITECTURE.md` | +1 mục “Khung `chat_action` cho Workspace Chat (TOOL-2)” |
| `PROJECT_HANDOVER.md` | +1 mục “Bổ sung ngày 2026-09-30 — Phiếu TOOL-2” |

## 5. Bằng chứng đã chạy

**a) Test khung + tool mẫu (cô lập store bằng `tmp_path`, không đụng dữ liệu thật):**
`uv run --no-sync --group dev python -m pytest -q tests/test_chat_action.py` → **17 passed**:
- chuẩn hóa bỏ dấu/hoa-thường; đăng ký + khớp hint (có dấu và không dấu);
- dispatch truyền đủ ngữ cảnh; handler lỗi → `None` (rơi về luồng thường); module builtin lỗi import → `None`;
- validate block (kind lạ, bảng thiếu header, action thiếu hint);
- render bảng GFM (escape `\|`, xuống dòng trong ô) + biểu đồ data-URI + trần ảnh quá lớn;
- tool mẫu: khớp câu hỏi, ra bảng đúng nội dung; chưa có sổ → câu hướng dẫn; `handle_chat_text` lưu đúng 2 tin nhắn và trả `True`, câu không khớp → `False` và không lưu gì;
- cờ mặc định TẮT (kể cả khi không có biến môi trường), override bật/tắt đúng, snapshot có cờ mới.

**b) Kiểm chứng render biểu đồ data-URI trong Streamlit thật** (phần khung, không cần tool có ảnh):
script tạm `scratch/check_chart_datauri.py` (gitignore) dựng `ChatActionOutcome` có khối `chart` + bảng, chạy `streamlit run` thật; ảnh chụp `local_runs/tool2_smoke/chart_datauri_render.png` (không commit): ảnh PNG nhúng data-URI hiển thị đúng trong markdown của Streamlit, bảng GFM render thành bảng.

**c) Smoke app thật (Streamlit + `AIOS_FEATURE_CHAT_ACTION=1`), sổ `mom_opcenter`:**
- Gõ đúng câu khớp hint trong ô chat duy nhất → action kích hoạt; bong bóng trả lời hiện tiêu đề “Gợi ý việc nên làm tiếp” + bảng `# | Việc nên làm tiếp` + chú thích `Sổ: MOM / Opcenter`; ảnh chụp `local_runs/tool2_smoke/app_action_answer.png` (không commit).
- Bằng chứng trong store chat cục bộ (không phải index): hội thoại mới `CONV-4B9D7403` có cặp tin nhắn `MSG-U-AE8F0DD5` (user) và `MSG-A-8A3FF2F7` (assistant, nội dung bảng) do chính hook lưu; lần hỏi lặp lại (câu ghép do ô nhập giữ chữ cũ) cũng khớp hint và lưu `MSG-A-36EC1099` — xác nhận cả đường “lưu tin nhắn” lẫn đường “render”.
- Trên app thật, câu không khớp hint không bị action chiếm (nhánh này do test đơn vị khẳng định chắc; smoke app không lặp lại sạch được vì phiên bị kẹt luồng “làm nóng bộ đọc” sẵn có — xem mục 6).

**d) Cổng kiểm tra:**
- `uv run --no-sync --group dev python -m compileall src tests` → sạch.
- `uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo).
- `uv run --no-sync --group dev python scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- `git diff --check` → sạch.
- `PYTHONPATH=src uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → OK (môi trường này cần `PYTHONPATH=src`, giống mọi lượt trước).
- `pytest -q` toàn bộ — hai lượt:
  - **Lượt A (đúng lệnh chuẩn, không workaround)**: `3220 đạt, 2 bỏ qua, 37 lỗi, 7 error` — 7 error là collection error do venv thiếu `xlrd` (nhóm `error_cases`), lỗi môi trường đã biết (các lượt E3/E4 cũng phải vá tạm cùng kiểu).
  - **Lượt B (đúng môi trường buoc0-deploy)**: `PYTHONPATH="src;C:/tmp/e3-py311"` + `AIOS_DATA_DIR="C:/tmp/aios-v14-data"` + `TMP=TEMP="C:/tmp"` → **`3295 đạt, 2 bỏ qua, 35 lỗi, 0 error`**; log đầy đủ `local_runs/tool2_smoke/pytest_full_env.txt` (không commit).
  - **Đối chiếu nền buoc0-deploy (`3276/2/37/0`)**: **+19 đạt** đúng bằng 17 test vé mới + 2 bài `owner_workflow_cli` nay import được tiến trình con (lượt B có `src` trong `PYTHONPATH`); **35 lỗi còn lại đúng bộ có sẵn** (9 graphify, 9 BGE worker/client, 4 đóng gói, 2 eval harness, 11 bài lẻ workspace-chat/mom/notebook/rag — danh sách trong log), **không bài nào đỏ thuộc vùng `chat_action`**; test vé 17/17 đạt.

**e) Ràng buộc vé:**
- Không ghi index/không embed: không chạy ingest, không mở `library.sqlite`, không gọi truy xuất; smoke chỉ hỏi trong hội thoại mới **không bật nguồn** và chỉ đi qua hook `chat_action` (đọc store chat JSONL).
- Không merge `main`; không đụng dữ liệu production. Ghi duy nhất ngoài repo: `local_runs/tool2_smoke/*.png` (đã gitignore) + store chat cục bộ của app (hội thoại smoke, đã nêu ở mục 5c).

## 6. Hạn chế / quan sát trung thực (cần Muse quyết)

1. **`daily_next_actions` vẫn đọc kho luồng cũ** (`local_cases/sources.jsonl` + `source_chunks.jsonl`) nên với sổ của luồng hiện hành (nguồn nằm ở `workspace_chat/notebook_sources.jsonl` — sổ `mom_opcenter` có 109 nguồn) tool sẽ luôn trả gợi ý “Nạp tài liệu nguồn vào Sổ tri thức”. Đây là đặc tính sẵn có của tool (TOOL-1 xếp nó “chưa nối”), không phải lỗi khung; **đề xuất vé riêng**: chuyển tool sang store hiện hành (kèm định nghĩa lại tiêu chí “đã có chunks” vì store mới không có danh sách chunk theo sổ).
2. **Quan sát sẵn có, không do TOOL-2**: hai hội thoại cũ nhiều nguồn (`CONV-6034EFB8`, `CONV-47535415`) dừng render **trước** khu vực composer (≥25 giây, lặp lại qua nhiều lần tải). Đã đối chứng A/B cùng hội thoại trên app bật cờ vs tắt cờ: kết quả **giống hệt nhau** (composer không xuất hiện ở cả hai), nên hiện tượng độc lập với vé này. Hội thoại mới render composer bình thường. Cần vé điều tra riêng nếu muốn xử lý (nghi bước gọi lại trí nhớ/đọc dấu vết trước composer — chưa chứng minh nguyên nhân).
3. `pytest -q` toàn bộ: xem mục 5d — ở lượt B (đủ môi trường) **35 lỗi + 0 error đúng bằng bộ lỗi có sẵn của nền**, không có bài nào thuộc TOOL-2; lượt A thiếu `xlrd` nên phát sinh thêm 7 collection error môi trường (không phải lỗi mã).

## 7. Đề xuất bước sau (ngoài vé này)

- TOOL-3/4/5 dùng lại khung: thêm 1 module action + 1 dòng vào `BUILTIN_ACTION_MODULES` (và bật cờ khi duyệt).
- Vé riêng chuyển `daily_next_actions` sang store hiện hành (mục 6.1).
- Cân nhắc trần ảnh biểu đồ và phương án “lưu tệp + `st.image`” nếu tool sau này trả ảnh lớn (hiện đã chốt data-URI + trần 400.000 byte).

## 8. Kiểm lại ngày 2026-10-05 (vé tái phát hành 2026-10-04 23:41 +07)

- Lý do kiểm lại: vé `TOOL-2` đã làm xong ngày 2026-09-30 và được verdict ĐẠT (`589d8fe`), nhưng ngày 2026-10-04 Muse phát hành lại vé này sau vé `OMP-MODEL-REPORT`. OMP kiểm cổng gate lúc 2026-10-05 00:25 +07: cổng MỞ (`HEAD` = `origin` = `0e06937`, `prompt.md` đúng vé `TOOL-2`, trạng thái `dang-lam` do OMP giữ từ 23:43, không có tệp watcher tự mở nào, `launchStallCount=0`). Vé thuộc lane NHÀ (code + test), khung đã có → chỉ kiểm lại, không viết lại code.
- Phạm vi rà: từ bản phát hành lại (`e60e621`) tới `HEAD` không đổi mã `chat_action` (`git diff e60e621..HEAD -- src/aios_habit/chat_action.py src/aios_habit/chat_action_next_actions.py` rỗng; chỉ thêm báo cáo `answer-draft-fallback`, dữ liệu thô enrichment và dòng tiến độ). Khung gốc 30/09 còn nguyên, chỉ mở rộng danh sách `BUILTIN_ACTION_MODULES` (1 → 19 module) nhờ các vé sau TOOL-3/4/5 — đúng hướng đã nêu ở mục 7.
- Bằng chứng chạy lại trên máy `h410asrock` (Windows, Python `3.11.14`):
  - `python -m compileall src tests` → sạch.
  - `pytest -q tests/test_chat_action.py` → **17 passed** (đúng 17 bài vé gốc).
  - `cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo); `import aios_habit.workspace_chat_app` → OK; `chat_action_enabled()` mặc định → `False` (cờ tắt); `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `git diff --check` → sạch.
  - `pytest -q` toàn bộ → **3998 đạt, 48 lỗi, 37 bỏ qua, 19 error** (lượt `bg_3`). Danh sách đỏ toàn nằm ngoài vùng vé: nhóm `BGE worker/client` (thiếu tiến trình con), `graphify` (thiếu gói), `error_cases_f4` + `chat_action_error_lookup` (thiếu tệp dữ liệu `/home/hatch/...`), đóng gói/mạng (`uv lock --check`, smoke thiếu module, `getaddrinfo failed`) — không bài nào thuộc `tests/test_chat_action.py` (17/17 vẫn xanh).
  - Ràng buộc vé giữ nguyên: không nút mới (`grep st.button/st.expander/st.tabs` trong 2 tệp khung rỗng), không ghi index (chỉ khớp chữ + đọc store chat JSONL, không mở `library.sqlite`/ingest/embed), không merge `main`, không đụng ổ D.
- Kết luận: giữ nguyên code 30/09, chỉ thêm mục kiểm lại này. Đề nghị Muse duyệt `xong-cho-duyet`.
