# Báo cáo vé TEST-STALE-GUARDS-HOME — dọn test bảo vệ chuỗi mã nguồn cũ + phân loại 2 ca truy xuất

- **Mã vé:** `TEST-STALE-GUARDS-HOME`
- **Máy thực hiện:** Nhà `h410asrock` (thợ OMP).
- **Thời điểm:** 2026-10-09 05:00 – 05:45 +07.
- **Căn cứ:** Mục 6 báo cáo `SYNTH-DEEPSEEK-PROTOCOL-HOME` — 5 ca đỏ triền miên che tín hiệu hồi quy thật.
- **Kết quả một câu:** **Đã dọn xong 5/5 ca — toàn bộ là test lạc hậu / chủ đích thiết kế, KHÔNG có hồi quy thật.** 3 ca chuỗi mã nguồn do `afd7fc6` (QUALITY2) đổi chủ đích; 1 ca preload do `1b33f88` (DENSE-NUMPY, verdict ĐẠT) đổi mặc định; 1 ca prefilter do `195b970` (PREFILTER-FIX) cải tiến lọc. Chỉ sửa test, không đụng `src/`.

---

## 1. Tái hiện 5 ca (trước sửa)

Chạy đúng 3 tệp vé nêu:

```
5 failed, 74 passed
FAILED test_app_preparation_gate_is_scoped_to_query_relevant_sources
FAILED test_app_retrieval_uses_the_exact_scope_that_preparation_checked
FAILED test_app_source_code_guards_for_large_library
FAILED test_dense_preload_disabled_without_flag — assert (8, 66.9…) == (0, 0.0)
FAILED test_cjk_prefilter_drops_short_term_only_matches — 'short-only' in […]
```

## 2. Ba ca bảo vệ chuỗi mã nguồn — chủ đích QUALITY2

Cả 3 ca đều đòi chuỗi `query_relevant_sources = ready_sources or ready_in_scope`
không còn tồn tại trong `workspace_chat_app.py`.

- **Commit thay:** `afd7fc6` (vé `UI-ANSWER-QUALITY2-HOME`) đổi thành
  `query_relevant_sources = ready_in_scope` — truy bằng `git log -S`, diff 1 dòng.
- **Xác nhận chủ đích:** báo cáo `ui-answer-quality2-home.md` mục 2.1–2.2:
  toán tử `or` chọn toàn bộ 75 nguồn MOM sẵn sàng, nuốt mất `ready_in_scope`
  (chỉ 1 nguồn đích C7620) → truy hồi chạy trên 75 tài liệu không liên quan,
  đè bẹp C7620. Verdict Muse 18:35 08/10 **công nhận chẩn đoán đúng**
  (CHƯA ĐẠT chỉ vì ảnh nghiệm thu, không phải vì sửa code).
- **Không phải hồi quy** → sửa test theo vé (khẳng định hành vi, không che lỗi).
- **Cách sửa test:** khẳng định hành vi mới — phạm vi giới hạn + có nguồn đích
  thì chỉ tìm nguồn đích (`= ready_in_scope`), cấm `or` nuốt nguồn đích;
  nhánh rộng vẫn tìm mọi nguồn sẵn sàng (`= ready_sources`).

## 3. Hai ca truy xuất — phân loại từng ca

### 3a. `test_dense_preload_disabled_without_flag` — lỗi TEST (giả định cũ)

- **Gốc:** `1b33f88` (vé `RETRIEVAL-DENSE-NUMPY-PC0575`, verdict **ĐẠT** 11:55
  08/10) đổi `numpy_dense_search_enabled()` từ "chỉ bật khi đặt cờ = 1"
  thành "**mặc định BẬT khi có numpy**" (tắt bằng cờ = 0).
- Test cũ `delenv` (xóa cờ) rồi kỳ vọng không nạp — giả định "mặc định tắt"
  không còn đúng. Thực tế đo: `(8, 66.9…)` — nạp đủ 8 chunk.
- **Không phải hồi quy** (parity 8/8 tuyệt đối ở vé gốc). Sửa test: đặt cờ
  `= "0"` (đường rollback 1 dòng) thay vì xóa cờ.

### 3b. `test_cjk_prefilter_drops_short_term_only_matches` — cải tiến CHỦ ĐÍCH

- **Gốc:** `195b970` (vé `CJK-PREFILTER-FIX-HOME`) gộp thực thể với thuật ngữ
  rồi lấy 2 cụm dài nhất. Với câu hỏi của vé, 2 cụm là `nguyên` + `beam径`:
  prefilter giữ đúng 4 mảnh thật, loại `short-only` — báo cáo vé mục 4 xác nhận
  thứ tự cuối `beam-ng, both, nguyen-nhan, metadata-only`.
- Điểm mới phát hiện khi tái hiện: **full-scan (đã tắt prefilter) cũng loại
  `short-only`** — tầng chấm điểm `_score_candidate` cho `short-only`
  (chỉ khớp `lỗi`/`iris`/`lsu`) điểm 3,0 nhưng không vượt ngưỡng xếp hạng
  đường thật. Prefilter và scorer đồng thuận loại cùng 1 mảnh nhiễu.
- **Không phải hồi quy** — test cũ kỳ vọng full-scan giữ `short-only` đã lạc hậu.
  Sửa test: khẳng định cả 2 tầng đều loại + prefilter là tập con của full-scan
  + giữ đúng 4 mảnh thật.

## 4. Kết quả sau sửa

- 3 tệp đã đụng: **79/79 PASS** (trước: 74/79).
- Lân cận: `test_rag_v2_index` + `test_rag_v2_numpy_dense` +
  `test_workspace_chat_rag_v2_adapter` + `test_workspace_chat_app_smoke`:
  **146/146 PASS**.
- Không chạy full suite (thay đổi chỉ trong 3 tệp test, vé cho phép khai rõ).
- Cổng repo: `compileall` sạch, `cli audit` `"status": "PASS"`,
  `import aios_habit.workspace_chat_app` OK.

## 5. Rào cứng đã giữ

- **Chỉ sửa test:** `git diff --stat` 3 tệp test, `diff HEAD -- src/` rỗng.
  Không đổi mã chạy thật (không phát hiện hồi quy thật nên không đụng hành vi).
- **Không ghi chỉ mục:** chỉ dùng chỉ mục tạm của kiểm thử (`tmp_path`).
- **Không merge `main`:** toàn bộ commit trên nhánh `phieu-viec/rag-fix1`.
- Commit sửa test: **`fb58bd6`**.

## 6. Tồn dư / ghi nhận

- Verdict QUALITY2 là CHƯA ĐẠT vì ảnh nghiệm thu — nhưng phần sửa `or`
  (gốc của 3 ca) được verdict công nhận đúng, và QUALITY3 ĐẠT phần nghiệm thu
  trên cùng codebase đã sửa. Đủ căn cứ coi hành vi mới là chủ đích.
- Nhóm 29 ca đỏ full-suite ở vé PROTOCOL nay còn **24 ca** (5 ca vé này đã xanh);
  24 ca còn lại toàn ngoài phạm vi (môi trường/thiếu tệp máy khác) theo phân loại
  mục 6 vé PROTOCOL — đề xuất vé tiếp theo dọn nốt nếu điều phối muốn tín hiệu
  full-suite sạch hẳn.
