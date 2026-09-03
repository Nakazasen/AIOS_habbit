# Hướng dẫn kiểm chứng đợt đang thực thi

Tài liệu này chỉ hướng dẫn nghiệm thu Đợt 0 và Đợt 1. Dữ liệu thật phải nằm trong vùng cục bộ được phép và không được commit.

## 1. Ghi baseline

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
```

Ghi lại thay đổi cục bộ cần bảo toàn. Không dùng số test hoặc commit cũ làm bằng chứng hiện tại.

## 2. Kiểm tra tập trung phần nền

```powershell
py -3 -m pytest -q tests/test_workspace_case_migrations.py tests/test_workspace_case_store.py tests/test_workspace_case_authorization.py tests/test_workspace_case_service.py tests/test_workspace_case_ui.py
py -3 -m pytest -q tests/test_workspace_chat_rag_v2_adapter.py
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
```

Nếu tên file test chuẩn bị nguồn đã thay đổi, chọn đúng các test chứa `source_preparation`, `preparation_summary`, `pending_question` và progress; ghi rõ danh sách thực chạy.

## 3. Smoke trình duyệt Đợt 0

### Chuẩn bị nguồn

1. Mở Workspace Chat với thư viện có nguồn chưa sẵn sàng.
2. Xác minh giao diện nói rõ chưa thể tìm kiếm đầy đủ, hiển thị phần trăm và số nguồn đã xong/đang chờ/gặp lỗi.
3. Xác minh không có tên engine/model nội bộ trong nhãn, lỗi hoặc cảnh báo.
4. Dừng/khởi động lại ứng dụng; tiến độ phải tiếp tục hoặc có nút “Tiếp tục chuẩn bị”, không đứng im mà không hướng dẫn.
5. Với một nguồn lỗi, nút “Thử lại” phải hoạt động và lỗi hiển thị bằng tiếng Việt, không có traceback.

### Hồ sơ vụ việc

1. Từ câu trả lời có citation, lưu vào hồ sơ.
2. Mở mục “Hồ sơ vụ việc”, lọc và chọn case trong tối đa ba thao tác.
3. Đổi trạng thái, ghi kết luận và mở trace gốc.
4. Khởi động lại ứng dụng; trạng thái và kết luận phải đọc lại đúng.
5. Với trace/evidence fixture bị thiếu, UI phải báo thiếu bằng chứng thay vì dựng lại nội dung.

## 4. Xác nhận tối thiểu trong case

1. Người được giao điều tra và có đúng scope xác nhận hoặc bác bỏ một manh mối, kèm lý do.
2. Thử thiếu lý do, sai scope, scope hết hạn hoặc sai digest; service phải từ chối.
3. Nếu có người theo dõi công đoạn thứ hai, tạo yêu cầu riêng và giữ cả hai phản hồi.
4. Khởi động lại; review cũ vẫn còn và không có thao tác sửa/xóa phá hủy.
5. Xác minh AI không có role/scope phê duyệt.

## 5. Pilot C-call hoặc Jam

1. Chọn một bộ log được phép, SOP, danh mục mã lỗi và mapping có phiên bản.
2. Ingest log vào `line_events.sqlite`; ghi source digest, collector version và timezone Việt Nam.
3. Tạo case điều tra, gắn event khớp và dựng timeline.
4. Truy vấn không khớp phải trả rỗng, không lấy các event gần nhất làm bằng chứng.
5. Người phụ trách xác nhận relevance của manh mối; mapping chưa duyệt không được hiển thị.
6. Ghi kết luận/outcome và tạo bản nháp báo cáo điều tra hoặc SOP.
7. Người có thẩm quyền xem, sửa và duyệt; mọi sửa đổi sau duyệt phải tạo version mới.

Pilot chỉ đạt khi có một case thật đi trọn vòng. Thiếu dữ liệu hoặc người xác nhận được ghi `BLOCKED`, không thay bằng fixture để đóng pilot.

## 6. Kiểm tra an toàn artifact

1. Thử tạo nháp khi không có evidence; phải bị chặn.
2. Thử ghi đè file nguồn hoặc ghi ngoài output root; phải bị chặn.
3. Tạo báo cáo/SOP mới, xem trước, duyệt rồi đọc lại provenance và version.
4. Xác minh không có dữ liệu thô, đường dẫn hệ thống hoặc secret trong UI/báo cáo đã làm sạch.

## 7. Đóng một đợt

Chỉ chạy bộ đầy đủ khi chuẩn bị hợp nhất, phát hành hoặc đánh dấu đợt hoàn tất:

```powershell
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
py -3 scripts/check_docs.py
git diff --check
git diff --cached --check
```

Ghi commit, nhánh, lệnh, exit code, số test và phần chưa kiểm chứng vào `PROJECT_HANDOVER.md`. Có lỗi môi trường hoặc thiếu bằng chứng thật thì dùng `PARTIAL`/`BLOCKED`, không ghi `PASS` thay.

## 8. Năng lực chưa kích hoạt

Promotion bài học, hàng chờ chuyên gia đầy đủ, prediction store/model/shadow tự động, cảnh báo, NAS nhiều người, Drum/DLP và Agent lập trình chỉ được bổ sung vào hướng dẫn khi điều kiện trong [plan.md](plan.md) đã đạt.
