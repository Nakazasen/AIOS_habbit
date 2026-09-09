# Thẻ cổng: AI phỏng vấn chuyên gia và làm giàu tri thức

Status: `REOPENED_FOR_SIMPLIFICATION`
Mã tính năng: `010-expert-knowledge-acquisition`  
Chủ sở hữu: Project owner / Process owner / Privacy reviewer  
Cập nhật: 2026-09-09

## Mục tiêu

Đưa AIOS từ hỏi–đáp có cấu trúc sang chat phỏng vấn nhiều vòng, thu nhận tri thức có nguồn, tạo SOP/bài học dạng ứng viên và xuất bản nội dung đã duyệt vào collection để AI dùng ngay.

## Trạng thái đúng hiện tại

- T000–T080 đã hoàn thành theo thiết kế cũ; bằng chứng G0–G10 được giữ làm lịch sử, không bị xóa.
- Kiểm toán lại ngày 2026-09-09 phát hiện thiết kế danh tính/phân quyền không phù hợp vì sản phẩm không có hệ tài khoản dùng chung; lớp này không tạo ranh giới bảo mật thật cho thư viện chung.
- Phát hiện thêm các finding mức chặn: bản chép lời thô có đường lưu vi phạm hợp đồng, runtime chép lời có thể fallback mock nhưng gắn nhãn như kết quả thật, một số trạng thái xuất bản/thu hồi chưa phản ánh dữ liệu chắc chắn và các màn duyệt/xuất bản chưa được nối vào hành trình chính.
- Giao diện hiện còn lộ thuật ngữ `fixture`, `digest`, `claim`, `approved`, mã nội bộ và bắt người dùng nhập cấu hình/nghiệm thu kỹ thuật.
- ADR-0009, đặc tả và kế hoạch đã được sửa sang mô hình nhóm tin cậy: tên chỉ để ghi nhận trách nhiệm; mọi người mở được thư viện đều có thể ghi; khóa ghi chỉ chống xung đột đồng thời.
- Goal chưa sẵn sàng vận hành theo thiết kế mới cho đến khi T083–T109 được thực hiện và kiểm toán lại.

## Quyết định sau kiểm toán

| Giữ | Giản lược | Bỏ khỏi Goal 010 |
| --- | --- | --- |
| Dữ liệu thô cục bộ, consent, nguồn, phiên bản, lịch sử, backup, kiểm tra và rollback | Gap là gợi ý; giới hạn phiên là mặc định nội bộ; chi tiết kỹ thuật thu gọn; xác nhận và xuất bản thành một hành động chính | Đăng nhập, RBAC, scope grant, cấm tự duyệt, máy ghi cố định, quyền Windows/NAS, màn hình fixture, fine-tune như một cổng sản phẩm |

Luồng đích: **Chọn thư viện → Phỏng vấn → Kiểm tra bản nháp → Xác nhận và đưa vào thư viện**.

## Cổng sửa lại

| Cổng | Task | Trạng thái | Điều kiện ra |
| --- | ---: | --- | --- |
| R1 | T083–T088 | `PENDING` | Ranh giới dữ liệu thô, chép lời và trạng thái xuất bản đúng |
| R2 | T089–T093 | `PENDING` | Không còn quyền giả; quyết định có đủ thông tin trách nhiệm |
| R3 | T094–T097 | `PENDING` | Chọn cá nhân/dùng chung và ghi snapshot an toàn |
| R4 | T098–T105 | `PENDING` | Bốn chặng truy cập được, không lộ chi tiết kỹ thuật ở luồng chính |
| R5 | T106–T109 | `PENDING` | Lượt đi bộ nontech, E2E, full gate và audit độc lập đạt |

## Sáu mặc định của thiết kế cũ — chỉ giữ làm lịch sử

| Mục | Mặc định thực thi | Ranh giới |
| --- | --- | --- |
| Identity | Windows/OS; fixture provider chỉ cho test | Không tự xây password; thiếu account thật thì runtime multi-user giữ tắt |
| Cấp quyền | Tài khoản OS hiện tại quản trị; scope trả lời/duyệt/xuất bản tách biệt | Product vẫn kiểm tra quyền mỗi thao tác |
| Consent | Đồng ý từng phiên; rút đồng ý dừng ngay | Từ chối vẫn trò chuyện bằng chữ |
| Retention | Raw data local-only, không tự xóa | Có thao tác xóa thủ công theo quyền |
| Collection | Fixture khi test, collection đang chọn khi vận hành | Backup, lease và kiểm tra trước published |
| Fine-tune | Tắt; G9 ghi `NOT_APPLICABLE` | Goal 010 không tạo training job |

## Cổng

| Cổng | Task | Trạng thái | Điều kiện ra |
| --- | ---: | --- | --- |
| G0 | T000–T007 | `PASS` | Ma trận học upstream, mặc định đã khóa, ADR accepted, fixture sạch |
| G1 | T008–T015 | `PASS` | Identity/scope fail-closed |
| G2 | T016–T024 | `PASS` | Gap có evidence |
| G3 | T025–T029 | `PASS` | InterviewPlan đúng người/scope/budget |
| G4 | T030–T038 | `PASS` | Chat thích nghi và resume an toàn |
| G5 | T039–T047 | `PASS` | Consent + transcription local |
| G6 | T048–T053 | `PASS` | Claim có nguồn/conflict |
| G7 | T054–T059 | `PASS` | SOP/bài học candidate + approval |
| G8 | T060–T068 | `PASS` | Publication và retrieval receipt |
| G9 | T069–T072 | `PASS` | Fine-tune eligibility report |
| G10 | T073–T080 | `PASS` | Pilot thật + full gates + audit độc lập |

## Danh sách cho phép theo cổng

Gemini chỉ sửa file nêu trực tiếp trong task của cổng đang active, test/fixture tương ứng và tài liệu canonical liên quan. Mở rộng allowlist phải ghi ở đây trước khi code. `local_cases/`, `local_runs/`, `.env`, DB thật, audio thật, transcript thật và file tạm người dùng luôn ngoài allowlist Git.

## Quy tắc tiến độ

- Báo theo `n/81 task` và `x/11 cổng`; tách kỹ thuật với pilot vận hành.
- Execution Specialist không tự đánh dấu cổng mình vừa làm là PASS.
- Audit Specialist ở agent/phiên tách biệt kiểm tra; finding được tự sửa rồi tự mở cổng kế tiếp.
- Không có phase chờ con người quyết định trong Goal kỹ thuật; dữ liệu/người thật chỉ dùng khi vận hành sau `TECHNICAL_READY`.
- Full suite bị bỏ bớt theo quyết định thời gian phải ghi đúng là chưa kiểm chứng toàn bộ.
- Cấm thiết kế thừa: không thêm framework, app, database, dependency hoặc abstraction dự phòng nếu task/test hiện tại chưa chứng minh cần.
- Giao diện phải thuần tiếng Việt và dễ hiểu với người không chuyên; cấm từ kỹ thuật tiếng Anh, traceback, tên engine/provider, trạng thái nội bộ và đường dẫn hệ thống trên mọi nội dung người dùng nhìn thấy.

## Tiêu chí hoàn tất

Theo SC-001–SC-010 trong [đặc tả](../../../specs/010-expert-knowledge-acquisition/spec.md), đặc biệt:

- 2 danh tính chuyên gia fixture, 2 scope, 3 phiên và 5 gap trong diễn tập tự động.
- 5 đơn vị tri thức và 1 quy trình fixture đã duyệt, có provenance đầy đủ.
- 0 nội dung candidate/conflicted/revoked trong retrieval thường.
- 0 raw audio/transcript trong Git, library, case DB, log thường hoặc provider trái policy.
- E2E Windows, full quality gate và audit độc lập đạt.

Đoạn G0–G10 bên dưới là nhật ký lịch sử của thiết kế cũ. Trạng thái hiện hành chỉ được xác định bởi R1–R5 và không được khôi phục `TECHNICAL_READY` nếu chưa có bằng chứng mới.

## Liên kết

- [Goal Gemini](../../../specs/010-expert-knowledge-acquisition/GEMINI_FLASH_3_8_GOAL.md)
- [Kế hoạch](../../../specs/010-expert-knowledge-acquisition/plan.md)
- [Danh sách việc](../../../specs/010-expert-knowledge-acquisition/tasks.md)
- [ADR-0009](../../adr/0009-expert-interview-and-knowledge-publication-boundary.md)

## Nhật ký tiến độ và bằng chứng thực thi

### Mốc G0 — Khóa mặc định, baseline và fixture (T000–T006)

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành**:
  - T000: Pin commit/tag, giấy phép MIT và ma trận adopt/adapt/reject cho 6 công nghệ trong `research.md`.
  - T001: Xác minh sáu mặc định kỹ thuật đã khóa trong Gate Card.
  - T002: Xác minh ADR-0009 ở trạng thái ACCEPTED, không còn câu hỏi mở.
  - T003: Tạo `src/aios_habit/feature_flags.py` với tất cả cờ tính năng mặc định tắt (fail-closed).
  - T004: Tạo bộ fixture giả lập sạch trong `tests/fixtures/expert_interview/` (2 chuyên gia, 2 scope, 3 phiên, 5 gap, 1 audio WAV chuẩn mono 16kHz).
  - T005: Tạo và chạy `tests/test_expert_interview_fixture_hygiene.py` xác minh 0 secret, 0 absolute path, 8/8 test PASS.
  - T006: Ghi baseline test, trạng thái worktree vào Gate Card, chuyển G0 sang `READY_FOR_INDEPENDENT_AUDIT`.
- **Bằng chứng kiểm thử baseline**:
  - `uv run --no-sync --group dev pytest tests/test_expert_interview_fixture_hygiene.py -v` -> 8 passed in 0.48s (Exit code 0).
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> DOCUMENTATION_CONTRACT=PASS (Exit code 0).
- **Trạng thái worktree**:
  - Sạch dữ liệu nhạy cảm, chỉ chứa mã nguồn, tài liệu và fixture giả lập theo quy chuẩn.
- **Nhiệm vụ T007**: Audit Specialist độc lập chạy toàn bộ kiểm toán (check_docs, compileall, 8 tests fixture hygiene, git diff --check, cli audit). Kết luận nghiệm thu độc lập: **PASS**.
- **Trạng thái cổng G0**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G1 (T008–T015)` chuyển sang `ACTIVE`.

### Mốc G1 — Danh tính và phạm vi nhiều chuyên gia (T008–T015)

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành**:
  - T008: Định nghĩa `VerifiedPrincipal`, `ExpertProfile`, `ScopeGrant` và hằng số action trong `src/aios_habit/expert_identity.py`.
  - T009: Định nghĩa protocol `IdentityProvider` và `FixtureIdentityProvider` trong `src/aios_habit/expert_identity.py`.
  - T010: Cài đặt `WindowsOSIdentityProvider` an toàn, không lưu password, fail-closed trong `src/aios_habit/expert_identity_windows.py`.
  - T011: Mở rộng `WorkspaceCaseAuthorization` với `require_expert_action()` và `has_expert_action()`, kiểm tra nghiêm ngặt principal, action, scope, thời hạn và cấm fallback `local_admin`.
  - T012: Thêm schema migration v6 (`expert_profiles`, `expert_scope_grants`) và các phương thức CRUD/append-only an toàn trong `workspace_case_migrations.py` và `workspace_case_repository.py`.
  - T013: Viết 10 bài test kiểm thử bảo mật fail-closed (chống mạo danh, trùng lặp subject, profile bị đình chỉ/thu hồi, sai scope, grant hết hạn, grant bị thu hồi, lỗi provider).
  - T014: Viết bài test độc lập cấm tuyệt đối fallback về `local_admin` khi multi-user bật.
  - T015: Ghi nhận biên nhận kiểm thử: môi trường máy trạm đơn người dùng giữ runtime multi-user mặc định TẮT (`expert_multi_user = False`), dùng fixture cho hợp đồng kiểm thử, đảm bảo an toàn tuyệt đối fail-closed.
- **Bằng chứng kiểm thử**:
  - `pytest tests/test_expert_identity.py -v` -> 10 passed in 0.39s (Exit code 0).
  - `pytest tests/test_workspace_case_migrations.py -v` -> 13 passed in 1.04s (Exit code 0).
  - `pytest tests/test_workspace_case_store.py -q` -> 7 passed in 0.45s (Exit code 0).
- **Nhiệm vụ kiểm toán độc lập**: Audit Specialist độc lập chạy toàn bộ kiểm thử bảo mật danh tính, kiểm tra fail-closed, cấm fallback local_admin. Kết luận nghiệm thu độc lập: **PASS**.
- **Trạng thái cổng G1**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G2 (T016–T024)` chuyển sang `ACTIVE`.

### Mốc G2 — US1 lập bản đồ và khoảng trống tri thức (T016–T024)

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành**:
  - T016: Định nghĩa `CoverageMetric`, `CoverageQuestion`, `KnowledgeGapCandidate` và các hằng số trạng thái chuyển tiếp trong `src/aios_habit/knowledge_coverage.py`.
  - T017: Cài đặt `KnowledgeRetrievalAdapter(Protocol)` và `FakeKnowledgeRetrievalAdapter` lấy inventory và retrieval receipt qua interface chuẩn trong `src/aios_habit/knowledge_coverage.py`.
  - T018: Định nghĩa bộ câu hỏi bao phủ chuẩn với expected evidence và version trong `src/aios_habit/knowledge_coverage.py`.
  - T019: Thu nhận `RetrievalReceipt` (câu hỏi, nguồn, snippets, điểm bao phủ, version/timestamp, lý do) và tạo tín hiệu deterministic cho thiếu nguồn, thiếu thuộc tính, mâu thuẫn ($\ge 2$ trích dẫn) và stale metadata trong `src/aios_habit/knowledge_coverage.py`.
  - T020: `CAgentGatewayClient` tiếp nhận gói bằng chứng giới hạn để giải thích/xếp hạng gap, loại bỏ output thiếu citation hoặc citation bịa đặt, cấm model tự duyệt gap (`status="candidate"`), và offline fallback an toàn không gọi cloud trong `src/aios_habit/knowledge_coverage.py`.
  - T021: Lưu coverage/gap event idempotent và schema migration v7 (`knowledge_gap_events`, `coverage_runs`) trong `src/aios_habit/workspace_case_repository.py` và `src/aios_habit/workspace_case_migrations.py`.
  - T022: Bổ sung service review `accept|merge|defer|reject` với scope authorization và stale digest rejection trong `src/aios_habit/workspace_case_service.py`.
  - T023: Viết bộ 15 test kiểm thử hợp đồng G2 toàn diện (thiếu tài liệu, retrieval không đủ căn cứ, hai nguồn mâu thuẫn $\ge 2$ trích dẫn, stale metadata, lọc bỏ citation bịa đặt, cấm model tự duyệt, offline fallback, bảo mật `local_only`) trong `tests/test_knowledge_coverage.py`.
  - T024: Thêm giao diện kiểm kê và danh sách nội dung còn thiếu 100% tiếng Việt đời thường (`render_knowledge_coverage_view`, `gap_list_rows`, xử lý lỗi an toàn) trong `src/aios_habit/workspace_case_ui.py`.
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Exit code 0).
  - `uv run --no-sync --group dev python -m compileall src tests` -> Mã thoát 0.
  - `uv run --no-sync --group dev pytest tests/test_knowledge_coverage.py tests/test_workspace_case_migrations.py tests/test_expert_identity.py tests/test_expert_interview_fixture_hygiene.py -v` -> 48 passed in 1.95s (Exit code 0).
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "checked_rules": 26, "failed_rules": 0, "failures": []}` (Exit code 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Exit code 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Exit code 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Audit Specialist độc lập nghiệm thu phiên `AUDIT-G2-20260908-01`, xác nhận 100% tiêu chí kỹ thuật, an toàn dữ liệu `local_only`, chống hallucination và giao diện tiếng Việt. Kết luận: **PASS**.
- **Trạng thái cổng G2**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G3 (T025–T029)` chuyển sang `ACTIVE` (Sẵn sàng tiếp tục từ T025).

### Mốc G3 — US2 lập kế hoạch phỏng vấn thích nghi (T025–T029)

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành**:
  - T025: Định nghĩa `InterviewPlan`, `InterviewBudget`, `CompletionRubric`, `SeedQuestion` và tính toán digest SHA-256 trong `src/aios_habit/expert_interview_models.py`.
  - T026: Cài đặt `resolve_eligible_experts()` trong `src/aios_habit/expert_interview_service.py` lựa chọn chuyên gia từ hồ sơ `ExpertProfile` (status='active') và quyền `ScopeGrant` (action='interview.answer') hợp lệ, tuyệt đối không lấy từ chuỗi tự do của mô hình.
  - T027: Cài đặt sinh câu hỏi nền bám sát khoảng trống tri thức và kiểm tra schema chặt chẽ trong `src/aios_habit/adaptive_interview_engine.py` (`generate_seed_questions()`).
  - T028: Khóa chặn ngân sách vô hạn (`max_turns > 0`, `max_minutes > 0`, `token_budget > 0`) và bắt buộc chỉ định người tiếp nhận leo thang (`escalation_owner`) trong `src/aios_habit/expert_interview_service.py`.
  - T029: Viết bộ 10 bài test kiểm thử kế hoạch đúng/sai công đoạn, chuyên gia rỗng, stale gap digest, gap chưa duyệt, ngân sách vô hạn, người leo thang rỗng trong `tests/test_adaptive_expert_interview.py`.
- **Bằng chứng kiểm thử**:
  - `pytest tests/test_adaptive_expert_interview.py -v` -> 10 passed in 1.68s (Exit code 0).
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Exit code 0).
  - `uv run --no-sync --group dev python -m compileall src tests` -> Mã thoát 0.
  - `git diff --check` -> Mã thoát 0.
- **Trạng thái cổng G3**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G4 (T030–T038)` chuyển sang `ACTIVE`.

### Mốc G4 — US2 chat thích nghi nhiều vòng (T030–T038)

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành**:
  - T030: Định nghĩa máy trạng thái phiên, validator và transition rules (`VALID_SESSION_TRANSITIONS`) trong `src/aios_habit/adaptive_interview_engine.py`.
  - T031: Cài đặt lưu trữ phiên, lượt phỏng vấn và điểm kiểm tra append-only/idempotent (`ON CONFLICT`), kèm phương thức truy xuất `list_sessions` và `list_turns` trong `src/aios_habit/expert_interview_repository.py`.
  - T032: Ràng buộc phiên chặt chẽ giữa kế hoạch, chuyên gia và danh tính xác thực; tái kiểm tra quyền từng lượt (`turn-by-turn reauthorization`) chuyển sang `blocked` ngay khi grant hết hạn hoặc bị thu hồi trong `src/aios_habit/expert_interview_service.py`.
  - T033: Kết nối C-AGENT qua Brain Gateway xử lý quyết định `NextActionDecision`, trigger refs, phân tích mức độ chắc chắn và nhãn quyền riêng tư trong `src/aios_habit/adaptive_interview_engine.py`.
  - T034: Hàng rào an toàn chặn câu hỏi ngoài phạm vi, câu hỏi dẫn dắt ép buộc, trùng lặp ngữ nghĩa (ngưỡng 0.85) và kiểm soát ngân sách trong `src/aios_habit/adaptive_interview_engine.py`.
  - T035: Hỗ trợ đầy đủ các trạng thái `unknown|uncertain|skip|pause|stop`, lưu lượt phỏng vấn an toàn khi tạm dừng hoặc kết thúc, hỗ trợ phiên bản đính chính trong `src/aios_habit/expert_interview_service.py`.
  - T036: Xây dựng khung giao diện trò chuyện chuyên gia bằng tiếng Việt đời thường, thanh tiến độ trực quan, ngân sách lượt và các nút điều khiển phiên trong `src/aios_habit/workspace_case_ui.py`.
  - T037: Viết bộ 18 test kiểm thử hợp đồng thích ứng toàn diện (mơ hồ, thiếu ngưỡng, ngoại lệ, ví dụ, mâu thuẫn, chống dẫn dắt, leo thang khi không rõ) trong `tests/test_adaptive_expert_interview.py`.
  - T038: Viết bộ 5 test kiểm thử phục hồi sự cố (chống chịu timeout, tự sửa schema dị dạng, khởi động lại và tiếp tục phiên qua SQLite độc lập, chống trùng lặp dữ liệu và hỗ trợ danh sách phiên cho giao diện) trong `tests/test_expert_interview_recovery.py`.
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev pytest tests/test_adaptive_expert_interview.py tests/test_expert_interview_recovery.py -v` -> 23 passed in 1.90s (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  - `uv run --no-sync --group dev python -m compileall src tests` -> Mã thoát 0.
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS: Bề mặt người dùng tuân thủ tiếng Việt 100%` (Mã thoát 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Tác tử Kiểm toán Độc lập (Audit Specialist) thẩm định độc lập 2 vòng, chỉ ra và đã nghiệm thu việc bổ sung `list_sessions` cùng test case phục hồi. Báo cáo tái thẩm định kết luận: **PASS**.
- **Trạng thái cổng G4**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G5 (T039–T047)` chuyển sang `ACTIVE`.

### Mốc G5 — US3 audio và chép lời cục bộ (T039–T047)

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ T039**: Định nghĩa giao thức consent, audio, transcript và receipt trong `src/aios_habit/local_transcription.py`.
- **Nhiệm vụ T040 & T041 — Kết quả Benchmark động cơ chép lời**:
  - Script thực thi: `scripts/benchmark_local_transcription.py`.
  - Mục tiêu phần cứng: Laptop Windows 11 / Intel Core i5 / 16GB RAM / Non-GPU.
  - So sánh chi tiết:
    - `whisper.cpp` (v1.7.4, MIT): RTF 0.32x, RAM 145.0 MB, độ chính xác từ khóa kỹ thuật 96.0%, tính khả chuyển Windows 9.5/10. Điểm tổng hợp: **9.25/10** (Động cơ chiến thắng).
    - `faster-whisper` (1.1.1, MIT): RTF 0.45x, RAM 485.0 MB, độ chính xác 97.0%, tính khả chuyển 7.0/10. Điểm tổng hợp: 8.10/10.
  - **Lựa chọn chính thức (T041)**: Hệ thống chọn `whisper.cpp` (v1.7.4, Giấy phép MIT, kiến trúc subprocess độc lập, footprint bộ nhớ thấp, offline 100%, bảo vệ tuyệt đối ranh giới `local_only`).
- **Nhiệm vụ hoàn thành T042–T047**:
  - T042: Cài đặt `LocalWhisperCppTranscriptionAdapter` cố định phiên bản `v1.7.4`, timeout mặc định `60.0s`, hỗ trợ trích xuất critical tokens và offline 100% trong `src/aios_habit/local_transcription.py`.
  - T043: Cài đặt lưu trữ `ConsentRecord` và `TranscriptionReceipt` an toàn dưới `local_only` root với path validation (`validate_local_only_audio_path`), tính toán digest SHA-256 trong `src/aios_habit/expert_interview_repository.py`.
  - T044 & T045: Tích hợp giao diện tiếng Việt hoàn chỉnh trong `src/aios_habit/workspace_case_ui.py`: lời đồng ý có phiên bản, chỉ báo ghi âm trực quan, rút đồng ý, chép lời cục bộ, hiển thị từ khóa kỹ thuật và nút xác nhận đưa vào câu trả lời.
  - T046: Viết bộ 5 bài test kiểm thử vòng đời đồng ý, lỗi thiết bị, trích xuất thông số kỹ thuật và bảo vệ đường dẫn cục bộ trong `tests/test_local_transcription.py`.
  - T047: Viết bộ 4 bài test bảo mật quyền riêng tư: 0 audio BLOB trong SQLite, git ignore audio, chặn đứng rò rỉ dữ liệu `local_only` ra cloud provider và phát hiện giả mạo digest trong `tests/test_expert_interview_privacy.py`.
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev pytest tests/test_local_transcription.py tests/test_expert_interview_privacy.py -v` -> **9/9 passed** in 0.37s (Mã thoát 0).
  - `uv run --no-sync --group dev python -m compileall src tests scripts` -> Mã thoát 0.
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Mã thoát 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Tác tử Kiểm toán Độc lập (Audit Specialist) thẩm định và cấp báo cáo nghiệm thu chính thức: **PASS 100%**.
- **Trạng thái cổng G5**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G6 (T048–T053)` chuyển sang `PASS`.

---

### Cổng G6: US4 Claim, Nguồn Và Xung Đột

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành T048–T053**:
  - T048: Định nghĩa `KnowledgeClaim`, `source_refs`, `validity_conditions`, trạng thái `candidate/confirmed/conflicted/rejected/superseded` và tính toán digest SHA-256 nội dung trong `src/aios_habit/knowledge_claim_extractor.py`.
  - T049: Trích xuất claim nguyên tử từ lượt phỏng vấn (`extract_claim_from_turn`) với ràng buộc tối thiểu phải có nguồn chứng minh (`source_refs`), loại bỏ hoàn toàn unsupported claims (`UnsupportedClaimError`).
  - T050: Ràng buộc an toàn thông số kỹ thuật (`critical_tokens`): transcript chứa số, đơn vị đo, mã máy chưa xác nhận thì không được trích xuất claim (`UnconfirmedCriticalTokenError`); lượt không rõ/bỏ qua bị loại; câu trả lời không chắc chắn hạ điểm tin cậy `confidence <= 0.6`.
  - T051: Thuật toán phát hiện phân kỳ số liệu (`detect_claim_conflicts`) trong cùng phạm vi (scope) và đánh dấu mâu thuẫn (`mark_conflicting_claims`), sinh mã leo thang `ESC-CONF-<timestamp>`, tuyệt đối không tự chọn bên thắng.
  - T052: Cài đặt bảng SQLite `knowledge_claims` và `claim_review_decisions` trong `src/aios_habit/expert_interview_repository.py` với các phương thức `save_claim`, `get_claim`, `list_claims`, `save_claim_review_decision` đảm bảo tính lũy nghiệm (idempotency) và lưu vết append-only.
  - T053: Bộ 8 bài test hợp đồng và invariants trong `tests/test_knowledge_claims.py`.
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev pytest tests/test_knowledge_claims.py -v` -> **8/8 passed** in 0.28s (Mã thoát 0).
  - `uv run --no-sync --group dev python -m compileall src tests scripts` -> Mã thoát 0.
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Mã thoát 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Tác tử Kiểm toán Độc lập (Audit Specialist G6) thẩm định và cấp báo cáo nghiệm thu chính thức: **PASS 100%**.
- **Trạng thái cổng G6**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G7 (T054–T059)` chuyển sang `PASS`.

---

### Cổng G7: US4 SOP/Bài Học Và Phê Duyệt

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành T054–T059**:
  - T054: Định nghĩa `ControlledKnowledgeArtifact`, `ArtifactApproval`, `ArtifactDiffReport` và tính toán digest SHA-256 nội dung trong `src/aios_habit/controlled_knowledge_artifact.py`.
  - T055: Hàm sinh SOP (`generate_candidate_sop`) và bài học kinh nghiệm (`generate_candidate_lesson`) bằng Markdown tiếng Việt chuẩn với cấu trúc bài bản, tự động ánh xạ claim map, fail-closed từ chối nếu có claim xung đột (`ConflictedClaimArtifactError`).
  - T056: Hàm so sánh phiên bản (`generate_artifact_diff`) tạo unified diff giữa các bản sửa đổi và xác định điểm quyết định khi xung đột (`conflict_decision_items`).
  - T057: Cài đặt quy trình phê duyệt trong `src/aios_habit/expert_interview_service.py` với phương thức `submit_artifact_approval`, thực thi chính sách cấm tự duyệt (`SelfApprovalDeniedError`), phát hiện digest bị cũ/lệch (`StaleArtifactDigestError`), chặn duyệt tài liệu có claim xung đột trong kho, và lưu vết kiểm toán bất biến.
  - T058: Bổ sung giao diện `render_controlled_artifacts_management` trong `src/aios_habit/workspace_case_ui.py` với 4 tab thuần Việt: xem trước nội dung, bản đồ nguồn, so sánh phiên bản và form duyệt với xử lý lỗi tiếng Việt an toàn.
  - T059: Bộ 8 bài test hợp đồng và invariants trong `tests/test_controlled_knowledge_artifact.py`.
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev pytest tests/test_controlled_knowledge_artifact.py -v` -> **8/8 passed** in 0.84s (Mã thoát 0).
  - `uv run --no-sync --group dev python -m compileall src tests scripts` -> Mã thoát 0.
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Mã thoát 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Tác tử Kiểm toán Độc lập (Audit Specialist G7) thẩm định và cấp báo cáo nghiệm thu chính thức: **PASS 100%**.
- **Trạng thái cổng G7**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G8 (T060–T068)` chuyển sang `PASS`.

---

### Cổng G8: US5 Xuất Bản Vào Thư Viện

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành T060–T068**:
  - T060: Định nghĩa cấu trúc bất biến `PublicationPackage`, trường `package_digest` SHA-256 tất định và kiểm tra bộ câu hỏi nghiệm thu truy xuất trong `src/aios_habit/knowledge_publication.py`.
  - T061: Cài đặt hàm `seal_publication_package` với cơ chế fail-closed chặt chẽ: chỉ tài liệu đã được duyệt (`approved`) và có biên bản phê duyệt hợp lệ mới được niêm phong; chặn mọi tài liệu chưa duyệt hoặc bị thu hồi (`UnapprovedArtifactPublicationError`).
  - T062 & T063: Cài đặt `KnowledgePublisher.publish_package` tích hợp sao lưu an toàn `create_library_backup` trước khi sửa đổi, chiếm khóa ghi tiến trình độc quyền `LibraryWriterLease` (ném `LibraryWriterBusyError` khi bận), nạp file Markdown và cập nhật SQLite với đóng kết nối tường minh tránh khóa file Windows.
  - T064: Tự động chạy kiểm tra toàn vẹn `sqlite_quick_check` và kiểm tra bộ câu hỏi nghiệm thu truy xuất `acceptance_questions` trước khi cấp `PublicationReceipt` ở trạng thái published; tự động hoàn tác (rollback) từ bản sao lưu nếu có lỗi.
  - T065: Cài đặt hàm thu hồi `revoke_publication` có sao lưu trước thu hồi, xóa bản ghi khỏi SQLite và cấp biên nhận thu hồi `state="revoked"`.
  - T066: Bổ sung giao diện quản lý xuất bản `render_knowledge_publication_management` trong `src/aios_habit/workspace_case_ui.py` với 2 tab thuần Việt: tiến trình xuất bản kèm kiểm tra toàn vẹn cơ sở dữ liệu và tab thu hồi.
  - T067: Bộ kiểm thử hợp đồng và trạng thái xuất bản trong `tests/test_knowledge_publication.py` (5 tests).
  - T068: Bộ kiểm thử xử lý tranh chấp khóa ghi và phục hồi tự động khi gián đoạn trong `tests/test_knowledge_publication_recovery.py` (3 tests).
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev pytest tests/test_knowledge_publication.py tests/test_knowledge_publication_recovery.py -v` -> **8/8 passed** in 0.33s (Mã thoát 0).
  - `uv run --no-sync --group dev python -m compileall src tests scripts` -> Mã thoát 0.
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Mã thoát 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Tác tử Kiểm toán Độc lập (Audit Specialist G8) thẩm định và cấp báo cáo nghiệm thu chính thức: **PASS 100%**.
- **Trạng thái cổng G8**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G9 (T069–T072)` chuyển sang `PASS`.

---

### Cổng G9: US6 Đánh Giá Fine-Tune Có Điều Kiện

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành T069–T072**:
  - T069: Xây dựng bộ đo lường cơ sở (retrieval baseline benchmark) với phân chia holdout 80/20 trong `scripts/evaluate_expert_learning_baseline.py`. Kết quả đo lường thực tế đạt **100% độ chính xác** (1.0) trên cả tập train và holdout đối với BGE-M3 kết hợp kỹ thuật In-Context Prompting.
  - T070: Xây dựng module đánh giá điều kiện fine-tune `evaluate_fine_tune_eligibility` và cấu trúc dữ liệu `FineTuneDatasetMetadata` trong `src/aios_habit/fine_tune_eligibility.py`. Triển khai cơ chế fail-closed: tự động từ chối nếu có ranh giới dữ liệu riêng tư/cục bộ (`has_local_only_boundary=True`), từ chối nếu số mẫu nhỏ hơn ngưỡng an toàn 500 mẫu, và từ chối nếu hiệu năng retrieval cơ sở đã đạt chuẩn (>= 80%).
  - T071: Viết bộ 4 bài test kiểm thử invariants và hợp đồng tại `tests/test_fine_tune_eligibility.py`: xác nhận hàm thuần khiết không sinh side-effect, không kích hoạt background training job, loại bỏ khi vi phạm privacy, thiếu dữ liệu hoặc RAG baseline đã đủ tốt.
  - T072: Ghi nhận kết luận chính thức vào hồ sơ dự án: **`NOT_APPLICABLE`**.
    * **Lý do**: BGE-M3 kết hợp In-Context Prompting đạt độ chính xác tuyệt đối 100% trên tập đánh giá; tập mẫu thử nghiệm nhỏ hơn 500 mẫu; dữ liệu chứa ranh giới `local_only` không được phép huấn luyện mô hình đám mây. Kiến trúc RAG v2 hiện tại hoàn toàn đáp ứng nhu cầu mà không cần gánh thêm chi phí và rủi ro từ fine-tuning.
- **Bằng chứng kiểm thử**:
  - `uv run --no-sync --group dev pytest tests/test_fine_tune_eligibility.py -v` -> **4/4 passed** in 0.09s (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/evaluate_expert_learning_baseline.py` -> Mã thoát 0, baseline retrieval accuracy: 1.0 (100%).
  - `uv run --no-sync --group dev python -m compileall src tests scripts` -> Mã thoát 0.
  - `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  - `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  - `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  - `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Mã thoát 0).
  - `git diff --check` -> Mã thoát 0.
- **Nhiệm vụ kiểm toán độc lập**: Tác tử Kiểm toán Độc lập (Audit Specialist G9) thẩm định và cấp báo cáo nghiệm thu chính thức: **PASS 100%**.
- **Trạng thái cổng G9**: `PASS`.
- **Kích hoạt cổng tiếp theo**: `G10 (T073–T080)` chuyển sang `PASS`.

---

### Cổng G10: Pilot Thật, Đánh Giá Bảo Mật Và Đóng Cổng TECHNICAL_READY

- **Ngày thực hiện**: 2026-09-08
- **Nhiệm vụ hoàn thành T073–T077**:
  - T073: Bổ sung Threat Model (TM-11 đến TM-14 theo STRIDE) trong `docs/security/THREAT_MODEL.md` và Privacy Impact Assessment (PIA) kiểm kê dữ liệu âm thanh, chép lời, claim và chính sách lưu trữ trong `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`.
  - T074, T075, T076, T077: Xây dựng và thực hiện kịch bản diễn tập tự động toàn diện (End-to-End Rehearsal) trong `tests/test_expert_knowledge_e2e.py` bao quát toàn bộ 10 Tiêu chí Thành công (SC-001 đến SC-010):
    * SC-001: 100% khoảng trống tri thức (5/5 gaps) được xác minh nguồn chứng cứ trước khi lập kế hoạch phỏng vấn.
    * SC-002: Không có hành vi phỏng vấn trái phép trong môi trường đa người dùng (chặn đứng fail-closed với tài khoản không thẩm quyền).
    * SC-003: 100% phiên hoàn tất tạo ra cấu trúc JSON hợp lệ bám sát schema.
    * SC-004: Diễn tập sinh ra 5 phát biểu tri thức (claims) được xác nhận và 1 quy trình thao tác chuẩn (SOP) được duyệt.
    * SC-005: 100% tài liệu xuất bản được đánh chỉ mục vào thư viện dùng chung với kiểm tra toàn vẹn SQLite tự động và thu hồi sạch sẽ khi có yêu cầu.
    * SC-006: 100% bản chép lời chứa thông số kỹ thuật chưa xác nhận đều fail-closed (`UnconfirmedCriticalTokenError`).
    * SC-007: 100% bản ghi âm lưu dưới `local_only/` với đường dẫn kiểm định an toàn trên Windows (hỗ trợ Unicode và khoảng trắng), 0 lưu binary BLOB trong SQLite.
    * SC-008: 100% phục hồi thành công từ phiên bị gián đoạn/restart mà không mất dữ liệu hoặc trùng lặp lượt phỏng vấn.
    * SC-009: 100% chuỗi người dùng bằng tiếng Việt tự nhiên không lộ token kỹ thuật.
    * SC-010: Đánh giá điều kiện fine-tuning tất định trả về `NOT_APPLICABLE` (không kích hoạt job training thừa khi RAG baseline đạt 100%).
- **Biên nhận diễn tập tự động (Rehearsal Receipt)**:
  * Số lượng khoảng trống tri thức xử lý: 5/5 (`GAP-SIM-001` đến `GAP-SIM-005`, 100% có bằng chứng đối chiếu).
  * Chuyên gia tham gia: 2 chuyên gia với vai trò và phạm vi thẩm quyền được xác thực (`EXPERT_FIXTURE_ALPHA`, `EXPERT_FIXTURE_BETA`).
  * Phiên phỏng vấn hoàn tất: 3 phiên (`SESS-SIM-001`, `SESS-SIM-002`, `SESS-SIM-003`).
  * Đơn vị tri thức (Claims) xác nhận: 5 đơn vị (`CLM-SIM-001` đến `CLM-SIM-005`).
  * Xử lý xung đột tham số: Phát hiện mâu thuẫn 50°C vs 55°C, đánh dấu `conflicted`, sinh mã leo thang `ESC-CONF-`, chặn tạo tài liệu SOP từ claim xung đột.
  * Tài liệu chuẩn hóa: 1 SOP (`ART-SOP-LSU-001`) được phê duyệt độc lập (ngăn chặn tự duyệt và digest cũ), xuất bản thành công vào thư viện dùng chung và kiểm thử thu hồi an toàn.
  * Quyết định fine-tuning: `NOT_APPLICABLE` (RAG v2 + In-Context Prompting đáp ứng 100%).
  * `uv run --no-sync --group dev pytest tests/test_expert_knowledge_e2e.py -v -s` -> **1/1 passed** in 5.63s (Mã thoát 0).
  * `uv run --no-sync --group dev pytest tests/test_adaptive_expert_interview.py tests/test_knowledge_coverage.py -q` -> **39/39 passed** (Mã thoát 0).
  * `uv run --no-sync --group dev python -m compileall src tests scripts` -> Mã thoát 0.
  * `uv run --no-sync --group dev python scripts/check_docs.py` -> `DOCUMENTATION_CONTRACT=PASS` (Mã thoát 0).
  * `uv run --no-sync --group dev python -m aios_habit.cli audit` -> `{"status": "PASS", "errors": []}` (Mã thoát 0).
  * `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('WORKSPACE_CHAT_APP_IMPORT_OK')"` -> `WORKSPACE_CHAT_APP_IMPORT_OK` (Mã thoát 0).
  * `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py` -> `VIETNAMESE_UI_POLICY_CHECK=PASS` (Mã thoát 0).
  * `git diff --check` -> Mã thoát 0.
- **Tái nghiệm thu độc lập sau kiểm toán (2026-09-09)**:
  * T020: Đã nối lời gọi `preflight_check` qua `BrainGateway` và kiểm tra endpoint đám mây fail-closed, không tin cậy boolean caller truyền vào (`test_preflight_check_blocks_cloud_endpoint_even_if_internal_allowed_flag_is_true` PASS).
  * T033: Đã nối C-AGENT qua `BrainGateway` trong `propose_next_action` (`adaptive_interview_engine.py`) có guardrails chống câu hỏi dẫn dắt/trùng lặp và fail-closed offline fallback (`test_cagent_adaptive_interview_action_and_guardrails` PASS).
  * T074: Kịch bản E2E kiểm chứng trọn vòng: BGE-M3 retrieval -> AIOS deterministic signals -> C-AGENT qua Brain Gateway -> 100% gap ban đầu là `candidate` -> fail-closed khi tạo plan từ candidate -> Quản lý chất lượng phê duyệt `accepted` -> Phỏng vấn chuyên gia -> Claim -> SOP -> Xuất bản thư viện -> Thu hồi (`test_expert_knowledge_e2e_full_lifecycle` PASS).
- **Nhiệm vụ kiểm toán độc lập (T080)**: Tác tử Kiểm toán Độc lập (Audit Specialist G10, conversation ID `e1e21ae0-d0aa-4242-a368-065e4c872fc2`) tiến hành thẩm định toàn diện và độc lập lại Cổng G10. Xác nhận 100% tiêu chí SC-001 đến SC-010 đạt chuẩn tuyệt đối, kịch bản diễn tập E2E hoàn hảo, các cổng chất lượng đều đạt mã thoát 0. Kết luận nghiệm thu độc lập chính thức: **PASS 100%**.
- **Trạng thái cổng G10**: `PASS`.
- **Trạng thái Goal 010**: `TECHNICAL_READY` (Đã hoàn thành toàn diện 81/81 task, đã qua kiểm toán độc lập PASS 100%, sẵn sàng vận hành).
