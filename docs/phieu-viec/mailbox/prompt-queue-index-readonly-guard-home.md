# VÉ: INDEX-READONLY-GUARD-HOME (khoá cứng chỉ đọc cho chỉ mục production ở đường giao diện)

- Mã vé: `INDEX-READONLY-GUARD-HOME`
- Role gợi ý: PLAN (đọc kỹ báo cáo truy nguyên trước) + DEFAULT khi code
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/index-readonly-guard-home.md`
- Căn cứ: báo cáo `index-hash-drift-trace-home.md` (đã verdict ĐẠT): đường "chuẩn bị nguồn" của giao diện ghi thẳng 27 mảnh vào chỉ mục production vì `_pipeline_config` mặc định `read_only=False` (không fail-closed) và `prepare_workspace_chat_sources` không truyền `read_only=True`. Vé này sửa điểm nối đó. Lệnh đóng băng đo app vẫn còn hiệu lực: vé này chỉ code + test đơn vị, KHÔNG chạy nghiệm thu trên app thật.

## Việc phải làm

1. **Fail-closed ở gốc:** sửa mặc định của `_pipeline_config` trong `workspace_chat_rag_v2_adapter.py` thành `read_only: bool = True`. Mọi điểm gọi thật sự cần ghi phải truyền `read_only=False` tường minh kèm comment lý do — liệt kê các điểm đó trong báo cáo (kiểm toàn bộ caller, không sửa mò).
2. **Chặn ghi vào kho production đã đóng dấu:** trong `prepare_workspace_chat_sources` và đường hàng đợi chuẩn bị (`_drain_preparation_queue_worker`): nếu cấu hình đích trỏ vào collection production `tri_thuc` (kho đã đóng dấu) thì chặn đứng bằng lỗi rõ ràng (raise exception có tên riêng, vd `ReadOnlyIndexViolationError`) và KHÔNG gọi worker chuẩn bị. Nguồn thuộc tài liệu đã có sẵn trong kho 889 tài liệu phải được nhận diện là đã sẵn sàng (ready) mà không cần qua pipeline chuẩn bị ghi.
3. **Test đơn vị bảo vệ (đỏ trước — xanh sau):**
   - `_pipeline_config` không truyền tham số → `index_read_only` là True.
   - Gọi prepare với nguồn thuộc collection production → bị chặn, không phát sinh lệnh prepare nào tới worker.
   - Đường truy vấn/hỏi đáp hiện hữu không đổi hành vi (chạy lại các test adapter liên quan).
4. **Cổng repo:** compileall, pytest các file liên quan (adapter, deployment, app), cli audit, import app — PASS. Tương thích Python 3.11.

## Rào cứng

- Không mở app chạy đo/nghiệm thu thật ở vé này (đóng băng còn hiệu lực tới khi chỉ mục được khôi phục và điều phối gỡ băng bằng ghi_chu riêng).
- Không đụng vào tệp chỉ mục production ngoài việc đọc cấu hình đường dẫn; không khôi phục chỉ mục ở vé này (việc khôi phục chờ quyết định riêng của user).
- Không merge `main`. Vé dài: mốc tối thiểu 15 phút/lần + checkpoint.
