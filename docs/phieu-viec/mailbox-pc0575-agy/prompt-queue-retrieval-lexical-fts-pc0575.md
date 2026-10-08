# VÉ: RETRIEVAL-LEXICAL-FTS-PC0575 (tối ưu chặng lexical FTS5 — điểm nghẽn cuối của truy hồi)

- Mã vé: `RETRIEVAL-LEXICAL-FTS-PC0575`
- Role gợi ý: PLAN (đo phân rã trước, chọn cách sửa theo bằng chứng) + DEFAULT khi code
- Máy: công ty KDTVN-PC0575 (CPU-only, KHÔNG dùng GPU)
- Báo cáo: `docs/phieu-viec/ket-qua/retrieval-lexical-fts-pc0575.md`
- Căn cứ: vé `RETRIEVAL-PERF-DIAG-PC0575` (lexical 52,5–84,0s/câu) + vé `RETRIEVAL-DENSE-NUMPY-PC0575` vừa ĐẠT (tổng warm 158,75 → 80,54s/câu; lexical giờ chiếm 71,7–83,8s, tức ~95% thời gian còn lại).

## Bối cảnh đã đo (không đo lại từ đầu)

- Chặng lexical FTS5 + chấm điểm ứng viên/diversity-cap bằng Python: 71,7–83,8 giây/câu ở trạng thái warm trên 3 câu chẩn đoán (Q0704/Q0701/Q0671).
- Mọi chặng khác đã nhanh: dense 0,61s, sparse warm ~0,4s, fusion <0,1s, embed ~0,2s.
- Giả thuyết từ chẩn đoán: FTS5 trả về hàng nghìn dòng ứng viên (đặc biệt từ các mảnh của bảng tính lớn `Loi KDTPS.xlsx`), sau đó Python chấm điểm + lọc đa dạng trên toàn bộ — cần giới hạn ứng viên ngay trong SQL (bm25 + LIMIT) hoặc bật đường lexical v2 nếu code đã có sẵn.

## Việc phải làm

**Bước 1 — Phân rã chặng lexical (chỉ đọc, có số):** trên 3 câu chẩn đoán + 7 câu nhóm A, đo riêng: (a) thời gian truy vấn FTS5 thuần, (b) số dòng ứng viên trả về theo từng tài liệu nguồn (liệt kê top tài liệu sinh nhiều ứng viên nhất), (c) thời gian chấm điểm Python, (d) thời gian diversity-cap. Xác định khâu nào ăn thời gian thật trước khi sửa. Nếu code đã có sẵn đường lexical thay thế (vd cờ `AIOS_RAGV2_LEXICAL_V2`) thì mô tả cơ chế của nó trong báo cáo.

**Bước 2 — Chụp baseline:** với code hiện tại (sau vé dense), ghi danh sách ngữ cảnh cuối (Top 15 sau fusion) của 10 câu trên vào file kết quả trong `local_runs/` + tóm tắt vào báo cáo (mã mảnh + hạng). Đây là mốc đối chiếu cho cổng parity ở Bước 4 — chụp TRƯỚC khi sửa bất cứ dòng nào.

**Bước 3 — Sửa theo bằng chứng Bước 1:** ưu tiên theo thứ tự: (1) giới hạn ứng viên trong SQL bằng bm25 của FTS5 + LIMIT hợp lý (nêu con số và căn cứ chọn), (2) chuyển phần chấm điểm lặp lại xuống SQL hoặc vector hoá, (3) bật đường lexical v2 có sẵn nếu nó đúng cơ chế cần thiết. Giữ fallback về đường cũ bằng biến môi trường/cờ, mặc định đường mới khi đạt cổng.

**Bước 4 — Cổng parity BẮT BUỘC (trượt = DỪNG, báo cáo nguyên trạng):** so danh sách ngữ cảnh cuối sau sửa với baseline Bước 2 trên 10 câu:
- Mọi câu nhóm A: tài liệu đích kỳ vọng vẫn nằm trong Top 3 và không câu nào mất tài liệu đích khỏi Top 15.
- Liệt kê MỌI khác biệt còn lại (mảnh nào vào/ra, đổi hạng bao nhiêu) kèm phán đoán từng mục có căn cứ. Cấm khẳng định "rủi ro thấp" thay cho bảng đối chiếu này.

**Bước 5 — Cổng hiệu năng + nghiệm thu dùng thật:**
- Lexical warm ≤ 10 giây/câu trên 3 câu chẩn đoán; tổng warm kỳ vọng ≤ ~15 giây/câu.
- Chạy 3 câu chẩn đoán qua đường app (`RagV2DevPipeline`/adapter) như các vé trước: đích đúng hạng + trích đáp án thật.

**Bước 6 — Cổng repo:** test đơn vị cho thay đổi (gồm test tắt cờ về đường cũ vẫn chạy), compileall, pytest các file liên quan, cli audit, import app — tất cả PASS.

## Rào cứng

- CPU-only; mở index chỉ đọc (`mode=ro`), kiểm kích thước/băm index trước–sau phải khớp tuyệt đối.
- Không đụng chặng dense/sparse/fusion ngoài phần lexical; không đổi rubric/cách chấm.
- Không merge `main`.
- Vé dài: mốc tiến độ tối thiểu 15 phút/lần vào `trang-thai.md` mailbox-pc0575-agy + checkpoint để ca sau resume được.
