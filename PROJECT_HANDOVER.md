# Biên bản Bàn giao Dự án (Project Handover)

Cập nhật: 2026-08-30
Nguồn trạng thái chuẩn: [ROADMAP.md](ROADMAP.md) là nguồn trạng thái chuẩn duy nhất cho vòng đời các Gate; tệp này là ảnh chụp nhanh (snapshot) vận hành và không được tự ý chuyển các tuyên bố lịch sử thành tuyên bố phát hành hiện tại.

## Ảnh chụp trạng thái hiện tại (Current Snapshot)

- **Chuẩn bị nguồn tăng dần (005):** Mã đã triển khai và 101 bài kiểm tra liên quan đã PASS:
  nguồn mới được chuẩn bị riêng, câu hỏi chờ tự tiếp tục một lần sau khi nguồn sẵn sàng, và
  câu hỏi quá rộng không kích hoạt đọc lại toàn bộ thư viện. Khi BGE-M3 không có deployment
  hợp lệ, giao diện phải hiện rõ `BGE-M3 chưa sẵn sàng`, không được báo sẵn sàng giả.

- **Sửa lỗi phạm vi câu hỏi chờ (005 follow-up):** Sau khi BGE-M3 được kích hoạt, lỗi thực tế
  được xác định là UI chuẩn bị một phạm vi hẹp nhưng retrieval chọn lại từ toàn bộ nguồn bật.
  Mã hiện dùng đúng một phạm vi (tối đa một tài liệu) từ chuẩn bị đến truy xuất, hiển thị số
  lượng đang chuẩn bị và cho phép hủy câu hỏi chờ. 103 test liên quan PASS; browser smoke với
  tài liệu thật vẫn là bước xác nhận còn lại.

- **Giao diện chính (Primary UI):** Workspace Chat. Các tệp giao diện công khai của Case Cockpit cũ đang được cho dừng (retired), tuy nhiên các dịch vụ dùng chung dựa trên `case_store` vẫn có các luồng gọi trực tiếp và tuyệt đối không được xóa nếu chưa có kế hoạch di chuyển tách biệt.
- **Git:** Nhánh `main...origin/main` hiện có một cây làm việc chưa commit đáng kể, bao gồm RAG, Workspace Chat, Antigravity, tài liệu và các bài kiểm thử. Cần bảo toàn các thay đổi hiện có; phân tách và đánh giá kỹ lưỡng trước khi đưa ra bất kỳ tuyên bố phát hành hoặc chạy benchmark nào.
- **Dữ liệu riêng tư:** `local_cases/`, `local_runs/`, tài liệu nguồn gốc, bộ nhớ đệm mô hình (cache), thông tin xác thực (credentials) và câu trả lời benchmark luôn được Git bỏ qua. Tuyệt đối không đưa chúng vào Git để làm cho báo cáo bàn giao trông có vẻ "đầy đủ".
- **Hồ sơ vụ Workspace Chat (Cổng 1, commit `2bb7a5f`, kiểm toán lại 2026-08-30):** Nền lưu hồ sơ được giữ nguyên: SQLite cục bộ tách kho, transaction case/evidence/audit, từ chối trace không phải `local_only`, không sao chép câu hỏi/câu trả lời/đoạn trích và idempotent theo trace. FR-002/FR-004 được nâng bằng migration có version/backup/rollback và activity append-only có chuỗi digest; FR-016 được khóa bằng thông báo UI tiếng Việt an toàn; FR-018 được kiểm bằng AST trên toàn bộ module Workspace Chat/case được hỗ trợ.
- **Vòng hồ sơ 008, Cổng 1A + US1:** `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE`. Đã có quyền/vai trò theo phạm vi cho người thao tác cục bộ, phiên bản chống ghi đè, danh sách/bộ lọc/chi tiết/dòng thời gian/việc cần bổ sung/giao việc/mở dấu vết và gắn thêm siêu dữ liệu bằng chứng. Lượt kiểm tra tập trung đạt `169 passed` trên lệnh mặc định và `56 passed` trên Python 3.11; lớp chặn thông báo cuối cùng đạt thêm `66 passed`. `compileall`, hợp đồng tài liệu, `git diff --check`, lệnh kiểm toán và lệnh nhập Workspace Chat đều thoát mã 0. Toàn bộ bộ kiểm thử Python 3.11 gần nhất, trước lớp chặn thông báo cuối cùng, ghi nhận `2.392 passed, 2 failed`: một lỗi cấu hình VPS bị biến môi trường hiện tại ghi đè và một lỗi kiểm tra môi trường sạch không tìm được `extract-msg`. Hai lỗi không thuộc phần thay đổi hồ sơ nhưng vẫn chặn tuyên bố đạt toàn kho. Chưa có kiểm tra trực tiếp trên trình duyệt và chưa mở luồng chuyên gia, bài học, thử nghiệm line, dự đoán LSU hoặc Agent thực thi.
- **Giới hạn định danh Cổng 1A:** runtime hiện chỉ được duyệt cho một người dùng cục bộ, với `local_admin` do ứng dụng cấp và quyền cụ thể theo phạm vi. Mã người thao tác không được lấy từ biểu mẫu hoặc nội dung AI. Phải giữ chế độ nhiều người dùng ở trạng thái từ chối cho đến khi có ánh xạ tài khoản/hệ điều hành và kiểm thử chống mượn danh.
- **Cấu hình kiểm thử:** `pytest` hiện nằm trong nhóm phụ thuộc `dev` và đã ghi nhận trong lockfile. Lệnh `uv lock --check` đã vượt qua. Môi trường `.venv` hiện tại gặp lỗi từ chối quyền truy cập (access denied) của Windows đối với metadata cũ của `aios_habit` khi chạy `uv sync`; không tự ý xóa hoặc thay đổi quyền sở hữu môi trường đó mà chưa có sự chấp thuận của chủ sở hữu.

## Bằng chứng đã xác minh ngày 2026-08-16 (Verified Evidence)

| Hạng mục | Bằng chứng hiện tại | Phạm vi ranh giới |
|---|---|---|
| Lưu trữ JSONL cục bộ | 33 bài kiểm thử trọng điểm ĐẠT; bao gồm ghi nguyên tử (atomic write), khôi phục (rollback) và ghi log an toàn dòng lỗi | Chưa phải kết quả toàn bộ suite |
| Workspace Chat / Giao diện bàn giao | 59 bài kiểm thử trọng điểm ĐẠT | Chưa phải smoke test trên trình duyệt hoặc trực tiếp với provider |
| Cầu nối Antigravity, bàn giao & RAG đa nguồn | 43 bài kiểm thử trọng điểm ĐẠT | Chưa kiểm chứng trực tiếp sidecar/provider thực tế |
| Adaptive Reranking UX (Feature 003) | 154 bài kiểm thử trọng điểm ĐẠT, 1.175 test toàn bộ ĐẠT, schema v3 và circuit breaker hoàn tất | `IMPLEMENTED_PENDING_REAL_BENCHMARK`; canary/production activation `BLOCKED` cho đến khi chạy benchmark thật trên model/corpus |

| Thu thập kiểm thử repository | `pytest --collect-only -q`: đã thu thập 1,143 bài kiểm thử | Thu thập không tương đương với chạy kiểm thử thành công |

| Vệ sinh mã nguồn | `compileall`, `uv lock --check`, và `git diff --check` ĐẠT | Cây làm việc vẫn ở trạng thái chưa commit |

Các Gate Card đã hoàn thành hiện có trong cây làm việc là tài liệu ghi nhận kết quả triển khai. Chúng được đánh dấu là đang chờ xác minh toàn bộ test suite cho đến khi toàn bộ quality gate bắt buộc được chạy thành công trên diff cuối cùng.

## Quy trình Tiếp tục An toàn (Safe Continuation)

1. Kiểm tra cây làm việc hiện có trước khi đưa ra bất kỳ quyết định benchmark, dọn dẹp hoặc commit nào:

   ```powershell
   git status --short --branch
   git diff --check
   git diff --cached --check
   ```

2. Trên một môi trường ổn định, cài đặt và chạy chuỗi công cụ phát triển có thể tái lập:

   ```powershell
   uv sync --group dev
   uv run --no-sync --group dev python scripts/check_docs.py
   uv run --no-sync --group dev python -m compileall src tests
   uv run --no-sync --group dev pytest -q
   uv run --no-sync --group dev python -m aios_habit.cli audit
   ```

3. Tuyệt đối không coi một bộ kiểm thử trọng điểm vượt qua hoặc số lượng test thu thập được là sự cho phép để đánh dấu Gate Card thành `DONE`, công bố báo cáo 12 câu hỏi, hoặc chạy benchmark provider trực tiếp. Phải ghi lại chính xác câu lệnh, mã thoát (exit code) và phạm vi kiểm thử.

4. Đối với luồng benchmark RAG, phải bảo toàn định danh/checkpoint đóng băng. Chẩn đoán cục bộ chưa đóng dấu chỉ được giới hạn ở preflight không dùng provider, Stage A hoặc chạy thử nghiệm (dry-run) với đúng `BQ01,BQ02`; bắt buộc phải từ chối `--run`.

5. Trước khi commit, cần tách biệt mã sản phẩm/tài liệu khỏi các tùy biến cục bộ và dữ liệu runtime bị bỏ qua. Chỉ cập nhật roadmap, changelog và biên bản bàn giao này dựa trên bằng chứng từ diff cuối cùng.

## Rủi ro Vận hành Cần Chuyển giao Tiếp theo (Operational Risks)

- Các dòng JSONL không hợp lệ hiện chỉ được hiển thị trong log cục bộ theo tên tệp/số dòng. Giữ lại tệp cục bộ gốc để phục hồi; tuyệt đối không sao chép nội dung bản ghi vào issue hoặc kênh chat.
- Lệnh `uv sync --group dev` có thể thất bại trên môi trường Windows `.venv` hiện tại do thư mục metadata cũ bị khóa quyền. Hãy dừng lại, xác định các tiến trình đang chạy và xin phê duyệt trước khi tạo lại môi trường.
- Toàn bộ bộ kiểm thử chưa được chạy lại đầy đủ trong đợt bàn giao này. Số lượng kiểm thử dự kiến thu thập là 1,143, nhưng chỉ lượt chạy hoàn chỉnh với mã thoát 0 mới được tính là ĐẠT.
- Tài liệu này không ngụ ý bất kỳ trạng thái worker benchmark/BGE nào đang hoạt động; hãy kiểm tra danh sách tiến trình và các artifact runtime bị bỏ qua ngay trước khi khởi chạy lại.
