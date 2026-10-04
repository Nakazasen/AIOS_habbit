# Vé `TOOL-4` — Nối interview + prediction vào chat: báo cáo nghiệm thu

- Trạng thái: **xong — chờ Muse duyệt** (code + test, không ghi index).
- Máy: `h410asrock` — Windows (`win32`, 10.0.18363); Python `3.11.14` (venv repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `d52af49` (nhận vé 04:58) → `af1e912` (mốc 1: chốt thiết kế) → `c426ac9` (code + test) → `ad569fb` (mốc 2) → `0bb16ba` (mốc 3: smoke) → báo cáo này. Không merge `main`, không force-push.
- Phạm vi ghi: mã nguồn + test trong repo, 2 tài liệu canonical (`ARCHITECTURE.md`, `PROJECT_HANDOVER.md`), báo cáo này và `docs/phieu-viec/mailbox/trang-thai.md`. **Không ghi index, không embed, không đụng dữ liệu/index production.**

## 1. Việc đã làm (đúng các bước của vé)

1. **Đăng ký interview và prediction làm chat action** — 2 module mới theo khung TOOL-2, thêm 2 dòng vào `BUILTIN_ACTION_MODULES` (mục 2).
2. **Hỏi “phỏng vấn chuyên gia về X” → chạy luồng phỏng vấn trong chat** — hiện phiên đã lưu theo chủ đề, diễn biến hỏi–đáp và câu hỏi kế tiếp do động cơ thích ứng chạy tại chỗ gợi ý (mục 3).
3. **Hỏi “dự đoán X” → chạy dự đoán → hiện kết quả trong câu trả lời** — chạy lại mô hình EWMA LSU Iris trong bộ nhớ trên gói dữ liệu đã đăng ký và render bảng rủi ro trong bong bóng (mục 3).
4. **Test đầy đủ** — 27 bài mới + hồi quy TOOL-2/TOOL-3 + nhóm prediction cũ + smoke app thật (mục 5).

## 2. Thiết kế và quyết định

- **Interview (`chat_action_expert_interview.py`, action `phong_van_chuyen_gia`) — chỉ đọc, chạy động cơ tất định tại chỗ.** Handler mở `local_cases/workspace_cases.sqlite` (đường dẫn mặc định của `WorkspaceCaseRepository` / `ExpertInterviewRepository`, có thể override qua `context["case_db_path"]` khi test), lấy khoảng trống tri thức đã lưu và các phiên/kế hoạch/lượt liên quan; khớp chủ đề X bằng so khớp bỏ dấu (khớp `title`, `description`, `scope` của khoảng trống; `expert_id`, chủ đề kế hoạch, câu hỏi mồi của phiên). Câu hỏi kế tiếp gọi `adaptive_interview_engine.propose_next_action` với `gateway_client=None` (nhánh dự phòng tất định, **không gọi mạng**); chưa có phiên thì hiện bộ câu hỏi mồi `generate_seed_questions`. **Không ghi gì**: không tạo khoảng trống/kế hoạch/phiên/lượt; thiếu store thì trả hướng dẫn và **không khởi tạo cơ sở dữ liệu**.
- **Prediction (`chat_action_prediction.py`, action `du_doan_rui_ro`) — chỉ đọc, thêm chế độ chỉ-đọc cho repository.** Mở kho `local_cases/production_prediction.sqlite` bằng `ProductionPredictionRepository(read_only=True)`: kết nối SQLite qua URI `mode=ro`, **bỏ bước migrate**. Lý do bắt buộc: `migrate_database` hiện **luôn** tạo bản sao `.bak_*` khi tệp đã tồn tại, nên mở repository theo cách thường sẽ ghi thêm tệp mỗi lần chạy action; chế độ chỉ-đọc giữ đúng ràng buộc “không ghi” của vé. Chọn gói dữ liệu theo mã gói hoặc mã đơn vị trong câu hỏi (quét tối đa 10 gói gần nhất), dựng chuỗi trong bộ nhớ (`lsu_iris.normalize_records` + `join_lsu_trace`), chạy `shadow.ManualShadowRunner` với `ReplayProtocol.default_lsu_iris()` (ngưỡng 3.0σ, tối thiểu 20 điểm/chỉ số) và `repository=None` — không lưu assessment/outcome. Kết quả render bằng presenter của `prediction_shadow_ui` (`format_shadow_risk_view`, `format_unit_trace_view`) để giữ đúng tiếng Việt và cách hiển thị của màn LSU.
- **Không đổi hook, không thêm cờ, không thêm UI.** Hook TOOL-2 trong `workspace_chat_app.py` đã tổng quát; 2 action dùng chung cờ `AIOS_FEATURE_CHAT_ACTION` (mặc định **TẮT**). Không thêm ô nhập, nút bấm hay màn hình mới.
- **Hạ cấp an toàn.** Thiếu store/kho rỗng/không khớp X → câu hướng dẫn tiếng Việt; lỗi bất kỳ trong handler vẫn rơi về luồng trả lời thường nhờ `dispatch` fail-closed của TOOL-2; không lộ traceback hay đường dẫn hệ thống.

## 3. Hành vi người dùng thấy

**Interview** — hint: “phỏng vấn chuyên gia”, “chạy phỏng vấn chuyên gia” (khớp bỏ dấu, không phân biệt hoa thường). Bong bóng trả lời gồm: dòng dẫn “Các phiên phỏng vấn liên quan tới «X» — chỉ đọc, không mở phiên mới”; bảng phiên (`# | Phiên | Chuyên gia | Trạng thái | Chủ đề | Số lượt | Cập nhật`, tối đa 10 phiên); với phiên mới nhất còn mở: khối diễn biến 6 lượt cuối (Hỏi/Đáp rút gọn) và dòng “Câu hỏi tiếp theo (động cơ thích ứng gợi ý): …”. Chưa có phiên nhưng có khoảng trống khớp → bảng khoảng trống + bảng câu hỏi mồi (tối đa 8). Không tìm thấy X → câu hướng dẫn kèm số khoảng trống/phiên hiện có. Phiên đã kết thúc → ghi chú trạng thái thay vì gợi ý câu hỏi.

**Prediction** — hint: “dự đoán”. Bong bóng trả lời gồm: dòng tóm tắt “Dự đoán EWMA (LSU Iris) trên gói dữ liệu «mã gói»…, phạm vi …, đã xử lý N/M đơn vị, K đơn vị cần kiểm tra. Chỉ đọc — không ghi kho dự đoán.”; nếu câu hỏi nêu mã đơn vị: hồ sơ đơn vị (nhãn OK/NG, lỗi) + bảng lô linh kiện + bảng kết quả JIG (rút gọn 8 dòng mỗi bảng); sau đó là bảng rủi ro `# | Đơn vị | Mức rủi ro | Yếu tố chính | Thời điểm` (tối đa 15 dòng, yếu tố chính lấy từ `format_shadow_risk_view`). Không phát hiện đơn vị vượt ngưỡng → ghi chú rõ ngưỡng đang áp dụng. Kho trống/chưa có store/không khớp mã → câu hướng dẫn mở mục Dự đoán (LSU) tương ứng.

## 4. Tệp đã đổi

| Tệp | Thay đổi |
|---|---|
| `src/aios_habit/chat_action_expert_interview.py` | Mới — action “Phỏng vấn chuyên gia”: khớp chủ đề, đọc gap/plan/session/turn, chạy `propose_next_action`/`generate_seed_questions` tất định, render bảng + Q/A |
| `src/aios_habit/chat_action_prediction.py` | Mới — action “Dự đoán rủi ro (LSU Iris)”: chọn gói/đơn vị theo X, chạy `ManualShadowRunner` in-memory, render bằng presenter `prediction_shadow_ui` |
| `src/aios_habit/chat_action.py` | +2 dòng: đăng ký 2 module mới vào `BUILTIN_ACTION_MODULES` |
| `src/aios_habit/production_prediction/repository.py` | Thêm `read_only=True` (keyword-only): bỏ migrate, kết nối SQLite `mode=ro`; đường mặc định giữ nguyên |
| `tests/test_chat_action_expert_interview.py` | Mới — 12 bài |
| `tests/test_chat_action_prediction.py` | Mới — 15 bài |
| `ARCHITECTURE.md` | +1 mục “Nối nhóm interview và dự đoán vào chat (TOOL-4)” |
| `PROJECT_HANDOVER.md` | +1 mục “Bổ sung ngày 2026-09-30 — Phiếu TOOL-4” |
| `docs/phieu-viec/ket-qua/tool4-interview-prediction-chat.md` | Báo cáo này |
| `docs/phieu-viec/mailbox/trang-thai.md` | Mốc nhận vé / mốc 1 / mốc 2 / mốc 3 / xong-chờ-duyệt |

## 5. Bằng chứng đã chạy

**a) Test vé (store cô lập bằng `tmp_path`, không đụng dữ liệu thật):**
`uv run --no-sync --group dev python -m pytest -q tests/test_chat_action_expert_interview.py tests/test_chat_action_prediction.py` → **27 passed**:
- interview (12): có mặt trong `BUILTIN_ACTION_MODULES` + registry; khớp câu có dấu/không dấu (3 biến thể); câu không liên quan không bị chiếm; thiếu store → hướng dẫn và **không tạo tệp**; chủ đề không khớp → hướng dẫn; khoảng trống chưa có phiên → bảng câu hỏi mồi; phiên có lượt → bảng phiên + Q/A + câu hỏi kế tiếp (“ngưỡng kỹ thuật”); lọc chủ đề loại phiên khác; `dispatch` chỉ đọc (byte DB và danh sách tệp không đổi); `handle_chat_text` lưu đúng 2 tin nhắn;
- prediction (15): registry; khớp có dấu/không dấu (3 biến thể); câu không liên quan không bị chiếm; thiếu store → hướng dẫn, không tạo tệp; kho rỗng → hướng dẫn; hỏi theo mã đơn vị → chạy đúng 1/1 đơn vị + hồ sơ đơn vị + bảng JIG; mã đơn vị lạ → hướng dẫn; hỏi “dự đoán rủi ro” → chạy toàn gói 15/15 (fixture `time_series`, protocol siết tạm) + bảng rủi ro `Cần kiểm tra`; hỏi theo mã gói → chọn đúng gói; protocol mặc định → ghi chú “Không phát hiện đơn vị nào vượt ngưỡng”; repository chỉ-đọc không tạo `.bak_*` và ném lỗi khi cố ghi (`sqlite3.OperationalError`); `dispatch` không đổi byte DB/không sinh tệp; `handle_chat_text` lưu bong bóng dự đoán.

**b) Hồi quy TOOL-2/TOOL-3:** `pytest -q` 4 file `chat_action` → **56 passed** (17 + 12 + 27). **Hồi quy prediction cũ** (đã sửa `repository.py`): 8 file (`test_lsu_prediction_repository`, `test_lsu_manual_shadow`, `test_prediction_shadow_ui`, `test_stream_api`, `test_lsu_prediction_evaluation`, `test_lsu_prediction_reporting`, `test_lsu_audit_fixes`, `test_iris_log_intake`) → **117 passed**.

**c) Smoke app Streamlit thật** (cờ `AIOS_FEATURE_CHAT_ACTION=1`, CWD/store tạm `C:/tmp/tool4-smoke`, không đụng store thật trong repo):
- Seed: sổ `mom_opcenter`, hội thoại `CONV-TOOL4-SMOKE`, store hồ sơ có khoảng trống accepted + kế hoạch + phiên `SESS-PLAN-GAP-TOOL4-SMOKE-…` + 1 lượt; kho dự đoán có gói 30 đơn vị (2 lô lệch chuẩn ở LOT_28/LOT_30).
- Hỏi “Phỏng vấn chuyên gia về bước sóng quang học” → action kích hoạt: bảng phiên (`expert_opt_lead`, Đang chạy, chủ đề “Thiếu ngưỡng bước sóng quang học”, 1 lượt) + “Diễn biến phiên gần nhất” + câu hỏi kế tiếp từ động cơ thích ứng.
- Hỏi “Dự đoán rủi ro” → action kích hoạt: xử lý 30/30 đơn vị, 2 đơn vị cần kiểm tra (`UNIT_28` 24.59σ, `UNIT_30` 8.23σ), ghi rõ “Chỉ đọc — không ghi kho dự đoán”; **kho smoke không sinh tệp `.bak_*`** (kiểm tra sau khi chạy).
- Bằng chứng trong store hội thoại: cặp tin nhắn do chính hook lưu (`MSG-U-…` / `MSG-A-…` chứa bảng markdown). Ảnh chụp (không commit): `local_runs/tool4_smoke/app_actions_fullpage.png`, `local_runs/tool4_smoke/app_actions_main.png`.

**d) Cổng kiểm tra:**
- `uv run --no-sync --group dev python -m compileall src tests` → sạch.
- `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo).
- `uv run --no-sync --group dev python scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.
- `PYTHONPATH=src uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → OK.
- `git diff --check` → sạch.

**e) Full suite toàn bộ** (đúng môi trường buoc0-deploy: `PYTHONPATH="src;C:/tmp/e3-py311"`, `AIOS_DATA_DIR=C:/tmp/aios-v14-data`, `TMP=TEMP=C:/tmp`): **3.334 đạt, 2 bỏ qua, 35 lỗi, 0 error** (301,09s). Đối chiếu nền TOOL-3 (`3.307/2/35/0`): **+27 đạt đúng bằng 27 test vé mới**; 35 lỗi giữ nguyên bộ có sẵn theo nhóm (9 `graphify_adapter`, 6 `bge_subprocess_worker` + 3 `bge_subprocess_client`, 4 đóng gói, 2 eval harness `rag_v2`, 11 bài lẻ workspace-chat/mom/notebook/owner-pilot/rag/khác — đã đối chiếu danh sách tệp) — **không bài nào thuộc `chat_action`**; riêng `test_expert_knowledge_e2e` kiểm lại thấy lỗi ở nhánh phân loại privacy (`NOT_APPLICABLE` vs `BLOCKED_PRIVACY`), không liên quan module vé này. Log đầy đủ: `local_runs/tool4_smoke/pytest_full_env.txt` (không commit). Vé không chạy lượt `pytest -q` trần; theo TOOL-2/TOOL-3 lượt đó vướng 7 collection error do venv thiếu `xlrd` (lỗi môi trường đã biết).

**f) Ràng buộc vé:**
- **Không ghi index/không embed**: không chạy ingest, không mở `library.sqlite`, không gọi truy xuất; prediction chạy hoàn toàn trên kho cục bộ với kết nối `mode=ro` và `repository=None`.
- **Không merge `main`**, không force-push.
- **Không đụng ổ D**: code/test mới không chứa đường dẫn `D:` (mọi đường dẫn đều CWD-relative `local_cases/…` hoặc `tmp_path`); smoke dùng `C:/tmp/tool4-smoke`; ảnh trong `local_runs/` (đã gitignore).

## 6. Hạn chế / quan sát trung thực (cần Muse quyết)

1. **Thứ tự hook: luồng log JIG chạy trước `chat_action` (thiết kế TOOL-2).** Câu hỏi chứa từ khóa lệnh JIG sẽ bị `jig_chat_wire` bắt trước; cụ thể `la_lenh_nguong` coi **mọi** câu chứa “ngưỡng” là lệnh ngưỡng, nên “Phỏng vấn chuyên gia về ngưỡng bước sóng…” bị trả lời bằng bảng ngưỡng JIG (tái hiện trong smoke). Đây là hành vi sẵn có của app (xảy ra cả khi cờ TẮT, với mọi câu chứa “ngưỡng”), không do vé này, nhưng làm giảm độ phủ của action interview với các chủ đề chứa từ khóa đó — **đề xuất vé riêng** siết `la_lenh_nguong` thành mẫu lệnh rõ ràng (xem/đặt/xóa ngưỡng) hoặc đổi thứ tự hook có kiểm soát.
2. **Hint “dự đoán” rộng**: khi bật cờ, mọi câu chứa “dự đoán” (kể cả câu ngoài phạm vi LSU) sẽ vào action và nhận hướng dẫn phạm vi thay vì luồng trả lời thường. Chấp nhận theo đúng câu chữ của vé; nếu Muse muốn hẹp hơn thì chuyển thành họ hint (“dự đoán rủi ro”, “dự đoán lỗi”, “chạy dự đoán”).
3. **Prediction tính lại in-memory, không hiển thị assessment đã lưu.** Action chạy lại EWMA trên gói đã đăng ký nên kết quả độc lập với các lần “chạy bóng” trước đó trong màn LSU; nếu cần hiển thị lịch sử đã lưu (`load_shadow_risk_assessments`) thì mở vé riêng.
4. **“X” phải khớp dữ liệu**: chỉ nhận mã gói (12 ký tự đầu) hoặc mã đơn vị có trong gói; không có tìm kiếm chủ đề tự do cho prediction (đúng bản chất mô hình LSU Iris, không phải mô hình chủ đề).
5. **Giới hạn quét/chạy**: quét tối đa 10 gói gần nhất; chạy tối đa 200 đơn vị/lần (dừng có ghi chú). Gói lớn hơn sẽ chỉ xử lý phần đầu — nêu rõ trong caption khi bị dừng.
6. **Chat chỉ xem phiên phỏng vấn, không mở phiên/không nộp câu trả lời** (action một-lần, giữ chỉ-đọc theo chuẩn các action trước). Muốn phỏng vấn tương tác trong chat thì cần vé riêng (ghi gap/plan/session + xác nhận người dùng).
7. **SQLite `mode=ro` với kho ở chế độ WAL** có thể không mở được trên một số cấu hình; hiện kho dự đoán dùng chế độ journal mặc định nên chạy tốt, và handler hạ cấp thành câu hướng dẫn nếu mở lỗi.

## 7. Đề xuất bước sau (ngoài vé này)

- Vé riêng cho xung đột “ngưỡng” giữa `jig_chat_wire` và câu hỏi thường (mục 6.1).
- Cân nhắc hiển thị lịch sử chạy bóng đã lưu trong action prediction (mục 6.3).
- TOOL-5 dùng lại khung: thêm 1 module + 1 dòng `BUILTIN_ACTION_MODULES` (như vé này), lưu ý `evidence_graph_viewer` đã nối sẵn theo TOOL-1.

## 8. Kiểm lại ngày 2026-10-05 (vé tái phát hành 2026-10-05 ~01:50 +07)

- Lý do kiểm lại: vé `TOOL-4` đã làm xong ngày 2026-09-30 và chờ duyệt (`59448e1`), nhưng ngày 2026-10-05 Muse phát hành lại vé này sau verdict `TOOL-3` ĐẠT. OMP kiểm cổng gate lúc 2026-10-05 01:55 +07: cổng MỞ (`HEAD` = `origin` = `f25816c`, `prompt.md` đúng vé `TOOL-4`, trạng thái `moi` mới ~01:50, watcher `LAUNCH 1/4` lúc 01:51 `launchStallCount=1` chưa chạm ngưỡng 4 lần `cho-muse`). Vé thuộc lane NHÀ (code + test), code đã có → chỉ kiểm lại, không viết lại code.
- Phạm vi rà: từ bản phát hành lại (`f25816c`) tới `HEAD` không đổi mã `src`/`tests` (`git diff f25816c..HEAD -- src tests` rỗng; chỉ thêm batch enrichment `chatgpt-enrichment-raw` và dòng tiến độ `trang-thai.md`). Code gốc 30/09 còn nguyên: `chat_action_expert_interview.py` (404 dòng), `chat_action_prediction.py` (353 dòng), `tests/test_chat_action_expert_interview.py` (201 dòng, 12 bài), `tests/test_chat_action_prediction.py` (198 dòng, 15 bài), `ARCHITECTURE.md` + `PROJECT_HANDOVER.md` đã có mục TOOL-4.
- Kiểm cổng gate lần 2 lúc 2026-10-05 02:01 +07: cổng MỞ (watcher ngoài working copy `D:/Sandbox/Vong_lap_giao_viec/watcher_state.json` ghi `launchStallCount=1`, `LAUNCH 1/4` lúc 01:51, `status` đã sang `dang-lam` sau khi OMP nhận vé 01:55; chưa chạm ngưỡng 4 lần `cho-muse`; `prompt.md` đúng vé TOOL-4). Không đặt `cho-muse`, không quay no-op.
- Bằng chứng chạy lại trên máy `h410asrock` (Windows, Python `3.11.14`, `uv 0.10.6`):
  - `python -m compileall src tests` → sạch.
  - `pytest -q tests/test_chat_action_expert_interview.py tests/test_chat_action_prediction.py` → **27 passed** (đúng 27 bài vé gốc).
  - `pytest -q tests/test_chat_action.py tests/test_chat_action_answer_quality.py tests/test_chat_action_expert_interview.py tests/test_chat_action_prediction.py` → **56 passed** (17 TOOL-2 + 12 TOOL-3 + 27 TOOL-4).
  - Hồi quy prediction cũ (đã sửa `repository.py` ở vé gốc): 8 file (`test_lsu_prediction_repository`, `test_lsu_manual_shadow`, `test_prediction_shadow_ui`, `test_stream_api`, `test_lsu_prediction_evaluation`, `test_lsu_prediction_reporting`, `test_lsu_audit_fixes`, `test_iris_log_intake`) → **117 passed**.
  - `PYTHONPATH=src python -m aios_habit.cli audit` → `"status": "PASS"` (0 lỗi, 0 cảnh báo); `import aios_habit.workspace_chat_app` → OK; `chat_action_enabled()` → `False` (cờ mặc định TẮT); 2 module vé đã đăng ký trong `BUILTIN_ACTION_MODULES` (tổng 15 module); `scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`; `git diff --check` → sạch.
  - Ràng buộc vé giữ nguyên: không nút mới (`st.button`/`st.expander`/`st.tabs` = 0 trong 2 tệp action), có `register_action`, không tham chiếu ổ D (0 kết quả `D:`), không merge `main`, không ghi index (test read-only vé gốc khẳng định byte store không đổi; prediction chạy `mode=ro` không sinh `.bak_*`).
  - Full suite toàn bộ chưa chạy lại lượt này; dựa vào kết quả gốc 30/09 trong mục 5e (lượt B đủ môi trường: **3.334 đạt, 2 bỏ qua, 35 lỗi, 0 error**, +27 đạt đúng bằng 27 test vé mới, 35 lỗi toàn ngoài vùng vé) + hồi quy 56/56 và 117/117 xanh hiện tại — code không đổi nên kết quả gốc còn giá trị.
- Kết luận: giữ nguyên code 30/09, chỉ thêm mục kiểm lại này. Đề nghị Muse duyệt `xong-cho-duyet`.
