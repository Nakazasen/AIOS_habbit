# Đường Cơ Sở Chuyên Nghiệp Hóa (PROFESSIONALIZATION-BASELINE)

Status: `DONE`  
Owner role: Project owner with security and release reviewers  
Opened: 2026-07-25  
Completed: 2026-07-25  
Last reviewed: 2026-07-25  
Review cadence: At each delivery slice and before gate closure  

## Mục Tiêu (Goal)

Thiết lập một đường cơ sở tài liệu chuyên nghiệp, dựa trên bằng chứng và dễ duy trì cho AIOS WorkLens mà không làm thay đổi runtime sản phẩm, luồng UI, lược đồ dữ liệu hay mặc định ưu tiên cục bộ.

## Trong Phạm Vi (In Scope)

- Các hồ sơ về bảo mật, quyền riêng tư, mô hình mối đe dọa và quản trị phụ thuộc.
- Các khung nhìn triển khai kiến trúc, ADR, yêu cầu và ma trận truy xuất nguồn gốc.
- Chiến lược chất lượng, kiểm tra hợp đồng tài liệu và tính tương đương trong CI.
- Các quy trình phục hồi, xử lý sự cố, giải quyết lỗi, khả năng quan sát và phát hành.
- Các hồ sơ về rủi ro, quyền sở hữu, người đóng góp, khả năng tiếp cận, di chuyển, bảo trì và tiếp nhận nhân sự mới.
- Mục lục tài liệu chuẩn tắc và các liên kết từ các tài liệu quản trị gốc.

## Các Phi Mục Tiêu (Non-goals)

- Không triển khai truy xuất kết hợp RAG v2.
- Không mở cổng A18 hoặc P1.0.
- Không thêm UI mới cho người dùng thông thường hoặc bảng điều khiển kỹ thuật.
- Không thêm hành vi mặc định dùng cloud, viễn trắc telemetry, lưu trữ bí mật hay di chuyển dữ liệu riêng tư.
- Không bịa đặt SLA, tuân thủ pháp lý, thời gian lưu giữ, người sở hữu cụ thể hoặc đầu mối công khai bảo mật.

## Điều Kiện Tiên Quyết (Preconditions)

- Bảo toàn bản hiến pháp ưu tiên cục bộ và ưu tiên quyền riêng tư hiện có.
- Bảo toàn các thay đổi chưa commit của router v0.4.0 và cổng dọn dẹp.
- Đối xử với mọi dữ liệu riêng tư / runtime dưới dạng bị gitignore.

## Danh Sách Cho Phép (Allowlist)

- Tài liệu dưới thư mục `docs/`, các tài liệu quản trị gốc, tệp người đóng góp / bảo mật.
- Script / kiểm thử xác thực tài liệu và cấu hình CI.
- Tuyệt đối không có mã ứng dụng runtime ngoại trừ tiện ích xác thực chỉ dùng cho tài liệu.

## Ràng Buộc Bảo Mật (Privacy Constraints)

- Tuyệt đối không đưa API key, văn bản tài liệu cục bộ, ảnh chụp màn hình, đường dẫn cục bộ hoặc dữ liệu runtime JSONL/SQLite vào tài liệu, fixture, artifact CI hay báo cáo.
- Các kiểm tra provider trực tiếp / mạng luôn là thủ công và mang tính opt-in; CI mặc định chạy ngoại tuyến (offline).
- Bất kỳ kiểm soát nào chưa được chứng minh trong mã nguồn / kiểm thử đều phải được gắn nhãn `PLANNED`, `PARTIAL` hoặc `OWNER_DECISION_REQUIRED`.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

1. Các tài liệu chuyên nghiệp bắt buộc có vai trò chủ sở hữu, trạng thái, ngày/chu kỳ xem xét và các liên kết cục bộ hoạt động tốt.
2. Tài liệu về mối đe dọa, quyền riêng tư, phát hành và vận hành phản ánh chính xác hành vi mã nguồn đã được kiểm chứng.
3. Các ADR, yêu cầu và ma trận truy xuất nguồn gốc kết nối các quyết định then chốt với mã nguồn, bài kiểm thử và sổ tay hướng dẫn.
4. Kiểm tra hợp đồng tài liệu được tự động hóa và bao phủ bởi các bài kiểm thử.
5. CI thực thi biên dịch, kiểm thử, kiểm toán, import Workspace Chat và kiểm tra tài liệu.
6. Xác thực toàn bộ repository đạt mà không có dữ liệu riêng tư nào bị theo dõi trong Git.

## Bằng Chứng Đóng Cổng (Closure Evidence)

- Tài liệu chuyên nghiệp, metadata và liên kết cục bộ: `DOCUMENTATION_CONTRACT=PASS`.
- Kiểm thử công cụ tài liệu / SBOM: `4 passed`.
- Toàn bộ bộ kiểm thử repository: `896 passed in 30.64s`.
- Biên dịch: PASS; Kiểm toán CLI audit: `PASS` không lỗi/cảnh báo; Import Workspace Chat: PASS (chỉ có cảnh báo bare-mode của Streamlit).
- Kịch bản sao lưu / phục hồi giả lập: PASS cho 6 loại thực thể JSONL của Workspace Chat cùng với chỉ mục SQLite `count()` / tìm kiếm từ vựng `search()`, chỉ sử dụng thư mục tạm thời.
- `git diff --check` và `git diff --cached --check`: PASS.
- `API Key.txt` và `local_runs/sbom/aios-habit-sbom.json` tự sinh: xác nhận đã bị bỏ qua / không theo dõi trong Git.

## Các Quyết Định Còn Lại và Theo Dõi

Đầu mối báo cáo bảo mật, phân phối / hỗ trợ, lưu giữ / RTO / RPO, định danh người đánh giá / CODEOWNERS và thực thi khuyến nghị phụ thuộc vẫn ở trạng thái `OWNER_DECISION_REQUIRED`. Cổng [AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md) đã hoàn thành việc chuyển giao thay đổi luồng điều khiển runtime riêng biệt và xác thực đặc thù tuyến trước khi tuyên bố phát hành provider bên ngoài có thể được xem xét.

## Kiểm Chứng (Verification)

```powershell
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

## Hoàn Tác (Rollback)

Hoàn tác các thay đổi tài liệu chuyên nghiệp hóa, CI và kiểm tra tài liệu. Không có sự di chuyển dữ liệu runtime, lệnh gọi provider, thay đổi secret hay hành vi UI nào cần hoàn tác trong cổng này.

