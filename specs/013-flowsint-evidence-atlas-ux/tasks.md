# Tasks: 013-flowsint-evidence-atlas-ux

**Branch**: `013-flowsint-evidence-atlas-ux` | **Spec**: [specs/013-flowsint-evidence-atlas-ux/spec.md](file:///d:/Sandbox/AIOS_habbit/specs/013-flowsint-evidence-atlas-ux/spec.md) | **Plan**: [specs/013-flowsint-evidence-atlas-ux/plan.md](file:///d:/Sandbox/AIOS_habbit/specs/013-flowsint-evidence-atlas-ux/plan.md)

---

## Phase 1: Sửa Dứt Điểm Lỗi Double SVG Escape `<tspan>` (Atlas Node Labels)

- [x] **T01-ATLAS-TSPAN**: Sửa hàm `_polish_evidence_atlas_html` trong `src/aios_habit/excaliflow_adapter.py`.
  - Bóc tách toàn bộ tag HTML/SVG bên trong nhãn node (`clean_label = re.sub(r"<[^>]+>", "", raw_label)`).
  - Giải mã thực thể HTML (`html.unescape`) trước khi chia dòng.
  - Đảm bảo các thẻ `<tspan>` được sinh ra chỉ chứa nội dung chữ thuần túy, tuyệt đối không lồng thẻ rác.
- [x] **T02-ATLAS-TEST**: Bổ sung unit test trong `tests/test_commit_d_packaging_and_adapters.py`.
  - Kiểm tra đầu ra của `render_evidence_atlas_html` không chứa chuỗi `&lt;tspan` hoặc `<tspan` bên trong thẻ chữ.

---

## Phase 2: Tái Thiết Kế Đồ Thị Bằng Chứng Phong Cách Flowsint (3 Cột: Thực Thể - Canvas Pill - Bảng Kiểm Tra)

- [x] **T03-I18N-KEYS**: Bổ sung các chuỗi bản địa hóa cho thanh thực thể và bảng kiểm tra trong `src/aios_habit/i18n.py`.
  - `entities_title`: "Danh sách thực thể"
  - `inspector_title`: "Bảng kiểm tra bằng chứng"
  - `search_entities_placeholder`: "Tìm kiếm thực thể hoặc nội dung..."
  - `select_node_hint`: "Chọn một thực thể trên canvas hoặc danh sách để xem chi tiết"
  - `confidence_score`: "Độ tin cậy"
  - `source_file`: "Tệp nguồn"
  - `full_snippet`: "Đoạn trích đầy đủ"
- [x] **T04-VIEWER-3COL-HTML**: Tái cấu trúc hàm render trong `src/aios_habit/evidence_graph_viewer.py` và `src/aios_habit/excaliflow_adapter.py`.
  - Thiết kế cấu trúc 3 cột:
    - Cột 1 (Entities Sidebar): Hiển thị phân nhóm các thực thể với số lượng đếm, biểu tượng và bộ lọc nhanh.
    - Cột 2 (Dark Canvas): Chuyển các card lớn thành các node **viên thuốc (pill)** nhỏ gọn với viền phát sáng, không nhồi nhét đoạn trích dẫn dài lên canvas.
    - Cột 3 (Inspector Panel): Thiết kế khung hiển thị chi tiết khi click vào node với đầy đủ trích đoạn nguyên vẹn, điểm tin cậy và đường dẫn tệp.
- [x] **T05-VIEWER-INTERACTION-JS**: Viết mã điều khiển tương tác (Client-side JavaScript).
  - Bắt sự kiện click chọn node -> cập nhật Inspector Panel tức thì.
  - Xử lý tô sáng tuyến bằng chứng (`Cross-Highlighting`): Khi click vào trích dẫn `[k]`, làm nổi bật đường nối `Answer -> Citation [k] -> Source` và làm mờ các thành phần khác.
  - Ô tìm kiếm lọc danh sách thực thể theo thời gian thực.

---

## Phase 3: Kiểm Thử & Kiểm Toán Chất Lượng Dự Án

- [x] **T06-UNIT-TESTS**: Chạy toàn bộ các test liên quan đến đồ thị bằng chứng:
  - `pytest tests/test_commit_c_evidence_graph_viewer.py -q`
  - `pytest tests/test_commit_d_packaging_and_adapters.py -q`
  - `pytest tests/test_workspace_chat_ui_i18n.py -q` (đảm bảo không lọt chuỗi hardcode).
  - `pytest tests/test_flowsint_evidence_atlas.py -q` (5/5 passed).
- [x] **T07-QUALITY-GATES**: Chạy các cổng kiểm thử chuẩn:
  - `uv run --no-sync --group dev python -m compileall src tests` (PASS)
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` ("status": "PASS")
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` (PASS)
- [x] **T08-CHECKPOINT**: Lưu trạng thái vào `AgentMemory` và cập nhật đồ thị tri thức `graphify`.
