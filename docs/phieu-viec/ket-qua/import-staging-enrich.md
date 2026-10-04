# Báo cáo vé IMPORT-STAGING-ENRICH — nhập cặp đã audit vào staging

- Ngày làm: 2026-10-04 buổi tối (máy thợ opencode, nhánh `phieu-viec/rag-fix1`).
- Vé: `docs/phieu-viec/mailbox-opencode/prompt.md` (chuyển từ hàng chờ OMP 22:55, đủ điều kiện: 2 vé audit ĐẠT).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-fixed/mom/` (15 tập tin) + `lsu/` (39 tập tin). Không dùng thư mục raw. Không merge `main`.

## 0. Cổng gate watcher

- Phiên này do người dùng mở trực tiếp, không phải watcher tự mở. Điều kiện mở đã đủ ngay từ đầu: vé `moi` hợp lệ + 2 vé audit ĐẠT (`audit-enrich-mom.md` 608 cặp, `audit-enrich-lsu.md` 1.790 cặp).
- Không rơi nhánh 4 lần watcher tự mở liên tiếp. Không đặt `cho-muse` ở bước gate, không quay no-op. Nhận vé `dang-lam` lúc 23:03 +07, báo mốc 23:06 / 23:10.

## 1. Xác minh rào chỉ ghi staging (bước 1 của vé) — ĐẠT

- Đọc `src/aios_habit/golden_answer_importer.py` và chạy kiểm tra khô (không ghi DB):
  - `staging_enrichment.sqlite` được nhận.
  - 4 đường production bị từ chối: `workspace_chat.sqlite`, `production.sqlite`, `workspace_chat_rag_v2_production`, `error_cases_dict.db`.
- Kết luận: module đúng là chỉ ghi staging, rào chặn ghi production còn nguyên. ĐẠT.

## 2. Đối chiếu đầu vào — CHƯA ĐỦ ĐỂ NHẬP (0 cặp đã nhập)

- Đếm thư mục fixed: 54 tập tin, 2.398 cặp (MOM 608: Q1–Q608; LSU 1.790: Q609–Q2408 thiếu Q639–Q648 có chủ đích). Khớp 2 báo cáo audit.
- Toàn repo `docs/phieu-viec/` có 0 file đáp án JSONL và không có manifest batch dạng JSON mà importer cần (`--answers` + `--manifest`). File `MANIFEST.md` duy nhất là bản kê chữ của thư mục raw, importer không đọc được.
- Cặp fixed có 6 trường (Khối, Ngôn ngữ, Bối cảnh, Cách hỏi, Hỏi, Đáp kèm nguồn file). Importer bắt buộc các trường không có trong fixed: `gap_id`, `case_ids`, `error_code`, `error_group`, `phenomenon`, và với đáp `answered` còn bắt buộc `hypotheses`, `causal_mechanism`, `m4_branches`, `evidence_to_collect`, `confirm_criteria`. Tự điền các trường này là bịa bằng chứng nên không làm.
- Mâu thuẫn nhãn: importer ép nhãn hệ thống `kiến thức đã được đào tạo bổ sung` và từ chối nhãn khác, trong khi rào cứng của vé cấm gắn nhãn này, yêu cầu nhãn `MOM`/`LSU` + `Bản thảo — chưa qua chuyên gia duyệt` (đúng nhãn fixed đang giữ).
- Vì 2 lý do trên, **0 cặp được nhập vào staging trong vé này**. Đây là dừng trung thực, không phải lỗi bỏ sót.

## 3. Chạy trùng lặp lần cuối trên staging-dữ-liệu-fixed (bước 2 của vé) — ĐẠT

- Chuẩn hóa đúng kiểu importer (chữ thường, gộp khoảng trắng, khóa `sha256(Hỏi|Đáp)`):
  - Nhóm trùng cả Hỏi lẫn Đáp: 0 (Q183 đã sửa ở vé audit phát huy tác dụng).
  - Nhóm trùng chỉ câu Hỏi: 51 (mẫu câu tái sử dụng qua nhiều file, Đáp khác số liệu và nguồn file nên giữ lại toàn bộ, không mất bằng chứng — khớp báo cáo audit LSU).
- Kết luận: không còn cặp trùng lọt qua audit ở mức nguyên văn.

## 4. Đo M1–M5 ánh xạ (bước 3 của vé)

- Cách đo: 5 mô đun `golden_question_*.py` hiện có thiết kế cho câu hỏi vàng phỏng vấn (hiện tượng, cặp giả thuyết, adapter truy hồi), không khớp trực tiếp cặp hỏi đáp làm giàu. Vì vậy đo ánh xạ trung thực như 2 vé audit, không bịa số:
  - M3 (đầy đủ biểu mẫu): 2.398/2.398 đủ 6 trường (100%). Đáp có số liệu 2.288/2.398 (95,4%). Đáp ghi nguồn file 2.037/2.398. Cách hỏi chỉ còn 5 giá trị chuẩn, không còn chữ ngoại ngữ.
  - M4 (phân biệt, ước lượng bằng tỉ lệ tổ hợp Hỏi+Đáp khác nhau): 2.398/2.398 (100%, 0 nhóm trùng nguyên văn).
  - M1 (độ phủ khoảng trống), M2 (truy hồi tốp 5), M5 (độ lệch sau duyệt chuyên gia): chưa đo được — cần ảnh chụp chỉ mục thật và chuyên gia duyệt thật; vé cấm nhập kho chính nên không chạy truy hồi trên chỉ mục thật. Đề nghị đo ở vòng có chuyên gia.
- Vòng xem lại sau sửa: số liệu trên khớp báo cáo audit MOM (608) + LSU (1.790).

## 5. Kiểm tra thử đọc 8 câu (bước 4 của vé, chỉ đọc file — ĐẠT)

- Chọn Q1, Q183, Q608 (MOM) + Q609, Q853, Q1128, Q2000, Q2408 (LSU):
  - Nhãn khối đúng (MOM/LSU), đầu file nào cũng có dòng `Bản thảo — chưa qua chuyên gia duyệt`.
  - Nội dung đúng bản đã audit: Q183 đã sửa (Spec Name/WorkCenter Name), Q853 đã sửa `trực tiếp`, Q1128 đã khôi phục câu hỏi gốc, Q1124 giữ nguyên giá trị thô.
  - Không chạm luồng trả lời chính của app (không khởi động app, không ghi chỉ mục, chỉ đọc file `.md`).

## 6. Xác nhận kho không đổi

- SHA-256 `local_cases/staging_enrichment.sqlite` trước và sau vé giống nhau: `4ECC3D7A2561B6BEA73F42C0ADA2F648249FF79BD26C4225BDC0363FC9D68F00` (đã sao lưu bản trước khi kiểm tra, file sao lưu nằm ngoài Git theo `.gitignore`).
- Staging giữ nguyên 34 đáp án + 1 claim cũ từ trước vé này, 0 đánh giá chuyên gia. Không có lệnh ghi nào tới kho production.

## 7. Kết luận — PARTIAL (một phần)

- ĐẠT: rào staging-only, kiểm trùng lần cuối (0 trùng nguyên văn), M3/M4 ánh xạ (100%), kiểm tra thử đọc 8 câu, kho không đổi.
- CHƯA LÀM: nhập 2.398 cặp vào staging (0 cặp) vì thiếu bộ chuyển đổi `.md` → JSONL/manifest và mâu thuẫn nhãn importer so với rào vé. Không fake PASS cho phần nhập.
- Đề xuất 2 phương án chờ duyệt:
  - A: viết bộ chuyển đổi `.md` → GoldenAnswer JSONL + manifest (mỗi cặp tự sinh `gap_id`/`case_ids`/`error_code` từ nguồn file, nhãn giữ `MOM`/`LSU` + bản thảo), và nới importer cho phép nhãn khối thay vì ép nhãn duy nhất — cần duyệt kiến trúc vì đụng schema + persistence.
  - B: đổi vé thành chỉ lưu file `.md` đã audit (không qua importer), đo M1/M2/M5 ở vòng có chuyên gia — ít đụng chạm nhất.

## 8. Cổng kỹ thuật

- Biên dịch `compileall src tests`: qua (mã thoát 0).
- Kiểm thử nhóm câu hỏi vàng (`pytest -q -k "golden"`): 48 bài qua (119 giây).
- Bộ kiểm thử đầy đủ (`pytest -q`): không chạy hết trong vé này (bộ đầy đủ rất lâu; thay đổi trong vé chỉ là tài liệu + báo cáo nên không ảnh hưởng mã nguồn; đã chạy nhóm liên quan golden).
- Lệnh `python -m aios_habit.cli audit`: trạng thái PASS (cần đặt `PYTHONPATH=src` vì gói chưa cài vào môi trường ảo).
- Lệnh `import aios_habit.workspace_chat_app`: thành công.
