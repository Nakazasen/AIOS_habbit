# Vé E2 vòng 3 — Fix chọn dòng: loại nhiễu tên bảng + neo `.exe` không tên

Ngày viết: 2026-09-29 (Muse VM, chế độ tự lái: CẤM hỏi user, ĐIỀU HƯỚNG ĐẾN XONG).
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Không force-push.

## Verdict E2v2: CHƯA ĐẠT (Muse verify độc lập, 2026-09-29 ~06:30 +07)

Bằng chứng (báo cáo `docs/phieu-viec/ket-qua/VE_E2_vong2_chon-dong.md`, commit `97d6e53`,
fetch + đọc toàn văn trên VM):
- Lượt chạy đúng commit fix `b8f06d6` (`gate_sha` nằm trong lịch sử HEAD, `is_ancestor_of_head=true`).
- B1 ĐẠT (đủ `11922`/`12860`/`12626`), B3 ĐẠT (nguyên văn `nvarchar(4000)`).
- **B2 RỚT**: toàn văn câu trả lời không có `YY2-Z151.exe`/`YY2-Z152.exe` — thoái lui chưa khôi phục.
- **B5 RỚT**: toàn văn không có định nghĩa `HOUSE_METHOD` (`'0'`:倉庫へ格納 / `'1'`:検査).
  Bộ chấm ngữ cảnh tự kiểm 9/9; chuỗi `'1'` thô trong đáp án là của `RECEIVE_TYPE`
  (`'1':マニュアル入庫`) — chấm ngữ cảnh từ chối đúng, không dương tính giả.
- An toàn giữ nguyên: SHA kho D `062ec090…` không đổi trước/sau lượt, snapshot cây D
  0 thêm/0 xóa/0 đổi, 51 mẫu `netstat` = 0 kết nối, `provider_used=false` cả 5 câu,
  fail-closed chứng minh được (6 khóa cloud còn nguyên trong env).
- Rớt 2/3 dòng kiểm có tên → **CHƯA ĐẠT**. Báo cáo OMP trung thực, phân tích nguyên nhân
  gốc đúng — dùng làm đầu vào Phase A vòng 3.

## Nguyên nhân gốc (dump `e2v2_dump_b2b5.json`, trace bằng chính `_fragment_score`)

1. **B5 — hoà điểm 1-1 vì tên bảng bị tính là "mã trường"**:
   `_extract_field_codes(B5)` = `('t_parts_recieve','house_method')` — tên bảng `T_PARTS_RECIEVE`
   cũng khớp `_FIELD_CODE_RE` (`[A-Z][A-Z0-9_]{3,}`) nên được cấp cùng trọng số với mã trường
   được hỏi. Mảnh `[3]` (bảng, 993 ký tự, vị trí 3/19) hoà khóa 1 với mảnh `[12]`
   (định nghĩa `HOUSE_METHOD`, 371 ký tự, vị trí 12/19), thắng ở `answer_value` 12 vs 11
   → định nghĩa `HOUSE_METHOD` không được chọn vào câu trả lời.
2. **B2 — ưu tiên mã tệp không kích hoạt**: `_extract_file_identifiers(B2)` = `()` —
   câu hỏi chỉ nói "tên tệp thực thi (.exe)" chung chung, không nêu tên tệp cụ thể, mà
   `_FILE_IDENTIFIER_RE` chỉ bắt tên **có trong câu hỏi**. Khóa `file_identifier` = 0 cho
   **mọi** mảnh → fix vòng 2 không đổi gì cho B2. Mảnh `[1]` (chứa cả 2 tên tệp, 837 ký tự,
   vị trí 1/10) vẫn thua `terms∩=6 < 8` như vòng 1.

## Phase A — Muse code trên VM (OMP KHÔNG làm gì ở phase này)

1. **Loại nhiễu tên bảng**: token dạng tên bảng (`T_<TÊN>` như `T_PARTS_RECIEVE`,
   `T_IF_PROD_RESULT`) không được tính là mã trường trong `_extract_field_codes`
   (tối thiểu: bỏ qua token khớp `^T_[A-Z0-9_]+$`). Và/hoặc: chỉ cấp điểm ưu tiên mã trường
   cho mảnh chứa mã trường **kèm giá trị mã hóa** — đúng hình dạng dòng định nghĩa cần lấy
   (mã trường + chuỗi trích dẫn/`'0'`/`'1'`).
2. **Neo `.exe` khi câu hỏi không nêu tên cụ thể**: khi câu hỏi có tín hiệu "tệp thực thi"/
   `.exe`/`executable` nhưng `_extract_file_identifiers` trả rỗng, lấy neo từ pack —
   ưu tiên mảnh chứa identifier `*.exe` bất kỳ (không chỉ tên nêu trong câu hỏi).
3. **Test** (SQLite `:memory:`, không ghi index; dữ liệu mô phỏng từ dữ liệu thật, gắn mác
   `SIMULATED_` theo lệnh user 2026-09-28 21:14):
   - (a) B5-like: câu hỏi chứa cả tên bảng `T_*` lẫn mã trường → mảnh định nghĩa
     (mã trường + giá trị mã hóa) phải thắng mảnh bảng.
   - (b) B2-like: câu hỏi hỏi chung "`*.exe`" không nêu tên → mảnh chứa tên tệp `.exe`
     phải được chọn.
   - (c) Chống thoái lui: 5 test vòng 2 (`tests/test_e2v2_line_selection.py`) + toàn bộ
     test synthesis hiện có vẫn pass.
4. Commit riêng, push fast-forward (cấm force).
5. Khi code push xong, Muse cập nhật mailbox (`trang-thai.md` → `moi`, ghi `e2v3_fix_commit`).
   **OMP chỉ sang Phase B khi thấy dòng `e2v3_fix_commit` trong mailbox.**

## Phase B — OMP chạy trên h410asrock (chỉ khi mailbox đã báo e2v3_fix_commit)

1. Pull commit fix. Không sửa code để "cho qua".
2. Chạy lại B1–B5 đúng protocol P1.4/E2/E2v2: câu hỏi
   `docs/phieu-viec/ket-qua/FIX3_dieu-tra-B-sai.md`; tuyến nội bộ (deterministic/local, cấm cloud);
   index dùng bản copy trên C (`C:\\AIOS_p1_4\\tri_thuc\\library.sqlite`, mở `mode=ro`),
   kiểm SHA khớp `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`;
   cấm ghi D; B4 loại khỏi chấm điểm.
3. ĐIỂM GIỮ NGUYÊN so với các vòng trước: **giữ nguyên** biến môi trường khóa cloud của máy
   (không blank) để kiểm chứng fix fail-closed — yêu cầu `provider_used=false` và worker stderr
   không có dòng gọi provider nào (cổng an toàn chạy trước như E2v2).
4. Báo cáo `docs/phieu-viec/ket-qua/VE_E2_vong3_chon-dong.md`: diff hành vi trước/sau fix,
   kết quả B1–B5 nguyên văn + latency, bằng chứng không ghi D (SHA + snapshot),
   bằng chứng fail-closed, phân tích nguyên nhân nếu còn rớt. Cập nhật mailbox `xong-cho-duyet`.

## Tiêu chí ĐẠT (Phase B)

- B1/B2/B3/B5 chạy xong, không lỗi, không timeout.
- B3 giữ được `nvarchar(4000)` (không thoái lui).
- B5 nêu được định nghĩa HOUSE_METHOD (`'0'` cất vào kho / `'1'` kiểm tra) —
  chấm theo ngữ cảnh `HOUSE_METHOD` + `倉庫`/`検査`, CẤM chấm bằng khớp chuỗi `'1'` thô.
- B2 giữ được `YY2-Z151.exe`/`YY2-Z152.exe`.
- Câu trả lời grounded từ bằng chứng truy xuất (không bịa).
- Không byte nào ghi lên D (kiểm chứng được: snapshot + SHA).
- Không dữ liệu nào rời máy — kể cả khi khóa cloud tồn tại trong env (kiểm chứng fail-closed).

Rớt 1 trong các dòng kiểm có tên cụ thể (B3/B5/B2) → CHƯA ĐẠT, ghi rõ điểm rớt còn lại
+ nguyên nhân gốc ở khâu nào (trích trace `_fragment_score` như vòng 2).

## Cấm kỵ

- Không gọi AI ngoài dưới mọi hình thức (kể cả "thử một câu").
- Không ghi lên D (kể cả log, cache, ledger).
- Không `--apply`, không vacuum, không embed.
- Không đụng `main`. Không force-push.

## Hàng đợi sau E2 (chưa làm, không nhét vào vé này)

- 422/496 document stale ở chế độ read-only → cần lượt chuẩn bị lại (có ghi/embed) do OMP làm.
- `source_path` trong index trỏ `..._canary/materialized_sources/` → xác nhận đường chuẩn bị
  nguồn trước khi app production truy vấn.
- E3 dọn XML ở extractor; E4 default backend ONNX fp32.
