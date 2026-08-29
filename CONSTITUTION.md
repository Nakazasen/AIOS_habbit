# Hiến chương AIOS Habit

## 1. Sứ mệnh

AIOS Habit tồn tại để bảo toàn **tri thức vận hành cá nhân** của người dùng dưới dạng có thể kiểm định, có thể kế thừa và không phụ thuộc vào một AI cụ thể.

Nền tảng này giúp tái tạo cách người dùng làm việc trên nhiều hệ AI khác nhau bằng cách lưu giữ:

- Cách người dùng ưu tiên công việc.
- Cách người dùng ra quyết định.
- Cách người dùng giao tiếp.
- Cách người dùng tổ chức tri thức.
- Workflow lặp lại.
- Tri thức dự án đã được kiểm chứng.

## 2. AIOS Habit không phải là gì

AIOS Habit **không phải**:

- Công cụ backup ChatGPT.
- Kho lưu toàn bộ lịch sử chat.
- Công cụ sao chép tài khoản AI.
- Hệ thống giám sát người dùng.
- Nơi lưu suy đoán không có bằng chứng.

## 3. Nguyên tắc tối cao

### Nguyên tắc 1: Không lưu hội thoại, lưu tri thức

Hội thoại thô chỉ là nguồn tạm để trích xuất. Bộ nhớ cuối cùng phải là tri thức đã được phân loại, tóm tắt và gắn bằng chứng.

### Nguyên tắc 2: Không lưu câu chữ, lưu quy luật

Hệ thống không tối ưu cho việc nhớ từng câu. Hệ thống tối ưu cho việc nhớ quy luật, sở thích, hành vi, quy trình và tiêu chuẩn đánh giá.

### Nguyên tắc 3: Không lưu suy đoán, chỉ lưu bằng chứng

Mọi đơn vị bộ nhớ phải có ít nhất một bản ghi bằng chứng. Nếu chưa có bằng chứng, trạng thái phải là `candidate` và không được dùng như sự thật.

### Nguyên tắc 4: AI phải thay được, tri thức không được mất

Không định dạng dữ liệu theo riêng một AI. Mọi bộ nhớ lõi phải dùng Markdown, JSON hoặc YAML mở, có schema rõ ràng.

### Nguyên tắc 5: Ưu tiên cục bộ (local-first)

Dữ liệu gốc thuộc người dùng. Mặc định lưu cục bộ. Không đồng bộ ra mây nếu chưa có chính sách rõ ràng.

### Nguyên tắc 6: Tài liệu người đọc phải tiếng Việt

Mọi câu văn trong tài liệu sản phẩm (README, hiến chương, quy tắc agent, kiến trúc, roadmap, spec đang mở, sổ thảo luận) viết tiếng Việt. Cấm tiêu đề và đoạn văn tiếng Anh. Chỉ được giữ token tiếng Anh khi là đường dẫn, lệnh, tên mã, nhãn máy (`Status:`, `PASS`) hoặc hằng (`local_only`) — và phải giải thích tiếng Việt bên cạnh. Luật chi tiết: `AGENT_RULES.md` mục 4.

## 4. Quy tắc bắt buộc khi phát triển

1. Audit trước khi fix.
2. Thiết kế trước khi code.
3. Phase hiện tại phải được đóng trước khi mở phase tiếp theo.
4. Mọi thay đổi kiến trúc phải cập nhật `ARCHITECTURE.md`.
5. Mọi thay đổi roadmap phải cập nhật `ROADMAP.md`.
6. Mọi thay đổi hành vi hệ thống phải cập nhật `PROJECT_HANDOVER.md`.
7. Mọi bộ nhớ mới phải có bằng chứng hoặc được đánh dấu `candidate`.
8. Không gộp dữ liệu thô chưa phân loại vào kho bộ nhớ.
9. Không dùng đầu ra AI như bằng chứng nếu không có nguồn gốc kèm theo.
10. Không tự ý kết luận khi chưa đủ dữ liệu.

## 5. Định nghĩa PASS/FAIL

Một hạng mục chỉ được đánh dấu `PASS` khi:

- Có evidence hoặc artifact cụ thể.
- Có người/AI reviewer xác nhận.
- Có rollback hoặc cách sửa nếu phát hiện sai.
- Có trạng thái được ghi lại trong changelog hoặc handover.

Nếu thiếu một trong các điều trên, trạng thái phải là `FAIL`, `BLOCKED` hoặc `PARTIAL`, không được ghi `PASS`.

## 6. Chính sách dữ liệu thô

Bản ghi chat thô, email, log cá nhân, tài liệu nhạy cảm không được đưa thẳng vào kho bộ nhớ.

Quy trình đúng:

```text
Nguồn thô → Bản ghi bằng chứng → Quy luật đã trích → Bộ nhớ đã xác thực → Gói xuất
```

## 7. Chính sách chống khóa nhà cung cấp AI

Mọi đầu ra dài hạn phải tồn tại được ngoài ChatGPT, Gemini, Claude, Grok. Không được phụ thuộc vào:

- Bộ nhớ nội bộ của một AI.
- Định dạng prompt độc quyền không có bản Markdown tương đương.
- Lịch sử hội thoại không xuất được.

## 8. Thứ tự ưu tiên khi xung đột

1. An toàn dữ liệu người dùng.
2. Bằng chứng và tính đúng đắn.
3. Khả năng kế thừa dài hạn.
4. Tính mở rộng.
5. Tốc độ triển khai.

Tốc độ không được vượt lên trên bằng chứng hoặc an toàn dữ liệu.

## 9. Tài liệu liên quan (không thay file này)

- Lối vào agent (L0): `AGENTS.md`
- Định vị sản phẩm / giai đoạn / “AIOS không phải”: `docs/AIOS_PRODUCT_POSITIONING.md`
- Phân loại dữ liệu local-first: `00_governance/DATA_POLICY.md`
- Kiến trúc: `ARCHITECTURE.md`
- Trạng thái chuyển giao: `ROADMAP.md`, `PROJECT_HANDOVER.md`

