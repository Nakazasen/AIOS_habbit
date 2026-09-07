# Hướng dẫn kiểm chứng đợt đang thực thi

Tài liệu này hướng dẫn nghiệm thu MVP Iris LSU theo từng mốc. Cổng kỹ thuật của mốc trước phải có bằng chứng trước khi xây implementation mốc sau. Rubric tự chấm dữ liệu và chạy bóng đọc-only; thiếu dữ liệu chỉ chặn đúng lô phụ thuộc, không chặn kiểm thử kỹ thuật bằng fixture đã làm sạch. Dữ liệu thật phải nằm trong vùng cục bộ được phép và không được commit.

## 1. Ghi baseline

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
uv run --no-sync --group dev python -V
```

Interpreter phải là Python 3.11. Trên máy này `py -3` có thể chọn Python khác phiên bản dự án nên không dùng lệnh đó làm cổng kiểm chứng.

Nếu `.venv` hiện có bị khóa hoặc sai phiên bản, tạo môi trường riêng không phá hủy:

```powershell
$repoRoot = (Resolve-Path '.').Path
$goalRoot = Join-Path $repoRoot 'local_runs\evidence_case_loop_goal\manual-preflight'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $goalRoot '.venv'
New-Item -ItemType Directory -Force -Path $goalRoot | Out-Null
uv sync --project $repoRoot --python 3.11 --group dev
uv run --project $repoRoot --no-sync --group dev python -V
```

Ghi lại thay đổi cục bộ cần bảo toàn. Không dùng số test hoặc commit cũ làm bằng chứng hiện tại. Không dùng `git add -A`; `.brain/`, `local_cases/`, `local_runs/` và dữ liệu thật không được stage.

## 2. Kiểm tra tập trung phần nền

```powershell
uv run --no-sync --group dev pytest -q tests/test_workspace_case_migrations.py tests/test_workspace_case_store.py tests/test_workspace_case_authorization.py tests/test_workspace_case_service.py tests/test_workspace_case_ui.py
uv run --no-sync --group dev pytest -q tests/test_workspace_chat_rag_v2_adapter.py
git diff --check
```

Kiểm tra import trong runtime tách biệt để lệnh không tạo/touch `local_cases/` thật:

```powershell
$repoRoot = (Resolve-Path '.').Path
$runtimeRoot = Join-Path $repoRoot 'local_runs\evidence_case_loop_goal\manual-preflight\runtime'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Push-Location $runtimeRoot
$env:PYTHONPATH = Join-Path $repoRoot 'src'
uv run --project $repoRoot --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
Pop-Location
```

Nếu tên file test chuẩn bị nguồn đã thay đổi, chọn đúng các test chứa `source_preparation`, `preparation_summary`, `pending_question` và progress; ghi rõ danh sách thực chạy.

## 3. Smoke trình duyệt Đợt 0

Khởi động một phiên smoke riêng từ `$runtimeRoot`, dùng cổng 8537 và chỉ tải fixture trong repo:

```powershell
Push-Location $runtimeRoot
$env:PYTHONPATH = Join-Path $repoRoot 'src'
uv run --project $repoRoot --no-sync streamlit run "$repoRoot\src\aios_habit\workspace_chat_app.py" --server.port 8537 --server.headless true --browser.gatherUsageStats false
Pop-Location
```

Kết thúc đúng tiến trình của phiên smoke sau khi kiểm tra. Gemini không mở thư mục `Tài liệu của tất cả dòng máy/` hoặc dữ liệu thật. Tiến trình kiểm tra cục bộ được phép đọc qua bí danh `KHO_LSU_CUC_BO` và chỉ trả manifest/số tổng hợp đã làm sạch cho tác tử. Bí danh `GOI_KYOCERA_CUC_BO` chỉ được đăng ký cho US4 sau này, không đọc trong đợt này.

### Chuẩn bị nguồn

1. Mở Workspace Chat với thư viện có nguồn chưa sẵn sàng.
2. Xác minh giao diện nói rõ chưa thể tìm kiếm đầy đủ, hiển thị phần trăm và số nguồn đã xong/đang chờ/gặp lỗi.
3. Xác minh không có tên engine/model nội bộ trong nhãn, lỗi hoặc cảnh báo.
4. Dừng/khởi động lại ứng dụng; tiến độ phải tiếp tục hoặc có nút “Tiếp tục chuẩn bị”, không đứng im mà không hướng dẫn.
5. Với một nguồn lỗi, nút “Thử lại” phải hoạt động và lỗi hiển thị bằng tiếng Việt, không có traceback.
6. Cố ý trả lỗi tiếng Anh từ thư viện hoặc dịch vụ giả lập; giao diện và nhật ký vận hành chỉ được hiện lời giải thích cùng bước xử lý bằng tiếng Việt.
7. Xác minh không có bộ chọn ngôn ngữ giao diện khác tiếng Việt. Tài liệu nguồn ngoại ngữ vẫn được giữ nguyên như bằng chứng.

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
5. Xác minh AI chỉ có vai trò chấm rubric hệ thống, không thể mượn role/scope của chuyên gia hoặc nâng quyền người dùng.

## 5. Kiểm tra chuỗi dữ liệu BOWSKEW 4 BEAM

1. Đặt các file lot linh kiện, liên kết Unit–lot và kết quả JIG/outcome trong thư mục cục bộ được phép.
2. Dùng data dictionary mặc định và target BOWSKEW 4 BEAM; không nhập đường dẫn hoặc dữ liệu thật vào Git.
3. Chạy kiểm tra Data Gate. Màn hình phải báo số bản ghi nối được, thiếu, trùng, mâu thuẫn, rubric version và kết luận tự động.
4. Chọn một `unit_serial`; xác minh xem được lot linh kiện, thông số đầu vào, JIG/lần đo và outcome cuối.
5. Xóa một khóa nối trong bản sao thử; hệ thống phải báo thiếu và không tự nối bằng tên file/thứ tự dòng.
6. Khi rubric trả `PASS` hoặc `PASS_WITH_WARNING`, chương trình tự tạo snapshot hợp lệ trong `production_prediction.sqlite`; file nguồn không bị sửa.

Nếu Data Gate thật không đạt, lưu báo cáo thiếu dữ liệu và đánh dấu `BLOCKED_DATA`. Vẫn kiểm thử kho tạm, báo cáo và mốc phát lại bằng fixture; fixture không được dùng để giả nhận snapshot thật hoặc độ chính xác thật.

Trong lượt Gemini, fixture luôn được dùng để đóng cổng kỹ thuật. Nếu bí danh nguồn cục bộ đã cấu hình, tiến trình cục bộ được chạy thêm trên dữ liệu thật nhưng chỉ trả kết luận rubric và số tổng hợp đã làm sạch; dữ liệu thật không được mở trong ngữ cảnh tác tử cloud.

## 6. Phát lại lịch sử

1. Chọn snapshot thật đã đăng ký; nếu chưa có thì chọn snapshot fixture trong kho SQLite tạm và ghi rõ đây là kiểm thử kỹ thuật.
2. Chạy phương án không cảnh báo và EWMA với cấu hình đã đóng băng gồm metric, chiều rủi ro, cửa sổ nền, tham số EWMA, khoảng dự báo, quy tắc ghép outcome và feature allowlist.
3. Xác minh không có feature nào dùng dữ liệu sau thời điểm dự báo.
4. Nếu Data Gate thật và công thức cỡ mẫu trong rubric đạt, mới cài/chạy đúng một hồi quy logistic nhẹ trên CPU. Nếu chưa đủ điều kiện, xác minh nhánh model trả `not_applicable` mà không thêm dependency.
5. Đối chiếu cùng một tập giữ lại; báo số cảnh báo đúng, cảnh báo nhầm, bỏ sót và thời gian cảnh báo sớm.
6. Chạy lại với cùng snapshot/protocol; báo cáo phải tái lập được.

Không đủ dữ liệu cho model thì baseline và báo cáo Data Gate vẫn là đầu ra hợp lệ. Nếu chưa có snapshot thật, báo cáo fixture chỉ đóng cổng kỹ thuật. Không thêm model chỉ để có biểu đồ đẹp.

## 7. Shadow thủ công

1. Với dữ liệu thật, chỉ dùng baseline/model, threshold và rubric đã đóng băng cho `AUTO_SHADOW` hoặc `LEARNING_SHADOW`; với fixture chỉ được chạy chế độ diễn tập kỹ thuật có nhãn rõ.
2. Người dùng chủ động chọn một lô file mới và bấm chạy.
3. Xác minh lô dự báo không đưa outcome/retest xảy ra sau `as_of_time` vào feature.
4. Workspace Chat hiển thị danh sách Unit có nguy cơ, lý do và nguồn/digest; câu chữ phải nói “cần kiểm tra”.
5. Chạy lại cùng lô; không được tạo case trùng dù thời điểm chạy trên đồng hồ thay đổi.
6. Người phụ trách ghi kết quả thật: đúng, cảnh báo nhầm, bỏ sót hoặc chưa xác định; phải ghi được Unit NG bị bỏ sót dù Unit đó không từng có cảnh báo.
7. Xác minh không có scheduler, gửi cảnh báo ngoài, PLC hoặc thao tác thay đổi máy.

## 8. Đóng một mốc

Ghi riêng cổng kỹ thuật và cổng vận hành. Một cổng vận hành đang chờ không được đổi thành PASS, nhưng cũng không được dùng để ngăn đóng cổng kỹ thuật hoặc chuẩn bị nhánh độc lập kế tiếp.

Chỉ chạy bộ đầy đủ khi chuẩn bị hợp nhất, phát hành hoặc đánh dấu đợt hoàn tất:

```powershell
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python scripts/check_docs.py
git diff --check
git diff --cached --check
```

Lệnh import vẫn chạy trong `$runtimeRoot` theo mục 2. Chỉ chạy một lệnh nặng tại một thời điểm; với kiểm thử dự đoán đặt `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` và `OPENBLAS_NUM_THREADS=1` để bảo vệ laptop.

Ghi commit, nhánh, lệnh, exit code, số test và phần chưa kiểm chứng vào `PROJECT_HANDOVER.md`. Có lỗi môi trường hoặc thiếu bằng chứng thật thì dùng `PARTIAL`/`BLOCKED`, không ghi `PASS` thay.

Trước khi đóng mốc, người kiểm thử phải đọc toàn bộ giao diện, báo cáo và nhật ký vận hành của luồng vừa làm. Nếu còn một câu tiếng Anh do chương trình tạo hoặc do lỗi bên ngoài lọt ra thì mốc chưa đạt.

## 9. Năng lực chưa kích hoạt

Promotion bài học, điều tra C-call/Jam, hàng chờ chuyên gia đầy đủ, artifact Agent, Agent lập trình, shadow tự động, cảnh báo, NAS nhiều người và Drum/DLP vẫn thuộc tầm nhìn. Chúng chỉ được bổ sung vào hướng dẫn khi điều kiện trong [plan.md](plan.md) đã đạt.
