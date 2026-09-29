# Báo cáo vé `pc0575-test-cleanup` — Dọn 16 test cũ + code chết theo chính sách mới (KDTVN-PC0575)

- Thời điểm: 2026-09-29 18:39–18:50 +07 (giờ máy `KDTVN-PC0575`)
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (ticket `pc0575-test-cleanup`, Muse viết 18:40)
- Commit OMP cho vé này: `ce11d5f` (nhận vé + `dang-lam`), `d8e7470` (16 test + code chết),
  commit này (báo cáo + chốt vé).
- Phạm vi: chỉ 16 test cũ + 2 điểm code chết. Không merge `main`, không đụng index production,
  không chạy batch embed, không đụng mailbox máy nhà (`docs/phieu-viec/mailbox/`).

## 1. Pull (mục 1 của vé) — ĐẠT

```
$ git pull origin phieu-viec/rag-fix1
 * branch            phieu-viec/rag-fix1 -> FETCH_HEAD
   bb964df..b73d0fa  phieu-viec/rag-fix1 -> origin/phieu-viec/rag-fix1
Updating bb964df..b73d0fa
Fast-forward
 docs/phieu-viec/mailbox-pc0575/prompt.md     | 55 ++++++++++++++++++++--------
 docs/phieu-viec/mailbox-pc0575/trang-thai.md | 27 +++++---------
```

HEAD sau pull: `b73d0fa` (commit vé của Muse). Commit liền trước là `bb964df` — verdict vé
`pc0575-gui-verify` → HEAD có commit verdict trước, đúng yêu cầu mục 1.

## 2. 16 test cập nhật theo chính sách MỚI (mục 2 của vé) — ĐẠT

Nguyên tắc áp dụng: giữ nguyên hành vi test đang kiểm ở chỗ hành vi đó **còn tồn tại** (ví dụ
nhánh `cloud_safe` + `allow_external_for_cloud_safe=False` vẫn chặn), chỉ đổi phần assert gắn
với chặn `local_only`/`metadata-only`. Không xóa test nào — cả 16 hành vi mới đều còn kiểm được.

| # | File | Test (tên mới) | Sửa gì | Vì sao |
|---|---|---|---|---|
| 1 | `test_provider_safety.py` | `test_cloud_provider_allowed_when_evidence_is_local_only` (đổi tên từ `..._blocked_...`) | `provider_call_allowed is True`, `block_reason == ""` | `check_privacy_gate` (`f27081d`) đã xóa nhánh `is_confidential`; test cũ vẫn đòi `False` / `"local_only_evidence"` |
| 2 | `test_provider_safety.py` | `test_metadata_only_evidence_does_not_block_provider_call` (đổi tên từ `..._blocks_final_answer`) | như #1 | nhánh `is_confidential` cũ gồm cả `_is_metadata_only == "True"` — đã bị xóa cùng commit |
| 3 | `test_rag_evidence.py` | `test_privacy_normalization_and_external_policy` (đổi tên từ `..._external_guard`) | `mixed.allowed_external is True`; giữ `privacy_mode == "local_only"`, `route_hint == "local_only"`, và cặp `cloud_safe` allowed/blocked theo config | `is_external_allowed` (`941c31c`) trả `True` cho `local_only`; nhánh config `allow_external_for_cloud_safe=False` vẫn chặn nên assert cũ giữ nguyên |
| 4 | `test_rag_evidence.py` | `test_snippet_prompt_and_path_safety` | chuỗi kỳ vọng `"External export NOT allowed"` → `"owner allows provider use"` | thông điệp PRIVACY NOTICE mới trong `format_evidence_pack_for_prompt` |
| 5 | `test_rag_evidence.py` | `test_search_integration` | `pack.allowed_external is True` | như #3 (kết quả search có chunk `local_only`) |
| 6 | `test_rag_v2_evidence.py` | `test_privacy_summary_local_only_label_recorded_but_cloud_allowed` (đổi tên từ `test_privacy_summary_local_only_wins`) | `"local_only" in labels_present`, `cloud_allowed is True`, `overall_label == "cloud_safe"` | `_BLOCKED_PRIVACY_LABELS = frozenset()` (`f27081d`) → `_compute_privacy_summary` không còn nhánh "strictest-wins" |
| 7 | `test_rag_v2_evidence.py` | `test_identical_passages_with_different_privacy_are_not_collapsed` | như #6, giữ `item_count == 2` | cùng lý do #6; mục đích test (không gộp 2 đoạn giống nhau khác nhãn) không đổi |
| 8 | `test_strong_answer_ui.py` | `test_ui_prompt_export_allows_direct_provider_call_for_local_only` (đổi tên từ `..._blocks_...`) | `blocked_direct_provider_call is False`, `privacy_warning == ""` | `build_strong_answer_prompt_for_ui` (`f27081d`) hard-code `blocked = False`, `warning = ""` |
| 9 | `test_antigravity_bridge.py` | `test_local_only_cloud_not_blocked_locally` (đổi tên từ `test_local_only_cloud_fail_closed`) | `monkeypatch` thay `bridge_module.urllib.request.urlopen` bằng hàm ghi lại `req.full_url` rồi raise `OSError`; assert `attempts == [endpoint]`, `ok is False`, `"Bị chặn" not in error_message` | cổng chặn fail-closed đã gỡ (`941c31c`); test cũ gọi mạng thật nên nhận lỗi DNS. Bản mới **không gọi mạng thật** và chứng minh lời gọi *đã được thử* |
| 10–13 | `test_antigravity_bridge.py` | `test_local_only_mode_no_longer_blocks_remote_endpoints[4 URL]` (đổi tên từ `..._blocks_remote_endpoints_immediately`) | như #9 | cùng lý do #9 (4 test tham số hóa qua 4 URL ngoài) |
| 14 | `test_fine_tune_eligibility.py` | `test_privacy_violation_disqualifies_fine_tune` | tách 2 ca: audio thô vẫn `BLOCKED_PRIVACY`; `has_local_only_data=True` (1000 mẫu, baseline 0.60) giờ `is_eligible is True` + `ELIGIBLE` | `has_local_only_data` bị bỏ khỏi Rule 1 (`941c31c`); PII/secrets vẫn chặn |
| 15 | `test_rag_answer_composer.py` | `test_compose_local_answer_local_only_privacy_warning` | `draft.allowed_external is True`; thay `"must not be exported externally"` → `"owner allows provider use"` | `compose_local_answer` + `is_external_allowed` theo chính sách mới |
| 16 | `test_ide_handoff_bridge.py` | `test_local_only_note_and_prompt_instruction` (đổi tên từ `..._privacy_warning_...`) | chuỗi kỳ vọng `"local_only evidence"` → `"local_only-classified evidence"` | `build_ide_task_instruction` (`941c31c`) đổi `PRIVACY WARNING` → `NOTE` |

Ghi chú: file thứ 10 của lệnh pytest là `tests/test_final_answer_composer.py` — **không có test
nào fail** ở file này nên không phải sửa (0 thay đổi).

7 test được đổi tên vì tên cũ khẳng định đúng hành vi đã bị gỡ (`blocked` / `fail_closed` /
`must not be exported`) — giữ tên cũ sẽ khiến test nói ngược với thứ nó kiểm.

## 3. Code chết đã dọn (mục 3 của vé) — ĐẠT

### 3.1 `privacy_blocked_status` trong `i18n.py` (vi/ja/zh)

Grep trước khi xóa (`src/`, `tests/`, `scripts/`): chỉ còn 3 dòng định nghĩa trong `i18n.py`
(dòng 174 `vi`, 1033 `ja`, 1892 `zh`), **0 nơi dùng**. Đã xóa cả 3. Grep lại: 0 hit.

### 3.2 Nhánh badge `"privacy_block"` + `render_privacy_block_message`

Grep `"privacy_block"` trong `src/` trước khi xóa:
- `workspace_chat_app.py:695` (import), `:3455` (`elif badge_data.get("type") == "privacy_block":`), `:3456` (gọi hàm)
- `workspace_chat_ui.py:1280` (định nghĩa `render_privacy_block_message`)
- **Không có nơi nào sinh badge `type == "privacy_block"`** — soát toàn bộ literal badge type:
  `ai_answered` (4 nguồn), `insufficient_context` (2 nguồn), `local_fallback_offered`
  (`antigravity_bridge.py:652`), còn `privacy_block` chỉ có đúng dòng tiêu thụ.

Đã xóa: dòng import trong `workspace_chat_app.py`, nhánh `elif` (2 dòng), hàm
`render_privacy_block_message` (3 dòng) trong `workspace_chat_ui.py`. Grep lại: 0 hit cả 3 chuỗi.

### 3.3 Hệ quả kéo theo (báo rõ để Muse review)

- `i18n.py`: xóa luôn `privacy_ai_hard_block_copy` (vi/ja/zh) — sau khi bỏ
  `render_privacy_block_message` thì đây là **nơi dùng duy nhất** còn lại của chuỗi này ⇒ chuỗi
  chết đúng tiêu chí "chỉ còn định nghĩa, 0 hit trong `src/`" như `privacy_blocked_status`.
  Grep trước khi xóa: `i18n.py:177/1036/1895` + `workspace_chat_ui.py:1282`. Grep lại: 0 hit.
  Không đụng hằng `PRIVACY_AI_HARD_BLOCK_COPY` trong `workspace_chat_ui.py` (xem 5.e).
- `tests/test_workspace_chat_ui_copy.py:247`: xóa 1 dòng
  `assert "render_privacy_block_message" in app_source` (assert sự tồn tại của hàm vừa bị gỡ;
  giữ lại sẽ FAIL). Hai dòng assert anh em (`render_ai_answer_header`, `render_insufficient_context`)
  giữ nguyên. Đây là thay đổi ngoài danh sách 16 test, **bắt buộc** để đạt mục 4 (0 FAIL).

## 4. Kiểm chứng (mục 4 của vé) — ĐẠT

```
$ .venv/Scripts/python.exe -m pytest tests/test_provider_safety.py tests/test_rag_evidence.py \
  tests/test_rag_v2_evidence.py tests/test_strong_answer_ui.py tests/test_antigravity_bridge.py \
  tests/test_fine_tune_eligibility.py tests/test_rag_answer_composer.py tests/test_final_answer_composer.py \
  tests/test_ide_handoff_bridge.py tests/test_workspace_chat_ui_copy.py -q -p no:cacheprovider
202 passed in 20.93s
```

→ **202 passed, 0 failed** (vé trước: `16 failed, 186 passed in 58.17s`). Thời gian chạy giảm
vì 5 test antigravity không còn gọi mạng thật.

```
$ py_compile 12 file đã đổi (PYTHONPYCACHEPREFIX trỏ ra %TEMP%)
py_compile OK=12 FAIL=0
$ .venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src'); import aios_habit.workspace_chat_app"
import workspace_chat_app OK
```

Interpreter: `.venv/Scripts/python.exe` = Python 3.11.15.

Probe thêm ngoài vé (để tìm hồi quy do chính sách, xem 5.a):
`tests/test_workspace_chat_ai_answer.py` → `61 passed`.

## 5. Phát hiện mới (không tự sửa theo yêu cầu vé)

**a) Còn một cổng chặn `local_only` trong luồng `workspace_chat_ai_answer`.** Không nằm trong 2
commit chính sách của Muse nên vẫn còn nguyên:

```python
# src/aios_habit/workspace_chat_ai_answer.py:234
def is_privacy_label_cloud_allowed(label): return cleaned in {"machine_only", "cloud_allowed"}
# :963
has_blocked_source = any(not is_privacy_label_cloud_allowed(src.privacy_label) for src in request.context_sources)
# :971 → "Chưa gửi tới AI. Một hoặc nhiều nguồn chỉ được dùng trên máy."
```

3 test **đang xanh** trong `tests/test_workspace_chat_ai_answer.py`
(`test_generate_workspace_ai_answer_cloud_privacy_block_{local_only,confidential,unknown}`) đang
ghim hành vi chặn này (`ok is False`, `client.call_count == 0`). Gọi `generate_workspace_ai_answer`:
`antigravity_bridge.py:1193`, `query_planner.py:176`, `scripts/battle_notebooklm_rag_v2.py:3138/3147`;
`workspace_chat_app.py` có import nhưng call site (`:4312`) đang bị comment.
→ Cần Muse quyết: mở cổng này theo chính sách mới (và cập nhật 3 test), hay giữ có chủ ý vì đây là
luồng consent riêng.

**b) `badge_data.get("type") == "source_changed"` cũng là nhánh không có nguồn sinh** — cùng loại
với `privacy_block`, chỉ khác là không có trong danh sách vé nên OMP giữ nguyên
(`render_source_changed_message` vẫn được import và dùng).

**c) `privacy_summary` mất tính "strictest-wins"**: pack có nhãn `local_only` giờ báo
`local_only == False` và `overall_label == "cloud_safe"` (nhãn vẫn được ghi ở `labels_present`).
Đúng về mặt "cho phép gửi provider", nhưng tên/ngữ nghĩa trường `local_only` + `overall_label`
giờ dễ gây hiểu sai — cân nhắc đổi tên hoặc ghi chú trong docstring
(`src/aios_habit/rag_v2/evidence.py:_compute_privacy_summary`).

**d) `manifest["allowed_external"]` của bundle IDE handoff vẫn tính theo công thức cũ**
(`ide_handoff_bridge.py:472`: `"allowed_external": privacy != "local_only"`) → bundle có
`local_only` vẫn ghi `false`, trong khi đường provider đã được mở. Test #16 vẫn giữ assert
`is False` (nó chưa từng fail). Không sửa vì ngoài phạm vi vé.

**e) Copy chủ sở hữu còn treo**: `PRIVACY_AI_HARD_BLOCK_COPY` và `PRIVACY_BLOCKED_STATUS`
(`workspace_chat_ui.py:82,85`) **0 nơi dùng trong code**, nhưng
`test_phase2i_exact_owner_privacy_copy_and_no_owner_enum_leak` đòi nguyên văn các chuỗi này
trong `workspace_chat_ui.py` → giữ lại, không xóa.

**f)** `specs/antigravity-truthful-bridge/plan.md:201` còn trỏ tên test cũ
(`TestAntigravityPrivacyAndSanitization::test_local_only_cloud_fail_closed`, đã đổi tên ở #9).
OMP không sửa (ngoài phạm vi vé).

**g)** Artifact sinh tự động (`graphify-out/*.json`, `.understand-anything/intermediate/batches.json`)
còn tên test cũ — bỏ qua, sinh lại được.

**h)** `uv.lock` tiếp tục có thay đổi cục bộ **từ trước vé** — OMP không đụng, không commit.

## 6. Kết luận

5/5 mục của vé ĐẠT: pull đúng HEAD, 16/16 test assert chính sách mới, 2 điểm code chết đã dọn
(kèm 1 chuỗi chết kéo theo + 1 assert test phải bỏ), pytest 10 file **0 FAIL**, py_compile 12/12 OK,
`import workspace_chat_app` OK. Không merge `main`, không đụng index/env, không đụng mailbox máy nhà.
`trang-thai.md` → `xong-cho-duyet` — chờ Muse review.
