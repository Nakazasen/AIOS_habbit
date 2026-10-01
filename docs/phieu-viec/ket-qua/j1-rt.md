# Vé `J1-RT` — JIG realtime: kết quả kiểm chứng trên máy nhà

- Trạng thái: **CHƯA ĐẠT; giữ `dang-lam` chờ Muse sửa các sai lệch hợp đồng.** Luồng phát lại cơ bản chạy được, nhưng API hiện có thể báo nhận đủ khi âm thầm bỏ dữ liệu, và còn các điểm không khớp đặc tả về JSON, xác thực, thử lại và tiếp tục cursor.
- Nhánh: `phieu-viec/rag-fix1`. Mã Muse kiểm: `3fd332c` (chuỗi `c2e99da` → `71d3500` → `3fd332c`); mốc ghi nhận OMP mới nhất trước báo cáo: `e37071b`.
- Máy: Windows 10 x64, Python 3.11.14. Đúng lane `[VM]`: OMP chỉ kiểm chứng, không sửa mã. CSV nguồn được đọc qua bản mirror cục bộ chỉ-đọc; mọi tệp phát sinh ở `C:/tmp/j1-rt-verify/`, không đưa dữ liệu hoặc SQLite vào repo, không đụng DB gốc, ổ D hay `main`.

## 1. Mốc 1 — test vé và nhóm liên quan

| Lệnh / phạm vi | Kết quả |
|---|---|
| `tests/test_j1_rt.py` từ repo, không có mirror CSV | **13 đạt / 3 bỏ qua**; các bài cần dữ liệu thật bỏ qua đúng do thiếu đường dẫn trên máy. |
| Cùng test vé, chạy bằng Python 3.11.14 từ `C:/tmp` với mirror CSV Iris cục bộ | **16/16 đạt**. |
| Nhóm hồi quy `test_stream_api.py`, `test_iris_any_log_and_archive.py`, `test_iris_log_intake.py`, `test_j1_csv.py` từ gốc repo | **99 đạt / 4 bỏ qua**. |

Một lượt nhóm hồi quy chạy nhầm `cwd=C:/tmp` làm lệch fixture tương đối; chạy lại từ gốc repo cho kết quả nêu trên. Không dùng kết quả lỗi do sai `cwd` làm kết luận về mã.

## 2. Mốc 2 — E2E phát lại qua HTTP

- Từ CSV JIG thật, lấy **60 dòng `SKEW:BLACK` theo thứ tự thời gian**; thêm **12 điểm đuôi mô phỏng** tính từ thống kê nền để kích hoạt drift. Không sửa nội dung 60 dòng nguồn. Gửi 72 bản tin qua `gui_lo_len_server` đến `StreamListener` cục bộ bằng Bearer token.
- Kết quả: **72/72 dòng được lưu**; `RtConsumer` nhận **2 sự kiện `canh_bao_drift`**; thẻ cảnh báo hiển thị nhãn `SIMULATED_REALTIME` bằng tiếng Việt. GET thiếu token trả **401**.
- SQLite giữ sự kiện sau khi khởi động lại listener. Lưu cursor `2` ra tệp scratch rồi khởi tạo consumer mới với cursor đó cho kết quả 0 sự kiện mới; consumer mặc định cursor `0` đọc lại 2 sự kiện. Như vậy kho sự kiện bền, còn việc lưu/khôi phục cursor hiện do bên gọi tự làm.
- Kiểm tra giới hạn: gửi **105** dòng trong một lô; server lưu **100** nhưng trả HTTP 200 với `so_dong=105`. Năm dòng bị bỏ mà bên gửi được xác nhận đã nhận đủ — **lỗi mất dữ liệu chặn ĐẠT**.
- Kiểm tra lỗi lô: lô có dòng hợp lệ trước rồi đến dòng không hợp lệ trả **400**, nhưng dòng hợp lệ đứng trước đã được ghi SQLite. Đây là ghi một phần trên phản hồi lỗi; gửi lại lô có thể ghi trùng.
- Kiểm tra JSON: object `application/json` được định dạng nhiều dòng (pretty JSON) trả **400**, dù đặc tả cho phép một object JSON. Bộ phân nhánh hiện coi mọi newline là NDJSON.

## 3. Đối chiếu hợp đồng đặc tả ↔ mã

| Hợp đồng | Chứng cứ | Kết luận |
|---|---|---|
| JSON object, array hoặc NDJSON hợp lệ | `j1-rt-api-spec.md` mục 1 cho phép cả ba; `stream_api.py` chọn NDJSON chỉ vì body có newline. Pretty JSON một object đã thử và bị 400. | Sai định dạng hợp lệ; cần sửa trước ĐẠT. |
| Tối đa 100 dòng/lô, phần thừa bị cắt | Đặc tả mô tả cắt phần thừa; mã chỉ append `records[:100]` nhưng phản hồi `so_dong=len(records)`. Probe 105 dòng xác nhận 100 lưu, 105 báo nhận. | Mất dữ liệu và ACK sai; blocker. |
| Lỗi 400 không tạo trạng thái nhập khó đoán | Probe lô trộn hợp lệ/sai trả 400 sau khi dòng hợp lệ đầu tiên đã commit. Đặc tả chưa nêu rõ tính nguyên tử của lô; đây là rủi ro toàn vẹn dữ liệu cần Muse quyết và xử lý. | Ghi một phần; gửi lại có thể trùng. |
| Token riêng từng JIG | Đặc tả mục 1 và checklist hạ tầng yêu cầu token riêng; `StreamListener` chỉ có một `auth_token` dùng chung cho listener. | Chưa đáp ứng phân quyền theo JIG. |
| Replay sender thử lại lỗi mạng/timeout theo backoff | Đặc tả mục 1 yêu cầu tối đa 3 lần; `_gui_mot_lo` đổi lỗi mạng/timeout thành `ValueError` ngay, không thử lại. | Thiếu cơ chế retry của sender. |
| Consumer tiếp tục từ cursor đã lưu | Đặc tả mục 2 yêu cầu resume từ cursor cuối đã lưu; `RtConsumer.cursor` chỉ là trường RAM, không có lưu bền trong consumer. Consumer có retry backoff và chỉ tiến cursor sau khi xử lý hết lô sự kiện. | Cần bên gọi tự lưu/khôi phục; chưa có hợp đồng lưu cursor bền ở consumer. |

Các điểm khớp đã kiểm: sự kiện được lưu SQLite và còn sau khi listener khởi động lại; truy vấn sự kiện giữ thứ tự cursor và giới hạn `limit` tối đa 500; consumer có retry lỗi poll; dòng phát lại được gắn nhãn `SIMULATED_REALTIME`. Checklist hạ tầng nêu rõ máy chủ, LAN, agent trên JIG, token, vận hành và thứ tự triển khai. Triển khai hạ tầng thật thuộc vé khác theo phạm vi vé.

## 4. Mốc 3 — cổng nền và full suite

- `uv run --no-sync --group dev python -m compileall -q src tests` → **EXIT=0**.
- `uv run --no-sync --group dev python scripts/check_docs.py` → **DOCUMENTATION_CONTRACT=PASS**.
- CLI audit với `PYTHONPATH=src` → **`status: PASS`**, không lỗi/cảnh báo; import `aios_habit.workspace_chat_app` với cùng `PYTHONPATH` → **OK**. Lệnh không đặt `PYTHONPATH` ban đầu không tìm thấy package theo bố cục `src`; chạy lại đúng đường dẫn đã đạt.
- `uv run --no-sync --group dev pytest -q` → **3.564 đạt / 36 bỏ qua / 37 lỗi / 19 error**, exit 1, 561,88 giây. Log: `C:/tmp/j1-rt-verify/pytest_full_j1rt.log`.
- Lượt full suite này không đặt `AIOS_DATA_DIR` hoặc `AIOS_B5_WORKBOOK`; khác môi trường báo cáo J1-CSV (**3.581/6/26/9**), vì vậy không kết luận tăng/giảm hồi quy theo phép trừ số lượng. Các lỗi hiện tại gồm thiếu fixture dữ liệu cục bộ, Graphify không có trong môi trường, không có kết nối mạng/provider, lỗi tiến trình BGE và một số kiểm thử CLI/lock/quyền riêng tư. Nhóm vé J1-RT và nhóm hồi quy liên quan đã đạt độc lập ở Mốc 1.
- `git diff --check` và `git diff --cached --check` sạch trước commit Mốc 3. Lượt `git status --short --ignored` báo cảnh báo quyền truy cập ở một số thư mục ignored; không stage dữ liệu ignored.

## 5. Đối chiếu tiêu chí vé

- [x] Có tài liệu đặc tả endpoint, định dạng, tần suất, xác thực, retry, cursor, drift và giới hạn.
- [x] Prototype phát lại CSV thật theo thời gian, đi qua HTTP và consumer; nhãn mô phỏng được giữ rõ.
- [x] Có danh sách yêu cầu hạ tầng phía công ty; triển khai thật được xác định ngoài phạm vi vé.
- [ ] **Chưa đạt tổng thể:** triển khai không tuân thủ một số hợp đồng trong chính đặc tả; đặc biệt ACK sai làm mất 5/105 dòng, JSON hợp lệ bị từ chối, xác thực chưa tách token từng JIG, sender thiếu retry, cursor không được lưu bền. Cần Muse sửa trên lane `[VM]`, sau đó OMP chạy lại probe giới hạn, JSON, lô lỗi, token, retry/cursor và test vé trước khi chuyển trạng thái.

## 6. Bằng chứng cục bộ

Các bản CSV thử, SQLite, cursor và log nằm ngoài repo trong `C:/tmp/j1-rt-verify/`. Không đưa dữ liệu CSV, nội dung đo hoặc DB vào commit. Commit OMP chỉ cập nhật báo cáo và mailbox; không sửa mã vé.
