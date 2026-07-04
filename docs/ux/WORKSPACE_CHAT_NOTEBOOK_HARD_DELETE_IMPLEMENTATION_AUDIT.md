# WORKSPACE_CHAT_NOTEBOOK_HARD_DELETE_IMPLEMENTATION_AUDIT

## 1. Tổng quan (Overview)
Tài liệu này ghi nhận kết quả kiểm tra chất lượng (audit), thiết kế kiến trúc và quá trình triển khai sửa đổi tính năng **Xóa vĩnh viễn sổ tài liệu (Workspace Chat Notebook Hard Delete)** với cơ chế Cascade Delete và Danger Zone UI.

- **Baseline Git Commit**: `ddff554bb6b3ecec18afea7cc9d86670d5a8b076`
- **Nhánh triển khai (Branch)**: `main`
- **Ngôn ngữ người dùng**: Tiếng Việt (Vietnamese)

---

## 2. Hợp đồng Cascade Delete (Cascade Delete Contract)
Hành động xóa vĩnh viễn sổ tài liệu (`DocumentNotebook`) phải xóa hoàn toàn và vĩnh viễn các bản ghi con liên kết trực tiếp và gián tiếp sau đây:
1. Bản ghi Sổ tài liệu (`DocumentNotebook`)
2. Tất cả các Cuộc trò chuyện (`WorkspaceConversation`) thuộc sổ tài liệu đó.
3. Tất cả các Tin nhắn (`ChatMessage`) thuộc các cuộc trò chuyện trên.
4. Tất cả các Nguồn sổ tài liệu (`NotebookSource`) thuộc sổ tài liệu đó.
5. Tất cả các Nguồn cuộc trò chuyện tạm thời (`TemporaryConversationSource`) thuộc các cuộc trò chuyện trên.
6. Tất cả các Lựa chọn nguồn trò chuyện (`ConversationSourceSelection`) thuộc các cuộc trò chuyện trên.

### Bảo toàn dữ liệu không liên quan (Unrelated Data Preservation)
Dữ liệu của bất kỳ sổ tài liệu nào khác không thuộc mục tiêu xóa (bao gồm cả các cuộc trò chuyện, tin nhắn, nguồn và trạng thái bật/tắt nguồn của chúng) được đảm bảo giữ nguyên vẹn 100% không bị thay đổi.

### Hành vi khi thiếu sổ tài liệu (Missing Notebook Behavior)
Nếu gọi xóa sổ tài liệu với một `notebook_id` không tồn tại, hàm sẽ trả về `False` ngay lập tức và đảm bảo không chạm, tạo mới, ghi đè hoặc thay đổi bất kỳ tập tin dữ liệu nào trong store.

---

## 3. Cơ chế xử lý lỗi và Atomicity (Failure Handling & Atomicity)
Do hệ thống sử dụng các tập tin JSONL riêng biệt để lưu trữ các thực thể, hệ thống không đảm bảo tính giao dịch nguyên tử đa tập tin hoàn toàn (multi-file transactional atomicity). Để tối thiểu hóa rủi ro và tăng cường độ tin cậy, quy trình thay thế nguyên tử trên từng tập tin đơn lẻ (per-file atomic replacement) và khôi phục nỗ lực tốt nhất (best-effort rollback) được áp dụng:

1. **Chuẩn bị và Ghi file tạm (`.tmp`)**: Toàn bộ nội dung mới sau khi lọc bỏ dữ liệu cần xóa sẽ được chuẩn bị và ghi vào các file tạm tương ứng (ví dụ `notebooks.tmp`). Nếu bất kỳ lỗi nào xảy ra trong giai đoạn này (bao gồm cả lỗi xảy ra trong quá trình gọi `.write()` sau khi mở tệp thành công), tất cả các file tạm đã tạo sẽ bị xóa và các file gốc được bảo toàn nguyên vẹn 100% trên đĩa.
2. **Sao lưu bằng cách sao chép (Backup copies)**: Hệ thống tạo bản sao lưu `.bak` bằng cách sao chép (`shutil.copy2()`), giữ nguyên file gốc tại vị trí của nó. File gốc luôn tồn tại liên tục, tránh tạo ra khoảng trống không tồn tại (target-missing gap) trước thời điểm thay thế thực sự.
3. **Thay thế nguyên tử (`os.replace`)**: File gốc được thay thế trực tiếp và nguyên tử bằng file tạm bằng cách gọi `os.replace()`.
4. **Nỗ lực khôi phục tốt nhất (Best-effort Rollback)**: Nếu quá trình thay thế gặp lỗi tại bất kỳ file nào sau khi đã thay thế thành công các file trước đó, hệ thống sẽ dừng lại ngay lập tức, trả về `False` (không báo cáo thành công giả) và tự động khôi phục lại trạng thái ban đầu của các file đã thay thế từ các file `.bak` sao lưu.

### Các rủi ro và khoảng trống đã biết (Known Risks & Gaps)
- **Không phải database transaction thực sự**: Rollback chỉ là nỗ lực tốt nhất (best-effort). Việc mất nguồn điện (power loss) hoặc lỗi phần cứng nghiêm trọng lúc đang replace/rollback có thể dẫn đến trạng thái dữ liệu không nhất quán.
- **Rủi ro ghi đồng thời (Concurrency Risk)**: MVP giả định là ứng dụng single-owner local chạy đơn tiến trình, không tích hợp cơ chế khóa ghi (concurrent writer lock). Nếu có tiến trình ghi đồng thời khác ghi đè vào các file JSONL trong lúc đang xóa, quá trình rollback có thể ghi đè làm mất đi thay đổi đồng thời đó.
- **Lỗi dọn dẹp file tạm (Cleanup failure)**: Có rủi ro nhỏ nếu việc dọn dẹp các file `.tmp` hoặc `.bak` bị thất bại (ví dụ do lỗi phân quyền của hệ điều hành), để lại các file rác trên đĩa cứng (dù không làm hỏng dữ liệu chính).

---

## 4. Danh sách các File được chỉnh sửa (Modified Files)

### A. Mã nguồn ứng dụng (App Sources)
1. **[src/aios_habit/workspace_chat_store.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_store.py)**
   - Triển khai hàm `delete_notebook_permanently(notebook_id: str) -> bool` sử dụng `shutil.copy2` để backup, `os.replace` để thay thế nguyên tử và dọn dẹp/rollback khi có sự cố.
2. **[src/aios_habit/workspace_chat_ui.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_ui.py)**
   - Tích hợp **Vùng nguy hiểm (Danger Zone)** và các widget xác nhận xóa.
3. **[src/aios_habit/workspace_chat_app.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_app.py)**
   - Quản lý callbacks, dọn dẹp active session và trạng thái widget (`_clear_delete_notebook_confirmation_state`).

### B. Bộ kiểm thử (Test Suites)
1. **[tests/test_workspace_chat_store.py](file:///D:/Sandbox/AIOS_habbit/tests/test_workspace_chat_store.py)**
   - `test_delete_notebook_permanently_missing`: So sánh byte-by-byte cả 6 file lưu trữ để chứng minh không bị chạm vào.
   - `test_delete_notebook_permanently_temp_write_failure`: Sử dụng `FaultyFileWrapper` để kiểm thử lỗi ghi dở dang sau khi file tạm đã được tạo/mở thành công, verify việc dọn dẹp toàn bộ file `.tmp` dở dang.
   - `test_delete_notebook_permanently_failure_rollback`: Kiểm thử khôi phục byte-by-byte khi gặp lỗi thay thế giữa chừng và dọn dẹp các file `.tmp`/`.bak`.
   - `test_delete_notebook_permanently_no_target_gap`: Kiểm thử happy path không bao giờ sử dụng `unlink` hay `rename` trên file gốc trước thay thế.
2. **[tests/test_workspace_chat_ui_copy.py](file:///D:/Sandbox/AIOS_habbit/tests/test_workspace_chat_ui_copy.py)**
   - `test_hard_delete_required_copy`: Kiểm thử nhãn tiếng Việt và chặn rò rỉ jargon kỹ thuật hướng tới user.
3. **[tests/test_workspace_chat_source_selection_owner_flow.py](file:///D:/Sandbox/AIOS_habbit/tests/test_workspace_chat_source_selection_owner_flow.py)**
    - `test_app_hard_delete_behavioral_flows`: Kiểm thử wrong-title spy (không gọi helper, dọn dẹp widget), exact-title spy (gọi đúng 1 lần, dọn dẹp active session/widgets), archived delete flow, dọn dẹp trạng thái cancel, verify delete không gọi AI answer path và không tạo assistant message. Đảm bảo patch đúng namespace của `app`. Sử dụng so sánh snapshot đầy đủ `(id, conversation_id, role, content)` (đã sort) để chứng minh tin nhắn không liên quan được bảo toàn tuyệt đối cả về số lượng, vai trò và nội dung.
    - `test_app_hard_delete_helper_failure_behavioral_flow`: Kiểm thử khi helper `delete_notebook_permanently` trả `False` (giữ nguyên session active, hiển thị thông báo lỗi tiếng Việt, dọn dẹp widget/pending states, không gọi AI answer, bảo toàn messages). Sử dụng so sánh snapshot đầy đủ `(id, conversation_id, role, content)` (đã sort) để chứng minh tin nhắn hiện tại của notebook đang xóa dở dang được bảo toàn nguyên vẹn 100% cả về số lượng, vai trò và nội dung khi quá trình xóa thất bại.

---

## 5. Kết quả Xác thực (Verification & Test Results)

### Kiểm thử tự động (Automated Tests)
Toàn bộ hệ thống kiểm thử gồm **707 test cases** đã được chạy thành công mà không có lỗi:
```bash
py -3 -m pytest tests/
```
**Kết quả**: `707 passed`

### Lệnh Audit CLI
```bash
py -3 -m aios_habit.cli audit
```
**Kết quả**:
```json
{
  "errors": [],
  "status": "PASS",
  "warnings": []
}
```

### Git Check Whitespace
```bash
git diff --check
```
**Kết quả**: Không có lỗi khoảng trắng cuối dòng (trailing whitespace).

---

## 6. Quy trình Kiểm thử thủ công (Manual Verification Flow)
Khi chạy ứng dụng Streamlit:
1. **Yêu cầu xóa**: Bấm nút **"Xóa vĩnh viễn sổ"** tại vùng nguy hiểm.
2. **Giao diện xác nhận**:
   - Nhập chính xác tên sổ vào ô nhập liệu *"Nhập chính xác tên sổ để xác nhận xóa"*.
   - Chọn checkbox *"Tôi hiểu dữ liệu sẽ bị xóa vĩnh viễn"*.
   - Nút *"Xác nhận xóa vĩnh viễn"* sáng lên để bấm.
3. **Huỷ bỏ / Nhập sai**: Nếu bấm "Hủy" hoặc nhập sai tiêu đề, toàn bộ trạng thái chữ và checkbox đã nhập sẽ được dọn dẹp sạch sẽ khỏi session, tránh việc hiển thị lại khi mở lại hộp thoại.
4. **Xác nhận xóa**: Nhấn nút xác nhận để xóa vĩnh viễn sổ và toàn bộ dữ liệu liên đới.

PASS_READY_FOR_CODEX_AUDIT
