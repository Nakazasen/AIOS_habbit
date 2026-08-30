# Hướng dẫn kiểm chứng theo gate

Tài liệu này là run guide nghiệm thu, không phải hướng dẫn triển khai code. Dữ liệu thật chỉ chạy trong vùng cục bộ được chủ sở hữu cho phép và không được commit.

## 1. Baseline hiện tại

```powershell
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
py -3 -m pytest -q tests/test_workspace_case_store.py tests/test_workspace_case_service.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py
```

Kỳ vọng baseline tại thời điểm lập kế hoạch: nhánh `gate1-local-case-sqlite`, commit `2bb7a5f`, 80 test đạt. Nếu checkout thay đổi, chạy lại và ghi kết quả mới; không dùng con số này làm bằng chứng hiện tại.

## 2. Gate 1A — Migration và audit Cổng 1

1. Tạo DB bằng schema Cổng 1, thêm một case/evidence/audit event.
2. Chạy migration lên version mới.
3. Đọc lại record và xác minh digest không đổi.
4. Fault injection giữa migration; xác minh restore snapshot và `quick_check` đạt.
5. Tìm chuỗi câu hỏi/câu trả lời/excerpt fixture trong DB; kỳ vọng không có.

## 3. Gate 2 — Danh sách và chi tiết case

1. Từ answer có citation, bấm “Lưu vào hồ sơ”.
2. Mở mục “Hồ sơ vụ việc”, lọc theo loại/trạng thái, bấm case.
3. Xem timeline/evidence/assignee và mở trace gốc.
4. Xóa trace fixture có kiểm soát; case detail phải báo thiếu bằng chứng, không tái tạo nội dung.
5. Thử transition với version cũ; service phải từ chối.

## 4. Gate 3 — Chuyên gia

1. Tạo role/scope fixture cục bộ.
2. Giao một câu hỏi cho chuyên gia đúng scope; hàng chờ hiển thị.
3. Thử xác nhận thiếu rationale/sai scope/sai evidence digest; đều bị từ chối.
4. Ghi hai review trái chiều; case chuyển trạng thái cần phân xử và giữ cả hai record.
5. Restart/readback; audit chain vẫn đầy đủ.

## 5. Gate 4 — Vòng học

1. Tạo learning candidate từ review `confirmed`.
2. Tìm trong case-memory trước promotion; không có kết quả chuẩn.
3. Promotion bằng quality manager, tìm lại và mở provenance.
4. Withdraw; kết quả biến mất khỏi search thông thường nhưng audit còn.
5. Xác minh `library.sqlite` không thay đổi.

## 6. Gate 5 — Pilot line

1. Ingest log được phép vào `line_events.sqlite`; ghi source digest/timezone/version.
2. Tạo case điều tra, attach event match và dựng timeline.
3. Câu hỏi không match phải trả rỗng, không lấy năm event gần nhất.
4. Chuyên gia review relevance; mapping chỉ mở với manifest đã duyệt.
5. Hoàn tất một case thật với SOP, mã lỗi, báo cáo và outcome được duyệt.

Pilot thiếu dữ liệu thật được ghi `BLOCKED`, không thay bằng fixture tổng hợp để đóng gate.

## 7. Gate 6–7 — Agent

### Artifact theo case

1. Tạo proposal báo cáo/SOP từ case confirmed.
2. Thử evidence rỗng, output path bảo vệ, overwrite và approval sai version; đều bị từ chối.
3. Generate → verify → approve → export; file mới có version và provenance.
4. Chỉnh artifact sau approval; phải yêu cầu approval mới.

### Lập trình

1. Tạo task pack với branch/head/allowed files/commands/tests.
2. Thử truy cập `local_cases`, `.env`, source nhà máy hoặc file ngoài workspace; bị deny.
3. Tạo patch proposal, xem diff, approve đúng digest, chạy test allowlisted.
4. Self-report PASS không observed evidence phải `REVIEW_REQUIRED`/từ chối.
5. Xác minh không tự commit/merge/push.

## 8. Gate 8–9 — Dữ liệu và model LSU/Iris

1. Chạy data validator trên snapshot local: join keys, unit, timezone, version, duplicates, label provenance.
2. Thiếu một trong sáu readiness conditions; kết quả `blocked`, không tạo model.
3. Đóng băng dataset/protocol; build feature snapshot với `as_of_time`.
4. Chạy baseline không cảnh báo, EWMA/CUSUM và model ứng viên theo cùng temporal/group split.
5. Report phải có false alarm, missed detection, lead time, precision/recall, calibration, stability slice và digests.
6. Thử đưa feature tương lai vào snapshot; leakage guard phải chặn.

## 9. Gate 10 — Shadow prediction

1. Approve model/threshold cho shadow.
2. Replay input window; tạo `RiskAssessment` và case prediction khi vượt threshold.
3. Chạy lại cùng signal trong cooldown; không tạo case trùng.
4. Gắn outcome đúng/sai/chưa đủ và kiểm metric cập nhật.
5. Theo dõi connector/mock; không có call PLC, alert ngoài hoặc route cloud.

## 10. Gate 11–12 — Alert có duyệt và Drum/DLP

1. Chưa có owner approval/kill switch; enable alert phải bị chặn.
2. Sau approval, chỉ role được phép thấy in-app alert và mở case.
3. Action proposal cần human approval; không có plant control.
4. Drum/DLP phải chạy Data Gate riêng; threshold/model LSU không được reuse nguyên trạng.

## 11. Gate 13 — NAS và pilot tổ chức

1. Chạy trên đường dẫn thư viện thật được phép.
2. Xác minh one-writer/multi-reader và fail-closed writer thứ hai.
3. Online backup, `quick_check`, restore và readback.
4. Hai người/ca bàn giao một case và mở đúng evidence/review/outcome.

Không có môi trường thật thì Gate A giữ `PARTIAL`.

## 12. Lệnh đóng mỗi gate

```powershell
py -3 -m compileall src tests
py -3 -m pytest -q <tests-tập-trung>
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
```

Trước merge/đóng gate:

```powershell
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
```

Kỳ vọng audit có `"status": "PASS"`. Kết quả phải ghi commit, branch, lệnh, exit code, test count, artifact path đã scrub và những phần chưa runtime-verified.
