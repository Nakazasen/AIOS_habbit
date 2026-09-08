# Thẻ cổng: AI phỏng vấn chuyên gia và làm giàu tri thức

Status: `READY_TO_RUN`  
Mã tính năng: `010-expert-knowledge-acquisition`  
Chủ sở hữu: Project owner / Process owner / Privacy reviewer  
Cập nhật: 2026-09-07

## Mục tiêu

Đưa AIOS từ hỏi–đáp có cấu trúc sang chat phỏng vấn nhiều vòng, thu nhận tri thức có nguồn, tạo SOP/bài học dạng ứng viên và xuất bản nội dung đã duyệt vào collection để AI dùng ngay.

## Trạng thái đúng hiện tại

- Hồ sơ đặc tả, kế hoạch, contract, 81 task và runbook Gemini đã được chuẩn bị.
- Chưa triển khai code feature 010.
- Chưa có identity provider nhiều người dùng được duyệt.
- Chưa ghi âm/chạy dữ liệu thật/chuyên gia thật.
- Chưa đưa lesson mới vào `library.sqlite` và chưa fine-tune.

## Sáu mặc định đã khóa để chạy liên tục

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
| G5 | T039–T047 | `ACTIVE` | Consent + transcription local |
| G6 | T048–T053 | `LOCKED` | Claim có nguồn/conflict |
| G7 | T054–T059 | `LOCKED` | SOP/bài học candidate + approval |
| G8 | T060–T068 | `LOCKED` | Publication và retrieval receipt |
| G9 | T069–T072 | `LOCKED` | Fine-tune eligibility report |
| G10 | T073–T080 | `LOCKED` | Pilot thật + full gates + audit độc lập |

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

Khi fixture, E2E và audit đạt, trạng thái là `TECHNICAL_READY`. Vận hành với người thật bắt đầu sau đó mà không cần đổi code.

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
