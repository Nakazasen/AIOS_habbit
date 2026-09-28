# Vé E2 vòng 2 — Fix chọn dòng: ưu tiên mã trường + mã tệp

Ngày viết: 2026-09-29 (Muse VM, chế độ tự lái: CẤM hỏi user, ĐIỀU HƯỚNG ĐẾN XONG).
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Không force-push.

## Verdict E2: CHƯA ĐẠT

Bằng chứng (báo cáo `docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`, commit `4aa6d68`,
verify độc lập SHA/diff: commit chỉ thêm báo cáo + sửa mailbox, không sửa code):
- Rớt 1 trong 2 dòng kiểm then chốt → CHƯA ĐẠT theo chính tiêu chí của vé.
- **B3 ĐẠT** (đã nêu nguyên văn `nvarchar(4000)`) — giữ, không được thoái lui.
- **B5 RỚT**: đoạn `[12]` (doc `wsc-ff8304af86028eaa474a1706`, 371 ký tự, vị trí 11/19 trong pack,
  `score=1.0`) có nguyên văn `19 格納方法 HOUSE_METHOD varchar '0':倉庫へ格納'1':検査` nhưng câu
  trả lời chỉ trích `[3]`,`[17]`,`[16]`,`[11]`,`[9]`. Rớt ở **khâu chọn dòng soạn câu trả lời**,
  không phải truy xuất hay đóng gói bằng chứng (đoạn đáp án đã nằm trong pack). Fix Phase A
  (commit `725c40f`) chưa phủ được trường hợp: đoạn đáp án là **bảng tiếng Nhật nằm giữa pack**,
  không trùng khớp từ vựng với câu hỏi tiếng Việt ngoài chính mã trường `HOUSE_METHOD`.
- **Điểm mới — B2 thoái lui so với P1.4**: fix số 1 Phase A (chọn claim theo giá trị) đã hạ hạng
  dòng chứa mã tệp `YY2-Z151.exe`/`YY2-Z152.exe` (đoạn `[1]`, doc `wsc-5035a3d752d88cc0e20eb4c3`,
  `score=29.0`, bằng chứng còn trong pack). Câu trả lời E2 trích `[5]`,`[6]`,`[10]`,`[2]`,`[3]` —
  không còn tên tệp `.exe`. Đây là thoái lui do chính code của Muse, phải sửa.
- Các tiêu chí còn lại của E2 đều ĐẠT (không ai được làm hỏng):
  B1/B2/B3/B5 chạy xong không lỗi/không timeout (52,75/21,55/17,51/24,92 giây, B4 chạy đủ 46,39s loại);
  câu trả lời grounded từ bằng chứng truy xuất, `provider_used=false` cả 5, `mode=local_extractive`;
  **không byte nào ghi lên D** (SHA kho production `062ec090…` không đổi, 2 lượt snapshot 0 thay đổi);
  **fail-closed chứng minh được** — 6 khóa cloud còn nguyên trong env, `create_synthesis_provider()`
  vẫn trả `None`, stderr worker 0 dòng gọi provider, 44 mẫu mạng = **0 kết nối**.
- Cảnh báo cho vòng chấm tới: câu trả lời B5 **có** chuỗi `'1'` — nhưng đó là
  `'1':マニュアル入庫` của trường `RECEIVE_TYPE` (đoạn `[3]`), **không phải** giá trị của `HOUSE_METHOD`.
  Chấm bằng khớp chuỗi thô sẽ ra dương tính giả; phải chấm theo ngữ cảnh `HOUSE_METHOD` + `倉庫`/`検査`.

## Phase A — Muse code trên VM (OMP KHÔNG làm gì ở phase này)

1. **Fix chọn dòng theo mã trường**: trích token dạng mã trường từ câu hỏi
   (ví dụ pattern `[A-Z][A-Z0-9_]{3,}` như `HOUSE_METHOD`, `ORICON_STATUS`) → claim/đoạn chứa mã
   trường đó được cộng điểm ưu tiên cao, kể cả khi phần còn lại của đoạn là tiếng Nhật và không
   trùng từ vựng với câu hỏi. Nếu pack có dòng định nghĩa của trường đó thì phải đưa vào claims.
2. **Fix trọng số mã định danh dạng tệp**: token dạng mã định danh/`*.exe`
   (`YY2-Z151.exe`, `YY2-Z152.exe`) được ưu tiên trong `_compose_grounded_claims`,
   không bị fix "chọn claim theo giá trị" hạ hạng. Bắt buộc không thoái lui B2.
3. **Test** (SQLite `:memory:`, không ghi index; dữ liệu mô phỏng từ dữ liệu thật, gắn mác
   `SIMULATED_` theo lệnh user 2026-09-28 21:14):
   - (a) B5-like: đoạn bảng tiếng Nhật có `HOUSE_METHOD` nằm giữa pack, không trùng từ vựng
     câu hỏi tiếng Việt → phải được chọn vào câu trả lời.
   - (b) B2-like: đoạn có `YY2-Z151.exe` → phải được chọn (test chống thoái lui).
   - (c) B1/B3-like: không được làm mất dữ kiện đã qua (test chống thoái lui).
4. Commit riêng từng phần, push fast-forward (cấm force).
5. Khi code push xong, Muse cập nhật mailbox (`trang-thai.md` → `moi`, ghi `e2v2_fix_commit`).
   **OMP chỉ sang Phase B khi thấy dòng `e2v2_fix_commit` trong mailbox.**

## Phase B — OMP chạy trên h410asrock (chỉ khi mailbox đã báo e2v2_fix_commit)

1. Pull commit fix. Không sửa code để "cho qua".
2. Chạy lại B1–B5 đúng protocol P1.4/E2: câu hỏi `docs/phieu-viec/ket-qua/FIX3_dieu-tra-B-sai.md`;
   tuyến nội bộ (deterministic/local, cấm cloud); index dùng bản copy trên C
   (`C:\AIOS_p1_4\tri_thuc\library.sqlite`, mở `mode=ro`), kiểm SHA khớp
   `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`; cấm ghi D;
   B4 loại khỏi chấm điểm.
3. ĐIỂM GIỮ NGUYÊN so với E2: **giữ nguyên** biến môi trường khóa cloud của máy (không blank)
   để kiểm chứng fix fail-closed — yêu cầu `provider_used=false` và worker stderr
   không có dòng gọi provider nào (cổng an toàn chạy trước như E2).
4. Báo cáo `docs/phieu-viec/ket-qua/VE_E2_vong2_chon-dong.md`: diff hành vi trước/sau fix,
   kết quả B1–B5 nguyên văn + latency, bằng chứng không ghi D (SHA + snapshot),
   bằng chứng fail-closed. Cập nhật mailbox `xong-cho-duyet`.

## Tiêu chí ĐẠT (Phase B)

- B1/B2/B3/B5 chạy xong, không lỗi, không timeout.
- B3 giữ được `nvarchar(4000)` (không thoái lui).
- B5 nêu được định nghĩa HOUSE_METHOD (`'0'` cất vào kho / `'1'` kiểm tra) —
  chấm theo ngữ cảnh `HOUSE_METHOD` + `倉庫`/`検査`, CẤM chấm bằng khớp chuỗi `'1'` thô.
- B2 giữ được `YY2-Z151.exe`/`YY2-Z152.exe` (không thoái lui so với P1.4).
- Câu trả lời grounded từ bằng chứng truy xuất (không bịa).
- Không byte nào ghi lên D (kiểm chứng được: snapshot + SHA).
- Không dữ liệu nào rời máy — kể cả khi khóa cloud tồn tại trong env (kiểm chứng fail-closed).

Rớt 1 trong các dòng kiểm có tên cụ thể (B3/B5/B2) → CHƯA ĐẠT, ghi rõ điểm rớt còn lại.

## Cấm kỵ

- Không gọi AI ngoài dưới mọi hình thức (kể cả "thử một câu").
- Không ghi lên D (kể cả log, cache, ledger).
- Không `--apply`, không vacuum, không embed.
- Không đụng `main`. Không force-push.

## Hàng đợi sau E2 vòng 2 (chưa làm, không nhét vào vé này)

- 422/496 document stale ở chế độ read-only → cần lượt chuẩn bị lại (có ghi/embed) do OMP làm.
- `source_path` trong index trỏ `..._canary/materialized_sources/` → xác nhận đường chuẩn bị
  nguồn trước khi app production truy vấn.
- E3 dọn XML ở extractor; E4 default backend ONNX fp32.
