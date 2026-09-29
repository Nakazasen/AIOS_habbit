# Vé E2 vòng 4 — Khắc phục 2 điểm rớt của E2v3 + chạy lại B1–B5

Ngày viết: 2026-09-29 (Muse VM, chế độ tự lái: CẤM hỏi user, ĐIỀU HƯỚNG ĐẾN XONG).
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Không force-push.

## Verdict E2v3: CHƯA ĐẠT (Muse verify độc lập, 2026-09-29 ~21:35 +07)

Bằng chứng (báo cáo `docs/phieu-viec/ket-qua/VE_E2_vong3_chon-dong.md`, commit `59e8974`,
đọc toàn văn trên VM):
- Cổng Phase B hợp lệ: `e2v3_fix_commit` = `ada3ed5` là tổ tiên của HEAD lúc chạy
  `8add0f1` (verify độc lập qua Commits API) → lượt chạy đúng code fix vòng 3.
- Nội dung ĐẠT: B1 (đủ `11922`/`12860`/`12626`), B3 (`nvarchar(4000)`),
  B5 (định nghĩa `HOUSE_METHOD`: `'0'` cất vào kho / `'1'` kiểm tra — chấm ngữ cảnh),
  B2 (đủ `YY2-Z151.exe`/`YY2-Z152.exe`, sau phục hồi). B4 loại khỏi chấm. Bộ chấm tự kiểm 9/9.
  → Fix vòng 3 có tác dụng đúng hướng: B2/B5 đã lên được nội dung.
- An toàn giữ nguyên: snapshot cây kho mã trên D 114.052 tệp, 0 thêm/0 xóa/0 đổi;
  SHA index D và C `062ec090…` không đổi, mtime nguyên; 6 khóa cloud còn nguyên trong env,
  `create_synthesis_provider()` → `none`, `provider_used=false` cả 5 câu.
- **Điểm rớt 1 — B2 có lỗi worker**: `SemanticBackendError` → khởi động lại worker →
  tổng 326,818 giây, vượt ngân sách 180 giây/câu → rớt tiêu chí "chạy xong, không lỗi".
- **Điểm rớt 2 — sự cố `functions.find`**: ở mốc nhận vé, lệnh tìm kiếm phát sinh 27 request
  OpenRouter (đều HTTP 402 `insufficient credits`); 19 tệp/24,1 KB đã bị đọc nhưng không
  chứng minh được nội dung chưa rời máy → rớt tiêu chí "không dữ liệu nào rời máy,
  kiểm chứng được".
- Báo cáo OMP trung thực, không giấu sự cố → dùng làm đầu vào vòng 4.

## Phạm vi vòng 4 (Phase B thuần túy — KHÔNG Phase A, chưa có code cần sửa)

1. **Điều tra + chốt sự cố `functions.find`** (ưu tiên 1):
   - Liệt kê chính xác 19 tệp đã bị đọc (từ log agent), phạm vi
     `local_runs/workspace_chat_rag_v2_production/`; ghi danh sách vào báo cáo vòng 4.
   - Coi đây là sự cố rò rỉ tiềm ẩn: **KHÔNG gọi thêm bất kỳ request ngoài nào** để "kiểm tra lại".
   - Từ vòng này: **CẤM dùng `functions.find` và mọi công cụ AI/mạng ngoài** trong vé E-series —
     tìm kiếm tệp chỉ dùng `ripgrep`/`grep`/`git ls-files` cục bộ. Ghi cam kết vào báo cáo.
2. **Điều tra B2 chậm + worker lỗi** (ưu tiên 2):
   - Đọc log worker vòng 3 (`C:/AIOS_p1_4/out/e2v3/`): nguyên nhân `SemanticBackendError`
     (thiếu bộ nhớ? input dài? ONNX provider?); vì sao vòng 3 chậm gấp ~10x vòng 2 trên cùng
     cấu hình (B1 143s vs 12,7s; B2 327s vs 13,3s).
   - Nếu là yếu tố môi trường (máy bận việc khác, cache lạnh...) → loại trừ rồi chạy lại.
     Nếu là lỗi code/model → báo về Muse, **không tự sửa code synthesis**, chờ vé Phase A.
3. **Chạy lại B1–B5** đúng protocol E2v3: câu hỏi
   `docs/phieu-viec/ket-qua/FIX3_dieu-tra-B-sai.md`; tuyến nội bộ (deterministic/local,
   cấm cloud); index dùng bản copy trên C (`C:\AIOS_p1_4\tri_thuc\library.sqlite`,
   mở `mode=ro`), kiểm SHA khớp `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`;
   cấm ghi D; giữ nguyên 6 khóa cloud trong env để kiểm fail-closed; B4 chạy nhưng loại khỏi chấm.
4. **Chốt chính sách lưu trữ** (áp dụng vĩnh viễn từ vòng này): nguyên văn câu trả lời trích từ
   tài liệu nội bộ **chỉ lưu local** (`C:/AIOS_p1_4/out/e2v4/`), KHÔNG đưa vào Git — theo
   DATA_POLICY `local_only` của repo. Báo cáo Git chỉ giữ giá trị tối thiểu để đối chiếu tiêu chí
   (mã/trích dẫn kiểm, latency, SHA, snapshot, danh sách sự cố). OMP vòng 3 làm đúng chính sách
   khi không đưa nguyên văn vào Git — ghi nhận, không tính là điểm trừ.
5. Báo cáo `docs/phieu-viec/ket-qua/VE_E2_vong4_chon-dong.md`, cập nhật mailbox `xong-cho-duyet`.

## Tiêu chí ĐẠT (vòng 4)

- B1/B2/B3/B5 chạy xong, **không lỗi worker**, không timeout; mỗi câu < 180 giây.
- B3 giữ được `nvarchar(4000)` (không thoái lui).
- B5 nêu được định nghĩa HOUSE_METHOD (`'0'` cất vào kho / `'1'` kiểm tra) —
  chấm theo ngữ cảnh `HOUSE_METHOD` + `倉庫`/`検査`, CẤM chấm bằng khớp chuỗi `'1'` thô.
- B2 giữ được `YY2-Z151.exe`/`YY2-Z152.exe`.
- Câu trả lời grounded từ bằng chứng truy xuất (không bịa); nguyên văn lưu local, đường dẫn
  ghi trong báo cáo.
- Không byte nào ghi lên D (kiểm chứng được: snapshot + SHA).
- Không dữ liệu nào rời máy — kiểm chứng fail-closed: **không công cụ AI/mạng ngoài nào
  được gọi trong cả lượt, kể cả ở mốc nhận vé**; 6 khóa cloud còn nguyên trong env;
  `provider_used=false`; worker stderr không có dòng gọi provider.

Rớt 1 trong các dòng kiểm có tên cụ thể (B3/B5/B2) → CHƯA ĐẠT, ghi rõ điểm rớt còn lại
+ nguyên nhân gốc ở khâu nào (trích trace `_fragment_score` như vòng 2/3).

## Cấm kỵ

- Không gọi AI ngoài dưới mọi hình thức (kể cả "thử một câu"); đặc biệt **cấm `functions.find`**.
- Không ghi lên D (kể cả log, cache, ledger).
- Không `--apply`, không vacuum, không embed.
- Không sửa code synthesis (chờ vé Phase A nếu điều tra chỉ ra lỗi code).
- Không đụng `main`. Không force-push.

## Hàng đợi sau E2 (chưa tới lượt — giữ nguyên trong `trang-thai.md`)

`stale-check` → `don-o-c` → `onnx-upload-drive` → `E3` → `E4` →
`buoc0-deploy` (**DEADLINE 30/09 23:59**) → `TOOL-1` → `TOOL-2` → `TOOL-3` → `TOOL-4` → `TOOL-5`.
