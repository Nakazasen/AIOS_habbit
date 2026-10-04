# Ticket: ENRICH-STAGING-FILESTORE — Chốt kho bản thảo cặp enrichment bằng file (không qua importer)

> Verdict vé trước (`IMPORT-STAGING-ENRICH`, xem `docs/phieu-viec/ket-qua/import-staging-enrich.md`): PARTIAL trung thực — rào staging-only ĐẠT, dedup ĐẠT (0 trùng nguyên văn), M3/M4 ánh xạ 100%, smoke đọc 8 câu ĐẠT, kho không đổi; **0 cặp nhập staging** vì `golden_answer_importer` bắt buộc schema `GoldenAnswer` (JSONL + manifest, các trường bằng chứng `gap_id`, `case_ids`, `error_code`, `error_group`, `phenomenon`, `hypotheses`, `causal_mechanism`, `m4_branches`, `evidence_to_collect`, `confirm_criteria`) mà cặp fixed (6 trường: Khối, Ngôn ngữ, Bối cảnh, Cách hỏi, Hỏi, Đáp kèm nguồn) không có, và importer ép nhãn hệ thống `kiến thức đã được đào tạo bổ sung` trái rào cứng của vé.

## Quyết định kỹ thuật (Muse chốt theo bằng chứng, chế độ tự lái)

- **Phương án B (chốt):** KHÔNG nhập cặp enrichment draft qua `golden_answer_importer`. Lý do: (1) tự điền trường bằng chứng = bịa bằng chứng, trái chính sách "không bịa đáp án/evidence"; (2) ép nhãn importer trái rào "không gắn nhãn khi chưa duyệt"; (3) 54 file `.md` đã audit trong `docs/phieu-viec/chatgpt-enrichment-fixed/` (MOM 15 file/608 cặp, LSU 39 file/1.790 cặp, trừ Q639–Q648 có chủ đích) ĐÃ là kho bản thảo: có nhãn `MOM`/`LSU` + `Bản thảo — chưa qua chuyên gia duyệt` đúng rào, đã dedup, M3/M4 100%, versioned trong git, và là đầu vào trực tiếp của pipeline digest (sổ tay tri thức Markdown → context LLM). Nhập qua importer chỉ thêm rủi ro đụng chạm module dùng chung (golden pipeline, 48 test) mà không thêm giá trị.
- **Không đụng `golden_answer_importer.py`** trong vé này. Mâu thuẫn nhãn (importer ép nhãn `kiến thức đã được đào tạo bổ sung`) ghi nhận để Muse chính xem xét riêng — thợ không tự sửa module dùng chung.

## Việc cần làm (chỉ đọc + kiểm, không ghi DB, không sửa code)

1. Kiểm đếm cuối `docs/phieu-viec/chatgpt-enrichment-fixed/mom/` + `lsu/`: đủ 54 file, 2.398 cặp (MOM Q1–Q608, LSU Q609–Q2408 trừ Q639–Q648), mỗi cặp đủ 6 trường.
2. Kiểm nhãn: mỗi file có dòng `Bản thảo — chưa qua chuyên gia duyệt`; khối đúng `MOM`/`LSU`; KHÔNG có nhãn `kiến thức đã được đào tạo bổ sung` ở file nào.
3. Xác nhận thư mục `chatgpt-enrichment-raw/` không bị đụng (so manifest/kích thước với báo cáo audit).
4. Ghi báo cáo `docs/phieu-viec/ket-qua/enrich-staging-filestore.md`: kết quả 3 kiểm trên + ghi rõ quyết định phương án B và lý do. Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.

## Rào cứng

- Chỉ đọc, không ghi DB nào (staging hay production), không sửa code, không merge `main`.
- Không tạo file JSONL/manifest, không tự sinh trường bằng chứng cho cặp draft.
- Role gợi ý: SMOL/TINY (kiểm nhanh ~5 phút).
