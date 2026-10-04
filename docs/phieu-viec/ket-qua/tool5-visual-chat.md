# Báo cáo vé TOOL-5 — Nối nhóm visual maps vào chat

- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `1be7002` (nhận vé 05:38) → `7483c5a` (mốc 1: chốt thiết kế) → `a6ab4a4` (code + test đường Mermaid) → `f69d5c9` (code + test chuyển sang PNG Pillow) → `f08521e` (gỡ helper Mermaid khỏi UI, giữ nguyên hành vi cũ) → `ca73a7d` (dọn chữ, không đổi hành vi) → báo cáo này. Không merge `main`, không force-push.
- Phạm vi vé: (1) đăng ký visual maps làm chat action; (2) câu “vẽ bản đồ tri thức về X” render map **ngay trong câu trả lời**; (3) test đầy đủ. Ràng buộc: không ghi index production, chỉ code + test, không đụng ổ D.
- Trạng thái: hoàn tất, chờ Muse verdict.

## 1. Hiện trạng nhận vé (kiểm chứng động)

- `evidence_graph_viewer` **đã nối sẵn** đúng như cảnh báo của vé trước: `src/aios_habit/workspace_chat_ui.py:22-23` import `render_evidence_graph_streamlit`, bong bóng trợ lý có nút “🕸️ Xem đồ thị bằng chứng” khi tin nhắn có `trace_id` (Commit C, dòng ~520-568). Vé này **không phá** đường đó; chỉ thêm đường hỏi chủ động qua `chat_action`.
- `visual_knowledge_map` (pure, chưa nối), `knowledge_map_html` (pure HTML, chưa nối), `worklens_semantic_map` (đọc JSONL store, chưa nối) — 3 module còn lại đã được nối.

## 2. Thay đổi

| File | Thay đổi |
|---|---|
| `src/aios_habit/chat_action_visual_maps.py` | **Mới** — 3 action chỉ-đọc: `ban_do_tri_thuc`, `ban_do_ho_so`, `do_thi_bang_chung` |
| `src/aios_habit/visual_map_image.py` | **Mới** — renderer PNG phía máy chủ bằng Pillow (không thêm phụ thuộc mới) |
| `src/aios_habit/chat_action.py` | +1 dòng `BUILTIN_ACTION_MODULES` (đăng ký module mới) |
| `tests/test_chat_action_visual_maps.py` | **Mới** — 29 bài test vé |
| `ARCHITECTURE.md`, `PROJECT_HANDOVER.md` | Thêm mục TOOL-5 (chỉ thêm, không xoá dòng cũ) |
| `docs/phieu-viec/mailbox/trang-thai.md` | Mốc nhận vé / mốc 1 / mốc 2 / mốc 3 / xong-chờ-duyệt |

Không sửa: hook `workspace_chat_app.py`, `workspace_chat_ui.py` (đã gỡ helper thử nghiệm), `library.sqlite`, index/embed, `local_cases` của repo.

## 3. Ba action mới (chung cờ `AIOS_FEATURE_CHAT_ACTION`, mặc định TẮT)

**a) “Bản đồ tri thức” (`ban_do_tri_thuc`)** — hint: “bản đồ tri thức”, “sơ đồ tri thức”.
- Dữ liệu: `_load_graph_inputs()` đọc JSONL cục bộ — `load_notebooks`, `load_sources`, `load_cases`, `load_evidence`, `load_learning_cards` (chỉ đọc).
- Dựng đồ thị: `worklens_semantic_map.build_worklens_semantic_graph` (60 nút/120 cạnh).
- Lọc chủ đề: tách “về X” sau hint (bỏ nối từ “về/của/cho/…”), giữ nút khớp X + nút kề 1 bước (tối đa 30 nút/60 cạnh); không khớp → hướng dẫn, không vẽ.
- Trả về: markdown mở đầu + trạng thái đồ thị (`_meta_note` theo `graph_kind`/nguồn gốc), **ảnh PNG** (khối `chart`), bảng theo khu (`knowledge_map_html.ZONE_DEFS`), bảng quan hệ (nhãn tiếng Việt từ `knowledge_map_html.RELATION_LABELS`).

**b) “Bản đồ hồ sơ” (`ban_do_ho_so`)** — hint: “bản đồ hồ sơ”, “sơ đồ hồ sơ”, “bản đồ case”, “sơ đồ case”.
- Tìm hồ sơ theo mã/tên trong `load_cases()`; không có → hướng dẫn + bảng danh sách hồ sơ (tối đa 10).
- Dựng đồ thị: `visual_knowledge_map.build_visual_knowledge_graph` (bằng chứng, câu trả lời mạnh `ide_handoff_strong_answer`, bài học `load_learning_cards_for_case`).
- Trả về: markdown mở đầu + **ảnh PNG** + bảng chỉ số `summarize_map_metrics` (nút/cạnh/bằng chứng/câu trả lời/bài học/độ phủ trích dẫn) + bảng nút.

**c) “Đồ thị bằng chứng” (`do_thi_bang_chung`)** — hint: “đồ thị bằng chứng”, “sơ đồ bằng chứng”.
- Lấy dấu vết mới nhất của hội thoại: `workspace_chat_store.load_conversation_traces(conversation_id)` → phần tử cuối.
- Dựng view model: `evidence_graph_viewer.build_evidence_graph_view_model(trace, locale)`; `is_insufficient` → thông báo thiếu bằng chứng (không vẽ).
- Trả về: markdown mở đầu + `stats_label` + **ảnh PNG** + bảng nút (loại/nhãn/nguồn-trích dẫn).

**Ảnh bản đồ** do `visual_map_image.render_map_png` vẽ bằng Pillow: hộp bo góc theo khu (mỗi khu một cột, tối đa 4 cột/24 nút trong khung ≤1400×1000), cạnh gấp khúc + mũi tên, nhãn quan hệ tiếng Việt (tối đa 8 nhãn), font fallback kiểu `production_prediction/spc_chart.py` (Arial/Tahoma → DejaVu/Liberation → mặc định). Ảnh trả qua khối `chart` của khung TOOL-2: data-URI nhúng thẳng vào markdown nên hiện trong bong bóng và tồn tại theo tin nhắn (trần `CHART_MAX_BYTES` 400 KB; ảnh thật ~12–60 KB).

## 4. Đường Mermaid đã thử và **loại** (bằng chứng)

1. `st.mermaid_chart` (Streamlit 1.60) hiện diện và render được trong app tối giản: cùng nội dung mermaid cho SVG `viewBox="0 0 673.86 309.4"` — khớp đủ nội dung.
2. Trong **app thật** (cờ bật, cwd store tạm), cùng nội dung cho `viewBox="-122.108 -32.7 682.364 293.549"` — hộp bao bị tính thiếu; nút xa nhất ở `translate(551.76, 154.7)` + bề rộng nút nằm ngoài hộp nên ảnh blob bị **cắt nút** (kiểm bằng cách fetch blob SVG và so `viewBox` với toạ độ nút).
3. Đã thử `width="content"` (không đổi), probe `layout="wide"` (không tái hiện lỗi), và cả fence ```mermaid native của markdown Streamlit 1.60 (frontend tự dựng `MermaidChart`) — trong app vẫn bị cắt (`viewBox="-137.6 -40.2 1406.16 835.3"` với nút ở x≈1388).
4. Kết luận: không phụ thuộc phần tử Mermaid của Streamlit; vẽ PNG phía máy chủ (đường `chart` đã được TOOL-2 kiểm chứng). Helper `render_assistant_content` từng thêm vào `workspace_chat_ui.py` đã được gỡ (`f08521e`), UI giữ nguyên hành vi trước vé.

## 5. Bằng chứng đã chạy

**a) Test vé:** `uv run --no-sync --group dev pytest -q tests/test_chat_action_visual_maps.py` → **29 passed**: đăng ký/module; khớp có dấu–không dấu cho 3 action; câu không liên quan không bị chiếm; bản đồ tri thức render ảnh + khu + nhãn quan hệ; lọc chủ đề + nút kề; chủ đề không khớp → hướng dẫn; store rỗng/lỗi → hướng dẫn; **không ghi gì** (cwd tạm sạch); bản đồ hồ sơ (danh sách/không tìm thấy/đồ thị + chỉ số + nút); đồ thị bằng chứng (thiếu hội thoại/thiếu trace/trace đủ/thiếu bằng chứng/lỗi store); renderer PNG (chữ ký PNG, trần 400 KB, trần 1400×1000, spec rỗng, data-URI giải mã đúng).

**b) Hồi quy liên quan:** 4 file action (`test_chat_action*.py`) + `test_commit_c_evidence_graph_viewer.py` + 4 file visual map/knowledge map + `test_agent_conversational_omnibar.py` → **151 passed**.

**c) Cổng kiểm tra:**
- `uv run --no-sync --group dev python -m compileall src tests` → sạch.
- `uv run --no-sync --group dev python scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo).
- `PYTHONPATH=src uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → OK.

**d) Smoke app Streamlit thật** (cờ `AIOS_FEATURE_CHAT_ACTION=1`, cwd/store tạm `C:/tmp/tool5-smoke`; seed: sổ `NB-TOOL5`, hồ sơ `CASE-TOOL5-1/2`, bằng chứng, bài học, hội thoại `CONV-TOOL5-SMOKE` + trace `TRC-TOOL5-SMOKE`):
- Hỏi “vẽ bản đồ tri thức” → bảng khu + quan hệ + **ảnh PNG hiện trong bong bóng** (ảnh trích từ app: `local_runs/tool5_smoke/app_final_knowledge_map.png`, 1244×428).
- Hỏi “vẽ bản đồ hồ sơ CASE-TOOL5-1” → chỉ số 4 nút/4 quan hệ + ảnh (`app_final_case_map.png`).
- Hỏi “vẽ đồ thị bằng chứng” → “Thống kê đồ thị: 4 nút · 3 liên kết” + ảnh (`app_final_evidence_graph.png`).
- Hỏi có chủ đề “về làm mát” → lọc đúng cụm chủ đề, ghi rõ “Đã ẩn 5 nút ngoài chủ đề”.
- Ảnh chụp màn hình (không commit): `local_runs/tool5_smoke/…`; tin nhắn do hook lưu chứa đúng markdown + data-URI.

**e) Full suite toàn bộ:** `PYTHONPATH="src;C:/tmp/e3-py311"`, `TMP=TEMP=C:/tmp`, `AIOS_DATA_DIR=C:/tmp/aios-v14-data`, `HEAD f69d5c9` (bản chạy; sau đó chỉ có 1 commit dọn chữ `ca73a7d` không đổi hành vi, test vé chạy lại 29/29) → **3.363 đạt, 2 bỏ qua, 35 lỗi, 0 error** (673 s). Đối chiếu nền TOOL-4 (`3.334/2/35/0`): **+29 đạt đúng bằng 29 test vé mới**; 35 lỗi giữ nguyên bộ có sẵn (9 `graphify_adapter`, nhóm `rag_v2` eval/cli/synthesis, vài bài workspace-chat/owner-pilot/mom privacy — **không bài nào thuộc `chat_action`/`visual_map`**).

**f) Ràng buộc vé:**
- **Không ghi index/embed:** không mở `library.sqlite`, không ingest, không embed; các action chỉ đọc JSONL cục bộ (và trace của chat store).
- **Không merge `main`**, không force-push.
- **Không đụng ổ D:** grep 0 hit `D:` trong code/test mới; smoke dùng `C:/tmp/tool5-smoke`; ảnh trong `local_runs/` (đã gitignore).

## 6. Hạn chế & đề xuất

1. **Ảnh chỉ vẽ tối đa 4 cột khu (24 nút)**; phần vượt quá vẫn có trong bảng khu/quan hệ (bảng liệt kê đầy đủ hơn ảnh). Nhãn cạnh tối đa 8; nhiều cạnh cùng khu có thể chồng nhẹ — chấp nhận để giữ ảnh gọn.
2. **Quan hệ của bản đồ hồ sơ** (`case_has_evidence`, `answer_cites_evidence`, …) được ánh xạ tiếng Việt bằng bảng cục bộ 4 mục trong module action (vì `visual_knowledge_map` phát quan hệ riêng, `knowledge_map_html.RELATION_LABELS` không có các khoá này).
3. **`worklens_semantic_map` chưa gồm import NotebookLM** (`include_bridge_imports=False`) — đồ thị nhập từ bridge vẫn xem ở tab Bản đồ; nếu cần đưa vào chat thì mở vé riêng (kèm đo chi phí đọc store).
4. **Lỗi Mermaid của Streamlit** (mục 4) là hạn chế upstream: nếu muốn diagram Mermaid thật trong bong bóng cần component riêng (như ExcaliFlow) hoặc báo upstream — ngoài phạm vi vé này.
5. `case_store`/`learning_models` loader tự `init_store()` (mkdir/touch file rỗng) khi store chưa tồn tại — hành vi sẵn có của app, không phải do vé; khi test, handler được kiểm bằng loader giả nên khẳng định **không tạo tệp nào**.

## 7. Kiểm lại ngày 2026-10-05 (vé tái phát hành 2026-10-05 ~02:07 +07)

- Lý do kiểm lại: vé `TOOL-5` đã làm xong ngày 2026-09-30 và chờ duyệt, nhưng ngày 2026-10-05 Muse phát hành lại vé này sau verdict `TOOL-4` ĐẠT. OMP kiểm cổng gate lúc 2026-10-05 02:18 +07: cổng MỞ (`HEAD` = `origin` = `00a4bd7`, `prompt.md` đúng vé `TOOL-5`, trạng thái `moi` mới ~02:07, watcher `LAUNCH 1/4` lúc 02:09 `launchStallCount=1` chưa chạm ngưỡng 4 lần `cho-muse`, không có file watcher tự mở trong mailbox). Vé thuộc lane NHÀ (code + test), code đã có → chỉ kiểm lại, không viết lại code.
- Phạm vi rà: từ bản phát hành lại (`a97f844`) tới `HEAD` không đổi mã `src`/`tests` (`git diff a97f844..HEAD -- src tests` rỗng; chỉ thêm batch enrichment `chatgpt-enrichment-raw` và dòng tiến độ `trang-thai.md`). Code gốc 30/09 còn nguyên: `chat_action_visual_maps.py` (832 dòng, 3 action `ban_do_tri_thuc`/`ban_do_ho_so`/`do_thi_bang_chung`), `visual_map_image.py` (311 dòng, renderer PNG Pillow), `tests/test_chat_action_visual_maps.py` (501 dòng, 29 bài).
- Kiểm cổng gate lần 2 lúc 2026-10-05 02:30 +07: cổng MỞ (watcher ngoài working copy `D:/Sandbox/Vong_lap_giao_viec/watcher_state.json` ghi `launchStallCount=1`, `LAUNCH 1/4` lúc 02:09, `status` đã sang `dang-lam` sau khi OMP nhận vé 02:18, 0 `RELAUNCH` cho TOOL-5; chưa chạm ngưỡng 4 lần `cho-muse`; `prompt.md` đúng vé TOOL-5). Không đặt `cho-muse`, không quay no-op.
- Bằng chứng chạy lại trên máy `h410asrock` (Windows, Python `3.11.14`, `uv 0.10.6`):
  - `python -m compileall src tests` → sạch.
  - `pytest -q tests/test_chat_action_visual_maps.py` → **29 passed** (đúng 29 bài vé gốc, 5.78s).
  - `pytest -q` 5 file `chat_action` (TOOL-2/3/4/5) → **85 passed** (17 + 12 + 27 + 29).
  - `PYTHONPATH=src python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo); `import aios_habit.workspace_chat_app` → OK; `chat_action_enabled()` → `False` (cờ mặc định TẮT); module vé đã đăng ký trong `BUILTIN_ACTION_MODULES` (tổng 15 module); `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `git diff --check` → sạch.
  - Ràng buộc vé giữ nguyên: không nút mới (`st.button`/`st.expander`/`st.tabs` = 0 trong 2 tệp vé), có `register_action`, không tham chiếu ổ D (0 kết quả `D:`), không merge `main`, không ghi index (test read-only vé gốc khẳng định store không đổi; action chỉ đọc JSONL cục bộ + trace chat store).
  - Full suite toàn bộ chưa chạy lại lượt này; dựa vào kết quả gốc 30/09 trong mục 5e (**3.363 đạt, 2 bỏ qua, 35 lỗi, 0 error**, +29 đạt đúng bằng 29 test vé mới, 35 lỗi toàn ngoài vùng vé) + hồi quy 85/85 xanh hiện tại — code không đổi nên kết quả gốc còn giá trị.
- Kết luận: giữ nguyên code 30/09, chỉ thêm mục kiểm lại này. Đề nghị Muse duyệt `xong-cho-duyet`.

