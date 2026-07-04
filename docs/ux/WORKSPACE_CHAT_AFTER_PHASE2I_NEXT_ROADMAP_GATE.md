# Workspace Chat After Phase 2I Next Roadmap Gate

## 1. Kết luận

`PASS_READY_FOR_NEXT_IMPLEMENTATION_PROMPT`

Workspace Chat đã đủ điều kiện rời Phase 2I. Bước tiếp theo nên là một lát cắt
nhỏ của real-work owner pilot: làm rõ và thu gọn hành trình hiện có từ tạo sổ,
thêm nguồn, chọn quyền riêng tư, kiểm tra nguồn, hỏi AI hoặc nhận safe block,
đến lưu trữ/khôi phục. Không mở lại lifecycle, không cấu hình provider, và
không biến placeholder `Lưu vào Case` thành tích hợp Case Cockpit trong task này.

## 2. Baseline và pre-gate

- Branch: `main`
- HEAD: `59c37577aa75645db0873b01716b5c3048c37ae6`
- `origin/main`: `59c37577aa75645db0873b01716b5c3048c37ae6`
- Ahead/behind: `0/0`
- Worktree trước gate: sạch
- Runtime paths trước gate: sạch
- Baseline yêu cầu: HEAD/origin/main
  `59c37577aa75645db0873b01716b5c3048c37ae6`

## 3. Nguồn audit

### Tài liệu đã đọc

- `README.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_REAL_WORK_PILOT_READINESS_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_OWNER_PILOT_CHECKLIST.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2H_OWNER_SMOKE_GAP_TRIAGE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_IMPLEMENTATION_AUDIT.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_OWNER_SMOKE_RESULT.md`

Tài liệu được yêu cầu theo tên
`docs/ux/WORKSPACE_CHAT_PHASE2H_OWNER_SMOKE_GAPS.md` không tồn tại. Repo có tài
liệu tương ứng theo tên
`docs/ux/WORKSPACE_CHAT_PHASE2H_OWNER_SMOKE_GAP_TRIAGE.md`, và tài liệu đó đã
được dùng làm bằng chứng thay thế.

### Code và test đã đọc

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ai_answer.py`
- `src/aios_habit/workspace_chat_store.py`
- `tests/test_workspace_chat_ai_answer.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`

## 4. Trạng thái hiện tại

- Phase 2H answer clarity đã hoàn tất: source check không giả làm câu trả lời,
  chỉ explicit ask mới đi vào AI path, và provider chưa cấu hình được báo
  trung thực.
- Phase 2I privacy source control đã hoàn tất: owner có thể chọn nguồn được gửi
  AI hoặc chỉ dùng trên máy; một nguồn bị chặn sẽ chặn toàn bộ request.
- Phase 2I notebook lifecycle đã hoàn tất: archive/hide/restore có persistence,
  không hard delete và không sửa child data.
- Owner smoke lifecycle được chấp nhận với trạng thái
  `PASS_WITH_ACCEPTED_GAP_ACCEPTED_FOR_PHASE2I`.
- Core archive/restore và privacy quick smoke đều PASS.
- Lỗi import Streamlit cũ được xác định là stale process/module cache và hết sau
  restart, không cần code change.
- Stale two-session browser path chưa được browser-verify end-to-end, nhưng đã
  có structural test và được ghi nhận là accepted gap, không phải blocker.

Do đó không có bằng chứng buộc phải mở lại Phase 2I.

## 5. Khoảng trống còn lại

1. **Provider success smoke.** `tests/test_workspace_chat_ai_answer.py` có mock
   success/error/privacy coverage, nhưng owner chưa smoke được provider success
   vì môi trường chưa có provider được cấu hình và phê duyệt. Workspace Chat
   cũng chưa có owner-facing provider setup.
2. **Stale two-session browser automation.** Task tương lai đã được ghi nhận:
   `HARDEN_WORKSPACE_CHAT_PHASE2I_STALE_SESSION_BROWSER_AUTOMATION`.
3. **Test hygiene.** Test lifecycle còn dead variable `msg`; một số test phụ
   thuộc seeded notebook IDs; confirmation/cancel/stale-session cần direct UI
   behavior coverage mạnh hơn.
4. **Hành trình owner chưa được hợp nhất.** Các capability đã có nhưng UI vẫn
   trình bày theo nhiều khối kỹ thuật/pilot. App còn expander checklist pilot,
   action tạo dữ liệu test, nhiều đường thêm nguồn, và phân tách source check /
   ask / privacy / lifecycle chưa thành một đường đi ngắn, dễ tự hoàn thành.
5. **Handoff chưa thật.** `Lưu vào Case` hiện là placeholder trung thực, được
   test để không persist và không gọi provider. Chưa có Workspace Chat evidence
   pack/handoff thật.
6. **Roadmap cấp repo bị cũ ở phần Active Position.** Đây là vấn đề tài liệu
   rộng hơn gate này; sửa `ROADMAP.md` sẽ không còn là thay đổi tối thiểu và
   không nên trộn vào next implementation.

## 6. Các phương án

### Option A — Provider Success Smoke / Configured AI Success Path

Giá trị là đóng khoảng trống end-to-end quan trọng nhất của AI answer. Tuy
nhiên success behavior đã được mock-test; task hiện chưa implementation-ready
nếu chưa có quyết định provider/locality, secret handling và dữ liệu synthetic.
Không được tự thêm key, tự chọn cloud, hoặc dùng dữ liệu thật.

Thời điểm phù hợp: chạy như một smoke/audit độc lập ngay khi owner phê duyệt
provider target; không nên là implementation phase kế tiếp.

### Option B — Real-Work Owner Pilot Flow

Giá trị owner cao nhất vì nối các capability đã hoàn tất thành một hành trình
dễ tự dùng. Rủi ro scope cao nếu bao gồm cả provider setup, Case handoff và
redesign. Có thể làm implementation-ready bằng cách giới hạn vào information
architecture/copy/progressive disclosure của flow hiện có.

Thời điểm phù hợp: ngay tiếp theo, với scope hẹp nêu tại mục 8.

### Option C — Test/Browser Hardening

Giảm nợ test rõ ràng: stale-session automation, dead `msg`, seeded-ID fragility,
direct confirmation/cancel tests. Rủi ro kỹ thuật thấp và testability cao,
nhưng giá trị owner nhìn thấy thấp; accepted gap hiện không chặn MVP.

Thời điểm phù hợp: sau owner-flow slice, hoặc kéo lên ngay nếu pilot mới tìm
thấy lifecycle regression.

### Option D — Evidence Pack / Handoff Polish

Có giá trị cao sau một cuộc hội thoại, nhưng Workspace Chat hiện chỉ có
placeholder và repo đã có Case Cockpit/IDE bridge riêng. Làm ngay dễ tạo hai
nguồn sự thật, duplicate export contract hoặc coupling ngược.

Thời điểm phù hợp: design gate riêng sau khi owner-flow pilot xác nhận output
nào thực sự cần handoff.

### Option E — UX Consolidation

Giảm cognitive load và loại cảm giác “màn hình thử nghiệm”. Nếu chỉ làm visual
polish, phương án này có thể che provider/handoff gaps mà không cải thiện task
completion. Phần có ích của Option E được nhập vào Option B, đo theo hành trình
owner thay vì thẩm mỹ.

Thời điểm phù hợp: ngay bây giờ, nhưng chỉ như phương pháp thực hiện Option B,
không là phase riêng.

Không thêm Option F: bằng chứng repo chưa chỉ ra một capability mới có tỷ lệ
owner value/risk tốt hơn lát cắt Option B.

## 7. Ma trận quyết định

Thang điểm: owner value và testability `1` thấp đến `5` cao; safety risk và
implementation risk `1` thấp đến `5` cao.

| Option | Owner value | Safety risk | Implementation risk | Testability | Recommended timing |
|---|---:|---:|---:|---:|---|
| A. Provider success smoke | 4 | 4 | 3 | 3 | Khi owner phê duyệt provider |
| B. Real-work owner flow hẹp | 5 | 2 | 2 | 4 | **Tiếp theo** |
| C. Test/browser hardening | 2 | 1 | 2 | 5 | Sau B; sớm hơn nếu có regression |
| D. Evidence pack/handoff | 4 | 3 | 4 | 3 | Design riêng sau pilot |
| E. UX consolidation độc lập | 3 | 2 | 2 | 3 | Nhập vào B, không mở phase riêng |

## 8. Recommended next gate

### Task và model

- Exact task name:
  `IMPLEMENT_WORKSPACE_CHAT_PHASE2J_REAL_WORK_OWNER_FLOW`
- Model: **Codex**

Codex phù hợp vì task cần thay đổi nhỏ nhưng xuyên qua Streamlit wiring, copy và
structural owner-flow tests, đồng thời phải giữ nguyên nhiều safety invariants.
Task không cần khả năng provider/cloud hay nghiên cứu ngoài repo.

### Vì sao làm ngay

- Tận dụng trực tiếp Phase 2H/2I thay vì tiếp tục hardening nội bộ vô hạn.
- Mang lại giá trị owner nhìn thấy mà không cần secrets hoặc network.
- Blast radius có thể giữ ở app/UI/tests.
- Tạo một pilot thực tế để thu bằng chứng trước khi đầu tư vào provider setup
  hoặc handoff contract.

### Implementation scope

1. Tạo một owner-facing “đường đi tiếp theo” ngắn, progressive, dùng capability
   hiện có:
   - tạo/mở sổ;
   - thêm nguồn;
   - chọn hoặc sửa quyền riêng tư;
   - bật đúng nguồn;
   - kiểm tra nguồn local;
   - explicit ask hoặc nhận safe block;
   - quay lại danh sách và archive/restore khi hoàn tất.
2. Thu gọn checklist pilot dài thành trợ giúp collapsed, ngắn và theo ngữ cảnh.
3. Chuyển `Tạo dữ liệu test không mật` ra khỏi luồng chính và giữ nó trong một
   vùng trợ giúp/thử nghiệm collapsed; không xóa helper hoặc thay semantics.
4. Làm rõ trạng thái hiện tại và next action bằng copy tiếng Việt owner-facing;
   không thêm internal jargon.
5. Giữ `Lưu vào Case` là placeholder trung thực hoặc hạ độ nổi bật nếu cần;
   không hiển thị success giả, không persist.
6. Không thay đổi thứ tự safety backend: source resolution, privacy gate,
   exact-source consent và provider call.
7. Không thay đổi archive/restore persistence hoặc child-data policy.

### Non-goals / forbidden scope

- Không cấu hình provider, key, endpoint, model, network hoặc cloud.
- Không chạy real provider trong implementation.
- Không sửa `workspace_chat_ai_answer.py` hoặc provider/router modules.
- Không làm evidence pack, export, paste-back hay Case Cockpit integration.
- Không biến `Lưu vào Case` thành persistence thật.
- Không sửa model/store/schema, lifecycle semantics hoặc privacy mapping.
- Không hard delete, bulk action, rename hoặc migration.
- Không thêm dependency, RAG, vector, embedding, retrieval, citation, OCR hay
  file format mới.
- Không sửa `.ai`, `local_cases`, `task.md`, `walkthrough.md`,
  `implementation_plan.md` hoặc runtime JSON.
- Không sửa `ROADMAP.md`/`CHANGELOG.md` trong implementation task.
- Không stage, commit hoặc push nếu owner chưa yêu cầu rõ sau audit.

### Allowed files/categories

Production allowlist:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`

Test allowlist:

- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`

Documentation allowlist:

- một implementation audit mới:
  `docs/ux/WORKSPACE_CHAT_PHASE2J_REAL_WORK_OWNER_FLOW_IMPLEMENTATION_AUDIT.md`

Nếu implementation chứng minh cần file ngoài allowlist, phải dừng và xin owner
phê duyệt; không tự mở rộng.

### Tests bắt buộc

- Hành trình chính hiển thị next action đúng ở notebook list và active chat.
- Pilot help collapsed và không chặn flow chính.
- Safe test data không nằm trong action hierarchy chính, vẫn tạo đúng một
  synthetic non-secret source khi owner explicit click.
- Privacy choices/copy và all-or-nothing block giữ nguyên.
- Source check không lưu assistant message và không gọi provider.
- Typing, paste/upload và privacy edit không gọi provider.
- Explicit ask vẫn là đường duy nhất có thể gọi provider.
- Provider chưa cấu hình vẫn không tạo answer bubble/success giả.
- `Lưu vào Case` vẫn là placeholder, không persistence/provider call.
- Archive confirmation/cancel/restore và stale-session structural behavior
  không regression.
- Không lộ internal terms trong owner-facing copy.
- Chạy nguyên bộ `tests/test_workspace_chat_ai_answer.py` không sửa file này.

### Validation commands

```text
py -3 -m pytest tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git diff --name-only
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md
```

### Commit/push policy

- Implementation agent không stage, commit hoặc push.
- Sau implementation audit PASS, owner quyết định có audit độc lập và
  commit/push hay không.
- Không reset, clean, stash, delete hoặc ghi đè dirty work của owner.

### Owner smoke plan

Dùng dữ liệu synthetic, không mật và không yêu cầu provider:

1. Mở app, tạo một sổ mới và xác nhận next action dễ thấy.
2. Thêm một nguồn text có thể gửi AI; xác nhận không auto-call.
3. Kiểm tra nguồn; xác nhận thấy local preview và `AI chưa trả lời`.
4. Đổi nguồn thành `Chỉ dùng trên máy / không gửi AI`.
5. Explicit ask; xác nhận hard block, không answer bubble, không partial send.
6. Đổi lại `Có thể gửi AI`; explicit ask.
7. Nếu provider chưa cấu hình, xác nhận thông báo no-send trung thực. Provider
   success không phải điều kiện PASS của smoke này.
8. Kiểm tra `Lưu vào Case` không báo success/persist giả.
9. Quay lại danh sách, archive, cancel một lần, archive thật và restore.
10. Xác nhận dữ liệu/nguồn còn nguyên và runtime paths không dirty ngoài dữ
    liệu owner chủ động tạo cho smoke.

PASS khi owner tự hoàn tất hành trình mà không cần biết internal terms và không
có safety regression.

## 9. Risk controls

| Risk | Control |
|---|---|
| “UX consolidation” trượt thành redesign | Chỉ thay hierarchy/copy/progressive disclosure trong allowlist |
| Copy làm yếu privacy | Backend không sửa; regression tests chạy nguyên |
| Test helper bị hiểu là production action | Đưa vào vùng collapsed ghi rõ thử nghiệm |
| Handoff placeholder tạo kỳ vọng sai | Giữ feedback trung thực, không success/persist |
| Provider gap bị che | Ghi rõ unconfigured path chỉ là safe failure; Option A vẫn mở khi owner phê duyệt |
| Phase 2I bị mở lại | Không sửa model/store/lifecycle; stale browser gap ở backlog C |

## 10. Các gate sau task này

1. Chạy owner smoke Phase 2J.
2. Nếu owner đã chọn provider/locality: chạy task docs/audit độc lập
   `AUDIT_WORKSPACE_CHAT_LOCAL_DEV_PROVIDER_SMOKE_PATH`, sau đó mới smoke bằng
   synthetic data; không cần implementation provider trong Phase 2J.
3. Nếu pilot cho thấy handoff là điểm nghẽn: mở design gate riêng cho Workspace
   Chat evidence/handoff contract và kiểm tra overlap với Case Cockpit/IDE
   bridge.
4. Chạy `HARDEN_WORKSPACE_CHAT_PHASE2I_STALE_SESSION_BROWSER_AUTOMATION` cùng
   test hygiene khi accepted gap tăng rủi ro hoặc trước production-readiness,
   không chặn owner value hiện tại.

## 11. Final status

`PASS_READY_FOR_NEXT_IMPLEMENTATION_PROMPT`

Gate đã chọn đúng một primary next task, có allowlist, non-goals, tests,
validation và owner smoke đủ cụ thể để tạo implementation prompt tiếp theo.
