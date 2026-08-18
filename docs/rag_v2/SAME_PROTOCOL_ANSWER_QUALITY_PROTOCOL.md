# Giao Thức Đánh Giá Chất Lượng Câu Trả Lời Theo Cùng Quy Chuẩn (Same-Protocol Answer Quality Evaluation Protocol)

Status: `ACTIVE`  
Owner role: `Project owner`  
Last reviewed: `2026-07-29`  
Review cadence: `Per evaluation gate`  

## Mục Đích & Phạm Vi (Purpose & Scope)

Tài liệu này quy định chi tiết giao thức thực thi chính xác nhằm đánh giá ứng viên sản xuất `bge_m3_hybrid` đã kích hoạt so với đường cơ sở đo chuẩn NotebookLM đã đóng băng. Nó đảm bảo tính tái lập, tuân thủ quyền riêng tư và kỷ luật đánh giá nghiêm ngặt mà không áp dụng tinh chỉnh tùy tiện hay để lộ dữ liệu trái phép ra ngoài.

## Đường Cơ Sở Đánh Giá Đã Đóng Băng (Frozen Evaluation Baseline)

- **Bộ câu hỏi (Question Set)**: Manifest chuẩn tắc `BQ01`–`BQ12`. Mã băm SHA-256 của bộ câu hỏi bắt buộc phải khớp với tham chiếu bất biến.
- **Tập ngữ liệu mục tiêu (Corpus Target)**: Tập hợp 70 tệp tài liệu chuẩn tắc `tailieugoc/` được kiểm toán đạt độ bao phủ 70/70.
- **Các mốc đo chuẩn lịch sử**:
  - Điểm tham chiếu NotebookLM: `3.807/5` (ban đầu) / `4.27/5` (lượt chạy lại fail-closed).
  - Điểm trước đây của RAG v2: `2.898/5` (ban đầu) / `3.15/5` (lượt chạy lại fail-closed).
- **Hồ sơ ứng viên (Candidate Profile)**: `bge_m3_hybrid` đã kích hoạt với phiên bản model cục bộ và checksum đã được phê duyệt.

## Mô Hình Phân Tầng: Giai Đoạn A vs Giai Đoạn B

Nhằm ngăn chặn việc rò rỉ dữ liệu lên cloud ngoài ý muốn và duy trì ranh giới bảo mật nghiêm ngặt, việc đánh giá tuân theo giao thức hai giai đoạn:

### Giai Đoạn A: Đánh Giá Cục Bộ / Không Dùng Provider (Stage A)

- Chạy hoàn toàn ngoại tuyến (offline) mà không nạp thông tin xác thực API hay mở socket mạng.
- Thực thi quy trình nạp tài liệu, chia chunk nhận biết cấu trúc, truy xuất kết hợp, chuẩn bị workspace và kiểm tra phương án dự phòng tổng hợp cục bộ.
- Xác thực ràng buộc định danh sản xuất (`rag_v2_subprocess`, `bge_m3_hybrid`, `fail_closed=True`, `lexical_fallback_enabled=True`).
- Nếu tập ngữ liệu được phân loại là `local_only` và không có tuyến xử lý trực tiếp nào được phê duyệt, Giai đoạn A hoàn tất với kết luận `BLOCKED_PRIVACY_ROUTE`.

### Giai Đoạn B: Đánh Giá Tổng Hợp Qua Provider Trực Tiếp (Stage B)

- Yêu cầu tập ngữ liệu phải được phân loại rõ ràng là `cloud_safe` hoặc `public` và có sự phê duyệt của chủ sở hữu.
- Chuyển bằng chứng đã truy xuất qua bộ định tuyến provider `BrainGateway` bằng các thông tin xác thực đã cấu hình.
- Thử lại các lỗi truyền tải tạm thời trong giới hạn đã khai báo trước mà không làm thay đổi cấu hình ứng viên.
- Yêu cầu chấm điểm mù độc lập bởi con người trên 3 nhánh hệ thống được xáo trộn ngẫu nhiên trước khi tuyên bố tính tương đương.

## Xác Minh Định Danh Sản Xuất & Ràng Buộc (Production Identity & Binding Verification)

Trước khi bất kỳ câu truy vấn nào được đánh giá, khung đo chuẩn benchmark bắt buộc phải kiểm tra khớp định danh ứng viên nghiêm ngặt:

1. **Manifest Triển Khai (Deployment Manifest)**: Phải là manifest `workspace_chat_rag_v2.local.json` đã kích hoạt chỉ định `requested_profile: bge_m3_hybrid`.
2. **Tính Toàn Vẹn Model (Model Integrity)**: Đường dẫn model BGE-M3 đã ghim, revision và checksum cây thư mục phải khớp với các hằng số sản xuất đã khai báo.
3. **Chuẩn Bị Workspace (Workspace Stage)**: Các trận so tài gắn với sản xuất phải tái sử dụng hoặc tạo một `workspace_stage_manifest.json` định danh theo nội dung để niêm phong dấu vân tay nguồn và trạng thái chuẩn bị.
4. **Viễn Trắc Dự Phòng (Fallback Telemetry)**: Mỗi hàng câu trả lời được đánh giá phải chứng minh việc thực thi bằng `rag_v2_subprocess` mà không bị suy giảm về luồng dự phòng.

## Kỷ Luật Đánh Giá (Evaluation Discipline)

1. **Yêu Cầu Đóng Băng**: Bộ câu hỏi, manifest tập ngữ liệu, định danh ứng viên và dữ liệu tham chiếu phải được đóng băng trước khi sinh câu trả lời.
2. **Không Tinh Chỉnh Sau Khi Mở Mù (No Tuning After Unblinding)**: Tuyệt đối không sửa đổi tham số truy xuất, câu từ prompt, kích thước chunk hay logic chấm điểm sau khi đã xem kết quả mở mù cho một cổng đang hoạt động.
3. **Bảo Mật Fail-Closed**: Các nguồn `local_only` tuyệt đối không bao giờ được truyền ra ngoài. Thiếu key, lỗi mạng hoặc không khớp định danh sẽ dẫn đến lỗi kỹ thuật (`FAIL` / `BLOCKED`), không được coi là các hàng chất lượng để chấm điểm.
4. **Một Lượt Chạy Chính Duy Nhất (Single Primary Run)**: Chỉ cho phép một lượt chạy đánh giá chính duy nhất cho mỗi điểm kiểm tra của cổng. Các lần thử lại lỗi truyền tải đã khai báo trước không làm thay đổi định danh lượt chạy.

## Tiêu Chí Nghiệm Thu & Định Nghĩa Kết Luận

Một lượt chạy cổng phải thỏa mãn toàn bộ các điều kiện cứng:

- Không có bất kỳ sự suy thoái nào về quyền riêng tư hoặc chính sách gateway.
- Khớp chính xác định danh ứng viên sản xuất đã kích hoạt.
- Đạt kiểm toán đầy đủ 70/70 tệp ngữ liệu và khớp mã băm hash.
- Không có bất kỳ trích dẫn bịa đặt nào và từ chối trả lời chính xác ở các câu hỏi thiếu dữ liệu (`BQ11`, `BQ12`).
- Quy trình thực thi đánh giá có tính tái lập, không bị gắn cứng mã nguồn.

### Các Kết Luận Đóng Cổng Tiêu Chuẩn

- `QUALITY_GATE_PASSED`: Thang đo đã đóng băng đạt hoặc vượt ngưỡng tương đương đã đăng ký trước.
- `QUALITY_IMPROVED_NOT_PARITY`: Điểm số được cải thiện so với đường cơ sở trước đó nhưng vẫn nằm dưới ngưỡng tương đương.
- `QUALITY_GATE_FAILED`: Điểm mở mù bị suy giảm hoặc các cổng chất lượng cứng bị trượt.
- `BLOCKED_PRIVACY_ROUTE`: Giai đoạn A đã xác minh định danh ứng viên, nhưng Giai đoạn B bị chặn do phân loại `local_only` hoặc thiếu tuyến gửi ra ngoài được phê duyệt.
- `INSUFFICIENT_EVIDENCE`: Lượt chạy hoàn tất với các hàng chưa hoàn chỉnh hoặc thiếu tệp điểm số của người đánh giá.

## Các Mẫu Lệnh (Command Patterns)

### Kiểm Tra Trước Giai Đoạn A Không Dùng Provider (Provider-Free Stage A Preflight)

```powershell
py -3 scripts/battle_notebooklm_rag_v2.py --source-root tailieugoc --preflight --privacy-label local_only --rag-profile bge_m3_hybrid --production-deployment-manifest config/workspace_chat_rag_v2.local.json
```

### Chuẩn Bị Chỉ Mục Workspace (Workspace Index Staging)

```powershell
py -3 scripts/battle_notebooklm_rag_v2.py --source-root tailieugoc --workspace-stage --privacy-label local_only --production-deployment-manifest config/workspace_chat_rag_v2.local.json
```

### Chạy Thử Khô Giai Đoạn A Không Dùng Provider (Provider-Free Stage A Dry Run)

```powershell
py -3 scripts/battle_notebooklm_rag_v2.py --source-root tailieugoc --dry-run --privacy-label local_only --rag-profile bge_m3_hybrid --production-deployment-manifest config/workspace_chat_rag_v2.local.json --workspace-staging-manifest <path-to-stage-manifest>
```

