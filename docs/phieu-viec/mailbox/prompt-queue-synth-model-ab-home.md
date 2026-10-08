# VÉ: SYNTH-MODEL-AB-HOME (A/B từng model free làm model chính tổng hợp — chốt con gánh lane theo số đo)

- Mã vé: `SYNTH-MODEL-AB-HOME`
- Role gợi ý: DEFAULT (đo + phân tích)
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-model-ab-home.md`
- Căn cứ: kết quả vé `ROUTER-POOL-COMMANDCODE-HOME` (báo cáo `router-pool-commandcode-home.md` §4): pool free chạy 50/50 câu, 0 lỗi kỹ thuật, GPA 1,25 — nhưng **validated chỉ 1/50** (lane Gemini cũ đạt 9/50) và model chính `ling-3.1-flash` (trễ ~14,8s) bị router luân chuyển, `ling-3.0-flash-sante` gánh 48/50 câu. Chưa rõ validated thấp là do model gánh (sante) hay do cả pool — vé này tách bạch bằng thực nghiệm.

## Việc phải làm

1. Dùng đúng bộ 50 câu LSU + đúng runner/harness của vé ROUTER (CPU-only, index chỉ đọc, kiểm băm trước/sau như vé ROUTER §4.1). Chạy 3 lượt đo, mỗi lượt ÉP một model free làm tuyến tổng hợp duy nhất (tắt luân chuyển/failover sang model khác; fallback trích cục bộ vẫn giữ như hành vi production):
   - Lượt A: `inclusionai/ling-3.1-flash:free`
   - Lượt B: `inclusionai/ling-3.0-flash-sante:free`
   - Lượt C: `poolside/laguna-s-2.1-free`
2. Mỗi lượt ghi: tổng điểm/GPA, số câu validated, số câu fallback, số câu đạt 3.0 và ≥2.0, độ trễ trung bình/câu, lỗi kỹ thuật, credits tiêu thụ (kỳ vọng $0).
3. Báo cáo: bảng so 3 lượt cạnh số của lane pool hiện tại (62,67 — GPA 1,25 — validated 1) và lane Gemini cũ (61,17 — GPA 1,22 — validated 9); kết luận khuyến nghị model chính cho lane tổng hợp + thứ tự failover, dựa trên validated trước, GPA sau, độ trễ cuối. Nếu cả 3 model free đều validated thấp hơn hẳn Gemini: nêu thẳng kết luận đó + đề xuất hướng tiếp (vd tiêu chí claim budget có đang quá khắt với phong cách viết của nhóm model này — chỉ nêu quan sát, không tự sửa claim budget ở vé này).

## Rào cứng

- Chỉ đo + phân tích; không sửa code/config production ở vé này (cấu hình ép tuyến chỉ trong phạm vi runner đo, khôi phục sau đo); không ghi index (kiểm băm trước/sau); không merge `main`.
- Đo bằng model free: $0 credits; nếu một model lỗi tuyến kéo dài thì ghi nhận và chuyển lượt, không tự đổi sang model trả phí.
