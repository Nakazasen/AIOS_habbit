# VÉ: RAG-RETRIEVAL-NUMPY-COMPLETE-HOME (numpy hoá nốt các khâu quét còn lai Python thuần + đo phân bổ chặng + đo lại giao diện) — ƯU TIÊN CAO NHẤT HÔM NAY

- Mã vé: `RAG-RETRIEVAL-NUMPY-COMPLETE-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/rag-retrieval-numpy-complete-home.md`
- Điều kiện bốc: ngay khi vé `STRUCTURED-LANE-TEST-FIXTURE-HOME` nộp xong (vé này là hàng chờ số 1; user chỉ đạo 2026-10-11 ~15:26: dồn toàn lực hôm nay cho vòng tốc độ hỏi đáp).
- Bối cảnh đã kiểm chứng từ mã tại tip hiện hành: lõi quét dense trong `rag_v2/index.py` ĐÃ numpy hoá (matmul float32 + argpartition, bật mặc định). Hai điểm còn lai Python thuần trong `rag_v2/semantic.py`: `cosine_similarity` (dòng 300 — tổng Python trên từng vector ứng viên; được gọi trong các vòng chấm lại tại `index.py` các dòng ~2708/2812/2945) và `sparse_dot_similarity` (dòng 324 — tích chập từ điển Python; được gọi trong vòng quét sparse tại `index.py` ~3460, tức có thể tới hàng chục/hàng trăm nghìn lần gọi mỗi câu hỏi trên một khối). Truy hồi đo được ~22 giây/câu ở đợt quét khối tri thức nhưng CHƯA từng đo phân bổ theo chặng.

## Bước 0 — Đo phân bổ chặng TRƯỚC khi sửa (bắt buộc làm trước, nộp số đo thô)

Trên khối `lsu` (chỉ mục tách khối hiện hành), với bộ câu cố định = 4 câu của đợt quét khối tri thức (nguyên văn trong báo cáo vé `DESKTOP-KNOWLEDGE-BLOCK-QA-HOME`) cộng 4 câu đầu của bộ 50 câu LSU, đo thời gian từng chặng của đường truy hồi: (a) nhúng câu hỏi; (b) quét dense; (c) quét sparse; (d) chấm lại/hợp nhất/rerank; (e) tổng truy hồi. Chạy tối thiểu 2 lượt mỗi câu (lượt đầu phiên lạnh của tiến trình đo, lượt sau ấm), ghi bảng số thô vào báo cáo. Không sửa mã ở bước này.

## Bước 1 — Numpy hoá hai điểm lai

- Quét sparse: chuyển sang phép nhân ma trận–vector theo lô (dựng cấu trúc thưa theo chỉ mục token một lần cho mỗi lần nạp chỉ mục/khối, tái dùng giữa các câu hỏi), thay vòng lặp gọi `sparse_dot_similarity` từng mảnh.
- Chấm lại dense: chuyển các vòng gọi `cosine_similarity` từng ứng viên sang matmul theo lô trên ma trận ứng viên (tái dùng hạ tầng matmul đã có của quét dense).
- Giữ nguyên ngữ nghĩa: cùng tập ứng viên, cùng công thức điểm; sai lệch số học cho phép theo tiền lệ float32 đã ghi trong mã (mã hiện có ghi chú mức sai lệch đo được giữa matmul float32 và cosine Python — trích lại con số đó trong báo cáo và dùng làm trần). Giữ đường Python cũ làm dự phòng sau một cờ môi trường, theo đúng mẫu cờ của quét dense.
- Test tương đương bắt buộc: bộ test mới khẳng định trên dữ kiện tổng hợp + mẫu trích từ chỉ mục thật (nếu trích được an toàn, chỉ đọc): điểm từng mảnh khớp trong dung sai đã tuyên bố VÀ thứ hạng top-k giống hệt giữa đường cũ và đường mới. Không nới khẳng định để lấy đạt.

## Bước 2 — Đo lại + cổng chất lượng

- Đo lại bảng phân bổ chặng như Bước 0 (cùng bộ câu, cùng điều kiện) → bảng trước/sau cạnh nhau trong báo cáo.
- Chạy đủ 4 cổng chất lượng của repo (compileall, pytest, cli audit, import app). Mọi test rớt phải liệt kê và phân loại (liên quan thay đổi này hay có từ trước kèm bằng chứng).

## Bước 3 — Đo lại trên giao diện thật (computer use)

- Chạy lại đúng 4 câu đợt quét khối tri thức trên giao diện thật, khối `lsu`, CPU-only: đáp án phải HOÀN TẤT (không treo), chụp trọn thân đáp án từng câu, ghi tổng thời gian từng câu từ nhật ký của chính phiên giao diện. Mốc so sánh (đã kiểm chứng sau vé sửa làn tổng hợp): 40,56 / 116,69 / 120,00 / 139,46 giây.
- Áp cổng bằng chứng bản siết 11/10: ảnh không trùng byte, ảnh hoàn tất trọn thân, số đo truy về nhật ký phiên giao diện (số đo gọi hàm không tính cho bước này).
- Tên tệp rows/số liệu của vé này dùng hậu tố riêng theo mã vé, không ghi đè tệp của vé khác.

## Báo cáo
Bảng phân bổ chặng trước/sau, bảng thời gian giao diện trước/sau, danh sách test tương đương + kết quả 4 cổng, khai cấu hình hiệu lực của phiên đo (CPU-only, commit HEAD, backend từng câu ở bước 3).
