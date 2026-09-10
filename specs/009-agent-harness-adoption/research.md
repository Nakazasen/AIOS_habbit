# Nghiên cứu và quyết định

**Ngày đối chiếu**: 2026-09-10

## 1. Hiện trạng repo là nền rời, chưa phải vòng Agent hoàn chỉnh

**Quyết định**: dùng lại `agent_task_pack.py`, `coding_assistant.py`, `agent_result_import.py` và policy hiện có theo hướng nâng tương thích; không coi `workspace_agent_orchestrator.py` cùng bridge NVIDIA là runtime hoàn chỉnh của feature 009.

**Lý do**: code hiện có đã kiểm tra hash, scope, report schema và từ chối PASS tự khai khi thiếu object observed evidence. Tuy nhiên tuyến Workspace Agent giữ proposal trong RAM, gửi raw command khi approve, không bind proposal với base/file/policy/expiry và chưa tạo Git worktree. Bridge hiện truyền toàn bộ `os.environ` cho tiến trình con. UI Workspace Chat đang ẩn; form Case có thể tạo `tests_passed=True` từ checkbox và một số nhánh lỗi vẫn gọi trạng thái thành công, nên chưa phải bằng chứng quan sát hay hợp đồng lỗi đúng. Graph codebase cũng nối trực tiếp `agent_result_import.py` với Task Pack và test, nhưng không có node protocol/adapter runtime kế thừa.

**Phương án khác đã cân nhắc**: mở lại UI và vá trực tiếp bridge hiện có. Loại vì sẽ ghép hai lifecycle khác nhau, tiếp tục mất resume/idempotency và biến bridge tạm thành harness song song.

## 2. Dùng adapter trước, không fork runtime

**Quyết định**: OpenCode server là ứng viên chính cho G1. Chỉ tạo adapter sau khi một probe trên bản pin chứng minh health/version, session, event stream, read/search và deny write/command trước thực thi. Không fork trong G1.

**Lý do**: tài liệu OpenCode công bố headless server, OpenAPI 3.1 tại `/doc`, session create/status/abort/diff/revert, permission response, file search và SSE `/event`. Permission hỗ trợ `allow`, `ask`, `deny`, nhưng semantics thay đổi theo version; vì vậy cấu hình không thay thế negative test của AIOS.

**Phương án khác đã cân nhắc**:

- Gọi OpenCode CLI rồi parse text: đơn giản lúc đầu nhưng yếu cho session/event/idempotency và error contract.
- Fork OpenCode: quyền kiểm soát cao hơn nhưng tăng gánh nặng upstream, supply chain và bề mặt bảo mật trước khi có bằng chứng adapter không đủ.
- Mở rộng bridge NVIDIA thành runtime chính: không phù hợp ADR-0008 và không giải quyết session persistence bằng contract chuẩn.

Nguồn: [OpenCode server](https://dev.opencode.ai/docs/server/), [OpenCode permissions](https://opencode.ai/docs/permissions/), [OpenCode license](https://github.com/anomalyco/opencode/blob/dev/LICENSE).

## 3. Cline là benchmark và fallback có điều kiện

**Quyết định**: dùng Cline để đối chiếu checkpoint, approval, resume và headless; chỉ spike adapter Cline khi OpenCode không đạt G1 theo cùng rubric.

**Lý do**: Cline mô tả checkpoint bằng shadow Git độc lập với lịch sử repo chính và có đường restore qua phiên editor. SDK/CLI có lifecycle, persistence và permission, nhưng chế độ tự duyệt có thể mở rộng quyền đáng kể; AIOS vẫn phải áp policy riêng và không kế thừa mặc định auto-approve.

**Phương án khác đã cân nhắc**: tích hợp đồng thời OpenCode và Cline. Loại vì nhân đôi adapter/test trước khi biết ứng viên chính có thiếu capability hay không.

Nguồn: [Cline checkpoints](https://docs.cline.bot/core-workflows/checkpoints), [Cline permission handling](https://docs.cline.bot/sdk/guides/permission-handling), [Cline SDK architecture](https://docs.cline.bot/sdk/architecture/overview), [Cline license](https://github.com/cline/cline/blob/main/LICENSE).

## 4. AIOS giữ policy và observed verification

**Quyết định**: permission của runtime là lớp chặn thứ hai; AIOS mới là nguồn quyết định cuối. Verifier AIOS tự lấy command từ Task Pack, chạy trong worktree kiểm chứng và quan sát exit code, timeout, Git status cùng file digest. Model report, runtime summary và checkbox UI chỉ là dữ liệu tự khai.

**Lý do**: runtime có thể đổi version, provider hoặc semantics permission. Bằng chứng thực thi phải tái hiện độc lập và không được sinh bằng cách copy field từ report. Đây là điều kiện của FR-001, FR-009 và Hiến chương.

**Phương án khác đã cân nhắc**: tin exit code/runtime event do adapter chuyển tiếp. Loại vì adapter hoặc model có thể báo sai, và partial hunk cần kiểm thử lại đúng payload được duyệt.

## 5. Worktree theo task, không cho runtime ghi main workspace

**Quyết định**: AIOS tạo Git worktree từ base commit cho mỗi task ghi. Workspace đích bẩn bị chặn ở chế độ ghi; người dùng phải tự làm sạch hoặc tiếp tục chỉ đọc. Runtime chỉ được cwd/mount worktree task. Apply vào workspace thật xảy ra sau approval, verification và revalidation.

**Lý do**: cách này tạo ranh giới filesystem rõ, giữ nguyên thay đổi người dùng và cho phép xóa worktree task như rollback kỹ thuật. Nó cũng tách hành vi Agent khỏi editor/terminal hiện hữu.

**Phương án khác đã cân nhắc**:

- Cho runtime sửa main rồi dùng `git restore`: có thể ghi đè thay đổi chưa commit và vi phạm yêu cầu phê duyệt trước apply.
- Chỉ copy thư mục: khó giữ symlink, rename/delete, mode và base commit chính xác.
- Container đầy đủ: tăng phụ thuộc và không cần cho bản Windows một người dùng đầu tiên.

## 6. Proposal bất biến; partial hunk nằm trong decision

**Quyết định**: proposal lưu manifest file/hunk, before/after digest, base commit, task/policy/runtime binding và expiry. Proposal không đổi sau khi tạo. Approval là record append-only chứa đúng tập `selected_hunk_ids` và `selection_digest`.

**Lý do**: sửa proposal khi bỏ một hunk làm digest/approval cũ mơ hồ. Tách proposal và decision bảo toàn lịch sử, chống replay và cho verifier dựng đúng payload được duyệt.

**Phương án khác đã cân nhắc**: tạo proposal mới cho mọi click hunk. An toàn nhưng gây churn không cần thiết; selection digest trong decision vẫn bind chính xác và dễ audit hơn.

## 7. Event ledger của AIOS bọc event runtime

**Quyết định**: adapter ánh xạ event upstream vào envelope AIOS có sequence tăng đơn điệu, `previous_event_digest`, idempotency key và payload đã làm sạch. Runtime cursor được lưu để reconnect nhưng không dùng làm khóa duy nhất chống ghi lặp.

**Lý do**: tài liệu OpenCode có SSE nhưng không cam kết trong kế hoạch rằng mọi version đều cung cấp replay cursor đủ mạnh. Ledger AIOS cho phép phát hiện gap/duplicate và giữ protocol ổn định khi đổi runtime.

**Phương án khác đã cân nhắc**: lưu toàn bộ SSE/transcript. Loại vì tăng dữ liệu thô trong Case, khóa nhà cung cấp và tạo rủi ro privacy.

## 8. Cancel/resume không tự đoán kết quả action

**Quyết định**: action mất kết nối chuyển `interrupted_unknown`. Resume phải đối chiếu session, process, worktree digest và receipt trước khi đi tiếp. Write/command không được tự replay. Cancel phải dừng cây tiến trình và ghi residue nếu không xác minh được trạng thái sạch.

**Lý do**: retry mù có thể áp patch hoặc chạy lệnh hai lần. Idempotency chỉ an toàn khi payload và outcome cũ đã được nhận diện.

**Phương án khác đã cân nhắc**: retry toàn task từ checkpoint gần nhất. Chỉ được phép sau rollback/đối chiếu rõ; không dùng làm mặc định.

## 9. Báo lỗi là contract dữ liệu, không phải ghép chuỗi UI

**Quyết định**: tạo `agent_error_report_v1` từ reason code nội bộ và observed facts. Renderer tiếng Việt sinh summary, impact, next actions, trạng thái resume/rollback và receipt refs. Raw exception/stdout/stderr chỉ ở vùng local task theo retention, có locator/digest nếu cần điều tra.

**Lý do**: lỗi đến từ runtime, Git, Windows process, policy và verifier. Nếu từng UI tự ghép chuỗi, dễ lộ traceback/path/secret và khó test tính nhất quán.

**Phương án khác đã cân nhắc**: dùng `str(error)` rồi qua sanitizer chung. Loại vì sanitizer không đủ ngữ cảnh để phân biệt bước thất bại, outcome mơ hồ và hành động khắc phục.

## 10. Code-OSS chỉ là client mỏng

**Quyết định**: extension dùng Tree View, command và diff API chuẩn để hiển thị task/event/proposal/error; chỉ dùng webview khi API gốc không thể trình bày partial hunk cần thiết. Extension không chạy model, không tự quyết quyền và không ghi file trực tiếp.

**Lý do**: Code-OSS đã cung cấp editor, SCM, terminal, LSP và debugger. Tài liệu extension khuyến nghị Tree View cho danh sách/hierarchy và hạn chế webview khi API chuẩn đủ dùng.

**Phương án khác đã cân nhắc**: xây UI editor/terminal trong Streamlit hoặc webview lớn. Loại vì trùng chức năng, tăng bề mặt bảo mật và làm policy bị chia đôi.

Nguồn: [Tree View API](https://code.visualstudio.com/api/extension-guides/tree-view), [Extension capabilities](https://code.visualstudio.com/api/extension-capabilities/overview), [Code-OSS repository](https://github.com/microsoft/vscode).

## 11. Không thêm kho session hoặc sao chép dữ liệu thô vào Case

**Quyết định**: runtime giữ session chi tiết trong vùng cục bộ của nó. `workspace_cases.sqlite` chỉ nhận binding ID/version, state, digest, receipt đã làm sạch và locator local. Diff đầy đủ, transcript và command output thô ở vùng task `local_only`, có retention và cleanup idempotent.

**Lý do**: giữ đúng ADR-0008, tránh database thứ năm, giảm dữ liệu nhạy cảm trong hồ sơ và vẫn truy vết qua digest.

**Phương án khác đã cân nhắc**: sao chép runtime session sang SQLite để dễ query. Loại vì khóa schema theo provider, giữ raw quá mức và mở rộng migration không cần thiết.

## 12. Điểm đã giải quyết và điểm chỉ được khóa bằng cổng

Không còn câu hỏi thiết kế cần làm rõ. Các giá trị sau không được suy đoán trong artifact kế hoạch mà phải trở thành evidence của G1/G7:

- version/checksum/gói cài OpenCode hoặc Cline;
- endpoint/capability thực tế đọc từ OpenAPI bản pin;
- event ordering/reconnect và hành vi permission trên Windows;
- khả năng dừng cây tiến trình và path Unicode;
- license notices/SBOM của bản được đóng gói.

Thiếu một điểm bắt buộc làm cổng tương ứng `BLOCKED`; không giả lập capability ở adapter và không đổi Goal thành `PASS`.
