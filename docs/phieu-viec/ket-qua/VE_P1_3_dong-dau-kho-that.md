# Báo cáo Vé P1.3 — Đóng dấu kho production

## Kết quả

**CHƯA ĐẠT nghiệm thu.** Đã sao lưu kho production cũ trên D sang C, chép canary lên production đúng một lần và xác minh kích thước, SHA-256, `quick_check`. Chưa chạy B1–B5 nên chưa đóng dấu kho.

## Máy và phạm vi

- Máy: `h410asrock`.
- Nhánh: `phieu-viec/rag-fix1`.
- Mã nhánh trước commit báo cáo: `541dabc`.
- Thời điểm: 2026-09-28, khoảng 05:43–06:30 giờ `+07`.
- Không sửa mã, kiểm thử, manifest hoặc `.env`; không ghi vào ổ D ngoài lần chép production duy nhất.
- App được mở từ mã nguồn hiện tại với trạng thái người dùng tạm thời trên C; thư mục thử nghiệm đã gỡ bỏ. Không đưa dữ liệu thư viện hoặc câu trả lời vào báo cáo.

## 1. Sao lưu kho production cũ

Tệp cũ trên D:

`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`

Bản sao lưu trên C:

`C:\AIOS_backup_production_2026-09-28\library.sqlite.backup`

| Tệp | Kích thước (byte) | SHA-256 | `quick_check` |
| --- | ---: | --- | --- |
| Production cũ trên D, trước khi thay | 32452608 | `eedf4bf28dcaf5a871a1f632ab28286dff3296c6d1a57ff11e11cda781ed9c32` | `ok` |
| Bản sao lưu trên C | 32452608 | `eedf4bf28dcaf5a871a1f632ab28286dff3296c6d1a57ff11e11cda781ed9c32` | `ok` |

## 2. Canary và chép production

- Nguồn canary: `C:\AIOS_habit_index_ve03\library.sqlite`.
- Đích production: `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
- Nguồn: 2552659968 byte; SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`; `quick_check=ok`.
- Đích sau chép: 2552659968 byte; SHA-256 `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`; `quick_check=ok`.
- SHA-256 nguồn và đích khớp hoàn toàn.
- Lần chép duy nhất: 2026-09-28 05:54:18–05:55:03 giờ `+07`, 44,67 giây; không có lỗi I/O trên D.
- `quick_check` đích hoàn tất trong 1043,5 giây; không có lỗi I/O.

SHA-256 tệp SQLite ở đây là dấu băm toàn bộ tệp; không đồng nhất với fingerprint vector ONNX trong báo cáo P1 trước.

## 3. Kiểm tra app

Đã mở Workspace Chat tại `http://127.0.0.1:8765` bằng mã nguồn nhánh hiện tại. App phân giải manifest activated tới:

```text
runtime_root: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production
requested_profile: bge_m3_hybrid
library: D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite
exists: True
```

App hiển thị đúng giao diện tiếng Việt và trạng thái cầu nối Gemini Web trực tiếp sẵn sàng. Trạng thái cô lập trên C không có nguồn tài liệu trong sổ thử nghiệm, nên không có bộ nguồn để chạy truy vấn B1–B5 qua app.

## 4. B1–B5 và lý do dừng

- B1: chưa chạy; không có kết quả hoặc thời gian.
- B2: chưa chạy; không có kết quả hoặc thời gian.
- B3: chưa chạy; không có kết quả hoặc thời gian.
- B4: chưa chạy; tiếp tục loại khỏi chấm đúng/sai theo kế hoạch; không có kết quả hoặc thời gian.
- B5: chưa chạy; không có kết quả hoặc thời gian.
- Backend ONNX trong truy vấn app: chưa xác minh bằng một lượt hỏi đáp.

Không gửi câu hỏi vì giao diện báo cầu nối Gemini Web đang trực tiếp sẵn sàng; luồng app dựng ngữ cảnh từ bằng chứng rồi gọi cầu nối. Kho được truy vấn có nhãn dữ liệu chỉ dùng cục bộ; quy tắc dữ liệu cấm đưa dữ liệu này tới Gemini Web hoặc Nakazasen Router. C-AGENT cũng chỉ được dùng khi người dùng chọn đúng cầu nối đó. Không có lựa chọn cầu nối an toàn nào được chỉ định trong vé. Do đó không chạy B1–B5 để tránh phát tán dữ liệu hoặc tự ý chọn nhà cung cấp.

Cổng nghiệm thu yêu cầu B1/B2/B3/B5 đúng và toàn bộ B1–B5 chạy không lỗi; hiện thiếu bằng chứng nên không ghi PASS/ĐẠT.

## 5. Việc còn lại và rủi ro

- Cần một tuyến chạy B1–B5 được người dùng cho phép rõ ràng và không gửi dữ liệu `local_only` tới bên ngoài; sau đó mới có thể hoàn tất báo cáo và đóng vé.
- Production hiện vẫn nằm trên ổ D đã được cảnh báo hỏng dần. Việc di chuyển sang C và cập nhật manifest cần vé riêng; không thực hiện trong P1.3.
- Không chạy `compileall`, `pytest` hoặc audit vì không sửa mã; không chạy thêm thao tác có thể ghi lên D ngoài ngoại lệ một lần của vé.
