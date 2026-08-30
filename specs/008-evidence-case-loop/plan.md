# Kế hoạch triển khai: Trợ lý công việc khép kín từ vụ việc đến phòng ngừa lỗi

**Mã tính năng**: `008-evidence-case-loop`

**Checkout hiện tại**: nhánh `gate1-local-case-sqlite`, commit `2bb7a5f`

**Nhánh được metadata Spec Kit khai báo**: `008-evidence-case-loop`

**Trạng thái**: Chủ sở hữu đã duyệt Gate 1A + US1 để triển khai
**Đặc tả**: [spec.md](spec.md)

## 1. Kết quả mong muốn

Chuyển Workspace Chat từ “não đọc tài liệu + kính lúp log” thành trợ lý công việc có kiểm soát:

```text
Vấn đề hoặc tín hiệu rủi ro
        ↓
Hồ sơ vụ việc + bằng chứng + dòng thời gian
        ↓
Hỏi phần còn thiếu + giao đúng chuyên gia
        ↓
Kết luận/outcome được con người xác nhận
        ↓
Bài học dùng lại + artifact công việc + dữ liệu đánh giá
        ↓
Shadow prediction và đề xuất phòng ngừa có duyệt
```

Kế hoạch không biến AI thành hệ điều khiển nhà máy. Sự chủ động được phép gồm gom dữ liệu, hỏi ngược, tạo case, tạo draft, chạy kiểm tra trong sandbox và xếp ưu tiên; mọi quyết định vận hành vẫn thuộc con người.

## 2. Hiện trạng và điểm bắt đầu

- Cổng lưu metadata case từ Workspace Chat đã được triển khai tại `2bb7a5f`; 80 test tập trung đã đạt trong lượt lập kế hoạch này.
- Chưa chạy full suite/audit độc lập cho toàn bộ chương trình mới; Cổng 1 là `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`, không phải `DONE`.
- `workspace_cases.sqlite` chưa có migration version chính thức.
- Chưa có list/detail UI, expert workflow, learning retrieval, prediction store/model/shadow.
- Agent artifact và Agent IDE đã có các mảnh nền nhưng chưa có capability contract thống nhất theo case.
- Gate A NAS vẫn `PARTIAL` cho đến khi có smoke thật.

Không làm lại Cổng 1. Việc tiếp theo là audit/khóa migration rồi mở giao diện case.

## 3. Bối cảnh kỹ thuật

| Hạng mục | Lựa chọn |
|---|---|
| Runtime | Python `>=3.11,<3.12` |
| Giao diện | Streamlit trong `workspace_chat_app.py`; không mở route Case Cockpit/Studio |
| Kho hồ sơ | `local_cases/workspace_cases.sqlite`, một máy, không sync |
| Kho log | `line_events.sqlite`, chỉ event `suspected` |
| Thư viện tài liệu | `library.sqlite`, tách khỏi case/log/prediction |
| Kho dự đoán | SQLite cục bộ mới dưới `local_cases/production_prediction.sqlite` |
| Xử lý bảng | `pandas` hiện có; giữ phép biến đổi tất định và có schema |
| Baseline prediction | Rule/SPC như EWMA/CUSUM sau khi dữ liệu đáp ứng giả định |
| Model ứng viên | `scikit-learn` trong optional extra riêng sau Data Gate; chưa khóa thuật toán thắng |
| Artifact Agent | Capability registry + output versioned + verifier + approval |
| Agent lập trình | Task pack + workspace bridge + proposal/diff/command + observed evidence |
| Quyền riêng tư | `local_only` mặc định; không gửi Gemini Web/Nakazasen Router |

Không còn mục `NEEDS CLARIFICATION` về kiến trúc. Các lựa chọn dữ liệu/role/threshold chưa có là **đầu vào bắt buộc của từng gate**, được ghi `BLOCKED` nếu chủ sở hữu chưa cung cấp; không được tự điền giả.

## 4. Kiến trúc đích

```text
Workspace Chat
 ├─ Trò chuyện/RAG ───────────────> library.sqlite
 ├─ Hồ sơ vụ việc
 │   ├─ Case UI + timeline
 │   ├─ Expert request/review
 │   ├─ Learning promotion/search
 │   └─ Artifact proposal/approval
 │                                  └─ workspace_cases.sqlite
 ├─ Điều tra line ────────────────> line_events.sqlite
 ├─ Prediction lab/shadow ────────> production_prediction.sqlite
 └─ Agent kỹ thuật phần mềm ──────> workspace code riêng + task pack
```

Các kho chỉ liên kết qua ID/digest bất biến. Không join bằng tên file hoặc nội dung LLM sinh. Module Workspace Chat không import `studio`/`case_cockpit`.

## 5. Kiểm tra Hiến chương trước thiết kế

| Nguyên tắc | Đánh giá | Cách đáp ứng |
|---|---|---|
| Bằng chứng trước tuyên bố | Đạt ở mức thiết kế | Tách `suspected`, `confirmed`, `false_alarm`, `unknown`; mọi promotion/model claim có digest/evidence. |
| Ưu tiên cục bộ | Đạt ở mức thiết kế | Bốn kho cục bộ tách biệt; route ngoài bị chặn theo policy. |
| Tri thức có thể chuyển đổi | Đạt ở mức thiết kế | Schema mở, model card/dataset manifest JSON/Markdown, không lệ thuộc provider. |
| Workspace Chat là UI duy nhất | Đạt ở mức thiết kế | Case/Expert/Prediction/Agent nằm trong Workspace Chat. |
| Thiết kế trước code, kiểm chứng theo gate | Đạt ở mức thiết kế | Có gate tuần tự, test/fault injection/audit độc lập và owner approval. |
| Tương thích dữ liệu lưu trữ | Cần xử lý trước Gate 2 | Thêm schema migration, backup và rollback trước khi mở rộng Cổng 1. |

Không có ngoại lệ Hiến chương được đề xuất.

## 6. Các phương án tổ chức chương trình

### Phương án A — Một đợt triển khai lớn

**Ưu**: nhìn như “làm hết” trong một lần.

**Nhược**: trộn UI, persistence, ML và Agent; khó audit độc lập, dễ fake PASS, rollback kém.
**Không chọn**.

### Phương án B — Chỉ hoàn thiện case, hoãn prediction và Agent

**Ưu**: rủi ro thấp, sớm có UI.

**Nhược**: không đạt ý đồ “Đôrêmon có kiểm soát” và không giải quyết LSU/Iris.
**Không chọn**.

### Phương án C — Một chương trình, ba track có gate phụ thuộc

**Ưu**: giữ đầy đủ phạm vi nhưng mỗi gate có artifact/test/rollback riêng; dữ liệu thật chặn đúng prediction mà không chặn case UI.

**Nhược**: nhiều gate và cần chủ sở hữu cung cấp dữ liệu/role ở đúng thời điểm.
**Chọn phương án này**.

Ba track là:

1. **Vòng vụ việc**: migration → case UI → chuyên gia → learning → line pilot.
2. **Agent tạo đầu ra**: capability policy → artifact Agent → coding Agent.
3. **Phòng ngừa lỗi**: data contract → LSU model lab → shadow case → alert có duyệt → adapter Drum/DLP.

Gate A NAS là track vận hành độc lập; không được dùng để tuyên bố toàn hệ thống production-ready.

## 7. Trình tự gate bắt buộc

### Gate 1A — Kiểm toán và khóa nền hồ sơ đã triển khai

- Audit commit `2bb7a5f`, chạy focused/full gates theo phạm vi.
- Thêm migration framework, schema version, backup/restore và fixture dữ liệu cũ.
- Loại bỏ/deprecate copy placeholder “chế độ mô phỏng” không còn dùng.
- Cập nhật contract dữ liệu lưu trữ trước khi thêm bảng.

**Điều kiện đóng**: readback/restart/fault injection/migration rollback đạt; audit độc lập xác nhận không lưu chat thô.

### Gate 2 — Mục “Hồ sơ vụ việc” và vòng đời case

- List/filter/detail/timeline/open-trace trong Workspace Chat.
- Thêm type, priority, assignee, missing-evidence checklist và state machine.
- Cho phép gắn thêm tham chiếu ảnh, SOP, tài liệu hoặc log đã có trong kho nguồn mà không sao chép nội dung thô.
- Không cho UI ghi transition trực tiếp; mọi thao tác qua service.

**Điều kiện đóng**: người dùng mở case trong tối đa ba thao tác; trace thiếu được hiển thị trung thực.

### Gate 3 — Giao việc và thẩm định chuyên gia

- Role/scope registry cục bộ.
- Expert request/inbox/response/conflict resolution.
- Review append-only, digest-bound, không tin caller boolean.

**Điều kiện đóng**: mọi transition sai quyền/thiếu lý do/sai digest bị fail-closed.

### Gate 4 — Promotion và dùng lại bài học

- Adapter import thẻ cũ chỉ khi người dùng chọn.
- Learning candidate → promoted/withdrawn.
- Retriever case-memory riêng, citation đến case/review/evidence.

**Điều kiện đóng**: case mới tìm được bài học promoted phù hợp; candidate/withdrawn không rò vào kết quả chuẩn.

### Gate 5 — Pilot điều tra line khép kín

- Bổ sung source digest/collector/timezone, bỏ fallback event không match.
- Timeline, repeat grouping, gap questions, relevance review.
- Mapping overlay chỉ từ manifest đã duyệt.
- Chạy một pilot thật từ case đến báo cáo/outcome.

**Điều kiện đóng**: có SOP/mã lỗi/log/report thật được phép, reviewer xác nhận; vẫn không tuyên bố chẩn đoán.

### Gate 6 — Capability registry và Agent artifact

- Định nghĩa loại artifact, risk tier, template, verifier, approver, output root.
- Hỗ trợ trước: báo cáo điều tra và SOP.
- Mở tiếp hồ sơ thiết kế công đoạn/bảng tính/sơ đồ sau khi chủ sở hữu chọn format đầu tiên.
- Mỗi lần xuất tạo version mới, diff/preview và audit event.

**Điều kiện đóng**: no-evidence/unapproved/overwrite/protected path đều bị chặn; artifact chính thức truy vết đầy đủ.

### Gate 7 — Agent lập trình có sandbox và phê duyệt

- Nối task pack, result import và Workspace Agent proposal thành một luồng case `agent_work`.
- Tách workspace code với dữ liệu nhà máy; allowlist file/command/test.
- Proposal diff/command bất biến; observed evidence là điều kiện PASS.

**Điều kiện đóng**: không tự merge/push, không truy cập `local_cases`, mọi patch/test có audit và rollback.

### Gate 8 — Data Gate cho LSU/Iris

- Chốt data dictionary, stable join keys, đơn vị, timezone, jig/process version, outcome labels.
- Ingest snapshot bất biến; kiểm completeness, duplicate, leakage, drift và class balance.
- Tạo dataset manifest và readiness report.

**Điều kiện đóng**: thiếu nhãn/owner/replay/leakage check thì `BLOCKED`; không train model.

### Gate 9 — Prediction lab và model card

- Baseline không cảnh báo, baseline EWMA/CUSUM và model có giám sát đơn giản.
- Temporal/group split, calibration, feature importance trên holdout.
- Đo false alarm, missed detection, lead time, precision/recall và stability slice.
- Chọn threshold theo cost do owner phê duyệt.

**Điều kiện đóng**: protocol đóng băng, report tái lập được, model/dataset/code digest đầy đủ; chưa phát alert.

### Gate 10 — Shadow prediction tạo hồ sơ dự đoán

- Local scheduler/replay tạo `RiskAssessment` từ feature snapshot.
- Dedup/cooldown và tạo/cập nhật case `prediction`.
- Kỹ sư gắn outcome `confirmed`, `false_alarm`, `unknown`.
- Dashboard shadow không ảnh hưởng line.

**Điều kiện đóng**: đạt số case và ngưỡng thời gian/chi phí do owner ký; không có plant action.

### Gate 11 — Cảnh báo có duyệt và đề xuất phòng ngừa

- Chỉ mở in-app alert cho role được phép.
- Action library versioned; Agent đề xuất kiểm tra/phòng ngừa có evidence.
- Theo dõi `effective`/`ineffective`, rollback threshold/model/action.

**Điều kiện đóng**: owner phê duyệt alert policy, escalation và kill switch; không có PLC/control.

### Gate 12 — Adapter Drum/DLP

- Reuse lõi dataset/model/shadow; mỗi miền có mapping, label, feature và acceptance riêng.
- Không copy threshold/model LSU sang Drum/DLP.

**Điều kiện đóng**: mỗi adapter có Data Gate và shadow evidence độc lập.

### Gate 13 — Gate A NAS và pilot tổ chức

- Nghiệm thu thư viện chung trên đường dẫn thật, one-writer/multi-reader, backup/restore.
- Pilot bàn giao case giữa ít nhất hai vai trò/ca làm việc.
- Cập nhật retention/backup runbook.

**Điều kiện đóng**: bằng chứng runtime thật; thiếu thì giữ `PARTIAL`.

### Gate 14 — Hội tụ và bàn giao

- Audit độc lập từng gate/commit.
- Chạy full quality gates, docs check, migration/restore drill, privacy/security regression.
- Cập nhật `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md`, PIA và compatibility contract theo hành vi thật.

## 8. Chiến lược nhánh và commit

Không triển khai tất cả trên một commit. Mỗi gate là một nhánh/commit nhỏ có allowlist và audit riêng. Trước khi bắt đầu Gate 2, chủ sở hữu chọn một trong hai cách:

1. Merge/audit `gate1-local-case-sqlite` rồi tạo nhánh `008-evidence-case-loop` từ `main` đã cập nhật.
2. Tiếp tục trên nhánh hiện tại nhưng chỉ sau khi tài liệu kế hoạch được tách rõ và Gate 1A đạt audit. Đây là phương án chủ sở hữu đã duyệt cho lượt triển khai Gate 1A + US1; không merge/push tự động.

Không tự chọn chiến lược merge khi chưa kiểm tra `origin/main` và chưa có phê duyệt.

## 9. Chiến lược kiểm thử

Mỗi gate có ba lớp:

1. **Contract/unit**: state machine, role, digest, migration, metric và policy.
2. **Integration**: restart/readback/fault injection/UI callback/store boundaries.
3. **Acceptance**: case/pilot/shadow bằng dữ liệu được phép; không dùng fixture tổng hợp để thay thế claim runtime thật.

Cuối mỗi gate chạy tối thiểu:

```powershell
py -3 -m compileall src tests
py -3 -m pytest -q <tests-tập-trung>
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
```

Trước đóng gate/merge chạy thêm:

```powershell
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
```

`cli audit` phải trả `"status": "PASS"`. Timeout, dependency thiếu, smoke chưa chạy hoặc dữ liệu thật chưa có là `PARTIAL`/`BLOCKED`.

## 10. Rủi ro và giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Schema Cổng 1 bị thay đổi không tương thích | Migration version + online backup + rollback test trước Gate 2. |
| UI làm người dùng nhầm AI đã xác nhận | Badge nguồn/trạng thái, service guard, append-only review. |
| Bài học case bị nhầm với SOP chuẩn | Retriever riêng, nhãn “Bài học đã xác nhận”, provenance bắt buộc. |
| Agent code trở thành đường tắt chạm dữ liệu nhà máy | Hai miền workspace, deny `local_cases`, task pack và approval riêng. |
| Prediction học từ tương lai | Feature snapshot tại thời điểm dự báo, temporal/group split, leakage audit. |
| Alert quá nhiều | Shadow trước, cost matrix, calibration, dedup/cooldown, owner threshold. |
| Mở rộng Drum/DLP quá sớm | LSU/Iris vertical slice là gate bắt buộc. |
| Gate A NAS bị báo PASS bằng test giả | Chỉ runtime evidence trên đường dẫn thật được đổi trạng thái. |

## 11. Kiểm tra Hiến chương sau thiết kế

- Không lưu chat thô trong case; đạt yêu cầu ưu tiên bằng chứng và dữ liệu tối thiểu.
- Không có production control hoặc autonomous factory action; đạt ranh giới thẩm quyền con người.
- Workspace Chat vẫn là UI duy nhất; không hồi sinh legacy.
- Mọi persistent schema mới có migration/rollback trong kế hoạch.
- Mọi model/alert claim có dataset/model/threshold version và outcome review.
- Full quality gates và audit độc lập là điều kiện đóng, không phải bước tùy chọn.

**Kết luận**: thiết kế không vi phạm Hiến chương. Việc triển khai code phải chờ chủ sở hữu phê duyệt kế hoạch và các quyết định gate tương ứng.
