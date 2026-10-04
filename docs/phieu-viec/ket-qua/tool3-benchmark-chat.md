# Vé `TOOL-3` — Nối nhóm benchmark vào chat (chấm điểm chất lượng trả lời): báo cáo nghiệm thu

- Trạng thái: **xong — chờ Muse duyệt** (code + test, không ghi index).
- Máy: `h410asrock` — Windows (`win32`, 10.0.18363); Python `3.11.14` (venv repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `2866268` (nhận vé) → `b274a18` (mốc 1: chốt thiết kế) → `2b482dc` (code + test) → `87ad9bc` (mốc 2) → báo cáo này. Không merge `main`, không force-push.
- Phạm vi ghi: mã nguồn + test trong repo, 2 tài liệu canonical (`ARCHITECTURE.md`, `PROJECT_HANDOVER.md`), báo cáo này và `docs/phieu-viec/mailbox/trang-thai.md`. **Không ghi index, không embed, không đụng dữ liệu/index production.**

## 1. Việc đã làm (đúng 3 bước của vé)

1. **Đăng ký benchmark làm chat action theo khung TOOL-2** — module `chat_action_answer_quality.py`, thêm 1 mục vào `BUILTIN_ACTION_MODULES` (mục 2).
2. **Hỏi “đánh giá chất lượng trả lời” → chạy chấm điểm → hiện bảng điểm trong câu trả lời** — chấm câu trả lời mới nhất của hội thoại theo dấu vết bằng chứng, 3 bảng trong bong bóng (mục 3–5).
3. **Test đầy đủ** — 12 bài mới + smoke app Streamlit thật (mục 5).

## 2. Thiết kế và quyết định

- **Phạm vi chấm điểm**: câu trả lời **mới nhất** của hội thoại đang mở (kèm câu hỏi người dùng ngay trước nó), lấy từ chính chat store cục bộ. Lý do: câu hỏi “đánh giá chất lượng trả lời” là đánh giá câu trả lời người dùng vừa nhận; đây cũng là dữ liệu duy nhất có thật và đọc-only được tại thời điểm hỏi.
- **Nguồn bằng chứng**: `EvidenceTrace` gắn với tin nhắn trả lời (`load_message_trace`, dự phòng `message.trace_id` → `load_evidence_trace`) — chỉ lấy node loại `source`/`chunk`/`evidence`/`citation` có `snippet`.
- **Ba tầng chấm điểm, đúng 3 module của vé**:
  1. `rag_evaluator.evaluate_grounded_answer` — 6 chỉ số heuristic trên bằng chứng trích dẫn (độ phủ, liên quan, tỷ lệ metadata, độ neo, khớp ý định, xử lý thiếu bằng chứng).
  2. `mom_benchmark.score_mom_real_answer` + `weighted_real_answer_score` — rubric 7 tiêu chí 0–5, tổng có trọng số /100; đầu vào dựng từ nội dung trả lời + `source_refs` lấy từ node bằng chứng + `confidence_level` đọc từ trace metadata (không bịa thêm trường).
  3. `rag_benchmark.run_rag_benchmark` — tự kiểm tra hồi quy truy xuất **trong bộ nhớ**: corpus là chính các đoạn bằng chứng đã trích dẫn, câu hỏi là câu hỏi gốc của trace (dự phòng câu hỏi người dùng), kỳ vọng là chính các đoạn đó → trả lời “bằng chứng đã trích dẫn còn tìm lại được theo câu hỏi không”.
- **Hạ cấp an toàn**: thiếu trace → vẫn hiện 2 bảng đầu nhưng chèn ghi chú “không tìm thấy dấu vết bằng chứng”, bỏ tầng 3; thiếu hội thoại/câu trả lời/lỗi store → trả câu hướng dẫn tiếng Việt, không lộ traceback; lỗi bất kỳ trong handler vẫn rơi về luồng trả lời thường nhờ `dispatch` fail-closed của TOOL-2.
- **Không thêm gì ngoài khung**: không đổi hook `workspace_chat_app.py` (hook TOOL-2 đã tổng quát), không thêm cờ (dùng chung `AIOS_FEATURE_CHAT_ACTION`, mặc định TẮT), không thêm ô nhập/nút bấm/màn hình.

## 3. Hành vi người dùng thấy

- Hint khớp câu hỏi (so khớp bỏ dấu, không phân biệt hoa thường): “đánh giá chất lượng trả lời”, “chất lượng trả lời”, “chất lượng câu trả lời”, “đánh giá chất lượng câu trả lời”, “đánh giá câu trả lời”, “chấm điểm câu trả lời”.
- Bong bóng trả lời hiện: dòng dẫn câu hỏi/trả lời (rút gọn) + **Bảng 1** 6 chỉ số bằng chứng (%) + **Bảng 2** rubric MOM 7 tiêu chí (0–5) kèm tổng có trọng số /100 + **Bảng 3** tự kiểm tra truy xuất (số đoạn bằng chứng, tìm lại đoạn, tìm lại tài liệu, kết quả `Đạt`/`Đạt (có cảnh báo)`/`Chưa đạt`) + ghi chú giới hạn tiếng Việt.
- Trường hợp biên: chưa mở hội thoại → hướng dẫn mở hội thoại; hội thoại chưa có câu trả lời → hướng dẫn đặt câu hỏi trước; câu trả lời không có trace → 2 bảng + ghi chú, không có tầng 3; thiếu câu hỏi gốc → ghi chú thay tầng 3.

## 4. Tệp đã đổi

| Tệp | Thay đổi |
|---|---|
| `src/aios_habit/chat_action_answer_quality.py` | Mới — action “Đánh giá chất lượng trả lời”: chọn câu trả lời mới nhất, dựng 3 tầng chấm điểm, hạ cấp an toàn, đăng ký qua `register_action` |
| `src/aios_habit/chat_action.py` | +2 dòng: thêm module mới vào `BUILTIN_ACTION_MODULES` |
| `tests/test_chat_action_answer_quality.py` | Mới — 12 bài (khớp/không khớp hint, thiếu hội thoại/câu trả lời, chấm đủ 3 tầng, thiếu trace, lỗi store, read-only, lưu tin nhắn qua `handle_chat_text`) |
| `ARCHITECTURE.md` | +1 mục “Chấm điểm chất lượng trả lời trong chat (TOOL-3)” |
| `PROJECT_HANDOVER.md` | +1 mục “Bổ sung ngày 2026-09-30 — Phiếu TOOL-3” |
| `docs/phieu-viec/ket-qua/tool3-benchmark-chat.md` | Báo cáo này |
| `docs/phieu-viec/mailbox/trang-thai.md` | Cập nhật mốc nhận vé / mốc 2 / xong-chờ-duyệt |

## 5. Bằng chứng đã chạy

**a) Test vé (store cô lập bằng `tmp_path`, không đụng dữ liệu thật):**
`uv run --no-sync --group dev python -m pytest -q tests/test_chat_action_answer_quality.py` → **12 passed**:
- đăng ký module trong `BUILTIN_ACTION_MODULES` + registry;
- khớp hint có dấu và không dấu (3 biến thể), câu không liên quan không bị chiếm;
- thiếu `conversation_id` → hướng dẫn; hội thoại chưa có câu trả lời → hướng dẫn;
- chấm câu trả lời **mới nhất** (2 cặp Q/A, cặp sau được chấm, cặp cũ không lọt vào kết quả) với bằng chứng thật: tầng 1 (phủ 100%), tầng 2 (`Truy vết nguồn 5/5`, có tổng /100), tầng 3 (3 đoạn bằng chứng, tìm lại 100%, `Đạt`);
- câu trả lời không có trace → ghi chú “không tìm thấy dấu vết bằng chứng”, không có tầng 3, phủ 0%;
- lỗi đọc store → câu hướng dẫn (không lộ lỗi);
- `dispatch` chỉ đọc: so byte toàn bộ file store trước/sau khi chấm → không đổi;
- `handle_chat_text` lưu đúng 2 tin nhắn và trả `True`, nội dung trợ lý chứa bảng điểm.

**b) Hồi quy TOOL-2:** `uv run --no-sync --group dev python -m pytest -q tests/test_chat_action_answer_quality.py tests/test_chat_action.py` → **29 passed** (17 bài TOOL-2 + 12 bài mới).

**c) Smoke app Streamlit thật** (đúng kịch bản vé “hỏi thử → action kích hoạt đúng → kết quả render đúng”):
- App chạy thật với `AIOS_FEATURE_CHAT_ACTION=1`, CWD/store tạm `C:/tmp/tool3-smoke` (không đụng store thật trong repo).
- Seed hội thoại `CONV-TOOL3-SMOKE` có 1 cặp hỏi/đáp + trace 3 đoạn bằng chứng; mở app, mở sổ, mở hội thoại, gõ “Đánh giá chất lượng trả lời” trong khung chat duy nhất.
- Kết quả đúng như thiết kế: action kích hoạt (không rơi vào luồng RAG thường), bong bóng “Câu trả lời mới nhất” hiện — Tầng 1: phủ 100%, liên quan 80%, metadata 0%, neo 100%, khớp ý định 0%, xử lý thiếu bằng chứng 100%; Tầng 2: rubric 7 tiêu chí, tổng `41.0/100`; Tầng 3: 3 đoạn bằng chứng, tìm lại đoạn 100%, tìm lại tài liệu 100%, kết quả `Đạt`; ghi chú giới hạn hiển thị tiếng Việt.
- Ảnh chụp bằng chứng: `local_runs/tool3_smoke/app_action_answer.png` (không commit). Hai tin nhắn của lượt smoke được hook lưu vào store tạm (không phải index).

**d) Cổng kiểm tra môi trường này:**
- `uv run --no-sync --group dev python -m compileall src tests` → sạch.
- `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo).
- `uv run --no-sync --group dev python scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- `PYTHONPATH=src uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → OK.
- `git diff --check` → sạch.

**e) Full suite toàn bộ** — hai lượt (cùng cách TOOL-2):
- **Lượt A (đúng lệnh chuẩn `uv run --no-sync --group dev pytest -q`)**: dừng ở **7 collection error do venv thiếu `xlrd`** (nhóm `error_cases`: `test_auto_classifier`, `test_error_cases_f1..f4`, `test_feedback_loop`, `test_investigation_tree`) — lỗi môi trường đã biết (TOOL-2/E3/E4 gặp y hệt), không phải lỗi mã.
- **Lượt B (đúng môi trường buoc0-deploy: `PYTHONPATH="src;C:/tmp/e3-py311"`, `AIOS_DATA_DIR="C:/tmp/aios-v14-data"`, `TMP=TEMP="C:/tmp"`)**: **3.307 đạt, 2 bỏ qua, 35 lỗi, 0 error** (349,87s). Đối chiếu nền TOOL-2 (`3.295/2/35/0`): **+12 đạt đúng bằng 12 test vé mới**; 35 lỗi còn lại đúng nhóm có sẵn (9 `graphify_adapter`, 9 BGE subprocess worker/client, 4 đóng gói, 2 eval harness `rag_v2`, còn lại là bài lẻ workspace-chat/mom/notebook/owner-pilot/rag) — **không bài nào thuộc `chat_action`**; test vé **12/12 đạt**.

**f) Ràng buộc vé:**
- **Không ghi index/không embed**: chỉ đọc chat store cục bộ (messages + traces) và chạy SQLite in-memory trong `rag_benchmark`; test `dispatch` read-only khẳng định byte store không đổi.
- **Không merge `main`**, không force-push; không thêm cờ/thao tác ghi nào.
- **Không đụng dữ liệu production**: smoke dùng store tạm trên `C:/tmp`; ảnh chụp để trong `local_runs/` (đã gitignore).

## 6. Hạn chế / quan sát trung thực (cần Muse quyết)

1. **Rubric MOM vốn dành cho câu trả lời kiểu MOM** (có mục “điều có bằng chứng / chưa đủ bằng chứng / next checks”). Câu trả lời chat thường sẽ thấp điểm ở phần cấu trúc (ví dụ smoke: độ đầy đủ 0/5, tính hành động 0/5) — đã ghi chú rõ ngay trong bong bóng; nếu Muse muốn rubric riêng cho chat thì mở vé chỉnh ngưỡng/mục.
2. **Tầng 3 chỉ là tự kiểm tra hồi quy truy xuất trên chính bằng chứng trích dẫn**, không phải benchmark truy xuất toàn kho: repo không có bộ câu hỏi vàng dùng chung (bộ 12 câu MOM là dữ liệu `local_cases/`, không commit), nên không thể tính hit-rate truy xuất thật cho mọi sổ mà không bịa kỳ vọng. `mom_benchmark.load_benchmark_records` (đọc bản ghi MOM đã lưu) không dùng vì máy trạm thường không có dữ liệu đó — sẽ hiển thị rỗng vô nghĩa.
3. **Chỉ chấm câu trả lời mới nhất**, không tổng hợp cả hội thoại — nếu muốn “bảng điểm nhiều câu trả lời” thì mở vé riêng.
4. **`Khớp ý định truy vấn` thường 0%** vì cần metadata `_score_explanation` chứa `intent=` — trace chat hiện không ghi trường này; hiển thị trung thực thay vì suy diễn.
5. Câu trả lời cũ/không có trace vẫn được chấm tầng 1–2 nhưng bằng chứng rỗng — đã có ghi chú cảnh báo trong bong bóng.

## 7. Đề xuất bước sau (ngoài vé này)

- TOOL-4/TOOL-5 dùng lại khung: thêm 1 module + 1 dòng `BUILTIN_ACTION_MODULES` (như vé này).
- Nếu cần “benchmark cả hội thoại” hoặc bộ câu hỏi vàng theo sổ → vé riêng.
- Cân nhắc bổ sung `confidence_level`/`confirmed_by_source` vào metadata trace khi luồng trả lời ghi trace, để rubric MOM chấm sát hành vi thật hơn.

## 8. Kiểm lại ngày 2026-10-05 (vé tái phát hành 2026-10-05 ~00:57 +07)

- Lý do kiểm lại: vé `TOOL-3` đã làm xong ngày 2026-09-30 và chờ duyệt (`15962ab`), nhưng ngày 2026-10-05 Muse phát hành lại vé này sau verdict `TOOL-2` ĐẠT. OMP kiểm cổng gate lúc 2026-10-05 01:08 +07: cổng MỞ (`HEAD` = `origin` = `b5d2f7f`, `prompt.md` đúng vé `TOOL-3`, trạng thái `moi` mới ~00:57, không có tệp watcher tự mở nào trong mailbox). Vé thuộc lane NHÀ (code + test), code đã có → chỉ kiểm lại, không viết lại code.
- Phạm vi rà: từ bản phát hành lại (`b5d2f7f`) tới `HEAD` không đổi mã `src`/`tests` (`git diff b5d2f7f..HEAD -- src tests` rỗng; chỉ thêm batch enrichment `chatgpt-enrichment-raw` và dòng tiến độ `trang-thai.md`). Code gốc 30/09 còn nguyên: `chat_action_answer_quality.py` (391 dòng), `chat_action.py` (`BUILTIN_ACTION_MODULES` có mục `aios_habit.chat_action_answer_quality`), `tests/test_chat_action_answer_quality.py` (233 dòng, 12 bài), `ARCHITECTURE.md` + `PROJECT_HANDOVER.md` đã có mục TOOL-3.
- Kiểm cổng gate lần 2 lúc 2026-10-05 01:33 +07: cổng MỞ (watcher ngoài working copy `D:/Sandbox/Vong_lap_giao_viec/watcher_state.json` ghi `launchStallCount=2`, `RELAUNCH 2/4` lúc 01:30:31, chưa chạm ngưỡng 4 lần `cho-muse`; `prompt.md` đúng vé TOOL-3). Không đặt `cho-muse`, không quay no-op.
- Bằng chứng chạy lại trên máy `h410asrock` (Windows, Python `3.11.14`, `uv 0.10.6`):
  - `python -m compileall src tests` → sạch.
  - `pytest -q tests/test_chat_action_answer_quality.py` → **12 passed** (0.85s, đúng 12 bài vé gốc).
  - `pytest -q tests/test_chat_action_answer_quality.py tests/test_chat_action.py` → **29 passed** (0.94s: 17 bài TOOL-2 + 12 bài mới).
  - `PYTHONPATH=src python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo); `import aios_habit.workspace_chat_app` → OK; cờ `chat_action` mặc định → `False` (TẮT); `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `git diff --check` → sạch.
  - Ràng buộc vé giữ nguyên: không nút mới (`grep st.button/st.expander/st.tabs` trong 2 tệp action bằng 0), không ghi index (chỉ đọc store chat JSONL + chạy trong bộ nhớ, test read-only khẳng định byte store không đổi), không merge `main`, không đụng ổ D.
  - Full suite toàn bộ chưa chạy lại lượt này; dựa vào kết quả gốc 30/09 trong mục 5e (lượt B đủ môi trường: **3.307 đạt, 2 bỏ qua, 35 lỗi, 0 error**, +12 đạt đúng bằng 12 test vé mới, 35 lỗi toàn ngoài vùng vé) + hồi quy 29/29 xanh hiện tại — code không đổi nên kết quả gốc còn giá trị.
- Kết luận: giữ nguyên code 30/09, chỉ thêm mục kiểm lại này. Đề nghị Muse duyệt `xong-cho-duyet`.
