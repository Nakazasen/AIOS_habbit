# Vé `J1-RT` — JIG realtime: kết quả kiểm chứng trên máy nhà

- Trạng thái: **CHƯA ĐẠT; kiểm lại thấy lỗ hổng xác thực với JIG chưa cấu hình.** Bộ test vé 24/24 và các cổng biên dịch/audit/import đạt, nhưng mã token hợp lệ vẫn ghi được bản tin cho `jig_id` không có trong cấu hình; chờ Muse sửa trên lane `[VM]` và OMP kiểm lại.
- Nhánh: `phieu-viec/rag-fix1`. Mã Muse kiểm lại: `f02a9e9` + `edf6f23`; mốc báo cáo OMP trước lượt kiểm này: `ef45353`.
- Máy: Windows 10 x64, Python 3.11.14. Đúng lane `[VM]`: OMP chỉ kiểm chứng, không sửa mã. CSV nguồn được đọc qua bản mirror cục bộ chỉ-đọc; mọi tệp phát sinh ở `C:/tmp/j1-rt-verify/`, không đưa dữ liệu hoặc SQLite vào repo, không đụng DB gốc, ổ D hay `main`.

## Mốc kiểm lại sau bản sửa Muse

- Mã Muse được kiểm: `f02a9e9` + `edf6f23`; đã `git pull --rebase origin phieu-viec/rag-fix1` trước khi chạy. Máy Windows 10 x64, Python 3.11.14. Chạy từ `C:/tmp` để kiểm thử dùng đúng mirror CSV cục bộ tại `C:/home/hatch/workspace/aios_data/lsu/Iris LSU/thu nghiem 6pcs do thong so va log/2ND-1035/IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv`; `PYTHONPATH` trỏ tới `D:/Sandbox/AIOS_habbit/src`.
- Lệnh `uv run --project D:/Sandbox/AIOS_habbit --no-sync --group dev python -m pytest -q D:/Sandbox/AIOS_habbit/tests/test_j1_rt.py` → **24 passed in 12.11s**.
- Sáu nhóm probe hồi quy trong bộ trên đều đạt: (1) lô 105 dòng → lưu/ACK 100, báo cắt 5; (2) JSON object/mảng pretty-print và NDJSON được nhận; (3) lô có dòng sai trả 400, không ghi một phần; (4) gửi lại lô không tạo dòng trùng; (5) token POST theo từng JIG, token khác/thiếu/sai bị từ chối cho JIG đã cấu hình; (6) sender thử lại với backoff, báo lỗi tiếng Việt khi hết lượt và consumer khôi phục cursor từ tệp sau restart. Các nhóm (3), (4), (6) có nhiều test riêng; toàn bộ test vé chạy trong lệnh nêu trên.
- Cổng nền: `uv run --no-sync --group dev python -m compileall -q src tests` chạy xong; `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit` → `status: PASS`, không lỗi/cảnh báo; import `aios_habit.workspace_chat_app` → `IMPORT=OK`. Full suite `uv run --no-sync --group dev pytest -q` đã bắt đầu; kết quả sẽ ghi bổ sung sau khi tiến trình hoàn tất.

### Blocker xác thực mới

- Đặc tả mục 1 yêu cầu mỗi JIG có Bearer token riêng; thiếu/sai token phải trả 401. Probe HTTP độc lập cấu hình `StreamListener(auth_token=None, jig_tokens={"J-A": "token-a", "J-B": "token-b"})`, rồi gửi `jig_id="J-UNKNOWN"` bằng `Bearer token-a`: máy chủ trả **HTTP 200**, `so_dong=1`; SQLite ghi **1** dòng của JIG chưa cấu hình.
- Nguyên nhân: `_token_cho_jig()` trả `None` cho JIG không nằm trong map; `_kiem_tra_auth_post()` bỏ qua kiểm tra khi token yêu cầu là `None`. Test mới chỉ thử dùng nhầm token của J-B để gửi cho J-A, chưa thử JIG không có khóa cấu hình.
- Chưa sửa mã theo ranh giới lane `[VM]`. Muse cần xử lý trường hợp JIG chưa cấu hình và thêm kiểm thử từ chối; sau commit OMP chạy lại probe này cùng test vé. Giữ `dang-lam`; chưa báo đạt.

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
