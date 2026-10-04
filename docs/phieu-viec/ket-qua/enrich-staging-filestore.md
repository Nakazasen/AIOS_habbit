# Báo cáo chốt kho bản thảo enrichment bằng tập tin (vé ENRICH-STAGING-FILESTORE)

- Ngày làm: 2026-10-04 buổi tối (máy thợ opencode, nhánh `phieu-viec/rag-fix1`).
- Vé: `docs/phieu-viec/mailbox-opencode/prompt.md` (phương án B sau verdict vé `IMPORT-STAGING-ENRICH` PARTIAL).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-fixed/mom/` (15 tập tin) + `lsu/` (39 tập tin). Đối chiếu gốc: `docs/phieu-viec/chatgpt-enrichment-raw/`. Không dùng nhập qua importer.
- Rào cứng tuân thủ: chỉ đọc, không ghi cơ sở dữ liệu nào, không sửa mã, không tạo tập tin JSONL/manifest, không tự sinh trường bằng chứng, không gộp nhánh `main`.

## 0. Cổng mở việc

- Phiên này do người dùng mở trực tiếp bằng lệnh `git pull`, không phải watcher tự mở. Điều kiện mở đủ ngay từ đầu: trạng thái `moi` + prompt phương án B hợp lệ.
- Không rơi nhánh 4 lần watcher tự mở liên tiếp. Không đặt `cho-muse`, không quay vòng không việc. Nhận vé `dang-lam` lúc 23:16 +07, báo mốc 23:22 +07.

## 1. Kiểm đếm cuối thư mục fixed — ĐẠT

- Tổng tập tin: 54 (MOM 15 + LSU 39). Đếm bằng liệt kê trực tiếp thư mục fixed.
- Tổng cặp: 2.398 (đếm dấu `## CÂU HỎI`). Dải số: Q1–Q2408, thiếu đúng 10 số Q639–Q648 bỏ trống có chủ đích vì tập tin `Thumbs.db` (khớp báo cáo audit LSU và manifest).
- Chi tiết: MOM Q1–Q608 (608 cặp), LSU Q609–Q2408 trừ Q639–Q648 (1.790 cặp). Số hiệu duy nhất 2.398/2.398, không trùng số, không thiếu ngoài dải chủ đích.
- Đủ 6 trường: kiểm từng khối câu hỏi có đủ `- Khối:`, `- Ngôn ngữ:`, `- Bối cảnh:`, `- Cách hỏi:`, `- Hỏi:`, `- Đáp:` — thiếu 0 trường (2.398/2.398 đạt 100%).

## 2. Kiểm nhãn — ĐẠT

- Nhãn bản thảo: 54/54 tập tin chứa dòng `Bản thảo — chưa qua chuyên gia duyệt` (33 tập tin dòng đầu `Trạng thái: Bản thảo...`, 21 tập tin dòng `Nhãn: LSU · Bản thảo...` ở đầu tập tin — khác cách trình bày nhưng cùng nội dung nhãn đúng rào).
- Nhãn khối: tập tin MOM chỉ chứa `- Khối: MOM`, tập tin LSU chỉ chứa `- Khối: LSU`. Không lệch khối, không lẫn khối trong cùng tập tin.
- Nhãn cấm của importer: quét toàn bộ 54 tập tin, 0 tập tin chứa `kiến thức đã được đào tạo bổ sung`. Đúng rào vé (giữ nhãn khối + bản thảo, không gắn nhãn khi chưa duyệt).

## 3. Xác nhận thư mục raw không bị đụng — ĐẠT

- Đếm hiện tại: `chatgpt-enrichment-raw/mom/` 15 tập tin + `lsu/` 39 tập tin = 54 tập tin enrichment (khớp số fixed và 2 báo cáo audit). Cộng thêm `dieuchinh/` 4 tập tin + `MANIFEST.md` + `README.md` = 60 tập tin toàn thư mục raw.
- Trạng thái git: `git diff HEAD -- docs/phieu-viec/chatgpt-enrichment-raw/` trống (không sửa, không thêm, không xóa trong phiên này). Nhật ký gần nhất của raw vẫn là các mẻ điều-tra-lỗi (batch-58/57/56), không có commit nào đụng raw trong vé này.
- Kết luận: raw giữ nguyên, mọi sửa audit nằm ở thư mục fixed.

## 4. Quyết định phương án B — chốt kho bằng tập tin, không qua importer

- Giữ nguyên quyết định của Muse trong prompt: phương án B — KHÔNG nhập cặp bản thảo qua `golden_answer_importer`.
- Lý do (theo bằng chứng vé trước):
  1. Tự điền trường bằng chứng (`gap_id`, `case_ids`, `error_code`, `error_group`, `phenomenon`, `hypotheses`, `causal_mechanism`, `m4_branches`, `evidence_to_collect`, `confirm_criteria`) cho cặp fixed 6 trường là bịa bằng chứng, trái chính sách không bịa đáp án/bằng chứng.
  2. Importer ép nhãn hệ thống `kiến thức đã được đào tạo bổ sung`, trái rào cứng giữ nhãn `MOM`/`LSU` + `Bản thảo — chưa qua chuyên gia duyệt`.
  3. 54 tập tin `.md` đã audit (đủ 2.398 cặp, dedup xong, M3/M4 100%, versioned trong git) đã là kho bản thảo, là đầu vào trực tiếp của pipeline digest (sổ tay tri thức Markdown thành ngữ cảnh mô hình). Nhập qua importer chỉ thêm rủi ro đụng module dùng chung mà không thêm giá trị.
- Không đụng `golden_answer_importer.py` trong vé này. Mâu thuẫn nhãn importer để Muse chính xem xét riêng.

## 5. Kết luận — ĐẠT, chờ duyệt

- Ba kiểm trên đều ĐẠT. Kho bản thảo chốt là 54 tập tin trong `chatgpt-enrichment-fixed/` (2.398 cặp, nhãn đúng, raw không đổi).
- Không ghi cơ sở dữ liệu, không sửa mã, không tạo JSONL/manifest trong vé này. Đề nghị Muse duyệt để khép vé.
