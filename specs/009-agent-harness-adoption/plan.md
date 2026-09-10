# Kế hoạch triển khai: Agent lập trình và thao tác file có kiểm soát

**Mã tính năng**: `009-agent-harness-adoption` | **Nhánh hiện tại**: `gate1-local-case-sqlite` | **Ngày cập nhật**: 2026-09-10 | **Đặc tả**: [spec.md](spec.md)

## 1. Tóm tắt

Hoàn thiện đường Agent sửa file bằng cách nối các nền Task Pack, proposal, policy và nhập báo cáo hiện có với một runtime kế thừa qua adapter có version. AIOS giữ quyền quyết định, phê duyệt, worktree, digest, receipt, verifier và hồ sơ bằng chứng; runtime giữ phiên và vòng model–tool; Code-OSS chỉ là mặt bàn editor/SCM/terminal. Bản đầu không dựng harness, editor, terminal hoặc kho session mới.

Điểm kết thúc của feature là một vòng có thể tái hiện: tạo Task Pack → chạy Agent trong Git worktree tách biệt → tạo proposal bất biến → duyệt toàn bộ hoặc một phần hunk → verifier chạy lệnh cố định và quan sát trạng thái → áp dụng vào workspace thật hoặc giữ nguyên → sinh báo cáo lỗi tiếng Việt và rollback khi cần. Lời model và checkbox giao diện không bao giờ là bằng chứng kiểm thử.

## 2. Bối cảnh kỹ thuật

- **Ngôn ngữ và phiên bản**: Python 3.11 cho Gateway/adapter/verifier; TypeScript chỉ cho extension Code-OSS mỏng ở G5.
- **Phụ thuộc chính**: Git CLI và Git worktree; runtime OpenCode cục bộ qua HTTP/OpenAPI/SSE sau khi vượt G1; API extension Code-OSS. Cline chỉ được đánh giá theo cùng rubric nếu OpenCode không đạt G1.
- **Lưu trữ**: `workspace_cases.sqlite` chỉ lưu metadata, digest, trạng thái và receipt đã làm sạch. Runtime tự giữ session kỹ thuật; transcript, diff đầy đủ và stdout/stderr thô nằm trong vùng cục bộ theo task hoặc bị xóa theo retention, không sao chép vào hồ sơ Case. Không tạo database session mới.
- **Kiểm thử**: `pytest`, contract test adapter, negative test quyền, fault injection, Git fixture, E2E Windows sạch và benchmark cố định.
- **Nền tảng đích**: Windows 10/11, cục bộ trước, một người dùng, một task ghi tại một thời điểm.
- **Loại dự án**: ứng dụng desktop/web cục bộ bằng Streamlit, có CLI/headless và extension Code-OSS đi kèm.
- **Mục tiêu vận hành**: event được truyền tăng dần để UI không chờ toàn bộ task; mọi command tuân thủ time/output/step budget trong Task Pack; cancel phải dừng cả cây tiến trình; ngưỡng thời gian định lượng được khóa trong evidence G1/G8 thay vì suy đoán trong kế hoạch.
- **Ràng buộc**: deny mặc định; bind server `127.0.0.1` và xác thực cục bộ; không commit/push/merge/deploy; không quyền admin; không ghi ngoài task worktree; không đường trực tiếp từ RAG answer đến tool ghi; không tin PASS tự khai.
- **Quy mô bản đầu**: một repo, một task ghi, một runtime session hoạt động và một chuỗi proposal tại một thời điểm; hỗ trợ nhiều file và command job bị giới hạn.
- **Sai lệch quy trình cần ghi nhận**: `setup-plan.ps1 -Json` nhận diện feature 010 theo nhánh hiện tại. Lượt này dùng feature 009 theo phạm vi được giao và không ghi đè artifact 010; trước bước `/speckit-tasks` phải truyền hoặc chọn đúng feature 009.

Không còn điểm cần làm rõ. Phiên bản runtime cụ thể không phải câu hỏi thiết kế: G1 phải đo rồi khóa version/checksum trước khi cho phép G2.

## 3. Hiện trạng và khoảng trống

| Lát cắt | Bằng chứng hiện có | Trạng thái thiết kế |
|---|---|---|
| Task Pack | `agent_task_pack.py` có schema v1, hash, allowlist và xuất cục bộ; có unit test | Nền dùng lại; cần bổ sung baseline workspace, runtime capability và budget mà không phá v1 |
| Proposal lập trình | `coding_assistant.py` có diff digest, scope và approve/reject | Mới ở mức object; chưa bind base/file digest, expiry, policy version, actor/scope và tập hunk |
| Nhập kết quả | `agent_result_import.py` kiểm report hash, phạm vi và đòi observed evidence | Nền dùng lại; chưa có verifier tự chạy và receipt append-only từ command thực |
| Workspace Agent | `workspace_agent_orchestrator.py` và bridge NVIDIA hỗ trợ khảo sát/proposal thủ công | Tuyến thử nghiệm tách rời; proposal giữ trong RAM, chưa có runtime protocol, event replay, worktree hay resume |
| Giao diện | Workspace Chat có khối Agent nhưng bị feature flag cứng ẩn; hồ sơ Case có form Task Pack/proposal/report | Chưa phải hành trình hằng ngày; form nghiệm thu hiện có thể dựng `tests_passed=True` từ checkbox nên không được dùng làm đường kiểm chứng |
| Runtime kế thừa | Chưa có `agent_runtime_protocol.py`, adapter OpenCode, probe hoặc fixture G1 | Chưa triển khai và chưa có bằng chứng capability |
| E2E sửa–test–sửa lỗi | Chưa có test worktree, partial hunk, cancel/resume, Windows hoặc clean-machine | Khoảng trống chặn Goal 009 |

Theo bằng chứng hiện tại, T001–T005 chưa có artifact G1 đủ điều kiện đánh dấu hoàn thành. Toàn bộ T006 trở đi vẫn bị chặn bởi quyết định G1; danh sách checkbox cũ không phải bằng chứng trạng thái.

## 4. Kiểm tra Hiến chương trước thiết kế

| Cổng | Kết quả |
|---|---|
| Bằng chứng trước tuyên bố | Đạt về thiết kế: mọi kết quả phải qua verifier và receipt; model chỉ được tự khai |
| Ưu tiên cục bộ và đồng ý | Đạt: runtime loopback, Task Pack khóa privacy route, dữ liệu thô không vào Case |
| Khả năng thay thế | Đạt: protocol AIOS độc lập runtime; OpenCode là ứng viên, Cline là fallback theo cùng rubric |
| Tiếng Việt duy nhất | Đạt: UI, CLI, nhật ký vận hành và báo cáo lỗi dùng tiếng Việt; lỗi upstream được ánh xạ |
| Kỷ luật thay đổi | Đạt: thiết kế trước code, worktree tách biệt, rollback và cổng G1 dừng sớm |
| Ranh giới legacy | Đạt: không import hoặc khôi phục Studio/Case Cockpit; bridge NVIDIA hiện có không được nâng thành harness song song |

Không yêu cầu ngoại lệ Hiến chương.

## 5. Kiến trúc được chọn

```text
Workspace Chat / Code-OSS / CLI
              ↓ cùng hợp đồng AIOS
Gateway Agent: Task Pack + policy + approval + receipt + báo lỗi
              ↓ adapter có version và capability handshake
Runtime kế thừa: session + model–tool + event + cancel/resume
              ↓ chỉ thao tác trong vùng được cấp
Git worktree theo task + vùng output local_only
              ↓ proposal/hunk bất biến
Verifier AIOS chạy lệnh cố định trong worktree kiểm chứng
              ↓ revalidate base/digest rồi mới apply
Workspace thật + hồ sơ agent_work đã làm sạch
```

### 5.1 Quyền sở hữu

- AIOS sở hữu policy, Task Pack, privacy route, worktree, proposal/decision, idempotency, verifier, receipt, báo lỗi, apply và liên kết Case.
- Runtime sở hữu phiên kỹ thuật, vòng model–tool, event stream và cơ chế cancel/resume mà adapter kiểm chứng được.
- Code-OSS sở hữu editor, diff viewer, terminal, SCM, LSP và debugger; extension chỉ trình bày state và gửi decision về Gateway.
- Main workspace không được runtime mount làm nơi ghi. Runtime chỉ thấy worktree theo task.

### 5.2 Luồng proposal và apply

1. AIOS khóa snapshot đầu vào gồm HEAD, trạng thái workspace và digest file được phép. Workspace bẩn làm task ghi bị chặn với hướng dẫn tiếng Việt; vẫn có thể chạy chế độ chỉ đọc.
2. AIOS tạo worktree từ đúng base commit. Runtime sửa và chạy tool trong worktree này.
3. AIOS tính lại diff từ filesystem/Git, tách hunk ổn định và tạo proposal bất biến. Không dùng diff do model tự khai.
4. Quyết định duyệt bind `task_id`, `session_id`, proposal digest, actor, policy version, expiry và tập hunk. Chọn một phần hunk không sửa proposal gốc; nó tạo selection digest trong decision.
5. Verifier tạo worktree kiểm chứng sạch từ cùng base, chỉ áp dụng đúng tập hunk đã duyệt và chạy command cố định lấy từ Task Pack. Exit code, timeout, trạng thái Git và digest do verifier quan sát.
6. Chỉ khi verifier đạt và snapshot workspace thật vẫn khớp, AIOS mới áp dụng đúng payload đã kiểm chứng. Mismatch hoặc hết hạn làm proposal vô hiệu và yêu cầu tạo lại.
7. Apply lỗi phải phục hồi snapshot trước apply; không sửa lịch sử Git, không xóa thay đổi có trước của người dùng.

### 5.3 Cancel, resume và idempotency

- Mỗi action có `idempotency_key` gắn payload digest. Cùng key/cùng payload trả receipt cũ; cùng key/khác payload bị từ chối.
- Event AIOS có sequence tăng đơn điệu và digest trước; cursor runtime chỉ là dữ liệu adapter. Reconnect đọc lại từ sequence cuối đã ghi.
- Sau mất kết nối, action đang chạy chuyển `interrupted_unknown`; không tự chạy lại write/command khi chưa đối chiếu filesystem, process và receipt.
- Cancel dừng nhận action mới, yêu cầu runtime abort, dừng cây tiến trình command, chụp trạng thái và ghi kết quả `cancelled`, `cancelled_with_residue` hoặc `interrupted_unknown`.
- Resume chỉ tiếp tục từ checkpoint đã đối chiếu; proposal/approval hết hạn không được phục hồi quyền thực thi.

### 5.4 Báo cáo lỗi

Mọi lỗi qua [hợp đồng báo lỗi](contracts/agent-error-report-v1.md). Báo cáo gồm bước thất bại, reason code, trạng thái quan sát, receipt liên quan, ảnh hưởng, bước người dùng có thể làm tiếp và khả năng resume/rollback. Traceback, absolute path, secret, prompt/transcript và stdout/stderr thô không xuất hiện trên UI hoặc hồ sơ thường.

## 6. Cổng triển khai

| Cổng | Phạm vi | Điều kiện ra |
|---|---|---|
| G0 | Đồng bộ đặc tả, kế hoạch, nghiên cứu, mô hình dữ liệu, contract và Gate Card | Owner chấp thuận ranh giới; `/speckit-tasks` sinh task mới từ bộ artifact này |
| G1 | Pin OpenCode; probe health/version/session/event/read/search và negative write/command trên Windows | Tất cả capability bắt buộc có receipt; nếu thiếu thì `BLOCKED` và đánh giá Cline theo cùng rubric |
| G2 | Protocol chung, session binding, event ledger, cancel/resume/idempotency | Restart đọc lại state, không lặp action và không thăng quyền |
| G3 | Worktree, proposal nhiều file, command job, snapshot, partial hunk, conflict và rollback | Main workspace không đổi trước apply; dirty/mismatch/expiry fail-closed; rollback sạch |
| G4 | Vòng plan → edit → test → repair; verifier độc lập; báo cáo lỗi | Fixture Python và TypeScript chứng minh cả đường lỗi và đường đạt; không tin model/checkbox |
| G5 | CLI/headless và extension Code-OSS mỏng dùng cùng protocol | Cùng task/state/decision qua hai client; không sửa JSON thủ công; UI tiếng Việt |
| G6 | Receipt vào `agent_work`, redaction, retention và lesson candidate có duyệt | Truy ngược digest được; raw không vào Case; reject/revoke/unverified không thành bài học |
| G7 | Threat model, secret scan, SBOM/license/notices, nâng upstream và gói Windows sạch | Cài đặt lặp lại được, bind/xác thực cục bộ, không lộ secret |
| G8 | 12 tình huống bắt buộc, 10 benchmark mù và full quality gate | Đạt SC-001–SC-007; reviewer độc lập mới quyết định trạng thái Goal |

Không bắt đầu G2 nếu G1 chưa có evidence. Không bật đường ghi UI trước khi G3–G4 đạt contract test.

## 7. Cấu trúc dự kiến

### 7.1 Artifact feature

```text
specs/009-agent-harness-adoption/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── agent-runtime-protocol.md
│   └── agent-error-report-v1.md
└── tasks.md                 # chỉ được cập nhật ở bước /speckit-tasks riêng
```

### 7.2 Mã nguồn dự kiến sau bước task

```text
src/aios_habit/
├── agent_task_pack.py             # nâng tương thích schema hiện có
├── coding_assistant.py            # proposal/decision/partial hunk
├── agent_result_import.py         # compatibility và import receipt đã làm sạch
├── workspace_agent_policy.py      # quyết định path/tool/command/expiry
├── workspace_agent_orchestrator.py# lifecycle, worktree, apply, rollback
├── agent_runtime_protocol.py      # contract AIOS độc lập runtime
├── opencode_runtime_adapter.py    # chỉ tạo sau khi G1 đạt
├── agent_runtime_cli.py           # client headless ở G5
└── agent_error_report.py          # ánh xạ lỗi tiếng Việt và redaction

extensions/aios-agent-companion/   # extension Code-OSS mỏng, chỉ mở ở G5
scripts/probe_opencode_runtime.py
tests/fixtures/agent_harness/
tests/test_agent_runtime_*.py
tests/test_agent_worktree_safety.py
tests/test_agent_companion_ui.py
```

Quyết định cấu trúc: nâng module US6 hiện có, chỉ thêm protocol/adapter/report ở nơi ranh giới mới thật sự cần. Không mở package harness hoặc service/database song song.

## 8. Tương thích và di chuyển

- Reader v1 của `aios_agent_task_pack_v1` và `aios_agent_report_v1` vẫn đọc được artifact lịch sử; đường chạy mới dùng schema version mới hoặc extension field có validator rõ, không âm thầm đổi nghĩa field v1.
- Proposal/session tạm trong bridge hiện tại không được migration thành approval hợp lệ; sau restart phải tạo proposal mới.
- Dữ liệu Case mới chỉ thêm bảng/field metadata theo migration chuẩn, có backup, `quick_check` và rollback. Payload raw không chuyển vào SQLite.
- Khối Agent Workspace Chat hiện ẩn tiếp tục bị ẩn cho đến G5; form nghiệm thu dựng observed evidence từ checkbox phải bị loại khỏi đường đạt trước khi mở UI.
- Bridge NVIDIA hiện có có thể giữ cho hành vi đọc legacy trong lúc chuyển tiếp nhưng không được tính là bằng chứng G1/G4 và không được làm nguồn policy.

## 9. Rủi ro và biện pháp

| Rủi ro | Biện pháp khóa trong thiết kế |
|---|---|
| API/permission OpenCode drift | Pin version/checksum, đọc OpenAPI lúc probe, contract test capability và dừng G1 khi lệch |
| Event SSE thiếu cursor ổn định | AIOS tự ghi sequence/digest; reconnect đối chiếu session state, không tự replay action mơ hồ |
| Partial hunk làm test cũ mất giá trị | Tạo worktree verifier chỉ chứa tập hunk được duyệt và chạy lại toàn bộ acceptance checks |
| Workspace thật đổi sau duyệt | So HEAD, status digest và file digest ngay trước apply; mismatch yêu cầu proposal mới |
| Cancel không dừng process con trên Windows | Job/process-tree abstraction có fault test; trạng thái residue không được báo hoàn tất |
| Diff/output chứa secret | Lưu payload trong vùng local task, scan/redact trước receipt/UI; Case chỉ giữ locator/digest đã làm sạch |
| SQLite migration làm hỏng Case | Online Backup, `quick_check`, transaction atomic và rollback migration |
| Hai tuyến Agent hiện tại bị nối chắp vá | Một protocol chung; adapter bridge/runtime chỉ triển khai contract, không gọi chéo UI/helper |

## 10. Kiểm tra Hiến chương sau thiết kế

Thiết kế sau Phase 1 vẫn đạt toàn bộ cổng: evidence được quan sát độc lập; dữ liệu raw tách local; runtime thay được; UI/báo lỗi tiếng Việt; worktree và rollback bảo vệ dữ liệu; cấu trúc không khôi phục legacy hay thêm kho session. Không có vi phạm cần ghi vào bảng theo dõi độ phức tạp.

## 11. Hướng dẫn sinh task ở bước riêng

Bước /speckit-tasks phải thay danh sách cũ bằng task nhỏ, có dependency và test trước, theo thứ tự sau:

1. **Khóa compatibility trước G1**: fixture cho aios_agent_task_pack_v1 và aios_agent_report_v1; contract reader cũ; quyết định version/migration cho schema mới. Không đổi nghĩa field v1.
2. **G1 độc lập**: pin supply-chain; tạo fixture Python/TypeScript; probe OpenCode; contract test capability/negative write-command; ghi quyết định Gate Card. Mọi task G2+ phụ thuộc task quyết định này.
3. **Protocol và persistence**: model/envelope/version, session binding, event/receipt append-only, migration SQLite có backup/quick-check/rollback, error-report builder và redaction.
4. **Worktree và quyền**: snapshot, worktree manager, canonical command spec, proposal/decision/expiry, partial hunk, verifier độc lập, apply/rollback và fault tests.
5. **Vòng Agent E2E**: plan–edit–test–repair; cancel/resume/idempotency; process-tree Windows; producer/persistence/UI contract của báo lỗi.
6. **Hợp nhất tuyến cũ**: chuyển orchestrator sang protocol; adapter runtime không kế thừa toàn bộ os.environ; giữ bridge NVIDIA ngoài đường đạt hoặc deprecate rõ; xóa đường checkbox dựng observed evidence; mọi nhánh lỗi UI phải dùng error state, không gọi st.success.
7. **Client và hồ sơ**: CLI/headless trước, extension Code-OSS mỏng sau; cùng contract; persistence agent_work; lesson chỉ từ receipt verified.
8. **An toàn và nghiệm thu**: privacy/threat/supply-chain, Windows clean-machine, 12 tình huống, 10 benchmark, full quality gate và audit độc lập.

Mỗi task implementation phải có test trọng điểm, file allowlist và tiêu chí rollback. Task audit cuối không được giao cho cùng Execution Specialist tự xác nhận.

## 12. Artifact liên quan và bước tiếp theo

- Quyết định kỹ thuật và nguồn: [research.md](research.md).
- Mô hình dữ liệu/trạng thái: [data-model.md](data-model.md).
- Hợp đồng runtime: [contracts/agent-runtime-protocol.md](contracts/agent-runtime-protocol.md).
- Hợp đồng báo lỗi: [contracts/agent-error-report-v1.md](contracts/agent-error-report-v1.md).
- Kịch bản xác minh: [quickstart.md](quickstart.md).

Bước kế tiếp bắt buộc là chạy `/speckit-tasks` riêng cho feature 009 và thay danh sách task cũ bằng danh sách phụ thuộc theo thiết kế đã làm mới. Lượt kế hoạch này không triển khai code, không đánh dấu task hoàn thành và không thay trạng thái Goal thành `DONE`/`PASS`.
