# Workspace Chat Phase 2J Real-Work Owner Flow Implementation Audit

## 1. Baseline

- Branch: `main`
- HEAD: `dcfd5e1719e3a2997b98e6a17706d84eeda3a2f2`
- `origin/main`: `dcfd5e1719e3a2997b98e6a17706d84eeda3a2f2`
- Ahead/behind trước implementation: `0/0`
- Worktree trước implementation: sạch
- Runtime paths trước implementation: sạch
- Design gate:
  `docs/ux/WORKSPACE_CHAT_AFTER_PHASE2I_NEXT_ROADMAP_GATE.md`

## 2. Scope implemented

Phase 2J chỉ thay đổi hierarchy và copy owner-facing:

- thêm chỉ dẫn `Bước tiếp theo` ngắn ở danh sách sổ;
- thêm chỉ dẫn next action ngắn trong active chat;
- thay checklist Pilot mở mặc định bằng `Xem luồng làm việc đề xuất` collapsed;
- luồng collapsed giải thích thêm nguồn, chọn quyền riêng tư, bật nguồn, kiểm
  tra nguồn local, explicit ask, safe block và archive/restore;
- chuyển test-data helper xuống sau các đường thêm nguồn thật và đặt trong
  `Công cụ thử nghiệm an toàn` collapsed;
- giữ test-data creation explicit-click only;
- làm rõ source check chỉ đọc nội dung trên máy, vẫn là `AI chưa trả lời`;
- giữ `Lưu vào hồ sơ` là placeholder trung thực.

Không thêm hard gate bắt buộc source check trước AI ask. Đây chỉ là
copy/hierarchy polish.

## 3. Files changed

Production:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`

Tests:

- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`

Documentation:

- `docs/ux/WORKSPACE_CHAT_PHASE2J_REAL_WORK_OWNER_FLOW_IMPLEMENTATION_AUDIT.md`

Không có file ngoài allowlist được sửa.

## 4. Explicit non-goals

- không provider setup, API key, endpoint, model config hoặc real provider call;
- không Case persistence hoặc Case Cockpit integration;
- không evidence pack, export hoặc handoff implementation;
- không model/store/schema change;
- không lifecycle semantic hoặc archive/restore persistence change;
- không hard delete, cascade delete, bulk action hoặc migration;
- không privacy backend/mapping change;
- không dependency, RAG, vector, embedding, citation, OCR hoặc file format mới.

## 5. Safety preservation

- Privacy tiếp tục all-or-nothing: một enabled local-only source chặn toàn bộ
  request; mixed sendable/local-only không partial send.
- AI path vẫn chỉ bắt đầu từ explicit ask.
- Typing, paste, upload, privacy edit và source check không gọi provider.
- Source check không lưu assistant message và hiển thị `AI chưa trả lời`.
- Provider-not-configured vẫn là safe failure; không fake answer bubble.
- Không có local-only leakage.
- Test-data helper chỉ chạy sau explicit button click.
- `Lưu vào hồ sơ` chỉ set placeholder state, không persistence/provider call và
  không hiển thị fake success.
- Archive/restore callbacks, confirmation/cancel copy, persisted lifecycle và
  stale-session structural path không thay đổi.
- `tests/test_workspace_chat_ai_answer.py` chạy nguyên vẹn, không sửa.

## 6. Test changes

Test mới/cập nhật kiểm tra:

- notebook next action và full owner-flow guidance bằng rendered mock calls;
- flow help là expander collapsed;
- guidance chứa create/open, source, privacy, local source check, explicit ask,
  safe-block recovery, archive và restore;
- guidance không lộ internal jargon;
- safe test tool nằm sau Excel source path, collapsed và explicit-click only;
- safe test helper không gọi AI/provider;
- copy Phase 2H được kiểm tra trên tổng owner-facing app/UI sau khi chuyển copy
  vào UI helper; assertions không bị xóa.

Các regression test privacy, source check, AI answer, placeholder và lifecycle
được giữ nguyên.

## 7. Validation results

```text
Targeted owner-flow/source/copy tests: 63 passed in 1.48s
AI answer tests unchanged: 41 passed in 0.44s
Full suite: 701 passed in 9.70s
CLI audit: PASS, no warnings
git diff --check: PASS
Runtime dirty check: empty
```

Git có thông báo line-ending dự kiến rằng LF có thể được đổi sang CRLF khi Git
chạm file trên Windows; không có whitespace error từ `git diff --check`.

## 8. Owner smoke checklist

Sử dụng dữ liệu synthetic, không mật:

1. Mở app; xác nhận danh sách sổ chỉ rõ mở sổ hoặc tạo sổ mới.
2. Tạo/mở sổ và cuộc trò chuyện; xác nhận `Bước tiếp theo` dễ thấy.
3. Mở `Xem luồng làm việc đề xuất`; xác nhận mặc định collapsed và nội dung
   ngắn, đúng thứ tự.
4. Dán một nguồn, chọn `Có thể gửi AI`, xác nhận không auto-call.
5. Bật nguồn và bấm `Kiểm tra nguồn trước`; xác nhận local preview và
   `AI chưa trả lời`, không có assistant message.
6. Đổi nguồn sang `Chỉ dùng trên máy / không gửi AI`, explicit ask và xác nhận
   exact hard-block copy, không partial send.
7. Đổi lại sendable và explicit ask; nếu provider chưa cấu hình, xác nhận safe
   failure trung thực và không fake answer.
8. Mở `Công cụ thử nghiệm an toàn`; xác nhận không có dữ liệu được tạo trước
   khi bấm nút, rồi bấm và xác nhận đúng một source synthetic được tạo/bật.
9. Bấm `Lưu vào hồ sơ`; xác nhận chỉ có placeholder info, không success/persist.
10. Quay lại danh sách; thử archive confirmation, cancel, archive và restore;
    xác nhận dữ liệu còn nguyên và không có hard delete.

## 9. Known gaps

- Provider success smoke vẫn là task riêng sau khi owner phê duyệt provider,
  locality và secret-safe synthetic procedure.
- Evidence/handoff vẫn cần design gate riêng để tránh overlap Case Cockpit/IDE
  bridge.
- Stale two-session browser hardening vẫn là future task:
  `HARDEN_WORKSPACE_CHAT_PHASE2I_STALE_SESSION_BROWSER_AUTOMATION`.
- Owner browser smoke Phase 2J chưa chạy trong implementation audit này.

## 10. Final status

`PASS_READY_FOR_CODEX_AUDIT`

Implementation nằm đúng allowlist, không sửa backend/store/schema/provider,
targeted tests, unchanged AI-answer tests, full suite, CLI audit, diff check và
runtime dirty check đều PASS. Không stage, commit hoặc push.
