# Báo cáo vé TEST-PORTABLE-AIANSWER-HOME — test `ai_answer` chạy được trên máy sạch thiếu gói `nakazasen_ai_router`

- Mã vé: `TEST-PORTABLE-AIANSWER-HOME`
- Máy: nhà `h410asrock`, Python 3.11 (`.venv`), CPU-only
- HEAD lúc làm: `4068e02` (nhánh `phieu-viec/rag-fix1`) — bản sửa vé này
- Phạm vi thay đổi: CHỈ `tests/test_workspace_chat_ai_answer.py` (+1 dòng). Không đụng `src/`, không ghi chỉ mục, không merge `main`.

---

## 1. Nguyên nhân từng lỗi

Chuỗi sự kiện trên máy/VM sạch (không cài gói ngoài) đúng như điều phối bắt được:

1. `ModuleNotFoundError: No module named 'nakazasen_ai_router'` — 2 test có mở `from nakazasen_ai_router import AIRouteOutcome, AIResult` bọc trong `try/...except ImportError` (nhánh dự phòng được thêm tại commit `8b48637` để test di động). Máy sạch không có gói → chương trình rơi vào nhánh `except`.
2. `NameError: name 'Any' is not defined` (dòng 1175 và 1251) — nhánh dự phòng định nghĩa `@dataclass AIRouteOutcome` với annotation `result: Any`, nhưng file test CHƯA từng import `Any`. Python đánh giá annotation trong thân class ngay lập tức (file không có `from __future__ import annotations`) → nổ `NameError` ngay khi định nghĩa class. Vì lỗi thứ hai xảy ra "trong khi đang xử lý" lỗi thứ nhất, traceback hiện cả hai lỗi liền nhau — đúng hiện tượng điều phối ghi trong vé.

Trên máy nhà có cài gói thật thì nhánh `except` không bao giờ chạy → test pass; đây là lý do hiện tượng chỉ lộ trên máy sạch.

## 2. Cách sửa

- Thêm đúng 1 dòng `from typing import Any` vào khối import đầu file test (`tests/test_workspace_chat_ai_answer.py`, dòng 5).
- Giữ nguyên ngữ nghĩa kiểm thử: có gói thật → vẫn dùng class thật của gói; thiếu gói → nhánh dự phòng tự định nghĩa dataclass cấu tạo tương đương (`status`, `result.text`, `provider_name`). KHÔNG xoá test, KHÔNG skip, không nới lỏng assertion nào.

## 3. Cách tách 2 môi trường để đo

- Máy sạch mô phỏng: chèn blocker qua `sitecustomize.py` nằm NGOÀI repo (`C:/tmp/test-portable-aianswer/sitecustomize.py`) — chặn mọi import `nakazasen_ai_router` trong tiến trình python, ném đúng `ModuleNotFoundError` như máy không cài gói.
  - `PYTHONPATH='C:/tmp/test-portable-aianswer' uv run --no-sync --group dev python -m pytest -q tests/test_workspace_chat_ai_answer.py`
- Máy thường (có gói thật tại `.venv/Lib/site-packages/nakazasen_ai_router/`):
  - `uv run --no-sync --group dev python -m pytest -q tests/test_workspace_chat_ai_answer.py`

## 4. Kết quả chạy lại (số đếm thật)

| Môi trường | Trước sửa | Sau sửa |
|---|---|---|
| Máy sạch mô phỏng (thiếu gói) | **2 failed / 59 passed** — đúng 2 ca vé chỉ tên, `NameError: name 'Any' is not defined` (dòng 1175/1251) | **61 passed / 0 failed** |
| Máy thường (có gói thật) | **61 passed / 0 failed** (nhánh `except` không chạy nên không có lỗi — khớp nhận định trong vé) | **61 passed / 0 failed** |

- 2 test vé chạy riêng: máy sạch mô phỏng **2 passed**; máy thường **2 passed**.
- Đối chứng liên quan: `tests/test_workspace_chat_router_adapter.py` trên máy sạch mô phỏng **4 passed** (mục tiêu "test di động" của chuỗi vé trước giữ nguyên).
- Ý nghĩa kiểm thử giữ nguyên: `test_generate_answer_via_router_integration_mocked_outcome` kiểm adapter đi qua tuyến legacy với router giả (đúng 1 lượt gọi, hợp đồng metadata sanitized, trả đúng text); `test_workspace_chat_router_creation_enables_network_and_v051_recovery` kiểm tạo router với `enable_network=True` + `policy.require_privacy_label=True` và lấy được kết quả `OK` (trên máy sạch, `policy` là bản dự phòng của adapter — vẫn kiểm đúng yêu cầu "bật mạng + khôi phục được").

## 5. Cổng repo

- Python 3.11 (`.venv`); `python -m compileall -q src tests`: OK
- `python -m aios_habit.cli audit`: `"status": "PASS"`, `errors: []`, `warnings: []`
- `python -c "import aios_habit.workspace_chat_app"`: OK
- Full `pytest -q` toàn repo (tại HEAD `4068e02`, 1072,69 giây ≈ 17,9 phút): **11 lỗi / 4192 đạt / 46 bỏ qua / 19 error** — đúng 30 mục đỏ, TẤT CẢ nằm ngoài file vé; phân loại:
  - **19 error**: thiếu dữ liệu theo đường dẫn của máy khác `\home\hatch\workspace\aios_data\dieu_tra_loi\...` (10 ca `tests/test_error_cases_f4.py` + 9 ca `tests/test_chat_action_error_lookup.py`) — lỗi môi trường dữ liệu, không phải lỗi logic.
  - **11 failed**:
    - 3 ca hạ tầng worker BGE: `test_bge_subprocess_client.py::test_client_enforces_bounded_deep_timeout` (`bge_subprocess_worker_crashed`), `test_bge_subprocess_worker.py::test_bge_subprocess_worker_crash_handling` (`PermissionError [WinError 5]` thư mục tạm), `test_bge_worker_self_healing.py::test_adapter_self_healing_reconciles_timeout_errors` (`assert 0 == 1`).
    - 2 ca cần mạng: `test_commit_b_tier5_adversarial.py::TestAntigravityBridgeCallsAndRouting::test_call_antigravity_bridge_privacy_guard` (`urlopen error [Errno 11001]`), `test_notebook_in_app_qa.py::test_in_app_qa_blocks_cloud_local_export` (`[WinError 10061] No connection`).
    - 3 ca khẳng định chuỗi mã nguồn app: `test_large_library_nonblocking_chat.py::test_app_source_code_guards_for_large_library`, `test_workspace_chat_source_selection_owner_flow.py::test_app_preparation_gate_is_scoped_to_query_relevant_sources`, `::test_app_retrieval_uses_the_exact_scope_that_preparation_checked` — đều đòi chuỗi `ready_sources or ready_in_scope` trong `workspace_chat_app.py`; chuỗi này đã bị gỡ bởi các commit `afd7fc6`/`b3a84e8` của vé khác và **vắng sẵn tại parent `bb318f1`** (trước commit vé này).
    - 2 ca `tests/test_rag_v2_opt_pyloops.py`: `test_cjk_prefilter_drops_short_term_only_matches` (cây hiện kỳ vọng `'short-only'` còn trong kết quả — ngược với bản sửa đã ĐẠT ghi ở báo cáo `cjk-prefilter-fix-home.md`) và `test_dense_preload_disabled_without_flag` (số khác nhau giữa 2 lần chạy: `(8, 0.655…)` vs `(8, 1.589…)` → phụ thuộc môi trường).
    - 1 ca index: `test_workspace_chat_production_index_filtering.py::test_production_index_specs_retrieval` (`496 != 889` — index production cục bộ trên máy này có 496 nguồn).
  - **Đối chứng "cây cũ"**: chạy lại đúng 11 ca failed này với file test của vé khôi phục về bản parent `bb318f1` → **vẫn 11 failed y hệt** (13,11 giây) → KHÔNG ca nào do diff vé.
  - So với baseline cũ trong báo cáo CLAIM-BUDGET (4150 đạt / 22 lỗi / 37 bỏ / 19 error): cây đã đổi bởi nhiều commit sau đó (thêm test mới), 30 mục đỏ hiện tại đều thuộc các nhóm môi trường/dữ liệu/commit khác như trên.

## 6. Rào cứng đã giữ

- Chỉ sửa file test (+1 dòng); KHÔNG sửa `src/` (nhánh fail-closed có sẵn của adapter giữ nguyên), không đổi hành vi chạy thật của app.
- Không ghi chỉ mục, không ghi DB; tệp mô phỏng máy sạch nằm ngoài repo, không commit.
- Không merge `main`; nhánh giữ `phieu-viec/rag-fix1`.
- Điều phối đối chiếu lại trên VM sạch: chỉ cần chạy `python -m pytest -q tests/test_workspace_chat_ai_answer.py` trên môi trường không cài gói → kỳ vọng `61 passed`.
