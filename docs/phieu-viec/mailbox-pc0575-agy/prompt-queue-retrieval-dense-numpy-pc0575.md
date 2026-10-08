# VÉ: RETRIEVAL-DENSE-NUMPY-PC0575 (bật đường dense numpy + cache ma trận RAM — cắt ~105 giây/câu, parity tuyệt đối)

- Mã vé: `RETRIEVAL-DENSE-NUMPY-PC0575`
- Role gợi ý: DEFAULT (code + đo kiểm parity trên máy công ty)
- Máy: công ty KDTVN-PC0575 (CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/retrieval-dense-numpy-pc0575.md`
- Căn cứ: báo cáo `retrieval-perf-diag-pc0575.md` §4 — quét dense thuần Python tốn 104,5–108,7s/câu (~66% thời gian warm); đường numpy đã có sẵn trong code (`AIOS_RAG_V2_NUMPY_DENSE`, mặc định tắt) cho 0,48s ở trạng thái warm với Top 5 khớp 100%. Vé này biến đường đó thành mặc định an toàn.

## Việc phải làm

1. Đọc đường dense hiện tại trong `src/aios_habit/rag_v2/index.py` (hàm `dense_candidates` + chỗ đọc `AIOS_RAG_V2_NUMPY_DENSE`): xác định vòng đời ma trận numpy hiện có (nạp mỗi lần gọi hay đã cache theo tiến trình). Nếu chưa cache: bổ sung cache ma trận dense theo tiến trình (nạp 1 lần từ SQLite chỉ-đọc, giữ trong RAM ~497MB, khoá an toàn luồng nếu cần), dùng lại cho mọi câu hỏi sau.
2. Đổi mặc định: đường numpy là mặc định khi numpy khả dụng; biến môi trường vẫn cho tắt về đường Python cũ (rollback 1 dòng). Khi numpy không khả dụng: tự rơi về đường Python + ghi log tiếng Việt rõ ràng, không sập.
3. Cổng parity (BẮT BUỘC, trên chỉ mục thật PC0575, chỉ-đọc): 3 câu chẩn đoán (`Q0704, Q0701, Q0671`) + 7 câu nhóm A của `RETRIEVAL-ENTITY-PC0575` — danh sách ứng viên dense Top 15 phải trùng tuyệt đối (mã + thứ tự; điểm số sai lệch chỉ trong dung sai float) giữa đường Python và đường numpy; đối chiếu thêm Top context đầu-cuối của pipeline trên 3 câu chẩn đoán.
4. Đo hiệu năng sau sửa trên 3 câu chẩn đoán (điều kiện như vé PERF-DIAG): chặng dense warm ≤ 2s/câu; ghi tổng retrieval warm trước/sau cạnh nhau (kỳ vọng tổng warm từ ~158s xuống còn ~55s — khâu lexical chưa đụng ở vé này, không hứa quá).
5. Nghiệm thu dùng thật: chạy qua đường của app (adapter/pipeline như app dùng) tối thiểu 3 câu chẩn đoán, nộp số đo từng chặng sau sửa.
6. Test: test đơn vị cho đường numpy (parity trên vector tổng hợp nhỏ, cờ tắt = hành vi cũ, thiếu numpy = fallback an toàn) + cổng repo đầy đủ (compileall, pytest liên quan, cli audit PASS, import app OK). Ghi nhận mức RAM của cache ma trận trong báo cáo.

## Rào cứng

- Không ghi chỉ mục (kiểm md5/băm trước/sau như các vé trước); không merge `main`.
- Parity trượt ở bất kỳ câu nào trong cổng mục 3 = DỪNG, báo cáo nguyên nhân, không nới cổng.
- Không đụng khâu lexical/sparse ở vé này (có vé riêng sau).
