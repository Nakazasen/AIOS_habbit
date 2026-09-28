# Vé E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại)

Ngày viết: 2026-09-29 (Muse VM, chế độ tự lái: CẤM hỏi user, ĐIỀU HƯỚNG ĐẾN XONG).
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Không force-push.

## Bối cảnh
- P1.4 **ĐẠT** (verdict Muse 2026-09-29, verify độc lập SHA/diff: báo cáo chỉ thêm 1 file
  `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`, không sửa code sản phẩm;
  SHA kho production trên D `062ec090…` không đổi sau toàn bộ lượt chạy; 43 mẫu mạng = 0 kết nối;
  B1/B2/B3/B5 chạy xong 50,8/18,2/19,6/21,9s, grounded, `provider_used=false`). **P1.3 đóng.**
- E1 đợt 2 xong (chỉ đọc, không sửa code): 9 điểm synthesis làm rớt dữ kiện —
  3 cũ (A1: budget 5 claim + duyệt pack theo thứ tự; A2: summary prepend với intent general;
  A3: chấm fragment chỉ đếm token overlap) + 6 mới (B1: repair vượt budget XÓA dữ kiện;
  B2: 1 dòng lỗi vứt cả đáp án provider; B3: mỗi facet đúng 1 claim; B4: mỗi evidence item 1 fragment;
  B5: pack giới hạn 5 chunk/document; B6: `max_claims` không nhất quán).
  Chi tiết: `docs/phieu-viec/ket-qua/E1_synthesis-dieu-tra-dot2.md` (Muse đưa vào repo ở Phase A).
- Bằng chứng thật từ P1.4 mà E2 phải fix: B3 rớt nguyên văn `nvarchar(4000)`;
  B5 rớt định nghĩa HOUSE_METHOD `'0':倉庫へ格納 '1':検査` dù đoạn bằng chứng có trong pack.

## Phase A — Muse code trên VM (OMP KHÔNG làm gì ở phase này)
- Implement 6 đề xuất fix ở mục C của E1 + test (test dùng SQLite `:memory:`, không ghi index).
- Fix fail-closed provider (commit tách biệt, revert độc lập được):
  `create_synthesis_provider()` không tự dựng provider cloud từ biến môi trường;
  chỉ dựng khi opt-in rõ ràng (cờ/env mới, mặc định TẮT).
- Commit riêng từng phần, push fast-forward (cấm force).
- Khi code push xong, Muse cập nhật mailbox (`trang-thai.md` → `moi`, ghi `e2_fix_commit`).
  **OMP chỉ sang Phase B khi thấy dòng `e2_fix_commit` trong mailbox.**

## Phase B — OMP chạy trên h410asrock (chỉ khi mailbox đã báo e2_fix_commit)
1. Pull commit fix. Không sửa code để "cho qua".
2. Chạy lại B1–B5 đúng protocol P1.4: câu hỏi `docs/phieu-viec/ket-qua/FIX3_dieu-tra-B-sai.md`;
   tuyến nội bộ (deterministic/local, cấm cloud); index mở `mode=ro` hoặc copy sang C rồi chạy;
   cấm ghi D; B4 loại khỏi chấm điểm. Chạy trên cùng tập 74 document read-only như P1.4 (không embed).
3. ĐIỂM MỚI so với P1.4: **giữ nguyên** biến môi trường khóa cloud của máy (không blank)
   để kiểm chứng fix fail-closed — yêu cầu `provider_used=false` và worker stderr
   không có dòng gọi provider nào.
4. Báo cáo `docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`: diff hành vi trước/sau fix,
   kết quả B1–B5 nguyên văn + latency, bằng chứng không ghi D,
   bằng chứng không gọi cloud dù khóa tồn tại trong env. Cập nhật mailbox `xong-cho-duyet`.

## Tiêu chí ĐẠT (Phase B)
- B1/B2/B3/B5 chạy xong, không lỗi, không timeout.
- B3 nêu được `nvarchar(4000)`; B5 nêu được định nghĩa HOUSE_METHOD
  (`'0'` cất vào kho / `'1'` kiểm tra). Rớt 1 trong 2 → CHƯA ĐẠT, ghi rõ điểm rớt còn lại.
- Câu trả lời grounded từ bằng chứng truy xuất (không bịa).
- Không byte nào ghi lên D (kiểm chứng được: snapshot + SHA).
- Không dữ liệu nào rời máy — kể cả khi khóa cloud tồn tại trong env (kiểm chứng fail-closed).

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
