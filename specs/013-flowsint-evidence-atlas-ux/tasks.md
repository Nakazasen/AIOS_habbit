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

---

## Phase 4: Nâng Cấp Đột Phá Thẩm Mỹ & UX Flowsint 2.0 (Toàn Diện)

- [x] **T09-FLOATING-CONTROLS**: Xây dựng thanh công cụ nổi (Floating Canvas Toolbar) trên Canvas:
  - Zoom In (`+`), Zoom Out (`-`), Căn vừa màn hình (`⊡ Fit to View`), Toàn màn hình (`⛶ Fullscreen`).
  - Hỗ trợ Pan / Drag kéo thả tự do canvas bằng chuột mượt mà.
- [x] **T10-SMOOTH-BEZIER-FLOW**: Nâng cấp đồ họa cạnh nối thành đường cong Cubic Bezier mượt mà:
  - Thay thế đường gấp khúc/đường thẳng bằng đường cong Bezier tính toán theo tiếp tuyến tự nhiên giữa các tầng.
  - Hiệu ứng tia sáng chuyển động (`stroke-dasharray animated pulse`) khi hover hoặc chọn đường nối.
- [x] **T11-COLLAPSIBLE-INSPECTOR**: Nâng cấp Inspector Panel thành công cụ điều tra toàn diện:
  - Nút thu gọn / mở rộng bảng kiểm tra (`‹ / ›`) linh hoạt.
  - Thước đo độ tin cậy đồ họa (Confidence Gauge Bar) đổi màu trực quan theo điểm số.
  - Cây liên kết hai chiều (Inbound & Outbound links) hỗ trợ click chuyển tiêu điểm tức thì sang node tương ứng trên canvas.
  - Khung đọc trích dẫn cao cấp với nút sao chép nhanh và đếm ký tự.
- [x] **T12-REALTIME-ENTITY-SEARCH**: Tích hợp thanh tìm kiếm thực thể thời gian thực và bộ lọc loại node ở cột trái; tự động làm mờ các node không khớp trên canvas.
- [x] **T13-EVIDENCE-GRAPH-UPGRADE**: Đồng bộ giao diện 3 cột và tương tác Flowsint 2.0 giữa Đồ thị bằng chứng nội tuyến (`evidence_graph_viewer.py`) và Atlas chi tiết (`excaliflow_adapter.py`).
- [x] **T14-TESTS-AND-AUDIT**: Bổ sung unit test trong `tests/test_flowsint_evidence_atlas.py` và chạy qua 100% Quality Gates (`compileall`, `pytest`, `cli audit`).

---

## Phase 5: Bước Nhảy Vọt - Mạng Thiên Hà Động Lực Học & Mini Radar Inspector

- [x] **T15-I18N-RADAR**: Bổ sung các nhãn i18n cho Mini Radar và chế độ thiên hà trong `src/aios_habit/i18n.py` (`neighbors_count`, `radar_title`, `galaxy_mode`, `layout_mode_switch`, `drag_node_hint`).
- [x] **T16-MINI-RADAR-DOM**: Xây dựng khung cấu trúc DOM/SVG cho Mini Radar (Ego Graph / Neighbors Ring) trong Inspector Panel tại `src/aios_habit/excaliflow_adapter.py`.
- [x] **T17-FORCE-SIMULATION-ENGINE**: Triển khai động cơ mô phỏng vật lý Client-side Force-Directed Simulation thuần Vanilla JS (Coulomb repulsion, Hooke springs, Center gravity, Drag-and-drop physics đàn hồi 60fps).
- [x] **T18-LOD-MICRO-DOTS**: Triển khai cơ chế Level of Detail (LOD): Các node trích dẫn hiển thị dưới dạng hạt sáng siêu nhỏ micro-dots (`r=4px`), tự động bung thành glowing pill capsule khi được hover/click hoặc khi là Hub node.
- [x] **T19-RADAR-INTERACTION-SCRIPT**: Viết script tương tác cho Mini Radar (vẽ các tia liên kết tới các láng giềng trên quỹ đạo tròn, click láng giềng để chuyển tiêu điểm ngay lập tức).
- [x] **T20-TESTS-AND-VERIFY**: Bổ sung unit tests cho Mini Radar và Force Galaxy, xác thực qua toàn bộ Quality Gates (`compileall`, `pytest`, `cli audit`, runtime import).

---

## Phase 6: Hoàn Thiện Tỉ Lệ Thị Giác, Khắc Phục Đè Node & Nền Quỹ Đạo Thiên Hà Đồng Tâm (v0.3.1)

- [x] **T21-MINI-RADAR-CONTAINMENT**: Khắc phục triệt để lỗi CSS toàn cục `svg { min-width: 1100px; }` ép phình to `#mini-radar-svg` và `#atlas-mini-radar-svg`. Cô lập scope selector `.scene-board svg` và `.canvas svg`, thiết lập kích thước chuẩn xác $160 \times 140\text{px}$ kèm `overflow: hidden; box-sizing: border-box;`.
- [x] **T22-AABB-COLLISION**: Triển khai thuật toán chống đè hộp AABB Box Collision Resolution trong `physicsTick`, tự động đẩy dạt các thẻ va chạm theo trục thâm nhập nhỏ nhất, xóa bỏ 100% tình trạng chồng đè chữ và thẻ.
- [x] **T23-CONCENTRIC-CELESTIAL-ORBITS**: Bổ sung 3 vòng quỹ đạo thiên hà đồng tâm thanh nhã (`celestial-orbit orbit-core/mid/outer`) và trục toạ độ chữ thập mờ (`celestial-axis`) ở nền SVG canvas, tạo chiều sâu không gian trực quan.
- [x] **T24-TIERED-RADIUS-DISTRIBUTION**: Tối ưu hóa phân bố 3 tầng bán kính tự nhiên: Tâm Core Hubs ($R \le 40\text{px}$) $\to$ Citations ($R \approx 195\text{px}$) $\to$ Documents ($R \approx 355\text{px}$) kết hợp lực hướng tâm quỹ đạo `kOrbit`.
- [x] **T25-UPSTREAM-EXCALIFLOW-STUDIO-SYNC**: Đồng bộ triệt để sang kho `ExcaliFlow Studio` (`D:\Sandbox\ExcaliFlow Studio`), cập nhật `evidence_atlas.py` và `test_knowledge.py`, bump version lên `0.3.1`, chạy 81/81 test pass, commit và push thành công lên GitHub `origin main`.
- [x] **T26-VERIFY-AND-CHECKPOINT**: Kiểm chứng qua toàn bộ Quality Gates của `AIOS_habbit` (`compileall`, `pytest`, `cli audit` PASS, runtime import `workspace_chat_app`), lưu AgentMemory Checkpoint.
