# Báo cáo vé `pc0575-gui-verify` — Pull code chính sách + GUI mới (KDTVN-PC0575)

- Thời điểm: 2026-09-29 ~18:26–18:34 +07 (giờ máy `KDTVN-PC0575`)
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (ticket `pc0575-gui-verify`, Muse viết 18:19)
- Phạm vi: **chỉ đọc** code + `py_compile` + chạy test liên quan. Không sửa code,
  không đụng index production, không đổi env, không merge `main`.
- Commit OMP cho vé này: `77b89d0` (nhận vé + mốc 1), `7df1290` (mốc 2), commit này (báo cáo + chốt vé).

## 1. Pull (mục 1 của vé) — ĐẠT

```
$ git pull origin phieu-viec/rag-fix1
 * branch            phieu-viec/rag-fix1 -> FETCH_HEAD
   6fb8a07..8998fa1  phieu-viec/rag-fix1 -> origin/phieu-viec/rag-fix1
Updating 6fb8a07..8998fa1
Fast-forward
 11 files changed, 51 insertions(+), 134 deletions(-)
```

Đủ 2 commit của Muse theo yêu cầu vé:

| Commit | Nội dung | File đổi |
|---|---|---|
| `f27081d` | Gỡ chặn provider `local_only`/`confidential` (quyết định chủ sở hữu 2026-09-29) | `00_governance/DATA_POLICY.md` + 4 file code |
| `941c31c` | Dọn GUI — bỏ khối chặn provider `local_only` | 9 file code |

HEAD sau pull: `8998fa1`. 13 file code đã đổi = 4 (f27081d) + 9 (941c31c) — khớp mô tả vé.

## 2. Kiểm tra chỉ-đọc (mục 2 của vé) — ĐẠT cả 3

### 2.1 `src/aios_habit/provider_safety.py` — `check_privacy_gate` hết nhánh chặn `local_only`

Cổng hiện tại chỉ còn 2 nhánh cấu trúc + 1 kết quả cho phép:

```python
def check_privacy_gate(evidence_pack, provider_config):
    if not provider_config or not provider_config.enabled:
        return PrivacyGateResult(False, "provider_not_configured")
    if not evidence_pack.items:
        return PrivacyGateResult(False, "no_content_evidence")
    # 2026-09-29: chu so huu go han che local_only/confidential (DATA_POLICY.md).
    # Cong khong con chan provider ngoai; nhan chi con y nghia phan loai noi bo.
    return PrivacyGateResult(True, "")
```

Diff `f27081d` xác nhận đã xóa khối `is_confidential` (nhánh chặn `local_only_evidence` /
`confidential_evidence`). ✅

### 2.2 `src/aios_habit/workspace_chat_ui.py` — hết dòng `st.warning(t("privacy_blocked_status"...`

- `grep -n "privacy_blocked_status" src/aios_habit/workspace_chat_ui.py` → **0 hit** ✅
- Diff `941c31c` tại `render_source_library` (~dòng 766): khối

  ```python
  if not privacy_label_is_sendable(privacy_label):
      st.warning(t("privacy_blocked_status", locale=locale))
  ```

  đã được thay bằng đúng 1 dòng chú thích:
  `# 2026-09-29: bo canh bao chan (chu so huu cho phep gui provider, DATA_POLICY.md)`
- Các `st.warning` còn lại trong file đều thuộc tính năng khác (xóa nguồn, undo, handoff,
  dữ liệu nguồn thay đổi…) — không liên quan chặn privacy.
- `privacy_label_is_sendable` vẫn được dùng để hiển thị nhãn (không phải để chặn) — không phải code chết.

### 2.3 `py_compile` 13 file đã đổi — 13/13 OK

Lệnh (Python 3.11.15 của `.venv`, `PYTHONPYCACHEPREFIX` trỏ ra `%TEMP%` để không ghi cache vào repo):

```
for f in <13 file>; do .venv/Scripts/python.exe -m py_compile "$f" || FAIL; done
```

Kết quả: `OK` cho **13/13** file, `fail=0`:

```
notebook_qa.py, provider_safety.py, rag_v2/evidence.py, strong_answer_ui.py,
antigravity_bridge.py, final_answer_composer.py, fine_tune_eligibility.py, i18n.py,
ide_handoff_bridge.py, mom_local_index.py, rag_answer_composer.py, rag_evidence.py,
workspace_chat_ui.py
```

Sau khi chạy, `git status` không phát sinh file lạ (chỉ còn `uv.lock` sửa cục bộ có từ trước — xem mục 5).

## 3. Smoke hành vi cổng (bổ sung — chứng minh chính sách mới có hiệu lực)

Chạy `.venv/Scripts/python.exe` với `sys.path=["src"]`, dựng `RAGEvidencePack` +
`ProviderConfig` trong bộ nhớ (không chạm index/env):

```
1) local_only + provider EXTERNAL    : provider_call_allowed=True,  block_reason=''
2) local_only + provider LOCAL       : provider_call_allowed=True,  block_reason=''
3) metadata_only + provider EXTERNAL : provider_call_allowed=True,  block_reason=''
4) provider tắt (enabled=False)      : provider_call_allowed=False, block_reason='provider_not_configured'
5) pack rỗng (không có evidence)     : provider_call_allowed=False, block_reason='no_content_evidence'
```

→ Đúng chủ ý: **không còn chặn theo `local_only`/`confidential`** (kể cả provider ngoài);
2 chốt cấu trúc (chưa cấu hình provider / không có nội dung) vẫn giữ. ✅

## 4. Test hiện có trong repo (bổ sung) — 16 FAIL / 186 PASS ở 10 file liên quan trực tiếp

Lệnh:

```
.venv/Scripts/python.exe -m pytest tests/test_provider_safety.py tests/test_rag_evidence.py \
  tests/test_rag_v2_evidence.py tests/test_strong_answer_ui.py tests/test_antigravity_bridge.py \
  tests/test_fine_tune_eligibility.py tests/test_rag_answer_composer.py tests/test_final_answer_composer.py \
  tests/test_ide_handoff_bridge.py tests/test_workspace_chat_ui_copy.py -q -p no:cacheprovider
→ 16 failed, 186 passed in 58.17s
```

**Toàn bộ 16 FAIL đều là test cũ còn khẳng định hành vi chặn CŨ** (chưa được cập nhật trong
2 commit của Muse) — không phải lỗi phát sinh thêm của môi trường:

| # | File test | Test | Vì sao FAIL |
|---|---|---|---|
| 1 | `test_provider_safety.py` | `test_cloud_provider_blocked_when_evidence_is_local_only` | còn đòi `provider_call_allowed is False` |
| 2 | `test_provider_safety.py` | `test_metadata_only_evidence_blocks_final_answer` | còn đòi chặn metadata-only |
| 3 | `test_rag_evidence.py` | `test_privacy_normalization_and_external_guard` | `is_external_allowed` giờ trả `True` cho `local_only` |
| 4 | `test_rag_evidence.py` | `test_snippet_prompt_and_path_safety` | còn đòi chuỗi `"External export NOT allowed"` (đã đổi thành "owner allows provider use") |
| 5 | `test_rag_evidence.py` | `test_search_integration` | như #3 |
| 6 | `test_rag_v2_evidence.py` | `test_privacy_summary_local_only_wins` | còn đòi `cloud_allowed=False` khi có `local_only` |
| 7 | `test_rag_v2_evidence.py` | `test_identical_passages_with_different_privacy_are_not_collapsed` | như #6 |
| 8 | `test_strong_answer_ui.py` | `test_ui_prompt_export_blocks_direct_provider_call_for_local_only` | còn đòi `blocked_direct_provider_call=True` |
| 9 | `test_antigravity_bridge.py` | `test_local_only_cloud_fail_closed` | hết chặn cục bộ → test gọi mạng thật, nhận lỗi DNS `getaddrinfo failed` thay vì `"Bị chặn"` |
| 10–13 | `test_antigravity_bridge.py` | `test_local_only_mode_blocks_remote_endpoints_immediately[…4 URL…]` | như #9 (lỗi DNS / `WinError 10060` timeout / `WinError 10054` / HTTP 403 từ `api.openai.com`) |
| 14 | `test_fine_tune_eligibility.py` | `test_privacy_violation_disqualifies_fine_tune` | còn đòi loại vì `local_only` |
| 15 | `test_rag_answer_composer.py` | `test_compose_local_answer_local_only_privacy_warning` | `allowed_external` giờ `True` |
| 16 | `test_ide_handoff_bridge.py` | `test_local_only_privacy_warning_and_prompt_instruction` | còn đòi chuỗi `"local_only evidence"` (thông điệp đã đổi) |

Khuyến nghị cho Muse (ngoài phạm vi vé này, OMP không sửa code): cập nhật/xóa 16 test trên theo
chính sách mới ở một vé riêng — đây là hệ quả trực tiếp của quyết định chủ sở hữu 2026-09-29,
không phải hồi quy do môi trường.

Chưa chạy toàn bộ `pytest` (ngoài phạm vi vé; máy công ty thiếu env ONNX theo P3 — chạy full sẽ lẫn
lỗi môi trường không liên quan).

## 5. Quan sát thêm (chỉ đọc, không ảnh hưởng kết luận vé)

- `privacy_blocked_status` sau khi gỡ khỏi UI chỉ còn **định nghĩa** trong `i18n.py` (đã đổi nhãn
  "Nguồn phân loại nội bộ" / "内部分類のソース" / "内部分类来源" cho vi/ja/zh), không còn nơi dùng
  trong `src/` — chuỗi chết, không phải lỗi chặn.
- Nhánh render `badge_data["type"] == "privacy_block"` trong `workspace_chat_app.py:3455` hiện
  **không còn nguồn sinh badge** `"privacy_block"` nào trong `src/` → nhánh này (và
  `render_privacy_block_message`) thành đường không tới được; Muse cân nhắc dọn cùng đợt test.
- Các cổng liên quan đã đổi đồng bộ cùng chính sách: `rag_evidence.is_external_allowed` trả `True`
  cho `local_only`; `rag_v2/evidence._BLOCKED_PRIVACY_LABELS` = rỗng.
- `uv.lock` có thay đổi cục bộ **từ trước vé này** (OMP không đụng, không commit).
- P5 (`p5-mang-cay-onnx`) vẫn tạm dừng — vé này không chạm gì tới P5/ONNX/index.

## 6. Kết luận

**3/3 mục của vé ĐẠT, không có FAIL.** Không sửa code, không đụng index/env, không merge `main`.
`trang-thai.md` chuyển `xong-cho-duyet` — chờ Muse review.
