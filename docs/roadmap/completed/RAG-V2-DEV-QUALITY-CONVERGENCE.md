# Hội Tụ Chất Lượng Dev Cho RAG v2 (RAG-V2-DEV-QUALITY-CONVERGENCE)

Status: `DONE`

## Mục Tiêu (Goal)

Tích hợp các thành phần nguyên thủy độc lập của RAG v2 vào một đường ống chỉ dành cho môi trường phát triển (Dev-only) có thể đo lường được, sau đó cải thiện độ bao phủ truy xuất, chất lượng trích dẫn, tính hành động và khả năng tổng hợp xuyên nguồn so với đường cơ sở đo chuẩn năng lực đã đóng.

Cổng này có thể tạo ra một ứng viên phù hợp cho kế hoạch tích hợp UI chính sau này. Bản thân cổng này không tự ý di chuyển hay kích hoạt RAG v2 trong Workspace Chat.

## Điều Kiện Tiên Quyết và Đường Cơ Sở Đã Khóa

- `RAG-V2-HYBRID-RETRIEVAL-MIN`: `DONE`.
- `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN`: `DONE`.
- `RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE`: `DONE`.
- `NOTEBOOKLM-BATTLE-RERUN-RAG-V2`: `DONE`.
- Đo chuẩn mù đã đóng: 11 hàng dùng chung, RAG v2 **2.898/5** so với NotebookLM **3.807/5**.
- Hồi quy RAG v2 tập trung lúc mở cổng: **61 passed** vào ngày 2026-07-25.
- Cây làm việc chứa các thay đổi của các cổng đã được phê duyệt trước đó; cổng này không được đặt lại hay ghi đè các sửa đổi không liên quan.

## Phạm Vi (Scope)

1. Thêm luồng điều phối chỉ dành cho Dev bao gồm registry chuyển đổi, chia chunk nhận biết cấu trúc, chỉ mục cục bộ, lập kế hoạch truy vấn và gói bằng chứng.
2. Thêm giao diện dòng lệnh cục bộ cho việc nạp (ingest), truy vấn (query), kiểm tra (inspect) và đánh giá (evaluation).
3. Thay thế việc sinh ứng viên từ vựng quét toàn bảng bằng SQLite FTS5/BM25 khi khả dụng, giữ nguyên cơ chế dự phòng tất định cục bộ.
4. Cải thiện độ bao phủ truy xuất cấp tập hợp và tính đa dạng nguồn tổng quát.
5. Thêm lập kế hoạch tổng hợp độc lập với provider, xác thực trích dẫn và phương án dự phòng cục bộ tất định trung thực.
6. Mở rộng khung đánh giá cục bộ cho bằng chứng bắt buộc, trích dẫn, độ phủ xuyên nguồn, tính hành động, các tuyên bố bị cấm và việc từ chối trả lời.
7. Phát lại đo chuẩn cục bộ riêng tư và, chỉ sau khi các cổng cục bộ đạt, mới thực hiện lượt chạy lại so tài / tổng hợp live được ủy quyền riêng biệt.

## Phi Mục Tiêu và Các Khóa Cứng (Non-goals and hard locks)

- Không thay đổi bố cục, nhãn, luồng của chủ sở hữu hay kích hoạt runtime chính của Workspace Chat (`Đóng băng UI`).
- Không di chuyển luồng truy xuất cũ của Workspace Chat trong cổng này.
- Không gắn cứng mã nguồn về nghiệp vụ, khách hàng, câu trả lời benchmark hay ngữ liệu riêng tư trong RAG v2.
- Không mặc định dùng cloud, không gọi provider ngầm, không ghi log credential, không mở A18 hay P1.0.
- Không tuyên bố tương đương trước khi có bằng chứng đo chuẩn mù hỗ trợ.
- Không xóa hay di chuyển các chỉ mục cục bộ cũ.

## Danh Sách Cho Phép (Allowlist)

Danh sách cho phép triển khai chính:
- `src/aios_habit/rag_v2/**`
- `scripts/rag_v2_dev.py`
- `scripts/battle_notebooklm_rag_v2.py` (chỉ sau khi các cổng Dev cục bộ đạt màu xanh)
- `tests/test_rag_v2_*.py`
- `tests/test_battle_notebooklm_rag_v2.py`
- Các fixture giả lập dưới `tests/fixtures/rag_v2_dev/**`
- Thẻ Cổng này, `ROADMAP.md`, và tài liệu đóng cổng

Mọi thay đổi ngoài danh sách này đều yêu cầu cập nhật phạm vi rõ ràng trước khi chỉnh sửa.

## Ràng Buộc Bảo Mật (Privacy Constraints)

- Mặc định chỉ dùng cục bộ cho nạp dữ liệu, truy xuất, bằng chứng và đánh giá.
- Luồng Dev tuyệt đối không đọc `API Key.txt` hay bất kỳ thông tin xác thực provider nào trừ khi một cổng con live tường minh được gọi.
- Đầu vào riêng tư và câu trả lời thô tự sinh giữ dưới các thư mục runtime cục bộ bị gitignore; các fixture được commit phải là dữ liệu giả lập (synthetic).
- Bằng chứng `local_only` và `confidential` tuyệt đối không được đưa vào yêu cầu tổng hợp cloud. Nhãn thiếu/không xác định sẽ áp dụng fail-closed.
- Các chẩn đoán an toàn có thể chứa số lượng, dấu vân tay ổn định, trạng thái và chỉ số tổng hợp, nhưng tuyệt đối không chứa bằng chứng riêng tư thô hoặc credential.
- Việc chọn nguồn và dấu vân tay kỳ vọng phải được thực thi trước khi xây dựng bằng chứng trả về.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

### Đường ống Dev (Dev pipeline)
- Converter -> chunker -> chỉ mục cục bộ bền vững -> truy xuất -> bằng chứng hoạt động đầu cuối qua một API độc lập duy nhất.
- Lập chỉ mục lại tăng dần thay thế các chunk cũ cho cùng một tài liệu / nguồn.
- Các nguồn bị tắt / không được chọn và nguồn có dấu vân tay cũ không thể xuất hiện trong kết quả.
- Chuyển đổi không hỗ trợ có hành vi fail-soft và có thể kiểm tra được.
- CLI mặc định trỏ vào thư mục runtime cục bộ bị gitignore và không sử dụng mạng / provider.

### Truy xuất và Bằng chứng (Retrieval and evidence)
- Truy xuất ứng viên sử dụng FTS5/BM25 khi được hỗ trợ và có phương án dự phòng tất định đã kiểm thử.
- Các biến thể truy vấn tổng quát không thể vượt qua các bộ lọc bảo mật, lựa chọn hoặc độ mới.
- Độ bao phủ tập bằng chứng được đánh giá trên toàn bộ các mục trả về, không chỉ mục đầu tiên.
- Metadata trích dẫn bảo toàn tọa độ trang, sheet, slide, mục, hàng, cột và ô khi có sẵn mà không làm lộ đường dẫn không an toàn.
- Các trường hợp giả lập đa nguồn, quy trình, so sánh, bảng biểu, đa ngôn ngữ và thiếu dữ liệu có kết quả kỳ vọng tất định.

### Tổng hợp và Chất lượng (Synthesis and quality)
- Lập kế hoạch tổng hợp độc lập với provider ánh xạ các khía cạnh bắt buộc vào bằng chứng và báo cáo các khía cạnh còn thiếu / xung đột.
- Các tuyên bố quan trọng phải ánh xạ tới các ID trích dẫn thực tế; phát hiện các trích dẫn bị thiếu hoặc không có căn cứ.
- Dự phòng cục bộ được gắn nhãn là bản tóm tắt / danh mục bằng chứng hoặc câu trả lời thiếu dữ liệu, tuyệt đối không bao giờ gắn nhãn là câu trả lời LLM chưa được xác minh.
- Đánh giá cục bộ liên tục ghi nhận các ngưỡng có phiên bản và đầu ra tổng hợp tất định.
- Không thể bù trừ sự suy giảm về quyền riêng tư hay khả năng từ chối trả lời bằng điểm số trung bình cao hơn.

### Quyết định Đề bạt (Promotion decision)
Một kế hoạch tích hợp UI chính chỉ có thể được đề xuất nếu toàn bộ các cổng cục bộ và xác thực repository đều đạt, đồng thời lượt chạy mù được ủy quyền đạt mức trung bình đã đóng của NotebookLM (**3.807/5**) hoặc bằng chứng theo cặp không còn cho thấy sự suy giảm chất lượng trên các quy trình quan trọng. Nếu không, kết luận cuối cùng vẫn là `DEV_READY_WITH_LIMITATIONS` hoặc `NOT_READY_FOR_PRIMARY_UI` với các khoảng cách còn lại.

## Kiểm Chứng (Verification)

```powershell
py -3 -m pytest -q tests/test_rag_v2_schema.py tests/test_rag_v2_adapters.py tests/test_rag_v2_converters.py tests/test_rag_v2_chunking.py
py -3 -m pytest -q tests/test_rag_v2_index.py tests/test_rag_v2_evidence.py tests/test_rag_v2_eval_harness.py tests/test_rag_v2_hardcode_guard.py
py -3 -m pytest -q tests/test_rag_v2_pipeline.py tests/test_rag_v2_synthesis.py tests/test_rag_v2_dev_cli.py
py -3 -m pytest -q tests/test_battle_notebooklm_rag_v2.py
py -3 -m compileall src tests scripts
py -3 -m pytest -q
py -3 scripts/check_docs.py
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

Các lệnh phát lại riêng tư và chạy lại trực tiếp phải được ghi nhận mà không chứa credential hoặc nội dung ngữ liệu thô.

## Hoàn Tác (Rollback)

- RAG v2 Dev vẫn tách biệt hoàn toàn khỏi Workspace Chat và có thể gỡ bỏ mà không cần di chuyển runtime sản phẩm.
- Chỉ mục Dev là các artifact cục bộ có thể tái tạo; bảng chunk chuẩn tắc giữ nguyên vẹn nếu FTS5 không khả dụng.
- Tổng hợp qua provider mặc định bị vô hiệu hóa và có thể hoàn tác độc lập.
- Chỉ hoàn tác cổng nhỏ nhất bị lỗi; bảo tồn các artifact đường cơ sở trước đó.
- Tuyệt đối không xóa chỉ mục cũ, nguồn riêng tư hoặc checkpoint benchmark trước đó như một phần của quá trình hoàn tác.

## Bằng Chứng Đóng Cổng (Closure Evidence)

- Đã triển khai điều phối Dev độc lập, CLI, truy xuất ứng viên FTS5/BM25 với dự phòng tất định, độ bao phủ bằng chứng cấp tập hợp, lập kế hoạch tổng hợp độc lập với provider, xác thực trích dẫn và đánh giá cục bộ liên tục, được bao phủ bởi bộ kiểm thử hồi quy RAG v2.
- Phát lại ngoại tuyến riêng tư: `BATTLE-RAGv2-1784998427-e33e5670`; preflight `PASS`; dấu vân tay ngữ liệu `tailieugoc` chuẩn tắc `78957a10...`; mã băm 12 câu hỏi đóng băng `e33e5670...`.
- Nạp dữ liệu phát lại: 70 tệp được duyệt, 53 tệp chuyển đổi, 17 tệp fail-soft, 767 chunk được lập chỉ mục qua `RagV2DevPipeline`.
- Bảo mật phát lại: router `SKIPPED_LOCAL_ONLY`, không cấu hình key, không tạo provider và không đọc credential. Toàn bộ 12 hàng đều được gắn nhãn chính xác là `DRY_RUN_ONLY`; chất lượng câu trả lời tự sinh do đó giữ trạng thái `INSUFFICIENT_EVIDENCE` trong đợt phát lại này.
- Hồi quy RAG v2 tập trung: 79 passed. Biên dịch toàn bộ repository và kiểm thử hồi quy: 998 passed. Hợp đồng tài liệu, kiểm toán CLI audit, import Workspace Chat và kiểm tra khoảng trắng Git: PASS vào ngày 2026-07-25.
- Không có bất kỳ thay đổi nào đối với UI Workspace Chat hay di chuyển runtime chính.

## Quyết Định Đóng Cổng (Closure Decision)

Giai đoạn triển khai Dev đã hoàn tất và Thẻ Cổng này có thể đóng lại. Kết luận cuối cùng là `DEV_READY_WITH_LIMITATIONS` và `NOT_READY_FOR_PRIMARY_UI`:
- Các cổng tích hợp Dev cục bộ và bảo mật / tính chính xác đều đạt màu xanh;
- Đo chuẩn mù trước đó vẫn là bằng chứng chất lượng câu trả lời tự sinh mới nhất (RAG v2 2.898/5 so với NotebookLM 3.807/5);
- Lượt phát lại chỉ dùng cục bộ này không thể hỗ trợ một tuyên bố tương đương mới; và
- Không có lượt chạy lại tổng hợp trực tiếp nào được ủy quyền ngầm hay thực hiện.

Một cổng được chủ sở hữu phê duyệt sau này có thể lên kế hoạch chạy lại mù trực tiếp hoặc tích hợp UI chính chỉ sau khi bằng chứng chất lượng theo cặp mới thỏa mãn các tiêu chí đề bạt. Việc đóng cổng này không mở A18/P1.0.

## Liên Kết Bằng Chứng (Evidence Links)

- Kiến trúc: `docs/rag_v2/RAG_V2_DESIGN.md`
- Đo chuẩn đường cơ sở: `docs/roadmap/completed/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md`
- Metadata phát lại tổng hợp riêng tư nằm dưới thư mục runtime cục bộ bị gitignore: `local_runs/rag_v2_dev_gate5_offline/BATTLE-RAGv2-1784998427-e33e5670/`.

