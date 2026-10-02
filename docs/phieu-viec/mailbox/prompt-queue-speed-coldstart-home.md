# Vé: SPEED-COLDSTART-HOME — nghiệm thu cold-start trên máy nhà (GPU), lane Gemini/Router

Lane: [NHÀ] OMP đo trên máy nhà. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user chốt 2026-10-02 ~22:00)

- PC công ty (KDTVN-PC0575) đã tắt giữa chừng khi đang đo nghiệm thu cold-start (vé `SPEED-COLDSTART-PC0575`). Code P1–P4 (worker BGE sống lâu qua named pipe, `AIOS_RAGV2_WORKER_PERSIST=1`) đã push lên nhánh `phieu-viec/rag-fix1` — không mất code, máy nhà pull về đo tiếp được.
- User đính chính: máy nhà RẤT liên quan — tiếp tục đo nghiệm thu cold-start trên máy nhà thay vì treo vé.
- Luồng C-Agent ở nhà không dùng được → đo bằng **lane 1 (Gemini Web qua cầu nối)** / **lane 3 (Nakazasen Router)**.

## Phase 0 — chốt trạng thái vé trước (bắt buộc)

- Vé `LLM-ENABLE-DO-NHA` đang `dang-lam` từ 06:51 ngày 2026-10-02 (im lặng ~15 tiếng, bất thường). Kiểm tra OMP/watcher còn sống không; nếu vé chưa xong thì hoàn tất trước, vì vé này cần công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` để có lane 1/3.
- Ghi rõ vào báo cáo: `LLM-ENABLE-DO-NHA` xong hay chưa, lane 1/3 có sẵn sàng không. Nếu lane 1/3 chưa dùng được thì DỪNG vé này, đặt `cho-muse`, không đo chay.

## Việc OMP làm [NHÀ]

1. Pull code mới nhất nhánh `phieu-viec/rag-fix1` (có worker BGE persist qua named pipe).
2. Restart app 3 lần; mỗi lần xác nhận worker tái sử dụng (gắn lại cùng PID, không nạp lại model), config lệch bị chặn đúng như thiết kế P3+P4.
3. Đo 6 câu L1–E3 ở trạng thái lạnh (ngay sau restart app), mỗi câu ghi 3 mốc: thời gian retrieval / synthesis / tổng, kèm lane đã dùng (1 hay 3).
4. Đo thời gian nạp model lần đầu (cold init) để đối chiếu với số đo PC0575 (180,9–408,5 giây).
5. Kiểm parity: đáp án 6 câu khớp với các lượt đo trước (`hodap-home`, `llm-enable-do-nha`). Đo SHA `collections/tri_thuc/library.sqlite` trước/sau — phải không đổi.

## Tiêu chí ĐẠT

- 3/3 lần restart tái dùng worker cũ (không nạp lại model).
- 6/6 câu lạnh trả lời thành công qua lane 1 hoặc 3, có bảng thời gian tách retrieval/synthesis/tổng.
- Parity đạt; SHA index production không đổi.

## Báo cáo

- `docs/phieu-viec/ket-qua/speed-coldstart-home.md` + `xong-cho-duyet`.
