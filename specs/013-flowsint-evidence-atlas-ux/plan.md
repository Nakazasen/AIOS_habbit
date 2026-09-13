# Implementation Plan: 013-flowsint-evidence-atlas-ux

**Branch**: `013-flowsint-evidence-atlas-ux` | **Date**: 2026-09-13 | **Spec**: [specs/013-flowsint-evidence-atlas-ux/spec.md](file:///d:/Sandbox/AIOS_habbit/specs/013-flowsint-evidence-atlas-ux/spec.md)

**Input**: Tái cơ cấu toàn diện giao diện Đồ thị bằng chứng (Evidence Graph) và Atlas chi tiết sang chuẩn UX 3 cột phong cách Flowsint (Entities List, Dark Canvas with Pill Nodes, Inspector Panel), kết hợp sửa triệt để lỗi double SVG escape (`<tspan>`) trên nhãn Atlas.

---

## Summary

Dự án nâng cấp trực quan hóa bằng chứng từ dạng flowchart thẻ lớn cồng kềnh sang trải nghiệm điều tra phân tích tri thức tinh gọn, hiện đại kiểu Flowsint:
1. **Khắc phục dứt điểm bug rò rỉ SVG `<tspan>`** trong `_polish_evidence_atlas_html` bằng cách bóc tách sạch sẽ mọi thẻ HTML/SVG và giải mã thực thể trước khi định dạng nhãn SVG.
2. **Thiết kế lại Canvas Đồ thị Bằng chứng** (`evidence_graph_viewer.py` & `excaliflow_adapter.py`):
   - Chuyển đổi các khối hình chữ nhật lớn chứa cả đoạn văn bản sang dạng **viên thuốc (pill)** nhỏ gọn, chỉ hiển thị tiêu đề hoặc mã trích dẫn (`[1]`, `[2]`, tên file rút gọn).
   - Thiết lập bố cục 3 cột tương tác:
     * **Cột trái**: Danh sách thực thể phân cấp (`Câu hỏi`, `Câu trả lời`, `Trích dẫn`, `Tệp nguồn`), tích hợp ô tìm kiếm và bộ lọc nhanh.
     * **Cột giữa**: Canvas nền tối hiện đại (`#0f172a`), các đường nối mỏng, hỗ trợ tương tác chọn node và di chuyển tự do.
     * **Cột phải**: Bảng kiểm tra chi tiết (**Inspector Panel**) hiển thị toàn bộ văn bản trích đoạn (snippet), đường dẫn tệp (file path), độ tin cậy và liên kết tới vị trí gốc.
3. **Hiệu ứng Cross-Highlighting**: Khi bấm chọn một trích dẫn `[k]`, toàn bộ luồng bằng chứng từ câu trả lời tới tệp nguồn sẽ được chiếu sáng, các thành phần ngoại vi tự động làm mờ.

---

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Streamlit 1.40+, HTML5/SVG/CSS3/Vanilla JS embedded in-process, `aios_habit.evidence_graph_viewer`, `aios_habit.excaliflow_adapter`  
**Storage**: Bất biến (Immutability), nạp từ `rag-trace/v1` `EvidenceTrace` và bảng chọn nguồn  
**Testing**: `pytest`, `compileall`, `aios_habit.cli audit`  
**Target Platform**: Windows 10/11, Desktop App Streamlit Local, Zero Cloud Egress  
**Project Type**: In-Process UI & Vector Visualization Engine  
**Performance Goals**: Render < 150ms cho đồ thị 50 nodes; tương tác Inspector Panel phản hồi tức thì (< 16ms, 60fps) qua client-side DOM.  
**Constraints**:
- Giữ vững 100% schema `rag-trace/v1` và lọc chuẩn Commit C (4 node types).
- 100% Offline (Không sử dụng CDN, không tải script/font ngoài).
- Toàn bộ nhãn, thông báo và tooltip phải bằng tiếng Việt theo `AGENT_RULES.md`.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá | Ghi chú |
| :--- | :---: | :--- |
| **P1: An toàn dữ liệu & Quyền riêng tư** | **PASS** | Hoạt động hoàn toàn in-process nội bộ, không gửi bất kỳ dữ liệu trace nào ra ngoài Internet. |
| **P2: Trung thực tuyệt đối & Không fake PASS** | **PASS** | Giữ nguyên bộ lọc Commit C và cơ chế Insufficient Evidence Guard: từ chối vẽ đồ thị giả nếu thiếu nguồn/trích dẫn. |
| **P3: Chính sách Ngôn ngữ & Giao diện** | **PASS** | 100% nhãn tiếng Việt dễ hiểu trên thanh Entities và Inspector Panel; cấm hardcode tiếng Anh hay biệt ngữ thô. |
| **P4: Khả năng kế thừa & Kiến trúc** | **PASS** | Tái sử dụng `EvidenceGraphViewModel`, không phá vỡ hợp đồng của `evidence_graph_viewer.py` đối với các module cha. |

---

## Project Structure

### Documentation
```text
specs/013-flowsint-evidence-atlas-ux/
├── spec.md              # Đặc tả tính năng và kịch bản kiểm thử
├── plan.md              # Kế hoạch triển khai kỹ thuật này
├── research.md          # Phân tích nguyên nhân gốc lỗi <tspan> và cấu trúc Flowsint
└── tasks.md             # Danh mục công việc chi tiết
```

### Source Code Modifying
```text
src/aios_habit/
├── evidence_graph_viewer.py     # Cải tiến template HTML đồ thị 3 cột Flowsint
├── excaliflow_adapter.py        # Sửa regex _polish_evidence_atlas_html và layout pill node
└── i18n.py                     # Bổ sung các từ khóa tiếng Việt cho thanh Entities & Inspector

tests/
├── test_commit_c_evidence_graph_viewer.py   # Cập nhật/bổ sung test kiểm chứng giao diện 3 cột
├── test_commit_d_packaging_and_adapters.py  # Test chống rò rỉ <tspan> trên Atlas
└── test_workspace_chat_ui_i18n.py           # Đảm bảo 100% chuỗi giao diện mới tuân thủ i18n
```

---

## Planned Phases

### Giai đoạn 1: Sửa triệt để bug rò rỉ SVG `<tspan>` trên Atlas (1-2 giờ)
- Sửa hàm `_polish_evidence_atlas_html` trong `src/aios_habit/excaliflow_adapter.py`:
  * Sử dụng biểu thức chính quy bóc tách toàn bộ tag HTML/SVG (`re.sub(r'<[^>]+>', '', match.group("label"))`).
  * Thực hiện unescape thực thể HTML trước khi chia dòng, đảm bảo chuỗi văn bản hoàn toàn sạch.
  * Viết unit test tự động trong `tests/test_commit_d_packaging_and_adapters.py` xác thực nhãn Atlas không bao giờ chứa `<tspan>` lồng thô.

### Giai đoạn 2: Tái thiết kế Đồ thị bằng chứng theo bố cục 3 cột Flowsint (3-4 giờ)
- Cập nhật `_render_graph_container` trong `src/aios_habit/evidence_graph_viewer.py`:
  * **Cột trái (Entities Panel)**: Liệt kê danh sách dạng thẻ nhỏ (Pill badge) cho Câu hỏi, Câu trả lời, Trích dẫn `[1]`, `[2]`, Tệp nguồn. Tích hợp thanh tìm kiếm và lọc type theo phong cách Flowsint.
  * **Cột giữa (Dark Canvas)**: Render canvas gọn gàng với các node pill, bỏ toàn bộ khối snippet dài khỏi thân node. Các cạnh nối mỏng với mũi tên định hướng mềm mại.
  * **Cột phải (Inspector Panel)**: Thiết kế thanh trượt chi tiết hiển thị toàn bộ nội dung trích đoạn đầy đủ (Full Snippet), mã định danh, độ tin cậy, tên tệp nguồn và nút sao chép/mở rộng.
- Tích hợp mã JavaScript nội bộ xử lý tương tác click-to-inspect và tô sáng tuyến bằng chứng (`highlight path`).

### Giai đoạn 3: Kiểm thử toàn diện & Đảm bảo cổng chất lượng (1-2 giờ)
- Chạy toàn bộ các bộ test: `test_commit_c_evidence_graph_viewer.py`, `test_workspace_chat_ui_i18n.py`, `test_workspace_chat_app_smoke.py`.
- Kiểm tra `compileall`, `aios_habit.cli audit`.
- Lưu checkpoint vào `AgentMemory` và cập nhật `graphify`.
