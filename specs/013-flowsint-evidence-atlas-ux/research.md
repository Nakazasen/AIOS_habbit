# Research & Technical Analysis: 013-flowsint-evidence-atlas-ux

## 1. Phân tích nguyên nhân gốc lỗi rò rỉ SVG `<tspan>` (Ảnh 3)

### Mã nguồn hiện tại (`src/aios_habit/excaliflow_adapter.py` lines 110-125)

```python
def _polish_evidence_atlas_html(atlas_html: str, graph: Dict[str, Any]) -> str:
    def replace_label(match: re.Match[str]) -> str:
        x, y = match.group("x"), match.group("y")
        lines = _atlas_label_lines(html.unescape(match.group("label")))
        tspans = "".join(
            f'<tspan x="{x}" dy="{0 if index == 0 else 17}">{html.escape(line)}</tspan>'
            for index, line in enumerate(lines)
        )
        return f'{match.group("open")}{tspans}</text>'

    atlas_html = re.sub(
        r'(?P<open><text class="node-label" x="(?P<x>[^"]+)" y="(?P<y>[^"]+)">)(?P<label>.*?)</text>',
        replace_label,
        atlas_html,
    )
```

### Cơ chế gây lỗi

1. Hàm `ea.build_evidence_atlas_html(graph)` từ thư viện ExcaliFlow đã tạo sẵn các thẻ `<text class="node-label"><tspan ...>...</tspan></text>`.
2. Biểu thức chính quy `(?P<label>.*?)` đã bắt trọn các thẻ `<tspan>` bên trong.
3. Khi `_atlas_label_lines` xử lý, nó nhận chuỗi có chứa ký tự `<tspan x="84" dy="0">...`.
4. Sau đó `html.escape(line)` mã hóa các ký tự `<` và `>` thành `&lt;` và `&gt;` rồi đặt vào trong thẻ `<tspan>` mới!
5. Trình duyệt khi dựng hình SVG sẽ hiển thị chữ thô: `<tspan x="84" dy="0">Dựa trên tài liệu hệ...</tspan>`.

### Giải pháp kỹ thuật chuẩn

Bóc tách sạch toàn bộ thẻ HTML/SVG trước khi đưa vào `_atlas_label_lines`:

```python
raw_label = match.group("label")
# Strip all inner SVG/HTML tags to extract pure text content
clean_label = re.sub(r"<[^>]+>", "", raw_label)
unescaped_text = html.unescape(clean_label).strip()
lines = _atlas_label_lines(unescaped_text)
```

---

## 2. Phân tích kiến trúc UX Flowsint & Đồ thị Bằng chứng (Ảnh 1 & Ảnh 2)

### Vấn đề hiện tại của Đồ thị Bằng chứng (Ảnh 2)

- Kích thước thẻ cố định `250px x 108px` nhưng cố nhét cả đoạn văn bản dài `snippet` vào thân thẻ qua hàm `_scene_text_lines()`.
- Chữ bị tràn hoặc cắt cụt (`truncate`), không thể đọc trọn vẹn nội dung.
- Các thẻ to chiếm hết diện tích, khiến đồ thị chỉ có hơn 20 node nhưng đã kéo dài màn hình, tạo cảm giác lộn xộn, rối mắt.

### Mô hình chuyển đổi sang Flowsint UX (Ảnh 1)

1. **Layout 3 Cột (3-Pane Grid)**:
   - **Left Pane (280px)**: `Entities Sidebar` - danh mục các thành phần trong đồ thị có thể lọc theo loại: Câu hỏi (1), Câu trả lời (1), Trích dẫn (N), Nguồn (M). Có ô tìm kiếm theo tên/nội dung.
   - **Center Pane (Flex Canvas)**: Canvas nền tối (`#0b0f19` / `#0f172a`), các node dạng **Pill badge**:
     - Kích thước nhỏ gọn (`height: 36px - 44px`).
     - Chỉ chứa: Icon loại node + Tên ngắn gọn (Ví dụ: `❓ Câu hỏi`, `💡 Câu trả lời`, `🏷️ [1]`, `📄 MOM_Interface.pdf`).
     - Tuyệt đối không nhét đoạn văn bản (snippet) lên mặt canvas.
   - **Right Pane (320px - 360px)**: `Inspector Panel` - hiển thị thông tin chuyên sâu của node đang được chọn:
     - Loại node & Tiêu đề đầy đủ.
     - Toàn bộ đoạn trích dẫn nguyên văn (Full snippet) trong khung cuộn đẹp mắt, có nút sao chép.
     - Đường dẫn tệp nguồn (Source file path).
     - Điểm số tin cậy (Confidence score).
     - Nút thao tác nhanh (Mở tệp / Xem ngữ cảnh).
2. **Tương tác Cross-Highlighting**:
   - Khi nhấp chọn trích dẫn `[k]`:
     - Canvas vẽ đường nối sáng màu nối từ Câu trả lời -> `[k]` -> File nguồn.
     - Cột trái tự động cuộn tới thực thể `[k]`.
     - Cột phải lập tức nạp thông tin trích dẫn `[k]`.

---

## 3. Kết Quả Deep Search Internet & Chuẩn Mực UX Đồ Thị Điều Tra Hiện Đại (Flowsint 2.0)

Dựa trên nghiên cứu sâu từ các nền tảng phân tích đồ thị tình báo hàng đầu thế giới (Flowsint, Palantir Foundry Graph, Maltego, Neo4j Bloom, Cytoscape):

### A. Hệ Thống Thẩm Mỹ Màu Sắc & Bề Mặt (Cyber-Intelligence Design System)

1. **Tránh màu đen thuần (#000000)**: Sử dụng tone xám sẫm sâu (`#070b14`, `#0b0f19`, `#0f172a`) để giảm độ chói mắt và tăng độ tương phản mềm mại.
2. **Lưới tọa độ kỹ thuật số (Subtle Tech Grid)**: Nền canvas kết hợp lưới chấm tròn mờ `radial-gradient(#1e293b 1px, transparent 1px)` hoặc lưới mờ 20px, tạo cảm giác buồng lái điều tra chuyên nghiệp (Ops Center).
3. **Phân tầng độ nổi (Surface Elevation)**:
   - Panel & Toolbar: `rgba(15, 23, 42, 0.85)` kết hợp hiệu ứng kính mờ `backdrop-filter: blur(12px)`.
   - Viền kim loại mờ: `1px solid rgba(56, 189, 248, 0.2)`.
   - Node dạng viên nang (Capsule/Pill) với gradient nhẹ `linear-gradient(145deg, #1e293b, #0f172a)` và bóng đổ viền phát sáng (neon glow aura).

### B. Điều Khiển Canvas Tương Tác Cấp Cao (Canvas Navigation Engine)

1. **Bộ công cụ nổi (Floating Canvas Toolbar)**:
   - `Zoom In (+)` và `Zoom Out (-)` mượt mà.
   - `Fit to View / Auto-Center (⊡)`: Tự động căn chỉnh toàn bộ đồ thị vào trung tâm màn hình.
   - `Fullscreen Toggle (⛶)`: Cho phép phóng to chiếm trọn màn hình khi cần soi chi tiết.
   - `Free Drag / Pan`: Cho phép kéo di chuyển canvas tự do bằng chuột không giới hạn.
2. **Đường cong Bezier & Hiệu ứng Dòng chảy Tri thức (Animated Flowing Edges)**:
   - Thay thế đường thẳng SVG thô bằng đường uốn lượn mềm mại (Smooth Bezier).
   - Khi hover hoặc chọn node: Kích hoạt đường nét đứt chuyển động (`stroke-dasharray` animated pulse) mô phỏng dòng dữ liệu được truyền từ nguồn đến câu trả lời.

### C. Bảng Kiểm Tra Thông Minh (Supercharged Inspector Panel)

1. **Collapsible Panel**: Nút thu gọn / mở rộng bảng kiểm tra để nhường 100% không gian cho Canvas khi cần.
2. **Confidence Gauge**: Thanh đo độ tin cậy đồ họa với mã màu (Xanh lá >80%, Vàng 50-80%, Đỏ <50%).
3. **Mạng quan hệ hai chiều (Inbound & Outbound Links)**: Liệt kê trực quan các liên kết liên quan kèm nút bấm chuyển tiêu điểm (Quick-focus jump).
